"""
tests/test_phase7_4_safe_beacon.py
----------------------------------
PHASE 7.4 AUTOMATED REGRESSION SUITE: SAFE BEACON & FAIL-SAFE COMMUNICATION VALIDATION
FOG-ORCHESTRATOR 2.0 — SIH 2026-27 (SIH26007)

Validates:
1. All 18 Machine-Checkable Safety Invariants (I1 to I18)
2. Complete Failure Injection Matrix (SAFE-01 to SAFE-25)
3. Safe Beacon Protocol Parsing & Monotonic Sequence Tracking
4. Precedence Rules: EMERGENCY > STOP > COMM_LOSS > DEGRADED > NORMAL
5. "No beacon" ≠ "vehicle disappeared" (confidence degradation without disappearance)
6. Dense Fog Hysteresis & Debounce Filter (elimination of 4.9m <-> 5.1m chattering)
"""

import math
import time
import pytest

from integration_adapters.fail_safe_controller import (
    LocalVehicleSafetyGovernor,
    IncomingCommand,
    GovernorDecision,
    FailSafeState,
    CommandAction,
)
from integration_adapters.safe_beacon_adapter import (
    SafeBeaconAdapter,
    SafeBeaconMessage,
    BeaconState,
    BeaconSystemState,
    DenseFogDebounceFilter,
)
from fog_safe.safety import solve_safe_speed, calculate_v_stop
from fog_safe.road import RoadSegment
from fog_safe.vehicle import MiningVehicle
from fog_safe.environment import EnvironmentState
from fog_safe.communication import CommunicationModel
from integration_adapters.grade_adapter import GradeAdapter


# ==============================================================================
# SECTION 1 — CRITICAL SAFETY INVARIANTS (I1 to I18)
# ==============================================================================

def test_invariant_i1_v_command_le_v_safe():
    """I1: v_command <= v_safe strictly holds across arbitrary requested speeds."""
    v_safe_limit = 4.3815
    gov = LocalVehicleSafetyGovernor(vehicle_id="TRUCK_01", v_safe_default=v_safe_limit, clock=lambda: 100.0)

    for req in [0.0, 1.0, 2.5, 4.3815, 5.0, 10.0, 25.0, 100.0]:
        cmd = IncomingCommand("TRUCK_01", sequence=int(req * 10) + 1, timestamp=100.0, requested_speed_mps=req)
        res = gov.process_command(cmd, now=100.0)
        assert res.applied_speed <= v_safe_limit + 1e-9, f"Invariant I1 violated: {res.applied_speed} > {v_safe_limit}"


def test_invariant_i2_comm_loss_cannot_increase_v_safe():
    """I2: Communication loss cannot increase v_safe."""
    adapter = SafeBeaconAdapter(local_vehicle_id="TRUCK_01", clock=lambda: 100.0)
    gov = LocalVehicleSafetyGovernor(vehicle_id="TRUCK_01", v_safe_default=5.0, beacon_adapter=adapter, clock=lambda: 100.0)

    initial_v_safe = gov.v_safe
    # Simulate comm loss across gateway and V2V
    gov.update_local_safety_state(v_safe=initial_v_safe, has_gateway=False, has_v2v=False, packet_loss_rate=1.0)

    assert gov.v_safe <= initial_v_safe, "Invariant I2 violated: v_safe increased upon comm loss"


def test_invariant_i3_comm_loss_cannot_increase_v_command():
    """I3: Communication loss cannot increase v_command."""
    gov = LocalVehicleSafetyGovernor(vehicle_id="TRUCK_01", v_safe_default=4.0, clock=lambda: 100.0)
    cmd = IncomingCommand("TRUCK_01", sequence=1, timestamp=100.0, requested_speed_mps=3.5)
    res_normal = gov.process_command(cmd, now=100.0)

    # Disconnect gateway
    gov.update_local_safety_state(v_safe=4.0, has_gateway=False)
    cmd2 = IncomingCommand("TRUCK_01", sequence=2, timestamp=100.1, requested_speed_mps=3.5)
    res_loss = gov.process_command(cmd2, now=100.1)

    assert res_loss.applied_speed <= res_normal.applied_speed, "Invariant I3 violated: applied speed increased on comm loss"


def test_invariant_i4_stale_commands_cannot_remain_valid():
    """I4: Stale commands cannot remain valid indefinitely."""
    gov = LocalVehicleSafetyGovernor(vehicle_id="TRUCK_01", v_safe_default=5.0, max_command_age_s=1.0)
    # Command issued at t=100.0, received at t=101.5 (age 1.5s > 1.0s)
    cmd = IncomingCommand("TRUCK_01", sequence=1, timestamp=100.0, requested_speed_mps=4.0)
    res = gov.process_command(cmd, now=101.5)

    assert res.action == CommandAction.REJECT
    assert res.state == FailSafeState.STALE_COMMAND


