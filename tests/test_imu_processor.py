"""
Unit tests for IMUProcessor adapter.
Tests conversion of raw MPU6050 LSB values to physical m/s^2 and rad/s,
gravity vector validation, and uncalibrated orientation exposure ("NOT_CALIBRATED").
"""

import pytest
from integration_adapters.imu_processor import IMUProcessor

def test_imu_raw_lsb_conversion():
    processor = IMUProcessor(is_calibrated=False)
    raw_imu = {
        "AcX": 0,
        "AcY": 0,
        "AcZ": 16384,  # 1.0g = 9.81 m/s^2
        "GyX": 0,
        "GyY": 0,
        "GyZ": 0
    }
    processed = processor.process(raw_imu)
    assert processed["acceleration_mps2"]["z"] == 9.81
    assert processed["acceleration_mps2"]["x"] == 0.0
    assert processed["estimated_pitch"] is None
    assert processed["quality"] == "NOT_CALIBRATED"

def test_imu_calibrated_quality():
    processor = IMUProcessor(is_calibrated=True)
    raw_imu = {"AcX": 0, "AcY": 0, "AcZ": 16384, "GyX": 0, "GyY": 0, "GyZ": 0}
    processed = processor.process(raw_imu)
    assert processed["quality"] == "VALID"

def test_imu_invalid_input():
    processor = IMUProcessor()
    processed = processor.process(None)
    assert processed["quality"] == "INVALID"

if __name__ == "__main__":
    pytest.main(["-v", __file__])
