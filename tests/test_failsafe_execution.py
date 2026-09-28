"""
tests/test_failsafe_execution.py
--------------------------------
Comprehensive Fail-Safe Test Matrix (FS-01 to FS-16) & Critical Invariants (I1 to I12).
Proves that the Local Vehicle Safety Governor remains the authoritative safety anchor
under all communication, telemetry, environmental, and command failure modes.
"""

import math
import pytest
from integration_adapters.fail_safe_controller import (
    LocalVehicleSafetyGovernor,
    IncomingCommand,
    FailSafeState,
    CommandAction,
)
from fog_safe.safety import solve_safe_speed
from fog_safe.road import RoadSegment
from fog_safe.vehicle import MiningVehicle
from fog_safe.environment import EnvironmentState
from fog_safe.communication import CommunicationModel
from integration_adapters.grade_adapter import GradeAdapter


# ==============================================================================
# PART 22 — FAIL-SAFE TEST MATRIX (FS-01 to FS-16)
# ==============================================================================

def test_fs01_valid_command():
    """FS-01: Valid dispatch command within safe speed -> ACCEPT, NORMAL state."""
    gov = LocalVehicleSafetyGovernor(vehicle_id="TRUCK_01", v_safe_default=5.0, clock=lambda: 100.0)
    cmd = IncomingCommand("TRUCK_01", sequence=1, timestamp=100.0, requested_speed_mps=4.0)
    res = gov.process_command(cmd, now=100.0)

    assert res.state == FailSafeState.NORMAL
    assert res.action == CommandAction.ACCEPT
    assert res.applied_speed == 4.0
    assert res.applied_speed <= res.v_safe


def test_fs02_command_above_safe_speed():
    """FS-02: Command above safe speed -> CLAMP to v_safe, UNSAFE_COMMAND state."""
    gov = LocalVehicleSafetyGovernor(vehicle_id="TRUCK_01", v_safe_default=4.20, clock=lambda: 100.0)
    cmd = IncomingCommand("TRUCK_01", sequence=1, timestamp=100.0, requested_speed_mps=5.50)
    res = gov.process_command(cmd, now=100.0)

    assert res.state == FailSafeState.UNSAFE_COMMAND
    assert res.action == CommandAction.CLAMP
    assert res.applied_speed == 4.20
    assert res.applied_speed <= res.v_safe


def test_fs03_stale_command():
    """FS-03: Stale command (age > max_command_age_s) -> REJECT, STALE_COMMAND state."""
    gov = LocalVehicleSafetyGovernor(vehicle_id="TRUCK_01", v_safe_default=5.0, max_command_age_s=1.0)
    cmd = IncomingCommand("TRUCK_01", sequence=1, timestamp=100.0, requested_speed_mps=3.5)
    # Processed at t = 101.5 (age = 1.5s > 1.0s)
    res = gov.process_command(cmd, now=101.5)

    assert res.state == FailSafeState.STALE_COMMAND
    assert res.action == CommandAction.REJECT


def test_fs04_duplicate_command():
    """FS-04: Duplicate command sequence -> REJECT, INVALID_COMMAND state."""
    gov = LocalVehicleSafetyGovernor(vehicle_id="TRUCK_01", v_safe_default=5.0)
    cmd1 = IncomingCommand("TRUCK_01", sequence=10, timestamp=100.0, requested_speed_mps=3.5)
    res1 = gov.process_command(cmd1, now=100.0)
    assert res1.action == CommandAction.ACCEPT

    # Replay of sequence 10
    cmd_dup = IncomingCommand("TRUCK_01", sequence=10, timestamp=100.1, requested_speed_mps=3.5)
    res2 = gov.process_command(cmd_dup, now=100.1)
    assert res2.state == FailSafeState.INVALID_COMMAND
    assert res2.action == CommandAction.REJECT


def test_fs05_out_of_order_command():
    """FS-05: Out-of-order sequence (lower than latest) -> REJECT, INVALID_COMMAND state."""
    gov = LocalVehicleSafetyGovernor(vehicle_id="TRUCK_01", v_safe_default=5.0)
    cmd_seq15 = IncomingCommand("TRUCK_01", sequence=15, timestamp=100.0, requested_speed_mps=4.0)
    gov.process_command(cmd_seq15, now=100.0)

    # Arrived late sequence 12
    cmd_seq12 = IncomingCommand("TRUCK_01", sequence=12, timestamp=100.1, requested_speed_mps=4.0)
    res = gov.process_command(cmd_seq12, now=100.1)
    assert res.state == FailSafeState.INVALID_COMMAND
    assert res.action == CommandAction.REJECT


