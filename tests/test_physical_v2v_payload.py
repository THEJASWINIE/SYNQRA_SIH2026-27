"""
Pytest suite for Physical V2V Relay payload parsing and HMI ingestion.
Verifies TRUCK_02 relay payloads with accel_x/y/z and gyro_x/y/z aliases.
"""

import sys
import os
import pytest
from fastapi.testclient import TestClient

# Ensure HMI backend module is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "SYNQRA_SIH2026-27-HMI", "backend"))
from app.main import app, vehicle_telemetry_store, deduplication_store, last_sequence_by_vehicle, HMI_MODE

client = TestClient(app)

@pytest.fixture(autouse=True)
def reset_hmi_state():
    vehicle_telemetry_store.clear()
    deduplication_store.clear()
    last_sequence_by_vehicle.clear()
    yield

def test_physical_v2v_relay_payload_ingestion():
    physical_relay_payload = {
        "vehicle_id": "TRUCK_01",
        "sequence": 4200,
        "rpm": 0.00,
        "speed": 0.00,
        "accel_x": -364,
        "accel_y": 220,
        "accel_z": 16920,
        "gyro_x": 584,
        "gyro_y": 398,
        "gyro_z": 191,
        "rssi": -87,
        "snr": 9.50,
        "source": "V2V_VIA_TRUCK_02"
    }

    response = client.post("/api/hardware/telemetry", json=physical_relay_payload)
    assert response.status_code == 200
    res_json = response.json()
    assert res_json["status"] == "ACCEPTED"
    assert res_json["vehicle_id"] == "TRUCK_01"
    assert res_json["sequence"] == 4200
    assert res_json["source"] == "V2V_VIA_TRUCK_02"

    veh_resp = client.get("/api/vehicles").json()
    assert veh_resp["mode"] == "LIVE"
    t1 = veh_resp["vehicles"]["TRUCK_01"]
    assert t1["sequence_number"] == 4200
    assert t1["source"] == "V2V_VIA_TRUCK_02"
    assert t1["raw_imu"]["ax"] == -364.0
    assert t1["raw_imu"]["ay"] == 220.0
    assert t1["raw_imu"]["az"] == 16920.0
    assert t1["communication"]["rssi"] == -87
    assert t1["communication"]["snr"] == 9.50

def test_physical_relay_duplicate_and_out_of_order():
    payload1 = {
        "vehicle_id": "TRUCK_01",
        "sequence": 100,
        "rpm": 0.0,
        "speed": 0.0,
        "accel_x": 0, "accel_y": 0, "accel_z": 16384,
        "gyro_x": 0, "gyro_y": 0, "gyro_z": 0,
        "rssi": -80, "snr": 9.0,
        "source": "V2V_VIA_TRUCK_02"
    }
    res1 = client.post("/api/hardware/telemetry", json=payload1).json()
    assert res1["status"] == "ACCEPTED"

    # Duplicate
    res_dup = client.post("/api/hardware/telemetry", json=payload1).json()
    assert res_dup["status"] == "ACCEPTED_DUPLICATE"

    # Out of order
    payload_old = dict(payload1)
    payload_old["sequence"] = 99
    res_old = client.post("/api/hardware/telemetry", json=payload_old).json()
    assert res_old["status"] == "REJECTED_OUT_OF_ORDER"
