import unittest
import numpy as np
from models.braking import calculate_deceleration, calculate_stopping_distance, solve_safe_speed
from models.vehicle_physics import resolve_v_safe, calculate_acceleration, calculate_retarder_speed_limit, calculate_curve_speed_limit
from twin.network import MineNetwork

class TestPhysics(unittest.TestCase):
    
    def setUp(self):
        # Setup typical parameters
        self.mass_loaded = 165000.0  # kg
        self.mass_empty = 74000.0    # kg
        self.max_brake = 600000.0    # N
        self.max_ret_power = 1200000.0 # W
        self.c_rr = 0.02
        self.friction_mu = 0.60
        self.tau = 0.25
        self.margin = 5.0
        self.speed_limit = 13.89

    def test_01_graph_validity(self):
        """TEST 01: Verify graph creation, node types, and edge connectivity."""
        net = MineNetwork()
        net.add_node("SHOVEL", "SHOVEL", 15.0, 2.0)
        net.add_node("INTERSECTION", "INTERSECTION", 120.0, 1.0)
        net.add_node("CRUSHER", "CRUSHER", 18.0, 4.0)
        
        net.add_edge("ROAD_1", "SHOVEL", "INTERSECTION", 500.0, 0.0, 0.0, 13.89, 15.0)
        net.add_edge("ROAD_2", "INTERSECTION", "CRUSHER", 400.0, -8.0, 50.0, 11.11, 12.0)
        
        self.assertIn("SHOVEL", net.nodes)
        self.assertEqual(net.nodes["SHOVEL"].type, "SHOVEL")
        self.assertIn("ROAD_1", net.edges)
        
        edge = net.get_edge_by_nodes("SHOVEL", "INTERSECTION")
        self.assertIsNotNone(edge)
        self.assertEqual(edge.id, "ROAD_1")
        self.assertEqual(edge.grade_percent, 0.0)

    def test_02_vehicle_parameter_validity(self):
        """TEST 02: Check dynamic mass and parameter consistency."""
        from models.vehicle import Vehicle
        cfg = {
            "tare_mass_kg": 74000.0,
            "payload_mass_kg": 91000.0,
            "length_m": 10.52,
            "width_m": 5.52,
            "wheelbase_m": 5.25
        }
        v = Vehicle("TRUCK_01", cfg, "SHOVEL")
        self.assertEqual(v.mass_kg, 74000.0)
        self.assertFalse(v.is_loaded)
        
        # Load
        v.load_cargo()
        self.assertEqual(v.mass_kg, 165000.0)
        self.assertTrue(v.is_loaded)
        
        # Unload
        v.unload_cargo()
        self.assertEqual(v.mass_kg, 74000.0)
        self.assertFalse(v.is_loaded)
        self.assertEqual(v.total_tonnes_hauled, 91.0)

    def test_03_safe_speed_calculation(self):
        """TEST 03: Verify stopping speed solution is correct and bounds are respected."""
        # Flat road, clear visibility 50m
        a_dec = calculate_deceleration(self.mass_loaded, 0.0, self.friction_mu, self.c_rr, self.max_brake)
        v_stop = solve_safe_speed(50.0, a_dec, self.tau, self.margin)
        
        # Safe speed must be physically viable
        self.assertTrue(0.0 < v_stop < 50.0)
        
        # If visibility is less than margin, safe speed must be 0
        v_stop_zero = solve_safe_speed(4.0, a_dec, self.tau, self.margin)
        self.assertEqual(v_stop_zero, 0.0)

    def test_04_stopping_distance_calculation(self):
        """TEST 04: Verify stopping distance calculation matches physical equation."""
        a_dec = 2.0  # m/s^2
        dist = calculate_stopping_distance(10.0, a_dec, self.tau)
        expected = 10.0 * self.tau + (10.0**2) / (2.0 * a_dec)
        self.assertAlmostEqual(dist, expected)

    def test_05_visibility_monotonicity(self):
        """TEST 05: Safe speed must decrease or stay constant as visibility decreases."""
        a_dec = calculate_deceleration(self.mass_loaded, 0.0, self.friction_mu, self.c_rr, self.max_brake)
        
        v_prev = float('inf')
        for vis in [50.0, 40.0, 30.0, 20.0, 15.0, 10.0, 5.0]:
            v_safe = solve_safe_speed(vis, a_dec, self.tau, self.margin)
            self.assertTrue(v_safe <= v_prev, f"Monotonicity violated: {v_safe} > {v_prev} as visibility decreased.")
            v_prev = v_safe

    def test_06_grade_monotonicity(self):
        """TEST 06: Increasing downhill steepness (more negative grade) must decrease or maintain safe speed."""
        v_prev = float('inf')
        # Slopes: flat (0%), downhill (-4%, -6.25%, -8%, -10%)
        for grade in [0.0, -4.0, -6.25, -8.0, -10.0]:
            res = resolve_v_safe(
                mass_kg=self.mass_loaded,
                grade_percent=grade,
                friction_mu=0.25,  # wet
                c_rr=0.03,
                hardware_max_brake_n=self.max_brake,
                max_retarder_power_w=self.max_ret_power,
                curve_radius_m=0.0,
                traction_speed_factor_mps=30.0,
                speed_limit_mps=13.89,
                visibility_m=20.0,
                tau_total=self.tau,
                s_margin=self.margin
            )
            v_safe = res["v_safe"]
            self.assertTrue(v_safe <= v_prev, f"Monotonicity violated: {v_safe} > {v_prev} as downhill grade got steeper.")
            v_prev = v_safe

    def test_07_friction_monotonicity(self):
        """TEST 07: Decreasing friction must decrease or maintain safe speed."""
        v_prev = 0.0
        # Friction sweep from wet (0.15) to dry (0.65)
        for mu in [0.15, 0.25, 0.35, 0.45, 0.55, 0.65]:
            res = resolve_v_safe(
                mass_kg=self.mass_loaded,
                grade_percent=-8.0,
                friction_mu=mu,
                c_rr=0.03,
                hardware_max_brake_n=self.max_brake,
                max_retarder_power_w=self.max_ret_power,
                curve_radius_m=50.0,
                traction_speed_factor_mps=30.0,
                speed_limit_mps=13.89,
                visibility_m=25.0,
                tau_total=self.tau,
                s_margin=self.margin
            )
            v_safe = res["v_safe"]
            self.assertTrue(v_safe >= v_prev, f"Monotonicity violated: {v_safe} < {v_prev} as friction increased.")
            v_prev = v_safe

    def test_08_latency_monotonicity(self):
        """TEST 08: Increasing reaction/ECU latency must increase or maintain stopping distance."""
        dist_prev = 0.0
        # Latency sweeps from 0.0s to 1.0s
        a_dec = 2.5
        for latency in [0.0, 0.1, 0.25, 0.5, 0.75, 1.0]:
            dist = calculate_stopping_distance(10.0, a_dec, latency)
            self.assertTrue(dist >= dist_prev, f"Monotonicity violated: {dist} < {dist_prev} as latency increased.")
            dist_prev = dist

if __name__ == "__main__":
    unittest.main()
