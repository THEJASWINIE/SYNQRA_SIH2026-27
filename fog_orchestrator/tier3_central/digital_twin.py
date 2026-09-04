"""
Tier 3: Digital Twin State Tracker for FOG-ORCHESTRATOR 2.0 (Post-Audit Corrected Version)
Tracks mine graph state, vehicle locations, queues, road capacities, weather, and buffer blocking.
Enforces physical minimum headway center-to-center bound (L_veh + S_base = 15.5m).
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from fog_orchestrator.core.graph_network import MineNetwork, MineNode, MineEdge
from fog_orchestrator.tier1_governor.safety_governor import VehicleSafetyGovernor, SafetyState

@dataclass
class VehicleState:
    """State tracking object for individual mine dumper vehicle."""
    vehicle_id: str
    is_loaded: bool
    mass_kg: float
    current_edge_id: str
    position_on_edge_m: float
    speed_mps: float
    acceleration_mps2: float
    direction: str  # 'DOWNSTREAM_TO_CRUSHER', 'UPSTREAM_TO_SHOVEL'
    assigned_route: List[str]
    current_route_index: int = 0
    safety_state: Optional[SafetyState] = None
    communication_confidence: float = 1.0
    route_commitment_timer_s: float = 0.0


class DigitalTwin:
    """Central Digital Twin Model: STATE + PREDICTION + WHAT-IF + OPTIMIZATION."""
    
    def __init__(self, network: MineNetwork, safety_governor: VehicleSafetyGovernor):
        self.network = network
        self.safety_governor = safety_governor
        self.vehicles: Dict[str, VehicleState] = {}
        self.current_time_s: float = 0.0

    def register_vehicle(self, vehicle: VehicleState):
        self.vehicles[vehicle.vehicle_id] = vehicle
        if vehicle.current_edge_id in self.network.edges:
            edge = self.network.edges[vehicle.current_edge_id]
            if vehicle.vehicle_id not in edge.active_vehicles:
                edge.active_vehicles.append(vehicle.vehicle_id)

    def compute_road_capacity(self, edge_id: str) -> float:
        """
        Calculates dynamic road segment capacity C_r (vehicles per hour):
        Enforces physical center-to-center headway lower bound: H_safe >= L_veh + S_base = 15.5m.
        """
        if edge_id not in self.network.edges:
            return 0.0

        edge = self.network.edges[edge_id]
        is_loaded = True if "S1" in edge.source_node or "SW1" in edge.source_node else False
        safety_eval = self.safety_governor.evaluate_tier1_safety(
            r_effective_m=edge.visibility_m,
            grade_rad=edge.grade_rad,
            is_loaded=is_loaded,
            friction_mu=edge.friction_true,
            curve_radius_m=edge.curve_radius_m,
            comm_confidence=1.0
        )

        v_safe_mps = safety_eval.v_safe_mps

        # PHYSICAL FIX: Enforce minimum center-to-center vehicle headway (10.5m length + 5.0m standstill = 15.5m)
        min_physical_headway_m = self.safety_governor.veh.length_m + self.safety_governor.comm.s_base_m
        h_safe_m = max(min_physical_headway_m, safety_eval.h_safe_m)

        if v_safe_mps <= 0.1 or h_safe_m <= 0.0:
            return 0.0

        cap_vps = v_safe_mps / h_safe_m
        width_factor = min(1.5, edge.width_m / 12.0)
        conflict_factor = 0.5 if edge.is_narrow_conflict_zone else 1.0

        capacity_vph = cap_vps * 3600.0 * width_factor * conflict_factor
        return capacity_vph

    def step_simulation(self, dt_s: float):
        """Advances digital twin state by time step dt_s."""
        self.current_time_s += dt_s

        for veh_id, veh in self.vehicles.items():
            if veh.route_commitment_timer_s > 0:
                veh.route_commitment_timer_s = max(0.0, veh.route_commitment_timer_s - dt_s)

            if veh.current_edge_id in self.network.edges:
                edge = self.network.edges[veh.current_edge_id]
                safety_eval = self.safety_governor.evaluate_tier1_safety(
                    r_effective_m=edge.visibility_m,
                    grade_rad=edge.grade_rad,
                    is_loaded=veh.is_loaded,
                    friction_mu=edge.friction_true,
                    curve_radius_m=edge.curve_radius_m,
                    comm_confidence=veh.communication_confidence
                )
                veh.safety_state = safety_eval

                v_target = safety_eval.v_safe_mps
                if veh.speed_mps < v_target:
                    veh.speed_mps = min(v_target, veh.speed_mps + 1.0 * dt_s)
                else:
                    veh.speed_mps = max(v_target, veh.speed_mps - 2.0 * dt_s)

                veh.position_on_edge_m += veh.speed_mps * dt_s

                if veh.position_on_edge_m >= edge.length_m:
                    target_node_id = edge.target_node
                    target_node = self.network.nodes.get(target_node_id)

                    if target_node and target_node.current_queue >= target_node.max_queue_capacity:
                        veh.position_on_edge_m = edge.length_m
                        veh.speed_mps = 0.0
                        target_node.is_blocked = True
                    else:
                        if target_node:
                            target_node.current_queue += 1.0
                        veh.position_on_edge_m = edge.length_m

        for node_id, node in self.network.nodes.items():
            if node.current_queue > 0:
                service_rate_vps = node.service_rate_vph / 3600.0
                served_vehicles = service_rate_vps * dt_s
                node.current_queue = max(0.0, node.current_queue - served_vehicles)
                if node.current_queue < node.max_queue_capacity:
                    node.is_blocked = False
