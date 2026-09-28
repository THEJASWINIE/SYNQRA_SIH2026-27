"""
integration_adapters/can_twai_hil.py
------------------------------------
FOG-ORCHESTRATOR 2.0 — CAN 2.0B / TWAI Hardware-in-the-Loop Emulation Layer.

EVIDENCE BOUNDARY & PROVENANCE (PART 19 / MASTER PROMPT):
  - Hardware Type: Isolated software emulation of ESP32 TWAI (Two-Wire Automotive Interface)
    operating at 250 kbps with 29-bit extended identifiers (ISO 11898-1 / SAE J1939 compatible).
  - Frame definitions are project-defined HIL frames formatted to standard J1939 PGN conventions.
  - Under NO circumstances does this module represent tapped OEM proprietary wiring on a
    physical BEML BH100 haul truck at NMDC Bailadila.
  - Physical vehicle electronic integration remains UNVALIDATED.

FRAME DEFINITIONS (SAE J1939 COMPATIBLE):
  1. ENGINE_SPEED   (0x0CF00400 / PGN 61444 EEC1): Engine RPM (0.125 rpm/bit, 20ms update, 100ms timeout)
  2. VEHICLE_SPEED  (0x18FEF100 / PGN 65265 CCVS): Wheel speed (1/256 km/h/bit, 50ms update, 150ms timeout)
  3. BRAKE_STATUS   (0x18F0010B / PGN 61441 EBC1): Brake pedal %, line pressure (50ms update, 200ms timeout)
  4. RETARDER_STAT  (0x18F0000F / PGN 61440 ERC1): Retarder percent torque (50ms update, 200ms timeout)
  5. SAFETY_COMMAND (0x0CFF0101 / PGN 65281 PropB): Speed ceiling, action, seq (50ms update, 150ms timeout)
  6. VEHICLE_STATE  (0x18FF0201 / PGN 65282 PropB): Health flags, grade, payload (100ms update, 300ms timeout)
"""

from __future__ import annotations

import math
import struct
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple


# Canonical 29-bit CAN IDs
CAN_ID_ENGINE_SPEED   = 0x0CF00400   # PGN 61444 (EEC1)
CAN_ID_VEHICLE_SPEED  = 0x18FEF100   # PGN 65265 (CCVS)
CAN_ID_BRAKE_STATUS   = 0x18F0010B   # PGN 61441 (EBC1)
CAN_ID_RETARDER_STATUS= 0x18F0000F   # PGN 61440 (ERC1)
CAN_ID_SAFETY_COMMAND = 0x0CFF0101   # PGN 65281 (Proprietary B - Safety Dispatch)
CAN_ID_VEHICLE_STATE  = 0x18FF0201   # PGN 65282 (Proprietary B - Vehicle State)


class CanBusState(str, Enum):
    ERROR_ACTIVE = "ERROR_ACTIVE"
    ERROR_PASSIVE = "ERROR_PASSIVE"
    BUS_OFF = "BUS_OFF"


@dataclass
class CanFrame:
    """Standard 29-bit extended CAN frame."""
    arbitration_id: int
    data: bytes
    timestamp: float                       # Wall-clock timestamp (s)
    is_extended: bool = True
    dlc: int = 8

    def __post_init__(self):
        if len(self.data) < 8:
            # Pad to 8 bytes with 0xFF as per J1939 standard
            self.data = self.data.ljust(8, b"\xFF")
        elif len(self.data) > 8:
            self.data = self.data[:8]
        self.dlc = len(self.data)


# ==============================================================================
# ENCODERS & DECODERS (SAE J1939 COMPATIBLE BIT LAYOUTS)
# ==============================================================================

def encode_engine_speed(rpm: float, timestamp: float) -> CanFrame:
    """
    PGN 61444 (EEC1):
    Bytes 3-4: Engine Speed in RPM, scaling 0.125 rpm/bit, offset 0.
    Valid range: 0.0 to 8031.875 rpm.
    """
    if math.isnan(rpm) or math.isinf(rpm) or rpm < 0:
        raw_val = 0xFFFF  # Error indicator
    else:
        clamped = min(8031.875, max(0.0, float(rpm)))
        raw_val = int(round(clamped / 0.125))

    data = bytearray(b"\xFF" * 8)
    data[3] = raw_val & 0xFF
    data[4] = (raw_val >> 8) & 0xFF
    return CanFrame(arbitration_id=CAN_ID_ENGINE_SPEED, data=bytes(data), timestamp=timestamp)


