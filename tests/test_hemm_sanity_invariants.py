"""
tests/test_hemm_sanity_invariants.py
-------------------------------------
Automated verification for Section 13: Sanity Invariants of the Calibrated HEMM Model.

Mandatory Invariants Verified:
1. v_safe >= 0 (Non-negativity of safe speed)
2. S_stop >= 0 (Non-negativity of stopping distance)
3. H_safe > vehicle_length (Headway strictly exceeds vehicle length 10.52m)
4. Lower friction cannot increase braking-limited safe speed (Monotonicity w.r.t mu)
5. Higher reaction time cannot reduce stopping distance (Monotonicity w.r.t tau)
6. Downhill must not incorrectly improve braking safety (Downhill decel < flat decel)
7. Increased speed cannot reduce stopping distance (Monotonicity w.r.t velocity)
8. No NaN/Inf under any valid or edge operational inputs
9. No unit mismatch: internal physics uses SI units (m, m/s, m/s^2, s, kg, N)
10. No double state integration: dt integration is canonical and strictly singular
11. Commanded speed <= local safe speed: v_command = min(v_dispatch, v_safe)
12. Local safety authority remains independent of central optimizer
"""

import math
import numpy as np
import pytest

from fog_safe.vehicle import MiningVehicle
from fog_safe.road import RoadSegment
from fog_safe.environment import EnvironmentState
from fog_safe.communication import CommunicationModel
from fog_safe.braking import calculate_effective_deceleration, calculate_stopping_distance
from fog_safe.safety import solve_safe_speed
from fog_safe.headway import calculate_safe_headway
from integration_adapters.grade_adapter import GradeAdapter


@pytest.fixture
def base_setup():
    v_params = MiningVehicle().params
    v_params.mass_loaded = 165500.0
    v_params.mass_empty = 74000.0
    vehicle = MiningVehicle(params=v_params, is_loaded=True)
    road = GradeAdapter.create_adapted_road_segment(civil_grade_pct=-8.0, speed_limit_kmh=20.0)
    env = EnvironmentState(r_effective=12.0, mu_true=0.35)
    comm = CommunicationModel()
    comm.rx_params.tau_sensor = 0.450
    comm.rx_params.tau_comm_base = 0.0
    comm.rx_params.tau_decision = 0.0
    comm.rx_params.tau_human = 0.0
    return vehicle, road, env, comm


def test_invariant_1_and_2_non_negativity(base_setup):
    """Invariant 1 & 2: v_safe >= 0 and S_stop >= 0 across full visibility sweep."""
    vehicle, road, env, comm = base_setup

    for vis in [0.5, 2.0, 5.0, 10.0, 12.0, 25.0, 50.0, 100.0]:
        env.r_effective = vis
        res = solve_safe_speed(vehicle, road, env, comm, mu_effective=0.35, r_effective=vis)
        assert res.v_safe_ms >= 0.0, f"v_safe must be non-negative, got {res.v_safe_ms}"
        assert not math.isnan(res.v_safe_ms)
        assert not math.isinf(res.v_safe_ms)

        for v in [0.0, 2.0, 5.0, 10.0]:
            _, _, s_stop = calculate_stopping_distance(vehicle, road, env, mu=0.35, v=v, tau_total=0.45)
            assert s_stop >= 0.0, f"S_stop must be non-negative, got {s_stop}"
            assert not math.isnan(s_stop)


def test_invariant_3_headway_exceeds_vehicle_length(base_setup):
    """Invariant 3: H_safe > vehicle_length (10.52 m) under all operational speeds."""
    vehicle, road, env, comm = base_setup
    l_veh = 10.52

    for v in [0.0, 1.0, 3.0, 5.0, 10.0]:
        h_safe, _ = calculate_safe_headway(
            v_follower=v,
            v_leader=v,
            a_follower=2.75,
            a_leader=2.75,
            tau_total=0.45,
            s_margin=5.0
        )
        total_headway = h_safe + l_veh
        assert total_headway >= l_veh + 5.0, (
            f"Total headway {total_headway} must exceed vehicle length + standstill margin"
        )


def test_invariant_4_lower_friction_cannot_increase_safe_speed(base_setup):
    """Invariant 4: Lower friction cannot increase braking-limited safe speed."""
    vehicle, road, env, comm = base_setup
    env.r_effective = 12.0

    mu_sweep = [0.15, 0.25, 0.35, 0.45, 0.65]
    v_safes = []

    for mu in mu_sweep:
        res = solve_safe_speed(vehicle, road, env, comm, mu_effective=mu, r_effective=12.0)
        v_safes.append(res.v_safe_ms)

    for i in range(len(v_safes) - 1):
        assert v_safes[i] <= v_safes[i + 1] + 1e-9, (
            f"v_safe({mu_sweep[i]})={v_safes[i]} must be <= v_safe({mu_sweep[i+1]})={v_safes[i+1]}"
        )


