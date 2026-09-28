"""
Baseline & System Controller Variants for FOG-ORCHESTRATOR 2.0 Benchmark Comparison
Implements Baselines 0-4, System 5, and System 6.
"""

from dataclasses import dataclass
from typing import Dict, List, Tuple
from fog_orchestrator.tier1_governor.safety_governor import VehicleSafetyGovernor, SafetyState
from fog_orchestrator.tier2_infrastructure.intersection_rsu import IntersectionRSU
from fog_orchestrator.tier3_central.digital_twin import DigitalTwin, VehicleState
from fog_orchestrator.tier3_central.optimizer import CentralOptimizer

@dataclass
class ControllerConfig:
    name: str
    description: str
    use_tier1_governor: bool
    use_tier2_slots: bool
    use_tier3_dispatch: bool
    optimizer_method: str  # 'NONE', 'DETERMINISTIC_MILP', 'ROBUST_SCENARIO_MPC', 'CHANCE_CONSTRAINED_MPC'
    use_bottleneck_scoring: bool
    use_arrival_shaping: bool
    fixed_speed_limit_kmh: Optional[float] = None
    is_unmanaged_human: bool = False


class BaselineFactory:
    """Factory creating exact baseline and system configuration specifications."""

    @staticmethod
    def get_all_controllers() -> Dict[str, ControllerConfig]:
        return {
            "BASELINE_0": ControllerConfig(
                name="Baseline 0: Unmanaged Human Fog",
                description="Unmanaged human-like fog operation with fixed 1.2s driver reaction latency and unadjusted speeds.",
                use_tier1_governor=False,
                use_tier2_slots=False,
                use_tier3_dispatch=False,
                optimizer_method="NONE",
                use_bottleneck_scoring=False,
                use_arrival_shaping=False,
                is_unmanaged_human=True
            ),
            "BASELINE_1": ControllerConfig(
                name="Baseline 1: Fixed Conservative Speed",
                description="Fixed conservative fog speed limit (10.0 km/h) applied uniformly whenever fog is detected.",
                use_tier1_governor=False,
                use_tier2_slots=False,
                use_tier3_dispatch=False,
                optimizer_method="NONE",
                use_bottleneck_scoring=False,
                use_arrival_shaping=False,
                fixed_speed_limit_kmh=10.0
            ),
            "BASELINE_2": ControllerConfig(
                name="Baseline 2: Vehicle-Only FOG-SAFE",
                description="Autonomous Tier 1 vehicle safety governor only. No central fleet dispatch or infrastructure slot reservation.",
                use_tier1_governor=True,
                use_tier2_slots=False,
                use_tier3_dispatch=False,
                optimizer_method="NONE",
                use_bottleneck_scoring=False,
                use_arrival_shaping=False
            ),
            "BASELINE_3": ControllerConfig(
                name="Baseline 3: Fleet-Only Dispatch",
                description="Central fleet dispatch optimizer with static speed limits. No Tier 1 fog safety governor.",
                use_tier1_governor=False,
                use_tier2_slots=False,
                use_tier3_dispatch=True,
                optimizer_method="DETERMINISTIC_MILP",
                use_bottleneck_scoring=False,
                use_arrival_shaping=False,
                fixed_speed_limit_kmh=20.0
            ),
            "BASELINE_4": ControllerConfig(
                name="Baseline 4: FOG-ORCHESTRATOR (Deterministic)",
                description="Full 3-tier architecture with Deterministic MILP dispatching. No chance constraints or bottleneck scoring.",
                use_tier1_governor=True,
                use_tier2_slots=True,
                use_tier3_dispatch=True,
                optimizer_method="DETERMINISTIC_MILP",
                use_bottleneck_scoring=False,
                use_arrival_shaping=True
            ),
            "SYSTEM_5": ControllerConfig(
                name="System 5: FOG-ORCHESTRATOR + Bottleneck Scoring",
                description="Full 3-tier architecture with Deterministic MILP dispatching and dynamic Bottleneck Scoring.",
                use_tier1_governor=True,
                use_tier2_slots=True,
                use_tier3_dispatch=True,
                optimizer_method="DETERMINISTIC_MILP",
                use_bottleneck_scoring=True,
                use_arrival_shaping=True
            ),
            "SYSTEM_6": ControllerConfig(
                name="System 6: FOG-ORCHESTRATOR + CC-MPC + Bottleneck Scoring",
                description="Full 3-tier architecture with Chance-Constrained MPC, Bottleneck Scoring, Arrival Shaping, and Slot Reservation.",
                use_tier1_governor=True,
                use_tier2_slots=True,
                use_tier3_dispatch=True,
                optimizer_method="CHANCE_CONSTRAINED_MPC",
                use_bottleneck_scoring=True,
                use_arrival_shaping=True
            )
        }