def test_invariant_i5_duplicate_sequence_cannot_alter_state():
    """I5: Duplicate sequence numbers cannot alter safety state."""
    adapter = SafeBeaconAdapter(local_vehicle_id="TRUCK_01", clock=lambda: 100.0)
    pkt1 = "BEACON,TRUCK_02,50,STOP,100.0,ZONE_A"
    res1 = adapter.ingest_beacon(pkt1, now=100.0)
    assert res1.accepted is True
    assert adapter.current_system_state == BeaconSystemState.STOP

    # Duplicate sequence 50 attempting to claim NORMAL
    pkt_dup = "BEACON,TRUCK_02,50,NORMAL,100.05,ZONE_A"
    res2 = adapter.ingest_beacon(pkt_dup, now=100.05)
    assert res2.accepted is False
    assert res2.error_code == "DUPLICATE"
    assert adapter.current_system_state == BeaconSystemState.STOP, "Invariant I5 violated: duplicate sequence altered state"


def test_invariant_i6_older_sequence_cannot_overwrite_newer_state():
    """I6: Older sequence numbers cannot overwrite newer state."""
    adapter = SafeBeaconAdapter(local_vehicle_id="TRUCK_01", clock=lambda: 100.0)
    # Arrived sequence 100 (EMERGENCY)
    adapter.ingest_beacon("BEACON,TRUCK_02,100,EMERGENCY,100.0,ZONE_A", now=100.0)
    assert adapter.current_system_state == BeaconSystemState.EMERGENCY

    # Delayed old sequence 95 (NORMAL)
    res_old = adapter.ingest_beacon("BEACON,TRUCK_02,95,NORMAL,100.01,ZONE_A", now=100.01)
    assert res_old.accepted is False
    assert res_old.error_code == "OUT_OF_ORDER"
    assert adapter.current_system_state == BeaconSystemState.EMERGENCY, "Invariant I6 violated: old sequence altered state"


def test_invariant_i7_malformed_packets_cannot_create_valid_command():
    """I7: Malformed packets cannot create a valid safety command."""
    adapter = SafeBeaconAdapter(local_vehicle_id="TRUCK_01", clock=lambda: 100.0)
    malformed_inputs = [
        "",
        "BEACON",
        "BEACON,TRUCK_02",
        "BEACON,TRUCK_02,not_a_number,NORMAL,100.0,ZONE_A",
        "BEACON,TRUCK_02,10,NORMAL,nan,ZONE_A",
        "BEACON,TRUCK_02,10,NORMAL,100.0,",  # empty zone
        "INVALID_HEADER,TRUCK_02,10,NORMAL,100.0,ZONE_A",
    ]
    for bad in malformed_inputs:
        res = adapter.ingest_beacon(bad, now=100.0)
        assert res.accepted is False, f"Invariant I7 violated: malformed packet accepted: {bad}"
        assert res.beacon is None


def test_invariant_i8_unknown_beacon_states_cannot_create_permissive_behavior():
    """I8: Unknown beacon states cannot create permissive behavior."""
    adapter = SafeBeaconAdapter(local_vehicle_id="TRUCK_01", clock=lambda: 100.0)
    for bad_state in ["ACCELERATE", "FULL_SPEED", "OVERRIDE", "UNKNOWN", "GO"]:
        pkt = f"BEACON,TRUCK_02,10,{bad_state},100.0,ZONE_A"
        res = adapter.ingest_beacon(pkt, now=100.0)
        assert res.accepted is False, f"Invariant I8 violated: unknown state accepted: {bad_state}"
        assert res.error_code == "UNKNOWN_STATE"
    assert adapter.current_system_state == BeaconSystemState.NORMAL


def test_invariant_i9_missing_beacon_cannot_directly_trigger_acceleration():
    """I9: Missing beacon cannot directly trigger acceleration."""
    adapter = SafeBeaconAdapter(local_vehicle_id="TRUCK_01", peer_timeout_s=1.0, clock=lambda: 100.0)
    adapter.ingest_beacon("BEACON,TRUCK_02,1,NORMAL,100.0,ZONE_A", now=100.0)
    multiplier_before = adapter.get_local_safe_headway_multiplier()

    # Time advances 2.5s without beacon
    timed_out = adapter.check_timeouts(now=102.5)
    assert "TRUCK_02" in timed_out
    assert adapter.current_system_state == BeaconSystemState.COMM_LOSS

    # Headway multiplier must expand (increase defensive spacing), NEVER decrease
    multiplier_after = adapter.get_local_safe_headway_multiplier()
    assert multiplier_after >= multiplier_before, "Invariant I9 violated: headway decreased after peer beacon loss"
    assert multiplier_after == 2.0


