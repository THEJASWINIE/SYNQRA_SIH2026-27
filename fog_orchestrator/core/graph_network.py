"""
Mine Network Graph Representation G=(V,E) for FOG-ORCHESTRATOR 2.0
Operational Targets: NMDC Kirandul, Bacheli, Donimalai Open-Cast Mines
"""

import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

@dataclass
class MineNode:
    """Node in mine graph G=(V,E): Shovel, Crusher, Intersection, Switchback, Buffer."""
    node_id: str
    node_type: str  # 'SHOVEL', 'CRUSHER', 'SWITCHBACK', 'INTERSECTION', 'DUMPING_POCKET', 'BUFFER'
    service_rate_vph: float  # Service rate mu (vehicles per hour)
    max_queue_capacity: float = 10.0  # Finite queue buffer Q_max (vehicles)
    current_queue: float = 0.0  # Current queue length Q(t)
    criticality: float = 1.0  # Weight in bottleneck scoring
    is_blocked: bool = False  # Buffer overflow state (blocking downstream/upstream)

    @property
    def utilization(self) -> float:
        """Calculate node queue fill fraction."""
        if self.max_queue_capacity <= 0:
            return 1.0
        return min(1.0, self.current_queue / self.max_queue_capacity)

@dataclass
class MineEdge:
    """Edge in mine graph G=(V,E): Haul road segment."""
    edge_id: str
    source_node: str
    target_node: str
    length_m: float
    grade_pct: float  # Slope %: positive = downhill towards target, negative = uphill
    curve_radius_m: float  # Curve radius (m), float('inf') for straight segments
    width_m: float  # Road width (m)
    is_narrow_conflict_zone: bool  # True if single-lane switchback or bottleneck conflict zone
    speed_limit_kmh: float = 20.0
    surface_state: str = "DRY"
    visibility_m: float = 50.0  # Spatial visibility V(s,t)
    friction_true: float = 0.35  # Ground truth friction mu_true
    active_vehicles: List[str] = field(default_factory=list)
    current_flow_vph: float = 0.0

    @property
    def grade_rad(self) -> float:
        """Convert grade percentage to radians angle theta."""
        return math.atan(self.grade_pct / 100.0)

    @property
    def grade_deg(self) -> float:
        """Convert grade percentage to degrees."""
        return math.degrees(self.grade_rad)


