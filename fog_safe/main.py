"""
FOG-SAFE Main CLI Orchestrator:
Executes formal validation, runs Tests 1-12, exports CSVs, generates plots, and writes machine-readable JSON summary.
"""

import os
import json
import pandas as pd
import numpy as np

from fog_safe.validation import run_formal_validation_suite
from fog_safe.scenarios import (
    run_test_1_basic_sanity,
    run_test_2_grade_sanity,
    run_test_3_friction_sanity,
    run_test_4_visibility_sanity,
    run_test_5_latency_sanity,
    run_test_6_retarder_check,
    run_test_7_combined_worst_case,
    run_test_8_rls_estimation,
    run_test_9_identifiability,
    run_test_10_comm_failure,
    run_test_11_monte_carlo,
    run_test_12_baseline_vs_fog_safe
)
from fog_safe.plots import generate_all_plots
from fog_safe.metrics import compute_summary_statistics

def main():
    print("=" * 70)
    print(" FOG-SAFE: Physics-Constrained Safe-Speed & Headway Engine ")
    print(" Target: Open-Cast Iron Ore Mine Haulage (NMDC Reference) ")
    print("=" * 70)

    results_dir = "results"
    plots_dir = "plots"
    os.makedirs(results_dir, exist_ok=True)
    os.makedirs(plots_dir, exist_ok=True)

    # STEP 1: Formal Validation Suite
    print("\n[STEP 1/5] Running Formal Physical Validation Suite...")
    val_status = run_formal_validation_suite()
    print("Validation Suite Status:", val_status["overall_status"])

    # STEP 2: Scenario Suite (Tests 1-12)
    print("\n[STEP 2/5] Running Scenario Suite (Tests 1 - 12)...")
    df_t1 = run_test_1_basic_sanity()
    df_t1.to_csv(os.path.join(results_dir, "test1_basic_sanity.csv"), index=False)

    df_t2 = run_test_2_grade_sanity()
    df_t2.to_csv(os.path.join(results_dir, "test2_grade_sanity.csv"), index=False)

    df_t3 = run_test_3_friction_sanity()
    df_t3.to_csv(os.path.join(results_dir, "test3_friction_sanity.csv"), index=False)

    df_t4 = run_test_4_visibility_sanity()
    df_t4.to_csv(os.path.join(results_dir, "test4_visibility_sanity.csv"), index=False)

    df_t5 = run_test_5_latency_sanity()
    df_t5.to_csv(os.path.join(results_dir, "test5_latency_sanity.csv"), index=False)

    df_t6 = run_test_6_retarder_check()
    df_t6.to_csv(os.path.join(results_dir, "test6_retarder_check.csv"), index=False)

    res_t7 = run_test_7_combined_worst_case()

    df_t8 = run_test_8_rls_estimation()
    df_t8.to_csv(os.path.join(results_dir, "test8_rls_estimation.csv"), index=False)

    res_t9 = run_test_9_identifiability()

    df_t10 = run_test_10_comm_failure()
    df_t10.to_csv(os.path.join(results_dir, "test10_comm_failure.csv"), index=False)

    df_t11 = run_test_11_monte_carlo(num_samples=1000)
    df_t11.to_csv(os.path.join(results_dir, "test11_monte_carlo.csv"), index=False)

    df_t12, res_t12 = run_test_12_baseline_vs_fog_safe()
    df_t12.to_csv(os.path.join(results_dir, "test12_policy_comparison.csv"), index=False)

    # STEP 3: Plot Generation
    print("\n[STEP 3/5] Generating 14 Visual Plot Figures...")
    generate_all_plots(output_dir=plots_dir)

    # STEP 4: Summary JSON Generation
    print("\n[STEP 4/5] Synthesizing JSON Summary Results...")
    mc_v_stats = compute_summary_statistics(df_t11["v_safe_kmh"])
    mc_s_stats = compute_summary_statistics(df_t11["s_stop_m"])

    summary_data = {
        "project": "FOG-SAFE Physics-Constrained Safe-Speed Optimization",
        "reference_vehicle": "BEML BH100 Mining Dumper",
        "operational_context": "NMDC Limited (BIOM-Kirandul, BIOM-Bacheli, Donimalai)",
        "validation_status": val_status["overall_status"],
        "key_metrics": {
            "test7_worst_case_v_safe_kmh": float(res_t7["v_safe_kmh"]),
            "test7_worst_case_is_safe": bool(res_t7["is_safe"]),
            "test9_identifiability_passed": bool(not res_t9["is_identifiable_from_ax_alone"]),
            "test11_mc_v_safe_mean_kmh": float(mc_v_stats["mean"]),
            "test11_mc_v_safe_p5_kmh": float(mc_v_stats["p5"]),
            "test11_mc_s_stop_p95_m": float(mc_s_stats["p95"]),
            "test12_throughput_improvement_pct": float(res_t12["throughput_improvement_pct"]),
            "test12_fog_safe_safety_violations": int(res_t12["fog_safe_violations"]),
            "test12_static_policy_safety_violations": int(res_t12["static_violations"])
        },
        "equations": {
            "longitudinal_dynamics": "m*dv/dt = F_drive + m*g*sin(theta) - C_rr*m*g*cos(theta) - 0.5*rho*Cd*A*v^2 - F_retarder - F_brake",
            "effective_deceleration": "a_dec = [ min(F_brake_max, mu*m*g*cos(theta)) + C_rr*m*g*cos(theta) + F_aero - m*g*sin(theta) ] / m",
            "safe_stopping_speed": "v_stop = -a_dec*tau + sqrt( a_dec^2*tau^2 + 2*a_dec*(R_effective - S_margin) )",
            "retarder_continuous_speed": "(m*g*sin(theta) - C_rr*m*g*cos(theta) - 0.5*rho*Cd*A*v^2)*v <= P_retarder_max",
            "safe_speed_optimizer": "v_safe = min(v_stop, v_retarder, v_traction, v_curve, v_mine)",
            "safe_headway": "H_safe = v_f*tau + v_f^2/(2*a_f) - v_l^2/(2*a_l) + S_margin",
            "inverse_friction_estimator": "mu_meas = [ g*sin(theta) - C_rr*g*cos(theta) - F_retarder/m - F_aero/m - a_x ] / [ g*cos(theta) ]"
        },
        "parameters": {
            "mass_empty_kg": 74000.0,
            "mass_loaded_kg": 165000.0,
            "payload_rated_kg": 91000.0,
            "retarder_power_max_kw": 1200.0,
            "mu_prior": 0.35,
            "c_rr_default": 0.02,
            "tau_total_default_s": 0.80,
            "v_mine_limit_kmh": 20.0
        },
        "limitations": [
            "Lateral dynamic rollover instability not fully coupled with longitudinal dynamic load transfer.",
            "Tire slip curve linearity assumed under transient brake onset.",
            "Friction estimation requires measured retarder torque and road grade input to remain identifiable."
        ]
    }

    with open("summary_results.json", "w") as f:
        json.dump(summary_data, f, indent=2)

    print("\n[STEP 5/5] Execution Complete!")
    print("Saved CSV results to 'results/'")
    print("Saved 14 plot figures to 'plots/'")
    print("Saved summary JSON to 'summary_results.json'")
    print("=" * 70)

if __name__ == "__main__":
    main()