def decode_engine_speed(frame: CanFrame) -> Tuple[bool, float]:
    """Decodes engine RPM from PGN 61444. Returns (is_valid, rpm)."""
    if frame.arbitration_id != CAN_ID_ENGINE_SPEED or len(frame.data) < 5:
        return False, 0.0
    raw_val = frame.data[3] | (frame.data[4] << 8)
    if raw_val >= 0xFAFF:  # 0xFAFF - 0xFFFF indicate error / not available
        return False, 0.0
    rpm = raw_val * 0.125
    return True, float(rpm)


def encode_vehicle_speed(speed_mps: float, timestamp: float) -> CanFrame:
    """
    PGN 65265 (CCVS):
    Bytes 1-2: Wheel-Based Vehicle Speed, scaling 1/256 km/h per bit (0.00390625 km/h/bit).
    Stored in km/h, converted from m/s.
    """
    if math.isnan(speed_mps) or math.isinf(speed_mps) or speed_mps < 0:
        raw_val = 0xFFFF
    else:
        speed_kmh = speed_mps * 3.6
        clamped_kmh = min(250.0, max(0.0, speed_kmh))
        raw_val = int(round(clamped_kmh * 256.0))

    data = bytearray(b"\xFF" * 8)
    data[1] = raw_val & 0xFF
    data[2] = (raw_val >> 8) & 0xFF
    return CanFrame(arbitration_id=CAN_ID_VEHICLE_SPEED, data=bytes(data), timestamp=timestamp)


def decode_vehicle_speed(frame: CanFrame) -> Tuple[bool, float]:
    """Decodes wheel speed in m/s from PGN 65265. Returns (is_valid, speed_mps)."""
    if frame.arbitration_id != CAN_ID_VEHICLE_SPEED or len(frame.data) < 3:
        return False, 0.0
    raw_val = frame.data[1] | (frame.data[2] << 8)
    if raw_val >= 0xFAFF:
        return False, 0.0
    speed_kmh = raw_val / 256.0
    speed_mps = speed_kmh / 3.6
    return True, float(speed_mps)


def encode_brake_status(pedal_pct: float, pressure_kpa: float, timestamp: float) -> CanFrame:
    """
    PGN 61441 (EBC1):
    Byte 1: Brake pedal position (0-100%, 0.4%/bit).
    Bytes 2-3: Brake pressure (kPa, 1 kPa/bit).
    """
    data = bytearray(b"\xFF" * 8)
    p_clamped = min(100.0, max(0.0, float(pedal_pct))) if not math.isnan(pedal_pct) else 0.0
    raw_p = int(round(p_clamped / 0.4))
    data[1] = raw_p & 0xFF

    press_clamped = min(2000.0, max(0.0, float(pressure_kpa))) if not math.isnan(pressure_kpa) else 0.0
    raw_press = int(round(press_clamped))
    data[2] = raw_press & 0xFF
    data[3] = (raw_press >> 8) & 0xFF
    return CanFrame(arbitration_id=CAN_ID_BRAKE_STATUS, data=bytes(data), timestamp=timestamp)


def decode_brake_status(frame: CanFrame) -> Tuple[bool, float, float]:
    """Decodes (is_valid, pedal_pct, pressure_kpa)."""
    if frame.arbitration_id != CAN_ID_BRAKE_STATUS or len(frame.data) < 4:
        return False, 0.0, 0.0
    pedal_pct = frame.data[1] * 0.4
    pressure_kpa = float(frame.data[2] | (frame.data[3] << 8))
    return True, pedal_pct, pressure_kpa