class MineNetwork:
    """Complete Mine Graph Network G=(V,E) Manager."""
    def __init__(self, name: str = "NMDC_Bacheli_Representative"):
        self.name = name
        self.nodes: Dict[str, MineNode] = {}
        self.edges: Dict[str, MineEdge] = {}
        self.adjacency: Dict[str, List[str]] = {}

    def add_node(self, node: MineNode):
        self.nodes[node.node_id] = node
        if node.node_id not in self.adjacency:
            self.adjacency[node.node_id] = []

    def add_edge(self, edge: MineEdge):
        self.edges[edge.edge_id] = edge
        if edge.source_node in self.adjacency:
            if edge.target_node not in self.adjacency[edge.source_node]:
                self.adjacency[edge.source_node].append(edge.target_node)

    def update_edge_visibility(self, edge_id: str, visibility_m: float):
        if edge_id in self.edges:
            self.edges[edge_id].visibility_m = max(1.0, visibility_m)

    def update_edge_friction(self, edge_id: str, friction: float):
        if edge_id in self.edges:
            self.edges[edge_id].friction_true = max(0.05, min(0.85, friction))

    @classmethod
    def create_representative_nmdc_bacheli(cls) -> 'MineNetwork':
        """
        Creates representative NMDC Bacheli open-cast mine network.
        Includes Shovels (S1, S2), Switchbacks (SW1, SW2), Intersection (I1),
        Crushers (C1, C2), and Dumping Pocket (DP1).
        """
        net = cls(name="NMDC_Bacheli_Representative")

        # Add Nodes
        net.add_node(MineNode("S1", "SHOVEL", service_rate_vph=15.0, max_queue_capacity=8.0, criticality=1.2))
        net.add_node(MineNode("S2", "SHOVEL", service_rate_vph=12.0, max_queue_capacity=6.0, criticality=1.0))
        net.add_node(MineNode("SW1", "SWITCHBACK", service_rate_vph=25.0, max_queue_capacity=4.0, criticality=1.5))
        net.add_node(MineNode("I1", "INTERSECTION", service_rate_vph=30.0, max_queue_capacity=5.0, criticality=1.4))
        net.add_node(MineNode("C1", "CRUSHER", service_rate_vph=18.0, max_queue_capacity=6.0, criticality=2.0))
        net.add_node(MineNode("C2", "CRUSHER", service_rate_vph=14.0, max_queue_capacity=5.0, criticality=1.8))
        net.add_node(MineNode("DP1", "DUMPING_POCKET", service_rate_vph=20.0, max_queue_capacity=8.0, criticality=1.5))

        # Add Edges (Downhill Haul Road from Shovels to Crushers)
        # Edge S1 -> SW1 (Steep downhill segment: 8% grade, narrow switchback access)
        net.add_edge(MineEdge("E_S1_SW1", "S1", "SW1", length_m=800.0, grade_pct=8.0, curve_radius_m=35.0, width_m=12.0, is_narrow_conflict_zone=True))
        # Edge S2 -> I1 (Moderate downhill: 4% grade)
        net.add_edge(MineEdge("E_S2_I1", "S2", "I1", length_m=650.0, grade_pct=4.0, curve_radius_m=60.0, width_m=14.0, is_narrow_conflict_zone=False))
        # Edge SW1 -> I1 (Downhill segment: 6.25% grade)
        net.add_edge(MineEdge("E_SW1_I1", "SW1", "I1", length_m=500.0, grade_pct=6.25, curve_radius_m=45.0, width_m=12.0, is_narrow_conflict_zone=True))
        # Edge I1 -> C1 (Crusher approach 1: 3% grade)
        net.add_edge(MineEdge("E_I1_C1", "I1", "C1", length_m=400.0, grade_pct=3.0, curve_radius_m=float('inf'), width_m=14.0, is_narrow_conflict_zone=False))
        # Edge I1 -> C2 (Crusher approach 2: 3% grade)
        net.add_edge(MineEdge("E_I1_C2", "I1", "C2", length_m=450.0, grade_pct=3.0, curve_radius_m=float('inf'), width_m=14.0, is_narrow_conflict_zone=False))
        # Edge C1 -> DP1 (Dumping pocket access: 2% grade)
        net.add_edge(MineEdge("E_C1_DP1", "C1", "DP1", length_m=300.0, grade_pct=2.0, curve_radius_m=float('inf'), width_m=16.0, is_narrow_conflict_zone=False))

        # Return Edges (Uphill Empty Return Runs: negative grade)
        net.add_edge(MineEdge("E_C1_I1", "C1", "I1", length_m=400.0, grade_pct=-3.0, curve_radius_m=float('inf'), width_m=14.0, is_narrow_conflict_zone=False))
        net.add_edge(MineEdge("E_C2_I1", "C2", "I1", length_m=450.0, grade_pct=-3.0, curve_radius_m=float('inf'), width_m=14.0, is_narrow_conflict_zone=False))
        net.add_edge(MineEdge("E_I1_SW1", "I1", "SW1", length_m=500.0, grade_pct=-6.25, curve_radius_m=45.0, width_m=12.0, is_narrow_conflict_zone=True))
        net.add_edge(MineEdge("E_SW1_S1", "SW1", "S1", length_m=800.0, grade_pct=-8.0, curve_radius_m=35.0, width_m=12.0, is_narrow_conflict_zone=True))
        net.add_edge(MineEdge("E_I1_S2", "I1", "S2", length_m=650.0, grade_pct=-4.0, curve_radius_m=60.0, width_m=14.0, is_narrow_conflict_zone=False))

        return net
