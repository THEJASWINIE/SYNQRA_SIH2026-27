"""
scenarios/scenario_runner.py
----------------------------
Master Batch Scenario Execution Engine for FOG-ORCHESTRATOR 2.0.
Executes scenarios S01 through S20 with full scenario isolation, deterministic seeds,
immutable base configurations, automated KPI extraction, and structured JSON output.

Evidence Tags:
- Scenario Suite: [SIMULATION SCENARIO] Validated execution matrix S01-S20.
- Isolation Invariant: [VERIFIED / PRIMARY] Clean state sandbox per run.
"""

from typing import Dict, Any, List, Optional
import os
import json
import copy
import math
import yaml
from dataclasses import dataclass, asdict

from twin.network import MineNetwork
from twin.simulator import MineDigitalTwinSimulator
from optimizer.baseline_dispatch import BaselineMode, BaselineDispatcher
from optimizer.milp_dispatch import DeterministicMILPDispatcher
from optimizer.robust_mpc import RobustScenarioMPCDispatcher
from optimizer.chance_mpc import ChanceConstrainedRHMPCDispatcher, ChanceForecastState


@dataclass
class ScenarioKPIs:
    """Standardized KPI metrics record for a completed scenario execution."""
    scenario_id: str
    scenario_name: str
    dispatch_mode: str
    fleet_size: int
    duration_seconds: float
    total_steps: int
    production_tonnes: float
    throughput_vph: float
    safety_violations_count: int
    average_queue_length: float
    peak_queue_length: float
    average_node_utilization: float
    estimated_travel_time_s: float
    primary_bottleneck_id: str
    bottleneck_migrations_count: int
    execution_status: str


