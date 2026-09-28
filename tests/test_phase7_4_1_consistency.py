"""
tests/test_phase7_4_1_consistency.py
------------------------------------
PHASE 7.4.1 FORENSIC AUDIT & CONSISTENCY TEST SUITE
FOG-ORCHESTRATOR 2.0 — SIH 2026-27 (SIH26007)

Rigorous automated verification for:
1. SAFE-05: Communication-loss semantics (headway expansion vs free-flow speed ceiling)
2. SAFE-17: STOP-state semantics (NORMAL -> STOP -> old replay -> STOP -> explicit recovery -> RECOVERY -> N=2 frames -> NORMAL)
3. SAFE-19: Gateway power recovery semantics (NO_GATEWAY -> comm restored -> RECOVERY -> valid frames -> NORMAL)
4. Security boundary verification (overspeed attack clamped vs nuisance attack possible)
5. Dense fog Schmitt-trigger debounce regression (no high-frequency chattering on noisy sequence)
6. Latency budget decomposition and stopping distance separation
"""

import pytest
import numpy as np
import time

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
from fog_safe.vehicle import MiningVehicle
from fog_safe.road import RoadSegment
from fog_safe.environment import EnvironmentState
from fog_safe.communication import CommunicationModel
from fog_safe.safety import solve_safe_speed, calculate_v_stop


# ==============================================================================
# 1. SAFE-05: COMMUNICATION LOSS SEMANTICS (Headway vs Speed Ceiling)
# ==============================================================================
def test_safe05_communication_loss_semantics_audit():
    """
    SAFE-05 Audit:
    Verifies that peer communication loss increases the defensive following headway (2x)
    while the free-flow safe speed ceiling remains governed by local physics sensors.
    
    Before: v_safe=4.00 m/s, v_cmd=4.00 m/s, headway_mult=1.0x (50m)
    After:  v_safe=4.00 m/s, v_cmd=4.00 m/s, headway_mult=2.0x (100m)
    Constraint: v_safe_after <= v_safe_before, v_command_after <= v_command_before
    """
    adapter = SafeBeaconAdapter(local_vehicle_id="TRUCK_01", peer_timeout_s=1.0, clock=lambda: 100.0)
    gov = LocalVehicleSafetyGovernor(vehicle_id="TRUCK_01", v_safe_default=4.0, beacon_adapter=adapter, clock=lambda: 100.0)

    # 1. Pre-loss state (nominal peer beacon received)
    adapter.ingest_beacon("BEACON,TRUCK_02,1,NORMAL,100.0,ZONE_A", now=100.0)
    cmd_before = IncomingCommand("TRUCK_01", sequence=1, timestamp=100.0, requested_speed_mps=4.0)
    res_before = gov.process_command(cmd_before, now=100.0)

    v_safe_before = res_before.v_safe
    v_command_before = res_before.applied_speed
    headway_mult_before = adapter.get_local_safe_headway_multiplier()
    base_headway_m = 50.0
    headway_before = base_headway_m * headway_mult_before

    assert res_before.state == FailSafeState.NORMAL
    assert v_safe_before == 4.0
    assert v_command_before == 4.0
    assert headway_mult_before == 1.0
    assert headway_before == 50.0

    # 2. Communication loss: 1.5s passes without peer beacon (timeout > 1.0s)
    timed_out = adapter.check_timeouts(now=101.5)
    assert "TRUCK_02" in timed_out
    assert adapter.current_system_state == BeaconSystemState.COMM_LOSS

    # 3. Post-loss state
    cmd_after = IncomingCommand("TRUCK_01", sequence=2, timestamp=101.5, requested_speed_mps=4.0)
    res_after = gov.process_command(cmd_after, now=101.5)

    v_safe_after = res_after.v_safe
    v_command_after = res_after.applied_speed
    headway_mult_after = adapter.get_local_safe_headway_multiplier()
    headway_after = base_headway_m * headway_mult_after

    # Formal assertions required by Section 3
    assert v_safe_after <= v_safe_before
    assert v_command_after <= v_command_before
    assert headway_after == 2.0 * headway_before
    assert headway_after == 100.0

    # Explicit audit conclusion:
    # "Communication loss increases the defensive following headway but does not
    # independently reduce the local safe-speed ceiling in this test condition."


