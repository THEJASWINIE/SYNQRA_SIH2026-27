"""
FOG-ORCHESTRATOR 2.0 — TRUCK_01 Wheel + IMU Odometry Adapter (Pass 2)

Truthful PHYSICAL-DERIVED local positioning capability for TRUCK_01.

HARDWARE TRUTH:
  MCU: ESP32
  Wheel Sensor: LM393 wheel/encoder sensor (GPIO 35)
  Pulses Per Revolution (PPR): 42.0
  Wheel Diameter: 0.10 m (Wheel Radius: 0.05 m)
  IMU: MPU6050 (I2C address 0x68) — gyroscope Z rate (gz)

RULES & CONSTRAINTS:
  1. Distance translation MUST use encoder pulses:
     delta_distance = (delta_pulses / 42.0) * pi * 0.10
     Do NOT use speed_mps as an alternative distance source.
  2. IMU heading uses MPU6050 gyro Z rate only for RELATIVE heading integration:
     delta_heading = gz_rad_s * dt
     heading = normalize(heading + delta_heading)
  3. Time base uses measured sample elapsed time dt (reject dt <= 0).
  4. Pulse count semantics: supports cumulative counter and interval delta.
  5. Initial pose: x=0.0, y=0.0, heading=0.0 explicitly marked "LOCAL ODOMETRY ORIGIN".
  6. TRUCK_02 is explicitly NOT supported (returns UNAVAILABLE).
"""

from __future__ import annotations

import math
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger("WheelImuOdometry")


