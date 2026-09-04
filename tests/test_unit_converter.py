"""
Unit tests for UnitConverter adapter.
Tests RPM to m/s conversion using measured wheel radius, invalid RPM rejection,
and m/s to km/h conversion.
"""

import pytest
from integration_adapters.unit_converter import UnitConverter

def test_rpm_to_speed_mps_valid():
    converter = UnitConverter()
    # TRUCK_01 r=0.05m -> 240 RPM -> (240 * 2 * pi * 0.05) / 60 = 1.2566 m/s
    speed_a = converter.rpm_to_speed_mps("TRUCK_01", 240.0)
    assert speed_a is not None
    assert abs(speed_a - 1.2566) < 0.01

    # TRUCK_02 r=0.0425m -> 180 RPM -> (180 * 2 * pi * 0.0425) / 60 = 0.8011 m/s
    speed_b = converter.rpm_to_speed_mps("TRUCK_02", 180.0)
    assert speed_b is not None
    assert abs(speed_b - 0.8011) < 0.01

def test_rpm_to_speed_mps_invalid_inputs():
    converter = UnitConverter()
    assert converter.rpm_to_speed_mps("TRUCK_01", -10.0) is None
    assert converter.rpm_to_speed_mps("TRUCK_01", None) is None
    assert converter.rpm_to_speed_mps("UNMAPPED_TRUCK", 240.0) is None

def test_mps_to_kmh():
    converter = UnitConverter()
    assert converter.mps_to_kmh(2.5) == 9.0
    assert converter.mps_to_kmh(0.0) == 0.0

if __name__ == "__main__":
    pytest.main(["-v", __file__])
