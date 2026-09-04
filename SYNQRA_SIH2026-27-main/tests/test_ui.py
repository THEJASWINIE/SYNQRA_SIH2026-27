"""
Unit tests for FOG-ORCHESTRATOR 2.0 Visualization UI & Simulation Bridge.
Verifies clean integration on top of the digital twin Simulator and physics pipeline,
including car-following safety headway, hysteresis, queue management, and UI rendering.
"""

import unittest
import os
import sys

# Add project root to sys.path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from game_ui import SimulationUIBridge, MiningVisualizerUI

class TestVisualizationUI(unittest.TestCase):
    def setUp(self):
        """Initializes a fresh UI simulation bridge."""
        self.bridge = SimulationUIBridge()

    def test_01_bridge_initialization(self):
        """Verifies clean initialization and configuration loading."""
        self.assertIsNotNone(self.bridge.sim)
        self.assertIsNotNone(self.bridge.network)
        self.assertEqual(len(self.bridge.sim.vehicles), 4)
        
        tel = self.bridge.get_telemetry()
        self.assertEqual(tel["truck_id"], "TRUCK_01")
        self.assertEqual(tel["visibility_m"], 50.0)
        self.assertFalse(tel["running"])
        self.assertFalse(tel["e_stop"])
        self.assertEqual(tel["safety_status"], "SAFE")

    def test_02_state_extraction(self):
        """Verifies telemetry state vector fields."""
        tel = self.bridge.get_telemetry()
        
        # Check vehicle physics fields
        self.assertIn("speed_mps", tel)
        self.assertIn("speed_kmh", tel)
        self.assertIn("v_safe_mps", tel)
        self.assertIn("v_safe_kmh", tel)
        self.assertIn("v_command_mps", tel)
        self.assertIn("current_edge", tel)
        self.assertIn("position_m", tel)
        
        # Check road environment fields
        self.assertIn("grade_percent", tel)
        self.assertIn("friction_mu", tel)
        self.assertIn("surface_state", tel)
        self.assertIn("visibility_m", tel)
        self.assertIn("stop_envelope_m", tel)
        self.assertIn("safe_headway_m", tel)
        self.assertIn("is_following_stopped", tel)

    def test_03_fog_control_and_safe_speed_propagation(self):
        """Verifies adjusting visibility updates road edges and invokes resolve_v_safe()."""
        tel_clear = self.bridge.get_telemetry()
        v_safe_clear = tel_clear["v_safe_kmh"]
        
        # Set Dense Fog (15m)
        self.bridge.set_visibility(15.0)
        self.bridge.step()
        
        tel_dense = self.bridge.get_telemetry()
        self.assertEqual(tel_dense["visibility_m"], 15.0)
        self.assertEqual(tel_dense["surface_state"], "wet")
        self.assertLess(tel_dense["v_safe_kmh"], v_safe_clear)
        self.assertLess(tel_dense["friction_mu"], 0.60)

        # Set Extreme Fog (5m)
        self.bridge.set_visibility(5.0)
        self.bridge.step()
        
        tel_ext = self.bridge.get_telemetry()
        self.assertEqual(tel_ext["visibility_m"], 5.0)
        self.assertEqual(tel_ext["surface_state"], "saturated")
        self.assertLess(tel_ext["v_safe_kmh"], tel_dense["v_safe_kmh"])

    def test_04_speed_control_and_local_governor(self):
        """Verifies speed commands are strictly bounded by backend physical safe speed."""
        # Command a high target speed of 50 km/h
        self.bridge.set_target_speed(50.0)
        self.bridge.step()
        
        tel = self.bridge.get_telemetry()
        # Commanded speed must be clamped by local governor to safe speed
        self.assertLessEqual(tel["v_command_mps"], tel["v_safe_mps"] + 1e-4)

    def test_05_safety_status_classification(self):
        """Verifies SAFE, CAUTION, UNSAFE status classification logic."""
        # Clear visibility and normal speed -> SAFE
        self.bridge.set_visibility(50.0)
        self.bridge.step()
        tel = self.bridge.get_telemetry()
        self.assertEqual(tel["safety_status"], "SAFE")

        # Extreme fog (5m) -> CAUTION / UNSAFE
        self.bridge.set_visibility(5.0)
        self.bridge.step()
        tel_fog = self.bridge.get_telemetry()
        self.assertIn(tel_fog["safety_status"], ["CAUTION", "UNSAFE"])

    def test_06_emergency_stop_and_reset(self):
        """Verifies emergency stop triggers braking and reset restores simulation."""
        # Advance some steps
        for _ in range(3):
            self.bridge.step()
        
        # Trigger E-Stop
        self.bridge.trigger_emergency_stop()
        self.bridge.step()
        tel_estop = self.bridge.get_telemetry()
        self.assertTrue(tel_estop["e_stop"])
        self.assertEqual(tel_estop["safety_status"], "E-STOP")
        self.assertEqual(tel_estop["v_command_mps"], 0.0)

        # Reset
        self.bridge.reset()
        tel_reset = self.bridge.get_telemetry()
        self.assertFalse(tel_reset["e_stop"])
        self.assertEqual(tel_reset["timestamp"], 0.0)

    def test_07_crusher_queuing_and_return_transition(self):
        """Verifies truck arrives at Crusher, queues for unloading, and transitions to ROAD_RETURN."""
        # Advance through ROAD_1 and ROAD_2 to Crusher
        for _ in range(120):
            self.bridge.step()
            if self.bridge.sim.network.nodes["CRUSHER"].queue.length > 0:
                break
        
        t1 = self.bridge.get_truck("TRUCK_01")
        loc_crush = self.bridge.get_vehicle_location(t1)
        self.assertEqual(loc_crush["node_id"], "CRUSHER")
        
        # Advance through dynamic Crusher service time (3600.0 / service_rate_vph)
        crusher_service_steps = int(self.bridge.sim.network.nodes["CRUSHER"].queue.service_time_s) + 10
        for _ in range(crusher_service_steps):
            self.bridge.step()
            if t1.current_edge == "ROAD_RETURN":
                break
                
        self.assertEqual(t1.current_edge, "ROAD_RETURN")
        self.assertFalse(t1.is_loaded)  # Cargo was unloaded

    def test_08_headless_ui_step_and_render(self):
        """Verifies headless UI engine initialization and frame rendering."""
        ui = MiningVisualizerUI(self.bridge, headless=True)
        ui.render()
        self.assertIsNotNone(ui.screen)
        ui.pygame.quit()

    def test_09_following_truck_stops_at_safe_headway(self):
        """Verifies following truck receives 0 km/h command when entering lead truck safe headway."""
        t1 = self.bridge.get_truck("TRUCK_01")
        t1.position_s = 200.0
        t1.speed_mps = 0.0  # Stationary lead truck

        t2 = self.bridge.get_truck("TRUCK_02")
        if t2 in self.bridge.sim.network.nodes["SHOVEL"].queue.vehicles:
            self.bridge.sim.network.nodes["SHOVEL"].queue.vehicles.remove(t2)
        t2.state = "traveling"
        t2.current_edge = "ROAD_1"
        t2.current_node = None
        t2.position_s = 175.0  # gap = 200 - 175 - 14.5 = 10.5m <= safe_headway (~15.5m)
        t2.speed_mps = 8.0
        self.bridge.sim.network.edges["ROAD_1"].vehicles.append(t2)

        self.bridge.evaluate_physics()

        self.assertTrue(t2.is_following_stopped)
        self.assertEqual(t2.v_command_mps, 0.0)
        self.assertEqual(t2.lead_vehicle_id, "TRUCK_01")

    def test_10_following_truck_remains_stopped_while_lead_stationary(self):
        """Verifies following truck comes to a stop and remains stationary while lead truck is stopped."""
        t1 = self.bridge.get_truck("TRUCK_01")
        t1.position_s = 200.0
        t1.speed_mps = 0.0

        t2 = self.bridge.get_truck("TRUCK_02")
        if t2 in self.bridge.sim.network.nodes["SHOVEL"].queue.vehicles:
            self.bridge.sim.network.nodes["SHOVEL"].queue.vehicles.remove(t2)
        t2.state = "traveling"
        t2.current_edge = "ROAD_1"
        t2.current_node = None
        t2.position_s = 170.0
        t2.speed_mps = 5.0
        self.bridge.sim.network.edges["ROAD_1"].vehicles.append(t2)

        # Advance 4 simulation steps
        for _ in range(4):
            t1.speed_mps = 0.0  # Keep lead truck stationary
            self.bridge.step()

        # Following truck must have decelerated and stopped before reaching TRUCK_01
        self.assertEqual(t2.speed_mps, 0.0)
        self.assertLess(t2.position_s, t1.position_s - 14.0)  # No physical overlap
        self.assertTrue(t2.is_following_stopped)

    def test_11_following_truck_resumes_after_lead_moves_away(self):
        """Verifies following truck resumes only when gap >= safe_headway + 5m (hysteresis)."""
        t1 = self.bridge.get_truck("TRUCK_01")
        t1.position_s = 200.0
        t1.speed_mps = 0.0

        t2 = self.bridge.get_truck("TRUCK_02")
        if t2 in self.bridge.sim.network.nodes["SHOVEL"].queue.vehicles:
            self.bridge.sim.network.nodes["SHOVEL"].queue.vehicles.remove(t2)
        t2.state = "traveling"
        t2.current_edge = "ROAD_1"
        t2.current_node = None
        t2.position_s = 180.0  # gap = 200 - 180 - 14.5 = 5.5m <= safe_headway (~10.5m)
        t2.speed_mps = 0.0
        self.bridge.sim.network.edges["ROAD_1"].vehicles.append(t2)

        self.bridge.evaluate_physics()
        self.assertTrue(t2.is_following_stopped)

        # Move lead truck slightly (gap opens from 5.5m to 13.5m, below safe_hw + 5m = 15.5m)
        t1.position_s = 208.0
        self.bridge.evaluate_physics()
        # Hysteresis keeps following stop active
        self.assertTrue(t2.is_following_stopped)
        self.assertEqual(t2.v_command_mps, 0.0)

        # Move lead truck far away (gap opens to 65.5m >= 15.5m)
        t1.position_s = 260.0
        self.bridge.evaluate_physics()
        # Following stop releases and truck resumes commanded speed
        self.assertFalse(t2.is_following_stopped)
        self.assertGreater(t2.v_command_mps, 0.0)

    def test_12_different_road_segments_do_not_trigger_false_stop(self):
        """Verifies trucks on different road segments (e.g. ROAD_1 vs ROAD_2) do not stop each other."""
        t1 = self.bridge.get_truck("TRUCK_01")
        t1.current_edge = "ROAD_1"
        t1.position_s = 480.0
        t1.speed_mps = 8.0

        t2 = self.bridge.get_truck("TRUCK_02")
        if t2 in self.bridge.sim.network.nodes["SHOVEL"].queue.vehicles:
            self.bridge.sim.network.nodes["SHOVEL"].queue.vehicles.remove(t2)
        t2.state = "traveling"
        t2.current_edge = "ROAD_2"
        t2.current_node = None
        t2.position_s = 10.0
        t2.speed_mps = 8.0
        self.bridge.sim.network.edges["ROAD_2"].vehicles.append(t2)

        self.bridge.evaluate_physics()

        # Both trucks travel independently on their own road segments
        self.assertFalse(t1.is_following_stopped)
        self.assertFalse(t2.is_following_stopped)
        self.assertGreater(t1.v_command_mps, 0.0)
        self.assertGreater(t2.v_command_mps, 0.0)

    def test_13_edge_vs_node_queue_separation(self):
        """Verifies road traveling trucks do not treat trucks inside Crusher queue as road headway obstacles."""
        t1 = self.bridge.get_truck("TRUCK_01")
        # Place TRUCK_01 in Crusher queue
        if t1 in self.bridge.sim.network.edges["ROAD_1"].vehicles:
            self.bridge.sim.network.edges["ROAD_1"].vehicles.remove(t1)
        self.bridge.sim.network.nodes["CRUSHER"].queue.add_vehicle(t1)

        # Place TRUCK_02 on ROAD_2
        t2 = self.bridge.get_truck("TRUCK_02")
        if t2 in self.bridge.sim.network.nodes["SHOVEL"].queue.vehicles:
            self.bridge.sim.network.nodes["SHOVEL"].queue.vehicles.remove(t2)
        t2.state = "traveling"
        t2.current_edge = "ROAD_2"
        t2.current_node = None
        t2.position_s = 350.0
        t2.speed_mps = 8.0
        self.bridge.sim.network.edges["ROAD_2"].vehicles.append(t2)

        self.bridge.evaluate_physics()

        # TRUCK_02 moves normally towards the Crusher without false road following stop
        self.assertFalse(t2.is_following_stopped)
        self.assertGreater(t2.v_command_mps, 0.0)

    def test_14_estop_highest_priority_over_car_following(self):
        """Verifies E-STOP overrides all vehicle dispatch and car-following commands."""
        t1 = self.bridge.get_truck("TRUCK_01")
        t1.position_s = 100.0
        t1.speed_mps = 8.0

        self.bridge.trigger_emergency_stop()
        self.bridge.evaluate_physics()

        tel = self.bridge.get_telemetry()
        self.assertTrue(tel["e_stop"])
        self.assertEqual(tel["v_command_mps"], 0.0)
        self.assertEqual(tel["safety_status"], "E-STOP")

    def test_15_physical_v_safe_authoritative_ceiling(self):
        """Verifies commanded speed is strictly clamped by physical v_safe even in free flow."""
        self.bridge.set_visibility(5.0)  # Extreme fog -> v_safe drops significantly (~14 km/h)
        self.bridge.set_target_speed(50.0)
        self.bridge.evaluate_physics()

        tel = self.bridge.get_telemetry()
        self.assertLess(tel["v_safe_kmh"], 20.0)
        self.assertLessEqual(tel["v_command_mps"], tel["v_safe_mps"] + 1e-4)

    def test_16_three_trucks_form_safe_following_queue(self):
        """Verifies three trucks on same edge form an orderly following queue with zero overlaps."""
        t1 = self.bridge.get_truck("TRUCK_01")
        t1.position_s = 250.0
        t1.speed_mps = 0.0

        t2 = self.bridge.get_truck("TRUCK_02")
        if t2 in self.bridge.sim.network.nodes["SHOVEL"].queue.vehicles:
            self.bridge.sim.network.nodes["SHOVEL"].queue.vehicles.remove(t2)
        t2.state = "traveling"
        t2.current_edge = "ROAD_1"
        t2.current_node = None
        t2.position_s = 220.0
        t2.speed_mps = 6.0
        self.bridge.sim.network.edges["ROAD_1"].vehicles.append(t2)

        t3 = self.bridge.get_truck("TRUCK_03")
        if t3 in self.bridge.sim.network.nodes["SHOVEL"].queue.vehicles:
            self.bridge.sim.network.nodes["SHOVEL"].queue.vehicles.remove(t3)
        t3.state = "traveling"
        t3.current_edge = "ROAD_1"
        t3.current_node = None
        t3.position_s = 190.0
        t3.speed_mps = 6.0
        self.bridge.sim.network.edges["ROAD_1"].vehicles.append(t3)

        # Run 6 steps
        for _ in range(6):
            t1.speed_mps = 0.0
            self.bridge.step()

        # Verify ordering: t3 < t2 < t1 with positive gaps and both stopped
        self.assertLess(t3.position_s, t2.position_s - 14.0)
        self.assertLess(t2.position_s, t1.position_s - 14.0)
        self.assertEqual(t2.speed_mps, 0.0)
        self.assertEqual(t3.speed_mps, 0.0)

    def test_17_robust_handling_missing_invalid_position(self):
        """Verifies handling of NaN or missing position values without crashing."""
        t1 = self.bridge.get_truck("TRUCK_01")
        t1.position_s = float('nan')
        
        # Should evaluate safely without crashing
        self.bridge.evaluate_physics()
        tel = self.bridge.get_telemetry()
        self.assertIsNotNone(tel)

    def test_18_fleet_telemetry_extraction(self):
        """Verifies fleet telemetry contains live segregated entries for all 4 trucks."""
        tel = self.bridge.get_telemetry()
        self.assertIn("fleet", tel)
        fleet = tel["fleet"]
        self.assertEqual(len(fleet), 4)

        truck_ids = [t["id"] for t in fleet]
        self.assertIn("TRUCK_01", truck_ids)
        self.assertIn("TRUCK_02", truck_ids)
        self.assertIn("TRUCK_03", truck_ids)
        self.assertIn("TRUCK_04", truck_ids)

        for truck in fleet:
            self.assertIn("speed_kmh", truck)
            self.assertIn("v_safe_kmh", truck)
            self.assertIn("v_command_kmh", truck)
            self.assertIn("location_id", truck)
            self.assertIn("lead_gap_m", truck)
            self.assertIn("status_label", truck)
            self.assertIn("status_color", truck)
            self.assertGreaterEqual(truck["v_safe_kmh"], 0.0)

    def test_19_fleet_telemetry_live_updates_and_status(self):
        """Verifies fleet telemetry updates live with truck following and queue states."""
        # Initial: TRUCK_01 traveling, TRUCK_02 loading at Shovel, TRUCK_03/04 queued at Shovel
        tel = self.bridge.get_telemetry()
        t2_init = next(t for t in tel["fleet"] if t["id"] == "TRUCK_02")
        self.assertEqual(t2_init["status_label"], "LOADING")

        # Step some steps
        for _ in range(5):
            self.bridge.step()

        tel_stepped = self.bridge.get_telemetry()
        t1_stepped = next(t for t in tel_stepped["fleet"] if t["id"] == "TRUCK_01")
        self.assertGreater(t1_stepped["speed_kmh"], 0.0)
        self.assertIn(t1_stepped["status_label"], ["MOVING", "CAUTION"])

if __name__ == "__main__":
    unittest.main()
