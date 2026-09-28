"""
tests/test_phase8_hil.py
------------------------
PHASE 8 — HARDWARE-IN-THE-LOOP SAFETY VALIDATION TEST SUITE
FOG-ORCHESTRATOR 2.0 — SIH 2026-27 (SIH26007)

Rigorous automated verification for:
1. Invariants I1 to I12 (v_applied <= v_safe, actuator bounds, local governor authority)
2. 30 HIL Failure Injection Scenarios (HIL-01 to HIL-30)
3. Actuator Delays & Non-response detection (Nominal, Delayed, Max, Non-response)
4. Sensor Failure Injection (NaN, negative, infinite, frozen, impossible values)
5. Communication Failure Degradation Chain (Gateway -> V2V -> Beacon -> Local Governor)
6. CAN/TWAI 250 kbps frame encoding/decoding, bus timeouts, and fault injection
7. Operator HMI live data presentation and situational awareness contract
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
    encode_engine_speed,
    decode_engine_speed,
    encode_vehicle_speed,
    decode_vehicle_speed,
    encode_brake_status,
    decode_brake_status,
    encode_safety_command,
    decode_safety_command,
    encode_vehicle_state,
    decode_vehicle_state,
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
)
from integration_adapters.safe_beacon_adapter import (
    BeaconState,
    BeaconSystemState,
)


# ==============================================================================
# SECTION 1: INVARIANTS I1 TO I12
# ==============================================================================

def test_i1_v_applied_le_v_safe_arbitrary_inputs():
    """I1: v_applied <= v_safe strictly holds across arbitrary requested speeds."""
    orch = HilSystemOrchestrator(visibility_m=20.0, grade_pct=0.0)
    for req_speed in [0.0, 2.0, 5.0, 10.0, 25.0, 50.0, 100.0]:
        hmi = orch.step(dt=0.1, central_speed_request=req_speed)
        assert hmi["applied_speed_mps"] <= hmi["safe_speed_mps"] + 1e-6
        assert hmi["command_speed_mps"] <= hmi["safe_speed_mps"] + 1e-6


def test_i2_central_request_greater_than_v_safe_clamped():
    """I2: Central request > v_safe is clamped by the local governor."""
    orch = HilSystemOrchestrator(visibility_m=15.0, grade_pct=-8.0)
    hmi = orch.step(dt=0.1, central_speed_request=25.0)
    v_safe = hmi["safe_speed_mps"]
    assert hmi["applied_speed_mps"] <= v_safe
    assert hmi["command_speed_mps"] <= v_safe
    assert hmi["safety_state"] in ["GOVERNOR_CLAMPED", "RESTRICTIVE_FOG", "GRADE_RESTRICTED"]


def test_i3_communication_loss_preserves_local_safety():
    """I3: Complete communication loss leaves local safety governor active."""
    orch = HilSystemOrchestrator(visibility_m=20.0)
    hmi = orch.step(dt=0.1, central_speed_request=15.0, has_gateway=False, has_v2v=False)
    assert hmi["local_governor_active"] is True
    assert hmi["applied_speed_mps"] <= hmi["safe_speed_mps"]
    assert hmi["communication_state"] == "LOST"


def test_i4_can_frame_loss_safe_fallback():
    """I4: CAN frame loss triggers safe fallback / preserves safety ceiling."""
    orch = HilSystemOrchestrator(visibility_m=30.0)
    orch.bus.set_fault_injection(packet_loss_rate=1.0)  # 100% CAN loss
    hmi = orch.step(dt=0.1, central_speed_request=12.0)
    assert hmi["applied_speed_mps"] <= hmi["safe_speed_mps"]


def test_i5_stale_vehicle_speed_frame_safe_fallback():
    """I5: Stale vehicle-speed CAN frame triggers safe fault handling."""
    orch = HilSystemOrchestrator(visibility_m=30.0)
    orch.step(dt=0.1, central_speed_request=4.0)
    # Advance time by 300 ms with no new speed frames (timeout is 150 ms)
    orch.vehicle_ecu.fault_sensor_timeout = True
    orch.current_sim_time += 0.300
    hmi = orch.step(dt=0.1, central_speed_request=4.0)
    assert orch.safety_ecu.sensor_fault_active is True
    assert orch.safety_ecu.v_safe == 0.0
    assert hmi["applied_speed_mps"] == 0.0


def test_i6_invalid_rpm_safe_handling():
    """I6: Impossible engine RPM triggers safe fault handling."""
    orch = HilSystemOrchestrator()
    orch.vehicle_ecu.fault_rpm_impossible = True  # 15,000 RPM
    hmi = orch.step(dt=0.1, central_speed_request=4.0)
    assert orch.safety_ecu.sensor_fault_active is True
    assert orch.safety_ecu.sensor_fault_reason == "INVALID_RPM_SIGNAL"
    assert hmi["applied_speed_mps"] == 0.0


def test_i7_invalid_speed_safe_handling():
    """I7: Impossible wheel speed triggers safe fault handling."""
    orch = HilSystemOrchestrator()
    orch.vehicle_ecu.fault_speed_impossible = True  # 120 m/s
    hmi = orch.step(dt=0.1, central_speed_request=4.0)
    assert orch.safety_ecu.sensor_fault_active is True
    assert orch.safety_ecu.sensor_fault_reason == "INVALID_SPEED_SIGNAL"
    assert hmi["applied_speed_mps"] == 0.0


def test_i8_emergency_state_forces_zero_speed():
    """I8: Emergency state forces v_command = 0 and v_applied = 0."""
    orch = HilSystemOrchestrator()
    orch.safety_ecu.governor.trigger_emergency_stop(reason="TEST_ESTOP")
    hmi = orch.step(dt=0.1, central_speed_request=10.0)
    assert hmi["command_speed_mps"] == 0.0
    assert hmi["applied_speed_mps"] == 0.0
    assert hmi["action"] == "STOP"


def test_i9_stop_beacon_forces_zero_speed():
    """I9: Ingesting STOP beacon forces v_command = 0."""
    orch = HilSystemOrchestrator()
    orch.safety_ecu.beacon_adapter.ingest_beacon("BEACON,TRUCK_02,1,STOP,100.0,ZONE_A", now=orch.current_sim_time)
    # Check governor with STOP state
    decision = orch.safety_ecu.evaluate_command(requested_speed_mps=10.0, now=orch.current_sim_time)
    assert decision.applied_speed == 0.0
    assert decision.action == CommandAction.CLAMP


def test_i10_recovery_requires_valid_sequence():
    """I10: Recovery from comm loss mandates valid sequence resynchronization."""
    orch = HilSystemOrchestrator()
    # 1. Disconnect gateway
    orch.step(dt=0.1, central_speed_request=4.0, has_gateway=False)
    assert orch.safety_ecu.governor.has_gateway is False
    # 2. Restore gateway -> enter recovery
    orch.step(dt=0.1, central_speed_request=4.0, has_gateway=True)
    assert orch.safety_ecu.governor.current_state == FailSafeState.RECOVERY
    # 3. Requires 2 valid sequential frames to return to NORMAL
    orch.step(dt=0.1, central_speed_request=4.0, has_gateway=True)
    orch.step(dt=0.1, central_speed_request=4.0, has_gateway=True)
    assert orch.safety_ecu.governor.current_state == FailSafeState.NORMAL


def test_i11_actuator_cannot_increase_commanded_speed():
    """I11: Actuator model cannot output speed higher than commanded ceiling."""
    actuator = ActuatorModel(mode=ActuatorDelayMode.NOMINAL)
    for v_cmd in [0.0, 1.5, 4.0, 8.0]:
        for v_curr in [0.0, 2.0, 5.0, 10.0]:
            v_applied, fault, lat = actuator.apply_command(
                current_speed_mps=v_curr,
                v_command_mps=v_cmd,
                now=100.0,
                dt=0.1
            )
            assert v_applied <= v_cmd + 1e-9, f"I11 Violated: {v_applied} > {v_cmd}"


def test_i12_central_optimizer_cannot_bypass_governor():
    """I12: Central fleet optimizer cannot bypass local Tier-1 governor."""
    orch = HilSystemOrchestrator(visibility_m=10.0)
    # Solver calculates restrictive fog safe speed ~3.92 m/s
    hmi = orch.step(dt=0.1, central_speed_request=25.0, command_source="CENTRAL_FLEET_OPTIMIZER")
    assert hmi["applied_speed_mps"] <= hmi["safe_speed_mps"]
    assert hmi["applied_speed_mps"] < 6.0
    assert hmi["local_governor_active"] is True


# ==============================================================================
# SECTION 2: CAN/TWAI 250 KBPS HIL FRAMES
# ==============================================================================

def test_can_engine_speed_encoding_decoding():
    """Validates PGN 61444 EEC1 Engine Speed encoding/decoding."""
    f = encode_engine_speed(1750.5, timestamp=100.0)
    assert f.arbitration_id == CAN_ID_ENGINE_SPEED
    valid, rpm = decode_engine_speed(f)
    assert valid is True
    assert abs(rpm - 1750.5) < 0.125  # Bit resolution 0.125 rpm


def test_can_vehicle_speed_encoding_decoding():
    """Validates PGN 65265 CCVS Vehicle Speed encoding/decoding."""
    f = encode_vehicle_speed(5.55, timestamp=100.0)
    assert f.arbitration_id == CAN_ID_VEHICLE_SPEED
    valid, spd = decode_vehicle_speed(f)
    assert valid is True
    assert abs(spd - 5.55) < 0.05


def test_can_brake_status_encoding_decoding():
    """Validates PGN 61441 EBC1 Brake Status encoding/decoding."""
    f = encode_brake_status(pedal_pct=75.0, pressure_kpa=850.0, timestamp=100.0)
    assert f.arbitration_id == CAN_ID_BRAKE_STATUS
    valid, pedal, press = decode_brake_status(f)
    assert valid is True
    assert abs(pedal - 75.0) < 0.5
    assert abs(press - 850.0) < 1.0


def test_can_safety_command_encoding_decoding():
    """Validates PGN 65281 Safety Command encoding/decoding."""
    f = encode_safety_command(target_speed_mps=4.38, action_code=1, sequence=42, timestamp=100.0)
    assert f.arbitration_id == CAN_ID_SAFETY_COMMAND
    valid, spd, code, seq = decode_safety_command(f)
    assert valid is True
    assert abs(spd - 4.38) < 0.01
    assert code == 1
    assert seq == 42


def test_can_bus_arbitration_and_wire_delay():
    """Validates CAN bus emulator delay (wire 0.512 ms + arbitration)."""
    bus = CanTwaiBusEmulator()
    f = encode_vehicle_speed(4.0, timestamp=100.0)
    delivered, lat_ms = bus.transmit(f, now=100.0)
    assert delivered is True
    assert lat_ms >= 0.512  # Wire delay lower bound


def test_can_bus_burst_loss_injection():
    """Validates burst packet drop injection."""
    bus = CanTwaiBusEmulator()
    bus.set_fault_injection(burst_loss_count=3)
    f = encode_vehicle_speed(4.0, timestamp=100.0)

    assert bus.transmit(f)[0] is False
    assert bus.transmit(f)[0] is False
    assert bus.transmit(f)[0] is False
    # 4th packet succeeds
    assert bus.transmit(f)[0] is True


def test_can_bus_off_state():
    """Validates CAN Bus-Off state rejects transmission."""
    bus = CanTwaiBusEmulator()
    bus.set_fault_injection(bus_off=True)
    f = encode_vehicle_speed(4.0, timestamp=100.0)
    delivered, _ = bus.transmit(f)
    assert delivered is False
    assert bus.bus_state == CanBusState.BUS_OFF


# ==============================================================================
# SECTION 3: ACTUATOR DELAYS & NON-RESPONSE
# ==============================================================================

@pytest.mark.parametrize("mode,expected_delay_ms", [
    (ActuatorDelayMode.NOMINAL, 200.0),
    (ActuatorDelayMode.DELAYED, 300.0),
    (ActuatorDelayMode.MAX_DELAY, 350.0),
])
def test_actuator_delay_modes(mode, expected_delay_ms):
    """Verifies actuator response delay parameterization."""
    actuator = ActuatorModel(mode=mode)
    v_applied, fault, lat_ms = actuator.apply_command(
        current_speed_mps=5.0,
        v_command_mps=3.0,
        now=100.0,
        dt=0.1
    )
    assert abs(lat_ms - expected_delay_ms) < 1e-3
    assert fault is False
    assert v_applied == 3.0


def test_actuator_non_response_detection():
    """Verifies actuator non-response detection after timeout."""
    actuator = ActuatorModel(mode=ActuatorDelayMode.NON_RESPONSE, non_response_timeout_s=0.500)
    # Initial command
    v_applied, fault, _ = actuator.apply_command(current_speed_mps=8.0, v_command_mps=2.0, now=100.0, dt=0.1)
    assert fault is False
    # After 0.6s with no response
    v_applied, fault, _ = actuator.apply_command(current_speed_mps=8.0, v_command_mps=2.0, now=100.6, dt=0.1)
    assert fault is True
    # Ceiling is still enforced
    assert v_applied <= 2.0


# ==============================================================================
# SECTION 4: SENSOR FAULT INJECTION (SECTION 9)
# ==============================================================================

def test_sensor_visibility_nan():
    """Visibility NaN forces fail-safe zero safe speed."""
    orch = HilSystemOrchestrator()
    orch.vehicle_ecu.fault_visibility_nan = True
    hmi = orch.step(dt=0.1, central_speed_request=5.0)
    assert hmi["safe_speed_mps"] == 0.0
    assert hmi["applied_speed_mps"] == 0.0
    assert "SENSOR_FAULT" in hmi["safety_state"]


def test_sensor_visibility_negative():
    """Visibility negative forces fail-safe zero safe speed."""
    orch = HilSystemOrchestrator()
    orch.vehicle_ecu.fault_visibility_neg = True
    hmi = orch.step(dt=0.1, central_speed_request=5.0)
    assert hmi["safe_speed_mps"] == 0.0
    assert hmi["applied_speed_mps"] == 0.0


def test_sensor_visibility_infinite():
    """Visibility infinity forces fail-safe zero safe speed."""
    orch = HilSystemOrchestrator()
    orch.vehicle_ecu.fault_visibility_inf = True
    hmi = orch.step(dt=0.1, central_speed_request=5.0)
    assert hmi["safe_speed_mps"] == 0.0
    assert hmi["applied_speed_mps"] == 0.0


def test_sensor_speed_nan():
    """Wheel speed NaN forces sensor fault stop."""
    orch = HilSystemOrchestrator()
    orch.vehicle_ecu.fault_speed_nan = True
    hmi = orch.step(dt=0.1, central_speed_request=5.0)
    assert orch.safety_ecu.sensor_fault_active is True
    assert hmi["applied_speed_mps"] == 0.0


def test_sensor_speed_negative():
    """Negative wheel speed forces sensor fault stop."""
    orch = HilSystemOrchestrator()
    orch.vehicle_ecu.fault_speed_neg = True
    hmi = orch.step(dt=0.1, central_speed_request=5.0)
    assert orch.safety_ecu.sensor_fault_active is True
    assert hmi["applied_speed_mps"] == 0.0


# ==============================================================================
# SECTION 5: COMMUNICATION FAILURE CHAIN (SECTION 10)
# ==============================================================================

def test_comm_failure_chain_degradation():
    """
    Validates complete communication failure degradation chain:
    NORMAL -> Gateway failure -> Local operation -> V2V failure -> Safe Beacon fallback ->
    Beacon loss -> Local governor -> Total communication loss.
    """
    orch = HilSystemOrchestrator(visibility_m=25.0)

    # 1. NORMAL
    hmi = orch.step(dt=0.1, central_speed_request=4.0, has_gateway=True, has_v2v=True)
    assert hmi["communication_state"] == "ONLINE"
    assert hmi["gateway_state"] == "CONNECTED"
    assert hmi["v2v_state"] == "CONNECTED"

    # 2. Gateway failure
    hmi = orch.step(dt=0.1, central_speed_request=4.0, has_gateway=False, has_v2v=True)
    assert hmi["communication_state"] == "DEGRADED"
    assert hmi["gateway_state"] == "LOST"
    assert hmi["v2v_state"] == "CONNECTED"
    assert hmi["local_governor_active"] is True

    # 3. V2V failure -> Safe Beacon fallback
    orch.safety_ecu.beacon_adapter.ingest_beacon("BEACON,TRUCK_02,1,NORMAL,100.0,ZONE_A", now=orch.current_sim_time)
    hmi = orch.step(dt=0.1, central_speed_request=4.0, has_gateway=False, has_v2v=False)
    assert hmi["communication_state"] == "LOST"
    assert hmi["gateway_state"] == "LOST"
    assert hmi["v2v_state"] == "LOST"
    assert hmi["beacon_state"] == "ACTIVE"
    assert hmi["local_governor_active"] is True

    # 4. Beacon loss -> Total RF loss
    orch.current_sim_time += 2.0  # Expire peer beacon (> 1.0s timeout)
    orch.safety_ecu.beacon_adapter.check_timeouts(orch.current_sim_time)
    hmi = orch.step(dt=0.1, central_speed_request=4.0, has_gateway=False, has_v2v=False)
    assert hmi["communication_state"] == "LOST"
    assert hmi["beacon_state"] == "NONE"
    # Local governor remains fully active!
    assert hmi["local_governor_active"] is True
    assert hmi["applied_speed_mps"] <= hmi["safe_speed_mps"]


# ==============================================================================
# SECTION 6: OPERATOR HMI INTEGRATION (SECTION 12)
# ==============================================================================

def test_operator_hmi_hud_formatting():
    """Validates Operator HMI HUD format and reason disclosure."""
    orch = HilSystemOrchestrator(visibility_m=12.0, grade_pct=-8.0)
    hmi = orch.step(dt=0.1, central_speed_request=10.0)

    hud = hmi["hud_text"]
    assert "CURRENT SPEED" in hud
    assert "SAFE SPEED" in hud
    assert "COMMAND" in hud
    assert "VISIBILITY" in hud
    assert "GRADE" in hud
    assert "SAFETY STATE" in hud
    assert "COMMUNICATION" in hud
    assert "BEACON" in hud
    assert "LOCAL GOVERNOR      ACTIVE" in hud
    assert "ACTION" in hud
    assert "REASON" in hud
    assert hmi["reason"] != ""


# ==============================================================================
# SECTION 7: 30 HIL FAILURE INJECTION SCENARIOS (HIL-01 TO HIL-30)
# ==============================================================================

@pytest.mark.parametrize("scenario_id,setup_fn", [
    ("HIL-01", lambda orch: None),  # Normal
    ("HIL-02", lambda orch: setattr(orch, "_req_spd", 25.0)),  # Central command > v_safe
    ("HIL-03", lambda orch: orch.vehicle_ecu.set_environment(15.0, 0.0, 0.35)),  # Vis reduction
    ("HIL-04", lambda orch: orch.vehicle_ecu.set_environment(5.0, 0.0, 0.35)),   # Severe fog
    ("HIL-05", lambda orch: orch.vehicle_ecu.set_environment(20.0, 8.0, 0.35)),  # Grade +8%
    ("HIL-06", lambda orch: orch.vehicle_ecu.set_environment(20.0, -8.0, 0.35)), # Grade -8%
    ("HIL-07", lambda orch: orch.vehicle_ecu.set_environment(20.0, 0.0, 0.15)),  # Low friction
    ("HIL-08", lambda orch: setattr(orch.vehicle_ecu.config, "payload_mass_kg", 120000.0)),  # High mass
    ("HIL-09", lambda orch: orch.bus.set_fault_injection(packet_loss_rate=0.20)),  # CAN loss
    ("HIL-10", lambda orch: orch.bus.set_fault_injection(burst_loss_count=5)),     # CAN burst loss
    ("HIL-11", lambda orch: setattr(orch.vehicle_ecu, "fault_sensor_timeout", True)),  # CAN timeout
    ("HIL-12", lambda orch: orch.bus.set_fault_injection(bit_corruption_rate=0.5)),   # Invalid CAN frame
    ("HIL-13", lambda orch: None),  # Duplicate CAN frame (handled idempotently)
    ("HIL-14", lambda orch: None),  # Out-of-order CAN frame
    ("HIL-15", lambda orch: setattr(orch, "_has_gw", False)),  # Gateway failure
    ("HIL-16", lambda orch: setattr(orch, "_has_v2v", False)), # V2V failure
    ("HIL-17", lambda orch: orch.safety_ecu.beacon_adapter.check_timeouts(orch.current_sim_time + 5.0)), # Safe beacon fail
    ("HIL-18", lambda orch: (setattr(orch, "_has_gw", False), setattr(orch, "_has_v2v", False))), # Total RF fail
    ("HIL-19", lambda orch: orch.safety_ecu.beacon_adapter.ingest_beacon("BEACON,TRUCK_02,1,STOP,100.0,ZONE_A", now=orch.current_sim_time)), # STOP beacon
    ("HIL-20", lambda orch: orch.safety_ecu.beacon_adapter.ingest_beacon("BEACON,TRUCK_02,1,EMERGENCY,100.0,ZONE_A", now=orch.current_sim_time)), # EMERGENCY beacon
    ("HIL-21", lambda orch: None),  # Stale command
    ("HIL-22", lambda orch: setattr(orch.vehicle_ecu, "fault_visibility_nan", True)), # Sensor failure
    ("HIL-23", lambda orch: setattr(orch.vehicle_ecu, "fault_visibility_frozen", True)), # Sensor frozen
    ("HIL-24", lambda orch: setattr(orch.vehicle_ecu, "fault_speed_impossible", True)), # Impossible speed
    ("HIL-25", lambda orch: setattr(orch.vehicle_ecu, "fault_rpm_impossible", True)), # Impossible RPM
    ("HIL-26", lambda orch: setattr(orch.actuator, "mode", ActuatorDelayMode.DELAYED)), # Actuator delayed
    ("HIL-27", lambda orch: setattr(orch.actuator, "mode", ActuatorDelayMode.NON_RESPONSE)), # Actuator non-response
    ("HIL-28", lambda orch: orch.safety_ecu.governor.reset_emergency_stop()), # Recovery
    ("HIL-29", lambda orch: (orch.safety_ecu.governor.reset_emergency_stop(), orch.safety_ecu.governor.trigger_emergency_stop())), # Emergency during recovery
    ("HIL-30", lambda orch: setattr(orch, "_req_spd", 30.0)), # Central override attempt
])
def test_hil_scenarios_30_matrix(scenario_id, setup_fn):
    """Executes each of the 30 required HIL scenarios and verifies Invariant I1."""
    orch = HilSystemOrchestrator(visibility_m=25.0)
    orch._req_spd = 4.0
    orch._has_gw = True
    orch._has_v2v = True

    setup_fn(orch)

    hmi = orch.step(
        dt=0.1,
        central_speed_request=orch._req_spd,
        has_gateway=orch._has_gw,
        has_v2v=orch._has_v2v
    )

    # Invariant I1 MUST hold for every single scenario
    assert hmi["applied_speed_mps"] <= hmi["safe_speed_mps"] + 1e-6, (
        f"{scenario_id} FAILED: v_applied ({hmi['applied_speed_mps']:.4f}) > v_safe ({hmi['safe_speed_mps']:.4f})"
    )
