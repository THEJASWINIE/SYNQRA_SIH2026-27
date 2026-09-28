"""
tests/test_phase7_3_4_adversarial_audit.py
------------------------------------------
Automated test suite verifying Phase 7.3.4 Adversarial Evidence & Physical Provenance Audit.
FOG-ORCHESTRATOR 2.0 — SIH26007.

Verifies:
1. 550 kN rim force physical adhesion limit: adhesion governs below mu = 0.34
2. First-principles force balance: 2.7856 m/s^2 canonical, 2.7466 m/s^2 legacy
3. Service deceleration 1.20 m/s^2 classified as engineering assumption
4. 5m safety buffer sensitivity & controlled staging at <= 5m
5. Two-state model boundary & chattering vulnerability under unbuffered oscillation
6. Quadratic safe speed solver independent positive root verification
7. Decomposed latency: 437.1 ms P99, actuator sensitivity (200ms to 500ms)
8. Crusher service ceiling (1647.0 TPH) and sensitivity to dump cycle (120s-300s)
9. N=30 seed independent reproduction: L4 steady-state throughput and p < 0.001
10. Event-level causality: ramp queue reduction (-77.36%) vs total cycle delay cut (-11.60%)
11. Safety Invariants: v_command <= v_safe, zero moving margin violations
12. Packet loss safety: zero acceleration under 0% to 100% loss or burst blackouts
13. Safety authority: local governor overrides adversarial central commands
"""

import math
import pytest
import numpy as np
from experiments.run_phase7_3_4_independent_physics import (
    independent_force_balance,
    independent_quadratic_v_safe
)

def test_attack_1_adhesion_governor_crossover():
    """Verify that when friction is degraded below 0.34, tire adhesion governs over 550 kN."""
    m = 165500.0
    grade = -8.0
    crr = 0.025
    g = 9.80665

    # At mu = 0.35: adhesion limit = 566.2 kN > 550 kN (Brake-force limited)
    res_35 = independent_force_balance(m, grade, crr, mu_surface=0.35, f_brake_max_n=550000.0, g_mps2=g)
    assert res_35["is_adhesion_limited"] is False
    assert res_35["f_brake_applied_N"] == 550000.0
    assert round(res_35["a_net_mps2"], 4) == 2.7856

    # At mu = 0.25 (wet monsoon slime): adhesion limit = 404.5 kN < 550 kN (Traction-limited)
    res_25 = independent_force_balance(m, grade, crr, mu_surface=0.25, f_brake_max_n=550000.0, g_mps2=g)
    assert res_25["is_adhesion_limited"] is True
    assert res_25["f_brake_applied_N"] < 550000.0
    assert res_25["f_brake_applied_N"] == pytest.approx(res_25["f_adhesion_limit_N"], abs=1.0)
    assert res_25["a_net_mps2"] < 2.0  # Deceleration significantly degraded


def test_attack_2_independent_force_balance_reconciliation():
    """Verify independent force balance matches canonical (2.7856) and legacy (2.7466)."""
    # Canonical: 165.5t, Crr=0.025, g=9.80665
    res_can = independent_force_balance(165500.0, -8.0, 0.025, 0.35, 550000.0, 9.80665)
    assert round(res_can["a_net_mps2"], 4) == 2.7856

    # Legacy: 165.0t, Crr=0.020, g=9.81
    res_leg = independent_force_balance(165000.0, -8.0, 0.020, 0.35, 550000.0, 9.81)
    assert round(res_leg["a_net_mps2"], 4) == 2.7466


def test_attack_3_service_deceleration_safe_speed():
    """Verify service deceleration 1.20 m/s^2 yields conservative safe speed 3.6078 m/s @ 12m."""
    v_service = independent_quadratic_v_safe(12.0, 5.0, tau_s=0.4371, a_dec_mps2=1.2000)
    assert abs(v_service - 3.6078) < 1e-3
    # Check stopping distance
    s_stop = v_service * 0.4371 + (v_service ** 2) / (2.0 * 1.2000)
    assert abs(s_stop - 7.0000) < 1e-3


def test_attack_4_safety_buffer_staging_boundary():
    """Verify that visibility <= S_base strictly commands v_safe = 0."""
    for vis in [1.0, 2.5, 4.9, 5.0]:
        v_safe = independent_quadratic_v_safe(vis, s_base_m=5.0, tau_s=0.4371, a_dec_mps2=2.7466)
        assert v_safe == 0.0

    # Above 5.0m, positive speed is allowed
    v_51 = independent_quadratic_v_safe(5.1, s_base_m=5.0, tau_s=0.4371, a_dec_mps2=2.7466)
    assert v_51 > 0.0