def test_fs06_no_gateway():
    """FS-06: No gateway connected -> REJECT central command, NO_GATEWAY state."""
    gov = LocalVehicleSafetyGovernor(vehicle_id="TRUCK_01", v_safe_default=3.50)
    gov.update_local_safety_state(v_safe=3.50, has_gateway=False)

    cmd = IncomingCommand("TRUCK_01", sequence=1, timestamp=100.0, requested_speed_mps=3.0)
    res = gov.process_command(cmd, now=100.0)

    assert res.state == FailSafeState.NO_GATEWAY
    assert res.action == CommandAction.REJECT
    assert res.applied_speed <= res.v_safe


def test_fs07_gateway_handover():
    """FS-07: Gateway handover in progress with elevated packet loss -> DEGRADED_COMMUNICATION."""
    gov = LocalVehicleSafetyGovernor(vehicle_id="TRUCK_01", v_safe_default=4.0)
    gov.update_local_safety_state(v_safe=4.0, has_gateway=True, packet_loss_rate=0.40)

    cmd = IncomingCommand("TRUCK_01", sequence=1, timestamp=100.0, requested_speed_mps=3.5)
    res = gov.process_command(cmd, now=100.0)

    assert res.state == FailSafeState.DEGRADED_COMMUNICATION
    assert res.action == CommandAction.ACCEPT
    assert res.applied_speed <= res.v_safe


def test_fs08_rf_loss_and_watchdog_timeout():
    """FS-08: Complete RF loss exceeds watchdog threshold -> EMERGENCY_STOP, speed forced to 0."""
    gov = LocalVehicleSafetyGovernor(vehicle_id="TRUCK_01", v_safe_default=4.0, firmware_watchdog_timeout_s=1.0)
    # Valid first command at t = 100.0
    gov.process_command(IncomingCommand("TRUCK_01", sequence=1, timestamp=100.0, requested_speed_mps=3.0), now=100.0)

    # Next attempt at t = 102.5 (2.5s RF silence > 1.0s timeout)
    res = gov.process_command(IncomingCommand("TRUCK_01", sequence=2, timestamp=102.5, requested_speed_mps=3.0), now=102.5)
    assert res.state == FailSafeState.EMERGENCY_STOP
    assert res.action == CommandAction.REJECT
    assert res.applied_speed == 0.0


def test_fs09_backend_loss():
    """FS-09: Backend unavailable causes stale commands -> Vehicle rejects commands safely."""
    gov = LocalVehicleSafetyGovernor(vehicle_id="TRUCK_01", v_safe_default=4.0, max_command_age_s=1.0)
    cmd_stale = IncomingCommand("TRUCK_01", sequence=5, timestamp=95.0, requested_speed_mps=3.0)
    res = gov.process_command(cmd_stale, now=100.0)

    assert res.state == FailSafeState.STALE_COMMAND
    assert res.action == CommandAction.REJECT


def test_fs10_invalid_vehicle_id():
    """FS-10: Command addressed to TRUCK_02 arriving at TRUCK_01 -> REJECT, INVALID_COMMAND."""
    gov = LocalVehicleSafetyGovernor(vehicle_id="TRUCK_01", v_safe_default=4.0)
    cmd = IncomingCommand("TRUCK_02", sequence=1, timestamp=100.0, requested_speed_mps=3.0)
    res = gov.process_command(cmd, now=100.0)

    assert res.state == FailSafeState.INVALID_COMMAND
    assert res.action == CommandAction.REJECT


def test_fs11_corrupted_command():
    """FS-11: Command with negative speed or NaN -> REJECT, INVALID_COMMAND."""
    gov = LocalVehicleSafetyGovernor(vehicle_id="TRUCK_01", v_safe_default=4.0)

    cmd_neg = IncomingCommand("TRUCK_01", sequence=1, timestamp=100.0, requested_speed_mps=-5.0)
    res_neg = gov.process_command(cmd_neg, now=100.0)
    assert res_neg.state == FailSafeState.INVALID_COMMAND

    cmd_nan = IncomingCommand("TRUCK_01", sequence=2, timestamp=100.0, requested_speed_mps=float("nan"))
    res_nan = gov.process_command(cmd_nan, now=100.0)
    assert res_nan.state == FailSafeState.INVALID_COMMAND


