import pytest
import time
from contracts import (
    VehicleStateMessage, SafetyStateMessage, RoadStateMessage,
    BottleneckStateMessage, DispatchCommandMessage, HealthMessage, CommandAckMessage
)


def test_vehicle_state_contract():
    now = time.time()
    msg = VehicleStateMessage(
        vehicle_id="TRUCK_01",
        timestamp=now,
        position=120.5,
        segment_id="ROAD_1",
        speed_mps=8.5,
        acceleration_mps2=0.2,
        heading=0.0,
        mode="traveling",
        communication_state="HEALTHY",
        is_loaded=True,
        total_tonnes_hauled=182.0
    )
    assert msg.vehicle_id == "TRUCK_01"
    assert msg.speed_mps == 8.5
    assert msg.is_loaded is True


def test_safety_state_contract():
    now = time.time()
    msg = SafetyStateMessage(
        vehicle_id="TRUCK_01",
        timestamp=now,
        actual_speed=8.5,
        v_safe=10.0,
        h_safe=25.0,
        risk_level=0.2,
        active_constraint="Visibility",
        is_safe=True
    )
    assert msg.actual_speed <= msg.v_safe
    assert msg.is_safe is True


def test_road_state_contract():
    now = time.time()
    msg = RoadStateMessage(
        segment_id="ROAD_1",
        timestamp=now,
        visibility_m=15.0,
        friction=0.25,
        grade=-4.0,
        capacity_vph=407.2,
        queue=2,
        utilization=0.8,
        safe_speed_mps=5.4
    )
    assert msg.visibility_m == 15.0
    assert msg.friction == 0.25


def test_dispatch_command_contract():
    now = time.time()
    cmd = DispatchCommandMessage(
        command_id="CMD_001",
        vehicle_id="TRUCK_01",
        timestamp=now,
        target_speed=6.0,
        action="TARGET_SPEED",
        reason_code="ARRIVAL_RATE_EXCEEDS_CAPACITY"
    )
    assert cmd.command_id == "CMD_001"
    assert cmd.action == "TARGET_SPEED"


def test_invalid_data_contract_rejection():
    with pytest.raises(Exception):
        # Missing required vehicle_id
        VehicleStateMessage(timestamp=time.time(), position=0.0, segment_id="ROAD_1", speed_mps=5.0)
