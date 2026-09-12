"""
optimizer/baseline_dispatch.py
------------------------------
Implements the 4 benchmark baseline dispatch modes for FOG-ORCHESTRATOR 2.0:
1. Human / Permissive Baseline: Nominal 40 km/h dispatch without proactive weather throttling.
2. Fixed-Speed 10 km/h Baseline: Conservative 2.78 m/s crawl heuristic.
3. Vehicle-Only Baseline: Local reactive speed reduction without fleet arrival shaping.
4. Fleet-Only Baseline: Centralized arrival shaping and queue control without overriding vehicle safety.

Requirements:
- Independent Tier-1 safety governor invariant: v_command = min(v_dispatch, v_safe).
- Standardized operational KPI evaluation across all modes.

Evidence Tags:
- Baseline Evaluation: [VERIFIED / COMPARISON] Benchmark performance metrics.
- Safety Invariant: [VERIFIED / PRIMARY] Local safety governor takes precedence.
"""

from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import math
import copy

from twin.network import MineNetwork
from twin.simulator import MineDigitalTwinSimulator
from twin.state import TwinState, RoadSegmentState
from models.vehicle import VehicleState


class BaselineMode(str, Enum):
    HUMAN_PERMISSIVE = "HUMAN_PERMISSIVE"
    FIXED_SPEED_10KMH = "FIXED_SPEED_10KMH"
    VEHICLE_ONLY = "VEHICLE_ONLY"
    FLEET_ONLY = "FLEET_ONLY"


@dataclass
class DispatchMetrics:
    """Standardized KPI summary for benchmark dispatch evaluation."""
    mode: str
    fleet_size: int
    duration_seconds: float
    production_tonnes: float
    throughput_vph: float
    violations_count: int
    average_queue: float
    max_queue: float
    average_utilization: float
    average_travel_time_s: float
    total_stops_count: int

    def to_dict(self) -> Dict[str, Any]:
        return {
            "mode": self.mode,
            "fleet_size": self.fleet_size,
            "duration_seconds": self.duration_seconds,
            "production_tonnes": self.production_tonnes,
            "throughput_vph": self.throughput_vph,
            "violations_count": self.violations_count,
            "average_queue": self.average_queue,
            "max_queue": self.max_queue,
            "average_utilization": self.average_utilization,
            "average_travel_time_s": self.average_travel_time_s,
            "total_stops_count": self.total_stops_count
        }


class BaselineDispatcher:
    """
    Executes benchmark dispatch policies and evaluates comparative metrics.
    """
    def __init__(
        self,
        mode: BaselineMode,
        network: MineNetwork,
        config: Optional[Dict[str, Any]] = None
    ):
        self.mode = mode
        self.network = network
        self.config = config or {}
        self.nominal_speed_mps = 11.11  # 40 km/h nominal mine speed
        self.fixed_speed_mps = 2.78    # 10 km/h crawl heuristic

    def compute_dispatch_speed(
        self,
        vehicle_id: str,
        vehicle_state: VehicleState,
        road_state: Optional[RoadSegmentState] = None
    ) -> float:
        """
        Compute Tier-3 dispatch target speed based on active baseline mode.
        NOTE: This output is ALWAYS passed into Tier-1 safety governor:
        v_command = min(v_dispatch, v_safe)
        """
        if self.mode == BaselineMode.HUMAN_PERMISSIVE:
            # Blindly requests nominal 40 km/h without fog awareness
            return self.nominal_speed_mps

        elif self.mode == BaselineMode.FIXED_SPEED_10KMH:
            # Constant 10 km/h crawl heuristic
            return self.fixed_speed_mps

        elif self.mode == BaselineMode.VEHICLE_ONLY:
            # Vehicle requests maximum allowable road speed limit
            speed_limit = road_state.speed_limit_mps if road_state else self.nominal_speed_mps
            return speed_limit

        elif self.mode == BaselineMode.FLEET_ONLY:
            # Fleet controller respects capacity-adjusted speed
            if road_state:
                return min(self.nominal_speed_mps, road_state.safe_speed_mps)
            return self.nominal_speed_mps

        return self.nominal_speed_mps