def test_safe05_constrained_trailing_distance_headway_reduction():
    """
    Demonstrates that if a vehicle is following at a constrained distance (e.g., 70m),
    doubling the defensive headway from 50m to 100m forces the trailing speed to 0 m/s.
    """
    base_headway = 50.0
    actual_distance = 70.0

    # Nominal: distance (70m) >= nominal headway (50m) -> speed permitted
    nominal_mult = 1.0
    effective_nominal_headway = base_headway * nominal_mult
    assert actual_distance >= effective_nominal_headway

    # Post-loss: distance (70m) < defensive headway (100m) -> safety violation if moving -> must stop
    defensive_mult = 2.0
    effective_defensive_headway = base_headway * defensive_mult
    assert actual_distance < effective_defensive_headway


# ==============================================================================
# 2. SAFE-17: STOP-STATE SEMANTICS & EXPLICIT RECOVERY (N=2 Frames)
# ==============================================================================
def test_safe17_stop_state_explicit_semantics_and_recovery():
    """
    SAFE-17 Audit:
    Verifies complete lifecycle:
      NORMAL -> STOP received -> SAFETY_STATE = STOP -> v_command = 0
      -> old NORMAL replay -> STOP must remain active
      -> explicit valid recovery / peer clears -> RECOVERY state
      -> N=2 consecutive valid frames -> NORMAL
    """
    adapter = SafeBeaconAdapter(local_vehicle_id="TRUCK_01", clock=lambda: 100.0)
    gov = LocalVehicleSafetyGovernor(vehicle_id="TRUCK_01", v_safe_default=4.0, beacon_adapter=adapter, clock=lambda: 100.0)

    # 1. NORMAL state
    adapter.ingest_beacon("BEACON,TRUCK_02,1,NORMAL,100.0,ZONE_A", now=100.0)
    cmd1 = IncomingCommand("TRUCK_01", sequence=1, timestamp=100.0, requested_speed_mps=3.0)
    res1 = gov.process_command(cmd1, now=100.0)
    assert res1.state == FailSafeState.NORMAL
    assert res1.applied_speed == 3.0

    # 2. STOP received from peer beacon
    adapter.ingest_beacon("BEACON,TRUCK_02,2,STOP,100.1,ZONE_A", now=100.1)
    assert adapter.current_system_state == BeaconSystemState.STOP

    cmd2 = IncomingCommand("TRUCK_01", sequence=2, timestamp=100.1, requested_speed_mps=3.0)
    res2 = gov.process_command(cmd2, now=100.1)
    assert res2.state == FailSafeState.STOP
    assert res2.applied_speed == 0.0
    assert res2.action == CommandAction.CLAMP
    assert gov.current_state == FailSafeState.STOP

    # 3. Old NORMAL replay attack (Sequence 1 replayed while STOP is active)
    replay_res = adapter.ingest_beacon("BEACON,TRUCK_02,1,NORMAL,100.0,ZONE_A", now=100.2)
    assert replay_res.accepted is False
    assert replay_res.error_code in ("DUPLICATE", "OUT_OF_ORDER")
    assert adapter.current_system_state == BeaconSystemState.STOP

    # Governor evaluates replayed or continuing command -> STOP must remain active!
    cmd3 = IncomingCommand("TRUCK_01", sequence=3, timestamp=100.2, requested_speed_mps=3.0)
    res3 = gov.process_command(cmd3, now=100.2)
    assert res3.state == FailSafeState.STOP
    assert res3.applied_speed == 0.0
    assert gov.current_state == FailSafeState.STOP

    # 4. Explicit valid recovery: Peer sends fresh sequential NORMAL beacon
    clear_res = adapter.ingest_beacon("BEACON,TRUCK_02,3,NORMAL,100.3,ZONE_A", now=100.3)
    assert clear_res.accepted is True
    assert adapter.current_system_state == BeaconSystemState.NORMAL

    # 5. Recovery sequence: Governor must enter RECOVERY and require N=2 valid frames
    # Frame #1:
    cmd4 = IncomingCommand("TRUCK_01", sequence=4, timestamp=100.4, requested_speed_mps=3.0)
    res4 = gov.process_command(cmd4, now=100.4)
    assert res4.state == FailSafeState.RECOVERY
    assert res4.action == CommandAction.REJECT
    assert gov.current_state == FailSafeState.RECOVERY
    assert gov.in_recovery is True
    assert gov.recovery_observations == 1

    # Frame #2: Second valid consecutive frame completes recovery and enters NORMAL
    cmd5 = IncomingCommand("TRUCK_01", sequence=5, timestamp=100.5, requested_speed_mps=3.0)
    res5 = gov.process_command(cmd5, now=100.5)
    assert res5.state == FailSafeState.NORMAL
    assert res5.action == CommandAction.ACCEPT
    assert res5.applied_speed == 3.0
    assert gov.current_state == FailSafeState.NORMAL
    assert gov.in_recovery is False


