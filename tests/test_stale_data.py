import pytest
import time
from hardware_emulator import VehicleHardwareEmulator


def test_stale_telemetry_detection_and_fallback():
    emulator = VehicleHardwareEmulator("TRUCK_A")
    emulator.update_environment(visibility_m=50.0, friction_mu=0.60, grade_pct=0.0)

    # Initial healthy state
    safety_normal = emulator.compute_local_safety_state()
    assert safety_normal.v_safe > 10.0

    # Simulate stale telemetry (last update > 5.0 seconds ago)
    emulator.last_update_timestamp = time.time() - 10.0

    safety_stale = emulator.compute_local_safety_state()
    assert safety_stale.active_constraint == "COMMUNICATION_DEGRADED_FALLBACK"
    assert safety_stale.v_safe <= 2.78