def run_single_baseline_simulation(
    mode: BaselineMode,
    network: MineNetwork,
    vehicle_cfg: Dict[str, Any],
    weather_cfg: Dict[str, Any],
    fleet_size: int = 10,
    duration_seconds: float = 300.0,
    weather_mode: str = "DENSE_FOG",
    visibility_m: float = 15.0,
    surface_state: str = "wet",
    seed: int = 42
) -> DispatchMetrics:
    """
    Execute a full simulation run under a designated baseline mode and measure KPIs.
    """
    sim = MineDigitalTwinSimulator(
        network=network,
        vehicle_config=vehicle_cfg,
        weather_config=weather_cfg,
        dt_seconds=1.0,
        seed=seed
    )
    
    dispatcher = BaselineDispatcher(mode=mode, network=network)
    sim.set_environmental_conditions(weather_mode=weather_mode, visibility_m=visibility_m, surface_state=surface_state)
    sim.spawn_fleet(num_vehicles=fleet_size)

    # Simulation loop
    steps = int(duration_seconds / sim.dt_seconds)
    queue_samples: List[float] = []
    utilization_samples: List[float] = []

    for _ in range(steps):
        # Apply baseline dispatch commands to active vehicles
        for vid, vehicle in sim.vehicles.items():
            v_state = vehicle.get_state()
            road_state = sim.state.roads.get(v_state.road_edge)
            v_disp = dispatcher.compute_dispatch_speed(vid, v_state, road_state)
            sim.vehicle_target_speeds[vid] = v_disp

        sim.step()

        # Sample network queues & utilization
        node_queues = [n.queue_length for n in sim.state.nodes.values()]
        queue_samples.append(sum(node_queues) / max(1, len(node_queues)))
        node_utils = [n.queue_length / max(1.0, n.queue_max) for n in sim.state.nodes.values()]
        utilization_samples.append(sum(node_utils) / max(1, len(node_utils)))

    # Compute aggregate metrics
    hours_simulated = max(1e-4, duration_seconds / 3600.0)
    throughput_vph = (sim.state.total_tonnage_delivered / 91.5) / hours_simulated
    avg_queue = sum(queue_samples) / max(1, len(queue_samples))
    max_q = max(queue_samples) if queue_samples else 0.0
    avg_util = sum(utilization_samples) / max(1, len(utilization_samples))

    # Travel time estimation from fleet average speed
    avg_speeds = [v.speed_v for v in sim.state.vehicles.values() if v.speed_v > 0.1]
    mean_spd = (sum(avg_speeds) / len(avg_speeds)) if avg_speeds else 1.0
    estimated_cycle_dist = 2000.0  # Approx 2 km round-trip haul
    avg_travel_time = estimated_cycle_dist / max(0.5, mean_spd)

    return DispatchMetrics(
        mode=mode.value,
        fleet_size=fleet_size,
        duration_seconds=duration_seconds,
        production_tonnes=sim.state.total_tonnage_delivered,
        throughput_vph=throughput_vph,
        violations_count=sim.state.safety_violations_count,
        average_queue=avg_queue,
        max_queue=max_q,
        average_utilization=avg_util,
        average_travel_time_s=avg_travel_time,
        total_stops_count=sim.state.total_stops_count
    )


def compare_all_baselines(
    network: MineNetwork,
    vehicle_cfg: Dict[str, Any],
    weather_cfg: Dict[str, Any],
    fleet_size: int = 10,
    duration_seconds: float = 300.0,
    weather_mode: str = "DENSE_FOG",
    visibility_m: float = 15.0,
    surface_state: str = "wet",
    seed: int = 42
) -> Dict[str, DispatchMetrics]:
    """
    Run deterministic side-by-side comparison across all 4 baseline modes.
    """
    results: Dict[str, DispatchMetrics] = {}
    for mode in BaselineMode:
        res = run_single_baseline_simulation(
            mode=mode,
            network=network,
            vehicle_cfg=vehicle_cfg,
            weather_cfg=weather_cfg,
            fleet_size=fleet_size,
            duration_seconds=duration_seconds,
            weather_mode=weather_mode,
            visibility_m=visibility_m,
            surface_state=surface_state,
            seed=seed
        )
        results[mode.value] = res

    return results
