"""
twin/network.py
---------------
Graph-first topological representation of the open-cast mine haul network G = (V, E)
implemented with NetworkX.

Features:
- Node management supporting: SHOVEL, CRUSHER, DUMP_POINT, INTERSECTION, SWITCHBACK, BUFFER.
- Edge management supporting directed and bidirectional haul road segments with geometry and surface attributes.
- Comprehensive structural validation (uniqueness, node existence, positive dimensions, valid modes).
- Route finding: shortest-path by distance/time, all simple routes, and route distance calculation.

Evidence Tags:
- Graph Topology: [VERIFIED / PRIMARY] Network graph model.
- Validation Rules: [MODEL CONFIG] Strict physical sanity checks.
"""

from typing import Dict, Any, List, Optional, Tuple, Set
import os
import yaml
import networkx as nx


class NetworkValidationError(ValueError):
    """Raised when mine graph configuration fails topological or physical validation."""
    pass


ALLOWED_NODE_TYPES: Set[str] = {
    "SHOVEL",
    "CRUSHER",
    "DUMP_POINT",
    "INTERSECTION",
    "SWITCHBACK",
    "BUFFER"
}

ALLOWED_DIRECTION_MODES: Set[str] = {
    "unidirectional",
    "bidirectional",
    "single_lane_alternating"
}

ALLOWED_SURFACE_STATES: Set[str] = {
    "dry",
    "damp",
    "wet",
    "saturated"
}


