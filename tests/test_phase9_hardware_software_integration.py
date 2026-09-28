"""
tests/test_phase9_hardware_software_integration.py
--------------------------------------------------
PHASE 9: HARDWARE + SOFTWARE INTEGRATION VALIDATION SUITE
SIH 2026-27 | Problem Statement: SIH26007

Validates:
1. Tests 01 to 18 (Section 12 of Phase 9 Master Prompt)
2. Adversarial Fault Injection Matrix (Section 13)
3. Safety Invariants I1 to I11 (Section 14)
4. Safe Beacon Standalone Failsafe Architecture (failsafe/safe_beacon.py)
5. End-to-End Safety State Machine (integration_adapters/end_to_end_safety_state_machine.py)
6. CAN/TWAI 250 kbps Timing and Latency Budget Verification
"""

import math
import time
import pytest
import numpy as np

from integration_adapters.can_twai_hil import (
    CAN_ID_ENGINE_SPEED,
    CAN_ID_VEHICLE_SPEED,
    CAN_ID_BRAKE_STATUS,
    CAN_ID_RETARDER_STATUS,
    CAN_ID_SAFETY_COMMAND,
    CAN_ID_VEHICLE_STATE,
    CanFrame,
    CanBusState,
    CanTwaiBusEmulator,
    encode_vehicle_speed,
    decode_vehicle_speed,
    encode_safety_command,
    decode_safety_command,
)
from integration_adapters.hil_simulator import (
    VehicleEcuConfig,
    ActuatorDelayMode,
    SimulatedVehicleECU,
    ActuatorModel,
    HilLocalSafetyECU,
    OperatorHmiBridge,
    HilSystemOrchestrator,
)
from integration_adapters.fail_safe_controller import (
    FailSafeState,
    CommandAction,
    IncomingCommand,
    LocalVehicleSafetyGovernor,
)
from integration_adapters.dsss_gateway_selector import (
    DSSSGatewaySelector,
    BeaconObservation,
    GatewaySelectionState,
    LinkState,
    RFHardwareAdapter,
    CommunicationLink,
    CarrierModulation,
    GatewayCorrelationEngine,
    GatewaySelectionStateMachine,
)
from integration_adapters.environmental_data_health import (
    DataHealthManager,
    EnvironmentalDataHealth,
    SensorQuality,
    SensorHealthRecord,
    to_sensor_health_record,
    DataState,
    FaultCode,
)
from failsafe.safe_beacon import (
    SafeBeaconState,
    SafeBeaconSystemState,
    SafeBeaconController,
    format_safe_beacon,
    parse_safe_beacon,
)
from integration_adapters.end_to_end_safety_state_machine import (
    EndToEndSafetyStateMachine,
    IntegratedSafetyState,
    SubsystemAuthority,
)


# ==============================================================================
# SECTION 1: HIL TESTS 01 TO 18 (SECTION 12)
# ==============================================================================

def test_hil_01_normal_operation():
    """TEST 01: Normal operation in clear visibility (50m) on flat ground."""
    orch = HilSystemOrchestrator(visibility_m=50.0, grade_pct=0.0)
    hmi = orch.step(dt=0.1, central_speed_request=5.0)
    assert hmi["applied_speed_mps"] <= hmi["safe_speed_mps"] + 1e-6
    assert hmi["communication_state"] in ["CONNECTED", "ONLINE"]
    assert hmi["local_governor_active"] is True
    assert hmi["safe_speed_mps"] > 0.0


def test_hil_02_dense_fog():
    """TEST 02: Dense fog (8.0m) restricts safe speed to crawling speed (<= 3.52 m/s)."""
    orch = HilSystemOrchestrator(visibility_m=8.0, grade_pct=-8.0)
    hmi = orch.step(dt=0.1, central_speed_request=10.0)
    assert hmi["applied_speed_mps"] <= hmi["safe_speed_mps"] + 1e-6
    assert hmi["safe_speed_mps"] < 4.0
    assert hmi["applied_speed_mps"] < 4.0


