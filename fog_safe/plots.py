"""
High-Resolution Chart Generator for all 14 required FOG-SAFE visual plots.
Uses publication-quality styling with Matplotlib.
"""

import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker

# Configure clean aesthetic style
plt.style.use('seaborn-v0_8-darkgrid' if 'seaborn-v0_8-darkgrid' in plt.style.available else 'default')
plt.rcParams['font.sans-serif'] = 'DejaVu Sans'
plt.rcParams['axes.edgecolor'] = '#cccccc'
plt.rcParams['axes.linewidth'] = 1.0

def generate_all_plots(output_dir: str = "plots"):
    """Generates and saves all 14 required visual figures to output_dir."""
    os.makedirs(output_dir, exist_ok=True)

    from fog_safe.vehicle import MiningVehicle
    from fog_safe.road import RoadSegment
    from fog_safe.environment import EnvironmentState
    from fog_safe.communication import CommunicationModel
    from fog_safe.braking import calculate_stopping_distance
    from fog_safe.safety import solve_safe_speed
    from fog_safe.retarder import calculate_retarder_speed_limit
    from fog_safe.headway import calculate_safe_headway
    from fog_safe.scenarios import (
        run_test_8_rls_estimation,
        run_test_11_monte_carlo,
        run_test_12_baseline_vs_fog_safe
    )

    vehicle = MiningVehicle()
    env = EnvironmentState()
    comm = CommunicationModel()

    # -------------------------------------------------------------
    # Plot 1: Stopping Distance vs Speed
    # -------------------------------------------------------------
    fig, ax = plt.subplots(figsize=(8, 5))
    speeds_kmh = np.linspace(2.0, 30.0, 100)
    for mu, col in [(0.25, '#e74c3c'), (0.35, '#e67e22'), (0.50, '#2ecc71')]:
        road = RoadSegment(percent_grade=6.25)
        s_stops = []
        for v_k in speeds_kmh:
            v_m = v_k / 3.6
            _, _, s = calculate_stopping_distance(vehicle, road, env, mu, v_m, comm.tau_total)
            s_stops.append(s)
        ax.plot(speeds_kmh, s_stops, label=f'Friction $\\mu$ = {mu}', color=col, linewidth=2)

    ax.set_title('1. Stopping Distance vs Operating Speed (Grade = 6.25%)', fontsize=12, fontweight='bold')
    ax.set_xlabel('Vehicle Speed (km/h)', fontsize=10)
    ax.set_ylabel('Total Stopping Distance $S_{stop}$ (m)', fontsize=10)
    ax.legend(frameon=True)
    ax.set_ylim(0, 100)
    plt.tight_layout()
    fig.savefig(os.path.join(output_dir, '01_stopping_distance_vs_speed.png'), dpi=200)
    plt.close(fig)

    # -------------------------------------------------------------
    # Plot 2: Safe Speed vs Visibility
    # -------------------------------------------------------------
    fig, ax = plt.subplots(figsize=(8, 5))
    vis_range = np.linspace(5.0, 60.0, 100)
    for g, col in [(0.0, '#3498db'), (6.25, '#f39c12'), (10.0, '#e74c3c')]:
        road = RoadSegment(percent_grade=g)
        v_safes = [solve_safe_speed(vehicle, road, env, comm, mu_effective=0.35, r_effective=r).v_safe_kmh for r in vis_range]
        ax.plot(vis_range, v_safes, label=f'Downhill Grade {g}%', color=col, linewidth=2)

    ax.set_title('2. Safe Speed $v_{safe}$ vs Effective Perception Range $R_{effective}$', fontsize=12, fontweight='bold')
    ax.set_xlabel('Effective Perception Range $R_{effective}$ (m)', fontsize=10)
    ax.set_ylabel('Allowable Safe Speed $v_{safe}$ (km/h)', fontsize=10)
    ax.legend(frameon=True)
    ax.set_ylim(0, 25)
    plt.tight_layout()
    fig.savefig(os.path.join(output_dir, '02_safe_speed_vs_visibility.png'), dpi=200)
    plt.close(fig)

    # -------------------------------------------------------------
    # Plot 3: Safe Speed vs Grade
    # -------------------------------------------------------------
    fig, ax = plt.subplots(figsize=(8, 5))
    grade_range = np.linspace(0.0, 12.0, 100)
    for r, col in [(15.0, '#e74c3c'), (30.0, '#f39c12'), (50.0, '#2ecc71')]:
        v_safes = []
        for g in grade_range:
            road = RoadSegment(percent_grade=g)
            v_safes.append(solve_safe_speed(vehicle, road, env, comm, mu_effective=0.35, r_effective=r).v_safe_kmh)
        ax.plot(grade_range, v_safes, label=f'Visibility R = {r}m', color=col, linewidth=2)

    ax.set_title('3. Safe Speed $v_{safe}$ vs Downhill Road Grade (%)', fontsize=12, fontweight='bold')
    ax.set_xlabel('Downhill Grade (%)', fontsize=10)
    ax.set_ylabel('Allowable Safe Speed $v_{safe}$ (km/h)', fontsize=10)
    ax.legend(frameon=True)
    ax.set_ylim(0, 25)
    plt.tight_layout()
    fig.savefig(os.path.join(output_dir, '03_safe_speed_vs_grade.png'), dpi=200)
    plt.close(fig)

    # -------------------------------------------------------------
    # Plot 4: Safe Speed vs Friction
    # -------------------------------------------------------------
    fig, ax = plt.subplots(figsize=(8, 5))
    mu_range = np.linspace(0.15, 0.80, 100)
    for r, col in [(15.0, '#e74c3c'), (30.0, '#3498db'), (50.0, '#9b59b6')]:
        road = RoadSegment(percent_grade=6.25)
        v_safes = [solve_safe_speed(vehicle, road, env, comm, mu_effective=mu, r_effective=r).v_safe_kmh for mu in mu_range]
        ax.plot(mu_range, v_safes, label=f'Visibility R = {r}m', color=col, linewidth=2)

    ax.set_title('4. Safe Speed $v_{safe}$ vs Tire-Road Friction Coefficient $\\mu$', fontsize=12, fontweight='bold')
    ax.set_xlabel('Friction Coefficient $\\mu$', fontsize=10)
    ax.set_ylabel('Allowable Safe Speed $v_{safe}$ (km/h)', fontsize=10)
    ax.legend(frameon=True)
    plt.tight_layout()
    fig.savefig(os.path.join(output_dir, '04_safe_speed_vs_friction.png'), dpi=200)
    plt.close(fig)

    # -------------------------------------------------------------
    # Plot 5: Safe-Speed Operating Envelope (2D Contour Plot)
    # -------------------------------------------------------------
    fig, ax = plt.subplots(figsize=(8, 6))
    G, M = np.meshgrid(np.linspace(0.0, 10.0, 50), np.linspace(0.20, 0.70, 50))
    Z = np.zeros_like(G)
    for i in range(G.shape[0]):
        for j in range(G.shape[1]):
            road = RoadSegment(percent_grade=G[i, j])
            Z[i, j] = solve_safe_speed(vehicle, road, env, comm, mu_effective=M[i, j], r_effective=25.0).v_safe_kmh

    contour = ax.contourf(G, M, Z, levels=12, cmap='viridis')
    cbar = fig.colorbar(contour, ax=ax)
    cbar.set_label('Safe Speed $v_{safe}$ (km/h)', fontsize=10)
    ax.set_title('5. Safe-Speed Operating Envelope Contour (R = 25m)', fontsize=12, fontweight='bold')
    ax.set_xlabel('Downhill Grade (%)', fontsize=10)
    ax.set_ylabel('Tire-Road Friction Coefficient $\\mu$', fontsize=10)
    plt.tight_layout()
    fig.savefig(os.path.join(output_dir, '05_safe_speed_operating_envelope.png'), dpi=200)
    plt.close(fig)

    # -------------------------------------------------------------
    # Plot 6: Friction Estimate vs True Friction
    # -------------------------------------------------------------
    df_rls = run_test_8_rls_estimation()
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.plot(df_rls['step'], df_rls['mu_true'], 'k--', label='True Friction $\\mu_{true}$ (0.35)', linewidth=2)
    ax.plot(df_rls['step'], df_rls['mu_meas'], 'r.', label='Noisy Inverse Measurements $\\mu_{meas}$', alpha=0.6)
    ax.plot(df_rls['step'], df_rls['mu_hat'], 'b-', label='RLS Estimate $\\hat{\\mu}$', linewidth=2)
    ax.fill_between(df_rls['step'], df_rls['mu_lower'], df_rls['mu_hat'] + 2*df_rls['sigma_mu'], color='blue', alpha=0.15, label='95% Confidence Band')

    ax.set_title('6. RLS Friction Estimator vs True Ground Truth', fontsize=12, fontweight='bold')
    ax.set_xlabel('Observation Step (Braking Events)', fontsize=10)
    ax.set_ylabel('Friction Coefficient $\\mu$', fontsize=10)
    ax.legend(frameon=True)
    plt.tight_layout()
    fig.savefig(os.path.join(output_dir, '06_friction_estimate_vs_true.png'), dpi=200)
    plt.close(fig)

    # -------------------------------------------------------------
    # Plot 7: RLS Uncertainty Convergence
    # -------------------------------------------------------------
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.plot(df_rls['step'], df_rls['sigma_mu'], 'm-o', label='Uncertainty $\\sigma_{\\mu}$', linewidth=2)
    ax.plot(df_rls['step'], df_rls['mu_lower'], 'g-s', label='Safety-Critical Lower Bound $\\mu_{lower}$', linewidth=2)

    ax.set_title('7. RLS Estimation Uncertainty Convergence $\\sigma_{\\mu}$', fontsize=12, fontweight='bold')
    ax.set_xlabel('Observation Step', fontsize=10)
    ax.set_ylabel('Uncertainty / Bound Value', fontsize=10)
    ax.legend(frameon=True)
    plt.tight_layout()
    fig.savefig(os.path.join(output_dir, '07_rls_uncertainty_convergence.png'), dpi=200)
    plt.close(fig)

    # -------------------------------------------------------------
    # Plot 8: Safe Headway vs Communication Latency
    # -------------------------------------------------------------
    fig, ax = plt.subplots(figsize=(8, 5))
    tau_arr = np.linspace(0.2, 3.0, 50)
    road = RoadSegment(percent_grade=6.25)
    v_test = 15.0 / 3.6
    h_safes = []
    t_headways = []
    a_dec = 2.0
    for tau in tau_arr:
        h, t_h = calculate_safe_headway(v_test, v_test, a_dec, a_dec, tau, s_margin=5.0)
        h_safes.append(h)
        t_headways.append(t_h)

    ax.plot(tau_arr, h_safes, 'b-', label='Safe Headway Distance $H_{safe}$ (m)', linewidth=2)
    ax2 = ax.twinx()
    ax2.plot(tau_arr, t_headways, 'r--', label='Time Headway $T_{headway}$ (s)', linewidth=2)
    ax2.grid(False)

    ax.set_title('8. Safe Headway vs Reaction & Perception Latency $\\tau_{total}$', fontsize=12, fontweight='bold')
    ax.set_xlabel('Total Latency $\\tau_{total}$ (s)', fontsize=10)
    ax.set_ylabel('Headway Distance $H_{safe}$ (m)', color='b', fontsize=10)
    ax2.set_ylabel('Time Headway $T_{headway}$ (s)', color='r', fontsize=10)
    plt.tight_layout()
    fig.savefig(os.path.join(output_dir, '08_safe_headway_vs_latency.png'), dpi=200)
    plt.close(fig)

    # -------------------------------------------------------------
    # Plot 9: Safe Speed vs Communication Quality Index C_comm
    # -------------------------------------------------------------
    fig, ax = plt.subplots(figsize=(8, 5))
    c_comm_arr = np.linspace(0.0, 1.0, 50)
    road = RoadSegment(percent_grade=6.25)
    v_safes_comm = []
    margins = []
    for c_c in c_comm_arr:
        comm_obj = CommunicationModel(c_comm=c_c)
        res = solve_safe_speed(vehicle, road, env, comm_obj, mu_effective=0.35, r_effective=25.0)
        v_safes_comm.append(res.v_safe_kmh)
        margins.append(res.s_margin)

    ax.plot(c_comm_arr, v_safes_comm, '#16a085', label='Safe Speed $v_{safe}$ (km/h)', linewidth=2)
    ax.set_title('9. Safe Speed & Adaptive Margin vs Comm Quality $C_{comm}$', fontsize=12, fontweight='bold')
    ax.set_xlabel('Communication Quality Index $C_{comm}$ (1.0=Perfect, 0.0=Lost)', fontsize=10)
    ax.set_ylabel('Safe Speed (km/h)', fontsize=10)
    ax.legend(frameon=True)
    plt.tight_layout()
    fig.savefig(os.path.join(output_dir, '09_safe_speed_vs_comm_confidence.png'), dpi=200)
    plt.close(fig)

    # -------------------------------------------------------------
    # Plot 10: Baseline vs FOG-SAFE Policy Comparison
    # -------------------------------------------------------------
    df_comp, summary_comp = run_test_12_baseline_vs_fog_safe()
    fig, ax = plt.subplots(figsize=(9, 5))
    df_fs = df_comp[df_comp['policy'] == 'FOG_SAFE']
    df_st = df_comp[df_comp['policy'] == 'STATIC_CONSERVATIVE']

    ax.plot(df_fs['t'], df_fs['speed_kmh'], '#27ae60', label='FOG-SAFE Dynamic Policy', linewidth=2)
    ax.plot(df_st['t'], df_st['speed_kmh'], '#7f8c8d', label='Static Conservative Policy (10 km/h)', linewidth=2, linestyle='--')
    ax.plot(df_fs['t'], df_fs['v_safe_kmh'], 'r:', label='Dynamic Physical Limit $v_{safe}$', linewidth=1.5)

    ax.set_title('10. Operating Speed Timeline: FOG-SAFE vs Static Policy', fontsize=12, fontweight='bold')
    ax.set_xlabel('Time (seconds)', fontsize=10)
    ax.set_ylabel('Vehicle Speed (km/h)', fontsize=10)
    ax.legend(frameon=True)
    plt.tight_layout()
    fig.savefig(os.path.join(output_dir, '10_baseline_vs_fog_safe_throughput.png'), dpi=200)
    plt.close(fig)

    # -------------------------------------------------------------
    # Plot 11: Monte Carlo Safe-Speed Distribution
    # -------------------------------------------------------------
    df_mc = run_test_11_monte_carlo(num_samples=1000)
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.hist(df_mc['v_safe_kmh'], bins=30, color='#2980b9', edgecolor='black', alpha=0.7)
    ax.set_title('11. Monte Carlo Safe-Speed Distribution (1000 Samples)', fontsize=12, fontweight='bold')
    ax.set_xlabel('Safe Speed $v_{safe}$ (km/h)', fontsize=10)
    ax.set_ylabel('Sample Frequency', fontsize=10)

    p5 = np.percentile(df_mc['v_safe_kmh'], 5)
    mean_v = df_mc['v_safe_kmh'].mean()
    ax.axvline(p5, color='red', linestyle='--', linewidth=2, label=f'5th Percentile: {p5:.1f} km/h')
    ax.axvline(mean_v, color='green', linestyle='-', linewidth=2, label=f'Mean: {mean_v:.1f} km/h')
    ax.legend(frameon=True)
    plt.tight_layout()
    fig.savefig(os.path.join(output_dir, '11_monte_carlo_safe_speed_distribution.png'), dpi=200)
    plt.close(fig)

    # -------------------------------------------------------------
    # Plot 12: Monte Carlo Stopping-Distance Distribution
    # -------------------------------------------------------------
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.hist(df_mc['s_stop_m'], bins=30, color='#8e44ad', edgecolor='black', alpha=0.7)
    ax.set_title('12. Monte Carlo Stopping-Distance Distribution $S_{stop}$', fontsize=12, fontweight='bold')
    ax.set_xlabel('Stopping Distance $S_{stop}$ (m)', fontsize=10)
    ax.set_ylabel('Sample Frequency', fontsize=10)
    p95 = np.percentile(df_mc['s_stop_m'], 95)
    ax.axvline(p95, color='orange', linestyle='--', linewidth=2, label=f'95th Percentile: {p95:.1f} m')
    ax.legend(frameon=True)
    plt.tight_layout()
    fig.savefig(os.path.join(output_dir, '12_monte_carlo_stopping_distance_distribution.png'), dpi=200)
    plt.close(fig)

    # -------------------------------------------------------------
    # Plot 13: Active Constraint Map
    # -------------------------------------------------------------
    fig, ax = plt.subplots(figsize=(9, 5))
    vis_pts = [10.0, 20.0, 30.0, 40.0, 50.0]
    grades_pts = [0.0, 4.0, 6.25, 8.0, 10.0]

    matrix_active = []
    for g in grades_pts:
        row = []
        for r in vis_pts:
            rd = RoadSegment(percent_grade=g)
            res = solve_safe_speed(vehicle, rd, env, comm, mu_effective=0.35, r_effective=r)
            row.append(res.primary_constraint)
        matrix_active.append(row)

    # Plot candidate curves for 6.25% grade across visibility
    rd = RoadSegment(percent_grade=6.25)
    v_stops = [solve_safe_speed(vehicle, rd, env, comm, mu_effective=0.35, r_effective=r).candidate_limits_kmh['v_stop'] for r in vis_pts]
    v_rets = [solve_safe_speed(vehicle, rd, env, comm, mu_effective=0.35, r_effective=r).candidate_limits_kmh['v_retarder'] for r in vis_pts]
    v_mines = [20.0]*len(vis_pts)

    ax.plot(vis_pts, v_stops, 'r-o', label='Stopping Limit $v_{stop}$', linewidth=2)
    ax.plot(vis_pts, v_rets, 'b-s', label='Retarder Limit $v_{retarder}$', linewidth=2)
    ax.plot(vis_pts, v_mines, 'k--', label='Site Speed Limit $v_{mine}$', linewidth=1.5)
    ax.set_title('13. Active Constraint Map: Stopping vs Retarder vs Site Limits (6.25% Grade)', fontsize=12, fontweight='bold')
    ax.set_xlabel('Perception Range $R_{effective}$ (m)', fontsize=10)
    ax.set_ylabel('Speed Limit (km/h)', fontsize=10)
    ax.legend(frameon=True)
    plt.tight_layout()
    fig.savefig(os.path.join(output_dir, '13_active_constraint_map.png'), dpi=200)
    plt.close(fig)

    # -------------------------------------------------------------
    # Plot 14: Worst-Case Scenario Timeline
    # -------------------------------------------------------------
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(9, 7), sharex=True)

    t_axis = df_fs['t']
    ax1.plot(t_axis, df_fs['r_effective'], 'g-', label='Visibility $R_{effective}$ (m)', linewidth=2)
    ax1.plot(t_axis, df_fs['mu'] * 100.0, 'b--', label='Friction $\\mu \\times 100$', linewidth=1.5)
    ax1.set_ylabel('Environment Signals', fontsize=10)
    ax1.set_title('14. Worst-Case Dynamic Scenario Timeline (Fog + Wet Patch + Comm Loss)', fontsize=12, fontweight='bold')
    ax1.legend(loc='upper right', frameon=True)

    ax2.plot(t_axis, df_fs['speed_kmh'], 'b-', label='Vehicle Speed (km/h)', linewidth=2)
    ax2.plot(t_axis, df_fs['v_safe_kmh'], 'r--', label='Safe Speed Limit $v_{safe}$ (km/h)', linewidth=2)
    ax2.set_xlabel('Time (s)', fontsize=10)
    ax2.set_ylabel('Speed (km/h)', fontsize=10)
    ax2.legend(loc='upper right', frameon=True)

    plt.tight_layout()
    fig.savefig(os.path.join(output_dir, '14_worst_case_scenario_timeline.png'), dpi=200)
    plt.close(fig)

    print(f"Successfully generated all 14 visual plots in '{output_dir}/'.")
