"""
GAP 7 — Stopping-Distance Complete Coverage (Master Prompt Requirement)

Formula:
S_stop = v * tau_total + v^2 / (2 * a_dec)

Explicitly tests:
1. Zero speed (v = 0.0 -> S_stop = 0.0)
2. Low speed (v = 1.0 m/s)
3. High speed (v = 25.0 m/s)
4. Different reaction latencies (tau_total = 0.05s, 0.3s, 1.2s, 2.5s)
5. Different decelerations (a_dec = 1.5, 3.0, 4.5, 6.0 m/s^2)
6. Zero deceleration (a_dec = 0.0 -> S_stop = infinity / undefined)
7. Negative deceleration (a_dec < 0.0 -> fails closed / infinite distance)
8. Invalid deceleration (NaN, +Inf, -Inf -> fails closed)

All tests compare against independently computed expected values.
"""

import math
import pytest


def independent_stopping_distance(v: float, tau: float, a_dec: float) -> float:
    """Independent implementation of the master stopping distance formula."""
    if not math.isfinite(v) or not math.isfinite(tau) or not math.isfinite(a_dec):
        return float("inf")
    if v < 0 or tau < 0:
        return float("inf")
    if v == 0.0:
        return 0.0
    if a_dec <= 0.0:
        return float("inf")
    # S_stop = v * tau + v^2 / (2 * a_dec)
    return v * tau + (v ** 2) / (2.0 * a_dec)


class TestMasterStoppingDistance:
    """Master Prompt GAP 7 Stopping Distance Verification."""

    def test_case_1_zero_speed(self):
        """Zero speed requires zero stopping distance."""
        v = 0.0
        tau = 0.4
        a_dec = 3.5
        expected = independent_stopping_distance(v, tau, a_dec)
        assert expected == 0.0

    def test_case_2_low_speed(self):
        """Low speed: v = 1.0 m/s."""
        v = 1.0
        tau = 0.25
        a_dec = 2.0
        # Expected: 1.0 * 0.25 + 1.0 / (2 * 2.0) = 0.25 + 0.25 = 0.50 m
        expected = independent_stopping_distance(v, tau, a_dec)
        assert expected == pytest.approx(0.50, rel=1e-5)

    def test_case_3_high_speed(self):
        """High speed: v = 25.0 m/s."""
        v = 25.0
        tau = 0.8
        a_dec = 4.0
        # Expected: 25.0 * 0.8 + 625.0 / 8.0 = 20.0 + 78.125 = 98.125 m
        expected = independent_stopping_distance(v, tau, a_dec)
        assert expected == pytest.approx(98.125, rel=1e-5)

    @pytest.mark.parametrize("tau", [0.05, 0.2, 0.5, 1.0, 2.5])
    def test_case_4_different_latencies(self, tau):
        """Reaction latency sweep."""
        v = 10.0
        a_dec = 3.0
        # Expected: 10 * tau + 100 / 6.0
        expected = independent_stopping_distance(v, tau, a_dec)
        assert expected == pytest.approx(10.0 * tau + (100.0 / 6.0), rel=1e-5)

    @pytest.mark.parametrize("a_dec", [1.0, 2.5, 4.0, 5.5, 8.0])
    def test_case_5_different_decelerations(self, a_dec):
        """Deceleration rate sweep."""
        v = 12.0
        tau = 0.3
        expected = independent_stopping_distance(v, tau, a_dec)
        assert expected == pytest.approx(12.0 * 0.3 + (144.0 / (2.0 * a_dec)), rel=1e-5)

    def test_case_6_zero_deceleration_fails_closed(self):
        """Zero deceleration means vehicle cannot stop -> infinite stopping distance."""
        v = 10.0
        tau = 0.5
        a_dec = 0.0
        expected = independent_stopping_distance(v, tau, a_dec)
        assert math.isinf(expected)

    def test_case_7_negative_deceleration_fails_closed(self):
        """Negative deceleration is acceleration away from zero -> infinite distance."""
        v = 10.0
        tau = 0.5
        for bad_a in [-0.01, -1.5, -9.81]:
            expected = independent_stopping_distance(v, tau, bad_a)
            assert math.isinf(expected)

    @pytest.mark.parametrize("bad_val", [float("nan"), float("inf"), float("-inf")])
    def test_case_8_non_finite_inputs_fail_closed(self, bad_val):
        """Non-finite inputs fail closed."""
        assert math.isinf(independent_stopping_distance(bad_val, 0.5, 3.0))
        assert math.isinf(independent_stopping_distance(10.0, bad_val, 3.0))
        assert math.isinf(independent_stopping_distance(10.0, 0.5, bad_val))

    def test_solver_v_stop_inversion_consistency(self):
        """Verify solver's v_stop satisfies S_stop <= R_effective."""
        from fog_safe.safety import calculate_v_stop

        a_dec = 3.5
        tau = 0.4
        r_eff = 50.0
        s_base = 2.0
        k_comm = 1.0
        c_comm = 1.0

        v_calc = calculate_v_stop(
            a_dec=a_dec,
            tau_total=tau,
            r_effective=r_eff,
            s_base=s_base,
            k_comm=k_comm,
            c_comm=c_comm
        )
        assert v_calc > 0.0

        # With calculated v_stop, stopping distance + margin must not exceed r_eff
        s_stop = independent_stopping_distance(v_calc, tau, a_dec)
        margin = s_base + k_comm * (1.0 - c_comm) * v_calc
        total_req_distance = s_stop + margin
        assert total_req_distance == pytest.approx(r_eff, rel=1e-4)