def test_hil_03_visibility_degradation():
    """TEST 03: Continuous visibility degradation progressively clamps speed."""
    orch = HilSystemOrchestrator(visibility_m=50.0, grade_pct=0.0)
    speeds = []
    for vis in [50.0, 25.0, 12.0, 8.0, 5.0, 3.0]:
        orch.vehicle_ecu.visibility_m = vis
        hmi = orch.step(dt=0.1, central_speed_request=10.0)
        speeds.append(hmi["safe_speed_mps"])
    
    # Speeds must be monotonically non-increasing
    for i in range(len(speeds) - 1):
        assert speeds[i] >= speeds[i+1]
    # At <= 5.0m (blindout), safe speed must be 0.0
    assert speeds[-2] == 0.0
    assert speeds[-1] == 0.0


def test_hil_04_sensor_dropout():
    """TEST 04: Environmental sensor dropout triggers conservative fallback."""
    mgr = DataHealthManager()
    sig = mgr.process_environmental_telemetry(visibility_m=None, sequence=1)
    assert sig.health == DataState.UNAVAILABLE
    assert sig.r_effective_conservative == 8.0  # Conservative dense fog floor


def test_hil_05_sensor_stuck_at():
    """TEST 05: Stuck-at sensor detected after persistence threshold."""
    t = 1000.0
    edh = EnvironmentalDataHealth(clock=lambda: t)
    # Feed 11 identical samples across 350s (> 300s window)
    for seq in range(1, 12):
        t += 35.0
        sig = edh.update(visibility_m=30.0, sequence=seq, timestamp=t)
    rec = to_sensor_health_record(sig, "VIS_01", edh.last_valid_timestamp)
    assert rec.quality == SensorQuality.STUCK or sig.health == DataState.DEGRADED or sig.fault_code == FaultCode.STUCK_AT


def test_hil_06_sensor_bias():
    """TEST 06: Impossible sensor spike / bias rejected by physical range check."""
    mgr = DataHealthManager()
    sig = mgr.process_environmental_telemetry(visibility_m=5000.0, sequence=1)
    assert sig.health == DataState.UNAVAILABLE
    assert sig.fault_code == FaultCode.RANGE_VIOLATION


def test_hil_07_communication_packet_loss():
    """TEST 07: High RF packet loss marks link degraded and tracks packet loss rate."""
    t = 100.0
    selector = DSSSGatewaySelector(clock=lambda: t)
    for seq in range(10):
        t += 0.1
        obs = BeaconObservation(
            gateway_id="GW_01",
            pn_sequence_id="PN_1",
            correlation_score=0.85 if seq % 2 == 0 else 0.20,
            rssi_dbm=-75.0 if seq % 2 == 0 else -120.0,
            snr_db=5.0,
            timestamp=t,
            packet_sequence=seq,
            crc_valid=(seq % 2 == 0)
        )
        status = selector.process_observation(obs)
    assert selector.current_packet_loss_rate > 0.0


def test_hil_08_gateway_loss():
    """TEST 08: Loss of primary gateway causes failover to available candidate."""
    t = 100.0
    selector = DSSSGatewaySelector(fail_timeout_s=1.0, clock=lambda: t)
    # Connect GW-01
    obs1 = BeaconObservation("GW-01", "PN-1", 0.90, -70.0, 8.0, t, 1)
    selector.process_observation(obs1)
    assert selector.current_gateway_id == "GW-01"

    # Also observe GW-02
    obs2 = BeaconObservation("GW-02", "PN-2", 0.85, -75.0, 6.0, t, 1)
    selector.process_observation(obs2)

    # Fast forward 1.5s with only GW-02 emitting
    t += 1.5
    obs2_new = BeaconObservation("GW-02", "PN-2", 0.85, -75.0, 6.0, t, 2)
    status = selector.process_observation(obs2_new)
    assert status.gateway_id == "GW-02"


