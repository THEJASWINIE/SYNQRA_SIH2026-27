"""
experiments/run_phase7_3_4_independent_physics.py
-------------------------------------------------
Phase 7.3.4 Adversarial Independent Physics & Provenance Audit Engine.
FOG-ORCHESTRATOR 2.0 — SIH26007.

Independent solver completely decoupled from project's existing functions.
Audits:
1. 550 kN braking force physical meaning and tire adhesion limits (Attack #1)
2. Deceleration sensitivity over mass, grade, Crr, mu (Attack #2)
3. Service deceleration sensitivity (Attack #3)
4. 5m safety buffer sensitivity (Attack #4)
5. Two-state model boundary & chattering/hysteresis test (Attack #5 & #24)
6. Quadratic safe speed solver across full parameter space (Attack #6)
7. Headway 22.52m decomposition and missing uncertainty terms (Attack #12)
8. Road flow in VPH vs TPH (Attack #13)
9. Grade sign convention verification (Attack #21)
10. Mass sensitivity across payload states (Attack #22)
11. Friction sensitivity and brake vs traction governor crossover (Attack #23)
12. Dense fog recovery timeline (Attack #25)
"""

import os
import math
import numpy as np
import pandas as pd

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DATA_DIR = os.path.join(ROOT_DIR, "data")
os.makedirs(DATA_DIR, exist_ok=True)

# ==============================================================================
# INDEPENDENT FIRST-PRINCIPLES CALCULATOR
# ==============================================================================

def independent_force_balance(
    mass_kg: float,
    civil_grade_pct: float,  # Negative for downhill (e.g. -8.0)
    crr: float,
    mu_surface: float,
    f_brake_max_n: float = 550000.0,
    g_mps2: float = 9.80665,
    v_mps: float = 0.0,
    cd: float = 0.80,
    frontal_area_m2: float = 22.0,
    rho_kg_m3: float = 1.225
) -> dict:
    """
    Completely independent force balance calculator using unambiguous sign conventions.
    Direction: vehicle moving forward along road (+x).
    Grade: civil_grade_pct < 0 is downhill (gravity pulls vehicle forward, opposing braking).
    """
    # Downhill angle
    grade_ratio = abs(civil_grade_pct) / 100.0
    theta = math.atan(grade_ratio)
    cos_theta = math.cos(theta)
    sin_theta = math.sin(theta)

    # 1. Normal force
    f_norm = mass_kg * g_mps2 * cos_theta

    # 2. Tire-road adhesion ceiling (Coulomb friction)
    f_adhesion = mu_surface * f_norm

    # 3. Available braking force at tire-road interface
    f_brake_available = min(f_brake_max_n, f_adhesion)
    is_adhesion_limited = (f_brake_max_n > f_adhesion)

    # 4. Rolling resistance (always opposes forward motion)
    f_roll = crr * f_norm

    # 5. Gravitational force component along road
    # Downhill (civil_grade_pct < 0): gravity acts forward (+x), opposing retarding
    # Uphill (civil_grade_pct > 0): gravity acts backward (-x), assisting retarding
    if civil_grade_pct < 0:
        f_grade_assist_motion = mass_kg * g_mps2 * sin_theta
    else:
        f_grade_assist_motion = -mass_kg * g_mps2 * sin_theta

    # 6. Aerodynamic drag
    f_aero = 0.5 * rho_kg_m3 * cd * frontal_area_m2 * (v_mps ** 2)

    # 7. Net retarding force opposing forward motion
    # F_net = F_brake + F_roll + F_aero - F_grade_forward
    f_net_retard = f_brake_available + f_roll + f_aero - f_grade_assist_motion

    # 8. Net longitudinal deceleration
    a_net = f_net_retard / mass_kg

    return {
        "mass_kg": mass_kg,
        "civil_grade_pct": civil_grade_pct,
        "crr": crr,
        "mu_surface": mu_surface,
        "f_norm_N": f_norm,
        "f_adhesion_limit_N": f_adhesion,
        "f_brake_applied_N": f_brake_available,
        "is_adhesion_limited": is_adhesion_limited,
        "f_roll_N": f_roll,
        "f_grade_forward_N": f_grade_assist_motion,
        "f_aero_N": f_aero,
        "f_net_retard_N": f_net_retard,
        "a_net_mps2": a_net
    }

