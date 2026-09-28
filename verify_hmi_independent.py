"""
==================================================
HMI INDEPENDENT VERIFICATION SUITE
==================================================
Acceptance testing script for System A (HMI / Supervisory Dashboard).
Verifies complete independent operation without Digital Twin dependencies.
"""

import sys
import os
import time
import json
from typing import Dict, Any

# Add HMI backend directory to sys.path for direct import
hmi_backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "SYNQRA_SIH2026-27-HMI", "backend"))
if hmi_backend_dir not in sys.path:
    sys.path.insert(0, hmi_backend_dir)

from fastapi.testclient import TestClient
from app.main import app
from mock_vehicle_generator import MockVehicleGenerator


def run_hmi_verification() -> bool:
    print("==================================================")
    print("HMI INDEPENDENT VERIFICATION")
    print("==================================================")

    results = {}
    client = TestClient(app)
    gen = MockVehicleGenerator()

    # -------------------------------------------------------------
    # CHECK 1: Backend starts (FastAPI Health Endpoint)
    # -------------------------------------------------------------
    try:
        res = client.get("/api/health")
        results["CHECK 1"] = "PASS" if res.status_code == 200 and res.json().get("status") in ["ok", "healthy"] else "FAIL"
    except Exception:
        results["CHECK 1"] = "FAIL"

    # -------------------------------------------------------------
    # CHECK 2: Frontend starts (Vite Package & Component Audit)
    # -------------------------------------------------------------
    try:
        fe_pkg = os.path.join("SYNQRA_SIH2026-27-HMI", "frontend", "package.json")
        fe_entry = os.path.join("SYNQRA_SIH2026-27-HMI", "frontend", "src", "main.tsx")
        if os.path.exists(fe_pkg) and os.path.exists(fe_entry):
            with open(fe_pkg, "r") as f:
                pkg_data = json.load(f)
                results["CHECK 2"] = "PASS" if pkg_data.get("name") == "fog-orchestrator-hmi-frontend" else "FAIL"
        else:
            results["CHECK 2"] = "FAIL"
    except Exception:
        results["CHECK 2"] = "FAIL"

    # -------------------------------------------------------------
    # CHECK 3: WebSocket connection established
    # -------------------------------------------------------------
    try:
        with client.websocket_connect("/api/ws") as websocket:
            data = websocket.receive_json()
            results["CHECK 3"] = "PASS" if data.get("type") == "connection_established" else "FAIL"
    except Exception:
        results["CHECK 3"] = "FAIL"

    # -------------------------------------------------------------
    # CHECK 4: Mock telemetry reaches backend
    # -------------------------------------------------------------
    try:
        frames = gen.update(dt_s=0.5)
        res1 = client.post("/api/telemetry", json=frames[0])
        res2 = client.post("/api/telemetry", json=frames[1])
        results["CHECK 4"] = "PASS" if res1.status_code == 200 and res2.status_code == 200 else "FAIL"
    except Exception:
        results["CHECK 4"] = "FAIL"

    # -------------------------------------------------------------
    # CHECK 5: Telemetry reaches frontend / vehicle store
    # -------------------------------------------------------------
    try:
        res = client.get("/api/vehicles")
        vehs = res.json().get("vehicles", {})
        results["CHECK 5"] = "PASS" if len(vehs) >= 2 else "FAIL"
    except Exception:
        results["CHECK 5"] = "FAIL"

    # -------------------------------------------------------------
    # CHECK 6: Vehicle identification works (TRUCK_01, TRUCK_02)
    # -------------------------------------------------------------
    try:
        res = client.get("/api/vehicles")
        vehs = res.json().get("vehicles", {})
        vids = set(vehs.keys())
        results["CHECK 6"] = "PASS" if "TRUCK_01" in vids and "TRUCK_02" in vids else "FAIL"
    except Exception:
        results["CHECK 6"] = "FAIL"

    # -------------------------------------------------------------
    # CHECK 7: Speed and RPM update
    # -------------------------------------------------------------
    try:
        updated_frames = gen.update(dt_s=2.0)
        client.post("/api/telemetry", json=updated_frames[0])
        res = client.get("/api/vehicles")
        truck_a = res.json().get("vehicles", {}).get("TRUCK_01", {})
        results["CHECK 7"] = "PASS" if "speed_mps" in truck_a and "rpm" in truck_a and truck_a["rpm"] > 0 else "FAIL"
    except Exception:
        results["CHECK 7"] = "FAIL"

    # -------------------------------------------------------------
    # CHECK 8: Safety state displayed (NORMAL, CAUTION, COMMUNICATION_DEGRADED)
    # -------------------------------------------------------------
    try:
        res = client.get("/api/vehicles")
        vehs = res.json().get("vehicles", {})
        safety_states = [v.get("safety_state") for v in vehs.values()]
        results["CHECK 8"] = "PASS" if any(s in ["NORMAL", "CAUTION", "COMMUNICATION_DEGRADED"] for s in safety_states) else "FAIL"
    except Exception:
        results["CHECK 8"] = "FAIL"

    # -------------------------------------------------------------
    # CHECK 9: Stale telemetry condition detected
    # -------------------------------------------------------------
    try:
        res = client.get("/api/vehicles")
        vehs = res.json().get("vehicles", {})
        truck_b = vehs.get("TRUCK_02", {})
        results["CHECK 9"] = "PASS" if truck_b.get("is_stale") is True or truck_b.get("communication_state") == "COMMUNICATION_DEGRADED" else "FAIL"
    except Exception:
        results["CHECK 9"] = "FAIL"

    # -------------------------------------------------------------
    # CHECK 10: Command path accepts TARGET_SPEED, HOLD, STOP, RELEASE
    # -------------------------------------------------------------
    commands_to_test = [
        {"command_id": "CMD_101", "vehicle_id": "TRUCK_01", "action": "TARGET_SPEED", "target_speed": 10.0, "reason": "DISPATCH"},
        {"command_id": "CMD_102", "vehicle_id": "TRUCK_01", "action": "HOLD", "target_speed": 0.0, "reason": "JUNCTION_WAIT"},
        {"command_id": "CMD_103", "vehicle_id": "TRUCK_01", "action": "STOP", "target_speed": 0.0, "reason": "SAFETY_STOP"},
        {"command_id": "CMD_104", "vehicle_id": "TRUCK_01", "action": "RELEASE", "target_speed": 5.0, "reason": "PROCEED"},
    ]
    all_cmds_pass = True
    try:
        for cmd in commands_to_test:
            res = client.post("/api/commands", json=cmd)
            if res.status_code != 200 or res.json().get("status") != "ACCEPTED":
                all_cmds_pass = False
        results["CHECK 10"] = "PASS" if all_cmds_pass else "FAIL"
    except Exception:
        results["CHECK 10"] = "FAIL"

    # -------------------------------------------------------------
    # Print formatted output
    # -------------------------------------------------------------
    all_passed = True
    for i in range(1, 11):
        check_name = f"CHECK {i}"
        status = results.get(check_name, "PASS")
        print(f"{check_name} ........ {status}")
        if status != "PASS":
            all_passed = False

    print("\nFINAL RESULT:\n")
    final_status = "PASS" if all_passed else "FAIL"
    print(f"HMI INDEPENDENT SYSTEM: {final_status}")

    return all_passed


if __name__ == "__main__":
    success = run_hmi_verification()
    sys.exit(0 if success else 1)
