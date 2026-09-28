"""
tests/test_stage2_hard_invariants.py
------------------------------------
STAGE 2: Automated Hard Safety Invariants Verification Suite.

Validates the 10 Non-Negotiable Safety Invariants defined in Section 21:
1.  v_command <= v_safe
2.  stale command != accepted
3.  invalid command != accepted
4.  out-of-order telemetry != state rollback
5.  duplicate telemetry != state rollback
6.  central optimizer cannot bypass local safety governor
7.  prediction cannot directly control actuator
8.  communication loss -> safe fallback
9.  sensor failure -> defined safe state
10. grade conversion is physically consistent
"""

import time
import math
import pytest
import numpy as np

from command_gateway import CommandGateway, VehicleCommand, CommandSource, CommandStatus
from contracts import DispatchCommandMessage
from hardware_emulator import VehicleHardwareEmulator
from twin.twin_state_store import TwinStateStore, TwinMode, Sourced, Source, Quality, ClockDomain
from telemetry_ingest import TelemetryIngestor, REJECT_OUT_OF_ORDER, REJECT_DUPLICATE
from fog_safe.vehicle import MiningVehicle
from fog_safe.road import RoadSegment
from fog_safe.environment import EnvironmentState
from fog_safe.communication import CommunicationModel
from fog_safe.safety import solve_safe_speed
from integration_adapters.grade_adapter import GradeAdapter, GradeConventionError


# ==============================================================================
# Invariant 1: v_command <= v_safe
# ==============================================================================
def test_invariant_1_command_clamped_to_v_safe():
    """Ensure that any command exceeding local v_safe is clamped strictly <= v_safe."""
    emulator = VehicleHardwareEmulator("TRUCK_01")
    emulator.update_environment(visibility_m=20.0, friction_mu=0.30, grade_pct=0.0)
    safety = emulator.compute_local_safety_state()
    v_safe = safety.v_safe

    # Attempt to command an overspeed of 25.0 m/s
    cmd = DispatchCommandMessage(
        command_id="CMD_INV_1",
        vehicle_id="TRUCK_01",
        timestamp=time.time(),
        target_speed=25.0,
        action="TARGET_SPEED",
        reason_code="MAX_PRODUCTIVITY"
    )
    ack = emulator.process_dispatch_command(cmd)

    assert ack.status == "CLAMPED"
    assert ack.applied_speed <= v_safe + 1e-4
    assert emulator.speed_mps <= v_safe + 1e-4


# ==============================================================================
# Invariant 2: stale command != accepted
# ==============================================================================
def test_invariant_2_stale_command_rejected():
    """Ensure that a command older than the allowed tolerance is rejected."""
    store = TwinStateStore(mode=TwinMode.SIMULATION)
    store.register_vehicle("TRUCK_01")
    gateway = CommandGateway(store=store, validity_window_s=2.0)

    # Command created 10 seconds in the past
    stale_cmd = VehicleCommand(
        command_id="CMD_INV_2_STALE",
        vehicle_id="TRUCK_01",
        created_at=time.time() - 10.0,
        action="TARGET_SPEED",
        target_speed_mps=5.0,
        source=CommandSource.OPERATOR,
        reason="LATE_DISPATCH"
    )
    res = gateway.submit(stale_cmd)
    assert res.status == CommandStatus.STALE
    assert not res.accepted


# ==============================================================================
# Invariant 3: invalid command != accepted
# ==============================================================================
def test_invariant_3_invalid_command_rejected():
    """Ensure commands with negative speed, NaN, or unknown vehicles are rejected."""
    store = TwinStateStore(mode=TwinMode.SIMULATION)
    store.register_vehicle("TRUCK_01")
    gateway = CommandGateway(store=store)

    # 1. Negative speed
    cmd_neg = VehicleCommand(
        command_id="CMD_INV_3_NEG",
        vehicle_id="TRUCK_01",
        created_at=time.time(),
        target_speed_mps=-5.0,
        source=CommandSource.DISPATCH,
        reason="INVALID_NEG"
    )
    res_neg = gateway.submit(cmd_neg)
    assert res_neg.status == CommandStatus.INVALID

    # 2. NaN speed
    cmd_nan = VehicleCommand(
        command_id="CMD_INV_3_NAN",
        vehicle_id="TRUCK_01",
        created_at=time.time(),
        target_speed_mps=float('nan'),
        source=CommandSource.DISPATCH,
        reason="INVALID_NAN"
    )
    res_nan = gateway.submit(cmd_nan)
    assert res_nan.status == CommandStatus.INVALID

    # 3. Unknown vehicle
    cmd_unknown = VehicleCommand(
        command_id="CMD_INV_3_UNKWN",
        vehicle_id="TRUCK_UNKNOWN_99",
        created_at=time.time(),
        target_speed_mps=5.0,
        source=CommandSource.DISPATCH,
        reason="UNKNOWN_VEHICLE"
    )
    res_unknown = gateway.submit(cmd_unknown)
    assert res_unknown.status == CommandStatus.UNKNOWN_VEHICLE