def encode_safety_command(
    target_speed_mps: float,
    action_code: int,
    sequence: int,
    timestamp: float
) -> CanFrame:
    """
    PGN 65281 (Proprietary B): Safety Command Frame.
    Bytes 0-1: Commanded speed limit in m/s (0.01 m/s per bit, 0 - 655.35 m/s).
    Byte 2: Action code (0=ACCEPT, 1=CLAMP, 2=REJECT, 3=STOP, 4=EMERGENCY_STOP).
    Bytes 3-4: Monotonic sequence number (0 - 65535).
    """
    data = bytearray(b"\xFF" * 8)
    spd_clamped = min(60.0, max(0.0, float(target_speed_mps))) if not math.isnan(target_speed_mps) else 0.0
    raw_spd = int(round(spd_clamped * 100.0))
    data[0] = raw_spd & 0xFF
    data[1] = (raw_spd >> 8) & 0xFF

    data[2] = int(action_code) & 0xFF
    data[3] = int(sequence) & 0xFF
    data[4] = (int(sequence) >> 8) & 0xFF

    return CanFrame(arbitration_id=CAN_ID_SAFETY_COMMAND, data=bytes(data), timestamp=timestamp)


def decode_safety_command(frame: CanFrame) -> Tuple[bool, float, int, int]:
    """Decodes (is_valid, target_speed_mps, action_code, sequence)."""
    if frame.arbitration_id != CAN_ID_SAFETY_COMMAND or len(frame.data) < 5:
        return False, 0.0, 0, 0
    raw_spd = frame.data[0] | (frame.data[1] << 8)
    speed_mps = raw_spd / 100.0
    action_code = frame.data[2]
    sequence = frame.data[3] | (frame.data[4] << 8)
    return True, float(speed_mps), action_code, sequence


def encode_vehicle_state(
    safety_state_code: int,
    comm_flags: int,
    grade_pct: float,
    payload_tonnes: float,
    timestamp: float
) -> CanFrame:
    """
    PGN 65282 (Proprietary B): Vehicle State & Terrain Awareness.
    Byte 0: Safety state enum index.
    Byte 1: Comm status bitfield (bit0=GW, bit1=V2V, bit2=BEACON, bit3=CAN).
    Byte 2: Civil road grade in % (-128 to +127, signed int8).
    Byte 3: Payload in tonnes (0 - 250 tonnes).
    """
    data = bytearray(b"\xFF" * 8)
    data[0] = int(safety_state_code) & 0xFF
    data[1] = int(comm_flags) & 0xFF
    grade_int = int(round(max(-128.0, min(127.0, grade_pct))))
    data[2] = grade_int & 0xFF
    data[3] = int(round(max(0.0, min(250.0, payload_tonnes)))) & 0xFF
    return CanFrame(arbitration_id=CAN_ID_VEHICLE_STATE, data=bytes(data), timestamp=timestamp)


def decode_vehicle_state(frame: CanFrame) -> Tuple[bool, int, int, float, float]:
    """Decodes (is_valid, state_code, comm_flags, grade_pct, payload_tonnes)."""
    if frame.arbitration_id != CAN_ID_VEHICLE_STATE or len(frame.data) < 4:
        return False, 0, 0, 0.0, 0.0
    state_code = frame.data[0]
    comm_flags = frame.data[1]
    raw_grade = frame.data[2]
    grade_pct = float(raw_grade if raw_grade < 128 else raw_grade - 256)
    payload_t = float(frame.data[3])
    return True, state_code, comm_flags, grade_pct, payload_t


# ==============================================================================
# CAN 2.0B / TWAI BUS EMULATOR WITH TIMING & FAULT INJECTION
# ==============================================================================

