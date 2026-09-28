"""
Scenarios & Test Suite Execution for Tests 1 through 12.
"""

import numpy as np
import pandas as pd

from fog_safe.config import VehicleParameters, EnvironmentParameters, SiteParameters
from fog_safe.vehicle import MiningVehicle
from fog_safe.road import RoadSegment
from fog_safe.environment import EnvironmentState
from fog_safe.communication import CommunicationModel
from fog_safe.braking import calculate_stopping_distance, calculate_effective_deceleration
from fog_safe.retarder import calculate_retarder_speed_limit
from fog_safe.safety import solve_safe_speed, calculate_v_stop
from fog_safe.headway import calculate_safe_headway
from fog_safe.rls import RecursiveFrictionEstimator, analyze_identifiability_failure
from fog_safe.simulator import DynamicSimulator

def run_test_1_basic_sanity() -> pd.DataFrame:
    """Test 1: Basic Sanity Check on flat road."""
    vehicle = MiningVehicle()
    road = RoadSegment(percent_grade=0.0)
    env = EnvironmentState(r_effective=30.0, mu_true=0.40)
    comm = CommunicationModel(c_comm=1.0)

    records = []
    speeds_kmh = [10.0, 15.0, 20.0]
    frictions = [0.25, 0.40, 0.60]
    latencies = [0.4, 0.8, 1.5]

    for v_kmh in speeds_kmh:
        for mu in frictions:
            for tau in latencies:
                v_ms = v_kmh / 3.6
                d_react, d_brake, s_stop = calculate_stopping_distance(vehicle, road, env, mu, v_ms, tau)
                records.append({
                    "speed_kmh": v_kmh,
                    "friction_mu": mu,
                    "latency_tau_s": tau,
                    "d_reaction_m": d_react,
                    "d_brake_m": d_brake,
                    "s_stop_m": s_stop
                })

    df = pd.DataFrame(records)
    return df

def run_test_2_grade_sanity() -> pd.DataFrame:
    """Test 2: Grade Sanity Check (0%, 4%, 6.25%, 8%, 10% downhill)."""
    vehicle = MiningVehicle()
    env = EnvironmentState(r_effective=30.0, mu_true=0.35)
    comm = CommunicationModel(c_comm=1.0)
    grades = [0.0, 4.0, 6.25, 8.0, 10.0]

    records = []
    for g in grades:
        road = RoadSegment(percent_grade=g)
        res = solve_safe_speed(vehicle, road, env, comm, mu_effective=env.mu_true)
        a_dec = calculate_effective_deceleration(vehicle, road, env, mu=env.mu_true, v=res.v_safe_ms)
        records.append({
            "percent_grade": g,
            "a_dec_ms2": a_dec,
            "v_stop_kmh": res.candidate_limits_kmh["v_stop"],
            "v_retarder_kmh": res.candidate_limits_kmh["v_retarder"],
            "v_safe_kmh": res.v_safe_kmh,
            "s_stop_m": res.s_stop,
            "s_margin_m": res.s_margin,
            "primary_constraint": res.primary_constraint
        })

    df = pd.DataFrame(records)
    return df

def run_test_3_friction_sanity() -> pd.DataFrame:
    """Test 3: Friction Sanity Check (mu = 0.20 to 0.80)."""
    vehicle = MiningVehicle()
    road = RoadSegment(percent_grade=6.25)
    env = EnvironmentState(r_effective=30.0)
    comm = CommunicationModel(c_comm=1.0)
    frictions = [0.20, 0.30, 0.40, 0.50, 0.60, 0.80]

    records = []
    for mu in frictions:
        res = solve_safe_speed(vehicle, road, env, comm, mu_effective=mu)
        records.append({
            "friction_mu": mu,
            "a_dec_ms2": res.a_dec,
            "v_safe_kmh": res.v_safe_kmh,
            "s_stop_m": res.s_stop,
            "primary_constraint": res.primary_constraint
        })

    df = pd.DataFrame(records)
    return df

