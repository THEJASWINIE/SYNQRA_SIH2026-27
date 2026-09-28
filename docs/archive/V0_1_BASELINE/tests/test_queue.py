import unittest
from models.queue_model import calculate_next_queue_size, ServiceQueue

class MockVehicle:
    def __init__(self, v_id: str):
        self.id = v_id
        self.state = "idle"
        self.speed_mps = 0.0
        self.acceleration_mps2 = 0.0
        self.is_loaded = False
        
    def load_cargo(self):
        self.is_loaded = True
        
    def unload_cargo(self):
        self.is_loaded = False

class TestQueue(unittest.TestCase):
    
    def test_11_queue_conservation(self):
        """TEST 11: Verify queue conservation (Q_new = Q_old + arrivals - departures)."""
        q = 5.0
        q_new = calculate_next_queue_size(q, 3.0, 2.0)
        self.assertEqual(q_new, 6.0)
        
        # Test zero floor limit
        q_floor = calculate_next_queue_size(1.0, 0.0, 5.0)
        self.assertEqual(q_floor, 0.0)

    def test_12_queue_growth(self):
        """TEST 12: Verify queue growth when arrival > service capacity."""
        # Crusher service queue at 10 vph (service time = 360 seconds)
        srv_queue = ServiceQueue("CRUSHER", 10.0)
        self.assertEqual(srv_queue.service_time_s, 360.0)
        
        # Add 3 trucks
        v1 = MockVehicle("V1")
        v2 = MockVehicle("V2")
        v3 = MockVehicle("V3")
        
        srv_queue.add_vehicle(v1)
        srv_queue.add_vehicle(v2)
        srv_queue.add_vehicle(v3)
        self.assertEqual(srv_queue.length, 3)
        
        # Step simulation by 100 seconds (service time is 360s, so no discharge yet)
        discharged = srv_queue.step(100.0)
        self.assertEqual(len(discharged), 0)
        self.assertEqual(srv_queue.length, 3)

    def test_13_queue_recovery(self):
        """TEST 13: Verify queue recovery/dissipation when service is applied over time."""
        # Shovel at 30 vph (service time = 120s)
        srv_queue = ServiceQueue("SHOVEL", 30.0)
        self.assertEqual(srv_queue.service_time_s, 120.0)
        
        v1 = MockVehicle("V1")
        v2 = MockVehicle("V2")
        srv_queue.add_vehicle(v1)
        srv_queue.add_vehicle(v2)
        
        # Step by 130 seconds (1 vehicle should be discharged)
        discharged = srv_queue.step(130.0)
        self.assertEqual(len(discharged), 1)
        self.assertEqual(discharged[0].id, "V1")
        self.assertEqual(srv_queue.length, 1)
        
        # Step by another 120 seconds (the second vehicle should be discharged)
        discharged = srv_queue.step(120.0)
        self.assertEqual(len(discharged), 1)
        self.assertEqual(discharged[0].id, "V2")
        self.assertEqual(srv_queue.length, 0)

if __name__ == "__main__":
    unittest.main()
