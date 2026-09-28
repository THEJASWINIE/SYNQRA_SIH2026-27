"""
experiments/run_stage3_robustness_and_sensitivity.py
----------------------------------------------------
STAGE 3 Multi-Seed Statistical Robustness & Parameter Sensitivity Analysis.
Runs 20 independent seeds across 7 control levels.
Conducts Tornado sensitivity analysis over 8 core parameters.
Generates:
  docs/STAGE3_MULTI_SEED_RESULTS.csv
  docs/STAGE3_FINAL_BENCHMARK.csv
  docs/STAGE3_SENSITIVITY_RESULTS.csv
"""

import os
import sys
import copy
import math
import yaml
import numpy as np
import pandas as pd
from typing import Dict, Any, List

WORKSPACE_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
TWIN_DIR = os.path.join(WORKSPACE_ROOT, "fog-orchester-3d-digital-twin")

if WORKSPACE_ROOT not in sys.path:
    sys.path.insert(0, WORKSPACE_ROOT)
if TWIN_DIR not in sys.path:
    sys.path.insert(0, TWIN_DIR)

from twin.network import MineNetwork
from twin.simulator import MineDigitalTwinSimulator
from optimizer.chance_mpc import ChanceConstrainedRHMPCDispatcher
from optimizer.milp_dispatch import DeterministicMILPDispatcher
from fog_safe.safety import solve_safe_speed
from fog_safe.vehicle import MiningVehicle
from fog_safe.road import RoadSegment
from fog_safe.environment import EnvironmentState
from fog_safe.communication import CommunicationModel


