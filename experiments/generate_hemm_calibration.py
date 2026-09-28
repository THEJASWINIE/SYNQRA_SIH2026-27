"""
experiments/generate_hemm_calibration.py
-----------------------------------------
Deterministic Calibration Matrix & Sensitivity Analysis Generator
for FOG-ORCHESTRATOR 2.0 (SIH 2026-27).

Generates:
1. HEMM_CALIBRATION_MATRIX.csv (Comprehensive full-envelope 4,860-point sweep)
2. HEMM_SENSITIVITY_ANALYSIS.csv (Local sensitivity gradients & elasticities around nominal)
"""

import sys
import os
sys.path.insert(0, os.path.abspath("."))

import math
import numpy as np
import pandas as pd
from typing import Dict, List, Tuple

from fog_safe.vehicle import MiningVehicle
from fog_safe.road import RoadSegment
from fog_safe.environment import EnvironmentState
from fog_safe.communication import CommunicationModel
from fog_safe.braking import calculate_effective_deceleration, calculate_stopping_distance
from fog_safe.safety import solve_safe_speed
from fog_safe.headway import calculate_safe_headway
from integration_adapters.grade_adapter import GradeAdapter


def run_calibration_sweep() -> pd.DataFrame:
    """
    Executes the full multi-parameter calibration sweep:
    - Visibility: 100m, 50m, 25m, 12m, 10m, 8m, 5m, 4m, 3m
    - Grade: +8%, +5%, 0%, -5%, -8% (Civil convention)
    - Friction: Dry/High (0.65), Moderate (0.45), Wet (0.35), Low (0.20)
    - Vehicle Loading: Empty (74.0t), Medium (119.75t), Max (165.5t)
    - Reaction Time: Low (0.30s), Nominal (0.45s), High (1.20s)
    - Initial Speed: Low (3.0 m/s), Medium (5.56 m/s), High (11.11 m/s)
    """
    visibilities = [100.0, 50.0, 25.0, 12.0, 10.0, 8.0, 5.0, 4.0, 3.0]
    grades = [8.0, 5.0, 0.0, -5.0, -8.0]
    frictions = [("dry_high", 0.65), ("moderate", 0.45), ("wet", 0.35), ("low_friction", 0.20)]
    loadings = [("empty", 74000.0), ("medium", 119750.0), ("max_gross", 165500.0)]
    reaction_times = [("low", 0.300), ("nominal", 0.450), ("high_human", 1.200)]
    speeds = [("low", 3.00), ("medium_site", 5.56), ("high_max", 11.11)]

    records = []

    for vis in visibilities:
        for civil_g in grades:
            road = GradeAdapter.create_adapted_road_segment(civil_grade_pct=civil_g, speed_limit_kmh=20.0)
            for f_label, mu in frictions:
                for load_label, mass in loadings:
                    # Configure vehicle
                    v_params = MiningVehicle().params
                    v_params.mass_loaded = mass
                    v_params.mass_empty = mass
                    vehicle = MiningVehicle(params=v_params, is_loaded=True)

                    for tau_label, tau in reaction_times:
                        comm = CommunicationModel()
                        # Override reaction time
                        comm.rx_params.tau_sensor = tau
                        comm.rx_params.tau_comm_base = 0.0
                        comm.rx_params.tau_decision = 0.0
                        comm.rx_params.tau_human = 0.0

                        env = EnvironmentState(r_effective=vis, mu_true=mu)

                        # Solve safe speed under current conditions
                        if vis <= 5.0:
                            # Mandatory physical zero speed halt below 5m
                            v_safe = 0.0
                            limiting_constraint = "TIER_1_SAFETY_ZERO_SPEED_HALT"
                            a_dec_nominal = calculate_effective_deceleration(vehicle, road, env, mu, v=0.0)
                        else:
                            safe_res = solve_safe_speed(
                                vehicle,
                                road,
                                env,
                                comm,
                                mu_effective=mu,
                                r_effective=vis
                            )
                            v_safe = safe_res.v_safe_ms
                            limiting_constraint = safe_res.primary_constraint
                            a_dec_nominal = safe_res.a_dec

                        # Headway at v_safe
                        h_safe, _ = calculate_safe_headway(
                            v_follower=v_safe,
                            v_leader=v_safe,
                            a_follower=max(0.1, a_dec_nominal),
                            a_leader=max(0.1, a_dec_nominal),
                            tau_total=tau,
                            s_margin=5.0,
                            assume_brick_wall=True
                        )
                        # Add vehicle length (10.52m)
                        h_safe_total = h_safe + 10.52

                        for spd_label, v_init in speeds:
                            # Evaluate deceleration and stopping distance at initial speed
                            a_dec_init = calculate_effective_deceleration(vehicle, road, env, mu, v=v_init)
                            _, _, s_stop_init = calculate_stopping_distance(
                                vehicle, road, env, mu, v=v_init, tau_total=tau
                            )

                            records.append({
                                "visibility_m": vis,
                                "civil_grade_pct": civil_g,
                                "friction_label": f_label,
                                "friction_mu": mu,
                                "loading_label": load_label,
                                "mass_kg": mass,
                                "reaction_label": tau_label,
                                "reaction_time_s": tau,
                                "speed_label": spd_label,
                                "initial_speed_mps": v_init,
                                "deceleration_mps2": round(a_dec_init, 4),
                                "stopping_distance_m": round(s_stop_init, 4),
                                "safe_speed_mps": round(v_safe, 4),
                                "safe_speed_kmh": round(v_safe * 3.6, 2),
                                "safe_headway_m": round(h_safe_total, 4),
                                "limiting_constraint": limiting_constraint
                            })

    df = pd.DataFrame(records)
    return df


