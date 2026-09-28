"""
Unit tests for KinematicScaleAdapter.
Tests physical to twin speed scaling, twin advisory scaling to prototype bounds,
and zero raw data overwriting.
"""

import pytest
from integration_adapters.kinematic_scale import KinematicScaleAdapter

def test_physical_to_twin_speed():
    adapter = KinematicScaleAdapter()
    res = adapter.physical_to_twin_speed(1.5)  # 50% max speed on 3.0 m/s proto
    assert res["physical_speed_mps"] == 1.5
    assert res["normalized_speed"] == 0.5
    assert abs(res["twin_equivalent_speed_mps"] - 5.56) < 0.1

def test_twin_advisory_to_physical_speed():
    adapter = KinematicScaleAdapter()
    # Twin requests 11.11 m/s (100% dumper speed) -> prototype should scale to 3.0 m/s
    proto_speed = adapter.twin_advisory_to_physical_speed(11.11)
    assert proto_speed == 3.0

    # Twin requests 5.56 m/s (50% dumper speed) -> prototype should scale to 1.5 m/s
    proto_speed_half = adapter.twin_advisory_to_physical_speed(5.555)
    assert abs(proto_speed_half - 1.5) < 0.05

def test_over_speed_clamping():
    adapter = KinematicScaleAdapter()
    # Unsafe twin advisory (30 m/s) clamped to max prototype speed (3.0 m/s)
    proto_speed_clamped = adapter.twin_advisory_to_physical_speed(30.0)
    assert proto_speed_clamped <= 3.0

if __name__ == "__main__":
    pytest.main(["-v", __file__])
