import unittest
from models.road_capacity import calculate_road_capacity

class TestCapacity(unittest.TestCase):
    
    def test_10_capacity_calculation(self):
        """TEST 10: Verify road capacity formula and bounds."""
        # 1. Normal clear conditions: v = 13.89 m/s, H_safe = 30m
        cap = calculate_road_capacity(13.89, 30.0, 15.5)
        # expected: 3600 * 13.89 / 30.0 = 1666.8 vehicles/hour
        self.assertAlmostEqual(cap, 3600.0 * 13.89 / 30.0)
        
        # 2. Stopped conditions: v = 0.0, capacity must be 0
        cap_zero = calculate_road_capacity(0.0, 20.0, 15.5)
        self.assertEqual(cap_zero, 0.0)
        
        # 3. Dynamic responsiveness: capacity should decrease if H_safe increases
        cap_high_headway = calculate_road_capacity(10.0, 50.0, 15.5)
        cap_low_headway = calculate_road_capacity(10.0, 20.0, 15.5)
        self.assertTrue(cap_high_headway < cap_low_headway)

    def test_headway_validity(self):
        """TEST 09: Enforce physical packaging margin. Headway must not go below min_headway."""
        # Even if safe headway is calculated as 5.0m, the function must use min_headway (15.5m)
        cap_short = calculate_road_capacity(10.0, 5.0, 15.5)
        cap_expected = 3600.0 * 10.0 / 15.5
        self.assertAlmostEqual(cap_short, cap_expected)

if __name__ == "__main__":
    unittest.main()
