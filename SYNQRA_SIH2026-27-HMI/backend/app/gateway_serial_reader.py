"""
FOG-ORCHESTRATOR 2.0 — USB Serial Gateway Reader & Telemetry Normalizer

Reads LoRa Gateway USB Serial packets, parses canonical key-value strings,
tracks vehicle communication health (ONLINE, STALE, OFFLINE), and forwards
normalized vehicle state updates to the HMI backend store and WebSockets.
"""

import time
import json
import threading
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger("GatewaySerialReader")

class GatewayTelemetryParser:
    """Parses and validates compact LoRa telemetry key-value strings."""

    _sequence_counters: Dict[str, int] = {}

    @classmethod
    def parse_packet(cls, raw_line: str, provenance_source: str = "SIMULATION") -> Optional[Dict[str, Any]]:
        """
        Parses string format:
        V=TRUCK_01,SEQ=101,RPM=240.0,SPD=2.50,AX=0.12,AY=-0.05,AZ=9.81,GX=0.02,GY=0.01,GZ=-0.03,RSSI=-65,SNR=9.2
        Or Command ACK format:
        ACK_ID=CMD_101,V=TRUCK_01,STATUS=CLAMPED,APPLIED=10.87
        """
        if not raw_line:
            return None

        line = raw_line.strip()
        tokens = line.split(",")
        kv_map = {}
        for token in tokens:
            if "=" in token:
                k, v = token.split("=", 1)
                kv_map[k.strip().upper()] = v.strip()

        # Check for Command ACK
        if "ACK_ID" in kv_map or "ACK" in kv_map:
            ack_id = kv_map.get("ACK_ID") or kv_map.get("ACK")
            vid = kv_map.get("V", "TRUCK_01")
            status = kv_map.get("STATUS", "ACCEPTED")
            try:
                applied = float(kv_map.get("APPLIED", 0.0))
            except ValueError:
                applied = 0.0
            return {
                "type": "command_ack",
                "provenance_source": provenance_source,
                "command_id": ack_id,
                "vehicle_id": vid,
                "status": status,
                "applied_speed": applied,
                "timestamp": time.time()
            }

        vid = kv_map.get("V")
        if not vid:
            return None

        now = time.time()
        try:
            # Parse sequence number or auto-increment
            if "SEQ" in kv_map:
                seq_num = int(kv_map["SEQ"])
            else:
                cls._sequence_counters[vid] = cls._sequence_counters.get(vid, 0) + 1
                seq_num = cls._sequence_counters[vid]

            rpm = float(kv_map.get("RPM", 0.0))
            spd = float(kv_map.get("SPD", 0.0))
            ax = float(kv_map.get("AX", 0.0))
            ay = float(kv_map.get("AY", 0.0))
            az = float(kv_map.get("AZ", 9.81))
            gx = float(kv_map.get("GX", 0.0))
            gy = float(kv_map.get("GY", 0.0))
            gz = float(kv_map.get("GZ", 0.0))
            rssi = int(kv_map.get("RSSI", -65))
            snr = float(kv_map.get("SNR", 9.0))
        except (ValueError, TypeError):
            return None

        # Segmented latency estimation
        # T_E2E = T_LoRa (~15ms) + T_Gateway (~2ms) + T_Serial (~3ms) + T_Backend (~2ms) + T_WebSocket (~3ms)
        t_lora_ms = 15.0
        t_gateway_ms = 2.0
        t_serial_ms = 3.0
        t_backend_ms = 2.0
        t_websocket_ms = 3.0
        latency_ms = round(t_lora_ms + t_gateway_ms + t_serial_ms + t_backend_ms + t_websocket_ms, 2)

        # Determine safety state based on motion & comms
        safety_state = "NORMAL"
        if spd > 12.0:
            safety_state = "CAUTION"

        return {
            "vehicle_id": vid,
            # P3 PROVENANCE: HARDWARE only when this record genuinely came off the serial
            # port. The simulated fallback loop below stamps SIMULATION so a disconnected
            # gateway can never masquerade as live hardware.
            "provenance_source": provenance_source,
            "sequence_number": seq_num,
            "timestamp": now,
            "latency_ms": latency_ms,
            "rpm": max(0.0, rpm),
            "speed_mps": max(0.0, spd),
            "speed_kmh": round(spd * 3.6, 2),
            "acceleration": {
                "x": ax,
                "y": ay,
                "z": az
            },
            "gyroscope": {
                "x": gx,
                "y": gy,
                "z": gz
            },
            "communication": {
                "status": "ONLINE",
                "last_seen": now,
                "rssi": rssi,
                "snr": snr,
                "latency_ms": latency_ms
            },
            "communication_state": "HEALTHY",
            "safety_state": safety_state,
            "mode": "traveling" if spd > 0.1 else "idle",
            "stale_threshold_s": 3.0,
            "offline_threshold_s": 10.0
        }