def test_fs12_emergency_stop():
    """FS-12: Emergency stop action -> Latches EMERGENCY_STOP, applied speed forced to 0.0."""
    gov = LocalVehicleSafetyGovernor(vehicle_id="TRUCK_01", v_safe_default=4.0)
    cmd = IncomingCommand("TRUCK_01", sequence=1, timestamp=100.0, requested_speed_mps=3.0, action="EMERGENCY_STOP")
    res = gov.process_command(cmd, now=100.0)

    assert res.state == FailSafeState.EMERGENCY_STOP
    assert res.applied_speed == 0.0

    # Next ordinary command is still locked out by latched E-stop
    cmd2 = IncomingCommand("TRUCK_01", sequence=2, timestamp=100.1, requested_speed_mps=2.0)
    res2 = gov.process_command(cmd2, now=100.1)
    assert res2.state == FailSafeState.EMERGENCY_STOP
    assert res2.applied_speed == 0.0


def test_fs13_recovery():
    """FS-13: E-stop reset enters RECOVERY state requiring sequence re-synchronization."""
    gov = LocalVehicleSafetyGovernor(vehicle_id="TRUCK_01", v_safe_default=4.0)
    gov.trigger_emergency_stop("Test Fault")

    gov.reset_emergency_stop()
    assert gov.in_recovery is True
    assert gov.current_state == FailSafeState.RECOVERY

    # Observation 1 of recovery -> rejected
    cmd1 = IncomingCommand("TRUCK_01", sequence=1, timestamp=100.0, requested_speed_mps=2.5)
    res1 = gov.process_command(cmd1, now=100.0)
    assert res1.state == FailSafeState.RECOVERY
    assert res1.action == CommandAction.REJECT

    # Observation 2 of recovery -> recovery complete, command accepted
    cmd2 = IncomingCommand("TRUCK_01", sequence=2, timestamp=100.1, requested_speed_mps=2.5)
    res2 = gov.process_command(cmd2, now=100.1)
    assert res2.state == FailSafeState.NORMAL
    assert res2.action == CommandAction.ACCEPT


def test_fs14_unsafe_command_during_severe_fog():
    """FS-14: Command above safe speed during severe fog (vis <= 5m) -> CLAMP to severe fog safe limit."""
    # Compute ground-truth safe speed for 4m visibility
    road = RoadSegment.from_civil_grade(0.0)
    env = EnvironmentState(r_effective=4.0, mu_true=0.35)
    veh = MiningVehicle()
    comm = CommunicationModel()
    safe_sol = solve_safe_speed(veh, road, env, comm, mu_effective=0.35, r_effective=4.0)

    gov = LocalVehicleSafetyGovernor(vehicle_id="TRUCK_01", v_safe_default=safe_sol.v_safe_ms)
    # Central attempts to dispatch at 4.0 m/s in 4m fog
    cmd = IncomingCommand("TRUCK_01", sequence=1, timestamp=100.0, requested_speed_mps=4.0)
    res = gov.process_command(cmd, now=100.0)

    assert res.action == CommandAction.CLAMP
    assert res.applied_speed == pytest.approx(safe_sol.v_safe_ms, abs=1e-3)
    assert res.applied_speed <= res.v_safe


def test_fs15_unsafe_command_during_low_friction():
    """FS-15: Low friction (mu = 0.15 slick mud) -> CLAMP to reduced traction/braking safe limit."""
    road = RoadSegment.from_civil_grade(0.0)
    env = EnvironmentState(r_effective=30.0, mu_true=0.15)
    veh = MiningVehicle()
    comm = CommunicationModel()
    safe_sol = solve_safe_speed(
        veh, road, env, comm,
        mu_effective=0.15,
        r_effective=30.0,
        traction_ceiling_factor_mps=30.0
    )

    gov = LocalVehicleSafetyGovernor(vehicle_id="TRUCK_01", v_safe_default=safe_sol.v_safe_ms)
    cmd = IncomingCommand("TRUCK_01", sequence=1, timestamp=100.0, requested_speed_mps=6.0)
    res = gov.process_command(cmd, now=100.0)

    assert res.action == CommandAction.CLAMP
    assert res.applied_speed == pytest.approx(safe_sol.v_safe_ms, abs=1e-3)
    assert res.applied_speed <= safe_sol.v_safe_ms


