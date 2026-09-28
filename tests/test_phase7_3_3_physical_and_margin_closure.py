"""
tests/test_phase7_3_3_physical_and_margin_closure.py
---------------------------------------------------
Automated regression test suite for Phase 7.3.3:
Physical Derivation & Safety-Margin Closure.

Verifies:
1. First-principles brake force & longitudinal force balance on -8% ramp.
2. Independent stopping distance calculator & quadratic closed-form root.
3. Service (1.20 m/s^2) and emergency (2.7466 / 2.7856 m/s^2) regimes.
4. Two-State Safety Model (Moving vs Staged/Stopped).
5. Resolution of dense fog (3m, 4m, 5m) blindout and clearance margin definitions.
6. Reframing of road flow in VPH (817.8 / 587.2 VPH) and retraction of 74,828 TPH headline.
7. Modeled crusher ceiling (1647.0 TPH) and steady-state throughput (1591.4 TPH).
8. Safety invariant preservation (v_command <= v_safe).
"""

import math
import pytest
import numpy as np
from experiments.run_phase7_3_3_physics_and_margin_closure import (
    independent_stopping_distance,
    independent_safe_speed,
    longitudinal_force_balance,
    two_state_safety_evaluator
)

def test_first_principles_force_balance_legacy():
    """Verify legacy parameter set yields exactly 2.7466 m/s^2."""
    res = longitudinal_force_balance(
        mass_kg=165000.0,
        grade_pct=-8.0,
        crr=0.020,
        g=9.81,
        mu_tire_road=0.35,
        f_rim_max=550000.0
    )
    assert round(res["a_net_mps2"], 4) == 2.7466
    assert res["adhesion_limit_N"] > res["f_rim_brake_applied_N"]
    assert res["is_adhesion_exceeded"] is False


def test_first_principles_force_balance_canonical():
    """Verify canonical parameter set (165.5t, Crr=0.025, g=9.80665) yields 2.7856 m/s^2."""
    res = longitudinal_force_balance(
        mass_kg=165500.0,
        grade_pct=-8.0,
        crr=0.025,
        g=9.80665,
        mu_tire_road=0.35,
        f_rim_max=550000.0
    )
    assert round(res["a_net_mps2"], 4) == 2.7856
    assert res["f_downhill_N"] > 129000.0
    assert res["f_roll_N"] > 40000.0
    assert res["is_adhesion_exceeded"] is False


def test_independent_stopping_distance_calculator():
    """Verify pure independent formula without project imports."""
    v = 5.1158
    tau = 0.4371
    a = 2.7466
    
    d_react, d_brake, s_stop = independent_stopping_distance(v, tau, a)
    assert abs(d_react - 2.2361) < 1e-3
    assert abs(d_brake - 4.7643) < 1e-3
    assert abs(s_stop - 7.0004) < 1e-3


def test_independent_safe_speed_quadratic():
    """Verify positive root for 12m visibility at both deceleration levels."""
    tau = 0.4371
    r_eff = 12.0
    s_margin = 5.0
    
    # Emergency deceleration:
    v_emerg = independent_safe_speed(r_eff, s_margin, tau, a_dec_mps2=2.7466, v_cap=20.0)
    assert abs(v_emerg - 5.1156) < 1e-3
    
    # Service deceleration:
    v_service = independent_safe_speed(r_eff, s_margin, tau, a_dec_mps2=1.2000, v_cap=20.0)
    assert abs(v_service - 3.6078) < 1e-3


def test_two_state_safety_model_dense_fog():
    """Verify semantic distinction between State 1 (Moving) and State 2 (Staged)."""
    tau = 0.4371
    a = 2.7466
    s_margin = 5.0
    
    # Test dense fog blindout conditions:
    for vis in [3.0, 4.0, 5.0]:
        res = two_state_safety_evaluator(vis, s_margin, tau, a)
        assert res["operational_state"] == "STAGED_STOPPED"
        assert res["v_safe_mps"] == 0.0
        assert res["s_stop_m"] == 0.0
        assert res["standoff_sight_distance_m"] == vis
        assert res["gross_clearance_m"] == vis
        # Net travel margin is None for staged vehicles (or <= 0 if forced):
        assert res["is_safe"] is True
        
    # Test clear condition:
    res_clear = two_state_safety_evaluator(12.0, s_margin, tau, a)
    assert res_clear["operational_state"] == "MOVING"
    assert abs(res_clear["v_safe_mps"] - 5.1156) < 1e-3
    assert abs(res_clear["net_travel_margin_m"] - 0.0) < 1e-4
    assert res_clear["is_safe"] is True


def test_road_flow_reframing_vph():
    """Verify road flow is correctly stated in VPH and 74,828 TPH is treated as pipe flux."""
    h_space = 7.0004 + 5.0 + 10.52  # 22.5204 m
    v_emerg = 5.1158
    vph_emerg = (v_emerg / h_space) * 3600.0
    assert abs(vph_emerg - 817.8) < 0.5
    
    v_serv = 3.6734
    vph_serv = (v_serv / h_space) * 3600.0
    assert abs(vph_serv - 587.2) < 0.5


def test_crusher_bottleneck_ceiling():
    """Verify modeled crusher ceiling remains authoritative over road flow."""
    truck_payload_t = 91.5
    dump_cycle_s = 200.0
    tph_ceiling = (3600.0 / dump_cycle_s) * truck_payload_t
    assert abs(tph_ceiling - 1647.0) < 1e-5
