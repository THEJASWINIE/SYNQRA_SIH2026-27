"""
FOG-ORCHESTRATOR 2.0 — Wireless Vehicle Telemetry Software Emulator

Simulates dual Wi-Fi Direct and redundant V2V relay telemetry paths for Vehicle A (TRUCK_01)
and Vehicle B (TRUCK_02) across Scenarios A, B, C, D, and E.
"""

import time
import logging
from typing import Dict, Any, List

logger = logging.getLogger("WirelessVehicleEmulator")

class WirelessVehicleEmulator:
    """Simulates wireless telemetry frames across direct Wi-Fi and V2V relay paths."""

    def __init__(self):
        self.seq_map = {"TRUCK_01": 1, "TRUCK_02": 1}

    def generate_payload(self, vehicle_id: str, source: str, rpm: float = 240.0,
                         speed: float = None, seq_override: int = None,
                         rssi: int = -75, snr: float = 9.5) -> Dict[str, Any]:
        """Generates canonical payload matching POST /api/hardware/telemetry schema."""
        if seq_override is not None:
            seq = seq_override
        else:
            seq = self.seq_map.get(vehicle_id, 1)
            self.seq_map[vehicle_id] = seq + 1

        return {
            "vehicle_id": vehicle_id,
            "sequence": seq,
            "rpm": float(rpm),
            "speed": speed,
            "ax": -496,
            "ay": 132,
            "az": 16696,
            "gx": 703,
            "gy": 342,
            "gz": 191,
            "rssi": rssi,
            "snr": snr,
            "source": source,
            "timestamp": time.time()
        }

    def run_scenario(self, scenario_code: str) -> List[Dict[str, Any]]:
        """
        Executes one of the 5 failover scenarios (A, B, C, D, E):
        - Scenario A: A Wi-Fi ON, B Wi-Fi ON, A LoRa ON
        - Scenario B: A Wi-Fi OFF, B Wi-Fi ON, A LoRa ON (A visible via V2V relay)
        - Scenario C: B completely OFF (Critical failover: A DIRECT_WIFI, B OFFLINE)
        - Scenario D: B Wi-Fi OFF, B LoRa ON
        - Scenario E: A Wi-Fi ON, B Wi-Fi ON, A LoRa OFF
        """
        code = scenario_code.upper()
        payloads = []

        if code == "A":
            # Scenario A: All active
            seq_a = self.seq_map["TRUCK_01"]
            payloads.append(self.generate_payload("TRUCK_01", "DIRECT_WIFI", rpm=240.0, seq_override=seq_a))
            payloads.append(self.generate_payload("TRUCK_01", "V2V_VIA_TRUCK_02", rpm=240.0, seq_override=seq_a))  # Duplicate over relay
            payloads.append(self.generate_payload("TRUCK_02", "DIRECT_WIFI", rpm=180.0))
            self.seq_map["TRUCK_01"] = seq_a + 1

        elif code == "B":
            # Scenario B: A Wi-Fi OFF, B Wi-Fi ON, A LoRa ON (A relayed through B)
            seq_a = self.seq_map["TRUCK_01"]
            payloads.append(self.generate_payload("TRUCK_01", "V2V_VIA_TRUCK_02", rpm=240.0, seq_override=seq_a))
            payloads.append(self.generate_payload("TRUCK_02", "DIRECT_WIFI", rpm=180.0))
            self.seq_map["TRUCK_01"] = seq_a + 1

        elif code == "C":
            # Scenario C: B completely OFF (Critical Failover)
            payloads.append(self.generate_payload("TRUCK_01", "DIRECT_WIFI", rpm=240.0))
            # No payload for TRUCK_02

        elif code == "D":
            # Scenario D: B Wi-Fi OFF, B LoRa ON
            payloads.append(self.generate_payload("TRUCK_01", "DIRECT_WIFI", rpm=240.0))
            # TRUCK_02 Wi-Fi down, so no payload to HMI from TRUCK_02

        elif code == "E":
            # Scenario E: A Wi-Fi ON, B Wi-Fi ON, A LoRa OFF
            payloads.append(self.generate_payload("TRUCK_01", "DIRECT_WIFI", rpm=240.0))
            payloads.append(self.generate_payload("TRUCK_02", "DIRECT_WIFI", rpm=180.0))

        return payloads
