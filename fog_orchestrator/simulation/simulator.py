"""
Dynamic Simulator for FOG-ORCHESTRATOR 2.0 (Post-Audit Corrected Version)
Integrates network dynamics, weather injects, baseline controllers with realistic human perception models, and KPI collection.
"""

import math
import random
import pandas as pd
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from fog_orchestrator.core.config import VehicleParameters, EnvironmentalParameters, DEFAULT_VEHICLE, DEFAULT_ENV
from fog_orchestrator.core.graph_network import MineNetwork, MineNode, MineEdge
from fog_orchestrator.tier1_governor.safety_governor import VehicleSafetyGovernor, SafetyState
from fog_orchestrator.tier2_infrastructure.intersection_rsu import IntersectionRSU
from fog_orchestrator.tier3_central.digital_twin import DigitalTwin, VehicleState
from fog_orchestrator.tier3_central.optimizer import CentralOptimizer
from fog_orchestrator.baselines.baseline_controllers import ControllerConfig


@dataclass
class SimulationMetrics:
    total_tonnes_delivered: float = 0.0
    total_cycles_completed: int = 0
    safety_violations_count: int = 0
    emergency_stops_count: int = 0
    peak_queue_length: float = 0.0
    average_queue_length: float = 0.0
    total_wait_time_s: float = 0.0
    fuel_consumption_liters: float = 0.0
    avg_solve_time_s: float = 0.0


