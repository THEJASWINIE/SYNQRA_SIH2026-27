"""
FOG-ORCHESTRATOR 2.0 — Mock Vehicle Telemetry Generator for HMI Independent Validation

IMPORTANT:
This module has ZERO dependencies on Digital Twin, Mine simulation, Fog physics engine,
Vehicle simulator, or Orchestrator. It exists exclusively for HMI validation (System A).
"""

import time
import math
import random
import requests
from typing import Dict, Any, List


class MockVehicleGenerator:
    """
    Independent Mock Telemetry Generator for System A (HMI).
    Simulates Vehicle A (TRUCK_01 - nominal) and Vehicle B (TRUCK_02 - comm degradation test).
    """

    def __init__(self, backend_url: str = "http://localhost:8000"):
        self.backend_url = backend_url
        self.wheel_radius_m = 0.5
        self.time_step = 0.0

        # State for Vehicle A (TRUCK_01 - Nominal)
        self.veh_a = {
            "vehicle_id": "TRUCK_01",
            "speed_mps": 8.0,
            "rpm": 150.0,
            "acceleration_mps2": 0.2,
            "communication_health": "HEALTHY",
            "communication_state": "HEALTHY",
            "safety_state": "NORMAL",
            "mode": "traveling",
            "stale_threshold_s": 5.0,
            "last_update_ts": time.time()
        }

        # State for Vehicle B (TRUCK_02 - Degraded / Stale Test)
        self.veh_b = {
            "vehicle_id": "TRUCK_02",
            "speed_mps": 5.0,
            "rpm": 95.0,
            "acceleration_mps2": -0.1,
            "communication_health": "DEGRADED",
            "communication_state": "COMMUNICATION_DEGRADED",
            "safety_state": "COMMUNICATION_DEGRADED",
            "mode": "traveling",
            "stale_threshold_s": 5.0,
            "last_update_ts": time.time() - 10.0  # Deliberately stale (10s old)
        }

    def update(self, dt_s: float = 0.5) -> List[Dict[str, Any]]:
        """Updates simulated telemetry state for Vehicle A and Vehicle B."""
        self.time_step += dt_s
        now = time.time()

        # Update Vehicle A (TRUCK_01) - Varying speed & RPM smoothly
        speed_a = 8.0 + 3.0 * math.sin(0.5 * self.time_step)
        rpm_a = (speed_a * 60.0) / (2.0 * math.pi * self.wheel_radius_m)
        acc_a = 1.5 * math.cos(0.5 * self.time_step)

        self.veh_a.update({
            "timestamp": now,
            "speed_mps": round(speed_a, 2),
            "speed_kmh": round(speed_a * 3.6, 2),
            "rpm": round(rpm_a, 1),
            "acceleration_mps2": round(acc_a, 2),
            "communication_health": "HEALTHY",
            "communication_state": "HEALTHY",
            "safety_state": "NORMAL" if speed_a < 12.0 else "CAUTION",
            "last_update_ts": now
        })

        # Update Vehicle B (TRUCK_02) - Comm degradation & stale timestamp test
        speed_b = 4.0 + 1.5 * math.cos(0.3 * self.time_step)
        rpm_b = (speed_b * 60.0) / (2.0 * math.pi * self.wheel_radius_m)
        
        # Keep timestamp stale (older than 5.0 seconds threshold) for stale data testing
        stale_timestamp = now - 12.0

        self.veh_b.update({
            "timestamp": stale_timestamp,
            "speed_mps": round(speed_b, 2),
            "speed_kmh": round(speed_b * 3.6, 2),
            "rpm": round(rpm_b, 1),
            "acceleration_mps2": -0.2,
            "communication_health": "DEGRADED",
            "communication_state": "COMMUNICATION_DEGRADED",
            "safety_state": "COMMUNICATION_DEGRADED",
            "last_update_ts": stale_timestamp
        })

        return [self.veh_a, self.veh_b]

    def push_to_backend(self) -> bool:
        """Pushes telemetry frame to independent HMI backend REST API."""
        telemetry_list = self.update()
        success = True
        for veh in telemetry_list:
            try:
                res = requests.post(
                    f"{self.backend_url}/api/telemetry",
                    json=veh,
                    timeout=2.0
                )
                if res.status_code != 200:
                    success = False
            except Exception:
                success = False
        return success


if __name__ == "__main__":
    generator = MockVehicleGenerator()
    print("Starting Mock Vehicle Telemetry Generator...")
    for _ in range(5):
        frames = generator.update()
        print(f"Vehicle A: {frames[0]['vehicle_id']} -> Speed: {frames[0]['speed_kmh']} km/h, RPM: {frames[0]['rpm']}")
        print(f"Vehicle B: {frames[1]['vehicle_id']} -> State: {frames[1]['communication_state']} (Stale TS: {frames[1]['timestamp']:.1f})")
        time.sleep(0.5)
