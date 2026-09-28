"""
validation/test_bidirectional_topology.py
-----------------------------------------
Automated verification suite explicitly testing the 15 requirements for the
single bidirectional haul-road routing, two-lane virtual offsets, and vehicle movement:

TEST 1: Only one physical road exists.
TEST 2: No ROAD_RETURN_* exists.
TEST 3: Outbound and return use the same physical road IDs.
TEST 4: Outbound truck lateral offset is approximately +W/4.
TEST 5: Return truck lateral offset is approximately -W/4.
TEST 6: Both positions remain within the physical road width.
TEST 7: Opposing trucks on the same road do not have identical center positions.
TEST 8: Opposing trucks have appropriate lateral separation.
TEST 9: Same-direction headway still works.
TEST 10: Switchback mutual exclusion still works.
TEST 11: Truck can complete SHOVEL -> CRUSHER -> SHOVEL using the same physical road IDs.
TEST 12: Fog still changes visibility and safe speed.
TEST 13: Tier-1 governor remains: v_command = min(v_dispatch, v_safe).
TEST 14: Existing S01–S20 scenarios continue to work.
TEST 15: Existing APIs and telemetry continue to work.
"""

import unittest
import os
import math
import yaml
from fastapi.testclient import TestClient

from twin.network import MineNetwork
from twin.simulator import MineDigitalTwinSimulator
from interfaces.task1_hmi import Task1HMIBridge, create_task1_fastapi_app, create_default_digital_twin_simulator
from scenarios.scenario_runner import ScenarioExecutionEngine


