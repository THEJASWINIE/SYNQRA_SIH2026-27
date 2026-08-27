"""
Unit tests for FOG-ORCHESTRATOR 2.0 Visualization UI & Simulation Bridge.
Verifies clean integration on top of the digital twin Simulator and physics pipeline.
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

if __name__ == "__main__":
    unittest.main()