def test_fs16_unsafe_command_during_downhill_operation():
    """FS-16: Steep downhill (-8% grade) -> CLAMP to retarder/downhill stopping safe limit."""
    road_downhill = RoadSegment.from_civil_grade(-8.0)
    env = EnvironmentState(r_effective=30.0, mu_true=0.35)
    veh = MiningVehicle()
    comm = CommunicationModel()
    safe_sol = solve_safe_speed(veh, road_downhill, env, comm, mu_effective=0.35, r_effective=30.0)

    gov = LocalVehicleSafetyGovernor(vehicle_id="TRUCK_01", v_safe_default=safe_sol.v_safe_ms)
    cmd = IncomingCommand("TRUCK_01", sequence=1, timestamp=100.0, requested_speed_mps=7.0)
    res = gov.process_command(cmd, now=100.0)

    assert res.action == CommandAction.CLAMP
    assert res.applied_speed == pytest.approx(safe_sol.v_safe_ms, abs=1e-3)
    assert res.applied_speed <= safe_sol.v_safe_ms


# ==============================================================================
# PART 23 — CRITICAL SAFETY INVARIANTS (I1 to I12)
# ==============================================================================

def test_invariant_i1_command_never_exceeds_v_safe():
    """I1: v_command <= v_safe strictly holds across arbitrary requested speeds."""
    gov = LocalVehicleSafetyGovernor(vehicle_id="TRUCK_01", v_safe_default=4.38)
    for requested in [0.0, 1.0, 4.38, 5.0, 10.0, 25.0, 100.0]:
        cmd = IncomingCommand("TRUCK_01", sequence=int(requested * 10), timestamp=100.0, requested_speed_mps=requested)
        res = gov.process_command(cmd, now=100.0)
        assert res.applied_speed <= 4.38 + 1e-6, f"Invariant I1 violated for requested {requested}"


def test_invariant_i2_stale_command_cannot_actuate():
    """I2: Stale command cannot actuate."""
    gov = LocalVehicleSafetyGovernor(vehicle_id="TRUCK_01", v_safe_default=5.0, max_command_age_s=1.0)
    cmd = IncomingCommand("TRUCK_01", sequence=1, timestamp=90.0, requested_speed_mps=4.0)
    res = gov.process_command(cmd, now=100.0)
    assert res.action == CommandAction.REJECT
    assert res.state == FailSafeState.STALE_COMMAND


def test_invariant_i3_duplicate_command_cannot_actuate():
    """I3: Duplicate command cannot actuate."""
    gov = LocalVehicleSafetyGovernor(vehicle_id="TRUCK_01", v_safe_default=5.0)
    cmd1 = IncomingCommand("TRUCK_01", sequence=5, timestamp=100.0, requested_speed_mps=3.0)
    gov.process_command(cmd1, now=100.0)
    cmd_dup = IncomingCommand("TRUCK_01", sequence=5, timestamp=100.1, requested_speed_mps=4.0)
    res = gov.process_command(cmd_dup, now=100.1)
    assert res.action == CommandAction.REJECT


def test_invariant_i4_out_of_order_command_cannot_actuate():
    """I4: Out-of-order command cannot actuate."""
    gov = LocalVehicleSafetyGovernor(vehicle_id="TRUCK_01", v_safe_default=5.0)
    gov.process_command(IncomingCommand("TRUCK_01", sequence=10, timestamp=100.0, requested_speed_mps=3.0), now=100.0)
    res = gov.process_command(IncomingCommand("TRUCK_01", sequence=8, timestamp=100.1, requested_speed_mps=4.0), now=100.1)
    assert res.action == CommandAction.REJECT


def test_invariant_i5_no_gateway_cannot_bypass_local_safety():
    """I5: No gateway cannot bypass local safety."""
    gov = LocalVehicleSafetyGovernor(vehicle_id="TRUCK_01", v_safe_default=3.0)
    gov.update_local_safety_state(v_safe=3.0, has_gateway=False)
    res = gov.process_command(IncomingCommand("TRUCK_01", sequence=1, timestamp=100.0, requested_speed_mps=6.0), now=100.0)
    assert res.applied_speed <= 3.0
    assert res.action == CommandAction.REJECT