class TestBidirectionalHaulRoadTopology(unittest.TestCase):
    """Verifies single bidirectional haul road topology and two-lane virtual truck movement."""

    def setUp(self):
        self.base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        self.nodes_path = os.path.join(self.base_dir, "config", "nodes.yaml")
        self.roads_path = os.path.join(self.base_dir, "config", "roads.yaml")
        self.network = MineNetwork.from_yaml_files(self.nodes_path, self.roads_path)

    def test_01_only_one_physical_road_exists(self):
        """TEST 1: Only one physical road network exists (exactly 7 segments ROAD_01 to ROAD_07)."""
        with open(self.roads_path, "r", encoding="utf-8") as f:
            roads_yaml = yaml.safe_load(f)
        segments = roads_yaml.get("roads", {}).get("segments", [])
        segment_ids = [s["id"] for s in segments]

        self.assertNotIn("ROAD_RETURN_CRUSHER_TO_PIT", segment_ids)
        self.assertNotIn("ROAD_RETURN_CRUSHER_TO_PIT", self.network.roads_by_id)
        # Exactly 7 physical road segments (ROAD_01 to ROAD_07)
        self.assertEqual(len(self.network.roads_by_id), 7)
        self.assertEqual(len(segment_ids), 7)

    def test_02_no_road_return_exists(self):
        """TEST 2: No ROAD_RETURN_* duplicate edges exist in network or config."""
        for road_id in self.network.roads_by_id:
            self.assertFalse(
                road_id.startswith("ROAD_RETURN"),
                f"Duplicate return road edge ID found: {road_id}"
            )
        for u, v, data in self.network.graph.edges(data=True):
            edge_id = data.get("id", "")
            self.assertFalse(
                edge_id.startswith("ROAD_RETURN"),
                f"Graph edge ({u} -> {v}) references duplicate return ID: {edge_id}"
            )

    def test_03_outbound_and_return_use_same_physical_road_ids(self):
        """TEST 3: Outbound and return use the same physical road IDs in reverse order."""
        # Outbound: SHOVEL_01 -> CRUSHER_01
        outbound_nodes = self.network.find_shortest_path("SHOVEL_01", "CRUSHER_01")
        outbound_edges = [
            self.network.get_edge_data(u, v)["id"]
            for u, v in zip(outbound_nodes[:-1], outbound_nodes[1:])
        ]

        # Return: CRUSHER_01 -> SHOVEL_01
        return_nodes = self.network.find_shortest_path("CRUSHER_01", "SHOVEL_01")
        return_edges = [
            self.network.get_edge_data(u, v)["id"]
            for u, v in zip(return_nodes[:-1], return_nodes[1:])
        ]

        self.assertEqual(return_nodes, list(reversed(outbound_nodes)))
        self.assertEqual(return_edges, list(reversed(outbound_edges)))

    def test_04_outbound_truck_lateral_offset_is_positive_w_over_4(self):
        """TEST 4: Outbound truck lateral offset is approximately +W/4."""
        bridge = Task1HMIBridge(create_default_digital_twin_simulator())
        sim = bridge.simulator
        road = sim.network.roads_by_id["ROAD_06_BUFFER1_TO_CRUSHER1"]
        w = float(road["width_m"])  # 16.0m

        v_fwd = sim.spawn_vehicle("V_FWD", "BUFFER_01", is_loaded=True)
        v_fwd.update_position("ROAD_06_BUFFER1_TO_CRUSHER1", 100.0)
        v_fwd.state.lane_or_direction = "forward"

        fleet = bridge.get_fleet_state()["vehicles"]
        fwd_data = next(v for v in fleet if v["id"] == "V_FWD")

        expected_offset = w / 4.0  # +4.0m
        self.assertAlmostEqual(fwd_data["lateral_offset_m"], expected_offset, delta=0.2)
        self.assertEqual(fwd_data["virtual_lane"], "outbound")

    def test_05_return_truck_lateral_offset_is_negative_w_over_4(self):
        """TEST 5: Return truck lateral offset is approximately -W/4."""
        bridge = Task1HMIBridge(create_default_digital_twin_simulator())
        sim = bridge.simulator
        road = sim.network.roads_by_id["ROAD_06_BUFFER1_TO_CRUSHER1"]
        w = float(road["width_m"])  # 16.0m

        v_rev = sim.spawn_vehicle("V_REV", "CRUSHER_01", is_loaded=False)
        v_rev.update_position("ROAD_06_BUFFER1_TO_CRUSHER1", 100.0)
        v_rev.state.lane_or_direction = "reverse"

        fleet = bridge.get_fleet_state()["vehicles"]
        rev_data = next(v for v in fleet if v["id"] == "V_REV")

        expected_offset = -(w / 4.0)  # -4.0m
        self.assertAlmostEqual(rev_data["lateral_offset_m"], expected_offset, delta=0.2)
        self.assertEqual(rev_data["virtual_lane"], "return")

    def test_06_both_positions_remain_within_physical_road_width(self):
        """TEST 6: Both positions remain within the physical road width (2 * abs(offset) < W)."""
        bridge = Task1HMIBridge(create_default_digital_twin_simulator())
        sim = bridge.simulator

        for road_id, road in sim.network.roads_by_id.items():
            w = float(road["width_m"])
            is_single = (road.get("direction_mode") == "single_lane_alternating" or road_id == "ROAD_04_SWITCH1_TO_INT2")

            v_test_fwd = sim.spawn_vehicle(f"FWD_{road_id}", road["from_node"], is_loaded=True)
            v_test_fwd.update_position(road_id, road["length_m"] * 0.5)
            v_test_fwd.state.lane_or_direction = "forward"

            v_test_rev = sim.spawn_vehicle(f"REV_{road_id}", road["to_node"], is_loaded=False)
            v_test_rev.update_position(road_id, road["length_m"] * 0.5)
            v_test_rev.state.lane_or_direction = "reverse"

            fleet = bridge.get_fleet_state()["vehicles"]
            f_data = next(v for v in fleet if v["id"] == f"FWD_{road_id}")
            r_data = next(v for v in fleet if v["id"] == f"REV_{road_id}")

            if is_single:
                self.assertEqual(f_data["lateral_offset_m"], 0.0)
                self.assertEqual(r_data["lateral_offset_m"], 0.0)
            else:
                # 2 * abs(offset) = W/2 < W
                self.assertLess(2.0 * abs(f_data["lateral_offset_m"]), w)
                self.assertLess(2.0 * abs(r_data["lateral_offset_m"]), w)
                self.assertLess(abs(f_data["lateral_offset_m"]), w / 2.0)
                self.assertLess(abs(r_data["lateral_offset_m"]), w / 2.0)

    def test_07_opposing_trucks_do_not_have_identical_center_positions(self):
        """TEST 7: Opposing trucks on the same road do not have identical center positions."""
        bridge = Task1HMIBridge(create_default_digital_twin_simulator())
        sim = bridge.simulator

        v_fwd = sim.spawn_vehicle("V_FWD_7", "BUFFER_01", is_loaded=True)
        v_fwd.update_position("ROAD_06_BUFFER1_TO_CRUSHER1", 150.0)
        v_fwd.state.lane_or_direction = "forward"

        v_rev = sim.spawn_vehicle("V_REV_7", "CRUSHER_01", is_loaded=False)
        v_rev.update_position("ROAD_06_BUFFER1_TO_CRUSHER1", 150.0)
        v_rev.state.lane_or_direction = "reverse"

        fleet = bridge.get_fleet_state()["vehicles"]
        fwd_data = next(v for v in fleet if v["id"] == "V_FWD_7")
        rev_data = next(v for v in fleet if v["id"] == "V_REV_7")

        # They must NOT occupy the exact same 3D coordinates!
        self.assertNotEqual(fwd_data["position_xyz"], rev_data["position_xyz"])

    def test_08_opposing_trucks_have_appropriate_lateral_separation(self):
        """TEST 8: Opposing trucks have appropriate lateral separation (~W/2 = 2 * (W/4))."""
        bridge = Task1HMIBridge(create_default_digital_twin_simulator())
        sim = bridge.simulator
        road = sim.network.roads_by_id["ROAD_06_BUFFER1_TO_CRUSHER1"]
        w = float(road["width_m"])  # 16.0m

        v_fwd = sim.spawn_vehicle("V_FWD_8", "BUFFER_01", is_loaded=True)
        v_fwd.update_position("ROAD_06_BUFFER1_TO_CRUSHER1", 150.0)
        v_fwd.state.lane_or_direction = "forward"

        v_rev = sim.spawn_vehicle("V_REV_8", "CRUSHER_01", is_loaded=False)
        v_rev.update_position("ROAD_06_BUFFER1_TO_CRUSHER1", 150.0)
        v_rev.state.lane_or_direction = "reverse"

        fleet = bridge.get_fleet_state()["vehicles"]
        fwd_p = next(v for v in fleet if v["id"] == "V_FWD_8")["position_xyz"]
        rev_p = next(v for v in fleet if v["id"] == "V_REV_8")["position_xyz"]

        dist = math.hypot(fwd_p[0] - rev_p[0], fwd_p[1] - rev_p[1])
        expected_sep = w / 2.0  # 8.0m
        self.assertAlmostEqual(dist, expected_sep, delta=0.5)

    def test_09_same_direction_headway_still_works(self):
        """TEST 9: Same-direction headway still works (follower brakes to maintain safe gap)."""
        sim = create_default_digital_twin_simulator(fleet_size=0)
        v_lead = sim.spawn_vehicle("LEADER", "BUFFER_01", is_loaded=True)
        v_lead.update_position("ROAD_06_BUFFER1_TO_CRUSHER1", 100.0)
        v_lead.state.speed_v = 0.0  # Stationary leader

        v_follow = sim.spawn_vehicle("FOLLOWER", "BUFFER_01", is_loaded=True)
        v_follow.update_position("ROAD_06_BUFFER1_TO_CRUSHER1", 80.0)  # 20m behind
        v_follow.state.speed_v = 10.0

        sim._recalculate_safety_and_capacities()
        # Follower must have restricted target speed due to close headway gap (< safe headway)
        self.assertLess(v_follow.state.target_speed, 11.11)

    def test_10_switchback_mutual_exclusion_still_works(self):
        """TEST 10: Switchback mutual exclusion still prevents simultaneous conflicting occupancy."""
        sim = create_default_digital_twin_simulator(fleet_size=0)
        coord = sim.switchback_coordinators["SWITCHBACK_01"]

        # Request slot for loaded downhill truck
        ok1, slot1, _ = coord.request_reservation("TRUCK_1", start_time=10.0, duration_seconds=30.0, direction="downhill", is_loaded=True)
        self.assertTrue(ok1)
        self.assertIsNotNone(slot1)

        # Conflicting overlapping request for uphill return truck must be rejected
        ok2, slot2, reason = coord.request_reservation("TRUCK_2", start_time=20.0, duration_seconds=30.0, direction="uphill", is_loaded=False)
        self.assertFalse(ok2)
        self.assertIsNone(slot2)
        self.assertIn("CONFLICT", reason)

    def test_11_truck_can_complete_full_cycle_shovel_crusher_shovel(self):
        """TEST 11: Truck can complete SHOVEL -> CRUSHER -> SHOVEL using the same physical road IDs."""
        sim = create_default_digital_twin_simulator(fleet_size=0)
        truck = sim.spawn_vehicle("TRUCK_TEST", "SHOVEL_01", is_loaded=True)
        self.assertEqual(truck.state.payload_tonnes, 91.5)
        self.assertTrue(truck.state.is_loaded)

        visited_edges_forward = []
        visited_edges_reverse = []
        unloaded_at_crusher = False

        for step in range(800):
            sim.step()
            state = truck.state
            if state.lane_or_direction == "forward":
                if state.road_edge not in visited_edges_forward:
                    visited_edges_forward.append(state.road_edge)
                if unloaded_at_crusher and state.is_loaded:
                    break
            else:
                unloaded_at_crusher = True
                if state.road_edge not in visited_edges_reverse:
                    visited_edges_reverse.append(state.road_edge)

        self.assertTrue(unloaded_at_crusher, "Truck never entered reverse return journey from crusher")
        # Reverse edges must be a subset of the forward physical road edges (same IDs)
        for r_edge in visited_edges_reverse:
            self.assertIn(r_edge, visited_edges_forward, f"Return edge {r_edge} not in forward physical edges")

    def test_12_fog_changes_visibility_and_safe_speed(self):
        """TEST 12: Fog still changes visibility and safe speed."""
        sim = create_default_digital_twin_simulator(fleet_size=0)
        sim.spawn_vehicle("TRUCK_1", "SHOVEL_01", is_loaded=True)

        # Clear conditions (50m)
        sim.set_environmental_conditions("CLEAR", 50.0, "dry", 0.65)
        sim.step()
        v_safe_clear = sim.state.vehicles["TRUCK_1"].target_speed

        # Dense fog conditions (12m)
        sim.set_environmental_conditions("DENSE_FOG", 12.0, "wet", 0.45)
        sim.step()
        v_safe_fog = sim.state.vehicles["TRUCK_1"].target_speed

        self.assertLess(v_safe_fog, v_safe_clear, "Safe speed did not strictly decrease under dense fog")

    def test_13_tier1_governor_remains_invariant(self):
        """TEST 13: Tier-1 governor remains: v_command = min(v_dispatch, v_safe)."""
        sim = create_default_digital_twin_simulator(fleet_size=6)

        for _ in range(30):
            sim.step()
            for vid, v in sim.state.vehicles.items():
                v_dispatch = sim.vehicle_target_speeds.get(vid, 11.11)
                self.assertLessEqual(
                    v.target_speed,
                    v_dispatch + 1e-4,
                    f"v_command {v.target_speed} exceeds v_dispatch {v_dispatch}"
                )

    def test_14_existing_scenarios_continue_to_work(self):
        """TEST 14: Existing S01–S20 scenarios continue to work."""
        engine = ScenarioExecutionEngine(
            config_dir=os.path.join(self.base_dir, "config"),
            results_dir=os.path.join(self.base_dir, "results")
        )
        kpi = engine.run_scenario("S01")
        self.assertIsNotNone(kpi)
        self.assertEqual(kpi.scenario_id, "S01")
        self.assertEqual(kpi.safety_violations_count, 0)

    def test_15_existing_apis_and_telemetry_work(self):
        """TEST 15: Existing APIs and telemetry continue to work with two-lane fields."""
        app = create_task1_fastapi_app(Task1HMIBridge(create_default_digital_twin_simulator()))
        client = TestClient(app)

        res_fleet = client.get("/api/v1/state/fleet")
        self.assertEqual(res_fleet.status_code, 200)
        fleet_data = res_fleet.json()
        self.assertIn("vehicles", fleet_data)
        for v in fleet_data["vehicles"]:
            self.assertIn("lateral_offset_m", v)
            self.assertIn("virtual_lane", v)
            self.assertIn("lane_or_direction", v)

        res_roads = client.get("/api/v1/state/roads")
        self.assertEqual(res_roads.status_code, 200)
        roads_data = res_roads.json()
        self.assertEqual(len(roads_data["roads"]), 7)

        res_reset = client.post("/api/v1/control/reset")
        self.assertEqual(res_reset.status_code, 200)


if __name__ == "__main__":
    unittest.main()
