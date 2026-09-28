import unittest
import json
import numpy as np
import yaml
import os
import copy
from twin.network import MineNetwork
from twin.simulator import Simulator
from interfaces.task1_hmi import HMIInterface
from interfaces.task3_vehicle_io import TelemetryAdapter

class TestInterfaces(unittest.TestCase):
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
            
        self.sim = Simulator(self.network, self.vehicle_cfg, self.weather_cfg, self.scenario_cfg)

    def test_01_hmi_state_packaging(self):
        # Package current state vector
        state_vector = HMIInterface.package_hmi_state(
            timestamp=self.sim.current_time,
            scenario_name="clear",
            network=self.sim.network,
            vehicles=self.sim.vehicles,
            shaping_active=self.sim.shaping_active,
            shovel_delay=15.0
        )
        
        self.assertEqual(state_vector["timestamp"], 0.0)
        self.assertEqual(state_vector["scenario"], "clear")
        self.assertEqual(len(state_vector["vehicle_states"]), len(self.sim.vehicles))
        self.assertFalse(state_vector["warning_fault"])

    def test_waiting_for_release_mapping(self):
        # Mock a vehicle in 'waiting_for_release' state
        vehicles = copy.deepcopy(self.sim.vehicles)
        vehicles[0].state = "waiting_for_release"
        
        state_vector = HMIInterface.package_hmi_state(
            timestamp=self.sim.current_time,
            scenario_name="clear",
            network=self.sim.network,
            vehicles=vehicles,
            shaping_active=self.sim.shaping_active,
            shovel_delay=15.0
        )
        
        # Verify it is mapped to 'queued' in the packaged state vector
        self.assertEqual(state_vector["vehicle_states"][0]["state"], "queued")

    def test_02_telemetry_adapter_ingestion(self):
        adapter = TelemetryAdapter(self.sim, stale_threshold_s=5.0)
        
        # Valid telemetry packet
        packet = {
            "vehicle_id": "TRUCK_01",
            "timestamp": 12.0,
            "speed_mps": 8.5,
            "acceleration_mps2": 0.5,
            "brake_state": False,
            "retarder_state": False,
            "comm_confidence": 0.98
        }
        
        success = adapter.ingest_telemetry(json.dumps(packet))
        self.assertTrue(success)
        
        # Check that TRUCK_01 state inside simulator was synchronized
        t1 = next(v for v in self.sim.vehicles if v.id == "TRUCK_01")
        self.assertEqual(t1.speed_mps, 8.5)
        self.assertEqual(t1.acceleration_mps2, 0.5)
        self.assertEqual(getattr(t1, "comm_confidence", 0.0), 0.98)

    def test_03_telemetry_adapter_invalid_packet(self):
        adapter = TelemetryAdapter(self.sim)
        # Invalid packet (missing required brake_state)
        packet = {
            "vehicle_id": "TRUCK_01",
            "timestamp": 12.0,
            "speed_mps": 8.5
        }
        
        success = adapter.ingest_telemetry(json.dumps(packet))
        self.assertFalse(success)

    def test_04_telemetry_staleness_fallback(self):
        adapter = TelemetryAdapter(self.sim, stale_threshold_s=3.0)
        
        packet = {
            "vehicle_id": "TRUCK_01",
            "timestamp": 10.0,
            "speed_mps": 8.5,
            "brake_state": False
        }
        adapter.ingest_telemetry(json.dumps(packet))
        
        # Check staleness at sim time 12.0s (difference = 2.0s <= threshold 3.0s)
        stale = adapter.verify_communication_liveness(current_sim_time=12.0)
        self.assertEqual(len(stale), 0)
        
        # Check staleness at sim time 15.0s (difference = 5.0s > threshold 3.0s)
        stale = adapter.verify_communication_liveness(current_sim_time=15.0)
        self.assertIn("TRUCK_01", stale)
        
        # Verify that safe speed of TRUCK_01 was reduced in local safety governor fallback
        t1 = next(v for v in self.sim.vehicles if v.id == "TRUCK_01")
        self.assertEqual(t1.v_safe_mps, 2.78)
