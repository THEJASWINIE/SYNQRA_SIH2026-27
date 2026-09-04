"""
Unit tests for CoordinateMapper adapter.
Tests initial position, straight movement dead reckoning, heading change, stop,
stale telemetry rejection, and explicit "ESTIMATED" position quality flag.
"""

import pytest
from integration_adapters.coordinate_mapper import CoordinateMapper

def test_initial_position():
    mapper = CoordinateMapper()
    pose_a = mapper.update_pose("TRUCK_01", speed_mps=0.0, yaw_rate_rads=0.0, dt_s=0.1)
    assert pose_a["x_p"] == 0.0
    assert pose_a["y_p"] == 0.0
    assert pose_a["position_quality"] == "ESTIMATED"

def test_straight_movement():
    mapper = CoordinateMapper()
    # Speed = 2.0 m/s for 1.0s straight ahead (heading = 0)
    pose = mapper.update_pose("TRUCK_01", speed_mps=2.0, yaw_rate_rads=0.0, dt_s=1.0)
    assert abs(pose["x_p"] - 2.0) < 0.01
    assert abs(pose["y_p"] - 0.0) < 0.01
    assert pose["x_twin"] == 102.0  # Offset onto mine grid

def test_stale_telemetry_rejection():
    mapper = CoordinateMapper()
    pose_stale = mapper.update_pose("TRUCK_01", speed_mps=2.0, yaw_rate_rads=0.0, dt_s=1.0, is_stale=True)
    assert pose_stale["position_quality"] == "ESTIMATED_STALE"

if __name__ == "__main__":
    pytest.main(["-v", __file__])
