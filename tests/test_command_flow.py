import pytest
import time
from hardware_emulator import VehicleHardwareEmulator
from contracts import DispatchCommandMessage


def test_command_flow_and_acknowledgement():
    emulator = VehicleHardwareEmulator("TRUCK_A")
    emulator.update_environment(visibility_m=20.0, friction_mu=0.30, grade_pct=0.0)

    # Dispatch command to target 8.0 m/s
    cmd = DispatchCommandMessage(
        command_id="CMD_101",
        vehicle_id="TRUCK_A",
        timestamp=time.time(),
        target_speed=8.0,
        action="TARGET_SPEED",
        reason_code="SPEED_PACING"
    )

    ack = emulator.process_dispatch_command(cmd)

    assert ack.command_id == "CMD_101"
    assert ack.vehicle_id == "TRUCK_A"
    assert ack.status in ["ACCEPTED", "CLAMPED"]
    assert ack.applied_speed <= 8.0