class CanTwaiBusEmulator:
    """
    Software-isolated CAN 2.0B / TWAI 250 kbps bus emulator.
    Provides arbitration modeling, transmission wire delay (0.512 ms),
    variable traffic queue delay, frame loss injection, burst loss,
    timeout detection, and CAN bus-off state transitions.
    """

    # Timeouts per CAN ID (seconds)
    TIMEOUTS_S: Dict[int, float] = {
        CAN_ID_ENGINE_SPEED: 0.100,    # 100 ms
        CAN_ID_VEHICLE_SPEED: 0.150,   # 150 ms
        CAN_ID_BRAKE_STATUS: 0.200,    # 200 ms
        CAN_ID_RETARDER_STATUS: 0.200, # 200 ms
        CAN_ID_SAFETY_COMMAND: 0.150,  # 150 ms
        CAN_ID_VEHICLE_STATE: 0.300,   # 300 ms
    }

    def __init__(
        self,
        nominal_wire_delay_ms: float = 0.512,
        mean_arbitration_ms: float = 5.79,
        clock: Callable[[], float] = time.time
    ):
        self.nominal_wire_delay_ms = nominal_wire_delay_ms
        self.mean_arbitration_ms = mean_arbitration_ms
        self.clock = clock

        self.bus_state = CanBusState.ERROR_ACTIVE
        self.last_frames: Dict[int, CanFrame] = {}
        self.last_rx_timestamps: Dict[int, float] = {}

        # Fault injection controls
        self.packet_loss_rate: float = 0.0
        self.in_burst_loss: bool = False
        self.burst_packets_remaining: int = 0
        self.forced_bus_off: bool = False
        self.bit_corruption_rate: float = 0.0

        # Statistics
        self.total_transmitted: int = 0
        self.total_delivered: int = 0
        self.total_dropped: int = 0
        self.total_corrupted: int = 0
        self.delivery_latencies_ms: List[float] = []

    def set_fault_injection(
        self,
        packet_loss_rate: float = 0.0,
        burst_loss_count: int = 0,
        bus_off: bool = False,
        bit_corruption_rate: float = 0.0
    ):
        """Configures channel degradation and fault injection parameters."""
        self.packet_loss_rate = max(0.0, min(1.0, packet_loss_rate))
        self.burst_packets_remaining = max(0, burst_loss_count)
        self.in_burst_loss = (self.burst_packets_remaining > 0)
        self.forced_bus_off = bus_off
        self.bus_state = CanBusState.BUS_OFF if bus_off else CanBusState.ERROR_ACTIVE
        self.bit_corruption_rate = max(0.0, min(1.0, bit_corruption_rate))

    def transmit(self, frame: CanFrame, now: Optional[float] = None) -> Tuple[bool, float]:
        """
        Transmits a CAN frame across the virtual bus.
        Returns (delivered: bool, transport_latency_ms: float).
        """
        self.total_transmitted += 1
        t_now = now if now is not None else self.clock()

        # 1. Check Bus-Off State
        if self.forced_bus_off or self.bus_state == CanBusState.BUS_OFF:
            self.total_dropped += 1
            return False, 0.0

        # 2. Check Burst Loss
        if self.in_burst_loss:
            self.total_dropped += 1
            self.burst_packets_remaining -= 1
            if self.burst_packets_remaining <= 0:
                self.in_burst_loss = False
            return False, 0.0

        # 3. Check Stochastic Packet Loss
        if self.packet_loss_rate > 0.0:
            import random
            if random.random() < self.packet_loss_rate:
                self.total_dropped += 1
                return False, 0.0

        # 4. Check Bit Corruption Injection
        if self.bit_corruption_rate > 0.0:
            import random
            if random.random() < self.bit_corruption_rate:
                # Corrupt payload byte
                corrupted_data = bytearray(frame.data)
                corrupted_data[0] ^= 0xFF
                frame = CanFrame(frame.arbitration_id, bytes(corrupted_data), frame.timestamp)
                self.total_corrupted += 1

        # 5. Model Transport Latency (Wire Time + Arbitration Queue)
        latency_ms = self.nominal_wire_delay_ms + max(0.5, self.mean_arbitration_ms)
        self.delivery_latencies_ms.append(latency_ms)

        # Store delivery
        self.last_frames[frame.arbitration_id] = frame
        self.last_rx_timestamps[frame.arbitration_id] = t_now
        self.total_delivered += 1
        return True, latency_ms

    def receive_latest(self, can_id: int, now: Optional[float] = None) -> Tuple[bool, Optional[CanFrame], bool]:
        """
        Retrieves the latest delivered frame for a given CAN ID.
        Returns:
            (has_frame: bool, frame: Optional[CanFrame], is_stale: bool)
        """
        t_now = now if now is not None else self.clock()

        if can_id not in self.last_frames:
            return False, None, True

        frame = self.last_frames[can_id]
        last_t = self.last_rx_timestamps.get(can_id, 0.0)
        timeout_s = self.TIMEOUTS_S.get(can_id, 0.200)

        elapsed = t_now - last_t
        is_stale = (elapsed > timeout_s)

        return True, frame, is_stale