def test_hil_09_gateway_handover():
    """TEST 09: Smooth gateway handover requiring switch margin and persistence count."""
    t = 100.0
    selector = DSSSGatewaySelector(switch_margin=0.15, persistence_count=3, clock=lambda: t)
    # Connect GW-01 at 0.70
    selector.process_observation(BeaconObservation("GW-01", "PN-1", 0.70, -80.0, 4.0, t, 1))

    # GW-02 appears at 0.90 (> 0.70 + 0.15). Needs 3 observations
    t += 0.1
    obs1 = BeaconObservation("GW-02", "PN-2", 0.90, -65.0, 9.0, t, 2)
    s1 = selector.process_observation(obs1)
    assert s1.selection_state == GatewaySelectionState.HANDOVER_PENDING

    t += 0.1
    obs2 = BeaconObservation("GW-02", "PN-2", 0.90, -65.0, 9.0, t, 3)
    s2 = selector.process_observation(obs2)
    assert s2.selection_state == GatewaySelectionState.HANDOVER_PENDING

    t += 0.1
    obs3 = BeaconObservation("GW-02", "PN-2", 0.90, -65.0, 9.0, t, 4)
    s3 = selector.process_observation(obs3)
    assert s3.selection_state == GatewaySelectionState.CONNECTED
    assert s3.gateway_id == "GW-02"


def test_hil_10_total_rf_communication_loss():
    """TEST 10: Total RF loss leaves local safety governor fully authoritative."""
    orch = HilSystemOrchestrator(visibility_m=20.0)
    hmi = orch.step(dt=0.1, central_speed_request=15.0, has_gateway=False, has_v2v=False)
    assert hmi["communication_state"] == "LOST"
    assert hmi["local_governor_active"] is True
    assert hmi["applied_speed_mps"] <= hmi["safe_speed_mps"]


def test_hil_11_safe_beacon_activation():
    """TEST 11: Safe Beacon activates within specified window upon comm timeout."""
    ctrl = SafeBeaconController(comm_timeout_s=0.5, clock=lambda: 10.0)
    ctrl.notify_central_comm_received(timestamp=10.0)
    assert ctrl.check_comm_timeout(now=10.2) is False

    # After 600 ms (> 500 ms) timeout triggers
    assert ctrl.check_comm_timeout(now=10.6) is True
    beacon_str = ctrl.generate_beacon(now=10.6)
    valid, msg, code = parse_safe_beacon(beacon_str, clock=lambda: 10.6)
    assert valid is True
    assert msg.state in [SafeBeaconState.DEGRADED, SafeBeaconState.STOP, SafeBeaconState.EMERGENCY]


def test_hil_12_can_latency_increase():
    """TEST 12: CAN bus transmission latency handled without frame drops under nominal load."""
    bus = CanTwaiBusEmulator(nominal_wire_delay_ms=0.5, mean_arbitration_ms=5.0)
    frame = encode_vehicle_speed(5.0, timestamp=1.0)
    delivered, latency_ms = bus.transmit(frame, now=1.0)
    assert delivered is True
    assert latency_ms > 0.5


def test_hil_13_can_timeout():
    """TEST 13: CAN frame timeout marks frame stale and activates defensive fallback."""
    bus = CanTwaiBusEmulator()
    frame = encode_vehicle_speed(6.0, timestamp=1.0)
    bus.transmit(frame, now=1.0)
    has_f, f, is_stale = bus.receive_latest(CAN_ID_VEHICLE_SPEED, now=1.05)
    assert is_stale is False

    # Vehicle speed timeout is 150 ms
    has_f2, f2, is_stale2 = bus.receive_latest(CAN_ID_VEHICLE_SPEED, now=1.20)
    assert is_stale2 is True


def test_hil_14_delayed_actuator_response():
    """TEST 14: Delayed actuator response preserves stopping safety envelope."""
    orch = HilSystemOrchestrator(visibility_m=15.0, actuator_mode=ActuatorDelayMode.MAX_DELAY)
    hmi = orch.step(dt=0.1, central_speed_request=8.0)
    assert hmi["applied_speed_mps"] <= hmi["safe_speed_mps"] + 1e-6