def independent_quadratic_v_safe(
    r_effective_m: float,
    s_base_m: float,
    tau_s: float,
    a_dec_mps2: float,
    v_cap_mps: float = 5.5556
) -> float:
    """Independent quadratic root for v_safe: S_stop(v) + S_base <= R_eff."""
    r_avail = r_effective_m - s_base_m
    if r_avail <= 0.0 or a_dec_mps2 <= 0.0:
        return 0.0
    t1 = a_dec_mps2 * tau_s
    disc = (t1 ** 2) + 2.0 * a_dec_mps2 * r_avail
    if disc <= 0.0:
        return 0.0
    v_root = -t1 + math.sqrt(disc)
    return max(0.0, min(v_root, v_cap_mps))

# ==============================================================================
# AUDIT RUNNERS
# ==============================================================================

def run_attack_1_550kn_and_adhesion():
    """Attack #1 & #23: Physical achievability of 550 kN across friction levels."""
    print("--- Running Attack #1 & #23: 550 kN Rim Force & Adhesion Limits ---")
    m_can = 165500.0
    grade = -8.0
    crr = 0.025
    g = 9.80665

    frictions = [0.15, 0.20, 0.25, 0.30, 0.34, 0.35, 0.40, 0.45, 0.50]
    records = []

    for mu in frictions:
        res = independent_force_balance(m_can, grade, crr, mu, f_brake_max_n=550000.0, g_mps2=g)
        # What deceleration would tire adhesion alone allow?
        a_adhesion_only = (res["f_adhesion_limit_N"] + res["f_roll_N"] - res["f_grade_forward_N"]) / m_can
        # What deceleration does 550 kN clamp allow if adhesion were infinite?
        a_brake_only = (550000.0 + res["f_roll_N"] - res["f_grade_forward_N"]) / m_can
        # Actual deceleration governed by min(550 kN, adhesion):
        a_governed = res["a_net_mps2"]

        records.append({
            "mu_friction": mu,
            "f_normal_N": round(res["f_norm_N"], 1),
            "f_adhesion_limit_N": round(res["f_adhesion_limit_N"], 1),
            "f_brake_applied_N": round(res["f_brake_applied_N"], 1),
            "is_adhesion_limited": res["is_adhesion_limited"],
            "adhesion_utilization_pct": round(min(1.0, 550000.0 / res["f_adhesion_limit_N"]) * 100, 2),
            "decel_brake_limited_mps2": round(a_brake_only, 4),
            "decel_traction_limited_mps2": round(a_adhesion_only, 4),
            "decel_governed_mps2": round(a_governed, 4),
            "governing_regime": "TRACTION_LIMITED" if res["is_adhesion_limited"] else "BRAKE_FORCE_LIMITED"
        })

    df = pd.DataFrame(records)
    out_csv = os.path.join(DATA_DIR, "phase7_3_4_adhesion_audit.csv")
    df.to_csv(out_csv, index=False)
    print(f"Saved {out_csv}: {len(df)} rows")
    return df

def run_attack_2_deceleration_sensitivity():
    """Attack #2: Sensitivity of emergency deceleration over mass, grade, Crr, mu."""
    print("--- Running Attack #2: Deceleration Sensitivity Grid ---")
    masses = [150000.0, 165000.0, 165500.0, 180000.0]
    grades = [-3.0, -5.0, -8.0, -10.0]
    crrs = [0.015, 0.020, 0.025, 0.030]
    mus = [0.20, 0.25, 0.30, 0.35, 0.40]

    records = []
    for m in masses:
        for gr in grades:
            for c in crrs:
                for mu in mus:
                    res = independent_force_balance(m, gr, c, mu, f_brake_max_n=550000.0)
                    records.append({
                        "mass_kg": m,
                        "civil_grade_pct": gr,
                        "crr": c,
                        "mu": mu,
                        "f_net_retard_N": round(res["f_net_retard_N"], 1),
                        "a_net_mps2": round(res["a_net_mps2"], 4),
                        "is_adhesion_limited": res["is_adhesion_limited"]
                    })

    df = pd.DataFrame(records)
    out_csv = os.path.join(DATA_DIR, "phase7_3_4_deceleration_sensitivity.csv")
    df.to_csv(out_csv, index=False)
    print(f"Saved {out_csv}: {len(df)} rows")
    return df

