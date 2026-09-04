"""
FOG-ORCHESTRATOR 2.0 — V2V Telemetry Software Emulator

Generates deterministic software V2V telemetry streams matching the exact frozen protocol:
STATE,<VEHICLE_ID>,<SEQ>,<RPM>,<SPEED>,<AX>,<AY>,<AZ>,<GX>,<GY>,<GZ>

Supports Scenarios 1 through 13 for automated HMI software compatibility testing.
"""

import time
import math
import random
import logging
from typing import Dict, Any, List, Generator

logger = logging.getLogger("V2VTelemetryEmulator")

class V2VTelemetryEmulator:
    """Deterministic V2V Telemetry Stream Generator."""

    def __init__(self):
        self.seq_map = {"TRUCK_01": 1, "TRUCK_02": 1}

    def generate_packet(self, vehicle_id: str, rpm: float = 240.0, speed: float = 0.0,
                        ax: int = -496, ay: int = 132, az: int = 16696,
                        gx: int = 703, gy: int = 342, gz: int = 191,
                        seq_override: int = None) -> str:
        """Generates single valid V2V STATE packet string."""
        if seq_override is not None:
            seq = seq_override
        else:
            seq = self.seq_map.get(vehicle_id, 1)
            self.seq_map[vehicle_id] = seq + 1

        return f"STATE,{vehicle_id},{seq},{rpm:.2f},{speed:.2f},{ax},{ay},{az},{gx},{gy},{gz}"

    def run_scenario(self, scenario_id: int) -> List[Dict[str, Any]]:
        """Executes one of the 13 test scenarios and returns generated packets with metadata."""
        packets = []
        now = time.time()

        if scenario_id == 1:
            # SCENARIO 1: Both vehicles healthy
            p1 = self.generate_packet("TRUCK_01", rpm=240.0)
            p2 = self.generate_packet("TRUCK_02", rpm=180.0)
            packets.append({"packet": p1, "delay": 0.0, "rssi": -78, "snr": 9.75})
            packets.append({"packet": p2, "delay": 0.1, "rssi": -82, "snr": 8.50})

        elif scenario_id == 2:
            # SCENARIO 2: TRUCK_01 speed/RPM changes
            for r in [120.0, 240.0, 360.0]:
                p = self.generate_packet("TRUCK_01", rpm=r)
                packets.append({"packet": p, "delay": 0.1, "rssi": -75, "snr": 10.0})

        elif scenario_id == 3:
            # SCENARIO 3: TRUCK_02 speed/RPM changes
            for r in [90.0, 180.0, 270.0]:
                p = self.generate_packet("TRUCK_02", rpm=r)
                packets.append({"packet": p, "delay": 0.1, "rssi": -80, "snr": 9.0})

        elif scenario_id == 4:
            # SCENARIO 4: Vehicle A telemetry stops
            p_b = self.generate_packet("TRUCK_02", rpm=180.0)
            packets.append({"packet": p_b, "delay": 0.0, "rssi": -80, "snr": 9.0})

        elif scenario_id == 5:
            # SCENARIO 5: Vehicle B telemetry stops
            p_a = self.generate_packet("TRUCK_01", rpm=240.0)
            packets.append({"packet": p_a, "delay": 0.0, "rssi": -78, "snr": 9.75})

        elif scenario_id == 6:
            # SCENARIO 6: Packet delay
            p = self.generate_packet("TRUCK_01", rpm=240.0)
            packets.append({"packet": p, "delay": 3.5, "rssi": -88, "snr": 6.0})

        elif scenario_id == 7:
            # SCENARIO 7: Packet loss (Gap in sequence)
            s_curr = self.seq_map["TRUCK_01"]
            p = self.generate_packet("TRUCK_01", rpm=240.0, seq_override=s_curr + 5)
            self.seq_map["TRUCK_01"] = s_curr + 6
            packets.append({"packet": p, "delay": 0.0, "rssi": -78, "snr": 9.75})

        elif scenario_id == 8:
            # SCENARIO 8: Duplicate sequence
            s_curr = self.seq_map["TRUCK_01"]
            p1 = self.generate_packet("TRUCK_01", rpm=240.0, seq_override=s_curr)
            p2 = self.generate_packet("TRUCK_01", rpm=240.0, seq_override=s_curr)
            packets.append({"packet": p1, "delay": 0.0, "rssi": -78, "snr": 9.75})
            packets.append({"packet": p2, "delay": 0.05, "rssi": -78, "snr": 9.75})

        elif scenario_id == 9:
            # SCENARIO 9: Out-of-order sequence
            p_high = self.generate_packet("TRUCK_01", rpm=240.0, seq_override=100)
            p_low = self.generate_packet("TRUCK_01", rpm=240.0, seq_override=50)
            packets.append({"packet": p_high, "delay": 0.0, "rssi": -78, "snr": 9.75})
            packets.append({"packet": p_low, "delay": 0.05, "rssi": -78, "snr": 9.75})

        elif scenario_id == 10:
            # SCENARIO 10: Malformed packet
            packets.append({"packet": "STATE,TRUCK_01,CORRUPTED_FEILD_COUNT", "delay": 0.0, "rssi": -78, "snr": 9.75})

        elif scenario_id == 11:
            # SCENARIO 11: Unknown vehicle ID
            p = self.generate_packet("TRUCK_99", rpm=240.0)
            packets.append({"packet": p, "delay": 0.0, "rssi": -78, "snr": 9.75})

        elif scenario_id == 12:
            # SCENARIO 12: Unexpected message type (PING/ACK)
            packets.append({"packet": "PING,TRUCK_01,1,OK", "delay": 0.0, "rssi": -78, "snr": 9.75})
            packets.append({"packet": "ACK,TRUCK_01,1,ACCEPTED", "delay": 0.0, "rssi": -78, "snr": 9.75})

        elif scenario_id == 13:
            # SCENARIO 13: Recovery after communication loss (2 consecutive packets)
            p1 = self.generate_packet("TRUCK_01", rpm=240.0)
            p2 = self.generate_packet("TRUCK_01", rpm=240.0)
            packets.append({"packet": p1, "delay": 0.0, "rssi": -78, "snr": 9.75})
            packets.append({"packet": p2, "delay": 0.2, "rssi": -78, "snr": 9.75})

        return packets