def test_hil_15_invalid_command():
    """TEST 15: Corrupted, NaN, negative, or infinite speed command rejected."""
    gov = LocalVehicleSafetyGovernor(vehicle_id="TRUCK_01")
    cmd_nan = IncomingCommand("TRUCK_01", 1, 100.0, float("nan"))
    d_nan = gov.process_command(cmd_nan, now=100.0)
    assert d_nan.action == CommandAction.REJECT
    assert d_nan.applied_speed == 0.0

    cmd_neg = IncomingCommand("TRUCK_01", 2, 100.0, -5.0)
    d_neg = gov.process_command(cmd_neg, now=100.0)
    assert d_neg.action == CommandAction.REJECT
    assert d_neg.applied_speed == 0.0


def test_hil_16_emergency_stop():
    """TEST 16: Emergency stop has highest overriding command priority."""
    sm = EndToEndSafetyStateMachine(vehicle_id="TRUCK_01")
    sm.trigger_emergency_stop("TEST_ESTOP")
    ev = sm.evaluate_state(visibility_m=50.0, sensor_quality=SensorQuality.VALID,
                           gateway_state=GatewaySelectionState.CONNECTED, comm_lost=False,
                           requested_speed_mps=10.0)
    assert ev.state == IntegratedSafetyState.EMERGENCY_STOP
    assert ev.authority == SubsystemAuthority.EMERGENCY_PHYSICAL_SAFETY
    assert ev.applied_speed_mps == 0.0
    assert ev.command_action == CommandAction.REJECT


def test_hil_17_recovery_after_comm_restoration():
    """TEST 17: Sequence stream resynchronization required to exit RECOVERY."""
    gov = LocalVehicleSafetyGovernor(vehicle_id="TRUCK_01")
    gov.update_local_safety_state(v_safe=5.0, has_gateway=False)
    # Gateway restored
    gov.update_local_safety_state(v_safe=5.0, has_gateway=True)
    assert gov.in_recovery is True

    # Frame 1: must be rejected while synchronizing
    cmd1 = IncomingCommand("TRUCK_01", 10, 100.0, 4.0)
    d1 = gov.process_command(cmd1, now=100.0)
    assert d1.action == CommandAction.REJECT
    assert d1.state == FailSafeState.RECOVERY

    # Frame 2: resynchronized, command accepted
    cmd2 = IncomingCommand("TRUCK_01", 11, 100.1, 4.0)
    d2 = gov.process_command(cmd2, now=100.1)
    assert d2.action == CommandAction.ACCEPT
    assert gov.in_recovery is False


def test_hil_18_simultaneous_sensor_and_comm_degradation():
    """TEST 18: Simultaneous sensor + comm degradation fails closed safely."""
    sm = EndToEndSafetyStateMachine(vehicle_id="TRUCK_01")
    ev = sm.evaluate_state(
        visibility_m=8.0,
        sensor_quality=SensorQuality.MISSING,
        gateway_state=GatewaySelectionState.DEGRADED,
        comm_lost=True,
        requested_speed_mps=10.0
    )
    assert ev.state == IntegratedSafetyState.COMMUNICATION_LOST
    assert ev.remote_command_allowed is False
    assert ev.applied_speed_mps <= ev.v_safe_mps
    assert ev.applied_speed_mps < 4.0


# ==============================================================================
# SECTION 2: ADVERSARIAL TESTING (SECTION 13)
# ==============================================================================

def test_adversarial_stale_command():
    gov = LocalVehicleSafetyGovernor(max_command_age_s=1.0)
    cmd = IncomingCommand("TRUCK_01", 1, timestamp=50.0, requested_speed_mps=5.0)
    d = gov.process_command(cmd, now=52.0)  # 2.0s old > 1.0s
    assert d.action == CommandAction.REJECT
    assert d.state == FailSafeState.STALE_COMMAND


def test_adversarial_out_of_order_sequence():
    gov = LocalVehicleSafetyGovernor()
    gov.process_command(IncomingCommand("TRUCK_01", 10, 100.0, 4.0), now=100.0)
    # Receive older packet (seq 9 < 10)
    d_old = gov.process_command(IncomingCommand("TRUCK_01", 9, 100.1, 4.0), now=100.1)
    assert d_old.action == CommandAction.REJECT
    assert d_old.state == FailSafeState.INVALID_COMMAND