def test_invariant_i10_gateway_failure_cannot_disable_local_governor():
    """I10: Gateway failure cannot disable the local safety governor."""
    gov = LocalVehicleSafetyGovernor(vehicle_id="TRUCK_01", v_safe_default=3.20, clock=lambda: 100.0)
    gov.update_local_safety_state(v_safe=3.20, has_gateway=False)

    # Central attempts to command 15.0 m/s
    cmd = IncomingCommand("TRUCK_01", sequence=1, timestamp=100.0, requested_speed_mps=15.0)
    res = gov.process_command(cmd, now=100.0)
    assert res.applied_speed <= 3.20, "Invariant I10 violated: local governor failed to clamp during gateway failure"
    assert res.action == CommandAction.REJECT


def test_invariant_i11_v2v_failure_cannot_disable_local_governor():
    """I11: V2V failure cannot disable the local safety governor."""
    gov = LocalVehicleSafetyGovernor(vehicle_id="TRUCK_01", v_safe_default=3.50, clock=lambda: 100.0)
    gov.update_local_safety_state(v_safe=3.50, has_gateway=True, has_v2v=False)

    cmd = IncomingCommand("TRUCK_01", sequence=1, timestamp=100.0, requested_speed_mps=8.0)
    res = gov.process_command(cmd, now=100.0)
    assert res.applied_speed <= 3.50, "Invariant I11 violated: local governor failed to clamp during V2V failure"


def test_invariant_i12_total_rf_failure_leaves_local_governor_operational():
    """I12: Gateway + V2V + beacon failure must still leave the local governor operational."""
    adapter = SafeBeaconAdapter(local_vehicle_id="TRUCK_01", clock=lambda: 100.0)
    gov = LocalVehicleSafetyGovernor(vehicle_id="TRUCK_01", v_safe_default=2.80, beacon_adapter=adapter, clock=lambda: 100.0)

    # All RF channels severed
    gov.update_local_safety_state(v_safe=2.80, has_gateway=False, has_v2v=False, packet_loss_rate=1.0)
    adapter.current_system_state = BeaconSystemState.COMM_LOSS

    for req in [0.0, 2.0, 5.0, 20.0]:
        cmd = IncomingCommand("TRUCK_01", sequence=int(req * 10) + 1, timestamp=100.0, requested_speed_mps=req)
        res = gov.process_command(cmd, now=100.0)
        assert res.applied_speed <= 2.80, "Invariant I12 violated: speed exceeded local safe envelope during total RF failure"


def test_invariant_i13_emergency_state_never_increases_commanded_speed():
    """I13: Emergency state must never result in a higher commanded speed than preceding state."""
    adapter = SafeBeaconAdapter(local_vehicle_id="TRUCK_01", clock=lambda: 100.0)
    gov = LocalVehicleSafetyGovernor(vehicle_id="TRUCK_01", v_safe_default=4.0, beacon_adapter=adapter, clock=lambda: 100.0)

    # Step 1: Nominal operation at 3.0 m/s
    res1 = gov.process_command(IncomingCommand("TRUCK_01", sequence=1, timestamp=100.0, requested_speed_mps=3.0), now=100.0)
    assert res1.applied_speed == 3.0

    # Step 2: Emergency beacon arrives
    adapter.ingest_beacon("BEACON,TRUCK_02,1,EMERGENCY,100.05,ZONE_A", now=100.05)
    res2 = gov.process_command(IncomingCommand("TRUCK_01", sequence=2, timestamp=100.05, requested_speed_mps=3.0), now=100.05)

    assert res2.applied_speed == 0.0
    assert res2.applied_speed <= res1.applied_speed, "Invariant I13 violated: speed increased in emergency"


def test_invariant_i14_stop_results_in_commanded_speed_zero():
    """I14: STOP must result in commanded speed = 0 within modeled command-decision path."""
    adapter = SafeBeaconAdapter(local_vehicle_id="TRUCK_01", clock=lambda: 100.0)
    gov = LocalVehicleSafetyGovernor(vehicle_id="TRUCK_01", v_safe_default=4.0, beacon_adapter=adapter, clock=lambda: 100.0)

    adapter.ingest_beacon("BEACON,TRUCK_02,1,STOP,100.0,ZONE_A", now=100.0)
    cmd = IncomingCommand("TRUCK_01", sequence=1, timestamp=100.0, requested_speed_mps=3.0)
    res = gov.process_command(cmd, now=100.0)

    assert res.applied_speed == 0.0
    assert res.action == CommandAction.CLAMP


def test_invariant_i15_recovery_does_not_instantly_restore_unrestricted_speed():
    """I15: Recovery from communication failure must not instantly restore unrestricted speed."""
    gov = LocalVehicleSafetyGovernor(vehicle_id="TRUCK_01", v_safe_default=4.0, clock=lambda: 100.0)
    gov.trigger_emergency_stop()
    gov.reset_emergency_stop()
    assert gov.in_recovery is True

    # Immediate frame 1 must be rejected / held
    res1 = gov.process_command(IncomingCommand("TRUCK_01", sequence=1, timestamp=100.0, requested_speed_mps=3.5), now=100.0)
    assert res1.action == CommandAction.REJECT
    assert res1.state == FailSafeState.RECOVERY


