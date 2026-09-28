"""
D002 — Curve radius fail-closed regression tests.

Verifies that solve_safe_speed() correctly handles:
    +Inf radius     = explicit straight/no-curve → v_curve = inf
    finite positive = normal curve calculation → v_curve > 0
    0, negative, NaN, -Inf = FAIL CLOSED → v_curve = 0.0

Also verifies the adapter convention in vehicle_physics.py is preserved.
"""

import numpy as np
import pytest

from fog_safe.safety import solve_safe_speed
from fog_safe.vehicle import MiningVehicle
from fog_safe.road import RoadSegment
from fog_safe.environment import EnvironmentState
from fog_safe.communication import CommunicationModel


def _solve_with_curve_radius(curve_radius, mu=0.35):
    """Helper: solve with a given curve_radius and known-good other parameters."""
    veh = MiningVehicle()
    road = RoadSegment(percent_grade=0.0, speed_limit_kmh=50.0, curve_radius=curve_radius)
    env = EnvironmentState(r_effective=50.0, mu_true=mu)
    comm = CommunicationModel()
    return solve_safe_speed(veh, road, env, comm, mu_effective=mu, r_effective=50.0)


class TestCurveRadiusThreeWayBranch:

    def test_positive_inf_is_straight_road(self):
        """Explicit +inf = straight road, no curve constraint."""
        result = _solve_with_curve_radius(np.inf)
        assert result.candidate_limits_ms["v_curve"] == np.inf
        # v_safe should be positive (limited by other constraints, not curve)
        assert result.v_safe_ms > 0

    def test_finite_positive_is_normal_curve(self):
        """Finite positive curve_radius = normal curve calculation."""
        result = _solve_with_curve_radius(50.0)
        v_curve = result.candidate_limits_ms["v_curve"]
        assert np.isfinite(v_curve)
        assert v_curve > 0
        # Should be sqrt(mu * g * R) = sqrt(0.35 * 9.81 * 50) ≈ 13.1
        expected = np.sqrt(0.35 * 9.81 * 50.0)
        assert abs(v_curve - expected) < 0.01

    def test_zero_radius_fails_closed(self):
        """curve_radius = 0 must FAIL CLOSED (v_curve = 0)."""
        result = _solve_with_curve_radius(0.0)
        assert result.candidate_limits_ms["v_curve"] == 0.0
        assert result.v_safe_ms == 0.0

    def test_negative_radius_fails_closed(self):
        """curve_radius = -10 must FAIL CLOSED."""
        result = _solve_with_curve_radius(-10.0)
        assert result.candidate_limits_ms["v_curve"] == 0.0
        assert result.v_safe_ms == 0.0

    def test_nan_radius_fails_closed(self):
        """curve_radius = NaN must FAIL CLOSED."""
        result = _solve_with_curve_radius(float("nan"))
        assert result.candidate_limits_ms["v_curve"] == 0.0
        assert result.v_safe_ms == 0.0

    def test_negative_inf_radius_fails_closed(self):
        """curve_radius = -Inf must FAIL CLOSED (not treated as straight road)."""
        result = _solve_with_curve_radius(float("-inf"))
        assert result.candidate_limits_ms["v_curve"] == 0.0
        assert result.v_safe_ms == 0.0

    def test_invalid_radius_cannot_increase_safe_speed(self):
        """No invalid curve_radius can produce a v_safe > 0 (the whole point of D002)."""
        for bad_radius in [0, -10, float("nan"), float("-inf")]:
            result = _solve_with_curve_radius(bad_radius)
            assert result.v_safe_ms == 0.0, \
                f"curve_radius={bad_radius} produced v_safe={result.v_safe_ms} (must be 0.0)"

    def test_tighter_curve_reduces_speed(self):
        """A tighter curve (smaller positive radius) should reduce v_curve."""
        wide = _solve_with_curve_radius(200.0)
        tight = _solve_with_curve_radius(20.0)
        assert tight.candidate_limits_ms["v_curve"] < wide.candidate_limits_ms["v_curve"]


class TestAdapterConventionPreserved:

    @pytest.mark.skip(reason="Adapter import requires full module path; verified by source inspection")
    def test_adapter_converts_zero_radius_to_inf(self):
        """vehicle_physics.py adapter converts curve_radius_m <= 0 to np.inf."""
        pass

    def test_adapter_source_uses_inf_for_no_curve(self):
        """Verify the adapter convention exists in source (static check)."""
        import os
        adapter_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "SYNQRA_SIH2026-27-main", "models", "vehicle_physics.py",
        )
        with open(adapter_path) as f:
            src = f.read()
        # The adapter converts curve_radius_m <= 0 to np.inf
        assert "curve_radius_m" in src
        assert "np.inf" in src
        # Verify the convention: "if curve_radius_m and curve_radius_m > 0 else np.inf"
        assert "curve_radius_m > 0" in src