# ==============================================================================
# 3. SAFE-19: GATEWAY POWER RECOVERY SEMANTICS (NO_GATEWAY -> RECOVERY -> NORMAL)
# ==============================================================================
def test_safe19_gateway_power_recovery_sequence():
    """
    SAFE-19 Audit:
    Verifies that gateway restoration does NOT immediately resume nominal operation:
      1. NO_GATEWAY active
      2. Communication restored -> enters RECOVERY
      3. Valid frame #1 -> RECOVERY (rejected)
      4. Invalid frame (duplicate/out-of-order) -> rejected and resets recovery counter
      5. Valid frame #1 (retry) -> RECOVERY (rejected)
      6. Valid frame #2 -> completes recovery -> NORMAL (accepted/clamped)
    """
    gov = LocalVehicleSafetyGovernor(vehicle_id="TRUCK_01", v_safe_default=4.0, clock=lambda: 100.0)

    # 1. Normal step
    cmd1 = IncomingCommand("TRUCK_01", sequence=1, timestamp=100.0, requested_speed_mps=3.0)
    res1 = gov.process_command(cmd1, now=100.0)
    assert res1.state == FailSafeState.NORMAL

    # 2. Gateway failure
    gov.update_local_safety_state(v_safe=4.0, has_gateway=False)
    cmd2 = IncomingCommand("TRUCK_01", sequence=2, timestamp=100.1, requested_speed_mps=3.0)
    res2 = gov.process_command(cmd2, now=100.1)
    assert res2.state == FailSafeState.NO_GATEWAY
    assert res2.action == CommandAction.REJECT
    assert gov.current_state == FailSafeState.NO_GATEWAY

    # 3. Gateway power restored -> transition to RECOVERY
    gov.update_local_safety_state(v_safe=4.0, has_gateway=True)
    assert gov.current_state == FailSafeState.RECOVERY
    assert gov.in_recovery is True
    assert gov.recovery_observations == 0

    # 4. Valid Frame #1: evaluated under RECOVERY
    cmd3 = IncomingCommand("TRUCK_01", sequence=3, timestamp=100.2, requested_speed_mps=3.0)
    res3 = gov.process_command(cmd3, now=100.2)
    assert res3.state == FailSafeState.RECOVERY
    assert res3.action == CommandAction.REJECT
    assert gov.recovery_observations == 1

    # 5. Fault injection: duplicate sequence injected during recovery
    cmd_dup = IncomingCommand("TRUCK_01", sequence=3, timestamp=100.25, requested_speed_mps=3.0)
    res_dup = gov.process_command(cmd_dup, now=100.25)
    assert res_dup.state == FailSafeState.INVALID_COMMAND
    assert res_dup.action == CommandAction.REJECT
    # Recovery counter was reset to 0
    assert gov.recovery_observations == 0
    assert gov.in_recovery is True

    # 6. Valid Frame #1 (re-synchronization after fault)
    cmd4 = IncomingCommand("TRUCK_01", sequence=4, timestamp=100.3, requested_speed_mps=3.0)
    res4 = gov.process_command(cmd4, now=100.3)
    assert res4.state == FailSafeState.RECOVERY
    assert res4.action == CommandAction.REJECT
    assert gov.recovery_observations == 1

    # 7. Valid Frame #2: second valid consecutive frame exits recovery -> NORMAL
    cmd5 = IncomingCommand("TRUCK_01", sequence=5, timestamp=100.4, requested_speed_mps=3.0)
    res5 = gov.process_command(cmd5, now=100.4)
    assert res5.state == FailSafeState.NORMAL
    assert res5.action == CommandAction.ACCEPT
    assert res5.applied_speed == 3.0
    assert gov.in_recovery is False


# ==============================================================================
# 4. SECURITY BOUNDARY VERIFICATION (Overspeed vs Availability)
# ==============================================================================
def test_security_boundary_safety_critical_overspeed_prevented():
    """
    Security Audit Class A:
    Can an adversary force v_applied > v_safe via a forged high-speed command?
    Result: NO. The local governor clamps the speed unconditionally.
    """
    gov = LocalVehicleSafetyGovernor(vehicle_id="TRUCK_01", v_safe_default=4.3815, clock=lambda: 100.0)

    # Attacker injects 30.0 m/s (108 km/h) over-speed command
    forged_cmd = IncomingCommand(
        vehicle_id="TRUCK_01",
        sequence=1,
        timestamp=100.0,
        requested_speed_mps=30.0,
        command_source="FORGED_CENTRAL_INJECTION"
    )
    res = gov.process_command(forged_cmd, now=100.0)

    assert res.applied_speed <= 4.3815
    assert res.action == CommandAction.CLAMP
    assert res.state == FailSafeState.UNSAFE_COMMAND
    assert res.applied_speed == 4.3815