class OrchestratorSimulator:
    """Dynamic continuous-time mine simulator."""

    def __init__(
        self,
        controller_config: ControllerConfig,
        num_vehicles: int = 20,
        sim_duration_s: float = 1200.0,
        dt_s: float = 1.0,
        random_seed: int = 42
    ):
        self.config = controller_config
        self.num_vehicles = num_vehicles
        self.sim_duration_s = sim_duration_s
        self.dt_s = dt_s
        self.seed = random_seed

        random.seed(self.seed)
        self.network = MineNetwork.create_representative_nmdc_bacheli()
        self.safety_governor = VehicleSafetyGovernor()
        self.digital_twin = DigitalTwin(self.network, self.safety_governor)

        self.optimizer = CentralOptimizer(
            method=self.config.optimizer_method if self.config.use_tier3_dispatch else "NONE",
            arrival_shaping_enabled=self.config.use_arrival_shaping,
            bottleneck_scoring_enabled=self.config.use_bottleneck_scoring
        )

        self.rsu_sw1 = IntersectionRSU("RSU_SW1", "E_S1_SW1", zone_length_m=100.0)
        self.rsu_i1 = IntersectionRSU("RSU_I1", "E_SW1_I1", zone_length_m=80.0)

        self._initialize_fleet()
        self.metrics = SimulationMetrics()
        self.time_series_data: List[Dict] = []

    def _initialize_fleet(self):
        """Initializes mine dumper fleet across network nodes/edges."""
        for i in range(self.num_vehicles):
            v_id = f"BH100_{i+1:03d}"
            is_loaded = (i % 2 == 0)
            edge_id = "E_S1_SW1" if is_loaded else "E_C1_I1"
            init_pos = (i * 35.0) % 500.0

            veh = VehicleState(
                vehicle_id=v_id,
                is_loaded=is_loaded,
                mass_kg=DEFAULT_VEHICLE.mass_loaded_kg if is_loaded else DEFAULT_VEHICLE.mass_empty_kg,
                current_edge_id=edge_id,
                position_on_edge_m=init_pos,
                speed_mps=4.0,
                acceleration_mps2=0.0,
                direction="DOWNSTREAM_TO_CRUSHER" if is_loaded else "UPSTREAM_TO_SHOVEL",
                assigned_route=["E_S1_SW1", "E_SW1_I1", "E_I1_C1"] if is_loaded else ["E_C1_I1", "E_I1_SW1", "E_SW1_S1"]
            )
            self.digital_twin.register_vehicle(veh)

    def run_simulation(
        self,
        visibility_profile_m: Dict[float, float] = None,
        friction_profile: Dict[float, float] = None,
        comm_health_profile: Dict[float, float] = None
    ) -> Tuple[SimulationMetrics, pd.DataFrame]:
        """Runs dynamic simulation and collects metrics & time-series data."""
        current_time = 0.0
        q_history = []

        while current_time < self.sim_duration_s:
            vis_m = 50.0
            if visibility_profile_m:
                past_times = [t for t in visibility_profile_m.keys() if t <= current_time]
                if past_times:
                    vis_m = visibility_profile_m[max(past_times)]

            fric = 0.35
            if friction_profile:
                past_times = [t for t in friction_profile.keys() if t <= current_time]
                if past_times:
                    fric = friction_profile[max(past_times)]

            comm_h = 1.0
            if comm_health_profile:
                past_times = [t for t in comm_health_profile.keys() if t <= current_time]
                if past_times:
                    comm_h = comm_health_profile[max(past_times)]

            for edge in self.network.edges.values():
                edge.visibility_m = vis_m
                edge.friction_true = fric

            if self.config.use_tier3_dispatch:
                solve_decisions = self.optimizer.solve_dispatch(self.digital_twin)
                if solve_decisions:
                    self.metrics.avg_solve_time_s += solve_decisions[0].solve_time_s

            for veh_id, veh in self.digital_twin.vehicles.items():
                veh.communication_confidence = comm_h
                edge = self.network.edges.get(veh.current_edge_id)
                if not edge:
                    continue

                if self.config.is_unmanaged_human:
                    # REALISTIC HUMAN PERCEPTION MODEL (Post-Audit Fix):
                    # Human driver slows down in fog, but underestimates downhill gravity pull by 25%
                    v_human_desired = max(8.0 / 3.6, (vis_m / 2.5) / 3.6)
                    # Human over-speed margin due to slope acceleration underestimation
                    slope_overshoot = max(0.0, math.sin(edge.grade_rad) * 4.0)
                    v_cmd_mps = v_human_desired + slope_overshoot
                elif self.config.fixed_speed_limit_kmh is not None:
                    v_cmd_kmh = self.config.fixed_speed_limit_kmh
                    v_cmd_mps = v_cmd_kmh / 3.6
                elif self.config.use_tier1_governor:
                    safety_eval = self.safety_governor.evaluate_tier1_safety(
                        r_effective_m=edge.visibility_m,
                        grade_rad=edge.grade_rad,
                        is_loaded=veh.is_loaded,
                        friction_mu=edge.friction_true,
                        curve_radius_m=edge.curve_radius_m,
                        comm_confidence=veh.communication_confidence
                    )
                    veh.safety_state = safety_eval
                    v_cmd_mps = safety_eval.v_safe_mps

                    if safety_eval.s_stop_m > edge.visibility_m + 0.5:
                        self.metrics.safety_violations_count += 1
                else:
                    v_cmd_mps = 20.0 / 3.6

                if self.config.use_tier2_slots and edge.is_narrow_conflict_zone:
                    slot = self.rsu_sw1.process_vehicle_beacon(
                        vehicle_id=veh_id,
                        is_loaded=veh.is_loaded,
                        is_downhill=(edge.grade_pct > 0),
                        current_time_s=current_time,
                        eta_to_zone_s=max(1.0, (edge.length_m - veh.position_on_edge_m) / max(1.0, veh.speed_mps)),
                        v_safe_kmh=v_cmd_mps * 3.6
                    )
                    v_cmd_mps = min(v_cmd_mps, slot.target_speed_kmh / 3.6)

                if veh.speed_mps < v_cmd_mps:
                    veh.speed_mps = min(v_cmd_mps, veh.speed_mps + 1.2 * self.dt_s)
                else:
                    veh.speed_mps = max(v_cmd_mps, veh.speed_mps - 2.5 * self.dt_s)

                veh.position_on_edge_m += veh.speed_mps * self.dt_s

                if veh.position_on_edge_m >= edge.length_m:
                    if edge.target_node == "C1" or edge.target_node == "C2":
                        if veh.is_loaded:
                            self.metrics.total_tonnes_delivered += DEFAULT_VEHICLE.payload_rated_kg / 1000.0
                            self.metrics.total_cycles_completed += 1
                            veh.is_loaded = False
                            veh.current_edge_id = "E_C1_I1"
                            veh.position_on_edge_m = 0.0
                    elif edge.target_node == "S1" or edge.target_node == "S2":
                        if not veh.is_loaded:
                            veh.is_loaded = True
                            veh.current_edge_id = "E_S1_SW1"
                            veh.position_on_edge_m = 0.0

            self.digital_twin.step_simulation(self.dt_s)

            total_q = sum(n.current_queue for n in self.network.nodes.values())
            q_history.append(total_q)
            self.metrics.peak_queue_length = max(self.metrics.peak_queue_length, total_q)

            self.time_series_data.append({
                "time_s": current_time,
                "visibility_m": vis_m,
                "friction": fric,
                "total_queue": total_q,
                "tonnes_delivered": self.metrics.total_tonnes_delivered,
                "safety_violations": self.metrics.safety_violations_count
            })

            current_time += self.dt_s

        self.metrics.average_queue_length = sum(q_history) / max(1, len(q_history))
        df_ts = pd.DataFrame(self.time_series_data)
        return self.metrics, df_ts
