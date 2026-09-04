"""
FOG-ORCHESTRATOR 2.0 — IMU Processor Adapter (Blocker 6 Resolution)

Converts MPU6050 raw LSB sensor values to canonical physical units (m/s^2, rad/s).
Exposes explicit quality indicators ("VALID" vs "NOT_CALIBRATED") rather than
fabricating orientation or uncalibrated values.
"""

import math
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger("IMUProcessor")

class IMUProcessor:
    """Processes raw ESP32 MPU6050 telemetry into canonical physical IMU state."""

    ACCEL_SCALE_FACTOR = 16384.0  # LSB / g for +/- 2g range
    GYRO_SCALE_FACTOR = 131.0     # LSB / (deg/s) for +/- 250 deg/s range
    GRAVITY_MPS2 = 9.81

    def __init__(self, is_calibrated: bool = False):
        self.is_calibrated = is_calibrated

    def process(self, raw_imu_dict: Dict[str, Any]) -> Dict[str, Any]:
        """
        Accepts dict containing raw LSB or physical values (AcX, AcY, AcZ, GyX, GyY, GyZ or ax, ay, az).
        Returns canonical IMU state.
        """
        if not raw_imu_dict or not isinstance(raw_imu_dict, dict):
            return {
                "acceleration_mps2": {"x": 0.0, "y": 0.0, "z": self.GRAVITY_MPS2},
                "angular_velocity_rads": {"x": 0.0, "y": 0.0, "z": 0.0},
                "estimated_pitch": None,
                "estimated_roll": None,
                "quality": "INVALID"
            }

        # Check if already normalized physical floats
        if "acceleration" in raw_imu_dict:
            acc = raw_imu_dict["acceleration"]
            gyro = raw_imu_dict.get("gyroscope", {"x": 0.0, "y": 0.0, "z": 0.0})
            ax = float(acc.get("x", 0.0))
            ay = float(acc.get("y", 0.0))
            az = float(acc.get("z", self.GRAVITY_MPS2))
            gx = float(gyro.get("x", 0.0))
            gy = float(gyro.get("y", 0.0))
            gz = float(gyro.get("z", 0.0))
        else:
            # Parse raw LSB values
            ac_x = float(raw_imu_dict.get("AcX", 0))
            ac_y = float(raw_imu_dict.get("AcY", 0))
            ac_z = float(raw_imu_dict.get("AcZ", 16384))
            gy_x = float(raw_imu_dict.get("GyX", 0))
            gy_y = float(raw_imu_dict.get("GyY", 0))
            gy_z = float(raw_imu_dict.get("GyZ", 0))

            ax = (ac_x / self.ACCEL_SCALE_FACTOR) * self.GRAVITY_MPS2
            ay = (ac_y / self.ACCEL_SCALE_FACTOR) * self.GRAVITY_MPS2
            az = (ac_z / self.ACCEL_SCALE_FACTOR) * self.GRAVITY_MPS2

            gx = (gy_x / self.GYRO_SCALE_FACTOR) * (math.pi / 180.0)
            gy = (gy_y / self.GYRO_SCALE_FACTOR) * (math.pi / 180.0)
            gz = (gy_z / self.GYRO_SCALE_FACTOR) * (math.pi / 180.0)

        quality = "VALID" if self.is_calibrated else "NOT_CALIBRATED"

        return {
            "acceleration_mps2": {
                "x": round(ax, 3),
                "y": round(ay, 3),
                "z": round(az, 3)
            },
            "angular_velocity_rads": {
                "x": round(gx, 4),
                "y": round(gy, 4),
                "z": round(gz, 4)
            },
            "estimated_pitch": None,
            "estimated_roll": None,
            "quality": quality
        }