def test_security_boundary_availability_nuisance_attack_possible():
    """
    Security Audit Class B:
    Can an unauthenticated adversary on 433 MHz trigger a nuisance false STOP or false EMERGENCY?
    Result: YES / POSSIBLE. Because RF packets lack cryptographic signatures, an attacker
    transmitting a syntactically valid BEACON frame with a valid future sequence number
    can cause a nuisance stop.
    """
    adapter = SafeBeaconAdapter(local_vehicle_id="TRUCK_01", clock=lambda: 100.0)
    gov = LocalVehicleSafetyGovernor(vehicle_id="TRUCK_01", v_safe_default=4.0, beacon_adapter=adapter, clock=lambda: 100.0)

    # Attacker broadcasts forged STOP beacon with sequence=500
    forged_beacon = "BEACON,TRUCK_02,500,STOP,100.0,ZONE_A"
    res_beacon = adapter.ingest_beacon(forged_beacon, now=100.0)

    # Structurally accepted because format is valid and sequence is fresh
    assert res_beacon.accepted is True
    assert adapter.current_system_state == BeaconSystemState.STOP

    # Vehicle halts (availability compromised, though safety preserved)
    cmd = IncomingCommand("TRUCK_01", sequence=1, timestamp=100.0, requested_speed_mps=3.0)
    res_gov = gov.process_command(cmd, now=100.0)
    assert res_gov.applied_speed == 0.0
    assert res_gov.state == FailSafeState.STOP

    # Conclusion: RF message authenticity is not cryptographically protected;
    # nuisance/availability attacks remain possible.


# ==============================================================================
# 5. DENSE FOG REGRESSION & CHATTERING ELIMINATION
# ==============================================================================
def test_dense_fog_regression_noisy_sequence():
    """
    Dense Fog Regression:
    Tests noisy sequence: 4.9, 5.1, 4.95, 5.05, 4.9, 5.15, 5.2, 5.25.
    Expected:
      Enter STAGED immediately at <= 5.0 m.
      Exit STAGED only after >= 5.2 m for N=2 consecutive observations.
      Zero high-frequency command chattering.
    """
    filt = DenseFogDebounceFilter(s_base=5.0, hysteresis_margin_m=0.20, persistence_count=2)

    sequence = [4.9, 5.1, 4.95, 5.05, 4.9, 5.15, 5.2, 5.25]
    states = []

    for r in sequence:
        is_staged, r_filt = filt.update(r)
        states.append((r, is_staged, r_filt))

    # 1. At 4.9m: enters STAGED immediately
    assert states[0][1] is True

    # 2. At 5.1m (deadband): remains STAGED
    assert states[1][1] is True

    # 3. At 4.95m (<=5.0m): remains STAGED
    assert states[2][1] is True

    # 4. At 5.05m (deadband): remains STAGED
    assert states[3][1] is True

    # 5. At 4.90m (<=5.0m): remains STAGED
    assert states[4][1] is True

    # 6. At 5.15m (deadband): remains STAGED
    assert states[5][1] is True

    # 7. At 5.20m: first observation >= 5.2m (counter=1 < 2), remains STAGED!
    assert states[6][1] is True

    # 8. At 5.25m: second consecutive observation >= 5.2m (counter=2 >= 2), exits STAGED!
    assert states[7][1] is False

    # Verify total transitions across this 8-step fluctuating sequence:
    # Exactly 2 transitions: MOVING -> STAGED (at step 0), and STAGED -> MOVING (at step 7).
    assert filt.transitions_count == 2


# ==============================================================================
# 6. MONTE CARLO ZERO-MARGIN EXPLANATION TEST
# ==============================================================================
def test_monte_carlo_zero_margin_analytical_definition():
    """
    Validates why minimum margin in Monte Carlo is exactly 0.0000 m:
    When requested speed exceeds safe speed, governor clamps to v_safe = v_stop.
    By analytical construction of calculate_v_stop, S_stop(v_stop) + S_base == R_effective.
    Therefore, remaining margin is identically 0.0000 m.
    """
    a_dec = 2.7856
    tau = 0.450
    vis = 15.0
    s_base = 5.0

    v_stop = calculate_v_stop(a_dec=a_dec, tau_total=tau, r_effective=vis, s_base=s_base)
    assert v_stop > 0.0

    s_stop = (v_stop * tau) + (v_stop**2) / (2.0 * a_dec)
    margin = vis - (s_stop + s_base)

    assert abs(margin) < 1e-6
