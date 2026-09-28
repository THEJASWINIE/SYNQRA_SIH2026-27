"""
tests/test_grade_adapter.py
---------------------------
Unit tests for Blocker 2: Grade Sign Convention & Normalization Adapter.
Validates:
1. Civil vs Physics conversion correctness.
2. Clamping and error handling on NaN/Inf/None.
3. Physical monotonicity:
   - Civil downhill (-8%) produces LOWER safe speed and LONGER stopping distance than flat (0%).
   - Civil uphill (+8%) produces HIGHER safe speed and SHORTER stopping distance than flat (0%).
   - Retarding and braking constraints correctly reflect gravity aiding vs resisting.
"""

import math
import pytest
from integration_adapters.grade_adapter import GradeAdapter, GradeConventionError
from fog_safe.road import RoadSegment
from fog_safe.vehicle import MiningVehicle
from fog_safe.environment import EnvironmentState
from fog_safe.communication import CommunicationModel
from fog_safe.braking import calculate_effective_deceleration, calculate_stopping_distance
from fog_safe.safety import solve_safe_speed


def test_grade_adapter_direct_conversions():
    # Zero grade
    assert GradeAdapter.civil_to_physics_grade(0.0) == 0.0
    assert GradeAdapter.physics_to_civil_grade(0.0) == 0.0

    # Civil Uphill (+8%) -> Physics (-8%)
    assert GradeAdapter.civil_to_physics_grade(8.0) == -8.0
    assert GradeAdapter.physics_to_civil_grade(-8.0) == 8.0

    # Civil Downhill (-8%) -> Physics (+8%)
    assert GradeAdapter.civil_to_physics_grade(-8.0) == 8.0
    assert GradeAdapter.physics_to_civil_grade(8.0) == -8.0

    # Clamp bounds check (MAX_MINE_GRADE_PCT = 25.0)
    assert GradeAdapter.civil_to_physics_grade(30.0) == -25.0
    assert GradeAdapter.civil_to_physics_grade(-30.0) == 25.0


def test_grade_adapter_error_handling():
    with pytest.raises(GradeConventionError):
        GradeAdapter.civil_to_physics_grade(float('nan'))
    with pytest.raises(GradeConventionError):
        GradeAdapter.civil_to_physics_grade(float('inf'))
    with pytest.raises(GradeConventionError):
        GradeAdapter.civil_to_physics_grade(None)


def test_road_segment_civil_integration():
    # Test RoadSegment created with civil_grade_pct
    road_downhill = RoadSegment.from_civil_grade(
        civil_grade_pct=-8.0,
        speed_limit_kmh=50.0
    )
    assert road_downhill.civil_grade_pct == -8.0
    # Internal percent_grade must be positive for downhill
    assert road_downhill.percent_grade == 8.0
    assert road_downhill.theta > 0.0

    road_uphill = RoadSegment.from_civil_grade(
        civil_grade_pct=8.0,
        speed_limit_kmh=50.0
    )
    assert road_uphill.civil_grade_pct == 8.0
    # Internal percent_grade must be negative for uphill
    assert road_uphill.percent_grade == -8.0
    assert road_uphill.theta < 0.0


def test_physics_monotonicity_braking_and_safe_speed():
    """
    CRITICAL INVARIANT:
    On a civil downhill slope (-8%):
    - Gravity accelerates the truck forward in the travel direction.
    - Stopping distance S_stop(v) is GREATER than on flat ground.
    - Deceleration a_dec is LESS than on flat ground.
    - Safe speed v_safe is LOWER than on flat ground.

    On a civil uphill slope (+8%):
    - Gravity opposes forward motion.
    - Stopping distance S_stop(v) is LESS than on flat ground.
    - Deceleration a_dec is GREATER than on flat ground.
    - Safe speed v_safe is HIGHER than on flat ground (capped by mine limit / traction).
    """
    vehicle = MiningVehicle(is_loaded=True)
    env = EnvironmentState(r_effective=25.0)  # Moderate fog (25m visibility)
    comm = CommunicationModel()
    mu = 0.35  # Wet gravel road friction

    road_flat = RoadSegment.from_civil_grade(civil_grade_pct=0.0, speed_limit_kmh=50.0)
    road_downhill = RoadSegment.from_civil_grade(civil_grade_pct=-8.0, speed_limit_kmh=50.0)
    road_uphill = RoadSegment.from_civil_grade(civil_grade_pct=8.0, speed_limit_kmh=50.0)

    # 1. Effective deceleration check at initial speed v = 8.0 m/s
    a_dec_flat = calculate_effective_deceleration(vehicle, road_flat, env, mu, v=8.0)
    a_dec_downhill = calculate_effective_deceleration(vehicle, road_downhill, env, mu, v=8.0)
    a_dec_uphill = calculate_effective_deceleration(vehicle, road_uphill, env, mu, v=8.0)

    print(f"\nDecelerations (m/s^2): Downhill={a_dec_downhill:.3f}, Flat={a_dec_flat:.3f}, Uphill={a_dec_uphill:.3f}")
    assert a_dec_downhill < a_dec_flat, f"Downhill decel ({a_dec_downhill}) must be less than flat ({a_dec_flat})"
    assert a_dec_flat < a_dec_uphill, f"Flat decel ({a_dec_flat}) must be less than uphill ({a_dec_uphill})"

    # 2. Stopping distance check at constant initial speed v = 8.0 m/s, tau = 1.0s
    _, _, s_stop_flat = calculate_stopping_distance(vehicle, road_flat, env, mu, v=8.0, tau_total=1.0)
    _, _, s_stop_downhill = calculate_stopping_distance(vehicle, road_downhill, env, mu, v=8.0, tau_total=1.0)
    _, _, s_stop_uphill = calculate_stopping_distance(vehicle, road_uphill, env, mu, v=8.0, tau_total=1.0)

    print(f"Stopping distances (m): Uphill={s_stop_uphill:.2f}, Flat={s_stop_flat:.2f}, Downhill={s_stop_downhill:.2f}")
    assert s_stop_downhill > s_stop_flat, f"Downhill stopping distance ({s_stop_downhill}) must be greater than flat ({s_stop_flat})"
    assert s_stop_flat > s_stop_uphill, f"Flat stopping distance ({s_stop_flat}) must be greater than uphill ({s_stop_uphill})"

    # 3. Maximum safe speed under fog (visibility = 25m)
    res_downhill = solve_safe_speed(vehicle, road_downhill, env, comm, mu_effective=mu, r_effective=25.0)
    res_flat = solve_safe_speed(vehicle, road_flat, env, comm, mu_effective=mu, r_effective=25.0)
    res_uphill = solve_safe_speed(vehicle, road_uphill, env, comm, mu_effective=mu, r_effective=25.0)

    print(f"Safe speeds (m/s): Downhill={res_downhill.v_safe_ms:.2f}, Flat={res_flat.v_safe_ms:.2f}, Uphill={res_uphill.v_safe_ms:.2f}")
    assert res_downhill.v_safe_ms < res_flat.v_safe_ms, f"Downhill v_safe ({res_downhill.v_safe_ms}) must be lower than flat ({res_flat.v_safe_ms})"
    assert res_flat.v_safe_ms <= res_uphill.v_safe_ms, f"Flat v_safe ({res_flat.v_safe_ms}) must be <= uphill ({res_uphill.v_safe_ms})"


