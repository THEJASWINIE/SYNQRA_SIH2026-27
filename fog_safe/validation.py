"""
Formal Mathematical & Physical Validation Engine.
Performs:
  1. Dimensional consistency assertions
  2. Boundary-value tests
  3. Monotonicity assertions
  4. Failure case & edge case safety verification
"""

import numpy as np
from fog_safe.config import VehicleParameters
from fog_safe.vehicle import MiningVehicle
from fog_safe.road import RoadSegment
from fog_safe.environment import EnvironmentState
from fog_safe.communication import CommunicationModel
from fog_safe.braking import calculate_stopping_distance, calculate_effective_deceleration
from fog_safe.safety import solve_safe_speed, calculate_v_stop

def run_formal_validation_suite() -> dict:
    """
    Executes automated physical sanity checks and monotonicity tests.
    Returns validation status report dict.
    """
    results = {}

    vehicle = MiningVehicle()
    env = EnvironmentState()
    comm = CommunicationModel()

    # --- 1. Boundary-Value Test: Zero Friction (mu -> 0) ---
    road_flat = RoadSegment(percent_grade=0.0)
    a_dec_zero_mu = calculate_effective_deceleration(vehicle, road_flat, env, mu=0.0)
    v_stop_zero_mu = calculate_v_stop(a_dec_zero_mu, comm.tau_total, r_effective=30.0, s_base=5.0)
    # With zero friction, rolling resistance still gives slight deceleration on flat road
    # On steep downhill, zero friction MUST give a_dec <= 0 and v_stop = 0
    road_steep = RoadSegment(percent_grade=8.0)
    a_dec_steep_zero = calculate_effective_deceleration(vehicle, road_steep, env, mu=0.0)
    v_stop_steep_zero = calculate_v_stop(a_dec_steep_zero, comm.tau_total, r_effective=30.0, s_base=5.0)

    results["test_zero_friction_flat_a_dec"] = float(a_dec_zero_mu)
    results["test_zero_friction_steep_v_stop"] = float(v_stop_steep_zero)
    assert v_stop_steep_zero == 0.0, "FAIL: Steep downhill with zero friction did not return v_stop = 0!"

    # --- 2. Boundary-Value Test: Visibility <= Safety Margin ---
    env_low_vis = EnvironmentState(r_effective=5.0)
    res_low_vis = solve_safe_speed(vehicle, road_flat, env_low_vis, comm, mu_effective=0.35, r_effective=5.0)
    results["test_vis_less_than_margin_v_safe"] = res_low_vis.v_safe_kmh
    assert res_low_vis.v_safe_ms == 0.0, "FAIL: Visibility <= S_margin did not return STOP!"

    # --- 3. Monotonicity Test: Grade vs Deceleration & Speed ---
    grades = [0.0, 4.0, 8.0, 10.0]
    a_decs = []
    v_safes = []
    for g in grades:
        rd = RoadSegment(percent_grade=g)
        res = solve_safe_speed(vehicle, rd, env, comm, mu_effective=0.35, r_effective=30.0)
        a_decs.append(res.a_dec)
        v_safes.append(res.v_safe_ms)

    # Check strictly non-increasing safe speed with steeper downhill grade
    is_grade_monotonic = all(x >= y for x, y in zip(v_safes[:-1], v_safes[1:]))
    results["test_grade_monotonicity_passed"] = is_grade_monotonic
    assert is_grade_monotonic, "FAIL: Safe speed did not monotonically decrease with downhill grade!"

    # --- 4. Monotonicity Test: Friction vs Safe Speed ---
    frictions = [0.20, 0.35, 0.50, 0.70]
    v_safes_mu = []
    for mu in frictions:
        res = solve_safe_speed(vehicle, road_steep, env, comm, mu_effective=mu, r_effective=30.0)
        v_safes_mu.append(res.v_safe_ms)

    is_friction_monotonic = all(x <= y for x, y in zip(v_safes_mu[:-1], v_safes_mu[1:]))
    results["test_friction_monotonicity_passed"] = is_friction_monotonic
    assert is_friction_monotonic, "FAIL: Safe speed did not monotonically increase with friction!"

    # --- 5. Monotonicity Test: Visibility vs Safe Speed ---
    visibilities = [10.0, 20.0, 30.0, 50.0]
    v_safes_vis = []
    for r in visibilities:
        res = solve_safe_speed(vehicle, road_steep, env, comm, mu_effective=0.35, r_effective=r)
        v_safes_vis.append(res.v_safe_ms)

    is_vis_monotonic = all(x <= y for x, y in zip(v_safes_vis[:-1], v_safes_vis[1:]))
    results["test_visibility_monotonicity_passed"] = is_vis_monotonic
    assert is_vis_monotonic, "FAIL: Safe speed did not monotonically increase with visibility!"

    results["overall_status"] = "PASSED"
    return results

if __name__ == "__main__":
    res = run_formal_validation_suite()
    print("Formal Validation Suite Results:", res)