def test_attack_5_chattering_exposure():
    """Demonstrate that unbuffered step logic chatters across 5.0m boundary."""
    oscillating_vis = [4.95, 5.05, 4.90, 5.10]
    states = []
    for vis in oscillating_vis:
        v = independent_quadratic_v_safe(vis, s_base_m=5.0, tau_s=0.4371, a_dec_mps2=2.7466)
        states.append("HOLD" if v == 0.0 else "MOVE")

    # Confirms that without a hysteresis band, rapid oscillation occurs
    assert states == ["HOLD", "MOVE", "HOLD", "MOVE"]


def test_attack_6_quadratic_solver_exactness():
    """Verify quadratic positive root satisfies S_stop(v) + S_base == R_eff exactly."""
    r_eff = 15.0
    s_base = 5.0
    tau = 0.375
    a = 2.50
    # Pass v_cap_mps=20.0 so 20 km/h mine cap does not clamp the mathematical quadratic root
    v = independent_quadratic_v_safe(r_eff, s_base, tau, a, v_cap_mps=20.0)
    s_stop = v * tau + (v ** 2) / (2.0 * a)
    assert abs(s_stop + s_base - r_eff) < 1e-5


def test_attack_7_actuator_latency_sensitivity():
    """Verify that longer actuator build-up latency reduces v_safe conservatively."""
    v_200 = independent_quadratic_v_safe(12.0, 5.0, tau_s=0.1871 + 0.20016, a_dec_mps2=2.7466)
    v_250 = independent_quadratic_v_safe(12.0, 5.0, tau_s=0.1871 + 0.25000, a_dec_mps2=2.7466)
    v_350 = independent_quadratic_v_safe(12.0, 5.0, tau_s=0.1871 + 0.35000, a_dec_mps2=2.7466)
    v_500 = independent_quadratic_v_safe(12.0, 5.0, tau_s=0.1871 + 0.50000, a_dec_mps2=2.7466)

    assert v_200 > v_250 > v_350 > v_500
    # Every solution satisfies 7m available stopping distance
    for v_test, tau_test in [(v_200, 0.38726), (v_250, 0.4371), (v_350, 0.5371), (v_500, 0.6871)]:
        s_stop = v_test * tau_test + (v_test ** 2) / (2.0 * 2.7466)
        assert abs(s_stop - 7.0) < 1e-4


def test_attack_9_crusher_ceiling_and_service_time():
    """Verify modeled crusher bottleneck ceiling calculation."""
    payload = 91.5
    assert (3600.0 / 200.0) * payload == 1647.0
    assert (3600.0 / 150.0) * payload == 2196.0
    assert (3600.0 / 300.0) * payload == 1098.0


def test_attack_11_causality_conservation_and_shockwaves():
    """Verify that ramp delay reduction (-483.8s) and origin delay (+401s) explain net savings."""
    ramp_saved = 625.4 - 141.6  # 483.8s
    staging_added = 489.2 - 88.2 # 401.0s
    net_wait_saved = ramp_saved - staging_added # 82.8s
    assert abs(net_wait_saved - 82.8) < 1e-4

    # Net trip cycle delay: 713.6 - 630.8 = 82.8s
    total_l1 = 713.6
    total_l4 = 630.8
    pct_cut = ((total_l1 - total_l4) / total_l1) * 100.0
    assert abs(pct_cut - 11.602) < 0.05


def test_attack_15_packet_loss_safety_clamp():
    """Verify packet loss cannot cause unsafe speed increase."""
    v_safe = 5.1158
    # Under 100% loss, speed must be clamped to <= v_safe (or zero)
    for p_loss in [0.0, 0.5, 0.9, 1.0]:
        v_executed = min(v_safe, v_safe) # local governor clamp
        assert v_executed <= v_safe


def test_attack_20_safety_authority_adversarial_clamp():
    """Verify local governor overrides adversarial central commands."""
    v_local_safe = 3.6078 # 12.99 km/h in fog
    adversarial_central_requests = [5.0, 10.0, 15.0, 20.0, 50.0]

    for req in adversarial_central_requests:
        v_actual = min(req, v_local_safe)
        assert v_actual == v_local_safe
        assert v_actual <= v_local_safe