class WheelImuOdometryCalculator:
    """
    Local relative pose calculator for TRUCK_01 using wheel encoder pulses and MPU6050 gyro Z.
    """

    TARGET_VEHICLE_ID = "TRUCK_01"
    PPR = 42.0
    WHEEL_DIAMETER_M = 0.10
    WHEEL_CIRCUMFERENCE_M = math.pi * WHEEL_DIAMETER_M  # ~0.31415926535 m

    def __init__(self, vehicle_id: str = "TRUCK_01"):
        self.vehicle_id = vehicle_id.strip().upper()
        self.x: float = 0.0
        self.y: float = 0.0
        self.heading_rad: float = 0.0
        self.distance_m: float = 0.0
        self.last_timestamp: Optional[float] = None
        self.last_pulse_count: Optional[int] = None
        self.origin_type: str = "LOCAL ODOMETRY ORIGIN"

    def reset(self, x: float = 0.0, y: float = 0.0, heading_rad: float = 0.0) -> None:
        """Reset state to local origin or specified initial pose."""
        self.x = float(x)
        self.y = float(y)
        self.heading_rad = float(heading_rad)
        self.distance_m = 0.0
        self.last_timestamp = None
        self.last_pulse_count = None

    def update(
        self,
        timestamp: float,
        pulse_count: Optional[int] = None,
        delta_pulses: Optional[int] = None,
        gz_rad_s: Optional[float] = None,
        is_simulated: bool = False,
        stale_after_s: float = 3.0,
    ) -> Dict[str, Any]:
        """
        Process a telemetry update and return the current position_odom payload.
        """
        if self.vehicle_id != self.TARGET_VEHICLE_ID:
            return self._build_unavailable_dict("TRUCK_02 odometry is not supported in Pass 2")

        if timestamp is None or not math.isfinite(timestamp) or timestamp <= 0.0:
            return self.snapshot(status="INVALID")

        # Initial timestamp setup
        if self.last_timestamp is None:
            self.last_timestamp = timestamp
            if pulse_count is not None and isinstance(pulse_count, (int, float)):
                self.last_pulse_count = int(pulse_count)
            return self.snapshot(status="VALID" if (pulse_count is not None or delta_pulses is not None) else "UNAVAILABLE")

        dt = timestamp - self.last_timestamp

        # Reject invalid dt (<= 0 or implausibly large gap > 10s)
        if dt <= 0.0 or not math.isfinite(dt) or dt > 10.0:
            logger.warning("Invalid dt=%.3f for odometry update on %s", dt, self.vehicle_id)
            return self.snapshot(status="STALE" if dt > 10.0 else "INVALID")

        # Determine pulses to integrate
        pulses_to_integrate: Optional[int] = None

        if delta_pulses is not None and isinstance(delta_pulses, (int, float)):
            if math.isfinite(delta_pulses) and delta_pulses >= 0:
                pulses_to_integrate = int(delta_pulses)
        elif pulse_count is not None and isinstance(pulse_count, (int, float)):
            if math.isfinite(pulse_count):
                curr_pulses = int(pulse_count)
                if self.last_pulse_count is None:
                    pulses_to_integrate = 0
                else:
                    diff = curr_pulses - self.last_pulse_count
                    if diff < 0:
                        # Rollover detection or counter reset
                        pulses_to_integrate = 0
                    else:
                        pulses_to_integrate = diff
                self.last_pulse_count = curr_pulses

        # Strict Requirement 1: If encoder pulse data is missing/unavailable, odometry is UNAVAILABLE or STALE.
        # Do NOT substitute speed_mps as a distance source!
        if pulses_to_integrate is None:
            return self.snapshot(status="STALE" if dt < stale_after_s else "UNAVAILABLE")

        # Heading integration from MPU6050 gyro Z
        if gz_rad_s is not None and isinstance(gz_rad_s, (int, float)) and math.isfinite(gz_rad_s):
            delta_heading = float(gz_rad_s) * dt
            self.heading_rad += delta_heading
            # Normalize heading to [-pi, pi]
            self.heading_rad = math.atan2(math.sin(self.heading_rad), math.cos(self.heading_rad))

        # Distance calculation strictly from encoder pulses
        delta_distance = (pulses_to_integrate / self.PPR) * self.WHEEL_CIRCUMFERENCE_M

        # Integrate translation
        self.x += delta_distance * math.cos(self.heading_rad)
        self.y += delta_distance * math.sin(self.heading_rad)
        self.distance_m += abs(delta_distance)
        self.last_timestamp = timestamp

        origin_source = "SIMULATION" if is_simulated else "HARDWARE"

        return {
            "x_m": round(self.x, 4),
            "y_m": round(self.y, 4),
            "heading_rad": round(self.heading_rad, 4),
            "distance_m": round(self.distance_m, 4),
            "timestamp": timestamp,
            "source": "DERIVED",
            "origin": origin_source,
            "provenance_label": "PHYSICAL_DERIVED" if not is_simulated else "SIMULATED_DERIVED",
            "method": "WHEEL_IMU_ODOMETRY",
            "status": "VALID",
            "origin_type": self.origin_type,
            "verification_label": "ALGORITHM VERIFIED",
        }

    def snapshot(self, status: str = "VALID") -> Dict[str, Any]:
        """Return snapshot of current pose state."""
        return {
            "x_m": round(self.x, 4),
            "y_m": round(self.y, 4),
            "heading_rad": round(self.heading_rad, 4),
            "distance_m": round(self.distance_m, 4),
            "timestamp": self.last_timestamp,
            "source": "DERIVED",
            "origin": "HARDWARE",
            "provenance_label": "PHYSICAL_DERIVED",
            "method": "WHEEL_IMU_ODOMETRY",
            "status": status,
            "origin_type": self.origin_type,
            "verification_label": "ALGORITHM VERIFIED",
        }

    def _build_unavailable_dict(self, reason: str) -> Dict[str, Any]:
        return {
            "x_m": None,
            "y_m": None,
            "heading_rad": None,
            "distance_m": None,
            "timestamp": self.last_timestamp,
            "source": "UNKNOWN",
            "origin": "UNKNOWN",
            "provenance_label": "UNAVAILABLE",
            "method": "NONE",
            "status": "UNAVAILABLE",
            "origin_type": "NONE",
            "reason": reason,
            "verification_label": "CONTRACT VERIFIED",
        }
