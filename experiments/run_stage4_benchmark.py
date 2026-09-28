"""
experiments/run_stage4_benchmark.py
-----------------------------------
STAGE 4: Re-runs the 20-seed benchmark across all 7 levels following the
forensic resolution of segment-boundary target_speed clamping.

Generates:
  docs/STAGE4_MULTI_SEED_RESULTS.csv
  docs/STAGE4_FINAL_BENCHMARK.csv
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


def run_single_simulation(level_name: str, seed: int, network, vehicle_cfg, weather_cfg,
                          duration_s: float = 300.0, vis_m: float = 12.0, fric_mu: float = 0.35) -> Dict[str, Any]:
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
    waiting_times: List[float] = []
    
    milp_dispatcher = None
    chance_dispatcher = None
    if level_name == "FOG_ORCHESTRATOR":
        milp_dispatcher = DeterministicMILPDispatcher(network, planning_horizon_s=300.0, period_dt_s=30.0)
    elif level_name == "CHANCE_MPC":
        chance_dispatcher = ChanceConstrainedRHMPCDispatcher(network, veh_cfg, planning_horizon_s=300.0, period_dt_s=30.0)
        
    for step_idx in range(steps):
        # 1. Periodic central optimization
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
                
            if level_name != "NO_INTELLIGENCE":
                if target_spd > v_safe + 1e-3:
                    clamped_count += 1
                    target_spd = v_safe
                    
            sim.vehicle_target_speeds[vid] = target_spd
            vehicle.state.target_speed = target_spd
                            
        sim.step()
        
        q_vals = [n.queue_length for n in sim.state.nodes.values()]
        queue_history.append(sum(q_vals) / max(1, len(q_vals)))
        
        for vid, v in sim.state.vehicles.items():
            speeds_history.append(v.speed_v)
            if v.speed_v < 0.1:
                waiting_times.append(1.0)
            r_state = sim.state.roads.get(v.road_edge)
            v_safe_limit = r_state.safe_speed_mps if r_state else 11.11
            if v.speed_v > v_safe_limit + 1e-3:
                speed_violations += 1

    hours = duration_s / 3600.0
    prod_tonnes = sim.state.total_tonnage_delivered
    throughput_vph = (prod_tonnes / 91.5) / hours if hours > 0 else 0.0
    avg_q = float(np.mean(queue_history)) if queue_history else 0.0
    peak_q = float(np.max(queue_history)) if queue_history else 0.0
    mean_spd = float(np.mean(speeds_history)) if speeds_history else 0.0
    travel_time_s = 2000.0 / max(0.5, mean_spd)
    idle_pct = (sum(1 for s in speeds_history if s < 0.1) / max(1, len(speeds_history))) * 100.0
    total_waiting_s = sum(waiting_times) / 10.0  # Average waiting per vehicle

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
        "waiting_time_s": round(total_waiting_s, 1),
        "idle_pct": round(idle_pct, 1),
        "holds_count": int(holds_count)
    }


def run_stage4_evaluation():
    print("[1/2] Executing STAGE 4 Multi-Seed Robustness Evaluation (20 Seeds)...")
    
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
    out_csv = os.path.join(WORKSPACE_ROOT, "docs", "STAGE4_MULTI_SEED_RESULTS.csv")
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
            "Waiting_Time_S_Mean": round(sub["waiting_time_s"].mean(), 1),
            "Waiting_Time_S_Std": round(sub["waiting_time_s"].std(), 1),
            "Idle_Pct_Mean": round(sub["idle_pct"].mean(), 1),
            "Clamped_Commands_Mean": round(sub["clamped_commands"].mean(), 1)
        })
        
    df_summary = pd.DataFrame(summary_rows)
    benchmark_csv = os.path.join(WORKSPACE_ROOT, "docs", "STAGE4_FINAL_BENCHMARK.csv")
    df_summary.to_csv(benchmark_csv, index=False)
    print(f"Saved {benchmark_csv}")
    print("\n--- STAGE 4 FINAL BENCHMARK SUMMARY ---")
    print(df_summary.to_string(index=False))


if __name__ == "__main__":
    run_stage4_evaluation()
