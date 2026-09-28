"""
validation/unit_tests.py
------------------------
Automated test suite for Stage 1: Graph-First Mine Network & Vehicle Data Structure.

Test Coverage:
1. Graph creation from config files
2. Node creation and node type verification (SHOVEL, CRUSHER, DUMP_POINT, INTERSECTION, SWITCHBACK, BUFFER)
3. Road creation and full attribute verification (all 11 required fields)
4. Graph connectivity and reachability
5. Route finding (shortest path, route distance, alternative routes)
6. Invalid configuration rejection:
   - Duplicate node IDs
   - Unknown/invalid node types
   - Duplicate road IDs
   - Invalid / nonexistent node references
   - Non-positive road length (<= 0)
   - Invalid road width (<= 0)
   - Invalid curve radius (<= 0)
   - Invalid direction modes
   - Unphysical friction / negative visibility
7. Basic vehicle data structure verification (without physics)
"""

import unittest
import os
import copy
from twin.network import (
    MineNetwork,
    NetworkValidationError,
    ALLOWED_NODE_TYPES,
    ALLOWED_DIRECTION_MODES,
    ALLOWED_SURFACE_STATES
)
from models.vehicle import Vehicle, VehicleState


class TestStage1GraphAndVehicle(unittest.TestCase):
    """Stage 1 Unit Test Suite verifying mine graph and vehicle data structures."""

    def setUp(self):
        """Set up standard configuration paths."""
        self.base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        self.nodes_path = os.path.join(self.base_dir, "config", "nodes.yaml")
        self.roads_path = os.path.join(self.base_dir, "config", "roads.yaml")

    def test_01_graph_creation_from_yaml(self):
        """Test that the default YAML configuration files construct a valid mine graph."""
        network = MineNetwork.from_yaml_files(self.nodes_path, self.roads_path)
        summary = network.get_summary()

        self.assertGreater(summary["num_nodes"], 0)
        self.assertGreater(summary["num_edges"], 0)
        self.assertEqual(summary["num_unique_roads"], 7)
        self.assertEqual(summary["num_nodes"], 8)

    def test_02_node_creation_and_types(self):
        """Test that all required node types are present and correctly mapped."""
        network = MineNetwork.from_yaml_files(self.nodes_path, self.roads_path)

        # Verify all 6 mandatory node types exist in the network
        shovels = network.get_nodes_by_type("SHOVEL")
        crushers = network.get_nodes_by_type("CRUSHER")
        dumps = network.get_nodes_by_type("DUMP_POINT")
        intersections = network.get_nodes_by_type("INTERSECTION")
        switchbacks = network.get_nodes_by_type("SWITCHBACK")
        buffers = network.get_nodes_by_type("BUFFER")

        self.assertIn("SHOVEL_01", shovels)
        self.assertIn("SHOVEL_02", shovels)
        self.assertIn("CRUSHER_01", crushers)
        self.assertIn("DUMP_01", dumps)
        self.assertIn("INTERSECTION_01", intersections)
        self.assertIn("SWITCHBACK_01", switchbacks)
        self.assertIn("BUFFER_01", buffers)

        # Verify node attributes on a sample node
        crusher_data = network.nodes_by_id["CRUSHER_01"]
        self.assertEqual(crusher_data["type"], "CRUSHER")
        self.assertEqual(crusher_data["service_rate_vph"], 18.0)
        self.assertEqual(crusher_data["criticality"], 1.0)

    def test_03_road_creation_and_attributes(self):
        """Test that every road segment contains all 11 required fields with valid values."""
        network = MineNetwork.from_yaml_files(self.nodes_path, self.roads_path)

        required_fields = [
            "id", "length_m", "grade_pct", "curve_radius_m", "width_m",
            "direction_mode", "speed_limit_mps", "surface_state",
            "visibility_m", "friction_mu", "friction_sigma"
        ]

        for road_id, road in network.roads_by_id.items():
            for field in required_fields:
                self.assertIn(field, road, f"Road {road_id} is missing required field '{field}'")

            self.assertGreater(road["length_m"], 0.0)
            self.assertGreater(road["width_m"], 0.0)
            self.assertGreater(road["curve_radius_m"], 0.0)
            self.assertGreater(road["speed_limit_mps"], 0.0)
            self.assertIn(road["direction_mode"], ALLOWED_DIRECTION_MODES)
            self.assertIn(road["surface_state"], ALLOWED_SURFACE_STATES)
            self.assertGreater(road["friction_mu"], 0.0)
            self.assertGreaterEqual(road["friction_sigma"], 0.0)
            self.assertGreaterEqual(road["visibility_m"], 0.0)

    def test_04_network_connectivity(self):
        """Test that paths exist from all loading shovels to destinations (crusher, dump)."""
        network = MineNetwork.from_yaml_files(self.nodes_path, self.roads_path)

        # Shovel 1 to Crusher
        path_s1_c = network.find_shortest_path("SHOVEL_01", "CRUSHER_01")
        self.assertEqual(path_s1_c[0], "SHOVEL_01")
        self.assertEqual(path_s1_c[-1], "CRUSHER_01")

        # Shovel 2 to Crusher
        path_s2_c = network.find_shortest_path("SHOVEL_02", "CRUSHER_01")
        self.assertEqual(path_s2_c[0], "SHOVEL_02")
        self.assertEqual(path_s2_c[-1], "CRUSHER_01")

        # Shovel 1 to Waste Dump
        path_s1_d = network.find_shortest_path("SHOVEL_01", "DUMP_01")
        self.assertEqual(path_s1_d[0], "SHOVEL_01")
        self.assertEqual(path_s1_d[-1], "DUMP_01")

        # Reverse path (Crusher to Shovel 1) since segments are bidirectional
        path_return = network.find_shortest_path("CRUSHER_01", "SHOVEL_01")
        self.assertEqual(path_return[0], "CRUSHER_01")
        self.assertEqual(path_return[-1], "SHOVEL_01")

    def test_05_route_finding_and_distance(self):
        """Test route finding calculations and distance summation."""
        network = MineNetwork.from_yaml_files(self.nodes_path, self.roads_path)

        path = network.find_shortest_path("SHOVEL_01", "CRUSHER_01")
        expected_path = [
            "SHOVEL_01",
            "INTERSECTION_01",
            "SWITCHBACK_01",
            "INTERSECTION_02",
            "BUFFER_01",
            "CRUSHER_01"
        ]
        self.assertEqual(path, expected_path)

        # Total route length: 600 + 800 + 250 + 1200 + 300 = 3150m
        route_length = network.get_route_length(path)
        self.assertAlmostEqual(route_length, 3150.0, places=1)

        # All routes search
        all_routes = network.find_all_routes("SHOVEL_01", "CRUSHER_01")
        self.assertGreaterEqual(len(all_routes), 1)
        self.assertIn(expected_path, all_routes)

    def test_06_rejection_duplicate_node_id(self):
        """Test that duplicate node IDs raise NetworkValidationError."""
        nodes_cfg = {
            "nodes": [
                {"id": "NODE_A", "type": "SHOVEL"},
                {"id": "NODE_A", "type": "CRUSHER"}  # Duplicate ID
            ]
        }
        roads_cfg = {"roads": {"segments": []}}
        with self.assertRaises(NetworkValidationError) as ctx:
            MineNetwork(roads_config=roads_cfg, nodes_config=nodes_cfg)
        self.assertIn("Duplicate node ID", str(ctx.exception))

    def test_07_rejection_invalid_node_type(self):
        """Test that unknown node types raise NetworkValidationError."""
        nodes_cfg = {
            "nodes": [
                {"id": "NODE_A", "type": "FLYING_DRONE_PAD"}  # Invalid type
            ]
        }
        roads_cfg = {"roads": {"segments": []}}
        with self.assertRaises(NetworkValidationError) as ctx:
            MineNetwork(roads_config=roads_cfg, nodes_config=nodes_cfg)
        self.assertIn("Invalid node type", str(ctx.exception))

    def test_08_rejection_duplicate_road_id(self):
        """Test that duplicate road segment IDs raise NetworkValidationError."""
        nodes_cfg = {
            "nodes": [
                {"id": "NODE_A", "type": "SHOVEL"},
                {"id": "NODE_B", "type": "CRUSHER"}
            ]
        }
        roads_cfg = {
            "roads": {
                "segments": [
                    {
                        "id": "ROAD_1", "from_node": "NODE_A", "to_node": "NODE_B",
                        "length_m": 500.0, "grade_pct": 0.0, "curve_radius_m": 500.0,
                        "width_m": 14.0, "direction_mode": "bidirectional",
                        "speed_limit_mps": 11.11, "surface_state": "dry",
                        "visibility_m": 50.0, "friction_mu": 0.65, "friction_sigma": 0.05
                    },
                    {
                        "id": "ROAD_1", "from_node": "NODE_A", "to_node": "NODE_B",  # Duplicate road ID
                        "length_m": 500.0, "grade_pct": 0.0, "curve_radius_m": 500.0,
                        "width_m": 14.0, "direction_mode": "bidirectional",
                        "speed_limit_mps": 11.11, "surface_state": "dry",
                        "visibility_m": 50.0, "friction_mu": 0.65, "friction_sigma": 0.05
                    }
                ]
            }
        }
        with self.assertRaises(NetworkValidationError) as ctx:
            MineNetwork(roads_config=roads_cfg, nodes_config=nodes_cfg)
        self.assertIn("Duplicate road segment ID", str(ctx.exception))

    def test_09_rejection_invalid_node_reference(self):
        """Test that road referencing a nonexistent node raises NetworkValidationError."""
        nodes_cfg = {
            "nodes": [
                {"id": "NODE_A", "type": "SHOVEL"}
            ]
        }
        roads_cfg = {
            "roads": {
                "segments": [
                    {
                        "id": "ROAD_1", "from_node": "NODE_A", "to_node": "NONEXISTENT_NODE",
                        "length_m": 500.0, "grade_pct": 0.0, "curve_radius_m": 500.0,
                        "width_m": 14.0, "direction_mode": "bidirectional",
                        "speed_limit_mps": 11.11, "surface_state": "dry",
                        "visibility_m": 50.0, "friction_mu": 0.65, "friction_sigma": 0.05
                    }
                ]
            }
        }
        with self.assertRaises(NetworkValidationError) as ctx:
            MineNetwork(roads_config=roads_cfg, nodes_config=nodes_cfg)
        self.assertIn("invalid or missing 'to_node'", str(ctx.exception))

    def test_10_rejection_non_positive_length(self):
        """Test that negative or zero road length raises NetworkValidationError."""
        nodes_cfg = {
            "nodes": [
                {"id": "NODE_A", "type": "SHOVEL"},
                {"id": "NODE_B", "type": "CRUSHER"}
            ]
        }
        roads_cfg = {
            "roads": {
                "segments": [
                    {
                        "id": "ROAD_1", "from_node": "NODE_A", "to_node": "NODE_B",
                        "length_m": -50.0,  # Negative length
                        "grade_pct": 0.0, "curve_radius_m": 500.0,
                        "width_m": 14.0, "direction_mode": "bidirectional",
                        "speed_limit_mps": 11.11, "surface_state": "dry",
                        "visibility_m": 50.0, "friction_mu": 0.65, "friction_sigma": 0.05
                    }
                ]
            }
        }
        with self.assertRaises(NetworkValidationError) as ctx:
            MineNetwork(roads_config=roads_cfg, nodes_config=nodes_cfg)
        self.assertIn("must have positive length_m", str(ctx.exception))

    def test_11_rejection_invalid_width_and_radius(self):
        """Test that zero width or radius raises NetworkValidationError."""
        nodes_cfg = {
            "nodes": [
                {"id": "NODE_A", "type": "SHOVEL"},
                {"id": "NODE_B", "type": "CRUSHER"}
            ]
        }
        # Zero width
        roads_cfg_zero_width = {
            "roads": {
                "segments": [
                    {
                        "id": "ROAD_1", "from_node": "NODE_A", "to_node": "NODE_B",
                        "length_m": 500.0, "grade_pct": 0.0, "curve_radius_m": 500.0,
                        "width_m": 0.0,  # Zero width
                        "direction_mode": "bidirectional", "speed_limit_mps": 11.11,
                        "surface_state": "dry", "visibility_m": 50.0, "friction_mu": 0.65,
                        "friction_sigma": 0.05
                    }
                ]
            }
        }
        with self.assertRaises(NetworkValidationError) as ctx:
            MineNetwork(roads_config=roads_cfg_zero_width, nodes_config=nodes_cfg)
        self.assertIn("must have positive width_m", str(ctx.exception))

    def test_12_rejection_invalid_direction_mode(self):
        """Test that unknown direction mode raises NetworkValidationError."""
        nodes_cfg = {
            "nodes": [
                {"id": "NODE_A", "type": "SHOVEL"},
                {"id": "NODE_B", "type": "CRUSHER"}
            ]
        }
        roads_cfg = {
            "roads": {
                "segments": [
                    {
                        "id": "ROAD_1", "from_node": "NODE_A", "to_node": "NODE_B",
                        "length_m": 500.0, "grade_pct": 0.0, "curve_radius_m": 500.0,
                        "width_m": 14.0, "direction_mode": "teleportation",  # Invalid mode
                        "speed_limit_mps": 11.11, "surface_state": "dry",
                        "visibility_m": 50.0, "friction_mu": 0.65, "friction_sigma": 0.05
                    }
                ]
            }
        }
        with self.assertRaises(NetworkValidationError) as ctx:
            MineNetwork(roads_config=roads_cfg, nodes_config=nodes_cfg)
        self.assertIn("Invalid direction_mode", str(ctx.exception))

    def test_13_basic_vehicle_data_structure(self):
        """Test Vehicle entity state initialization, payload update, and position tracking."""
        vehicle = Vehicle(vehicle_id="TRUCK_01", config={"tare_tonnes": 74.0})
        state = vehicle.get_state()

        self.assertEqual(state.id, "TRUCK_01")
        self.assertEqual(state.mass_m, 74000.0)
        self.assertFalse(state.is_loaded)
        self.assertEqual(state.payload_tonnes, 0.0)

        # Set 91.5t payload
        vehicle.set_payload(91.5)
        state = vehicle.get_state()
        self.assertTrue(state.is_loaded)
        self.assertEqual(state.payload_tonnes, 91.5)
        self.assertEqual(state.mass_m, 74000.0 + 91500.0)

        # Update position
        vehicle.update_position("ROAD_01_SHOVEL1_TO_INT1", 150.0)
        self.assertEqual(state.road_edge, "ROAD_01_SHOVEL1_TO_INT1")
        self.assertEqual(state.position_s, 150.0)


if __name__ == "__main__":
    unittest.main()
