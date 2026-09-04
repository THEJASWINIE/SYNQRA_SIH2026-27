from models.queue_model import ServiceQueue

class Node:
    """
    Represents a vertex in the mine graph (e.g. Shovel, Crusher, Intersection).
    Houses service queues if applicable.
    """
    def __init__(self, node_id: str, node_type: str, service_rate_vph: float, criticality: float):
        self.id = node_id
        self.type = node_type.upper()  # SHOVEL, INTERSECTION, CRUSHER, BUFFER
        self.criticality = criticality
        self.service_rate_vph = service_rate_vph
        self.queue = ServiceQueue(node_id, service_rate_vph) if self.type in ["SHOVEL", "CRUSHER"] else None

class RoadEdge:
    """
    Represents a directed link (haul-road segment) between nodes in the mine graph.
    Maintains physical and environmental parameters.
    """
    def __init__(self, road_id: str, start_node: str, end_node: str, length_m: float,
                 grade_percent: float, curve_radius_m: float, speed_limit_mps: float, width_m: float):
        self.id = road_id
        self.start_node = start_node
        self.end_node = end_node
        self.length_m = length_m
        self.grade_percent = grade_percent
        self.curve_radius_m = curve_radius_m
        self.speed_limit_mps = speed_limit_mps
        self.width_m = width_m
        
        # Environmental states (updated dynamically)
        self.visibility_m = 50.0
        self.friction_mu = 0.60
        self.c_rr = 0.02
        self.surface_state = "dry"
        
        # Derived safety states (updated dynamically)
        self.v_safe_mps = speed_limit_mps
        self.safe_headway_m = 15.5
        self.capacity_vph = 120.0
        
        # List of vehicles currently traveling on this edge, sorted by position
        self.vehicles = []

class MineNetwork:
    """
    Custom graph model G=(V,E) representing the haul road network.
    """
    def __init__(self):
        self.nodes = {}
        self.edges = {}
        # Mappings to quickly find outward edges
        self.adjacency = {}  # {start_node: [road_edge]}

    def add_node(self, node_id: str, node_type: str, service_rate_vph: float, criticality: float):
        node = Node(node_id, node_type, service_rate_vph, criticality)
        self.nodes[node_id] = node
        if node_id not in self.adjacency:
            self.adjacency[node_id] = []

    def add_edge(self, road_id: str, start_node: str, end_node: str, length_m: float,
                 grade_percent: float, curve_radius_m: float, speed_limit_mps: float, width_m: float):
        edge = RoadEdge(road_id, start_node, end_node, length_m, grade_percent, 
                        curve_radius_m, speed_limit_mps, width_m)
        self.edges[road_id] = edge
        if start_node not in self.adjacency:
            self.adjacency[start_node] = []
        self.adjacency[start_node].append(edge)

    def get_edge_by_nodes(self, start_node: str, end_node: str) -> RoadEdge:
        """Find road segment connecting start and end nodes."""
        for edge in self.adjacency.get(start_node, []):
            if edge.end_node == end_node:
                return edge
        return None