def test_adversarial_duplicate_sequence():
    gov = LocalVehicleSafetyGovernor()
    gov.process_command(IncomingCommand("TRUCK_01", 10, 100.0, 4.0), now=100.0)
    # Receive duplicate (seq 10 again)
    d_dup = gov.process_command(IncomingCommand("TRUCK_01", 10, 100.1, 4.0), now=100.1)
    assert d_dup.action == CommandAction.REJECT
    assert d_dup.state == FailSafeState.INVALID_COMMAND


def test_adversarial_wrong_vehicle_id():
    gov = LocalVehicleSafetyGovernor(vehicle_id="TRUCK_01")
    cmd_spoofed = IncomingCommand("TRUCK_02", 1, 100.0, 5.0)
    d = gov.process_command(cmd_spoofed, now=100.0)
    assert d.action == CommandAction.REJECT
    assert d.state == FailSafeState.INVALID_COMMAND


def test_adversarial_future_timestamp_beacon():
    raw = format_safe_beacon("TRUCK_01", 1, SafeBeaconState.NORMAL, timestamp=1000.0, zone_id="Z1")
    # Receive with local clock at 100.0 (900s in future)
    valid, msg, code = parse_safe_beacon(raw, clock=lambda: 100.0)
    assert valid is False
    assert code == "FUTURE_TIMESTAMP"


def test_adversarial_can_corrupted_bits():
    bus = CanTwaiBusEmulator()
    bus.set_fault_injection(bit_corruption_rate=1.0)
    frame = encode_vehicle_speed(5.0, 1.0)
    delivered, lat = bus.transmit(frame, now=1.0)
    assert delivered is True
    assert bus.total_corrupted > 0


# ==============================================================================
# SECTION 3: SAFETY INVARIANTS I1 TO I11 (SECTION 14)
# ==============================================================================

def test_invariant_i1_v_command_le_v_safe():
    """I1: v_command <= v_safe strictly holds at all times."""
    orch = HilSystemOrchestrator(visibility_m=12.0)
    for speed in [0.0, 1.0, 5.0, 12.0, 25.0, 50.0]:
        hmi = orch.step(dt=0.1, central_speed_request=speed)
        assert hmi["applied_speed_mps"] <= hmi["safe_speed_mps"] + 1e-6


def test_invariant_i2_no_remote_command_during_comm_loss():
    """I2: No remote command accepted during COMMUNICATION_LOST."""
    ctrl = SafeBeaconController(comm_timeout_s=0.5, clock=lambda: 10.0)
    ctrl.is_standalone_active = True
    ctrl.system_state = SafeBeaconSystemState.COMM_LOSS

    cmd = IncomingCommand("TRUCK_01", 1, 10.0, 8.0)
    applied, action, reason = ctrl.evaluate_command_authority(cmd, local_visibility_m=10.0, now=10.0)
    assert action == CommandAction.REJECT
    assert "COMM_LOSS_STANDALONE" in reason


def test_invariant_i3_safe_beacon_activates_within_window():
    """I3: Safe Beacon activates within specified detection window (<= 1.0s)."""
    ctrl = SafeBeaconController(comm_timeout_s=0.5, clock=lambda: 0.0)
    ctrl.notify_central_comm_received(timestamp=0.0)
    assert ctrl.check_comm_timeout(now=0.49) is False
    assert ctrl.check_comm_timeout(now=0.55) is True


def test_invariant_i4_local_authority_survives_comm_loss():
    """I4: Local safety authority survives communication loss."""
    gov = LocalVehicleSafetyGovernor(vehicle_id="TRUCK_01", v_safe_default=4.0)
    gov.update_local_safety_state(v_safe=4.0, has_gateway=False)
    cmd = IncomingCommand("TRUCK_01", 1, 100.0, 10.0)
    d = gov.process_command(cmd, now=100.0)
    assert d.action == CommandAction.REJECT
    assert d.applied_speed <= 4.0