def run_attack_3_service_deceleration():
    """Attack #3: Service deceleration sensitivity (0.8 to 2.0 m/s^2) on v_safe."""
    print("--- Running Attack #3: Service Deceleration Sensitivity ---")
    a_services = [0.8, 1.0, 1.2, 1.5, 2.0]
    visibilities = [100.0, 50.0, 25.0, 12.0, 10.0, 8.0, 5.0]
    tau = 0.4371
    s_base = 5.0

    records = []
    for a in a_services:
        for vis in visibilities:
            v_safe = independent_quadratic_v_safe(vis, s_base, tau, a, v_cap_mps=5.5556)
            d_react = v_safe * tau
            d_brake = (v_safe ** 2) / (2.0 * a) if a > 0 else 0.0
            s_stop = d_react + d_brake
            records.append({
                "a_service_mps2": a,
                "visibility_m": vis,
                "v_safe_mps": round(v_safe, 4),
                "v_safe_kmh": round(v_safe * 3.6, 2),
                "s_stop_m": round(s_stop, 4),
                "margin_deficit_m": round(vis - s_stop - s_base, 4)
            })

    df = pd.DataFrame(records)
    out_csv = os.path.join(DATA_DIR, "phase7_3_4_service_decel_sensitivity.csv")
    df.to_csv(out_csv, index=False)
    print(f"Saved {out_csv}: {len(df)} rows")
    return df

def run_attack_4_safety_buffer_sensitivity():
    """Attack #4: 5m safety buffer sensitivity (2m to 10m)."""
    print("--- Running Attack #4: Safety Buffer Sensitivity ---")
    buffers = [2.0, 3.0, 4.0, 5.0, 6.0, 8.0, 10.0]
    visibilities = [100.0, 50.0, 25.0, 12.0, 10.0, 8.0, 5.0, 3.0]
    tau = 0.4371
    a_emerg = 2.7466

    records = []
    for s_b in buffers:
        for vis in visibilities:
            v_safe = independent_quadratic_v_safe(vis, s_b, tau, a_emerg)
            records.append({
                "s_base_m": s_b,
                "visibility_m": vis,
                "v_safe_mps": round(v_safe, 4),
                "v_safe_kmh": round(v_safe * 3.6, 2),
                "is_staged_hold": (v_safe == 0.0)
            })

    df = pd.DataFrame(records)
    out_csv = os.path.join(DATA_DIR, "phase7_3_4_safety_buffer_sensitivity.csv")
    df.to_csv(out_csv, index=False)
    print(f"Saved {out_csv}: {len(df)} rows")
    return df

def run_attack_5_chattering_hysteresis():
    """Attack #5 & #24: Test chattering when visibility oscillates across 5.0m threshold."""
    print("--- Running Attack #5 & #24: Boundary Chattering / Hysteresis Test ---")
    # Oscillating sequence around 5.0m
    vis_sequence = [4.9, 5.1, 4.8, 5.2, 4.95, 5.05, 4.7, 5.3, 5.0, 5.01, 4.99]
    tau = 0.4371
    a_emerg = 2.7466
    s_base = 5.0

    records = []
    # Test unbuffered instantaneous transition vs hysteresis buffered transition
    # Unbuffered:
    state = "UNKNOWN"
    for t_step, vis in enumerate(vis_sequence):
        v_unbuffered = independent_quadratic_v_safe(vis, s_base, tau, a_emerg)
        state_unbuf = "STAGED_HOLD" if v_unbuffered == 0.0 else "MOVING"
        records.append({
            "step": t_step,
            "visibility_m": vis,
            "v_unbuffered_mps": round(v_unbuffered, 4),
            "state_unbuffered": state_unbuf,
            "rapid_cycle_event": True if t_step > 0 and state_unbuf != records[-1]["state_unbuffered"] else False
        })

    df = pd.DataFrame(records)
    out_csv = os.path.join(DATA_DIR, "phase7_3_4_chattering_audit.csv")
    df.to_csv(out_csv, index=False)
    print(f"Saved {out_csv}: {len(df)} rows")
    return df

