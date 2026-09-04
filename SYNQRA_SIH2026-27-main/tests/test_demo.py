import unittest
import os
import yaml
from twin.network import MineNetwork
from scenarios.demo_v01 import run_scenario

class TestDemo(unittest.TestCase):
    
    def setUp(self):
        # Load configs
        config_dir = "config"
        with open(os.path.join(config_dir, "vehicle.yaml"), "r") as f:
            self.vehicle_cfg = yaml.safe_load(f)
        with open(os.path.join(config_dir, "roads.yaml"), "r") as f:
            self.roads_cfg = yaml.safe_load(f)
        with open(os.path.join(config_dir, "nodes.yaml"), "r") as f:
            self.nodes_cfg = yaml.safe_load(f)
        with open(os.path.join(config_dir, "weather.yaml"), "r") as f:
            self.weather_cfg = yaml.safe_load(f)
        with open(os.path.join(config_dir, "scenarios.yaml"), "r") as f:
            self.scenario_cfg = yaml.safe_load(f)
            
        # Build network
        self.network = MineNetwork()
        for n in self.nodes_cfg["nodes"]:
            self.network.add_node(n["id"], n["type"], n["service_rate_vph"], n["criticality"])
        for r in self.roads_cfg["segments"]:
            self.network.add_edge(
                road_id=r["road_id"], start_node=r["start_node"], end_node=r["end_node"],
                length_m=r["length_m"], grade_percent=r["grade_percent"],
                curve_radius_m=r["curve_radius_m"], speed_limit_mps=r["speed_limit_mps"],
                width_m=r["width_m"]
            )

    def test_17_safety_command_constraint(self):
        """TEST 17: Enforce that v_command <= v_safe holds at every single timestep for all vehicles."""
        # We run the full vertical slice scenario, which has the most environmental transitions
        history = run_scenario("DEMO_06_FULL_VERTICAL_SLICE", self.network, 
                               self.vehicle_cfg, self.weather_cfg, self.scenario_cfg)
        
        # Check every frame and every vehicle
        for frame in history:
            for v in frame["vehicle_states"]:
                # The commanded speed must NEVER exceed the local physical safe speed ceiling
                self.assertTrue(
                    v["v_command"] <= v["v_safe"] + 1e-5,
                    f"Safety violation at t={frame['timestamp']}s for {v['id']}: v_cmd={v['v_command']} > v_safe={v['v_safe']}"
                )

    def test_15_arrival_shaping(self):
        """TEST 15: Verify that enabling arrival shaping stabilizes the crusher queue under constraint."""
        # Case A: Without arrival shaping
        history_off = run_scenario("DEMO_05_ARRIVAL_SHAPING_OFF", self.network,
                                    self.vehicle_cfg, self.weather_cfg, self.scenario_cfg)
        max_q_off = max(next(n["queue_length"] for n in f["node_states"] if n["node_id"] == "CRUSHER") for f in history_off)
        
        # Case B: With arrival shaping
        history_on = run_scenario("DEMO_05_ARRIVAL_SHAPING_ON", self.network,
                                   self.vehicle_cfg, self.weather_cfg, self.scenario_cfg)
        max_q_on = max(next(n["queue_length"] for n in f["node_states"] if n["node_id"] == "CRUSHER") for f in history_on)
        
        # Shaping must stabilize the queue (max queue length with shaping should be smaller than without)
        print(f"Max Crusher Queue (Shaping OFF): {max_q_off} | Max Crusher Queue (Shaping ON): {max_q_on}")
        self.assertTrue(max_q_on < max_q_off)

    def test_16_fog_recovery(self):
        """TEST 16: Verify that fog clearing allows safe speed and capacity recovery."""
        history = run_scenario("DEMO_03_FOG_RECOVERY", self.network,
                               self.vehicle_cfg, self.weather_cfg, self.scenario_cfg)
        
        # Recovery starts at 600s, ends at 1500s (600 + 900s)
        # Check that capacity and speed at the end are higher than during dense fog (before 600s)
        frame_fog = history[300]     # t=300s, still in dense fog
        frame_clear = history[1700]  # t=1700s, fully cleared
        
        r2_fog = next(r for r in frame_fog["road_states"] if r["road_id"] == "ROAD_2")
        r2_clear = next(r for r in frame_clear["road_states"] if r["road_id"] == "ROAD_2")
        
        self.assertTrue(r2_clear["safe_speed_mps"] > r2_fog["safe_speed_mps"])
        self.assertTrue(r2_clear["capacity_vph"] > r2_fog["capacity_vph"])

if __name__ == "__main__":
    unittest.main()