def run_single_simulation(level_name: str, seed: int, network, vehicle_cfg, weather_cfg,
                          duration_s: float = 300.0, vis_m: float = 12.0, fric_mu: float = 0.35,
                          gross_mass_kg: float = 165500.0, tau_human_s: float = 0.5,
                          s_base_m: float = 5.0) -> Dict[str, Any]:
    """Executes a single simulation instance under specific parameters and random seed."""
    veh_cfg = copy.deepcopy(vehicle_cfg)
    w_cfg = copy.deepcopy(weather_cfg)
    
    sim = MineDigitalTwinSimulator(
        network=network,
        vehicle_config=veh_cfg,
        weather_config=w_cfg,
        dt_seconds=1.0,
        seed=seed
    )
    sim.set_environmental_conditions(weather_mode="DENSE_FOG", visibility_m=vis_m, surface_state="wet", friction_mu=fric_mu)
    sim.spawn_fleet(num_vehicles=10)
    
    steps = int(duration_s / sim.dt_seconds)
    queue_history: List[float] = []
    speeds_history: List[float] = []
    speed_violations = 0
    clamped_count = 0
    holds_count = 0
    
    milp_dispatcher = None
    chance_dispatcher = None
    if level_name == "FOG_ORCHESTRATOR":
        milp_dispatcher = DeterministicMILPDispatcher(network, planning_horizon_s=300.0, period_dt_s=30.0)
    elif level_name == "CHANCE_MPC":
        chance_dispatcher = ChanceConstrainedRHMPCDispatcher(network, veh_cfg, planning_horizon_s=300.0, period_dt_s=30.0)
        
    for step_idx in range(steps):
        # 1. Periodic central optimization for Level 4 and Level 5
        if step_idx % 30 == 0:
            if level_name == "FOG_ORCHESTRATOR" and milp_dispatcher:
                res = milp_dispatcher.solve(sim.state.vehicles, sim.state)
                if res.success:
                    for d in res.decisions:
                        for r_id, spd in d.planned_speeds_mps.items():
                            if d.vehicle_id in sim.vehicles:
                                sim.vehicle_target_speeds[d.vehicle_id] = spd
                                holds_count += 1
            elif level_name == "CHANCE_MPC" and chance_dispatcher:
                res = chance_dispatcher.solve_chance_dispatch(sim.state.vehicles, sim.state)
                for d in res.decisions:
                    for r_id, spd in d.planned_speeds_mps.items():
                        if d.vehicle_id in sim.vehicles:
                            sim.vehicle_target_speeds[d.vehicle_id] = spd

        # 2. Local Vehicle Safety Governor (Tier-1 Autonomous Authority)
        for vid, vehicle in sim.vehicles.items():
            v_state = vehicle.get_state()
            road_state = sim.state.roads.get(v_state.road_edge)
            v_safe = road_state.safe_speed_mps if road_state else 3.5
            
            if level_name == "STOP_ALL":
                target_spd = 0.0
            elif level_name == "NO_INTELLIGENCE":
                # Unaware human driver tries to maintain nominal 40 km/h (11.11 m/s)
                target_spd = 11.11
            elif level_name == "SAFETY_ONLY":
                target_spd = v_safe
            elif level_name == "SAFETY_CAPACITY":
                target_spd = min(v_safe, road_state.safe_speed_mps if road_state else 11.11)
            elif level_name == "SAFETY_CAPACITY_QUEUE":
                crusher_q = sim.state.nodes["CRUSHER"].queue_length if "CRUSHER" in sim.state.nodes else 0
                if crusher_q >= 3:
                    target_spd = min(v_safe * 0.4, 1.8)
                else:
                    target_spd = v_safe
            elif level_name in ["FOG_ORCHESTRATOR", "CHANCE_MPC"]:
                target_spd = sim.vehicle_target_speeds.get(vid, v_safe)
            else:
                target_spd = v_safe
                
            # Non-negotiable Tier-1 Governor Clamping
            if level_name != "NO_INTELLIGENCE":
                if target_spd > v_safe + 1e-3:
                    clamped_count += 1
                    target_spd = v_safe
            else:
                # Under NO_INTELLIGENCE, human ignores safety until crash/overspeed
                pass
                
            sim.vehicle_target_speeds[vid] = target_spd
                            
        sim.step()
        
        q_vals = [n.queue_length for n in sim.state.nodes.values()]
        queue_history.append(sum(q_vals) / max(1, len(q_vals)))
        
        for vid, v in sim.state.vehicles.items():
            speeds_history.append(v.speed_v)
            r_state = sim.state.roads.get(v.road_edge)
            v_safe_limit = r_state.safe_speed_mps if r_state else 11.11
            if v.speed_v > v_safe_limit + 1e-3:
                speed_violations += 1

    hours = duration_s / 3600.0
    prod_tonnes = sim.state.total_tonnage_delivered
    throughput_vph = (prod_tonnes / 91.5) / hours if hours > 0 else 0.0
    avg_q = sum(queue_history) / max(1, len(queue_history))
    peak_q = max(queue_history) if queue_history else 0.0
    mean_spd = sum(speeds_history) / max(1, len(speeds_history))
    travel_time_s = 2000.0 / max(0.5, mean_spd)
    idle_pct = (sum(1 for s in speeds_history if s < 0.1) / max(1, len(speeds_history))) * 100.0
    
    return {
        "production_tonnes": round(prod_tonnes, 1),
        "throughput_vph": round(throughput_vph, 2),
        "safety_violations": int(sim.state.safety_violations_count + speed_violations),
        "speed_violations": int(speed_violations),
        "clamped_commands": int(clamped_count),
        "average_queue": round(avg_q, 2),
        "peak_queue": round(peak_q, 2),
        "average_speed_mps": round(mean_spd, 2),
        "travel_time_s": round(travel_time_s, 1),
        "idle_pct": round(idle_pct, 1),
        "holds_count": int(holds_count)
    }


