"""
FOG-ORCHESTRATOR 2.0 — Physical V2V Relay HMI Verification Script
Verifies physical TRUCK_02 relay payloads (with accel_x/y/z, gyro_x/y/z fields)
and direct Wi-Fi payloads against HMI backend and canonical store contract.
"""

import sys
import os
import time
import requests

# Backend endpoint. Override per deployment:  FOG_BACKEND_URL=http://<host>:8000
BACKEND_URL = os.getenv("FOG_BACKEND_URL", "http://127.0.0.1:8000")

def run_physical_v2v_verification():
    print("====================================================")
    print("FOG-ORCHESTRATOR 2.0 — PHYSICAL V2V RELAY HMI VERIFICATION")
    print("====================================================")

    # 1. Health check
    try:
        r_health = requests.get(f"{BACKEND_URL}/api/health", timeout=3.0)
        assert r_health.status_code == 200, f"Health failed: {r_health.status_code}"
        print("[CHECK 1] HMI Backend Liveness ..................... PASS")
    except Exception as e:
        print(f"[CHECK 1] HMI Backend Liveness ..................... FAIL ({e})")
        sys.exit(1)

    # 2. Ingest Physical TRUCK_01 V2V Relay Payload
    relay_payload = {
        "vehicle_id": "TRUCK_01",
        "sequence": 5000,
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

    r_post = requests.post(f"{BACKEND_URL}/api/hardware/telemetry", json=relay_payload, timeout=3.0)
    assert r_post.status_code == 200, f"Relay post failed: {r_post.status_code} {r_post.text}"
    body = r_post.json()
    assert body["status"] == "ACCEPTED", f"Unexpected status: {body['status']}"
    assert body["source"] == "V2V_VIA_TRUCK_02", f"Source mismatch: {body['source']}"
    print("[CHECK 2] Physical Relay Ingestion HTTP 200 .......... PASS")

    # 3. Canonical Store Verification for TRUCK_01
    r_veh = requests.get(f"{BACKEND_URL}/api/vehicles", timeout=3.0)
    assert r_veh.status_code == 200, f"Get vehicles failed: {r_veh.status_code}"
    veh_data = r_veh.json()
    assert veh_data["mode"] == "LIVE", f"Mode is not LIVE: {veh_data['mode']}"
    t1 = veh_data["vehicles"].get("TRUCK_01")
    assert t1 is not None, "TRUCK_01 missing from canonical store"
    assert t1["sequence_number"] == 5000, f"Sequence mismatch: {t1['sequence_number']}"
    assert t1["source"] == "V2V_VIA_TRUCK_02", f"Source mismatch: {t1['source']}"
    assert t1["raw_imu"]["ax"] == -364.0, f"IMU ax mismatch: {t1['raw_imu']['ax']}"
    assert t1["communication"]["rssi"] == -87, f"RSSI mismatch: {t1['communication']['rssi']}"
    print("[CHECK 3] Canonical Vehicle Store Mapping .......... PASS")

    # 4. Ingest Physical TRUCK_02 Direct Wi-Fi Payload (Vehicle Isolation)
    direct_payload = {
        "vehicle_id": "TRUCK_02",
        "sequence": 4100,
        "rpm": 150.0,
        "speed": 1.2,
        "accel_x": 100,
        "accel_y": -50,
        "accel_z": 16384,
        "gyro_x": 10,
        "gyro_y": 5,
        "gyro_z": -2,
        "rssi": -72,
        "snr": 10.50,
        "source": "DIRECT_WIFI"
    }

    r_post2 = requests.post(f"{BACKEND_URL}/api/hardware/telemetry", json=direct_payload, timeout=3.0)
    assert r_post2.status_code == 200, f"Direct post failed: {r_post2.status_code}"
    r_veh2 = requests.get(f"{BACKEND_URL}/api/vehicles", timeout=3.0).json()
    t1_after = r_veh2["vehicles"].get("TRUCK_01")
    t2_after = r_veh2["vehicles"].get("TRUCK_02")
    assert t1_after["sequence_number"] == 5000, "TRUCK_01 overwritten by TRUCK_02"
    assert t2_after["sequence_number"] == 4100, "TRUCK_02 state not recorded"
    print("[CHECK 4] Vehicle Isolation & Multi-Vehicle State .. PASS")

    # 5. Out-of-order rejection
    older_payload = dict(relay_payload)
    older_payload["sequence"] = 4999
    r_old = requests.post(f"{BACKEND_URL}/api/hardware/telemetry", json=older_payload, timeout=3.0).json()
    assert r_old["status"] == "REJECTED_OUT_OF_ORDER", f"Failed to reject older sequence: {r_old}"
    print("[CHECK 5] Out-of-Order Packet Protection ........... PASS")

    print("====================================================")
    print("VERDICT: READY_FOR_PHYSICAL_V2V_HMI")
    print("====================================================")

if __name__ == "__main__":
    run_physical_v2v_verification()
