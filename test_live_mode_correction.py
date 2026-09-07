"""
Pytest suite for Live Hardware Telemetry HMI Mode Correction & Canonical State.
Verifies all 18 acceptance criteria for LIVE mode transition, mock overwrite protection,
communication status alignment, deduplication, out-of-order rejection, and staleness transitions.
"""

import sys
import os
import time
import pytest

hmi_backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "SYNQRA_SIH2026-27-HMI", "backend"))
if hmi_backend_dir in sys.path:
    sys.path.remove(hmi_backend_dir)
sys.path.insert(0, hmi_backend_dir)

from fastapi.testclient import TestClient
import app.main as hmi_main

hmi_app = hmi_main.app


@pytest.fixture(autouse=True)
def reset_backend_state():
    hmi_main.vehicle_telemetry_store.clear()
    hmi_main.deduplication_store.clear()
    hmi_main.last_sequence_by_vehicle.clear()
    hmi_main.HMI_MODE = "MOCK"
    hmi_main.last_hardware_packet_at = 0.0
    if hmi_main.twin_store is not None:
        with hmi_main.twin_store._lock:
            hmi_main.twin_store._vehicles.clear()
    if hmi_main.twin_ingestor is not None:
        hmi_main.twin_ingestor._last_sequence.clear()
        hmi_main.twin_ingestor._seen_sequences.clear()


@pytest.fixture
def client():
    return TestClient(hmi_app)


def test_1_physical_telemetry_ingestion_updates_vehicles_and_mode(client):
    # Verify initial state is MOCK
    mode_res0 = client.get("/api/mode")
    assert mode_res0.json()["mode"] == "MOCK"

    # Post physical packet for TRUCK_01 via V2V relay
    p1 = {
        "vehicle_id": "TRUCK_01",
        "sequence": 40,
        "rpm": 0.0,
        "speed": None,
        "ax": -176.0,
        "ay": 20.0,
        "az": 16780.0,
        "gx": 614.0,
        "gy": 352.0,
        "gz": 215.0,
        "rssi": -87,
        "snr": 9.75,
        "source": "V2V_VIA_TRUCK_02"
    }
    res1 = client.post("/api/hardware/telemetry", json=p1)
    assert res1.status_code == 200
    assert res1.json()["status"] == "ACCEPTED"

    # Post physical packet for TRUCK_02 via DIRECT_WIFI
    p2 = {
        "vehicle_id": "TRUCK_02",
        "sequence": 42,
        "rpm": 180.0,
        "speed": None,
        "ax": 100.0,
        "ay": -50.0,
        "az": 16384.0,
        "gx": 10.0,
        "gy": 5.0,
        "gz": -2.0,
        "rssi": -72,
        "snr": 10.5,
        "source": "DIRECT_WIFI"
    }
    res2 = client.post("/api/hardware/telemetry", json=p2)
    assert res2.status_code == 200

    # Verify /api/mode and /api/vehicles return LIVE mode and physical state
    mode_res = client.get("/api/mode")
    assert mode_res.json()["mode"] == "LIVE"

    veh_res = client.get("/api/vehicles")
    body = veh_res.json()
    assert body["mode"] == "LIVE"
    assert body["count"] == 2

    t1 = body["vehicles"]["TRUCK_01"]
    assert t1["sequence_number"] == 40
    assert t1["source"] == "V2V_VIA_TRUCK_02"
    assert t1["data_quality"] == "LIVE"
    assert t1["communication_status"] == "ONLINE"
    assert t1["communication"]["status"] == "ONLINE"  # Sub-dict aligned
    assert t1["raw_imu"]["ax"] == -176.0

    t2 = body["vehicles"]["TRUCK_02"]
    assert t2["sequence_number"] == 42
    assert t2["source"] == "DIRECT_WIFI"
    assert t2["communication_status"] == "ONLINE"
    assert t2["communication"]["status"] == "ONLINE"


