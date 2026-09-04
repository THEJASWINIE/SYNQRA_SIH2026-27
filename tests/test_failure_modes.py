import pytest
import time
from hardware_emulator import VehicleHardwareEmulator
from contracts import DispatchCommandMessage, HealthMessage


def test_failure_mode_a_twin_backend_stops():
    h = HealthMessage(component_id="DIGITAL_TWIN", timestamp=time.time(), state="STALE", age_ms=6000.0, error_code=503)
    assert h.state == "STALE"


def test_failure_mode_b_telemetry_stops():
    emulator = VehicleHardwareEmulator("TRUCK_01")
    emulator.telemetry_active = False
    _, _, h = emulator.get_telemetry_messages()
    assert h.state == "OFFLINE"


def test_failure_mode_c_optimizer_crashes():
    emulator = VehicleHardwareEmulator("TRUCK_01")
    # Vehicle operates locally without optimizer commands
    s = emulator.compute_local_safety_state()
    assert s.is_safe is True


def test_failure_mode_d_invalid_command():
    emulator = VehicleHardwareEmulator("TRUCK_01")
    emulator.comm_state = "LOST"
    cmd = DispatchCommandMessage(
        command_id="CMD_INVALID", vehicle_id="TRUCK_01", timestamp=time.time(),
        target_speed=10.0, action="TARGET_SPEED", reason_code="TEST"
    )
    ack = emulator.process_dispatch_command(cmd)
    assert ack.status == "REJECTED"


def test_failure_mode_e_central_speed_exceeds_safe():
    emulator = VehicleHardwareEmulator("TRUCK_01")
    emulator.update_environment(visibility_m=10.0, friction_mu=0.20, grade_pct=0.0)
    safety = emulator.compute_local_safety_state()
    
    cmd = DispatchCommandMessage(
        command_id="CMD_EXCEED", vehicle_id="TRUCK_01", timestamp=time.time(),
        target_speed=15.0, action="TARGET_SPEED", reason_code="EXCEED"
    )
    ack = emulator.process_dispatch_command(cmd)
    assert ack.status == "CLAMPED"
    assert ack.applied_speed <= safety.v_safe + 1e-4


def test_failure_mode_f_fog_sensor_disappears():
    emulator = VehicleHardwareEmulator("TRUCK_01")
    # Sensor NaN / fallback to minimum visibility 5.0m
    emulator.update_environment(visibility_m=5.0, friction_mu=0.25, grade_pct=0.0)
    s = emulator.compute_local_safety_state()
    assert s.v_safe < 5.0


def test_failure_mode_g_lora_comm_loss():
    emulator = VehicleHardwareEmulator("TRUCK_01")
    emulator.comm_state = "LOST"
    s = emulator.compute_local_safety_state()
    assert s.active_constraint == "COMMUNICATION_DEGRADED_FALLBACK"
    assert s.v_safe <= 2.78


def test_failure_mode_h_hmi_closes():
    emulator = VehicleHardwareEmulator("TRUCK_01")
    emulator.step_simulation(dt=1.0)
    s = emulator.compute_local_safety_state()
    assert s.is_safe is True