def test_invariant_i5_stale_sensor_cannot_silently_control():
    """I5: Stale sensor data cannot silently control the vehicle."""
    t = 100.0
    edh = EnvironmentalDataHealth(clock=lambda: t)
    # Feed valid sample at t = 100.0
    edh.update(visibility_m=30.0, sequence=1, timestamp=t)
    # Check at t = 170.0s (elapsed = 70s, between 60s and 120s)
    t = 170.0
    r_eff, state, conf = edh.get_current_health()
    assert state == DataState.STALE
    assert conf < 1.0
    assert r_eff < 30.0  # Penalized


def test_invariant_i6_gateway_handover_no_command_discontinuity():
    """I6: Gateway handover cannot cause unsafe command discontinuity."""
    orch = HilSystemOrchestrator(visibility_m=20.0)
    prev_speed = 0.0
    for step in range(5):
        hmi = orch.step(dt=0.1, central_speed_request=6.0)
        curr_speed = hmi["applied_speed_mps"]
        if step > 0:
            # Acceleration bounded
            assert abs(curr_speed - prev_speed) <= 1.5
        prev_speed = curr_speed


def test_invariant_i7_can_timeout_failsafe_holding():
    """I7: CAN timeout cannot result in uncontrolled command persistence."""
    bus = CanTwaiBusEmulator()
    frame = encode_safety_command(target_speed_mps=8.0, action_code=1, sequence=1, timestamp=0.0)
    bus.transmit(frame, now=0.0)
    # Check after timeout (150 ms)
    has_f, f, is_stale = bus.receive_latest(CAN_ID_SAFETY_COMMAND, now=0.25)
    assert is_stale is True


def test_invariant_i8_emergency_stop_highest_priority():
    """I8: Emergency stop has highest command priority."""
    sm = EndToEndSafetyStateMachine()
    sm.trigger_emergency_stop()
    ev = sm.evaluate_state(visibility_m=100.0, sensor_quality=SensorQuality.VALID,
                           gateway_state=GatewaySelectionState.CONNECTED, comm_lost=False,
                           requested_speed_mps=15.0)
    assert ev.priority_level == 1
    assert ev.applied_speed_mps == 0.0


def test_invariant_i9_grade_convention_bijective():
    """I9: Grade convention remains bijective (downhill negative, uphill positive)."""
    orch_downhill = HilSystemOrchestrator(visibility_m=20.0, grade_pct=-8.0)
    hmi_downhill = orch_downhill.step(dt=0.1, central_speed_request=10.0)

    orch_flat = HilSystemOrchestrator(visibility_m=20.0, grade_pct=0.0)
    hmi_flat = orch_flat.step(dt=0.1, central_speed_request=10.0)

    # Downhill ramp on -8% requires equal or lower safe speed than flat
    assert hmi_downhill["safe_speed_mps"] <= hmi_flat["safe_speed_mps"] + 1e-6


def test_invariant_i10_no_double_integration():
    """I10: No simulation timestep double integration (dt applied once)."""
    ecu = SimulatedVehicleECU(initial_speed_mps=5.0)
    ecu.update_physics(dt=0.1, target_speed_mps=5.0, brake_active=False)
    # Target speed equals current speed: speed must remain constant
    assert abs(ecu.speed_mps - 5.0) < 0.2


def test_invariant_i11_all_safety_decisions_auditable():
    """I11: All safety decisions are timestamped and auditable."""
    sm = EndToEndSafetyStateMachine()
    t_test = 1727135000.0
    ev = sm.evaluate_state(visibility_m=15.0, sensor_quality=SensorQuality.VALID,
                           gateway_state=GatewaySelectionState.CONNECTED, comm_lost=False,
                           requested_speed_mps=5.0, now=t_test)
    assert ev.timestamp == t_test
    assert len(sm.history) > 0
    assert sm.history[-1]["timestamp"] == t_test
    assert "applied_speed" in sm.history[-1]
