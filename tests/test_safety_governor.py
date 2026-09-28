import pytest
from hardware_emulator import VehicleHardwareEmulator
from contracts import DispatchCommandMessage


def test_safety_governor_command_clamping():
    emulator = VehicleHardwareEmulator("TRUCK_01")
    emulator.update_environment(visibility_m=15.0, friction_mu=0.25, grade_pct=-4.0)

    safety = emulator.compute_local_safety_state()
    v_safe = safety.v_safe

    # Central requests unsafe speed 12.0 m/s
    cmd = DispatchCommandMessage(
        command_id="CMD_TEST_UNSAFE",
        vehicle_id="TRUCK_01",
        timestamp=100.0,
        target_speed=12.0,
        action="TARGET_SPEED",
        reason_code="CENTRAL_OVERRIDE"
    )

    ack = emulator.process_dispatch_command(cmd)

    assert ack.status == "CLAMPED"
    assert ack.applied_speed <= v_safe + 1e-4
    assert emulator.speed_mps <= v_safe + 1e-4


def test_scenario_1_clear_visibility_normal_friction():
    emulator = VehicleHardwareEmulator("TRUCK_01")
    emulator.update_environment(visibility_m=50.0, friction_mu=0.60, grade_pct=0.0)
    s = emulator.compute_local_safety_state()
    assert s.v_safe > 10.0


def test_scenario_2_moderate_fog():
    emulator = VehicleHardwareEmulator("TRUCK_01")
    emulator.update_environment(visibility_m=25.0, friction_mu=0.50, grade_pct=0.0)
    s = emulator.compute_local_safety_state()
    assert s.v_safe < 12.0


def test_scenario_3_dense_fog():
    emulator = VehicleHardwareEmulator("TRUCK_01")
    emulator.update_environment(visibility_m=10.0, friction_mu=0.40, grade_pct=0.0)
    s = emulator.compute_local_safety_state()
    assert s.v_safe < 6.0


def test_scenario_4_dense_fog_reduced_friction():
    emulator = VehicleHardwareEmulator("TRUCK_01")
    emulator.update_environment(visibility_m=10.0, friction_mu=0.20, grade_pct=0.0)
    s = emulator.compute_local_safety_state()
    assert s.v_safe < 4.5


def test_scenario_5_downhill_dense_fog():
    emulator = VehicleHardwareEmulator("TRUCK_01")
    emulator.update_environment(visibility_m=10.0, friction_mu=0.20, grade_pct=-8.0)
    s = emulator.compute_local_safety_state()
    assert s.v_safe < 4.0


def test_scenario_6_unsafe_central_target_speed():
    emulator = VehicleHardwareEmulator("TRUCK_01")
    emulator.update_environment(visibility_m=10.0, friction_mu=0.20, grade_pct=-8.0)
    cmd = DispatchCommandMessage(
        command_id="CMD_999", vehicle_id="TRUCK_01", timestamp=10.0,
        target_speed=15.0, action="TARGET_SPEED", reason_code="UNSAFE"
    )
    ack = emulator.process_dispatch_command(cmd)
    assert ack.status == "CLAMPED"
    assert ack.applied_speed < 4.0