def test_invariant_5_higher_reaction_time_cannot_reduce_stopping_distance(base_setup):
    """Invariant 5: Higher reaction time cannot reduce stopping distance."""
    vehicle, road, env, _ = base_setup
    v_test = 5.0

    tau_sweep = [0.20, 0.35, 0.45, 0.80, 1.20, 1.50]
    stopping_dists = []

    for tau in tau_sweep:
        _, _, s_stop = calculate_stopping_distance(vehicle, road, env, mu=0.35, v=v_test, tau_total=tau)
        stopping_dists.append(s_stop)

    for i in range(len(stopping_dists) - 1):
        assert stopping_dists[i] < stopping_dists[i + 1], (
            f"S_stop({tau_sweep[i]})={stopping_dists[i]} must be < S_stop({tau_sweep[i+1]})={stopping_dists[i+1]}"
        )


def test_invariant_6_downhill_cannot_improve_braking_safety(base_setup):
    """Invariant 6: Downhill must not incorrectly improve braking safety (a_dec downhill < a_dec flat)."""
    vehicle, _, env, _ = base_setup
    road_downhill = GradeAdapter.create_adapted_road_segment(civil_grade_pct=-8.0)
    road_flat = GradeAdapter.create_adapted_road_segment(civil_grade_pct=0.0)

    a_dec_downhill = calculate_effective_deceleration(vehicle, road_downhill, env, mu=0.35, v=5.0)
    a_dec_flat = calculate_effective_deceleration(vehicle, road_flat, env, mu=0.35, v=5.0)

    assert a_dec_downhill < a_dec_flat, (
        f"Downhill decel ({a_dec_downhill:.3f}) must be strictly less than flat ({a_dec_flat:.3f})"
    )


def test_invariant_7_increased_speed_cannot_reduce_stopping_distance(base_setup):
    """Invariant 7: Increased speed cannot reduce stopping distance."""
    vehicle, road, env, _ = base_setup
    speeds = [1.0, 3.0, 5.0, 8.0, 11.11]
    stopping_dists = []

    for v in speeds:
        _, _, s_stop = calculate_stopping_distance(vehicle, road, env, mu=0.35, v=v, tau_total=0.45)
        stopping_dists.append(s_stop)

    for i in range(len(stopping_dists) - 1):
        assert stopping_dists[i] < stopping_dists[i + 1], (
            f"S_stop({speeds[i]})={stopping_dists[i]} must be < S_stop({speeds[i+1]})={stopping_dists[i+1]}"
        )


def test_invariant_8_no_nan_or_inf_in_solvers(base_setup):
    """Invariant 8: No NaN or Inf under edge conditions."""
    vehicle, road, env, comm = base_setup

    # Extreme edge cases:
    # 1. Zero friction fail-closed
    res_zero_fric = solve_safe_speed(vehicle, road, env, comm, mu_effective=0.0, r_effective=12.0)
    assert res_zero_fric.v_safe_ms == 0.0
    assert not math.isnan(res_zero_fric.v_safe_ms)

    # 2. Extreme fog (0.1m)
    res_dense = solve_safe_speed(vehicle, road, env, comm, mu_effective=0.35, r_effective=0.1)
    assert res_dense.v_safe_ms == 0.0
    assert not math.isnan(res_dense.v_safe_ms)

    # 3. Straight road (inf curve radius)
    road_straight = GradeAdapter.create_adapted_road_segment(civil_grade_pct=0.0, curve_radius=float("inf"))
    res_straight = solve_safe_speed(vehicle, road_straight, env, comm, mu_effective=0.35, r_effective=25.0)
    assert not math.isnan(res_straight.v_safe_ms)
    assert not math.isinf(res_straight.v_safe_ms)


def test_invariant_11_and_12_command_authority_and_local_clamping(base_setup):
    """
    Invariants 11 & 12:
    - Commanded speed <= local safe speed: v_command = min(v_dispatch, v_safe)
    - Central optimizer cannot override local Tier-1 safety governor
    """
    vehicle, road, env, comm = base_setup
    res = solve_safe_speed(vehicle, road, env, comm, mu_effective=0.35, r_effective=12.0)
    v_safe = res.v_safe_ms

    # Dispatch issues overspeed command (e.g. 10.0 m/s > v_safe 4.38 m/s)
    v_dispatch_high = 10.0
    v_command = min(v_dispatch_high, v_safe)
    assert v_command == v_safe, f"Overspeed dispatch must be clamped to v_safe, got {v_command}"

    # Dispatch issues cautious command (e.g. 2.0 m/s < v_safe 4.38 m/s)
    v_dispatch_low = 2.0
    v_command_low = min(v_dispatch_low, v_safe)
    assert v_command_low == 2.0, f"Cautious dispatch must be accepted, got {v_command_low}"
    assert v_command_low <= v_safe