def run_multi_seed_evaluation():
    print("[1/3] Executing 20-Seed Robustness Evaluation across 7 Levels...")
    
    cfg_dir = os.path.join(TWIN_DIR, "config")
    nodes_path = os.path.join(cfg_dir, "nodes.yaml")
    roads_path = os.path.join(cfg_dir, "roads.yaml")
    vehicle_cfg_path = os.path.join(cfg_dir, "vehicle.yaml")
    weather_cfg_path = os.path.join(cfg_dir, "weather.yaml")

    network = MineNetwork.from_yaml_files(nodes_path, roads_path)
    with open(vehicle_cfg_path, "r", encoding="utf-8") as f:
        vehicle_cfg = yaml.safe_load(f)
    with open(weather_cfg_path, "r", encoding="utf-8") as f:
        weather_cfg = yaml.safe_load(f)

    levels = [
        ("LEVEL_-1", "STOP_ALL"),
        ("LEVEL_0", "NO_INTELLIGENCE"),
        ("LEVEL_1", "SAFETY_ONLY"),
        ("LEVEL_2", "SAFETY_CAPACITY"),
        ("LEVEL_3", "SAFETY_CAPACITY_QUEUE"),
        ("LEVEL_4", "FOG_ORCHESTRATOR"),
        ("LEVEL_5", "CHANCE_MPC")
    ]
    
    seeds = [100 + i for i in range(20)]  # Seeds 100 to 119
    raw_results = []
    
    for seed in seeds:
        for lvl_id, lvl_name in levels:
            res = run_single_simulation(lvl_name, seed, network, vehicle_cfg, weather_cfg)
            res.update({
                "seed": seed,
                "level_id": lvl_id,
                "level_name": lvl_name
            })
            raw_results.append(res)
            
    df_raw = pd.DataFrame(raw_results)
    out_csv = os.path.join(WORKSPACE_ROOT, "docs", "STAGE3_MULTI_SEED_RESULTS.csv")
    df_raw.to_csv(out_csv, index=False)
    print(f"Saved {len(df_raw)} multi-seed runs to {out_csv}")
    
    # Statistical Aggregation
    summary_rows = []
    for lvl_id, lvl_name in levels:
        sub = df_raw[df_raw["level_name"] == lvl_name]
        
        summary_rows.append({
            "Method": lvl_name,
            "Safety_Violations_Mean": round(sub["safety_violations"].mean(), 2),
            "Safety_Violations_Std": round(sub["safety_violations"].std(), 2),
            "Safety_Violations_Max": int(sub["safety_violations"].max()),
            "Throughput_VPH_Mean": round(sub["throughput_vph"].mean(), 2),
            "Throughput_VPH_Std": round(sub["throughput_vph"].std(), 2),
            "Production_Tonnes_Mean": round(sub["production_tonnes"].mean(), 1),
            "Production_Tonnes_Std": round(sub["production_tonnes"].std(), 1),
            "Avg_Queue_Mean": round(sub["average_queue"].mean(), 2),
            "Avg_Queue_Std": round(sub["average_queue"].std(), 2),
            "Peak_Queue_Mean": round(sub["peak_queue"].mean(), 2),
            "Travel_Time_S_Mean": round(sub["travel_time_s"].mean(), 1),
            "Travel_Time_S_Std": round(sub["travel_time_s"].std(), 1),
            "Idle_Pct_Mean": round(sub["idle_pct"].mean(), 1),
            "Clamped_Commands_Mean": round(sub["clamped_commands"].mean(), 1)
        })
        
    df_summary = pd.DataFrame(summary_rows)
    benchmark_csv = os.path.join(WORKSPACE_ROOT, "docs", "STAGE3_FINAL_BENCHMARK.csv")
    df_summary.to_csv(benchmark_csv, index=False)
    print(f"Saved {benchmark_csv}")
    
    return df_raw, df_summary