# ==============================================================================
# Invariant 4: out-of-order telemetry != state rollback
# ==============================================================================
def test_invariant_4_out_of_order_telemetry_no_rollback():
    """Older telemetry packets must not roll back current vehicle state timestamp or values."""
    store = TwinStateStore(mode=TwinMode.SIMULATION)
    store.register_vehicle("TRUCK_01")
    ingestor = TelemetryIngestor(store=store)

    # Ingest seq = 100 with rpm = 500.0
    packet_100 = "STATE,TRUCK_01,100,500.0,2.5,0,0,16384,0,0,0"
    res_100 = ingestor.ingest_v2v_packet(packet_100)
    assert res_100.accepted

    v_state = store.get_vehicle("TRUCK_01")
    assert v_state.get("rpm").value == 500.0

    # Ingest out-of-order packet with seq = 95 and rpm = 200.0
    packet_95 = "STATE,TRUCK_01,95,200.0,1.0,0,0,16384,0,0,0"
    res_95 = ingestor.ingest_v2v_packet(packet_95)
    assert not res_95.accepted
    assert res_95.reason == REJECT_OUT_OF_ORDER

    # Authoritative twin state MUST remain at seq 100 (rpm=500.0), no rollback!
    v_state_after = store.get_vehicle("TRUCK_01")
    assert v_state_after.get("rpm").value == 500.0


# ==============================================================================
# Invariant 5: duplicate telemetry != state rollback
# ==============================================================================
def test_invariant_5_duplicate_telemetry_no_rollback():
    """Duplicate telemetry packet must not mutate or corrupt the existing valid state."""
    store = TwinStateStore(mode=TwinMode.SIMULATION)
    store.register_vehicle("TRUCK_01")
    ingestor = TelemetryIngestor(store=store)

    packet_100 = "STATE,TRUCK_01,100,500.0,2.5,0,0,16384,0,0,0"
    res_1 = ingestor.ingest_v2v_packet(packet_100)
    assert res_1.accepted

    # Re-apply duplicate packet with seq = 100
    res_dup = ingestor.ingest_v2v_packet(packet_100)
    assert not res_dup.accepted
    assert res_dup.reason == REJECT_DUPLICATE

    v_state = store.get_vehicle("TRUCK_01")
    assert v_state.get("rpm").value == 500.0


# ==============================================================================
# Invariant 6: central optimizer cannot bypass local safety governor
# ==============================================================================
def test_invariant_6_central_cannot_bypass_local_safety():
    """Even if central command is marked PRIORITY / OVERRIDE, local governor clamps it."""
    emulator = VehicleHardwareEmulator("TRUCK_02")
    # Low visibility -> low v_safe (~3-4 m/s)
    emulator.update_environment(visibility_m=12.0, friction_mu=0.25, grade_pct=0.0)
    safety = emulator.compute_local_safety_state()
    v_safe = safety.v_safe

    cmd_override = DispatchCommandMessage(
        command_id="CMD_CENTRAL_OVERRIDE_CRITICAL",
        vehicle_id="TRUCK_02",
        timestamp=time.time(),
        target_speed=15.0,
        action="OVERRIDE_SPEED",
        reason_code="EMERGENCY_DISPATCH_PRIORITY"
    )
    ack = emulator.process_dispatch_command(cmd_override)
    assert ack.status == "CLAMPED"
    assert ack.applied_speed <= v_safe + 1e-4
    assert emulator.speed_mps <= v_safe + 1e-4