class MineNetwork:
    """
    Topological road network graph connecting shovels, crushers, dump pockets,
    intersections, switchbacks, and staging buffers using a directed NetworkX graph.
    """
    def __init__(
        self,
        roads_config: Optional[Dict[str, Any]] = None,
        nodes_config: Optional[Dict[str, Any]] = None
    ):
        self.roads_config = roads_config or {}
        self.nodes_config = nodes_config or {}
        self.graph = nx.DiGraph()
        self.nodes_by_id: Dict[str, Dict[str, Any]] = {}
        self.roads_by_id: Dict[str, Dict[str, Any]] = {}

        if self.nodes_config or self.roads_config:
            self.build_graph()

    @classmethod
    def from_yaml_files(cls, nodes_yaml_path: str, roads_yaml_path: str) -> "MineNetwork":
        """Factory constructor loading directly from YAML files."""
        if not os.path.exists(nodes_yaml_path):
            raise FileNotFoundError(f"Nodes config file not found: {nodes_yaml_path}")
        if not os.path.exists(roads_yaml_path):
            raise FileNotFoundError(f"Roads config file not found: {roads_yaml_path}")

        with open(nodes_yaml_path, "r", encoding="utf-8") as f:
            nodes_data = yaml.safe_load(f)

        with open(roads_yaml_path, "r", encoding="utf-8") as f:
            roads_data = yaml.safe_load(f)

        return cls(roads_config=roads_data, nodes_config=nodes_data)

    def build_graph(self) -> None:
        """
        Constructs the NetworkX directed graph from configuration dictionaries
        and executes full validation.
        """
        self.graph.clear()
        self.nodes_by_id.clear()
        self.roads_by_id.clear()

        self._load_and_validate_nodes()
        self._load_and_validate_roads()

    def _load_and_validate_nodes(self) -> None:
        """Parse and validate node records."""
        raw_nodes = self.nodes_config.get("nodes", [])
        if not raw_nodes:
            raise NetworkValidationError("Nodes configuration must contain a non-empty 'nodes' list.")

        for node in raw_nodes:
            node_id = node.get("id")
            if not node_id:
                raise NetworkValidationError(f"Missing 'id' field in node definition: {node}")

            if node_id in self.nodes_by_id:
                raise NetworkValidationError(f"Duplicate node ID detected: '{node_id}'")

            node_type = str(node.get("type", "")).upper()
            if node_type not in ALLOWED_NODE_TYPES:
                raise NetworkValidationError(
                    f"Invalid node type '{node_type}' for node '{node_id}'. "
                    f"Must be one of {sorted(ALLOWED_NODE_TYPES)}"
                )

            # Store node attributes
            node_data = {
                "id": node_id,
                "type": node_type,
                "description": node.get("description", ""),
                "service_rate_vph": float(node.get("service_rate_vph", 15.0)),
                "queue_max": int(node.get("queue_max", 5)),
                "criticality": float(node.get("criticality", 0.5)),
                "location_local": node.get("location_local", [0.0, 0.0, 0.0])
            }

            self.nodes_by_id[node_id] = node_data
            self.graph.add_node(node_id, **node_data)

    def _load_and_validate_roads(self) -> None:
        """Parse and validate road segment edge records."""
        raw_segments = self.roads_config.get("roads", {}).get("segments", [])
        if not raw_segments:
            # Fallback if roads config is a list or flat structure
            raw_segments = self.roads_config.get("segments", [])

        if not raw_segments:
            raise NetworkValidationError("Roads configuration must contain a non-empty list of road segments.")

        for segment in raw_segments:
            road_id = segment.get("id")
            if not road_id:
                raise NetworkValidationError(f"Missing 'id' in road segment definition: {segment}")

            if road_id in self.roads_by_id:
                raise NetworkValidationError(f"Duplicate road segment ID detected: '{road_id}'")

            from_node = segment.get("from_node")
            to_node = segment.get("to_node")

            if not from_node or from_node not in self.nodes_by_id:
                raise NetworkValidationError(
                    f"Road '{road_id}' references invalid or missing 'from_node': '{from_node}'"
                )
            if not to_node or to_node not in self.nodes_by_id:
                raise NetworkValidationError(
                    f"Road '{road_id}' references invalid or missing 'to_node': '{to_node}'"
                )
            if from_node == to_node:
                raise NetworkValidationError(
                    f"Road '{road_id}' defines a self-loop (from_node == to_node == '{from_node}')"
                )

            # Validate physical dimensions
            length_m = float(segment.get("length_m", 0.0))
            if length_m <= 0.0:
                raise NetworkValidationError(
                    f"Road '{road_id}' must have positive length_m > 0, got {length_m}"
                )

            width_m = float(segment.get("width_m", 0.0))
            if width_m <= 0.0:
                raise NetworkValidationError(
                    f"Road '{road_id}' must have positive width_m > 0, got {width_m}"
                )

            curve_radius_m = float(segment.get("curve_radius_m", 0.0))
            if curve_radius_m <= 0.0:
                raise NetworkValidationError(
                    f"Road '{road_id}' must have positive curve_radius_m > 0, got {curve_radius_m}"
                )

            direction_mode = str(segment.get("direction_mode", "bidirectional")).lower()
            if direction_mode not in ALLOWED_DIRECTION_MODES:
                raise NetworkValidationError(
                    f"Invalid direction_mode '{direction_mode}' in road '{road_id}'. "
                    f"Must be one of {sorted(ALLOWED_DIRECTION_MODES)}"
                )

            speed_limit_mps = float(segment.get("speed_limit_mps", 11.11))
            if speed_limit_mps <= 0.0:
                raise NetworkValidationError(
                    f"Road '{road_id}' must have positive speed_limit_mps > 0, got {speed_limit_mps}"
                )

            surface_state = str(segment.get("surface_state", "dry")).lower()
            if surface_state not in ALLOWED_SURFACE_STATES:
                raise NetworkValidationError(
                    f"Invalid surface_state '{surface_state}' in road '{road_id}'. "
                    f"Must be one of {sorted(ALLOWED_SURFACE_STATES)}"
                )

            friction_mu = float(segment.get("friction_mu", 0.65))
            if friction_mu <= 0.0 or friction_mu > 1.2:
                raise NetworkValidationError(
                    f"Road '{road_id}' has unphysical friction_mu: {friction_mu}"
                )

            friction_sigma = float(segment.get("friction_sigma", 0.05))
            if friction_sigma < 0.0:
                raise NetworkValidationError(
                    f"Road '{road_id}' has negative friction_sigma: {friction_sigma}"
                )

            visibility_m = float(segment.get("visibility_m", 50.0))
            if visibility_m < 0.0:
                raise NetworkValidationError(
                    f"Road '{road_id}' has negative visibility_m: {visibility_m}"
                )

            road_data = {
                "id": road_id,
                "from_node": from_node,
                "to_node": to_node,
                "length_m": length_m,
                "grade_pct": float(segment.get("grade_pct", 0.0)),
                "curve_radius_m": curve_radius_m,
                "width_m": width_m,
                "direction_mode": direction_mode,
                "speed_limit_mps": speed_limit_mps,
                "surface_state": surface_state,
                "visibility_m": visibility_m,
                "friction_mu": friction_mu,
                "friction_sigma": friction_sigma
            }

            self.roads_by_id[road_id] = road_data

            # Add forward directed edge
            self.graph.add_edge(from_node, to_node, **road_data)

            # If bidirectional or single_lane_alternating, add reverse directed edge
            if direction_mode in {"bidirectional", "single_lane_alternating"}:
                reverse_data = dict(road_data)
                # Reverse grade direction for opposing traffic
                reverse_data["grade_pct"] = -road_data["grade_pct"]
                reverse_data["is_reverse_edge"] = True
                self.graph.add_edge(to_node, from_node, **reverse_data)

    def find_shortest_path(
        self,
        origin: str,
        destination: str,
        weight: str = "length_m"
    ) -> List[str]:
        """
        Calculates the shortest sequence of node IDs from origin to destination.
        Raises NetworkValidationError if nodes do not exist or no path connects them.
        """
        if origin not in self.graph:
            raise NetworkValidationError(f"Origin node '{origin}' not found in mine network.")
        if destination not in self.graph:
            raise NetworkValidationError(f"Destination node '{destination}' not found in mine network.")

        try:
            path = nx.shortest_path(self.graph, source=origin, target=destination, weight=weight)
            return path
        except nx.NetworkXNoPath:
            raise NetworkValidationError(
                f"No connected path exists from '{origin}' to '{destination}'."
            )

    def find_all_routes(
        self,
        origin: str,
        destination: str,
        max_depth: int = 10
    ) -> List[List[str]]:
        """
        Finds all simple loop-free node sequences between origin and destination.
        """
        if origin not in self.graph or destination not in self.graph:
            return []
        try:
            return list(nx.all_simple_paths(self.graph, source=origin, target=destination, cutoff=max_depth))
        except nx.NetworkXError:
            return []

    def get_route_length(self, path: List[str]) -> float:
        """
        Calculates total length in meters for a given node path.
        """
        if len(path) < 2:
            return 0.0

        total_length = 0.0
        for u, v in zip(path[:-1], path[1:]):
            if not self.graph.has_edge(u, v):
                raise NetworkValidationError(f"Disconnected edge in path: ({u} -> {v})")
            edge_data = self.graph.get_edge_data(u, v)
            total_length += edge_data.get("length_m", 0.0)

        return total_length

    def get_nodes_by_type(self, node_type: str) -> List[str]:
        """Returns all node IDs matching a specified node type."""
        target_type = node_type.upper()
        return [
            node_id for node_id, data in self.nodes_by_id.items()
            if data.get("type") == target_type
        ]

    def get_edge_data(self, u: str, v: str) -> Optional[Dict[str, Any]]:
        """Retrieves road edge attributes between two nodes."""
        if self.graph.has_edge(u, v):
            return dict(self.graph.get_edge_data(u, v))
        return None

    def get_summary(self) -> Dict[str, Any]:
        """Returns network summary statistics."""
        return {
            "num_nodes": self.graph.number_of_nodes(),
            "num_edges": self.graph.number_of_edges(),
            "num_unique_roads": len(self.roads_by_id),
            "node_types": {
                nt: len(self.get_nodes_by_type(nt)) for nt in ALLOWED_NODE_TYPES
            }
        }