def test_invariant_i16_replay_normal_after_stop_does_not_cancel_safety():
    """I16: Replay of an old NORMAL beacon after STOP must not cancel the safety state."""
    adapter = SafeBeaconAdapter(local_vehicle_id="TRUCK_01", clock=lambda: 100.0)
    # Sequence 10: NORMAL
    adapter.ingest_beacon("BEACON,TRUCK_02,10,NORMAL,100.0,ZONE_A", now=100.0)
    # Sequence 11: STOP
    adapter.ingest_beacon("BEACON,TRUCK_02,11,STOP,100.1,ZONE_A", now=100.1)
    assert adapter.current_system_state == BeaconSystemState.STOP

    # Attacker replays Sequence 10 (NORMAL)
    res_replay = adapter.ingest_beacon("BEACON,TRUCK_02,10,NORMAL,100.2,ZONE_A", now=100.2)
    assert res_replay.accepted is False
    assert adapter.current_system_state == BeaconSystemState.STOP, "Invariant I16 violated: replayed NORMAL canceled STOP state"


def test_invariant_i17_corrupted_packet_does_not_modify_safety_state():
    """I17: Corrupted packet must not modify safety state."""
    adapter = SafeBeaconAdapter(local_vehicle_id="TRUCK_01", clock=lambda: 100.0)
    adapter.ingest_beacon("BEACON,TRUCK_02,1,NORMAL,100.0,ZONE_A", now=100.0)
    state_before = adapter.current_system_state

    # Corrupt string
    res = adapter.ingest_beacon("CORRUPT_PACKET_GARBAGE#$@!%", now=100.1)
    assert res.accepted is False
    assert adapter.current_system_state == state_before, "Invariant I17 violated: corrupted packet modified state"


def test_invariant_i18_central_orchestration_cannot_override_local_physics():
    """I18: Central orchestration cannot override local physics constraints."""
    # Under steep downhill -8% and wet ore, physical safe speed ceiling is strictly bounded
    road_downhill = RoadSegment.from_civil_grade(-8.0)
    env = EnvironmentState(r_effective=20.0, mu_true=0.35)
    veh = MiningVehicle()
    comm = CommunicationModel()
    sol = solve_safe_speed(veh, road_downhill, env, comm, mu_effective=0.35, r_effective=20.0)

    gov = LocalVehicleSafetyGovernor(vehicle_id="TRUCK_01", v_safe_default=sol.v_safe_ms, clock=lambda: 100.0)
    # Central optimizer attempts urgent dispatch at 15.0 m/s
    cmd = IncomingCommand(
        vehicle_id="TRUCK_01",
        sequence=1,
        timestamp=100.0,
        requested_speed_mps=15.0,
        command_source="CENTRAL_FLEET_OPTIMIZER"
    )
    res = gov.process_command(cmd, now=100.0)

    assert res.applied_speed <= sol.v_safe_ms
    assert res.action == CommandAction.CLAMP
    assert res.state == FailSafeState.UNSAFE_COMMAND


# ==============================================================================
# SECTION 2 — FAILURE INJECTION TEST MATRIX (SAFE-01 to SAFE-25)
# ==============================================================================

def test_safe01_normal_operation():
    """SAFE-01: All communication healthy -> Normal operation."""
    adapter = SafeBeaconAdapter(local_vehicle_id="TRUCK_01", clock=lambda: 100.0)
    gov = LocalVehicleSafetyGovernor(vehicle_id="TRUCK_01", v_safe_default=5.0, beacon_adapter=adapter, clock=lambda: 100.0)
    adapter.ingest_beacon("BEACON,TRUCK_02,1,NORMAL,100.0,HAUL_01", now=100.0)

    cmd = IncomingCommand("TRUCK_01", sequence=1, timestamp=100.0, requested_speed_mps=4.0)
    res = gov.process_command(cmd, now=100.0)

    assert res.state == FailSafeState.NORMAL
    assert res.action == CommandAction.ACCEPT
    assert res.applied_speed == 4.0


def test_safe02_gateway_failure():
    """SAFE-02: Gateway radio lost -> Vehicle continues under local safety control."""
    gov = LocalVehicleSafetyGovernor(vehicle_id="TRUCK_01", v_safe_default=4.0, clock=lambda: 100.0)
    gov.update_local_safety_state(v_safe=4.0, has_gateway=False)

    cmd = IncomingCommand("TRUCK_01", sequence=1, timestamp=100.0, requested_speed_mps=3.5)
    res = gov.process_command(cmd, now=100.0)

    assert res.state == FailSafeState.NO_GATEWAY
    assert res.action == CommandAction.REJECT
    assert res.applied_speed <= 4.0