# ==============================================================================
# Invariant 7: prediction cannot directly control actuator
# ==============================================================================
def test_invariant_7_prediction_cannot_directly_actuate():
    """
    Predictions from what-if or queue models are advisory data structures.
    They have NO actuator interface and must pass through CommandGateway.
    When the twin has no valid safe speed or the command exceeds safety,
    the gateway refuses or fails closed.
    """
    store = TwinStateStore(mode=TwinMode.SIMULATION)
    store.register_vehicle("TRUCK_01")
    gateway = CommandGateway(store=store)

    predicted_speed = 18.0  # Predicted hypothetical speed
    cmd = VehicleCommand(
        command_id="CMD_PRED_01",
        vehicle_id="TRUCK_01",
        created_at=time.time(),
        target_speed_mps=predicted_speed,
        source=CommandSource.DISPATCH,
        reason="WHAT_IF_SCENARIO_OUTPUT"
    )
    # The twin store doesn't have an authoritative v_safe registered yet, so it fails closed
    res = gateway.submit(cmd)
    assert not res.accepted
    assert res.status == CommandStatus.REJECTED


# ==============================================================================
# Invariant 8: communication loss -> safe fallback
# ==============================================================================
def test_invariant_8_communication_loss_safe_fallback():
    """When communication drops or telemetry becomes stale, vehicle transitions to safe fallback."""
    emulator = VehicleHardwareEmulator("TRUCK_01")
    emulator.speed_mps = 12.0
    emulator.comm_state = "LOST"  # Comm dropped

    safety = emulator.compute_local_safety_state()
    assert safety.active_constraint == "COMMUNICATION_DEGRADED_FALLBACK"
    assert safety.v_safe <= 2.78  # Max 10 km/h fallback
    assert safety.actual_speed <= 2.78


# ==============================================================================
# Invariant 9: sensor failure -> defined safe state
# ==============================================================================
def test_invariant_9_sensor_failure_defined_safe_state():
    """Unusable friction (NaN, negative, zero) results in FAIL-CLOSED v_safe = 0.0."""
    vehicle = MiningVehicle(is_loaded=True)
    road = RoadSegment.from_civil_grade(civil_grade_pct=0.0)
    env = EnvironmentState(r_effective=50.0)
    comm = CommunicationModel()

    # 1. NaN friction
    res_nan = solve_safe_speed(vehicle, road, env, comm, mu_effective=float('nan'))
    assert res_nan.v_safe_ms == 0.0
    assert res_nan.primary_constraint == "INVALID_FRICTION"
    assert not res_nan.is_safe

    # 2. Negative friction
    res_neg = solve_safe_speed(vehicle, road, env, comm, mu_effective=-0.1)
    assert res_neg.v_safe_ms == 0.0
    assert res_neg.primary_constraint == "INVALID_FRICTION"

    # 3. Zero friction
    res_zero = solve_safe_speed(vehicle, road, env, comm, mu_effective=0.0)
    assert res_zero.v_safe_ms == 0.0
    assert res_zero.primary_constraint == "INVALID_FRICTION"


# ==============================================================================
# Invariant 10: grade conversion is physically consistent
# ==============================================================================
def test_invariant_10_grade_conversion_physically_consistent():
    """
    Civil grade mapping:
    -8% civil (downhill) -> longer stopping distance, lower deceleration, lower safe speed.
    0% civil (flat)      -> baseline.
    +8% civil (uphill)   -> shorter stopping distance, higher deceleration, higher/equal safe speed.
    """
    assert GradeAdapter.civil_to_physics_grade(-8.0) == 8.0   # Downhill forward gravity
    assert GradeAdapter.civil_to_physics_grade(8.0) == -8.0   # Uphill opposing gravity

    # Set speed limit high (50 km/h) so stopping distance / deceleration governs, not site cap
    road_down = RoadSegment.from_civil_grade(civil_grade_pct=-8.0, speed_limit_kmh=50.0)
    road_flat = RoadSegment.from_civil_grade(civil_grade_pct=0.0, speed_limit_kmh=50.0)
    road_up   = RoadSegment.from_civil_grade(civil_grade_pct=8.0, speed_limit_kmh=50.0)

    vehicle = MiningVehicle(is_loaded=True)
    env = EnvironmentState(r_effective=30.0)
    comm = CommunicationModel()
    mu = 0.35

    res_down = solve_safe_speed(vehicle, road_down, env, comm, mu_effective=mu)
    res_flat = solve_safe_speed(vehicle, road_flat, env, comm, mu_effective=mu)
    res_up   = solve_safe_speed(vehicle, road_up, env, comm, mu_effective=mu)

    assert res_down.v_safe_ms < res_flat.v_safe_ms
    assert res_flat.v_safe_ms <= res_up.v_safe_ms
    assert res_down.a_dec < res_flat.a_dec < res_up.a_dec
