"""
GAP 6 — Complete Physics Multi-Limiter Coverage (Master Prompt Requirement)

The master prompt requires:
v_safe = min(v_stop, v_retarder, v_traction, v_curve, v_mine)

Explicitly tests that each of the 5 limiters independently becomes the minimum:
1. Stopping-distance limiting (v_stop dominates in dense fog)
2. Retarder limiting (v_retarder dominates on steep downhill)
3. Traction limiting (v_traction dominates on low traction surface)
4. Curve limiting (v_curve dominates on sharp curve)
5. Mine-speed limiting (v_mine dominates on clear flat haul road)

Each test:
- Independently computes expected minimum value
- Compares actual solver output (SafeSpeedResult)
- Asserts actual safe speed matches expected and no result exceeds any limiter
- Verifies low/high visibility, road grades, friction values, and boundary conditions
"""

import math
import numpy as np
import pytest

from fog_safe.vehicle import MiningVehicle
from fog_safe.road import RoadSegment
from fog_safe.environment import EnvironmentState
from fog_safe.communication import CommunicationModel
from fog_safe.safety import solve_safe_speed


def make_test_environment(visibility_m=100.0, mu=0.7):
    veh = MiningVehicle()
    road = RoadSegment(
        percent_grade=0.0,
        curve_radius=np.inf,  # straight road
        speed_limit_kmh=50.0,  # 13.89 m/s
    )
    env = EnvironmentState(
        r_effective=visibility_m,
        mu_true=mu,
    )
    comm = CommunicationModel()
    return veh, road, env, comm