def run_test_4_visibility_sanity() -> pd.DataFrame:
    """Test 4: Visibility Sanity Check (R_effective = 50m down to 5m)."""
    vehicle = MiningVehicle()
    road = RoadSegment(percent_grade=6.25)
    env = EnvironmentState(mu_true=0.35)
    comm = CommunicationModel(c_comm=1.0)
    visibilities = [50.0, 30.0, 20.0, 15.0, 10.0, 5.0]

    records = []
    for r in visibilities:
        env.r_effective = r
        res = solve_safe_speed(vehicle, road, env, comm, mu_effective=env.mu_true, r_effective=r)
        records.append({
            "r_effective_m": r,
            "v_safe_kmh": res.v_safe_kmh,
            "v_stop_kmh": res.candidate_limits_kmh["v_stop"],
            "s_stop_m": res.s_stop,
            "s_margin_m": res.s_margin,
            "primary_constraint": res.primary_constraint,
            "is_safe": res.is_safe
        })

    df = pd.DataFrame(records)
    return df

def run_test_5_latency_sanity() -> pd.DataFrame:
    """Test 5: Latency Sanity Check (tau = 0.1s to 3.0s)."""
    vehicle = MiningVehicle()
    road = RoadSegment(percent_grade=6.25)
    env = EnvironmentState(r_effective=30.0, mu_true=0.35)
    latencies = [0.1, 0.25, 0.5, 1.0, 2.0, 3.0]

    records = []
    for tau in latencies:
        # Custom comm object overriding total latency
        comm = CommunicationModel(c_comm=1.0)
        comm.rx_params.tau_human = tau - (comm.rx_params.tau_sensor + comm.rx_params.tau_comm_base + comm.rx_params.tau_decision)
        res = solve_safe_speed(vehicle, road, env, comm, mu_effective=env.mu_true)
        records.append({
            "tau_total_s": tau,
            "v_safe_kmh": res.v_safe_kmh,
            "s_stop_m": res.s_stop,
            "primary_constraint": res.primary_constraint
        })

    df = pd.DataFrame(records)
    return df

def run_test_6_retarder_check() -> pd.DataFrame:
    """Test 6: Retarder Power Capability Check."""
    road = RoadSegment(percent_grade=8.0)
    env = EnvironmentState(r_effective=50.0, mu_true=0.40)
    powers_kw = [600.0, 800.0, 1000.0, 1200.0, 1400.0, 1600.0]

    records = []
    for p_kw in powers_kw:
        v_params = VehicleParameters(retarder_power_max=p_kw * 1000.0)
        vehicle = MiningVehicle(params=v_params)
        v_ret_ms = calculate_retarder_speed_limit(vehicle, road, env)
        records.append({
            "retarder_power_kw": p_kw,
            "v_retarder_kmh": v_ret_ms * 3.6
        })

    df = pd.DataFrame(records)
    return df

def run_test_7_combined_worst_case() -> dict:
    """Test 7: Combined Worst-Case Scenario."""
    # Loaded truck, 8% downhill, wet road mu=0.25, R_eff=10m, high latency tau=1.5s
    v_params = VehicleParameters(retarder_power_max=800000.0) # 800 kW
    vehicle = MiningVehicle(params=v_params, is_loaded=True)
    road = RoadSegment(percent_grade=8.0)
    env = EnvironmentState(r_effective=10.0, mu_true=0.25)
    comm = CommunicationModel(c_comm=0.5) # degraded comm
    comm.rx_params.tau_human = 1.0 # 1.5s total latency

    res = solve_safe_speed(vehicle, road, env, comm, mu_effective=env.mu_true)

    return {
        "scenario": "Combined Worst Case",
        "mass_kg": vehicle.mass,
        "grade_pct": road.percent_grade,
        "mu": env.mu_true,
        "r_effective_m": env.r_effective,
        "tau_total_s": comm.tau_total,
        "v_stop_kmh": res.candidate_limits_kmh["v_stop"],
        "v_retarder_kmh": res.candidate_limits_kmh["v_retarder"],
        "v_traction_kmh": res.candidate_limits_kmh["v_traction"],
        "v_safe_kmh": res.v_safe_kmh,
        "primary_constraint": res.primary_constraint,
        "is_safe": res.is_safe
    }

