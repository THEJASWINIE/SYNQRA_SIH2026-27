import unittest
from models.bottleneck import calculate_bottleneck_score

class TestBottleneck(unittest.TestCase):
    
    def test_14_crusher_bottleneck_detection(self):
        """TEST 14: Verify bottleneck score prioritizes constrained crusher node."""
        # Baseline rates: Shovel service (15 vph), Crusher service (18 vph)
        # 1. Under normal operating conditions: Shovel queue = 1, Crusher queue = 0
        b_sh_normal = calculate_bottleneck_score(arrival_rate_vph=15.0, service_rate_vph=15.0, 
                                                 queue_length=1, criticality=2.0)
        # b_sh = (1.0 * (15/15)) * (1.0 + 0.5 * 1) * (1.0 * 2.0) = 1.0 * 1.5 * 2.0 = 3.0
        
        b_cr_normal = calculate_bottleneck_score(arrival_rate_vph=15.0, service_rate_vph=18.0, 
                                                 queue_length=0, criticality=4.0)
        # b_cr = (1.0 * (15/18)) * (1.0 + 0.5 * 0) * (1.0 * 4.0) = 0.833 * 1.0 * 4.0 = 3.33
        
        # 2. Under Crusher constraint (service rate = 10 vph) and queue builds up to 3 trucks
        b_cr_constrained = calculate_bottleneck_score(arrival_rate_vph=15.0, service_rate_vph=10.0, 
                                                      queue_length=3, criticality=4.0)
        # b_cr = (1.0 * (15/10)) * (1.0 + 0.5 * 3) * (1.0 * 4.0) = 1.5 * 2.5 * 4.0 = 15.0
        
        # Crusher score must become significantly higher than normal shovel
        self.assertTrue(b_cr_constrained > b_sh_normal)
        self.assertTrue(b_cr_constrained > b_cr_normal)

if __name__ == "__main__":
    unittest.main()