def run_sensitivity_analysis():
    print("[2/3] Executing Parameter Sensitivity (Tornado) Sweep...")
    
    # Baseline parameters
    baseline_params = {
        "visibility_m": 12.0,
        "friction_mu": 0.35,
        "civil_grade_pct": -8.0,
        "gross_mass_kg": 165500.0,
        "tau_human_s": 0.50,
        "s_base_m": 5.0,
        "arrival_rate_vph": 18.0,
        "crusher_capacity_vph": 10.0
    }
    
    # Variations (+/- variations for tornado plot)
    variations = [
        {"param": "visibility_m", "low": 8.0, "base": 12.0, "high": 25.0, "unit": "m"},
        {"param": "friction_mu", "low": 0.20, "base": 0.35, "high": 0.55, "unit": "dimensionless"},
        {"param": "civil_grade_pct", "low": -10.0, "base": -8.0, "high": -4.0, "unit": "%"},
        {"param": "gross_mass_kg", "low": 74000.0, "base": 165500.0, "high": 180000.0, "unit": "kg"},
        {"param": "tau_human_s", "low": 0.30, "base": 0.50, "high": 0.90, "unit": "s"},
        {"param": "s_base_m", "low": 3.0, "base": 5.0, "high": 10.0, "unit": "m"},
        {"param": "arrival_rate_vph", "low": 12.0, "base": 18.0, "high": 24.0, "unit": "vph"},
        {"param": "crusher_capacity_vph", "low": 8.0, "base": 10.0, "high": 16.0, "unit": "vph"}
    ]
    
    sensitivity_records = []
    
    for v in variations:
        p_name = v["param"]
        low_val = v["low"]
        base_val = v["base"]
        high_val = v["high"]
        
        for val, setting in [(low_val, "LOW"), (base_val, "BASE"), (high_val, "HIGH")]:
            current_p = dict(baseline_params)
            current_p[p_name] = val
            
            # Compute physics safe speed
            g_civ = current_p["civil_grade_pct"]
            road = RoadSegment.from_civil_grade(civil_grade_pct=g_civ, speed_limit_kmh=50.0)
            from fog_safe.config import VehicleParameters as VParams
            v_params = VParams(mass_loaded=current_p["gross_mass_kg"])
            veh = MiningVehicle(params=v_params, is_loaded=True)
            env = EnvironmentState(r_effective=current_p["visibility_m"])
            comm = CommunicationModel()
            comm.rx_params.tau_human = current_p["tau_human_s"]
            comm.margin_params.s_base = current_p["s_base_m"]
            
            res = solve_safe_speed(veh, road, env, comm, mu_effective=current_p["friction_mu"], r_effective=current_p["visibility_m"])
            v_safe = res.v_safe_ms
            h_safe = res.s_stop + res.s_margin
            
            # Kinematic capacity & queue dynamics
            c_kin = (3600.0 * v_safe) / (h_safe + 10.52)
            lam = current_p["arrival_rate_vph"]
            mu = current_p["crusher_capacity_vph"]
            q_predicted = max(0.0, (lam - mu) * (600.0 / 3600.0))
            
            sensitivity_records.append({
                "parameter": p_name,
                "setting": setting,
                "param_value": val,
                "unit": v["unit"],
                "v_safe_mps": round(v_safe, 3),
                "v_safe_kmh": round(v_safe * 3.6, 2),
                "a_dec_mps2": round(res.a_dec, 3),
                "s_stop_m": round(res.s_stop, 2),
                "safe_headway_m": round(h_safe, 2),
                "kinematic_capacity_vph": round(c_kin, 1),
                "predicted_crusher_queue": round(q_predicted, 2)
            })
            
    df_sens = pd.DataFrame(sensitivity_records)
    sens_csv = os.path.join(WORKSPACE_ROOT, "docs", "STAGE3_SENSITIVITY_RESULTS.csv")
    df_sens.to_csv(sens_csv, index=False)
    print(f"Saved {len(df_sens)} sensitivity records to {sens_csv}")
    
    return df_sens


if __name__ == "__main__":
    run_multi_seed_evaluation()
    run_sensitivity_analysis()
    print("Robustness & Sensitivity Analysis Complete.")
