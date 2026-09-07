"""
===============================================================================
SYNQRA FOG-ORCHESTRATOR 2.0 — LIVE ADVERSARIAL VERIFICATION SUITE (A–L)
===============================================================================
Executes live adversarial tests against the running FastAPI application backend:

A. NaN RPM via frozen V2V path
B. negative RPM
C. valid zero RPM
D. 2 MB telemetry payload
E. huge nested payload
F. forged HARDWARE provenance
G. duplicate telemetry
H. out-of-order telemetry
I. invalid curve radius
J. malformed acceleration
K. malformed gyro
L. WebSocket reconnect after attack

Also verifies that the live HMI remains fully responsive and operational.
===============================================================================
"""

import sys
import os
import json
import time
import math
import numpy as np

# Set up paths
REPO_ROOT = os.path.dirname(os.path.abspath(__file__))
HMI_BACKEND = os.path.join(REPO_ROOT, "SYNQRA_SIH2026-27-HMI", "backend")
MAIN_DIR = os.path.join(REPO_ROOT, "SYNQRA_SIH2026-27-main")

for p in (REPO_ROOT, HMI_BACKEND, MAIN_DIR):
    if p not in sys.path:
        sys.path.insert(0, p)

from fastapi.testclient import TestClient
import app.main as backend
from app.main import (
    app,
    vehicle_telemetry_store,
    deduplication_store,
    last_sequence_by_vehicle,
    twin_store,
    twin_ingestor,
)
from v2v_packet_parser import V2VPacketParser
from fog_safe.safety import solve_safe_speed
from fog_safe.vehicle import MiningVehicle
from fog_safe.road import RoadSegment
from fog_safe.environment import EnvironmentState
from fog_safe.communication import CommunicationModel

v2v_parser = V2VPacketParser()


def _solve_with_curve_radius(curve_radius, mu=0.35):
    veh = MiningVehicle()
    road = RoadSegment(percent_grade=0.0, speed_limit_kmh=50.0, curve_radius=curve_radius)
    env = EnvironmentState(r_effective=50.0, mu_true=mu)
    comm = CommunicationModel()
    return solve_safe_speed(veh, road, env, comm, mu_effective=mu, r_effective=50.0)


def reset_all_backend_state():
    vehicle_telemetry_store.clear()
    deduplication_store.clear()
    last_sequence_by_vehicle.clear()
    backend.last_hardware_packet_at = None
    backend.HMI_MODE = "MOCK"
    if twin_store is not None:
        with twin_store._lock:
            twin_store._vehicles.clear()
    if twin_ingestor is not None:
        twin_ingestor._last_sequence.clear()
        twin_ingestor._seen_sequences.clear()


