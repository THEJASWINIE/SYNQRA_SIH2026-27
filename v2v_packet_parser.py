"""
FOG-ORCHESTRATOR 2.0 — V2V Packet Parser & Ingestion Adapter

Parses frozen V2V radio protocol packets:
STATE,<VEHICLE_ID>,<SEQ>,<RPM>,<SPEED>,<AX>,<AY>,<AZ>,<GX>,<GY>,<GZ>

Validates message types, sequence continuity, duplicate/out-of-order packets,
communication health (ONLINE, STALE, OFFLINE, RECOVERING), and normalizes raw LSB IMU values
without crashing the backend on malformed input.
"""

import time
import math
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger("V2VPacketParser")

class V2VPacketParser:
    """Non-crashing V2V Telemetry Packet Parser and Ingestion Adapter."""

    ACCEL_LSB_PER_G = 16384.0
    GYRO_LSB_PER_DEG = 131.0
    GRAVITY_MPS2 = 9.81
    DEG_TO_RAD = math.pi / 180.0

    def __init__(self, stale_sec: float = 3.0, offline_sec: float = 10.0):
        self.stale_sec = stale_sec
        self.offline_sec = offline_sec
        self.sequence_trackers: Dict[str, int] = {}
        self.seen_sequences: Dict[str, set] = {}
        self.last_seen_map: Dict[str, float] = {}
        self.previous_health_map: Dict[str, str] = {}
        self.recovery_counters: Dict[str, int] = {}

    def parse_v2v_packet(self, raw_packet: str, rssi: int = -75, snr: float = 9.5) -> Optional[Dict[str, Any]]:
        """
        Parses V2V packet string:
        STATE,TRUCK_01,28,240.00,0.00,-496,132,16696,703,342,191
        Or comma-appended metadata line:
        STATE,TRUCK_01,28,240.00,0.00,-496,132,16696,703,342,191,RSSI=-78,SNR=9.75
        """
        if not raw_packet or not isinstance(raw_packet, str):
            logger.warning("[V2VPacketParser] Malformed input: Packet is empty or not string")
            return None

        line = raw_packet.strip()
        if not line.startswith("STATE,") and ",STATE," not in line:
            # Safely reject non-STATE packets (e.g. PING/ACK) without crashing
            logger.info(f"[V2VPacketParser] Non-STATE packet received: '{line}'")
            return None

        # Handle appended RSSI/SNR metadata
        tokens = [t.strip() for t in line.split(",") if t.strip()]
        if len(tokens) < 11:
            logger.warning(f"[V2VPacketParser] Malformed input: Insufficient field count ({len(tokens)} < 11)")
            return None

        # Check for appended RSSI/SNR key-value pairs
        parsed_rssi = rssi
        parsed_snr = snr
        clean_tokens = []
        for token in tokens:
            if "RSSI=" in token.upper():
                try:
                    parsed_rssi = int(token.split("=")[1])
                except (ValueError, IndexError):
                    pass
            elif "SNR=" in token.upper():
                try:
                    parsed_snr = float(token.split("=")[1])
                except (ValueError, IndexError):
                    pass
            else:
                clean_tokens.append(token)

        if len(clean_tokens) < 11:
            logger.warning(f"[V2VPacketParser] Malformed input: Clean tokens < 11 after metadata extraction")
            return None

        msg_type = clean_tokens[0].upper()
        if msg_type != "STATE":
            return None

        vid = clean_tokens[1].upper()
        if vid not in ["TRUCK_01", "TRUCK_02"]:
            logger.warning(f"[V2VPacketParser] Unknown vehicle ID '{vid}' rejected")
            return None

        # Parse numeric fields safely
        try:
            seq = int(clean_tokens[2])
            rpm = float(clean_tokens[3])
            raw_speed = float(clean_tokens[4])
            ax_lsb = int(clean_tokens[5])
            ay_lsb = int(clean_tokens[6])
            az_lsb = int(clean_tokens[7])
            gx_lsb = int(clean_tokens[8])
            gy_lsb = int(clean_tokens[9])
            gz_lsb = int(clean_tokens[10])
        except (ValueError, TypeError) as e:
            logger.warning(f"[V2VPacketParser] Numeric parsing error in packet '{line}': {e}")
            return None

        now = time.time()

        # Sequence & duplicate tracking
        seen_set = self.seen_sequences.setdefault(vid, set())
        is_duplicate = seq in seen_set
        seen_set.add(seq)

        last_seq = self.sequence_trackers.get(vid, 0)
        is_out_of_order = (seq < last_seq) and not is_duplicate
        if seq > last_seq:
            self.sequence_trackers[vid] = seq

        # Health state evaluation
        prev_health = self.previous_health_map.get(vid, "ONLINE")
        if prev_health in ["OFFLINE", "STALE"]:
            cnt = self.recovery_counters.get(vid, 0) + 1
            self.recovery_counters[vid] = cnt
            health_status = "ONLINE" if cnt >= 2 else "RECOVERING"
        else:
            health_status = "ONLINE"

        self.previous_health_map[vid] = health_status
        self.last_seen_map[vid] = now

        # Convert raw LSB to physical units (m/s^2, rad/s)
        ax_mps2 = round((ax_lsb / self.ACCEL_LSB_PER_G) * self.GRAVITY_MPS2, 3)
        ay_mps2 = round((ay_lsb / self.ACCEL_LSB_PER_G) * self.GRAVITY_MPS2, 3)
        az_mps2 = round((az_lsb / self.ACCEL_LSB_PER_G) * self.GRAVITY_MPS2, 3)

        gx_rads = round((gx_lsb / self.GYRO_LSB_PER_DEG) * self.DEG_TO_RAD, 4)
        gy_rads = round((gy_lsb / self.GYRO_LSB_PER_DEG) * self.DEG_TO_RAD, 4)
        gz_rads = round((gz_lsb / self.GYRO_LSB_PER_DEG) * self.DEG_TO_RAD, 4)

        return {
            "vehicle_id": vid,
            "source": "V2V",
            "sequence_number": seq,
            "rpm": max(0.0, rpm),
            "speed": None,
            "speed_value": round(raw_speed, 2),
            "speed_unit": "m/s",
            "speed_calibrated": False,  # Explicit uncalibrated marker
            "acceleration": {
                "x": ax_mps2,
                "y": ay_mps2,
                "z": az_mps2
            },
            "gyroscope": {
                "x": gx_rads,
                "y": gy_rads,
                "z": gz_rads
            },
            "raw_imu": {
                "ax": ax_lsb,
                "ay": ay_lsb,
                "az": az_lsb,
                "gx": gx_lsb,
                "gy": gy_lsb,
                "gz": gz_lsb
            },
            "communication": {
                "status": health_status,
                "last_seen": now,
                "rssi": parsed_rssi,
                "snr": parsed_snr
            },
            "communication_status": health_status,
            "communication_state": "HEALTHY" if health_status in ["ONLINE", "RECOVERING"] else "COMMUNICATION_DEGRADED",
            "safety_state": "NORMAL",
            "data_quality": "LIVE" if health_status == "ONLINE" else health_status,
            "is_duplicate": is_duplicate,
            "is_out_of_order": is_out_of_order,
            "stale_threshold_s": self.stale_sec,
            "offline_threshold_s": self.offline_sec,
            "timestamp": now
        }

    def evaluate_health_status(self, vehicle_id: str, current_time: float) -> str:
        """Evaluates health state (ONLINE, STALE, OFFLINE, RECOVERING) based on current timestamp."""
        last_seen = self.last_seen_map.get(vehicle_id)
        if last_seen is None:
            self.previous_health_map[vehicle_id] = "OFFLINE"
            return "OFFLINE"

        age = current_time - last_seen
        if age <= self.stale_sec:
            return self.previous_health_map.get(vehicle_id, "ONLINE")
        elif age <= self.offline_sec:
            self.previous_health_map[vehicle_id] = "STALE"
            return "STALE"
        else:
            self.previous_health_map[vehicle_id] = "OFFLINE"
            return "OFFLINE"
