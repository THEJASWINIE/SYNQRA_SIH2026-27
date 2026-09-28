import pytest
from fastapi.testclient import TestClient
import time
import os
import sys

# Ensure backend app is on path
backend_dir = os.path.abspath("SYNQRA_SIH2026-27-HMI/backend")
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from app.main import app, deduplication_store, last_sequence_by_vehicle, last_boot_by_vehicle, last_beacon_seq_by_vehicle

@pytest.fixture(autouse=True)
def reset_backend_state():
    for vid in ["TRUCK_01", "TRUCK_02"]:
        last_sequence_by_vehicle[vid] = 0
        last_boot_by_vehicle.pop(vid, None)
        last_beacon_seq_by_vehicle.pop(vid, None)
        deduplication_store.clear_vehicle(vid)
    yield

def test_rf_failover_reboot_continuity():
    client = TestClient(app)

    # 1. Normal Wi-Fi operation advancing sequence to 702
    p1 = {
        "vehicle_id": "TRUCK_01",
        "sequence": 701,
        "rpm": 50.0,
        "speed": 0.5,
        "ax": 1000, "ay": 2000, "az": 16000,
        "gx": 10, "gy": 20, "gz": 30,
        "source": "DIRECT_WIFI",
        "boot_id": 1
    }
    r1 = client.post("/api/hardware/telemetry", json=p1)
    assert r1.status_code == 200

    p2 = dict(p1, sequence=702)
    r2 = client.post("/api/hardware/telemetry", json=p2)
    assert r2.status_code == 200
    assert last_sequence_by_vehicle["TRUCK_01"] == 702

    # 2. Out of order within session 1 MUST be rejected (e.g. seq 700)
    p_old = dict(p1, sequence=700)
    r_old = client.post("/api/hardware/telemetry", json=p_old)
    assert r_old.status_code == 409
    assert r_old.json()["status"] == "REJECTED_OUT_OF_ORDER"

    # 3. Duplicate within session 1 MUST be rejected
    p_dup = dict(p1, sequence=702)
    r_dup = client.post("/api/hardware/telemetry", json=p_dup)
    assert r_dup.status_code == 409
    assert r_dup.json()["status"] == "ACCEPTED_DUPLICATE"

    # 4. VEHICLE REBOOT: boot_id advances to 2, sequence resets to 1 on LoRa Gateway path
    p_reboot_1 = {
        "vehicle_id": "TRUCK_01",
        "sequence": 1,
        "rpm": 50.0,
        "speed": 0.5,
        "ax": 1000, "ay": 2000, "az": 16000,
        "gx": 10, "gy": 20, "gz": 30,
        "source": "LORA_GATEWAY",
        "boot_id": 2
    }
    r_reboot_1 = client.post("/api/hardware/telemetry", json=p_reboot_1)
    # MUST be accepted! Gap 1 resolution!
    assert r_reboot_1.status_code == 200
    assert r_reboot_1.json()["status"] == "ACCEPTED"
    assert r_reboot_1.json()["sequence"] == 1
    assert last_sequence_by_vehicle["TRUCK_01"] == 1

    # 5. Subsequent packet sequence 2 in session 2 MUST be accepted
    p_reboot_2 = dict(p_reboot_1, sequence=2)
    r_reboot_2 = client.post("/api/hardware/telemetry", json=p_reboot_2)
    assert r_reboot_2.status_code == 200
    assert r_reboot_2.json()["sequence"] == 2

    # 6. Duplicate in session 2 MUST be rejected
    r_reboot_dup = client.post("/api/hardware/telemetry", json=p_reboot_2)
    assert r_reboot_dup.status_code == 409
    assert r_reboot_dup.json()["status"] == "ACCEPTED_DUPLICATE"

    # 7. Old session packet (replay attack with boot_id=1, seq=702) MUST be rejected!
    r_replay = client.post("/api/hardware/telemetry", json=p2)
    assert r_replay.status_code == 409

def test_heuristic_reboot_without_explicit_boot_id():
    client = TestClient(app)

    # Sequence reaches 50
    p1 = {
        "vehicle_id": "TRUCK_01",
        "sequence": 50,
        "rpm": 0.0, "speed": 0.0,
        "ax": 0, "ay": 0, "az": 16384,
        "gx": 0, "gy": 0, "gz": 0,
        "source": "DIRECT_WIFI"
    }
    assert client.post("/api/hardware/telemetry", json=p1).status_code == 200

    # Simulate comm gap of 2 seconds (reboot silence)
    from app.main import vehicle_telemetry_store
    vehicle_telemetry_store["TRUCK_01"]["received_at"] = time.time() - 2.5

    # Sequence resets to 1 (LoRa failover after reboot without explicit boot_id)
    p_reboot = dict(p1, sequence=1, source="LORA_GATEWAY")
    r_reboot = client.post("/api/hardware/telemetry", json=p_reboot)
    assert r_reboot.status_code == 200
    assert r_reboot.json()["status"] == "ACCEPTED"
    assert r_reboot.json()["sequence"] == 1

def test_safe_beacon_endpoint_and_recovery():
    client = TestClient(app)

    # 1. Ingest Safe Beacon from LoRa Gateway
    beacon_payload = {
        "vehicle_id": "TRUCK_01",
        "beacon_sequence": 1,
        "state": "DEGRADED",
        "zone_id": "PIT_ZONE_A",
        "rssi": -78,
        "snr": 9.0,
        "source": "LORA_GATEWAY"
    }
    r = client.post("/api/hardware/beacon", json=beacon_payload)
    assert r.status_code == 200
    assert r.json()["status"] == "SAFE_BEACON_ACCEPTED"
    assert r.json()["safe_beacon_state"] == "DEGRADED"

    # 2. Check vehicles state reflects Safe Beacon
    r_veh = client.get("/api/vehicles").json()
    truck_state = r_veh["vehicles"]["TRUCK_01"]
    assert truck_state["safe_beacon_active"] is True
    assert truck_state["safe_beacon_state"] == "DEGRADED"
    assert truck_state["communication_state"] == "COMMUNICATION_LOST"

    # 3. Duplicate beacon sequence must be rejected
    r_dup = client.post("/api/hardware/beacon", json=beacon_payload)
    assert r_dup.status_code == 409
    assert r_dup.json()["status"] == "REJECTED_DUPLICATE_BEACON"

    # 4. Monotonic next beacon sequence must be accepted
    b2 = dict(beacon_payload, beacon_sequence=2)
    assert client.post("/api/hardware/beacon", json=b2).status_code == 200

    # 5. Normal telemetry resumption deactivates Safe Beacon
    norm_p = {
        "vehicle_id": "TRUCK_01",
        "sequence": 100,
        "rpm": 50.0, "speed": 0.5,
        "ax": 1000, "ay": 2000, "az": 16000,
        "gx": 10, "gy": 20, "gz": 30,
        "source": "DIRECT_WIFI"
    }
    assert client.post("/api/hardware/telemetry", json=norm_p).status_code == 200

    # Check that Safe Beacon is now INACTIVE
    r_recovered = client.get("/api/vehicles").json()
    truck_recovered = r_recovered["vehicles"]["TRUCK_01"]
    assert truck_recovered["safe_beacon_active"] is False
    assert truck_recovered["safe_beacon_state"] == "INACTIVE"
    assert truck_recovered["communication_state"] == "HEALTHY"
