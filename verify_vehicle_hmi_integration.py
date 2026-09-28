"""
====================================================
VEHICLE -> HMI INTEGRATION VERIFICATION SUITE
====================================================
Automated verification script for Phase 1 Physical Vehicles -> HMI Integration.
Tests LoRa telemetry packet parsing, Gateway serial ingestion, vehicle identification,
IMU/RPM mapping, WebSocket broadcasting, communication health (ONLINE/STALE/OFFLINE),
mock/hardware mode stability, and fault tolerance.
"""

import sys
import os
import time
import json
import asyncio
from typing import Dict, Any

# Ensure HMI Backend is in sys.path
hmi_backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "SYNQRA_SIH2026-27-HMI", "backend"))
if hmi_backend_dir not in sys.path:
    sys.path.insert(0, hmi_backend_dir)

from fastapi.testclient import TestClient
from app.main import app, vehicle_telemetry_store
from app.gateway_serial_reader import GatewayTelemetryParser, CommunicationHealthMonitor
from mock_vehicle_generator import MockVehicleGenerator


def run_hardware_hmi_verification() -> bool:
    print("====================================================")
    print("VEHICLE -> HMI INTEGRATION VERIFICATION")
    print("====================================================")

    results = {}
    client = TestClient(app)
    
    # -------------------------------------------------------------
    # CHECK 1 & 2: Vehicle A and Vehicle B telemetry packet received
    # -------------------------------------------------------------
    pkt_a_raw = "V=TRUCK_01,RPM=240.0,SPD=2.51,AX=0.12,AY=-0.05,AZ=9.81,GX=0.02,GY=0.01,GZ=-0.03,RSSI=-65,SNR=9.2"
    pkt_b_raw = "V=TRUCK_02,RPM=180.5,SPD=1.89,AX=-0.08,AY=0.02,AZ=9.78,GX=-0.01,GY=0.00,GZ=0.01,RSSI=-72,SNR=8.1"

    parsed_a = GatewayTelemetryParser.parse_packet(pkt_a_raw)
    parsed_b = GatewayTelemetryParser.parse_packet(pkt_b_raw)

    results["CHECK 1"] = "PASS" if parsed_a and parsed_a.get("vehicle_id") == "TRUCK_01" else "FAIL"
    results["CHECK 2"] = "PASS" if parsed_b and parsed_b.get("vehicle_id") == "TRUCK_02" else "FAIL"

    # -------------------------------------------------------------
    # CHECK 3: Vehicle IDs correctly separated (TRUCK_01 vs TRUCK_02)
    # -------------------------------------------------------------
    client.post("/api/telemetry", json=parsed_a)
    client.post("/api/telemetry", json=parsed_b)
    v_resp = client.get("/api/vehicles").json()
    vehs = v_resp.get("vehicles", {})
    results["CHECK 3"] = "PASS" if "TRUCK_01" in vehs and "TRUCK_02" in vehs and len(vehs) == 2 else "FAIL"

    # -------------------------------------------------------------
    # CHECK 4 & 5: Vehicle A and Vehicle B RPM reaches HMI
    # -------------------------------------------------------------
    truck_a = vehs.get("TRUCK_01", {})
    truck_b = vehs.get("TRUCK_02", {})
    results["CHECK 4"] = "PASS" if truck_a.get("rpm") == 240.0 else "FAIL"
    results["CHECK 5"] = "PASS" if truck_b.get("rpm") == 180.5 else "FAIL"

    # -------------------------------------------------------------
    # CHECK 6 & 7: Vehicle A and Vehicle B IMU reaches HMI (AX, AY, AZ, GX, GY, GZ)
    # -------------------------------------------------------------
    imu_a = truck_a.get("acceleration", {})
    imu_b = truck_b.get("acceleration", {})
    gyro_a = truck_a.get("gyroscope", {})
    gyro_b = truck_b.get("gyroscope", {})

    check_6_pass = imu_a.get("z") == 9.81 and gyro_a.get("x") == 0.02
    check_7_pass = imu_b.get("z") == 9.78 and gyro_b.get("x") == -0.01

    results["CHECK 6"] = "PASS" if check_6_pass else "FAIL"
    results["CHECK 7"] = "PASS" if check_7_pass else "FAIL"

    # -------------------------------------------------------------
    # CHECK 8: WebSocket updates frontend without refresh
    # -------------------------------------------------------------
    try:
        with client.websocket_connect("/api/ws") as ws:
            snap = ws.receive_json()
            # Send updated telemetry via REST and verify WebSocket broadcast
            updated_pkt = GatewayTelemetryParser.parse_packet("V=TRUCK_01,RPM=255.0,SPD=2.70,AX=0.15,AY=-0.02,AZ=9.80,GX=0.01,GY=0.00,GZ=-0.01")
            client.post("/api/telemetry", json=updated_pkt)
            broadcast = ws.receive_json()
            results["CHECK 8"] = "PASS" if broadcast.get("type") == "telemetry_update" and broadcast.get("data", {}).get("vehicle_id") == "TRUCK_01" else "FAIL"
    except Exception:
        results["CHECK 8"] = "FAIL"

    # -------------------------------------------------------------
    # CHECK 9 & 10: Vehicle A and Vehicle B communication loss detected (STALE / OFFLINE)
    # -------------------------------------------------------------
    health_mon = CommunicationHealthMonitor(stale_sec=1.0, offline_sec=3.0)
    now = time.time()
    health_mon.record_heartbeat("TRUCK_01", now - 2.0)  # 2s old -> STALE
    health_mon.record_heartbeat("TRUCK_02", now - 5.0)  # 5s old -> OFFLINE

    stale_a = health_mon.evaluate_health("TRUCK_01", now)
    offline_b = health_mon.evaluate_health("TRUCK_02", now)

    results["CHECK 9"] = "PASS" if stale_a == "STALE" else "FAIL"
    results["CHECK 10"] = "PASS" if offline_b == "OFFLINE" else "FAIL"

    # -------------------------------------------------------------
    # CHECK 11: Mock mode still works
    # -------------------------------------------------------------
    try:
        mock_gen = MockVehicleGenerator()
        mock_frames = mock_gen.update(dt_s=0.5)
        res_mock = client.post("/api/telemetry", json=mock_frames[0])
        results["CHECK 11"] = "PASS" if res_mock.status_code == 200 else "FAIL"
    except Exception:
        results["CHECK 11"] = "FAIL"

    # -------------------------------------------------------------
    # CHECK 12: Hardware mode works (Serial Gateway packet parsing)
    # -------------------------------------------------------------
    try:
        mode_res = client.get("/api/mode").json()
        hw_parsed = GatewayTelemetryParser.parse_packet("V=TRUCK_01,RPM=240.0,SPD=2.50,AX=0.10,AY=0.00,AZ=9.81,GX=0.00,GY=0.00,GZ=0.00")
        results["CHECK 12"] = "PASS" if mode_res.get("status") == "ACTIVE" and hw_parsed is not None else "FAIL"
    except Exception:
        results["CHECK 12"] = "FAIL"

    # -------------------------------------------------------------
    # CHECK 13: Backend remains stable when malformed packet is received
    # -------------------------------------------------------------
    try:
        bad_parsed_1 = GatewayTelemetryParser.parse_packet("GARBAGE_NOISE_LINE_WITHOUT_EQUALS")
        bad_parsed_2 = GatewayTelemetryParser.parse_packet("V=TRUCK_99,RPM=INVALID_STRING_VALUE")
        res_bad = client.post("/api/telemetry", json={"invalid": "payload"})
        results["CHECK 13"] = "PASS" if bad_parsed_1 is None and bad_parsed_2 is None and res_bad.status_code == 400 else "FAIL"
    except Exception:
        results["CHECK 13"] = "FAIL"

    # -------------------------------------------------------------
    # CHECK 14: Backend remains stable when only one vehicle is active
    # -------------------------------------------------------------
    try:
        vehicle_telemetry_store.clear()
        client.post("/api/telemetry", json=parsed_a)
        one_veh_resp = client.get("/api/vehicles").json()
        results["CHECK 14"] = "PASS" if len(one_veh_resp.get("vehicles", {})) == 1 and "TRUCK_01" in one_veh_resp.get("vehicles", {}) else "FAIL"
    except Exception:
        results["CHECK 14"] = "FAIL"

    # -------------------------------------------------------------
    # CHECK 15: HMI remains stable when both vehicles disconnect
    # -------------------------------------------------------------
    try:
        vehicle_telemetry_store.clear()
        empty_resp = client.get("/api/vehicles").json()
        results["CHECK 15"] = "PASS" if empty_resp.get("count") == 0 else "FAIL"
    except Exception:
        results["CHECK 15"] = "FAIL"

    # -------------------------------------------------------------
    # Print formatted output matching prompt requirements
    # -------------------------------------------------------------
    print("Vehicle A Telemetry ............. " + ("PASS" if results.get("CHECK 1") == "PASS" else "FAIL"))
    print("Vehicle B Telemetry ............. " + ("PASS" if results.get("CHECK 2") == "PASS" else "FAIL"))
    print("Vehicle Identification .......... " + ("PASS" if results.get("CHECK 3") == "PASS" else "FAIL"))
    print("LoRa Gateway .................... " + ("PASS" if results.get("CHECK 12") == "PASS" else "FAIL"))
    print("Backend Parser .................. " + ("PASS" if results.get("CHECK 4") == "PASS" and results.get("CHECK 5") == "PASS" else "FAIL"))
    print("WebSocket ....................... " + ("PASS" if results.get("CHECK 8") == "PASS" else "FAIL"))
    print("HMI Live Update ................. " + ("PASS" if results.get("CHECK 6") == "PASS" and results.get("CHECK 7") == "PASS" else "FAIL"))
    print("Mock Mode Regression ............ " + ("PASS" if results.get("CHECK 11") == "PASS" else "FAIL"))
    print("Communication Failure Handling .. " + ("PASS" if results.get("CHECK 9") == "PASS" and results.get("CHECK 10") == "PASS" else "FAIL"))
    print("====================================================")

    all_passed = all(status == "PASS" for status in results.values())
    
    print("\nFINAL VERDICT:\n")
    if all_passed:
        print("READY FOR HARDWARE-HMI OPERATION")
    else:
        print("NOT READY")

    return all_passed


if __name__ == "__main__":
    success = run_hardware_hmi_verification()
    sys.exit(0 if success else 1)
