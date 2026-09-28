import unittest
from models.switchback import SwitchbackCoordinator

class TestSwitchback(unittest.TestCase):
    def test_01_no_overlap(self):
        coord = SwitchbackCoordinator(priority_policy="fifo")
        approved1, t_s1 = coord.request_slot("SB_01", 10.0, 20.0, "TRUCK_01")
        approved2, t_s2 = coord.request_slot("SB_01", 25.0, 35.0, "TRUCK_02")
        
        self.assertTrue(approved1)
        self.assertEqual(t_s1, 10.0)
        self.assertTrue(approved2)
        self.assertEqual(t_s2, 25.0)

    def test_02_overlap_rejection(self):
        coord = SwitchbackCoordinator(priority_policy="fifo")
        approved1, t_s1 = coord.request_slot("SB_01", 10.0, 20.0, "TRUCK_01")
        approved2, t_s2 = coord.request_slot("SB_01", 15.0, 25.0, "TRUCK_02")
        
        self.assertTrue(approved1)
        self.assertFalse(approved2)
        self.assertEqual(t_s2, 20.0)  # Suggested start time is end of TRUCK_01 slot

    def test_03_priority_loaded_downhill(self):
        coord = SwitchbackCoordinator(priority_policy="loaded_downhill")
        p_loaded_down = coord.get_priority("TRUCK_01", is_loaded=True, grade_percent=-8.0, speed_mps=10.0, mass_kg=165000.0)
        p_empty_up = coord.get_priority("TRUCK_02", is_loaded=False, grade_percent=4.0, speed_mps=10.0, mass_kg=74000.0)
        
        self.assertTrue(p_loaded_down > p_empty_up)

    def test_04_priority_stopping_difficulty(self):
        coord = SwitchbackCoordinator(priority_policy="stopping_difficulty")
        p_heavy_down = coord.get_priority("TRUCK_01", is_loaded=True, grade_percent=-8.0, speed_mps=12.0, mass_kg=165000.0)
        p_light_flat = coord.get_priority("TRUCK_02", is_loaded=False, grade_percent=0.0, speed_mps=8.0, mass_kg=74000.0)
        
        self.assertTrue(p_heavy_down > p_light_flat)