def run_test_8_rls_estimation() -> pd.DataFrame:
    """Test 8: RLS Friction Estimation Convergence."""
    vehicle = MiningVehicle()
    road = RoadSegment(percent_grade=4.0)
    env = EnvironmentState(mu_true=0.35)

    estimator = RecursiveFrictionEstimator(mu_init=0.50, P_init=0.04)

    records = []
    np.random.seed(42)

    # 30 braking/coasting observation events
    for step in range(30):
        v = 4.0 # m/s
        # Measure acceleration with noise
        a_x_true = -0.5 # m/s^2 deceleration
        a_x_meas = a_x_true + np.random.normal(0.0, 0.05)

        mu_meas = estimator.calculate_inverse_mu(vehicle, road, env, v, a_x_meas, f_retarder=0.0)
        mu_hat, sigma, mu_lower = estimator.update(mu_meas)

        records.append({
            "step": step,
            "mu_true": env.mu_true,
            "mu_meas": mu_meas,
            "mu_hat": mu_hat,
            "sigma_mu": sigma,
            "mu_lower": mu_lower
        })

    df = pd.DataFrame(records)
    return df

def run_test_9_identifiability() -> dict:
    """Test 9: Identifiability Failure Test."""
    vehicle = MiningVehicle()
    road = RoadSegment(percent_grade=6.25)
    env = EnvironmentState(mu_true=0.35)

    v = 4.0 # m/s
    a_x_true = -0.8 # m/s^2 deceleration
    unknown_retarder_force = 150000.0 # 150 kN unmeasured retarding force

    return analyze_identifiability_failure(vehicle, road, env, v, a_x_true, unknown_retarder_force)

def run_test_10_comm_failure() -> pd.DataFrame:
    """Test 10: Communication Failure & Degradation."""
    vehicle = MiningVehicle()
    road = RoadSegment(percent_grade=4.0)
    env = EnvironmentState(r_effective=30.0, mu_true=0.35)
    c_comms = [1.0, 0.75, 0.50, 0.25, 0.0]

    records = []
    for c_c in c_comms:
        comm = CommunicationModel(c_comm=c_c)
        res = solve_safe_speed(vehicle, road, env, comm, mu_effective=env.mu_true)
        h_safe, t_headway = calculate_safe_headway(
            v_follower=res.v_safe_ms,
            v_leader=res.v_safe_ms,
            a_follower=res.a_dec,
            a_leader=res.a_dec,
            tau_total=comm.tau_total,
            s_margin=res.s_margin
        )

        records.append({
            "c_comm": c_c,
            "tau_total_s": comm.tau_total,
            "s_margin_m": res.s_margin,
            "v_safe_kmh": res.v_safe_kmh,
            "h_safe_m": h_safe,
            "t_headway_s": t_headway
        })

    df = pd.DataFrame(records)
    return df

def run_test_11_monte_carlo(num_samples: int = 1000) -> pd.DataFrame:
    """Test 11: Monte Carlo Uncertainty Analysis (1000+ samples)."""
    np.random.seed(123)

    records = []
    vehicle_base = MiningVehicle()
    road_base = RoadSegment()
    env_base = EnvironmentState()

    for i in range(num_samples):
        # Sample randomized parameters
        mass = np.random.uniform(74000.0, 165000.0) # mass range
        grade = np.random.uniform(0.0, 10.0) # downhill grade %
        mu = np.random.uniform(0.20, 0.70) # friction
        c_rr = np.random.uniform(0.015, 0.035) # rolling resistance
        r_eff = np.random.uniform(10.0, 50.0) # perception range
        tau_human = np.random.uniform(0.2, 1.2) # human latency
        c_comm = np.random.uniform(0.2, 1.0) # comm quality

        vehicle = MiningVehicle(params=VehicleParameters(mass_loaded=mass), is_loaded=True)
        road = RoadSegment(percent_grade=grade, c_rr=c_rr)
        env = EnvironmentState(r_effective=r_eff, mu_true=mu)
        comm = CommunicationModel(c_comm=c_comm)
        comm.rx_params.tau_human = tau_human

        res = solve_safe_speed(vehicle, road, env, comm, mu_effective=mu)
        h_safe, _ = calculate_safe_headway(res.v_safe_ms, res.v_safe_ms, res.a_dec, res.a_dec, comm.tau_total, res.s_margin)

        records.append({
            "sample_id": i,
            "mass_kg": mass,
            "grade_pct": grade,
            "mu": mu,
            "c_rr": c_rr,
            "r_effective_m": r_eff,
            "tau_total_s": comm.tau_total,
            "v_safe_kmh": res.v_safe_kmh,
            "s_stop_m": res.s_stop,
            "h_safe_m": h_safe,
            "is_safe": res.is_safe,
            "primary_constraint": res.primary_constraint
        })

    df = pd.DataFrame(records)
    return df