def run_sensitivity_analysis() -> pd.DataFrame:
    """
    Computes local sensitivity gradients (dY/dX) and elasticities ((dY/Y)/(dX/X))
    around the nominal operating baseline:
    - Visibility: 12.0 m
    - Grade: -8.0% (downhill)
    - Friction: 0.35 (wet ore)
    - Mass: 165,500 kg (fully loaded)
    - Reaction Time: 0.450 s
    - Initial Speed: 5.56 m/s
    """
    base_vis = 12.0
    base_grade = -8.0
    base_mu = 0.35
    base_mass = 165500.0
    base_tau = 0.450
    base_crr = 0.025
    base_fbrake = 550000.0

    def eval_system(vis, grade, mu, mass, tau, crr, fbrake):
        v_params = MiningVehicle().params
        v_params.mass_loaded = mass
        v_params.mass_empty = mass
        v_params.hardware_brake_max_force = fbrake
        vehicle = MiningVehicle(params=v_params, is_loaded=True)

        road = GradeAdapter.create_adapted_road_segment(civil_grade_pct=grade, c_rr=crr, speed_limit_kmh=20.0)
        env = EnvironmentState(r_effective=vis, mu_true=mu)
        comm = CommunicationModel()
        comm.rx_params.tau_sensor = tau
        comm.rx_params.tau_comm_base = 0.0
        comm.rx_params.tau_decision = 0.0
        comm.rx_params.tau_human = 0.0

        if vis <= 5.0:
            v_safe = 0.0
            a_dec = calculate_effective_deceleration(vehicle, road, env, mu, v=0.0)
        else:
            res = solve_safe_speed(vehicle, road, env, comm, mu_effective=mu, r_effective=vis)
            v_safe = res.v_safe_ms
            a_dec = res.a_dec

        _, _, s_stop = calculate_stopping_distance(vehicle, road, env, mu, v=5.56, tau_total=tau)
        h_safe, _ = calculate_safe_headway(v_safe, v_safe, max(0.1, a_dec), max(0.1, a_dec), tau, s_margin=5.0)
        return v_safe, s_stop, a_dec, h_safe + 10.52

    # Baseline values
    v_base, s_base, a_base, h_base = eval_system(
        base_vis, base_grade, base_mu, base_mass, base_tau, base_crr, base_fbrake
    )

    perturbations = [
        ("reaction_time_s", base_tau, 0.050, "tau", lambda d: eval_system(base_vis, base_grade, base_mu, base_mass, base_tau + d, base_crr, base_fbrake)),
        ("CAN_latency_assumed_s", 0.050, 0.020, "tau_CAN", lambda d: eval_system(base_vis, base_grade, base_mu, base_mass, base_tau + d, base_crr, base_fbrake)),
        ("visibility_m", base_vis, 1.0, "V", lambda d: eval_system(base_vis + d, base_grade, base_mu, base_mass, base_tau, base_crr, base_fbrake)),
        ("friction_mu", base_mu, 0.050, "mu", lambda d: eval_system(base_vis, base_grade, base_mu + d, base_mass, base_tau, base_crr, base_fbrake)),
        ("civil_grade_pct", base_grade, 1.0, "grade", lambda d: eval_system(base_vis, base_grade + d, base_mu, base_mass, base_tau, base_crr, base_fbrake)),
        ("gross_mass_kg", base_mass, 5000.0, "mass", lambda d: eval_system(base_vis, base_grade, base_mu, base_mass + d, base_tau, base_crr, base_fbrake)),
        ("rolling_resistance_crr", base_crr, 0.005, "c_rr", lambda d: eval_system(base_vis, base_grade, base_mu, base_mass, base_tau, base_crr + d, base_fbrake)),
        ("hardware_brake_force_n", base_fbrake, 25000.0, "f_brake", lambda d: eval_system(base_vis, base_grade, base_mu, base_mass, base_tau, base_crr, base_fbrake + d))
    ]

    sensitivity_rows = []

    for param_name, x0, dx, symbol, eval_fn in perturbations:
        v_plus, s_plus, a_plus, h_plus = eval_fn(dx)
        v_minus, s_minus, a_minus, h_minus = eval_fn(-dx)

        # Central difference derivatives
        dv_dx = (v_plus - v_minus) / (2 * dx)
        ds_dx = (s_plus - s_minus) / (2 * dx)
        da_dx = (a_plus - a_minus) / (2 * dx)
        dh_dx = (h_plus - h_minus) / (2 * dx)

        # Elasticities ((dY / Y0) / (dX / X0))
        elas_v = (dv_dx * (x0 / v_base)) if v_base > 0 else 0.0
        elas_s = (ds_dx * (x0 / s_base)) if s_base > 0 else 0.0
        elas_a = (da_dx * (x0 / a_base)) if a_base > 0 else 0.0
        elas_h = (dh_dx * (x0 / h_base)) if h_base > 0 else 0.0

        sensitivity_rows.append({
            "parameter": param_name,
            "nominal_value": x0,
            "delta_step": dx,
            "grad_v_safe": round(dv_dx, 4),
            "elasticity_v_safe": round(elas_v, 4),
            "grad_s_stop": round(ds_dx, 4),
            "elasticity_s_stop": round(elas_s, 4),
            "grad_a_dec": round(da_dx, 4),
            "elasticity_a_dec": round(elas_a, 4),
            "grad_h_safe": round(dh_dx, 4),
            "elasticity_h_safe": round(elas_h, 4)
        })

    df_sens = pd.DataFrame(sensitivity_rows)
    return df_sens


if __name__ == "__main__":
    print("Starting HEMM Calibration Sweep...")
    df_matrix = run_calibration_sweep()
    matrix_path = "HEMM_CALIBRATION_MATRIX.csv"
    exp_matrix_path = "experiments/hemm_calibration_matrix.csv"
    df_matrix.to_csv(matrix_path, index=False)
    df_matrix.to_csv(exp_matrix_path, index=False)
    print(f"Exported {len(df_matrix)} rows to {matrix_path} and {exp_matrix_path}")

    print("Starting HEMM Sensitivity Analysis...")
    df_sens = run_sensitivity_analysis()
    sens_path = "HEMM_SENSITIVITY_ANALYSIS.csv"
    exp_sens_path = "experiments/hemm_sensitivity_analysis.csv"
    df_sens.to_csv(sens_path, index=False)
    df_sens.to_csv(exp_sens_path, index=False)
    print(f"Exported {len(df_sens)} sensitivity parameters to {sens_path} and {exp_sens_path}")
    print("\nSensitivity Summary:")
    print(df_sens[["parameter", "nominal_value", "elasticity_v_safe", "elasticity_s_stop", "elasticity_a_dec"]])
