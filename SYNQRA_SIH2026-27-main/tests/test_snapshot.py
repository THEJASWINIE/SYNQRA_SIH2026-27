import unittest
import os
import yaml
from twin.network import MineNetwork
from twin.simulator import Simulator
from interfaces.simulation_snapshot import SimulationSnapshot, VehicleSnapshot

class TestSimulationSnapshot(unittest.TestCase):
    def setUp(self):
        # Load configurations
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
            
        self.sim = Simulator(self.network, self.vehicle_cfg, self.weather_cfg, self.scenario_cfg)

    def test_snapshot_creation(self):
        snapshot = SimulationSnapshot.from_simulator(self.sim, "clear")
        
        # Verify basic dataclass attributes
        self.assertEqual(snapshot.timestamp, 0.0)
        self.assertEqual(snapshot.scenario, "clear")
        self.assertEqual(len(snapshot.vehicles), len(self.sim.vehicles))
        
        # Verify dict serialization
        snap_dict = snapshot.to_dict()
        self.assertEqual(snap_dict["timestamp"], 0.0)
        self.assertEqual(len(snap_dict["vehicles"]), len(self.sim.vehicles))
        self.assertEqual(snap_dict["vehicles"][0]["id"], "TRUCK_01")