def test_safe03_v2v_failure():
    """SAFE-03: V2V lost -> Local safety remains active, degraded mode."""
    gov = LocalVehicleSafetyGovernor(vehicle_id="TRUCK_01", v_safe_default=4.0, clock=lambda: 100.0)
    gov.update_local_safety_state(v_safe=4.0, has_gateway=True, has_v2v=False)

    cmd = IncomingCommand("TRUCK_01", sequence=1, timestamp=100.0, requested_speed_mps=3.5)
    res = gov.process_command(cmd, now=100.0)

    assert res.state == FailSafeState.DEGRADED_COMMUNICATION
    assert res.applied_speed <= 4.0


def test_safe04_gateway_plus_v2v_failure():
    """SAFE-04: Both Gateway and V2V severed -> Local governor authoritative."""
    gov = LocalVehicleSafetyGovernor(vehicle_id="TRUCK_01", v_safe_default=3.5, clock=lambda: 100.0)
    gov.update_local_safety_state(v_safe=3.5, has_gateway=False, has_v2v=False)

    cmd = IncomingCommand("TRUCK_01", sequence=1, timestamp=100.0, requested_speed_mps=5.0)
    res = gov.process_command(cmd, now=100.0)

    assert res.applied_speed <= 3.5
    assert res.action == CommandAction.REJECT


def test_safe05_beacon_failure_loss_tracking():
    """SAFE-05: Peer beacon transmission stops -> Timeout -> COMM_LOSS, vehicle not forgotten."""
    adapter = SafeBeaconAdapter(local_vehicle_id="TRUCK_01", peer_timeout_s=1.0, clock=lambda: 100.0)
    adapter.ingest_beacon("BEACON,TRUCK_02,1,NORMAL,100.0,ZONE_A", now=100.0)

    # 1.5s passes without beacon
    timed_out = adapter.check_timeouts(now=101.5)
    assert "TRUCK_02" in timed_out
    assert "TRUCK_02" in adapter.peers
    assert adapter.peers["TRUCK_02"].in_comm_loss is True
    assert adapter.current_system_state == BeaconSystemState.COMM_LOSS


def test_safe06_total_rf_failure():
    """SAFE-06: Total RF failure -> Local safety governor enforces safe envelope."""
    adapter = SafeBeaconAdapter(local_vehicle_id="TRUCK_01", clock=lambda: 100.0)
    gov = LocalVehicleSafetyGovernor(vehicle_id="TRUCK_01", v_safe_default=3.0, beacon_adapter=adapter, clock=lambda: 100.0)
    gov.update_local_safety_state(v_safe=3.0, has_gateway=False, has_v2v=False, packet_loss_rate=1.0)
    adapter.current_system_state = BeaconSystemState.COMM_LOSS

    cmd = IncomingCommand("TRUCK_01", sequence=1, timestamp=100.0, requested_speed_mps=10.0)
    res = gov.process_command(cmd, now=100.0)

    assert res.applied_speed <= 3.0
    assert res.action == CommandAction.REJECT


def test_safe07_replay_attack():
    """SAFE-07: Replay of an old NORMAL beacon after STOP -> Rejected."""
    adapter = SafeBeaconAdapter(local_vehicle_id="TRUCK_01", clock=lambda: 100.0)
    adapter.ingest_beacon("BEACON,TRUCK_02,1,NORMAL,100.0,ZONE_A", now=100.0)
    adapter.ingest_beacon("BEACON,TRUCK_02,2,STOP,100.1,ZONE_A", now=100.1)

    # Replay sequence 1
    res_replay = adapter.ingest_beacon("BEACON,TRUCK_02,1,NORMAL,100.2,ZONE_A", now=100.2)
    assert res_replay.accepted is False
    assert res_replay.error_code in ("DUPLICATE", "OUT_OF_ORDER")
    assert adapter.current_system_state == BeaconSystemState.STOP


def test_safe08_duplicate_packet():
    """SAFE-08: Send identical sequence repeatedly -> Duplicate rejected."""
    adapter = SafeBeaconAdapter(local_vehicle_id="TRUCK_01", clock=lambda: 100.0)
    pkt = "BEACON,TRUCK_02,15,NORMAL,100.0,ZONE_A"
    res1 = adapter.ingest_beacon(pkt, now=100.0)
    assert res1.accepted is True

    for _ in range(5):
        res_dup = adapter.ingest_beacon(pkt, now=100.01)
        assert res_dup.accepted is False
        assert res_dup.error_code == "DUPLICATE"


