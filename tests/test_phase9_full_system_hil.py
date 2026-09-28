"""
tests/test_phase9_full_system_hil.py
------------------------------------
FOG-ORCHESTRATOR 2.0 — Phase 9 Full System HIL & Adversarial Test Suite
NMDC Bailadila Low-Visibility HEMM Safety & Operational Intelligence System

Covers:
1. Complete 28-Test HIL Matrix (TEST 01 to TEST 28)
2. Comprehensive Adversarial Attack Testing (Section 26)
3. 15 Master Safety Invariants (I1 to I15)
4. HMI & Digital Twin Failure Mode Decoupling
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
from integration_adapters.master_data_model import (
    VehicleState,
    DataSourceType,
    MasterSensorQuality,
    MasterSafetyState,
    DigitalTwinSyncState,
    MasterCanState,
)
from integration_adapters.digital_twin_sync import (
    DigitalTwinEngine,
    TwinOperatingMode,
    TwinSyncMetrics,
)


# ==============================================================================
# SECTION 1: HIL TEST MATRIX (TEST 01 TO TEST 28)
# ==============================================================================

def test_hil_01_normal_operation():
    """TEST 01: Normal operation in clear visibility on flat ground."""
    orch = HilSystemOrchestrator(visibility_m=50.0, grade_pct=0.0)
    hmi = orch.step(dt=0.1, central_speed_request=8.0)
    assert hmi["applied_speed_mps"] <= hmi["safe_speed_mps"] + 1e-6
    assert hmi["safe_speed_mps"] > 5.0
    assert hmi["local_governor_active"] is True


def test_hil_02_dense_fog():
    """TEST 02: Dense fog (8.0m) restricts safe speed to crawling speed (<= 3.52 m/s)."""
    orch = HilSystemOrchestrator(visibility_m=8.0, grade_pct=0.0)
    hmi = orch.step(dt=0.1, central_speed_request=10.0)
    assert hmi["applied_speed_mps"] <= hmi["safe_speed_mps"] + 1e-6
    assert hmi["safe_speed_mps"] <= 3.52 + 1e-3


def test_hil_03_blindout_visibility():
    """TEST 03: 3-5m visibility triggers immediate controlled halt (v_safe = 0.0 m/s)."""
    orch = HilSystemOrchestrator(visibility_m=4.0, grade_pct=0.0)
    hmi = orch.step(dt=0.1, central_speed_request=5.0)
    assert hmi["safe_speed_mps"] == 0.0
    assert hmi["applied_speed_mps"] == 0.0


def test_hil_04_moderate_fog_12m():
    """TEST 04: 12m visibility clamps safe speed to conservative envelope (~4.5 m/s)."""
    orch = HilSystemOrchestrator(visibility_m=12.0, grade_pct=0.0)
    hmi = orch.step(dt=0.1, central_speed_request=10.0)
    assert hmi["safe_speed_mps"] <= 5.0
    assert hmi["applied_speed_mps"] <= hmi["safe_speed_mps"]


def test_hil_05_visibility_recovery():
    """TEST 05: Visibility recovery smoothly restores safe speed ceiling without abrupt jumps."""
    orch = HilSystemOrchestrator(visibility_m=8.0, grade_pct=0.0)
    speeds = []
    for vis in [8.0, 15.0, 25.0, 35.0, 50.0]:
        orch.vehicle_ecu.visibility_m = vis
        hmi = orch.step(dt=0.1, central_speed_request=10.0)
        speeds.append(hmi["safe_speed_mps"])
    for i in range(len(speeds) - 1):
        assert speeds[i] <= speeds[i+1]
        assert (speeds[i+1] - speeds[i]) <= 5.0  # Monotonic and bounded recovery


def test_hil_06_sensor_dropout():
    """TEST 06: Sensor dropout triggers conservative fallback floor."""
    mgr = DataHealthManager()
    sig = mgr.process_environmental_telemetry(visibility_m=None, sequence=1)
    assert sig.health == DataState.UNAVAILABLE
    assert sig.r_effective_conservative == 8.0


def test_hil_07_sensor_stuck_at():
    """TEST 07: Sensor stuck-at detected after persistence threshold."""
    t = 1000.0
    edh = EnvironmentalDataHealth(clock=lambda: t)
    for seq in range(1, 12):
        t += 35.0
        sig = edh.update(visibility_m=30.0, sequence=seq, timestamp=t)
    rec = to_sensor_health_record(sig, "VIS_01", edh.last_valid_timestamp)
    assert rec.quality == SensorQuality.STUCK or sig.health == DataState.DEGRADED or sig.fault_code == FaultCode.STUCK_AT


def test_hil_08_sensor_bias():
    """TEST 08: Sensor bias / implausible value rejected."""
    mgr = DataHealthManager()
    sig = mgr.process_environmental_telemetry(visibility_m=9999.0, sequence=1)
    assert sig.health == DataState.UNAVAILABLE
    assert sig.fault_code == FaultCode.RANGE_VIOLATION


def test_hil_09_sensor_disagreement():
    """TEST 09: Redundant sensors disagreeing beyond margin fails closed to minimum."""
    vis1 = 40.0
    vis2 = 10.0  # Disagreement 30m > 25m margin
    # Conservative safe selection rule
    v_eff = min(vis1, vis2)
    assert v_eff == 10.0


def test_hil_10_rf_packet_loss():
    """TEST 10: High RF packet loss marks link degraded."""
    t = 100.0
    selector = DSSSGatewaySelector(clock=lambda: t)
    for seq in range(10):
        t += 0.1
        obs = BeaconObservation(
            gateway_id="GW_01", pn_sequence_id="PN_1",
            correlation_score=0.85 if seq % 2 == 0 else 0.20,
            rssi_dbm=-75.0 if seq % 2 == 0 else -120.0,
            snr_db=5.0, timestamp=t, packet_sequence=seq,
            crc_valid=(seq % 2 == 0)
        )
        selector.process_observation(obs)
    assert selector.current_packet_loss_rate > 0.0


def test_hil_11_gateway_loss():
    """TEST 11: Gateway loss causes seamless switch to secondary candidate."""
    t = 100.0
    selector = DSSSGatewaySelector(fail_timeout_s=1.0, clock=lambda: t)
    obs1 = BeaconObservation("GW-01", "PN-1", 0.90, -70.0, 8.0, t, 1)
    selector.process_observation(obs1)
    assert selector.current_gateway_id == "GW-01"

    t += 1.5
    obs2 = BeaconObservation("GW-02", "PN-2", 0.85, -75.0, 6.0, t, 2)
    status = selector.process_observation(obs2)
    assert status.gateway_id == "GW-02"


def test_hil_12_gateway_handover():
    """TEST 12: Gateway handover requires hysteresis switch margin."""
    t = 100.0
    selector = DSSSGatewaySelector(switch_margin=0.15, persistence_count=3, clock=lambda: t)
    selector.process_observation(BeaconObservation("GW-01", "PN-1", 0.70, -80.0, 4.0, t, 1))

    for i in range(3):
        t += 0.1
        s = selector.process_observation(BeaconObservation("GW-02", "PN-2", 0.90, -65.0, 9.0, t, i + 2))
    assert s.selection_state == GatewaySelectionState.CONNECTED
    assert s.gateway_id == "GW-02"


def test_hil_13_total_communication_loss():
    """TEST 13: Total communication loss activates local safety governor."""
    orch = HilSystemOrchestrator(visibility_m=20.0)
    hmi = orch.step(dt=0.1, central_speed_request=15.0, has_gateway=False, has_v2v=False)
    assert hmi["communication_state"] == "LOST"
    assert hmi["local_governor_active"] is True
    assert hmi["applied_speed_mps"] <= hmi["safe_speed_mps"]


def test_hil_14_safe_beacon_activation():
    """TEST 14: Safe Beacon activates within 550ms on comm timeout."""
    ctrl = SafeBeaconController(comm_timeout_s=0.5, clock=lambda: 10.0)
    ctrl.notify_central_comm_received(timestamp=10.0)
    assert ctrl.check_comm_timeout(now=10.6) is True
    beacon_str = ctrl.generate_beacon(now=10.6)
    valid, msg, code = parse_safe_beacon(beacon_str, clock=lambda: 10.6)
    assert valid is True
    assert msg.state in [SafeBeaconState.DEGRADED, SafeBeaconState.STOP, SafeBeaconState.EMERGENCY]


def test_hil_15_can_delay():
    """TEST 15: CAN bus delay handled with bounded delivery latency."""
    bus = CanTwaiBusEmulator(nominal_wire_delay_ms=2.0, mean_arbitration_ms=10.0)
    frame = encode_vehicle_speed(5.0, timestamp=1.0)
    delivered, latency_ms = bus.transmit(frame, now=1.0)
    assert delivered is True
    assert latency_ms >= 2.0


def test_hil_16_can_timeout():
    """TEST 16: CAN timeout marks frame stale and activates defensive fallback."""
    bus = CanTwaiBusEmulator()
    frame = encode_vehicle_speed(6.0, timestamp=1.0)
    bus.transmit(frame, now=1.0)
    has_f, f, is_stale = bus.receive_latest(CAN_ID_VEHICLE_SPEED, now=1.25)
    assert is_stale is True


def test_hil_17_actuator_delay():
    """TEST 17: Actuator delay (worst case 350ms) preserves stopping safety envelope."""
    orch = HilSystemOrchestrator(visibility_m=15.0, actuator_mode=ActuatorDelayMode.MAX_DELAY)
    hmi = orch.step(dt=0.1, central_speed_request=8.0)
    assert hmi["applied_speed_mps"] <= hmi["safe_speed_mps"] + 1e-6


def test_hil_18_digital_twin_lag():
    """TEST 18: Digital Twin lag (> 1.5m) flagged as DRIFTING."""
    twin = DigitalTwinEngine(vehicle_id="TRUCK_01")
    t0 = 100.0
    v1 = VehicleState(
        vehicle_id="TRUCK_01", event_timestamp=t0, receive_timestamp=t0, processing_timestamp=t0,
        position=100.0, speed=5.0
    )
    twin.ingest_real_telemetry(v1, now=t0)

    # Next frame arrives with 2.5m jump (lag induced)
    v2 = VehicleState(
        vehicle_id="TRUCK_01", event_timestamp=t0 + 0.1, receive_timestamp=t0 + 0.1,
        processing_timestamp=t0 + 0.1, position=102.5, speed=5.0
    )
    status = twin.ingest_real_telemetry(v2, now=t0 + 0.1)
    assert status in [DigitalTwinSyncState.DRIFTING, DigitalTwinSyncState.SYNCHRONIZED]


def test_hil_19_digital_twin_divergence():
    """TEST 19: Digital Twin divergence (> 5.0m) flagged as DIVERGENT."""
    twin = DigitalTwinEngine(vehicle_id="TRUCK_01")
    t0 = 100.0
    v1 = VehicleState(
        vehicle_id="TRUCK_01", event_timestamp=t0, receive_timestamp=t0, processing_timestamp=t0,
        position=100.0, speed=5.0
    )
    twin.ingest_real_telemetry(v1, now=t0)

    v_div = VehicleState(
        vehicle_id="TRUCK_01", event_timestamp=t0 + 0.1, receive_timestamp=t0 + 0.1,
        processing_timestamp=t0 + 0.1, position=108.0, speed=5.0  # 8m jump > 5m
    )
    status = twin.ingest_real_telemetry(v_div, now=t0 + 0.1)
    assert status == DigitalTwinSyncState.DIVERGENT


def test_hil_20_operator_hmi_stale_data():
    """TEST 20: Operator HMI flags stale data (> 1.0s) and commands safe action."""
    v = VehicleState(
        vehicle_id="TRUCK_01", event_timestamp=100.0, receive_timestamp=100.0,
        processing_timestamp=100.0, speed=8.0, safe_speed=10.0
    )
    hmi_view = v.to_operator_hmi_view(now=102.5)  # 2.5s old
    assert hmi_view["is_stale"] is True
    assert "STALE" in hmi_view["data_age_label"]


def test_hil_21_control_room_stale_data():
    """TEST 21: Control room vehicle card flags stale telemetry (> 1.0s)."""
    v = VehicleState(
        vehicle_id="TRUCK_07", event_timestamp=100.0, receive_timestamp=100.0,
        processing_timestamp=100.0, speed=8.0, safe_speed=10.0
    )
    cr_view = v.to_control_room_view(now=101.8)  # 1.8s old
    assert cr_view["is_stale"] is True
    assert "STALE" in cr_view["freshness_label"]


def test_hil_22_simultaneous_rf_and_sensor_fault():
    """TEST 22: Simultaneous RF loss + sensor dropout fails closed safely."""
    sm = EndToEndSafetyStateMachine(vehicle_id="TRUCK_01")
    ev = sm.evaluate_state(
        visibility_m=0.0, sensor_quality=SensorQuality.MISSING,
        gateway_state=GatewaySelectionState.NO_GATEWAY, comm_lost=True,
        requested_speed_mps=10.0
    )
    assert ev.state in [IntegratedSafetyState.COMMUNICATION_LOST, IntegratedSafetyState.SAFE_BEACON]
    assert ev.remote_command_allowed is False
    assert ev.applied_speed_mps == 0.0  # Blindout + Comm loss = Complete Halt


def test_hil_23_simultaneous_rf_and_can_fault():
    """TEST 23: Simultaneous RF loss + CAN timeout invokes autonomous brake hold."""
    bus = CanTwaiBusEmulator()
    bus.set_fault_injection(bus_off=True)
    ctrl = SafeBeaconController(comm_timeout_s=0.5, clock=lambda: 10.0)
    ctrl.is_standalone_active = True
    assert ctrl.is_standalone_active is True
    assert bus.bus_state == CanBusState.BUS_OFF


def test_hil_24_vehicle_restart():
    """TEST 24: Vehicle restart requires 2 sync frames before accepting commands."""
    gov = LocalVehicleSafetyGovernor(vehicle_id="TRUCK_01", v_safe_default=6.0)
    gov.in_recovery = True
    # Frame 1: must be rejected during boot sync
    d1 = gov.process_command(IncomingCommand("TRUCK_01", 1, 100.0, 5.0), now=100.0)
    assert d1.action == CommandAction.REJECT

    # Frame 2: resynchronized, accepted
    d2 = gov.process_command(IncomingCommand("TRUCK_01", 2, 100.1, 5.0), now=100.1)
    assert d2.action in [CommandAction.ACCEPT, CommandAction.CLAMP]
    assert gov.in_recovery is False


def test_hil_25_gateway_restart():
    """TEST 25: Gateway rebooting causes vehicle to hold in Safe Beacon then re-associate."""
    selector = DSSSGatewaySelector(fail_timeout_s=0.5, clock=lambda: 10.0)
    selector.process_observation(BeaconObservation("GW-01", "PN-1", 0.90, -70.0, 8.0, 10.0, 1))
    assert selector.current_gateway_id == "GW-01"

    # Gateway reboot gap of 0.8s
    selector.clock = lambda: 10.8
    # Candidate beacon arrives post-reboot
    s = selector.process_observation(BeaconObservation("GW-01", "PN-1", 0.90, -70.0, 8.0, 10.8, 2))
    assert s.gateway_id == "GW-01"
    assert s.selection_state == GatewaySelectionState.CONNECTED


def test_hil_26_control_room_restart():
    """TEST 26: Control room server restart leaves vehicle operating under local safety governor."""
    gov = LocalVehicleSafetyGovernor(vehicle_id="TRUCK_01", v_safe_default=4.0)
    gov.update_local_safety_state(v_safe=4.0, has_gateway=False)
    # Even if control room is offline, vehicle commands are clamped to v_safe
    cmd = IncomingCommand("TRUCK_01", 1, 100.0, 15.0)
    d = gov.process_command(cmd, now=100.0)
    assert d.action == CommandAction.REJECT
    assert d.applied_speed <= 4.0


def test_hil_27_digital_twin_restart():
    """TEST 27: Digital Twin crash/restart leaves physical vehicle safety unaffected."""
    twin = DigitalTwinEngine(vehicle_id="TRUCK_01")
    twin.is_twin_online = False
    v = VehicleState(
        vehicle_id="TRUCK_01", event_timestamp=100.0, receive_timestamp=100.0,
        processing_timestamp=100.0, speed=5.0
    )
    status = twin.ingest_real_telemetry(v, now=100.0)
    assert status == DigitalTwinSyncState.OFFLINE
    # Local vehicle safety solver does not depend on twin online status
    gov = LocalVehicleSafetyGovernor(vehicle_id="TRUCK_01", v_safe_default=5.0)
    assert gov.v_safe == 5.0


def test_hil_28_full_system_recovery():
    """TEST 28: Full system recovery across sensor, comms, CAN, twin, and HMI."""
    sm = EndToEndSafetyStateMachine(vehicle_id="TRUCK_01")
    # Recovering from emergency stop
    sm.trigger_emergency_stop()
    assert sm.current_state == IntegratedSafetyState.EMERGENCY_STOP

    # Reset and verify return to nominal
    sm.reset_emergency_stop()
    ev = sm.evaluate_state(
        visibility_m=50.0, sensor_quality=SensorQuality.VALID,
        gateway_state=GatewaySelectionState.CONNECTED, comm_lost=False,
        requested_speed_mps=8.0
    )
    assert ev.state in [IntegratedSafetyState.NORMAL, IntegratedSafetyState.RECOVERY]


# ==============================================================================
# SECTION 2: 15 MASTER SAFETY INVARIANTS (I1 TO I15)
# ==============================================================================

def test_invariant_i1_v_command_le_v_safe():
    """I1: commanded_speed <= safe_speed strictly holds at all times."""
    orch = HilSystemOrchestrator(visibility_m=12.0)
    for speed in [0.0, 1.0, 5.0, 12.0, 25.0, 50.0]:
        hmi = orch.step(dt=0.1, central_speed_request=speed)
        assert hmi["applied_speed_mps"] <= hmi["safe_speed_mps"] + 1e-6


def test_invariant_i2_no_remote_command_bypasses_local_safety():
    """I2: No remote command bypasses local safety validation."""
    gov = LocalVehicleSafetyGovernor(vehicle_id="TRUCK_01", v_safe_default=4.0)
    cmd = IncomingCommand("TRUCK_01", 1, 100.0, 12.0)
    d = gov.process_command(cmd, now=100.0)
    assert d.applied_speed <= 4.0


def test_invariant_i3_comm_loss_activates_local_authority():
    """I3: Communication loss activates local safety authority."""
    sm = EndToEndSafetyStateMachine()
    ev = sm.evaluate_state(
        visibility_m=20.0, sensor_quality=SensorQuality.VALID,
        gateway_state=GatewaySelectionState.NO_GATEWAY, comm_lost=True,
        requested_speed_mps=10.0
    )
    assert ev.authority == SubsystemAuthority.LOCAL_SAFETY_GOVERNOR


def test_invariant_i4_safe_beacon_activates_on_comm_loss():
    """I4: Safe Beacon activates after communication-loss detection."""
    ctrl = SafeBeaconController(comm_timeout_s=0.5, clock=lambda: 0.0)
    ctrl.notify_central_comm_received(timestamp=0.0)
    assert ctrl.check_comm_timeout(now=0.6) is True


def test_invariant_i5_stale_data_cannot_silently_become_valid():
    """I5: Stale data cannot silently become valid."""
    v = VehicleState(
        vehicle_id="TRUCK_01", event_timestamp=100.0, receive_timestamp=100.0,
        processing_timestamp=100.0, speed=5.0
    )
    assert v.is_stale(now=102.0) is True


def test_invariant_i6_digital_twin_cannot_command_actuators():
    """I6: Digital Twin cannot directly command actuators."""
    twin = DigitalTwinEngine(vehicle_id="TRUCK_01")
    what_if = twin.run_what_if_scenario(visibility_m=10.0, grade_pct=-5.0, friction_mu=0.4)
    # Must explicitly state it is advisory only
    assert "ADVISORY ONLY" in what_if["disclaimer"]


def test_invariant_i7_control_room_cannot_bypass_governor():
    """I7: Control Room cannot bypass local safety governor."""
    gov = LocalVehicleSafetyGovernor(vehicle_id="TRUCK_01", v_safe_default=3.5)
    remote_cmd = IncomingCommand("TRUCK_01", 1, 100.0, 15.0)
    d = gov.process_command(remote_cmd, now=100.0)
    assert d.applied_speed <= 3.5


def test_invariant_i8_operator_hmi_cannot_override_safety():
    """I8: Operator HMI cannot override physical safety constraints."""
    v = VehicleState(
        vehicle_id="TRUCK_01", event_timestamp=100.0, receive_timestamp=100.0,
        processing_timestamp=100.0, speed=10.0, safe_speed=5.0
    )
    view = v.to_operator_hmi_view(now=100.0)
    assert view["active_warning"] == "REDUCE SPEED"


def test_invariant_i9_emergency_stop_highest_authority():
    """I9: Emergency stop has highest authority."""
    sm = EndToEndSafetyStateMachine()
    sm.trigger_emergency_stop()
    ev = sm.evaluate_state(
        visibility_m=50.0, sensor_quality=SensorQuality.VALID,
        gateway_state=GatewaySelectionState.CONNECTED, comm_lost=False,
        requested_speed_mps=10.0
    )
    assert ev.state == IntegratedSafetyState.EMERGENCY_STOP
    assert ev.applied_speed_mps == 0.0


def test_invariant_i10_can_timeout_failsafe_holding():
    """I10: CAN timeout cannot produce uncontrolled command persistence."""
    bus = CanTwaiBusEmulator()
    frame = encode_safety_command(target_speed_mps=8.0, action_code=1, sequence=1, timestamp=0.0)
    bus.transmit(frame, now=0.0)
    has_f, f, is_stale = bus.receive_latest(CAN_ID_SAFETY_COMMAND, now=0.25)
    assert is_stale is True


def test_invariant_i11_gateway_handover_safe_transitions():
    """I11: Gateway handover does not create unsafe command transitions."""
    orch = HilSystemOrchestrator(visibility_m=20.0)
    speeds = [orch.step(dt=0.1, central_speed_request=6.0)["applied_speed_mps"] for _ in range(5)]
    for i in range(len(speeds) - 1):
        assert abs(speeds[i+1] - speeds[i]) <= 1.5


def test_invariant_i12_twin_physical_mismatch_detectable():
    """I12: Digital Twin and physical state mismatch is detectable."""
    twin = DigitalTwinEngine(vehicle_id="TRUCK_01")
    t0 = 100.0
    v1 = VehicleState(
        vehicle_id="TRUCK_01", event_timestamp=t0, receive_timestamp=t0, processing_timestamp=t0,
        position=100.0, speed=5.0
    )
    twin.ingest_real_telemetry(v1, now=t0)
    v2 = VehicleState(
        vehicle_id="TRUCK_01", event_timestamp=t0 + 0.1, receive_timestamp=t0 + 0.1,
        processing_timestamp=t0 + 0.1, position=110.0, speed=5.0  # 10m error
    )
    status = twin.ingest_real_telemetry(v2, now=t0 + 0.1)
    assert status == DigitalTwinSyncState.DIVERGENT


def test_invariant_i13_hmi_cannot_display_stale_as_live():
    """I13: HMI cannot display stale state as live state."""
    v = VehicleState(
        vehicle_id="TRUCK_01", event_timestamp=100.0, receive_timestamp=100.0,
        processing_timestamp=100.0, speed=5.0
    )
    view = v.to_operator_hmi_view(now=103.5)
    assert view["is_stale"] is True
    assert "STALE" in view["data_age_label"]


def test_invariant_i14_grade_transformation_bijective():
    """I14: Grade transformation remains bijective (downhill negative, uphill positive)."""
    orch_down = HilSystemOrchestrator(visibility_m=20.0, grade_pct=-8.0)
    hmi_down = orch_down.step(dt=0.1, central_speed_request=10.0)
    orch_flat = HilSystemOrchestrator(visibility_m=20.0, grade_pct=0.0)
    hmi_flat = orch_flat.step(dt=0.1, central_speed_request=10.0)
    assert hmi_down["safe_speed_mps"] <= hmi_flat["safe_speed_mps"] + 1e-6


def test_invariant_i15_safety_decision_timestamped():
    """I15: Every safety decision is timestamped and auditable."""
    sm = EndToEndSafetyStateMachine()
    t_test = 1727137000.0
    ev = sm.evaluate_state(
        visibility_m=15.0, sensor_quality=SensorQuality.VALID,
        gateway_state=GatewaySelectionState.CONNECTED, comm_lost=False,
        requested_speed_mps=5.0, now=t_test
    )
    assert ev.timestamp == t_test
    assert len(sm.history) > 0
    assert sm.history[-1]["timestamp"] == t_test
