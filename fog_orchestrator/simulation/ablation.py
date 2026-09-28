"""
Component-by-Component Ablation Study Engine for FOG-ORCHESTRATOR 2.0
Systematically evaluates leave-one-out performance changes to determine real component contributions.
"""

import sys
import pandas as pd
from typing import Dict, List, Tuple
from fog_orchestrator.baselines.baseline_controllers import ControllerConfig
from fog_orchestrator.simulation.simulator import OrchestratorSimulator, SimulationMetrics

class AblationStudyEngine:
    """Executes systematic leave-one-out feature ablation experiments."""

    @staticmethod
    def get_ablation_configs() -> Dict[str, ControllerConfig]:
        return {
            "FULL_SYSTEM": ControllerConfig(
                name="Full System 6",
                description="Complete FOG-ORCHESTRATOR 2.0 system with all 3 tiers active.",
                use_tier1_governor=True, use_tier2_slots=True, use_tier3_dispatch=True,
                optimizer_method="CHANCE_CONSTRAINED_MPC", use_bottleneck_scoring=True, use_arrival_shaping=True
            ),
            "NO_BOTTLENECK_SCORING": ControllerConfig(
                name="Ablation: No Bottleneck Scoring",
                description="Full system excluding Bottleneck Scoring.",
                use_tier1_governor=True, use_tier2_slots=True, use_tier3_dispatch=True,
                optimizer_method="CHANCE_CONSTRAINED_MPC", use_bottleneck_scoring=False, use_arrival_shaping=True
            ),
            "NO_ARRIVAL_SHAPING": ControllerConfig(
                name="Ablation: No Arrival Shaping",
                description="Full system excluding Arrival-Rate Shaping.",
                use_tier1_governor=True, use_tier2_slots=True, use_tier3_dispatch=True,
                optimizer_method="CHANCE_CONSTRAINED_MPC", use_bottleneck_scoring=True, use_arrival_shaping=False
            ),
            "NO_SLOT_RESERVATION": ControllerConfig(
                name="Ablation: No Virtual Slot Reservation",
                description="Full system excluding Tier 2 Virtual Slot Reservation.",
                use_tier1_governor=True, use_tier2_slots=False, use_tier3_dispatch=True,
                optimizer_method="CHANCE_CONSTRAINED_MPC", use_bottleneck_scoring=True, use_arrival_shaping=True
            ),
            "NO_CHANCE_CONSTRAINTS": ControllerConfig(
                name="Ablation: No Chance Constraints",
                description="Full system with Deterministic MILP instead of Chance Constraints.",
                use_tier1_governor=True, use_tier2_slots=True, use_tier3_dispatch=True,
                optimizer_method="DETERMINISTIC_MILP", use_bottleneck_scoring=True, use_arrival_shaping=True
            ),
            "NO_TIER1_GOVERNOR": ControllerConfig(
                name="Ablation: No Tier 1 Vehicle Governor",
                description="Central dispatch only without Tier 1 autonomous vehicle governor.",
                use_tier1_governor=False, use_tier2_slots=True, use_tier3_dispatch=True,
                optimizer_method="CHANCE_CONSTRAINED_MPC", use_bottleneck_scoring=True, use_arrival_shaping=True,
                fixed_speed_limit_kmh=18.0
            )
        }

    @classmethod
    def run_ablation_study(cls) -> pd.DataFrame:
        """Runs ablation study over dense fog & bottleneck scenario."""
        ablation_configs = cls.get_ablation_configs()
        results = []

        vis_profile = {0.0: 15.0}  # Dense fog
        fric_profile = {0.0: 0.35}

        # Benchmark Full System baseline performance
        sim_full = OrchestratorSimulator(ablation_configs["FULL_SYSTEM"], num_vehicles=15, sim_duration_s=60.0, random_seed=42)
        metrics_full, _ = sim_full.run_simulation(vis_profile, fric_profile)
        baseline_tonnes = max(1.0, metrics_full.total_tonnes_delivered)

        for cfg_id, cfg in ablation_configs.items():
            sim = OrchestratorSimulator(cfg, num_vehicles=15, sim_duration_s=60.0, random_seed=42)
            metrics, _ = sim.run_simulation(vis_profile, fric_profile)

            perf_delta_pct = ((metrics.total_tonnes_delivered - baseline_tonnes) / baseline_tonnes) * 100.0

            results.append({
                "ablation_id": cfg_id,
                "config_name": cfg.name,
                "tonnes_delivered": metrics.total_tonnes_delivered,
                "cycles_completed": metrics.total_cycles_completed,
                "peak_queue": metrics.peak_queue_length,
                "safety_violations": metrics.safety_violations_count,
                "perf_delta_pct": perf_delta_pct,
                "recommendation": "KEEP" if abs(perf_delta_pct) >= 3.0 or metrics.safety_violations_count > 0 else "CONSIDER_REMOVING"
            })
            print(f" -> Ablation {cfg_id} completed.", flush=True)

        return pd.DataFrame(results)