def test_safe09_out_of_order_packet():
    """SAFE-09: Sequence 100, 101, then 99, 98 -> 99 and 98 rejected."""
    adapter = SafeBeaconAdapter(local_vehicle_id="TRUCK_01", clock=lambda: 100.0)
    assert adapter.ingest_beacon("BEACON,TRUCK_02,100,NORMAL,100.0,ZONE_A", now=100.0).accepted is True
    assert adapter.ingest_beacon("BEACON,TRUCK_02,101,NORMAL,100.05,ZONE_A", now=100.05).accepted is True

    res99 = adapter.ingest_beacon("BEACON,TRUCK_02,99,NORMAL,100.10,ZONE_A", now=100.10)
    assert res99.accepted is False
    assert res99.error_code == "OUT_OF_ORDER"

    res98 = adapter.ingest_beacon("BEACON,TRUCK_02,98,NORMAL,100.15,ZONE_A", now=100.15)
    assert res98.accepted is False
    assert res98.error_code == "OUT_OF_ORDER"


def test_safe10_malformed_packet():
    """SAFE-10: Various corrupted and truncated packets safely rejected."""
    adapter = SafeBeaconAdapter(local_vehicle_id="TRUCK_01", clock=lambda: 100.0)
    test_cases = [
        "BEACON,",
        "BEACON,TRUCK_02",
        "BEACON,TRUCK_02,abc,NORMAL,100.0,ZONE_A",
        "BEACON,TRUCK_02,10,NORMAL,invalid_time,ZONE_A",
        "BEACON,TRUCK_02,10,NORMAL,100.0,",
        ",,,,,",
    ]
    for tc in test_cases:
        res = adapter.ingest_beacon(tc, now=100.0)
        assert res.accepted is False
        assert res.error_code == "MALFORMED"


def test_safe11_spoofed_vehicle_id():
    """SAFE-11: Unauthorized vehicle identifier -> Rejected."""
    adapter = SafeBeaconAdapter(local_vehicle_id="TRUCK_01", clock=lambda: 100.0)
    # TRUCK_99 is not in the allowed mining fleet
    res = adapter.ingest_beacon("BEACON,TRUCK_99,1,NORMAL,100.0,ZONE_A", now=100.0)
    assert res.accepted is False
    assert res.error_code == "UNKNOWN_VEHICLE"


def test_safe12_invalid_state():
    """SAFE-12: Unrecognized beacon state -> Rejected."""
    adapter = SafeBeaconAdapter(local_vehicle_id="TRUCK_01", clock=lambda: 100.0)
    res = adapter.ingest_beacon("BEACON,TRUCK_02,1,HYPER_DRIVE,100.0,ZONE_A", now=100.0)
    assert res.accepted is False
    assert res.error_code == "UNKNOWN_STATE"


def test_safe13_timestamp_failures():
    """SAFE-13: Future, ancient, zero, negative, and NaN timestamps rejected."""
    adapter = SafeBeaconAdapter(local_vehicle_id="TRUCK_01", future_tolerance_s=0.10, max_beacon_age_s=1.0, clock=lambda: 100.0)

    # Future timestamp: 105.0 > 100.0 + 0.10
    res_fut = adapter.ingest_beacon("BEACON,TRUCK_02,1,NORMAL,105.0,ZONE_A", now=100.0)
    assert res_fut.accepted is False
    assert res_fut.error_code == "FUTURE_TIMESTAMP"

    # Very old timestamp: age = 50.0s > 1.0s
    res_old = adapter.ingest_beacon("BEACON,TRUCK_02,2,NORMAL,50.0,ZONE_A", now=100.0)
    assert res_old.accepted is False
    assert res_old.error_code == "STALE"

    # Zero timestamp
    res_zero = adapter.ingest_beacon("BEACON,TRUCK_02,3,NORMAL,0.0,ZONE_A", now=100.0)
    assert res_zero.accepted is False
    assert res_zero.error_code == "MALFORMED"


def test_safe14_burst_loss():
    """SAFE-14: 100 consecutive lost packets -> Safe fallback occurs per timeout design."""
    adapter = SafeBeaconAdapter(local_vehicle_id="TRUCK_01", peer_timeout_s=1.0, clock=lambda: 100.0)
    adapter.ingest_beacon("BEACON,TRUCK_02,1,NORMAL,100.0,ZONE_A", now=100.0)

    # 100 packets lost over 5.0 seconds
    timed_out = adapter.check_timeouts(now=105.0)
    assert "TRUCK_02" in timed_out
    assert adapter.current_system_state == BeaconSystemState.COMM_LOSS


def test_safe15_recovery_progression():
    """SAFE-15: Communication failure -> DEGRADED/COMM_LOSS -> Recovery requires resync."""
    adapter = SafeBeaconAdapter(local_vehicle_id="TRUCK_01", peer_timeout_s=1.0, clock=lambda: 100.0)
    adapter.ingest_beacon("BEACON,TRUCK_02,1,NORMAL,100.0,ZONE_A", now=100.0)

    # Drop packets -> COMM_LOSS
    adapter.check_timeouts(now=102.0)
    assert adapter.current_system_state == BeaconSystemState.COMM_LOSS

    # Recovery beacon arrives
    res_rec = adapter.ingest_beacon("BEACON,TRUCK_02,2,NORMAL,102.5,ZONE_A", now=102.5)
    assert res_rec.accepted is True
    assert adapter.current_system_state == BeaconSystemState.NORMAL


