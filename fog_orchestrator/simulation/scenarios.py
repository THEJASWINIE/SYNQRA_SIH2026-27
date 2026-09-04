"""
22 Killer Scenario Definitions & Benchmarking Suite for FOG-ORCHESTRATOR 2.0
Fast vector-optimized benchmark execution engine.
"""

import sys
import pandas as pd
from typing import Dict, List, Tuple
from fog_orchestrator.baselines.baseline_controllers import BaselineFactory, ControllerConfig
from fog_orchestrator.simulation.simulator import OrchestratorSimulator, SimulationMetrics


class ScenarioSuite:
    """Executes Killer Scenarios across controllers with identical random seeds."""

    @staticmethod
    def get_scenario_profiles(scenario_id: int) -> Tuple[str, Dict[float, float], Dict[float, float], Dict[float, float]]:
        """Returns: (scenario_name, vis_profile, friction_profile, comm_profile)"""
        vis_default = {0.0: 50.0}
        fric_default = {0.0: 0.35}
        comm_default = {0.0: 1.0}

        scenarios_map = {
            1: ("Scen 01: Clear Weather", vis_default, fric_default, comm_default),
            2: ("Scen 02: Moderate Fog", {0.0: 25.0}, fric_default, comm_default),
            3: ("Scen 03: Dense Fog", {0.0: 15.0}, fric_default, comm_default),
            4: ("Scen 04: Extreme Fog", {0.0: 8.0}, fric_default, comm_default),
            5: ("Scen 05: Fog + Wet Road", {0.0: 15.0}, {0.0: 0.25}, comm_default),
            6: ("Scen 06: Fog + 8% Downhill", {0.0: 15.0}, fric_default, comm_default),
            7: ("Scen 07: Fog + Wet + Downhill", {0.0: 10.0}, {0.0: 0.25}, comm_default),
            8: ("Scen 08: Sudden Fog Bank", {0.0: 50.0, 15.0: 10.0}, fric_default, comm_default),
            9: ("Scen 09: Moving Fog Corridor", {0.0: 40.0, 15.0: 15.0}, fric_default, comm_default),
            10: ("Scen 10: False Fog Forecast", vis_default, fric_default, comm_default),
            11: ("Scen 11: Missed Fog Forecast", {0.0: 50.0, 15.0: 12.0}, fric_default, comm_default),
            12: ("Scen 12: Communication Loss", vis_default, fric_default, {0.0: 1.0, 15.0: 0.0}),
            13: ("Scen 13: Radar Sensor Degradation", {0.0: 5.0}, fric_default, comm_default),
            14: ("Scen 14: Crusher Bottleneck", {0.0: 20.0}, fric_default, comm_default),
            15: ("Scen 15: Shovel Bottleneck", {0.0: 20.0}, fric_default, comm_default),
            16: ("Scen 16: Switchback Conflict Bottleneck", {0.0: 15.0}, fric_default, comm_default),
            17: ("Scen 17: Multi-Bottleneck Stress", {0.0: 15.0}, {0.0: 0.30}, comm_default),
            18: ("Scen 18: Bottleneck Migration", {0.0: 20.0}, fric_default, comm_default),
            19: ("Scen 19: Post-Fog Staged Recovery", {0.0: 10.0, 15.0: 45.0}, fric_default, comm_default),
            20: ("Scen 20: Fleet Overload (20 Dumpers)", {0.0: 25.0}, fric_default, comm_default),
            21: ("Scen 21: Sparse Fleet (4 Dumpers)", {0.0: 25.0}, fric_default, comm_default),
            22: ("Scen 22: High Fleet Density (10 Dumpers)", {0.0: 20.0}, fric_default, comm_default),
        }
        return scenarios_map.get(scenario_id, ("Scen 01: Clear Weather", vis_default, fric_default, comm_default))

    @classmethod
    def run_all_scenarios(cls) -> pd.DataFrame:
        """Executes representative killer scenarios across controller variants."""
        controllers = BaselineFactory.get_all_controllers()
        results_records = []

        print("\n" + "="*70, flush=True)
        print(" RUNNING KILLER SCENARIO BENCHMARKING SUITE ", flush=True)
        print("="*70, flush=True)

        target_scenarios = [1, 3, 5, 7, 8, 12, 14, 18, 19, 20]

        for scen_id in target_scenarios:
            scen_name, vis_p, fric_p, comm_p = cls.get_scenario_profiles(scen_id)
            num_v = 20 if scen_id == 20 else (4 if scen_id == 21 else 8)

            for c_id, ctrl in controllers.items():
                sim = OrchestratorSimulator(
                    controller_config=ctrl,
                    num_vehicles=num_v,
                    sim_duration_s=30.0,  # Rapid 30s benchmark sweep
                    random_seed=42 + scen_id
                )
                metrics, _ = sim.run_simulation(vis_p, fric_p, comm_p)

                results_records.append({
                    "scenario_id": scen_id,
                    "scenario_name": scen_name,
                    "controller_id": c_id,
                    "controller_name": ctrl.name,
                    "tonnes_delivered": metrics.total_tonnes_delivered,
                    "cycles_completed": metrics.total_cycles_completed,
                    "safety_violations": metrics.safety_violations_count,
                    "peak_queue": metrics.peak_queue_length,
                    "avg_queue": metrics.average_queue_length,
                    "avg_solve_time_s": metrics.avg_solve_time_s / max(1, metrics.total_cycles_completed + 1)
                })
            print(f" -> Completed {scen_name}", flush=True)

        df_results = pd.DataFrame(results_records)
        return df_results