def run_live_adversarial_suite():
    print("=" * 72)
    print("SYNQRA FOG-ORCHESTRATOR 2.0 — LIVE ADVERSARIAL QA SUITE (A–L)")
    print("=" * 72)

    results = {}
    client = TestClient(app)

    # -------------------------------------------------------------------------
    # TEST A: NaN RPM via frozen V2V path
    # -------------------------------------------------------------------------
    reset_all_backend_state()
    try:
        # 1. Packet parser rejection
        nan_packet = "STATE,TRUCK_01,28,nan,0.00,-496,132,16696,703,342,191"
        parsed_nan = v2v_parser.parse_v2v_packet(nan_packet)
        assert parsed_nan is None, f"Expected parse_v2v_packet to reject NaN RPM, got {parsed_nan}"

        # 2. HTTP hardware telemetry rejection (422)
        import json as _json
        p_nan = {
            "vehicle_id": "TRUCK_01", "sequence": 1, "rpm": float("nan"),
            "speed": 0.0, "ax": 0, "ay": 0, "az": 16384, "gx": 0, "gy": 0, "gz": 0,
            "rssi": -75, "snr": 9.5, "source": "DIRECT_WIFI"
        }
        res_http = client.post(
            "/api/hardware/telemetry",
            content=_json.dumps(p_nan, allow_nan=True),
            headers={"content-type": "application/json"}
        )
        assert res_http.status_code == 422, f"Expected HTTP 422 for NaN RPM, got {res_http.status_code}"
        assert "TRUCK_01" not in vehicle_telemetry_store, "NaN RPM must not enter cache"

        results["A"] = "PASS"
        print("[PASS] Test A: NaN RPM via frozen V2V path correctly rejected")
    except Exception as e:
        results["A"] = f"FAIL: {e}"
        print(f"[FAIL] Test A: {e}")

    # -------------------------------------------------------------------------
    # TEST B: negative RPM
    # -------------------------------------------------------------------------
    reset_all_backend_state()
    try:
        neg_packet = "STATE,TRUCK_01,28,-50.00,0.00,-496,132,16696,703,342,191"
        parsed_neg = v2v_parser.parse_v2v_packet(neg_packet)
        assert parsed_neg is None, f"Expected parse_v2v_packet to reject negative RPM, got {parsed_neg}"

        p_neg = {
            "vehicle_id": "TRUCK_01", "sequence": 1, "rpm": -120.0,
            "speed": 0.0, "ax": 0, "ay": 0, "az": 16384, "gx": 0, "gy": 0, "gz": 0,
            "rssi": -75, "snr": 9.5, "source": "DIRECT_WIFI"
        }
        res_http = client.post("/api/hardware/telemetry", json=p_neg)
        assert res_http.status_code == 422, f"Expected HTTP 422 for negative RPM, got {res_http.status_code}"
        assert "TRUCK_01" not in vehicle_telemetry_store, "Negative RPM must not enter cache"

        results["B"] = "PASS"
        print("[PASS] Test B: Negative RPM rejected before canonicalization/mutation")
    except Exception as e:
        results["B"] = f"FAIL: {e}"
        print(f"[FAIL] Test B: {e}")

    # -------------------------------------------------------------------------
    # TEST C: valid zero RPM
    # -------------------------------------------------------------------------
    reset_all_backend_state()
    try:
        zero_packet = "STATE,TRUCK_01,28,0.00,0.00,-496,132,16696,703,342,191"
        parsed_zero = v2v_parser.parse_v2v_packet(zero_packet)
        assert parsed_zero is not None, "Valid RPM=0.0 must be accepted by parser"
        assert parsed_zero["rpm"] == 0.0

        p_zero = {
            "vehicle_id": "TRUCK_01", "sequence": 1, "rpm": 0.0,
            "speed": 0.0, "ax": 0, "ay": 0, "az": 16384, "gx": 0, "gy": 0, "gz": 0,
            "rssi": -75, "snr": 9.5, "source": "DIRECT_WIFI"
        }
        res_http = client.post("/api/hardware/telemetry", json=p_zero)
        assert res_http.status_code == 200, f"Expected HTTP 200 for RPM=0.0, got {res_http.status_code}"
        assert "TRUCK_01" in vehicle_telemetry_store
        assert vehicle_telemetry_store["TRUCK_01"]["rpm"] == 0.0

        results["C"] = "PASS"
        print("[PASS] Test C: Valid RPM=0.0 accepted and preserved")
    except Exception as e:
        results["C"] = f"FAIL: {e}"
        print(f"[FAIL] Test C: {e}")

    # -------------------------------------------------------------------------
    # TEST D: 2 MB telemetry payload
    # -------------------------------------------------------------------------
    reset_all_backend_state()
    try:
        huge_data = "x" * (2 * 1024 * 1024)
        attack_payload = {"vehicle_id": "ATTACKER_01", "data": huge_data}
        res_huge = client.post(
            "/api/telemetry",
            content=json.dumps(attack_payload).encode(),
            headers={"content-type": "application/json"},
        )
        assert res_huge.status_code == 413, f"Expected HTTP 413, got {res_huge.status_code}"
        assert "ATTACKER_01" not in vehicle_telemetry_store, "Attack payload must not enter cache"
        if twin_store is not None:
            assert twin_store.get_vehicle("ATTACKER_01") is None, "Attack payload must not mutate Twin"

        results["D"] = "PASS"
        print("[PASS] Test D: 2 MB payload rejected with 413 before parsing or state mutation")
    except Exception as e:
        results["D"] = f"FAIL: {e}"
        print(f"[FAIL] Test D: {e}")

    # -------------------------------------------------------------------------
    # TEST E: huge nested payload
    # -------------------------------------------------------------------------
    reset_all_backend_state()
    try:
        # Nested unknown fields within <= 64 KiB
        deep_nested = {"level1": {"level2": {"level3": "garbage" * 500}}, "junk": [1] * 1000}
        nested_payload = {
            "vehicle_id": "TRUCK_01",
            "rpm": 150.0,
            "speed": 1.5,
            "nested_junk": deep_nested,
        }
        res_nested = client.post("/api/telemetry", json=nested_payload)
        assert res_nested.status_code == 200
        # Allowlist ensures nested junk was not stored
        stored = vehicle_telemetry_store["TRUCK_01"]
        assert "nested_junk" not in stored, "Allowlist must discard unallowed nested fields"

        # Oversized nested structure (> 64 KiB)
        oversized_nested = {
            "vehicle_id": "TRUCK_01",
            "nested": {"deep": "x" * 70000},
        }
        res_over = client.post(
            "/api/telemetry",
            content=json.dumps(oversized_nested).encode(),
            headers={"content-type": "application/json"},
        )
        assert res_over.status_code == 413, f"Expected 413 for >64KB nested payload, got {res_over.status_code}"

        results["E"] = "PASS"
        print("[PASS] Test E: Huge nested payloads bounded & non-allowlisted fields filtered")
    except Exception as e:
        results["E"] = f"FAIL: {e}"
        print(f"[FAIL] Test E: {e}")

    # -------------------------------------------------------------------------
    # TEST F: forged HARDWARE provenance
    # -------------------------------------------------------------------------
    reset_all_backend_state()
    try:
        forged_payload = {
            "vehicle_id": "TRUCK_01",
            "sequence_number": 1,
            "rpm": 120.0,
            "data_quality": "LIVE",  # Forged claim on mock ingress
            "source": "DIRECT_WIFI",
        }
        res_forged = client.post("/api/telemetry", json=forged_payload)
        assert res_forged.status_code == 200
        stored = vehicle_telemetry_store["TRUCK_01"]
        assert stored["data_quality"] == "SIMULATED", "Mock ingress must force SIMULATED"
        assert backend.hardware_link_state(time.time())["hardware_connected"] is False
        assert client.get("/api/mode").json()["mode"] == "MOCK"

        results["F"] = "PASS"
        print("[PASS] Test F: Forged HARDWARE provenance refused; stamped SIMULATED")
    except Exception as e:
        results["F"] = f"FAIL: {e}"
        print(f"[FAIL] Test F: {e}")

    # -------------------------------------------------------------------------
    # TEST G: duplicate telemetry
    # -------------------------------------------------------------------------
    reset_all_backend_state()
    try:
        p_base = {
            "vehicle_id": "TRUCK_01",
            "sequence": 50,
            "rpm": 120.0,
            "source": "DIRECT_WIFI",
        }
        res1 = client.post("/api/hardware/telemetry", json=p_base)
        assert res1.status_code == 200
        assert res1.json()["status"] == "ACCEPTED"

        res2 = client.post("/api/hardware/telemetry", json=p_base)
        assert res2.status_code == 409, f"Duplicate must return 409, got {res2.status_code}"
        assert res2.json()["status"] == "ACCEPTED_DUPLICATE"

        results["G"] = "PASS"
        print("[PASS] Test G: Duplicate telemetry rejected with 409 ACCEPTED_DUPLICATE")
    except Exception as e:
        results["G"] = f"FAIL: {e}"
        print(f"[FAIL] Test G: {e}")

    # -------------------------------------------------------------------------
    # TEST H: out-of-order telemetry
    # -------------------------------------------------------------------------
    reset_all_backend_state()
    try:
        p55 = {"vehicle_id": "TRUCK_01", "sequence": 55, "rpm": 120.0, "source": "DIRECT_WIFI"}
        res1 = client.post("/api/hardware/telemetry", json=p55)
        assert res1.status_code == 200

        # Out-of-order sequence (52 after 55)
        p52 = dict(p55, sequence=52)
        res2 = client.post("/api/hardware/telemetry", json=p52)
        assert res2.status_code == 409, f"Out-of-order must return 409, got {res2.status_code}"
        assert res2.json()["status"] == "REJECTED_OUT_OF_ORDER"

        results["H"] = "PASS"
        print("[PASS] Test H: Out-of-order sequence rejected with 409 REJECTED_OUT_OF_ORDER")
    except Exception as e:
        results["H"] = f"FAIL: {e}"
        print(f"[FAIL] Test H: {e}")

    # -------------------------------------------------------------------------
    # TEST I: invalid curve radius
    # -------------------------------------------------------------------------
    try:
        # Straight road (+inf)
        res_straight = _solve_with_curve_radius(np.inf)
        assert res_straight.candidate_limits_ms["v_curve"] == np.inf, "Straight road (+inf) must not constrain curve"
        assert res_straight.v_safe_ms > 0.0

        # Valid curve
        res_curve = _solve_with_curve_radius(50.0)
        assert np.isfinite(res_curve.candidate_limits_ms["v_curve"])
        assert res_curve.candidate_limits_ms["v_curve"] > 0.0

        # Zero radius -> fail closed
        res_zero = _solve_with_curve_radius(0.0)
        assert res_zero.candidate_limits_ms["v_curve"] == 0.0
        assert res_zero.v_safe_ms == 0.0

        # Negative radius -> fail closed
        res_neg = _solve_with_curve_radius(-25.0)
        assert res_neg.candidate_limits_ms["v_curve"] == 0.0
        assert res_neg.v_safe_ms == 0.0

        # NaN radius -> fail closed
        res_nan = _solve_with_curve_radius(float("nan"))
        assert res_nan.candidate_limits_ms["v_curve"] == 0.0
        assert res_nan.v_safe_ms == 0.0

        # -inf radius -> fail closed
        res_minf = _solve_with_curve_radius(-np.inf)
        assert res_minf.candidate_limits_ms["v_curve"] == 0.0
        assert res_minf.v_safe_ms == 0.0

        results["I"] = "PASS"
        print("[PASS] Test I: Curve radius fail-closed (0, neg, nan, -inf -> 0; +inf -> unconstrained)")
    except Exception as e:
        results["I"] = f"FAIL: {e}"
        print(f"[FAIL] Test I: {e}")

    # -------------------------------------------------------------------------
    # TEST J: malformed acceleration
    # -------------------------------------------------------------------------
    reset_all_backend_state()
    try:
        # Non-dict acceleration
        for bad_acc in ["extreme", [1, 2, 3], 9.81, None]:
            p = {"vehicle_id": "TRUCK_01", "rpm": 120.0, "acceleration": bad_acc}
            res = client.post("/api/telemetry", json=p)
            assert res.status_code == 200, f"Malformed acceleration must not raise 500, got {res.status_code}"
            # Ensure /api/vehicles works smoothly
            veh_res = client.get("/api/vehicles")
            assert veh_res.status_code == 200

        results["J"] = "PASS"
        print("[PASS] Test J: Malformed acceleration handled gracefully without 500")
    except Exception as e:
        results["J"] = f"FAIL: {e}"
        print(f"[FAIL] Test J: {e}")

    # -------------------------------------------------------------------------
    # TEST K: malformed gyro
    # -------------------------------------------------------------------------
    reset_all_backend_state()
    try:
        # Non-dict gyroscope
        for bad_gyro in ["spinning", True, 42.0, [0.1, 0.2]]:
            p = {"vehicle_id": "TRUCK_01", "rpm": 120.0, "gyroscope": bad_gyro}
            res = client.post("/api/telemetry", json=p)
            assert res.status_code == 200, f"Malformed gyroscope must not raise 500, got {res.status_code}"
            veh_res = client.get("/api/vehicles")
            assert veh_res.status_code == 200

        results["K"] = "PASS"
        print("[PASS] Test K: Malformed gyroscope handled gracefully without 500")
    except Exception as e:
        results["K"] = f"FAIL: {e}"
        print(f"[FAIL] Test K: {e}")

    # -------------------------------------------------------------------------
    # TEST L: WebSocket reconnect after attack
    # -------------------------------------------------------------------------
    reset_all_backend_state()
    try:
        # 1. Deliver 2 MB attack payload
        big = {"vehicle_id": "ATTACKER_01", "data": "x" * (2 * 1024 * 1024)}
        client.post(
            "/api/telemetry",
            content=json.dumps(big).encode(),
            headers={"content-type": "application/json"},
        )

        # 2. Connect WebSocket client
        with client.websocket_connect("/api/ws") as ws:
            init_msg = ws.receive_json()
            assert init_msg["type"] == "connection_established"
            assert init_msg["vehicles"] == {}, "Raw cache vehicles must never be exposed"
            if "twin" in init_msg:
                assert isinstance(init_msg["twin"], dict)

            # Send valid telemetry while WS is connected
            valid_p = {"vehicle_id": "TRUCK_01", "rpm": 240.0, "speed": 2.5}
            post_res = client.post("/api/telemetry", json=valid_p)
            assert post_res.status_code == 200

            # Drain messages: should receive clean updates
            got_update = False
            for _ in range(5):
                msg = ws.receive_json()
                if msg.get("type") in ("telemetry_update", "twin_vehicle_update"):
                    got_update = True
                    break
            assert got_update, "WebSocket client received telemetry update after attack"

        results["L"] = "PASS"
        print("[PASS] Test L: WebSocket client reconnects and streams cleanly after 2 MB attack")
    except Exception as e:
        results["L"] = f"FAIL: {e}"
        print(f"[FAIL] Test L: {e}")

    # -------------------------------------------------------------------------
    # LIVE HMI HEALTH & OPERABILITY VERIFICATION
    # -------------------------------------------------------------------------
    try:
        assert client.get("/api/health").status_code == 200
        assert client.get("/api/mode").status_code == 200
        assert client.get("/api/vehicles").status_code == 200
        assert client.get("/api/twin/snapshot").status_code == 200
        assert client.get("/api/commands/history").status_code == 200
        print("[PASS] Live HMI API endpoints responsive and operational")
    except Exception as e:
        print(f"[FAIL] HMI operability check failed: {e}")
        return False

    print("=" * 72)
    print("LIVE ADVERSARIAL TEST SUMMARY:")
    all_passed = True
    for test_name in ["A", "B", "C", "D", "E", "F", "G", "H", "I", "J", "K", "L"]:
        status = results.get(test_name, "NOT TESTED")
        if status != "PASS":
            all_passed = False
        print(f"Test {test_name}: {status}")
    print("=" * 72)
    return all_passed


if __name__ == "__main__":
    success = run_live_adversarial_suite()
    sys.exit(0 if success else 1)