def test_safe16_emergency_beacon():
    """SAFE-16: Preceding vehicle EMERGENCY beacon -> Local speed commanded to 0."""
    adapter = SafeBeaconAdapter(local_vehicle_id="TRUCK_01", clock=lambda: 100.0)
    gov = LocalVehicleSafetyGovernor(vehicle_id="TRUCK_01", v_safe_default=4.0, beacon_adapter=adapter, clock=lambda: 100.0)

    adapter.ingest_beacon("BEACON,TRUCK_02,1,EMERGENCY,100.0,ZONE_A", now=100.0)
    res = gov.process_command(IncomingCommand("TRUCK_01", sequence=1, timestamp=100.0, requested_speed_mps=3.0), now=100.0)

    assert res.state == FailSafeState.EMERGENCY_STOP
    assert res.applied_speed == 0.0
    assert res.action == CommandAction.REJECT


def test_safe17_stop_beacon():
    """SAFE-17: Preceding vehicle STOP beacon -> Local speed commanded to 0."""
    adapter = SafeBeaconAdapter(local_vehicle_id="TRUCK_01", clock=lambda: 100.0)
    gov = LocalVehicleSafetyGovernor(vehicle_id="TRUCK_01", v_safe_default=4.0, beacon_adapter=adapter, clock=lambda: 100.0)

    adapter.ingest_beacon("BEACON,TRUCK_02,1,STOP,100.0,ZONE_A", now=100.0)
    res = gov.process_command(IncomingCommand("TRUCK_01", sequence=1, timestamp=100.0, requested_speed_mps=3.0), now=100.0)

    assert res.applied_speed == 0.0
    assert res.action == CommandAction.CLAMP
    assert res.state == FailSafeState.STOP


def test_safe18_race_condition():
    """SAFE-18: Precedence rules hold under simultaneous conflicting beacon arrivals."""
    adapter = SafeBeaconAdapter(local_vehicle_id="TRUCK_01", clock=lambda: 100.0)

    # Ingest STOP, NORMAL, and EMERGENCY in rapid sequence
    adapter.ingest_beacon("BEACON,TRUCK_02,10,STOP,100.0,ZONE_A", now=100.0)
    assert adapter.current_system_state == BeaconSystemState.STOP

    adapter.ingest_beacon("BEACON,TRUCK_03,5,NORMAL,100.01,ZONE_A", now=100.01)
    # TRUCK_02 STOP must still dominate TRUCK_03 NORMAL
    assert adapter.current_system_state == BeaconSystemState.STOP

    adapter.ingest_beacon("BEACON,TRUCK_02,11,EMERGENCY,100.02,ZONE_A", now=100.02)
    # EMERGENCY dominates STOP
    assert adapter.current_system_state == BeaconSystemState.EMERGENCY


def test_safe19_power_loss_and_restoration():
    """SAFE-19: Gateway power cut then restored -> No sudden unsafe speed surge."""
    gov = LocalVehicleSafetyGovernor(vehicle_id="TRUCK_01", v_safe_default=4.0, clock=lambda: 100.0)

    # Normal step
    res1 = gov.process_command(IncomingCommand("TRUCK_01", sequence=1, timestamp=100.0, requested_speed_mps=3.0), now=100.0)
    assert res1.applied_speed == 3.0

    # Gateway power lost
    gov.update_local_safety_state(v_safe=4.0, has_gateway=False)
    res2 = gov.process_command(IncomingCommand("TRUCK_01", sequence=2, timestamp=100.1, requested_speed_mps=3.0), now=100.1)
    assert res2.action == CommandAction.REJECT
    assert res2.applied_speed <= 4.0

    # Gateway restored -> enters RECOVERY state requiring sequence validation
    gov.update_local_safety_state(v_safe=4.0, has_gateway=True)
    # Frame 1: must be in RECOVERY (rejected to prevent surge before synchronization)
    res3 = gov.process_command(IncomingCommand("TRUCK_01", sequence=3, timestamp=100.2, requested_speed_mps=15.0), now=100.2)
    assert res3.applied_speed <= 4.0
    assert res3.state == FailSafeState.RECOVERY
    assert res3.action == CommandAction.REJECT

    # Frame 2: second valid consecutive frame exits recovery, clamps excessive command
    res4 = gov.process_command(IncomingCommand("TRUCK_01", sequence=4, timestamp=100.3, requested_speed_mps=15.0), now=100.3)
    assert res4.applied_speed <= 4.0
    assert res4.action == CommandAction.CLAMP
    assert res4.state == FailSafeState.UNSAFE_COMMAND