def test_five_point_grade_matrix():
    """
    EXPLICIT 5-POINT GRADE CONVENTION TEST (+8%, +5%, 0%, -5%, -8%):
    Verifies across the full operational envelope:
    - Civil uphill (+8%, +5%): Gravity opposes motion, assisting braking deceleration.
    - Flat (0%): No longitudinal grade force.
    - Civil downhill (-5%, -8%): Gravity accelerates forward, opposing braking deceleration.
    
    Monotonicity Invariant:
    a_dec(+8%) > a_dec(+5%) > a_dec(0%) > a_dec(-5%) > a_dec(-8%)
    S_stop(+8%) < S_stop(+5%) < S_stop(0%) < S_stop(-5%) < S_stop(-8%)
    v_safe(+8%) >= v_safe(+5%) >= v_safe(0%) > v_safe(-5%) > v_safe(-8%)
    """
    vehicle = MiningVehicle(is_loaded=True)
    env = EnvironmentState(r_effective=25.0)
    comm = CommunicationModel()
    mu = 0.35
    v_test = 6.0  # m/s
    tau = 0.450   # canonical autonomous reaction time

    grades = [8.0, 5.0, 0.0, -5.0, -8.0]
    decelerations = []
    stopping_distances = []
    safe_speeds = []

    for g in grades:
        road = GradeAdapter.create_adapted_road_segment(civil_grade_pct=g, speed_limit_kmh=50.0)
        a_dec = calculate_effective_deceleration(vehicle, road, env, mu, v=v_test)
        _, _, s_stop = calculate_stopping_distance(vehicle, road, env, mu, v=v_test, tau_total=tau)
        safe_res = solve_safe_speed(vehicle, road, env, comm, mu_effective=mu, r_effective=25.0)

        decelerations.append(a_dec)
        stopping_distances.append(s_stop)
        safe_speeds.append(safe_res.v_safe_ms)

    # 1. Strict monotonicity for decelerations (uphill highest, downhill lowest)
    for i in range(len(grades) - 1):
        assert decelerations[i] > decelerations[i + 1], (
            f"Deceleration must strictly decrease from uphill to downhill: "
            f"a_dec({grades[i]}%)={decelerations[i]:.3f} vs a_dec({grades[i+1]}%)={decelerations[i+1]:.3f}"
        )

    # 2. Strict monotonicity for stopping distances (uphill shortest, downhill longest)
    for i in range(len(grades) - 1):
        assert stopping_distances[i] < stopping_distances[i + 1], (
            f"Stopping distance must strictly increase from uphill to downhill: "
            f"s_stop({grades[i]}%)={stopping_distances[i]:.3f} vs s_stop({grades[i+1]}%)={stopping_distances[i+1]:.3f}"
        )

    # 3. Monotonicity for safe speed (uphill highest, downhill lowest)
    for i in range(len(grades) - 1):
        assert safe_speeds[i] >= safe_speeds[i + 1], (
            f"Safe speed must not decrease when moving uphill: "
            f"v_safe({grades[i]}%)={safe_speeds[i]:.3f} vs v_safe({grades[i+1]}%)={safe_speeds[i+1]:.3f}"
        )


if __name__ == "__main__":
    pytest.main(["-v", __file__])

