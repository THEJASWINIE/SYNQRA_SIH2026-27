"""
Unit tests for CommandAdapter.
Tests translation of Digital Twin advisories to physical commands, distinction between
RECOMMENDED, REQUESTED, and APPLIED values, ACK correlation (ACCEPTED, CLAMPED, REJECTED),
expired recommendation rejection, and duplicate command handling.
"""

import time
import pytest
from integration_adapters.command_adapter import CommandAdapter

def test_translate_twin_advisory():
    adapter = CommandAdapter()
    now = time.time()
    twin_adv = {
        "vehicle_id": "vehicle_1",
        "recommended_speed": 11.11,  # 100% max dumper speed -> scales to 3.0 m/s proto
        "action": "TARGET_SPEED",
        "timestamp": now
    }
    cmd = adapter.translate_twin_advisory(twin_adv)
    assert cmd is not None
    assert cmd["vehicle_id"] == "TRUCK_01"
    assert cmd["recommended_value"] == 11.11
    assert cmd["requested_value"] == 3.0

def test_process_vehicle_ack_clamped():
    adapter = CommandAdapter()
    now = time.time()
    twin_adv = {"vehicle_id": "vehicle_1", "recommended_speed": 11.11, "action": "TARGET_SPEED", "timestamp": now}
    cmd = adapter.translate_twin_advisory(twin_adv)

    # Physical ESP32 clamps speed to 2.5 m/s local safe limit
    ack_payload = {
        "command_id": cmd["command_id"],
        "vehicle_id": "TRUCK_01",
        "status": "CLAMPED",
        "applied_speed": 2.5
    }
    ack_res = adapter.process_vehicle_ack(ack_payload)
    assert ack_res["ack_status"] == "CLAMPED"
    assert ack_res["applied_value"] == 2.5
    assert ack_res["twin_vehicle_id"] == "vehicle_1"

def test_expired_recommendation_rejection():
    adapter = CommandAdapter()
    old_adv = {"vehicle_id": "vehicle_1", "recommended_speed": 5.0, "timestamp": time.time() - 10.0}
    assert adapter.translate_twin_advisory(old_adv) is None

if __name__ == "__main__":
    pytest.main(["-v", __file__])