def test_invariant_i6_central_cannot_override_local_governor():
    """I6: Central optimizer cannot override local governor."""
    gov = LocalVehicleSafetyGovernor(vehicle_id="TRUCK_01", v_safe_default=2.50)
    # Central optimizer requests emergency maximum speed 10.0 m/s
    cmd = IncomingCommand("TRUCK_01", sequence=1, timestamp=100.0, requested_speed_mps=10.0, command_source="CENTRAL_OPTIMIZER")
    res = gov.process_command(cmd, now=100.0)
    assert res.applied_speed == 2.50
    assert res.action == CommandAction.CLAMP


def test_invariant_i7_unsafe_command_is_rejected_or_clamped():
    """I7: Unsafe command is rejected or clamped."""
    gov = LocalVehicleSafetyGovernor(vehicle_id="TRUCK_01", v_safe_default=3.20)
    cmd = IncomingCommand("TRUCK_01", sequence=1, timestamp=100.0, requested_speed_mps=5.0)
    res = gov.process_command(cmd, now=100.0)
    assert res.action in (CommandAction.CLAMP, CommandAction.REJECT)
    assert res.applied_speed <= 3.20


def test_invariant_i8_emergency_state_forces_zero_speed():
    """I8: Emergency state forces zero commanded speed."""
    gov = LocalVehicleSafetyGovernor(vehicle_id="TRUCK_01", v_safe_default=4.0)
    res = gov.trigger_emergency_stop("Physical E-Stop Pressed")
    assert res.applied_speed == 0.0
    assert res.state == FailSafeState.EMERGENCY_STOP


def test_invariant_i9_recovery_does_not_immediately_bypass_validation():
    """I9: Communication recovery does not immediately bypass safety validation."""
    gov = LocalVehicleSafetyGovernor(vehicle_id="TRUCK_01", v_safe_default=4.0)
    gov.trigger_emergency_stop()
    gov.reset_emergency_stop()
    res1 = gov.process_command(IncomingCommand("TRUCK_01", sequence=1, timestamp=100.0, requested_speed_mps=3.0), now=100.0)
    assert res1.action == CommandAction.REJECT
    assert res1.state == FailSafeState.RECOVERY


def test_invariant_i10_negative_values_cannot_generate_unsafe_commands():
    """I10: Negative/invalid physical values cannot generate unsafe commands."""
    gov = LocalVehicleSafetyGovernor(vehicle_id="TRUCK_01", v_safe_default=4.0)
    cmd = IncomingCommand("TRUCK_01", sequence=1, timestamp=100.0, requested_speed_mps=-15.0)
    res = gov.process_command(cmd, now=100.0)
    assert res.action == CommandAction.REJECT
    assert res.applied_speed >= 0.0


def test_invariant_i11_nan_inf_cannot_propagate_to_actuator():
    """I11: NaN/Inf cannot propagate to vehicle command."""
    gov = LocalVehicleSafetyGovernor(vehicle_id="TRUCK_01", v_safe_default=4.0)
    for bad_val in [float("nan"), float("inf"), float("-inf")]:
        cmd = IncomingCommand("TRUCK_01", sequence=1, timestamp=100.0, requested_speed_mps=bad_val)
        res = gov.process_command(cmd, now=100.0)
        assert res.action == CommandAction.REJECT
        assert not math.isnan(res.applied_speed)
        assert not math.isinf(res.applied_speed)
        assert res.applied_speed >= 0.0


def test_invariant_i12_single_timestep_single_integration():
    """I12: One simulation timestep causes exactly one physical integration."""
    from fog_safe.simulator import DynamicSimulator
    vehicle = MiningVehicle(is_loaded=True)
    road = RoadSegment(percent_grade=0.0, speed_limit_kmh=50.0)
    env = EnvironmentState(r_effective=100.0, mu_true=0.65)
    comm = CommunicationModel()
    dt = 0.1
    duration = 5.0

    sim = DynamicSimulator(vehicle, road, env, comm, dt=dt)
    traj = sim.run_timeline_scenario(
        duration=duration,
        visibility_profile_fn=lambda t: 100.0,
        friction_profile_fn=lambda t: 0.65,
        comm_profile_fn=lambda t: 1.0,
        policy_type="STATIC_CONSERVATIVE"
    )

    num_steps = len(traj)
    assert num_steps == int(duration / dt), "Step count mismatch"
    # Verify that time advances strictly linearly by dt at each step
    for i, state in enumerate(traj):
        assert abs(state.t - i * dt) < 1e-5, f"Time progression error at step {i}"