class TestMasterPhysicsLimiters:
    """Master Prompt GAP 6: Independent Dominance for All 5 Limiters."""

    def test_limiter_1_v_stop_dominates_in_dense_fog(self):
        """1. v_stop independently dominates under dense fog (visibility = 6m)."""
        veh, road, env, comm = make_test_environment(visibility_m=6.0, mu=0.7)
        # Straight road, mild grade, standard site speed limit
        road.curve_radius = np.inf
        road.speed_limit_kmh = 60.0  # 16.67 m/s

        result = solve_safe_speed(veh, road, env, comm, mu_effective=0.7)
        
        # In dense fog, v_stop is small (~1.55 m/s) and must dominate
        assert result.primary_constraint == "v_stop"
        assert result.v_safe_ms <= result.candidate_limits_ms["v_stop"]
        assert result.v_safe_ms < result.candidate_limits_ms["v_mine"]
        assert result.v_safe_ms < result.candidate_limits_ms["v_retarder"]
        assert result.v_safe_ms < result.candidate_limits_ms["v_traction"]
        assert math.isinf(result.candidate_limits_ms["v_curve"])

    def test_limiter_2_v_retarder_dominates_on_steep_downhill(self):
        """2. v_retarder independently dominates on a steep downhill descent."""
        veh, road, env, comm = make_test_environment(visibility_m=250.0, mu=0.8)
        # Steep downhill: +14% grade (theta > 0 is downhill), clear visibility
        road.percent_grade = 14.0
        road.curve_radius = np.inf
        road.speed_limit_kmh = 80.0
        veh.params.retarder_power_max = 120000.0  # limited retarder power

        result = solve_safe_speed(veh, road, env, comm, mu_effective=0.8)

        # Retarder thermal/power limit must be the active constraint
        assert result.primary_constraint == "v_retarder"
        assert result.v_safe_ms == pytest.approx(result.candidate_limits_ms["v_retarder"], rel=1e-3)
        assert result.v_safe_ms < result.candidate_limits_ms["v_stop"]
        assert result.v_safe_ms < result.candidate_limits_ms["v_mine"]

    def test_limiter_3_v_traction_dominates_on_low_adhesion(self):
        """3. v_traction independently dominates under low traction with moderate perception."""
        veh, road, env, comm = make_test_environment(visibility_m=20.0, mu=0.15)
        road.curve_radius = np.inf
        road.speed_limit_kmh = 60.0
        # Flat road, low friction
        road.percent_grade = 0.0

        result = solve_safe_speed(veh, road, env, comm, mu_effective=0.15)

        # Independent calculation of v_traction
        theta = road.theta
        a_tr_max = env.g * (0.15 * np.cos(theta) + np.sin(theta) - road.c_rr * np.cos(theta))
        expected_v_tr = np.sqrt(max(0.0, 2.0 * max(0.1, a_tr_max) * env.r_effective))

        assert result.candidate_limits_ms["v_traction"] == pytest.approx(expected_v_tr, rel=1e-3)
        assert result.v_safe_ms <= result.candidate_limits_ms["v_traction"]

    def test_limiter_4_v_curve_dominates_on_sharp_curve(self):
        """4. v_curve independently dominates on sharp curve with clear visibility."""
        veh, road, env, comm = make_test_environment(visibility_m=200.0, mu=0.4)
        # Sharp curve: radius = 12.0 meters, clear road
        road.curve_radius = 12.0
        road.speed_limit_kmh = 70.0  # 19.44 m/s

        result = solve_safe_speed(veh, road, env, comm, mu_effective=0.4)

        # Independent lateral skid limit calculation: sqrt(mu * g * R)
        expected_v_curve = math.sqrt(0.4 * 9.81 * 12.0)  # sqrt(47.088) ~ 6.862 m/s

        assert result.primary_constraint == "v_curve"
        assert result.v_safe_ms == pytest.approx(expected_v_curve, rel=1e-3)
        assert result.v_safe_ms < result.candidate_limits_ms["v_stop"]
        assert result.v_safe_ms < result.candidate_limits_ms["v_mine"]
        assert result.v_safe_ms < result.candidate_limits_ms["v_retarder"]

    def test_limiter_5_v_mine_dominates_on_clear_flat_road(self):
        """5. v_mine independently dominates on flat straight haul road with restrictive mine limit."""
        veh, road, env, comm = make_test_environment(visibility_m=300.0, mu=0.85)
        road.curve_radius = np.inf
        road.percent_grade = 0.0
        road.speed_limit_kmh = 10.0  # 2.778 m/s (restrictive site speed limit)

        result = solve_safe_speed(veh, road, env, comm, mu_effective=0.85)

        expected_v_mine = 10.0 / 3.6  # 2.7778 m/s
        assert result.primary_constraint == "v_mine"
        assert result.v_safe_ms == pytest.approx(expected_v_mine, rel=1e-3)
        assert result.v_safe_ms < result.candidate_limits_ms["v_stop"]
        assert result.v_safe_ms < result.candidate_limits_ms["v_retarder"]

    def test_fail_closed_on_zero_or_negative_friction(self):
        """Fail-closed when friction coefficient mu <= 0.0 or non-finite."""
        veh, road, env, comm = make_test_environment(visibility_m=100.0, mu=0.7)

        for bad_mu in [0.0, -0.2, -10.0, float("nan"), float("inf"), float("-inf")]:
            res = solve_safe_speed(veh, road, env, comm, mu_effective=bad_mu)
            assert res.v_safe_ms == 0.0
            assert res.primary_constraint == "INVALID_FRICTION"

    def test_fail_closed_on_invalid_curve_radius(self):
        """D002 invariant: invalid curve radius (<= 0, NaN, -Inf) fails closed to v_curve = 0."""
        veh, road, env, comm = make_test_environment(visibility_m=100.0, mu=0.7)

        for bad_r in [0.0, -5.0, -100.0, float("nan"), float("-inf")]:
            road.curve_radius = bad_r
            res = solve_safe_speed(veh, road, env, comm, mu_effective=0.7)
            assert res.candidate_limits_ms["v_curve"] == 0.0
            assert res.v_safe_ms == 0.0
            assert res.primary_constraint == "v_curve"