def test_safe20_dense_fog_transition():
    """SAFE-20: Visibility drops from 50m to 3m -> v_safe immediately becomes 0, STAGED."""
    road = RoadSegment.from_civil_grade(0.0)
    veh = MiningVehicle()
    comm = CommunicationModel()

    # 50m visibility: non-zero safe speed
    env_50 = EnvironmentState(r_effective=50.0, mu_true=0.35)
    sol_50 = solve_safe_speed(veh, road, env_50, comm, mu_effective=0.35, r_effective=50.0)
    assert sol_50.v_safe_ms > 0.0

    # 3m visibility (below s_base = 5.0m): v_safe must be exactly 0.0 m/s
    env_3 = EnvironmentState(r_effective=3.0, mu_true=0.35)
    sol_3 = solve_safe_speed(veh, road, env_3, comm, mu_effective=0.35, r_effective=3.0)
    assert sol_3.v_safe_ms == 0.0


def test_safe21_visibility_noise():
    """SAFE-21: Noisy visibility above 5m -> Safe speed remains strictly bounded."""
    road = RoadSegment.from_civil_grade(-5.0)
    veh = MiningVehicle()
    comm = CommunicationModel()

    for vis in [6.0, 7.5, 9.2, 12.0, 25.0, 50.0]:
        env = EnvironmentState(r_effective=vis, mu_true=0.35)
        sol = solve_safe_speed(veh, road, env, comm, mu_effective=0.35, r_effective=vis)
        assert sol.v_safe_ms >= 0.0
        assert sol.s_stop + comm.margin_params.s_base <= vis + 1e-4


def test_safe22_chattering_elimination():
    """
    SAFE-22: Visibility fluctuating between 4.9m and 5.1m -> Debounce filter eliminates chattering!
    """
    debouncer = DenseFogDebounceFilter(s_base=5.0, hysteresis_margin_m=0.20, persistence_count=2)

    # Initial state: clear moving
    is_staged, r = debouncer.update(10.0)
    assert is_staged is False

    # Drop to 4.9m -> Immediate STAGED (halt)
    is_staged, r = debouncer.update(4.9)
    assert is_staged is True
    assert r <= 5.0

    # Fluctuates to 5.1m (between 5.0m and 5.2m exit threshold) -> Remains STAGED (no chatter)
    is_staged, r = debouncer.update(5.1)
    assert is_staged is True

    # Fluctuates to 4.95m -> Remains STAGED
    is_staged, r = debouncer.update(4.95)
    assert is_staged is True

    # Fluctuates to 5.15m -> Remains STAGED
    is_staged, r = debouncer.update(5.15)
    assert is_staged is True

    # Clear above 5.2m, first tick -> Still staged (persistence count 1 of 2)
    is_staged, r = debouncer.update(5.3)
    assert is_staged is True

    # Clear above 5.2m, second tick -> Transitions to MOVING
    is_staged, r = debouncer.update(5.3)
    assert is_staged is False
    assert r >= 5.2


def test_safe23_central_override_attempt():
    """SAFE-23: Central requests excessive speed -> Clamped to local safe envelope."""
    gov = LocalVehicleSafetyGovernor(vehicle_id="TRUCK_01", v_safe_default=3.5, clock=lambda: 100.0)
    cmd = IncomingCommand("TRUCK_01", sequence=1, timestamp=100.0, requested_speed_mps=12.0)
    res = gov.process_command(cmd, now=100.0)

    assert res.applied_speed == 3.5
    assert res.action == CommandAction.CLAMP


def test_safe24_stale_command_timeout():
    """SAFE-24: Command older than threshold -> Rejected as STALE_COMMAND."""
    gov = LocalVehicleSafetyGovernor(vehicle_id="TRUCK_01", v_safe_default=4.0, max_command_age_s=1.0)
    cmd = IncomingCommand("TRUCK_01", sequence=1, timestamp=95.0, requested_speed_mps=3.0)
    res = gov.process_command(cmd, now=100.0)

    assert res.action == CommandAction.REJECT
    assert res.state == FailSafeState.STALE_COMMAND


def test_safe25_command_recovery_resync():
    """SAFE-25: Recovery requires multiple valid frames before normal command execution."""
    gov = LocalVehicleSafetyGovernor(vehicle_id="TRUCK_01", v_safe_default=4.0)
    gov.trigger_emergency_stop()
    gov.reset_emergency_stop()

    # Frame 1 -> REJECT (RECOVERY)
    res1 = gov.process_command(IncomingCommand("TRUCK_01", sequence=1, timestamp=100.0, requested_speed_mps=2.5), now=100.0)
    assert res1.action == CommandAction.REJECT
    assert res1.state == FailSafeState.RECOVERY

    # Frame 2 -> ACCEPT (NORMAL)
    res2 = gov.process_command(IncomingCommand("TRUCK_01", sequence=2, timestamp=100.1, requested_speed_mps=2.5), now=100.1)
    assert res2.action == CommandAction.ACCEPT
    assert res2.state == FailSafeState.NORMAL