def run_test_12_baseline_vs_fog_safe() -> tuple[pd.DataFrame, dict]:
    """Test 12: Baseline Static Policy vs FOG-SAFE Dynamic Policy Comparison."""
    vehicle = MiningVehicle()
    road = RoadSegment(percent_grade=6.25)
    env = EnvironmentState()
    comm = CommunicationModel()

    sim = DynamicSimulator(vehicle, road, env, comm, dt=0.5)

    def visibility_profile(t):
        # Continuous physical fog entry transition between t=95s and t=100s
        if t < 95.0:
            return 40.0
        elif t <= 100.0:
            return 40.0 - (40.0 - 15.0) * ((t - 95.0) / 5.0)
        elif t <= 400.0:
            return 15.0
        elif t <= 405.0:
            return 15.0 + (40.0 - 15.0) * ((t - 400.0) / 5.0)
        else:
            return 40.0

    def friction_profile(t):
        if t < 195.0:
            return 0.40
        elif t <= 200.0:
            return 0.40 - (0.40 - 0.25) * ((t - 195.0) / 5.0)
        elif t <= 350.0:
            return 0.25
        elif t <= 355.0:
            return 0.25 + (0.40 - 0.25) * ((t - 350.0) / 5.0)
        else:
            return 0.40

    def comm_profile(t):
        if t < 295.0:
            return 1.0
        elif t <= 300.0:
            return 1.0 - (1.0 - 0.3) * ((t - 295.0) / 5.0)
        elif t <= 380.0:
            return 0.3
        elif t <= 385.0:
            return 0.3 + (1.0 - 0.3) * ((t - 380.0) / 5.0)
        else:
            return 1.0

    duration = 600.0 # 10 minutes

    traj_fog_safe = sim.run_timeline_scenario(duration, visibility_profile, friction_profile, comm_profile, policy_type="FOG_SAFE")
    traj_static = sim.run_timeline_scenario(duration, visibility_profile, friction_profile, comm_profile, policy_type="STATIC_CONSERVATIVE")

    df_fog_safe = pd.DataFrame([{
        "t": s.t, "speed_kmh": s.speed * 3.6, "v_safe_kmh": s.v_safe_result.v_safe_kmh,
        "r_effective": s.r_effective, "mu": s.mu_true, "violation": s.safety_violation, "position": s.position
    } for s in traj_fog_safe])

    df_static = pd.DataFrame([{
        "t": s.t, "speed_kmh": s.speed * 3.6, "v_safe_kmh": s.v_safe_result.v_safe_kmh,
        "r_effective": s.r_effective, "mu": s.mu_true, "violation": s.safety_violation, "position": s.position
    } for s in traj_static])

    summary = {
        "fog_safe_dist_km": df_fog_safe["position"].iloc[-1] / 1000.0,
        "static_dist_km": df_static["position"].iloc[-1] / 1000.0,
        "fog_safe_avg_speed_kmh": df_fog_safe["speed_kmh"].mean(),
        "static_avg_speed_kmh": df_static["speed_kmh"].mean(),
        "fog_safe_violations": int(df_fog_safe["violation"].sum()),
        "static_violations": int(df_static["violation"].sum()),
        "throughput_improvement_pct": ((df_fog_safe["position"].iloc[-1] - df_static["position"].iloc[-1]) / df_static["position"].iloc[-1]) * 100.0
    }

    return pd.concat([df_fog_safe.assign(policy="FOG_SAFE"), df_static.assign(policy="STATIC_CONSERVATIVE")]), summary
