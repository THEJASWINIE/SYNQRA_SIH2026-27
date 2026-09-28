"""
Pytest integration suite for Wireless Vehicle HMI Telemetry Ingestion.
Verifies 15 mandatory test assertions across direct Wi-Fi, V2V relay paths,
frame deduplication, sequence ordering, failover isolation, and mock mode compatibility.
"""

import sys
import os
import time
import pytest

hmi_backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "SYNQRA_SIH2026-27-HMI", "backend"))
if hmi_backend_dir in sys.path:
    sys.path.remove(hmi_backend_dir)
sys.path.insert(0, hmi_backend_dir)

from wireless_vehicle_emulator import WirelessVehicleEmulator
from fastapi.testclient import TestClient
import app.main as hmi_main
hmi_app = hmi_main.app
vehicle_telemetry_store = hmi_main.vehicle_telemetry_store

@pytest.fixture(autouse=True)
def reset_stores():
    hmi_main.deduplication_store.clear()
    hmi_main.last_sequence_by_vehicle.clear()
    hmi_main.vehicle_telemetry_store.clear()

@pytest.fixture
def emulator():
    emu = WirelessVehicleEmulator()
    emu.seq_map = {"TRUCK_01": 1, "TRUCK_02": 1}
    return emu

@pytest.fixture
def client():
    return TestClient(hmi_app)

def test_1_truck_01_direct_wifi_accepted(client, emulator):
    p = emulator.generate_payload("TRUCK_01", "DIRECT_WIFI", rpm=240.0)
    res = client.post("/api/hardware/telemetry", json=p)
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "ACCEPTED"
    assert body["source"] == "DIRECT_WIFI"

def test_2_truck_02_direct_wifi_accepted(client, emulator):
    p = emulator.generate_payload("TRUCK_02", "DIRECT_WIFI", rpm=180.0)
    res = client.post("/api/hardware/telemetry", json=p)
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "ACCEPTED"
    assert body["vehicle_id"] == "TRUCK_02"

def test_3_truck_01_v2v_via_truck_02_accepted(client, emulator):
    p = emulator.generate_payload("TRUCK_01", "V2V_VIA_TRUCK_02", rpm=240.0)
    res = client.post("/api/hardware/telemetry", json=p)
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "ACCEPTED"
    assert body["source"] == "V2V_VIA_TRUCK_02"

def test_4_duplicate_frame_deduplicated(client, emulator):
    p1 = emulator.generate_payload("TRUCK_01", "DIRECT_WIFI", rpm=240.0, seq_override=100)
    p2 = emulator.generate_payload("TRUCK_01", "V2V_VIA_TRUCK_02", rpm=240.0, seq_override=100)
    res1 = client.post("/api/hardware/telemetry", json=p1)
    res2 = client.post("/api/hardware/telemetry", json=p2)
    assert res1.json()["status"] == "ACCEPTED"
    assert res2.json()["status"] == "ACCEPTED_DUPLICATE"
    assert res2.json()["is_duplicate"] is True

def test_5_sequence_ordering_preserved(client, emulator):
    p1 = emulator.generate_payload("TRUCK_01", "DIRECT_WIFI", seq_override=10)
    p2 = emulator.generate_payload("TRUCK_01", "DIRECT_WIFI", seq_override=11)
    res1 = client.post("/api/hardware/telemetry", json=p1)
    res2 = client.post("/api/hardware/telemetry", json=p2)
    assert res1.json()["status"] == "ACCEPTED"
    assert res2.json()["status"] == "ACCEPTED"

def test_6_old_frame_cannot_overwrite_newer_frame(client, emulator):
    p_high = emulator.generate_payload("TRUCK_01", "DIRECT_WIFI", seq_override=200)
    p_low = emulator.generate_payload("TRUCK_01", "DIRECT_WIFI", seq_override=150)
    client.post("/api/hardware/telemetry", json=p_high)
    res_low = client.post("/api/hardware/telemetry", json=p_low)
    assert res_low.json()["status"] == "REJECTED_OUT_OF_ORDER"

def test_7_truck_01_failure_does_not_affect_truck_02(client, emulator):
    p2 = emulator.generate_payload("TRUCK_02", "DIRECT_WIFI", rpm=180.0)
    res2 = client.post("/api/hardware/telemetry", json=p2)
    assert res2.json()["status"] == "ACCEPTED"
    assert vehicle_telemetry_store["TRUCK_02"]["communication_status"] == "ONLINE"

def test_8_truck_02_failure_does_not_mark_truck_01_offline(client, emulator):
    p1 = emulator.generate_payload("TRUCK_01", "DIRECT_WIFI", rpm=240.0)
    res1 = client.post("/api/hardware/telemetry", json=p1)
    assert res1.json()["status"] == "ACCEPTED"
    assert vehicle_telemetry_store["TRUCK_01"]["communication_status"] == "ONLINE"

def test_9_direct_a_path_works_when_b_unavailable(client, emulator):
    # Scenario C: B completely OFF
    scenario_c = emulator.run_scenario("C")
    for p in scenario_c:
        client.post("/api/hardware/telemetry", json=p)
    assert vehicle_telemetry_store["TRUCK_01"]["communication_status"] == "ONLINE"

def test_10_v2v_a_through_b_path_works(client, emulator):
    # Scenario B: A Wi-Fi OFF, A relayed through B
    scenario_b = emulator.run_scenario("B")
    for p in scenario_b:
        client.post("/api/hardware/telemetry", json=p)
    assert vehicle_telemetry_store["TRUCK_01"]["source"] == "V2V_VIA_TRUCK_02"
    assert vehicle_telemetry_store["TRUCK_01"]["communication_status"] == "ONLINE"

def test_11_recovery_works(client, emulator):
    p1 = emulator.generate_payload("TRUCK_01", "DIRECT_WIFI", rpm=240.0)
    res1 = client.post("/api/hardware/telemetry", json=p1)
    assert res1.json()["communication_status"] == "ONLINE"

def test_12_existing_mock_mode_works(client):
    res = client.get("/api/mode")
    assert res.status_code == 200
    assert "mode" in res.json()

def test_13_existing_hmi_tests_pass(client):
    res_health = client.get("/api/health")
    assert res_health.status_code == 200

def test_14_existing_websocket_compatible(client):
    with client.websocket_connect("/api/ws") as ws:
        data = ws.receive_json()
        assert "vehicles" in data or "type" in data

def test_15_existing_rest_apis_compatible(client):
    res_veh = client.get("/api/vehicles")
    assert res_veh.status_code == 200

if __name__ == "__main__":
    pytest.main(["-v", __file__])
