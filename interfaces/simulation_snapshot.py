from dataclasses import dataclass, field
from typing import List, Dict, Any

@dataclass
class VehicleSnapshot:
    id: str
    state: str
    position_s: float
    speed_mps: float
    v_safe_mps: float
    v_command_mps: float
    v_dispatch_mps: float
    is_loaded: bool
    payload_kg: float
    mass_kg: float
    current_edge: str
    current_node: str
    stop_envelope_m: float
    safe_headway_m: float
    warning_fault: bool
    total_tonnes_hauled: float

@dataclass
class RoadSnapshot:
    id: str
    length_m: float
    grade_percent: float
    speed_limit_mps: float
    vehicles_on_road: List[str]
    friction_mu: float
    visibility_m: float

@dataclass
class NodeSnapshot:
    id: str
    type: str
    queue_length: int
    queued_vehicles: List[str]
    busy: bool

@dataclass
class SimulationSnapshot:
    timestamp: float
    scenario: str
    vehicles: List[VehicleSnapshot]
    roads: List[RoadSnapshot]
    nodes: List[NodeSnapshot]
    arrival_shaping_active: bool
    shovel_release_delay_s: float
    active_bottleneck: str
    warning_fault: bool

    def to_dict(self) -> Dict[str, Any]:
        import dataclasses
        return dataclasses.asdict(self)

    @classmethod
    def from_simulator(cls, sim, scenario_name: str) -> "SimulationSnapshot":
        # Extract vehicle snapshots
        vehicles = []
        warning_fault = False
        for v in sim.vehicles:
            is_ovr = v.v_command_mps < v.v_dispatch_mps - 1e-2 or v.warning_fault
            if is_ovr:
                warning_fault = True
            v_snap = VehicleSnapshot(
                id=v.id,
                state=v.state,
                position_s=float(v.position_s),
                speed_mps=float(v.speed_mps),
                v_safe_mps=float(v.v_safe_mps),
                v_command_mps=float(v.v_command_mps),
                v_dispatch_mps=float(v.v_dispatch_mps),
                is_loaded=v.is_loaded,
                payload_kg=float(v.payload_kg),
                mass_kg=float(v.mass_kg),
                current_edge=v.current_edge if v.current_edge else "",
                current_node=v.current_node if v.current_node else "",
                stop_envelope_m=float(getattr(v, "stop_envelope_m", 0.0)),
                safe_headway_m=float(getattr(v, "safe_headway_m", 0.0)),
                warning_fault=is_ovr,
                total_tonnes_hauled=float(v.total_tonnes_hauled)
            )
            vehicles.append(v_snap)

        # Extract road snapshots
        roads = []
        for road_id, edge in sim.network.edges.items():
            r_snap = RoadSnapshot(
                id=road_id,
                length_m=float(edge.length_m),
                grade_percent=float(edge.grade_percent),
                speed_limit_mps=float(edge.speed_limit_mps),
                vehicles_on_road=[v.id for v in edge.vehicles],
                friction_mu=float(edge.friction_mu),
                visibility_m=float(edge.visibility_m)
            )
            roads.append(r_snap)

        # Extract node snapshots
        nodes = []
        for node_id, node in sim.network.nodes.items():
            queued_v = [v.id for v in getattr(node.queue, "vehicles", [])] if node.queue else []
            n_snap = NodeSnapshot(
                id=node_id,
                type=node.type,
                queue_length=len(queued_v),
                queued_vehicles=queued_v,
                busy=node.queue.busy if (node.queue and hasattr(node.queue, "busy")) else False
            )
            nodes.append(n_snap)

        # Active bottleneck detection
        active_bottleneck = "NONE"
        crusher_q = next((n.queue_length for n in nodes if n.id == "CRUSHER"), 0)
        shovel_q = next((n.queue_length for n in nodes if n.id == "SHOVEL"), 0)
        if crusher_q >= 2:
            active_bottleneck = "CRUSHER"
        elif shovel_q >= 2:
            active_bottleneck = "SHOVEL"

        return cls(
            timestamp=float(sim.current_time),
            scenario=scenario_name,
            vehicles=vehicles,
            roads=roads,
            nodes=nodes,
            arrival_shaping_active=sim.shaping_active,
            shovel_release_delay_s=float(sim.arrival_shaper.active_delay_s),
            active_bottleneck=active_bottleneck,
            warning_fault=warning_fault
        )