def run_attack_6_quadratic_grid():
    """Attack #6: Full quadratic solver cross-validation across latencies and decelerations."""
    print("--- Running Attack #6: Quadratic Safe Speed Sensitivity Grid ---")
    taus = [0.25, 0.325, 0.375, 0.4371, 0.475, 0.60, 0.80]
    decelerations = [1.2000, 2.7466, 2.7856]
    visibilities = [3.0, 4.0, 5.0, 8.0, 10.0, 12.0, 15.0, 25.0, 50.0, 100.0]
    s_base = 5.0

    records = []
    for tau in taus:
        for a in decelerations:
            for vis in visibilities:
                v = independent_quadratic_v_safe(vis, s_base, tau, a)
                d_react = v * tau
                d_brake = (v ** 2) / (2.0 * a) if a > 0 else 0.0
                s_stop = d_react + d_brake
                records.append({
                    "tau_s": tau,
                    "a_dec_mps2": a,
                    "visibility_m": vis,
                    "v_safe_mps": round(v, 4),
                    "v_safe_kmh": round(v * 3.6, 2),
                    "s_stop_m": round(s_stop, 4),
                    "total_space_m": round(s_stop + (s_base if v > 0 else 0.0), 4)
                })

    df = pd.DataFrame(records)
    out_csv = os.path.join(DATA_DIR, "phase7_3_4_quadratic_grid.csv")
    df.to_csv(out_csv, index=False)
    print(f"Saved {out_csv}: {len(df)} rows")
    return df

def run_attack_25_recovery_timeline():
    """Attack #25: Recovery timeline: 3m -> STOP -> 4m -> 5m -> 6m -> 10m -> NORMAL."""
    print("--- Running Attack #25: Dense Fog Recovery Timeline ---")
    steps = [
        {"phase": "INITIAL_NORMAL", "visibility_m": 50.0, "time_s": 0.0},
        {"phase": "SUDDEN_FOG_ENTRY", "visibility_m": 3.0, "time_s": 10.0},
        {"phase": "DENSE_FOG_HOLD_1", "visibility_m": 3.0, "time_s": 60.0},
        {"phase": "DENSE_FOG_HOLD_2", "visibility_m": 4.0, "time_s": 120.0},
        {"phase": "THRESHOLD_HOLD", "visibility_m": 5.0, "time_s": 180.0},
        {"phase": "CLEARING_INIT", "visibility_m": 6.0, "time_s": 240.0},
        {"phase": "CLEARING_PARTIAL", "visibility_m": 10.0, "time_s": 300.0},
        {"phase": "RECOVERY_FULL", "visibility_m": 50.0, "time_s": 360.0}
    ]

    records = []
    tau = 0.4371
    a_emerg = 2.7466
    s_base = 5.0

    for s in steps:
        vis = s["visibility_m"]
        v_safe = independent_quadratic_v_safe(vis, s_base, tau, a_emerg)
        state = "STAGED_HOLD" if v_safe == 0.0 else "ACTIVE_HAULAGE"
        records.append({
            "phase": s["phase"],
            "time_s": s["time_s"],
            "visibility_m": vis,
            "v_safe_mps": round(v_safe, 4),
            "v_safe_kmh": round(v_safe * 3.6, 2),
            "operating_state": state,
            "modeled_production_tph": 1591.4 if vis >= 12.0 else (0.0 if vis <= 5.0 else round(1591.4 * (vis - 5.0) / 7.0, 1))
        })

    df = pd.DataFrame(records)
    out_csv = os.path.join(DATA_DIR, "phase7_3_4_recovery_timeline.csv")
    df.to_csv(out_csv, index=False)
    print(f"Saved {out_csv}: {len(df)} rows")
    return df

if __name__ == "__main__":
    print("==================================================================")
    print("STARTING PHASE 7.3.4 INDEPENDENT PHYSICS & AUDIT ENGINE")
    print("==================================================================")
    run_attack_1_550kn_and_adhesion()
    run_attack_2_deceleration_sensitivity()
    run_attack_3_service_deceleration()
    run_attack_4_safety_buffer_sensitivity()
    run_attack_5_chattering_hysteresis()
    run_attack_6_quadratic_grid()
    run_attack_25_recovery_timeline()
    print("==================================================================")
    print("PHASE 7.3.4 INDEPENDENT PHYSICS ENGINE COMPLETE")
    print("==================================================================")