def test_2_mock_telemetry_cannot_overwrite_active_live_hardware_state(client):
    # Ingest LIVE hardware packet
    p_live = {
        "vehicle_id": "TRUCK_01",
        "sequence": 40,
        "rpm": 240.0,
        "speed": None,
        "ax": 0.0, "ay": 0.0, "az": 16384.0,
        "gx": 0.0, "gy": 0.0, "gz": 0.0,
        "rssi": -80, "snr": 9.0,
        "source": "DIRECT_WIFI"
    }
    client.post("/api/hardware/telemetry", json=p_live)

    # Attempt to post mock telemetry to /api/telemetry
    mock_payload = {
        "vehicle_id": "TRUCK_01",
        "sequence_number": 9,
        "rpm": 999.0,
        "mode": "MOCK"
    }
    res_mock = client.post("/api/telemetry", json=mock_payload)
    assert res_mock.json()["status"] == "IGNORED_MOCK_OVERWRITE"

    # Verify vehicle state in /api/vehicles is still canonical LIVE hardware state
    veh_res = client.get("/api/vehicles").json()
    t1 = veh_res["vehicles"]["TRUCK_01"]
    assert t1["sequence_number"] == 40
    assert t1["rpm"] == 240.0
    assert t1["data_quality"] == "LIVE"


def test_3_deduplication_and_out_of_order_rejection(client):
    p41 = {
        "vehicle_id": "TRUCK_01",
        "sequence": 41,
        "rpm": 200.0,
        "speed": None,
        "ax": 0.0, "ay": 0.0, "az": 16384.0,
        "gx": 0.0, "gy": 0.0, "gz": 0.0,
        "rssi": -80, "snr": 9.0,
        "source": "DIRECT_WIFI"
    }
    # First send: ACCEPTED
    res1 = client.post("/api/hardware/telemetry", json=p41)
    assert res1.json()["status"] == "ACCEPTED"

    # Duplicate send: ACCEPTED_DUPLICATE
    res2 = client.post("/api/hardware/telemetry", json=p41)
    assert res2.json()["status"] == "ACCEPTED_DUPLICATE"

    # Out-of-order send (seq 40 after 41): REJECTED_OUT_OF_ORDER
    p40 = dict(p41, sequence=40)
    res3 = client.post("/api/hardware/telemetry", json=p40)
    assert res3.json()["status"] == "REJECTED_OUT_OF_ORDER"


def test_4_communication_staleness_and_recovery_transitions(client):
    p = {
        "vehicle_id": "TRUCK_01",
        "sequence": 50,
        "rpm": 240.0,
        "speed": None,
        "ax": 0.0, "ay": 0.0, "az": 16384.0,
        "gx": 0.0, "gy": 0.0, "gz": 0.0,
        "rssi": -80, "snr": 9.0,
        "source": "DIRECT_WIFI"
    }
    client.post("/api/hardware/telemetry", json=p)

    # Immediately: ONLINE
    v0 = client.get("/api/vehicles").json()["vehicles"]["TRUCK_01"]
    assert v0["communication_status"] == "ONLINE"
    assert v0["communication"]["status"] == "ONLINE"

    # Simulate 4 seconds age: STALE / COMMUNICATION_DEGRADED
    hmi_main.vehicle_telemetry_store["TRUCK_01"]["timestamp"] = time.time() - 4.0
    v1 = client.get("/api/vehicles").json()["vehicles"]["TRUCK_01"]
    assert v1["communication_status"] == "STALE"
    assert v1["communication"]["status"] == "STALE"
    assert v1["communication_state"] == "COMMUNICATION_DEGRADED"

    # Simulate 12 seconds age: OFFLINE / COMMUNICATION_DEGRADED
    hmi_main.vehicle_telemetry_store["TRUCK_01"]["timestamp"] = time.time() - 12.0
    v2 = client.get("/api/vehicles").json()["vehicles"]["TRUCK_01"]
    assert v2["communication_status"] == "OFFLINE"
    assert v2["communication"]["status"] == "OFFLINE"

    # Send new packet sequence 51: Recovery to ONLINE
    p51 = dict(p, sequence=51)
    client.post("/api/hardware/telemetry", json=p51)
    v3 = client.get("/api/vehicles").json()["vehicles"]["TRUCK_01"]
    assert v3["communication_status"] == "ONLINE"
    assert v3["communication"]["status"] == "ONLINE"
    assert v3["communication_state"] == "HEALTHY"