class CommunicationHealthMonitor:
    """Evaluates ONLINE, STALE, DEGRADED, OFFLINE, and RECOVERING health states for active vehicles."""

    def __init__(self, stale_sec: float = 3.0, offline_sec: float = 10.0):
        self.stale_sec = stale_sec
        self.offline_sec = offline_sec
        self.last_seen_map: Dict[str, float] = {}
        self.previous_state_map: Dict[str, str] = {}
        self.recovery_count_map: Dict[str, int] = {}

    def record_heartbeat(self, vehicle_id: str, timestamp: float):
        prev_state = self.previous_state_map.get(vehicle_id, "ONLINE")
        if prev_state == "OFFLINE":
            # Initiate recovery phase
            self.previous_state_map[vehicle_id] = "RECOVERING"
            self.recovery_count_map[vehicle_id] = 1
        elif prev_state == "RECOVERING":
            cnt = self.recovery_count_map.get(vehicle_id, 1) + 1
            self.recovery_count_map[vehicle_id] = cnt
            if cnt >= 2:
                self.previous_state_map[vehicle_id] = "ONLINE"
        else:
            self.previous_state_map[vehicle_id] = "ONLINE"

        self.last_seen_map[vehicle_id] = timestamp

    def evaluate_health(self, vehicle_id: str, current_time: float) -> str:
        last_seen = self.last_seen_map.get(vehicle_id)
        if last_seen is None:
            self.previous_state_map[vehicle_id] = "OFFLINE"
            return "OFFLINE"

        age = current_time - last_seen
        if age <= self.stale_sec:
            state = self.previous_state_map.get(vehicle_id, "ONLINE")
            return state
        elif age <= self.offline_sec:
            self.previous_state_map[vehicle_id] = "STALE"
            return "STALE"
        else:
            self.previous_state_map[vehicle_id] = "OFFLINE"
            return "OFFLINE"


class GatewaySerialReader:
    """Manages USB Serial connection to LoRa Gateway."""

    def __init__(self, port: str = "COM3", baudrate: int = 115200, is_simulated: bool = False):
        self.port = port
        self.baudrate = baudrate
        self.is_simulated = is_simulated
        self.running = False
        self.thread: Optional[threading.Thread] = None
        self.health_monitor = CommunicationHealthMonitor()
        self.callback = None

    def start(self, callback):
        self.callback = callback
        self.running = True
        self.thread = threading.Thread(target=self._run_loop, daemon=True)
        self.thread.start()

    def stop(self):
        self.running = False
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=1.0)

    def _run_loop(self):
        if self.is_simulated:
            self._run_simulated_loop()
            return

        try:
            import serial
            ser = serial.Serial(self.port, self.baudrate, timeout=1.0)
            while self.running:
                line = ser.readline().decode('utf-8', errors='ignore')
                if line:
                    # Genuine bytes off the physical gateway.
                    parsed = GatewayTelemetryParser.parse_packet(line, provenance_source="HARDWARE")
                    if parsed:
                        vid = parsed["vehicle_id"]
                        self.health_monitor.record_heartbeat(vid, parsed["timestamp"])
                        if self.callback:
                            self.callback(parsed)
        except Exception as e:
            logger.warning(f"Serial port {self.port} unavailable ({e}). Falling back to simulated hardware mode.")
            self._run_simulated_loop()

    def _run_simulated_loop(self):
        """
        Simulates incoming gateway serial lines when the physical USB gateway is absent.

        P3: every record produced here is stamped provenance_source="SIMULATION". It is
        NOT physical telemetry and must never be reported as a hardware measurement.
        """
        logger.warning(
            "GatewaySerialReader running in SIMULATED fallback mode - emitted telemetry is "
            "SIMULATION, not hardware."
        )
        step = 0
        while self.running:
            step += 1
            now = time.time()
            # Simulated Vehicle A (TRUCK_01)
            rpm_a = 240.0 + 20.0 * (step % 5)
            spd_a = (rpm_a * 3.14159 * 0.10) / 60.0
            pkt_a = f"V=TRUCK_01,RPM={rpm_a:.1f},SPD={spd_a:.2f},AX=0.12,AY=-0.05,AZ=9.81,GX=0.02,GY=0.01,GZ=-0.03,RSSI=-62,SNR=9.5"
            parsed_a = GatewayTelemetryParser.parse_packet(pkt_a, provenance_source="SIMULATION")
            if parsed_a and self.callback:
                self.health_monitor.record_heartbeat("TRUCK_01", now)
                self.callback(parsed_a)

            time.sleep(0.5)

            # Simulated Vehicle B (TRUCK_02)
            rpm_b = 180.0 + 15.0 * (step % 4)
            spd_b = (rpm_b * 3.14159 * 0.085) / 60.0
            pkt_b = f"V=TRUCK_02,RPM={rpm_b:.1f},SPD={spd_b:.2f},AX=-0.04,AY=0.01,AZ=9.79,GX=0.00,GY=0.01,GZ=0.00,RSSI=-75,SNR=7.8"
            parsed_b = GatewayTelemetryParser.parse_packet(pkt_b, provenance_source="SIMULATION")
            if parsed_b and self.callback:
                self.health_monitor.record_heartbeat("TRUCK_02", now)
                self.callback(parsed_b)

            time.sleep(0.5)