class ScenarioExecutionEngine:
    """
    Automated execution engine managing scenario batch runs, KPI extraction, and persistence.
    """
    def __init__(
        self,
        config_dir: str,
        results_dir: str
    ):
        self.config_dir = os.path.abspath(config_dir)
        self.results_dir = os.path.abspath(results_dir)
        os.makedirs(self.results_dir, exist_ok=True)

        self.nodes_path = os.path.join(self.config_dir, "nodes.yaml")
        self.roads_path = os.path.join(self.config_dir, "roads.yaml")
        self.vehicle_cfg_path = os.path.join(self.config_dir, "vehicle.yaml")
        self.weather_cfg_path = os.path.join(self.config_dir, "weather.yaml")
        self.scenarios_cfg_path = os.path.join(self.config_dir, "scenarios.yaml")

        self.network = MineNetwork.from_yaml_files(self.nodes_path, self.roads_path)
        with open(self.vehicle_cfg_path, "r", encoding="utf-8") as f:
            self.vehicle_cfg = yaml.safe_load(f)
        with open(self.weather_cfg_path, "r", encoding="utf-8") as f:
            self.weather_cfg = yaml.safe_load(f)
        with open(self.scenarios_cfg_path, "r", encoding="utf-8") as f:
            self.scenarios_dict = yaml.safe_load(f).get("scenarios", {})

    def run_scenario(self, scenario_id: str) -> ScenarioKPIs:
        """
        Execute an individual scenario in full sandbox isolation.
        The base configuration is strictly deep-copied and never mutated.
        """
        if scenario_id not in self.scenarios_dict:
            raise KeyError(f"Scenario '{scenario_id}' not found in {self.scenarios_cfg_path}")

        raw_cfg = copy.deepcopy(self.scenarios_dict[scenario_id])
        name = raw_cfg.get("name", scenario_id)
        fleet_size = int(raw_cfg.get("fleet_size", 10))
        duration_s = float(raw_cfg.get("duration_seconds", 300.0))
        dt_s = float(raw_cfg.get("dt_seconds", 1.0))
        seed = int(raw_cfg.get("seed", 42))
        disp_mode = raw_cfg.get("dispatch_mode", "FLEET_ONLY")
        env_cfg = raw_cfg.get("environment", {})

        # 1. Instantiate fresh sandbox simulator
        sim = MineDigitalTwinSimulator(
            network=self.network,
            vehicle_config=copy.deepcopy(self.vehicle_cfg),
            weather_config=copy.deepcopy(self.weather_cfg),
            dt_seconds=dt_s,
            seed=seed
        )

        # 2. Configure initial environment
        weather_mode = env_cfg.get("weather_mode", "CLEAR")
        vis_m = float(env_cfg.get("visibility_m", env_cfg.get("initial_visibility_m", 50.0)))
        surf_state = env_cfg.get("surface_state", "dry")
        sim.set_environmental_conditions(weather_mode=weather_mode, visibility_m=vis_m, surface_state=surf_state)

        # 3. Spawn fleet
        sim.spawn_fleet(num_vehicles=fleet_size)

        # 4. Instantiate optimizer / dispatch controller if needed
        milp_dispatcher = None
        robust_dispatcher = None
        chance_dispatcher = None

        if disp_mode == "MILP_OPTIMIZER":
            milp_dispatcher = DeterministicMILPDispatcher(self.network, planning_horizon_s=300.0, period_dt_s=30.0)
        elif disp_mode in {"ROBUST_MPC", "ROBUST_MPC_FALLBACK_TEST"}:
            robust_dispatcher = RobustScenarioMPCDispatcher(self.network, self.vehicle_cfg, planning_horizon_s=300.0, period_dt_s=30.0)
        elif disp_mode in {"CHANCE_MPC", "DIURNAL_CYCLE"}:
            chance_dispatcher = ChanceConstrainedRHMPCDispatcher(self.network, self.vehicle_cfg, planning_horizon_s=300.0, period_dt_s=30.0)

        # 5. Run simulation loop
        steps = int(duration_s / dt_s)
        queue_history: List[float] = []
        util_history: List[float] = []

        for step_idx in range(steps):
            t_curr = sim.state.timestamp

            # Dynamic weather incursion / dissipation / diurnal handling
            if weather_mode == "DYNAMIC_INCURSION":
                init_v = env_cfg.get("initial_visibility_m", 50.0)
                final_v = env_cfg.get("final_visibility_m", 10.0)
                dur = env_cfg.get("transition_duration_s", 60.0)
                progress = min(1.0, t_curr / max(1.0, dur))
                curr_v = init_v + progress * (final_v - init_v)
                sim.set_environmental_conditions("DENSE_FOG", visibility_m=curr_v, surface_state="wet")

            elif weather_mode == "DYNAMIC_DISSIPATION":
                init_v = env_cfg.get("initial_visibility_m", 10.0)
                final_v = env_cfg.get("final_visibility_m", 50.0)
                dur = env_cfg.get("transition_duration_s", 60.0)
                progress = min(1.0, t_curr / max(1.0, dur))
                curr_v = init_v + progress * (final_v - init_v)
                sim.set_environmental_conditions("CLEAR", visibility_m=curr_v, surface_state="dry")

            elif weather_mode == "DIURNAL_CYCLE":
                # Sinusoidal visibility oscillation mimicking 24-hr diurnal fog
                diurnal_vis = 25.0 + 18.0 * math.sin((2 * math.pi * t_curr) / 300.0)
                sim.set_environmental_conditions("DIURNAL_FOG", visibility_m=max(7.0, diurnal_vis), surface_state="wet")

            # Optimization / Dispatch step (Receding Horizon periodic updates every 30s)
            if step_idx % 30 == 0:
                if disp_mode == "MILP_OPTIMIZER" and milp_dispatcher:
                    res = milp_dispatcher.solve(sim.state.vehicles, sim.state)
                    if res.success:
                        for d in res.decisions:
                            for r_id, spd in d.planned_speeds_mps.items():
                                if d.vehicle_id in sim.vehicles:
                                    sim.vehicle_target_speeds[d.vehicle_id] = spd

                elif disp_mode in {"ROBUST_MPC", "ROBUST_MPC_FALLBACK_TEST"} and robust_dispatcher:
                    force_fail = (disp_mode == "ROBUST_MPC_FALLBACK_TEST")
                    res = robust_dispatcher.solve_robust_dispatch(sim.state.vehicles, sim.state, force_fail_for_test=force_fail)
                    for d in res.decisions:
                        for r_id, spd in d.planned_speeds_mps.items():
                            if d.vehicle_id in sim.vehicles:
                                sim.vehicle_target_speeds[d.vehicle_id] = spd

                elif disp_mode in {"CHANCE_MPC", "DIURNAL_CYCLE"} and chance_dispatcher:
                    res = chance_dispatcher.solve_chance_dispatch(sim.state.vehicles, sim.state)
                    for d in res.decisions:
                        for r_id, spd in d.planned_speeds_mps.items():
                            if d.vehicle_id in sim.vehicles:
                                sim.vehicle_target_speeds[d.vehicle_id] = spd

            # Advance digital twin step
            sim.step()

            # Track network metrics
            q_vals = [n.queue_length for n in sim.state.nodes.values()]
            queue_history.append(sum(q_vals) / max(1, len(q_vals)))
            u_vals = [n.queue_length / max(1.0, n.queue_max) for n in sim.state.nodes.values()]
            util_history.append(sum(u_vals) / max(1, len(u_vals)))

        # 6. Extract final aggregate KPIs
        hours = max(1e-4, duration_s / 3600.0)
        throughput_vph = (sim.state.total_tonnage_delivered / 91.5) / hours
        avg_q = sum(queue_history) / max(1, len(queue_history))
        peak_q = max(queue_history) if queue_history else 0.0
        avg_u = sum(util_history) / max(1, len(util_history))

        avg_spds = [v.speed_v for v in sim.state.vehicles.values() if v.speed_v > 0.1]
        mean_spd = (sum(avg_spds) / len(avg_spds)) if avg_spds else 1.0
        travel_time = 2000.0 / max(0.5, mean_spd)

        primary_b = sim.state.active_bottlenecks[0]["id"] if sim.state.active_bottlenecks else "NONE"
        mig_count = len(sim.bottleneck_detector.migration_history)

        kpis = ScenarioKPIs(
            scenario_id=scenario_id,
            scenario_name=name,
            dispatch_mode=disp_mode,
            fleet_size=fleet_size,
            duration_seconds=duration_s,
            total_steps=steps,
            production_tonnes=sim.state.total_tonnage_delivered,
            throughput_vph=throughput_vph,
            safety_violations_count=sim.state.safety_violations_count,
            average_queue_length=avg_q,
            peak_queue_length=peak_q,
            average_node_utilization=avg_u,
            estimated_travel_time_s=travel_time,
            primary_bottleneck_id=primary_b,
            bottleneck_migrations_count=mig_count,
            execution_status="COMPLETED_SUCCESS"
        )

        # 7. Persist scenario result JSON
        out_file = os.path.join(self.results_dir, f"{scenario_id}.json")
        with open(out_file, "w", encoding="utf-8") as f:
            json.dump(asdict(kpis), f, indent=2)

        return kpis

    def run_all_scenarios(self) -> Dict[str, ScenarioKPIs]:
        """
        Execute complete master scenario suite (S01 through S20).
        Saves individual JSONs and a consolidated summary matrix.
        """
        all_results: Dict[str, ScenarioKPIs] = {}
        for s_id in sorted(self.scenarios_dict.keys()):
            kpi = self.run_scenario(s_id)
            all_results[s_id] = kpi

        # Save consolidated summary
        summary_file = os.path.join(self.results_dir, "scenario_summary.json")
        summary_payload = {s_id: asdict(kpi) for s_id, kpi in all_results.items()}
        with open(summary_file, "w", encoding="utf-8") as f:
            json.dump(summary_payload, f, indent=2)

        return all_results


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="FOG-ORCHESTRATOR 2.0 - Scenario Runner")
    parser.add_argument("--scenario", type=str, default=None, help="Scenario ID (e.g. S01 to S20) or all")
    args = parser.parse_args()

    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    cfg_dir = os.path.join(base_dir, "config")
    res_dir = os.path.join(base_dir, "results")
    runner = ScenarioExecutionEngine(cfg_dir, res_dir)

    print("==================================================================")
    print("       FOG-ORCHESTRATOR 2.0 - Batch Scenario Execution Engine     ")
    print("==================================================================")

    if args.scenario and args.scenario.upper() != "ALL":
        s_id = args.scenario.upper()
        print(f"Executing Single Scenario: {s_id}...")
        kpi = runner.run_scenario(s_id)
        print(f"Scenario {s_id} Completed: {kpi.production_tonnes:.1f} tonnes delivered, {kpi.safety_violations_count} safety violations.")
    else:
        print("Executing Complete Master Scenario Suite (S01 - S20)...")
        results = runner.run_all_scenarios()
        print(f"Successfully executed {len(results)} scenarios. Results saved to {res_dir}")

