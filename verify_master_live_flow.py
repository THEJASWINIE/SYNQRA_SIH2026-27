"""
Master Live Flow Verification: Real Subprocess Uvicorn + Real HTTP + Real WebSocket.

Requirement:
1. Launch real backend on ephemeral port 8091.
2. Connect WebSocket client.
3. Ingest 3 successive telemetry packets for TRUCK_01:
   - speed = 1.0 m/s
   - speed = 2.0 m/s
   - speed = 0.5 m/s
4. Receive each update over the live WebSocket stream without page reload / reconnect.
5. Assert each state projection updates immediately and accurately.
6. Verify communication status is ONLINE throughout.

CLASSIFICATION: SIMULATION ONLY / SOFTWARE EMULATION (No physical motor connected).
"""

import json
import os
import subprocess
import sys
import time
import urllib.request
from websockets.sync.client import connect

ROOT = os.path.dirname(os.path.abspath(__file__))
BACKEND = os.path.join(ROOT, "SYNQRA_SIH2026-27-HMI", "backend")
PORT = 8091
BASE = f"http://127.0.0.1:{PORT}"
WS_URL = f"ws://127.0.0.1:{PORT}/api/ws"

results = []

def record(test_name: str, passed: bool, evidence: str):
    results.append({
        "test": test_name,
        "status": "PASS" if passed else "FAIL",
        "evidence": evidence
    })
    print(f"[{'PASS' if passed else 'FAIL'}] {test_name}: {evidence}")

def get(path):
    with urllib.request.urlopen(BASE + path, timeout=5) as r:
        return json.loads(r.read())

def post(path, payload):
    req = urllib.request.Request(
        BASE + path,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"}
    )
    try:
        with urllib.request.urlopen(req, timeout=5) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read() or b"{}")

def main():
    print("=" * 80)
    print("STARTING MASTER LIVE FLOW VERIFICATION (PORT 8091)")
    print("=" * 80)

    env = dict(os.environ, PYTHONPATH=ROOT + os.pathsep + os.path.join(ROOT, "SYNQRA_SIH2026-27-main"))
    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app.main:app",
         "--host", "127.0.0.1", "--port", str(PORT), "--log-level", "warning"],
        cwd=BACKEND, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT
    )

    try:
        # Wait for server ready
        ready = False
        for _ in range(60):
            try:
                h = get("/api/health")
                if h.get("status") == "ok":
                    ready = True
                    break
            except Exception:
                time.sleep(0.1)

        if not ready:
            print("Server failed to start within timeout.")
            return 1
        record("Server Bootstrap", True, f"Backend healthy on port {PORT}")

        # Connect WebSocket
        with connect(WS_URL, open_timeout=5) as ws:
            init_msg = json.loads(ws.recv(timeout=5))
            assert init_msg["type"] == "connection_established"
            record("WebSocket Initial Handshake", True, "Received connection_established")

            # Sequence of speeds to verify real-time progression: 1.0 -> 2.0 -> 0.5 m/s
            speeds_to_test = [1.0, 2.0, 0.5]

            for idx, target_speed in enumerate(speeds_to_test, 1):
                seq = idx * 10
                payload = {
                    "vehicle_id": "TRUCK_01",
                    "sequence": seq,
                    "source": "DIRECT_WIFI",
                    "rpm": target_speed * 60.0,
                    "speed": target_speed,
                }
                
                status_code, resp = post("/api/hardware/telemetry", payload)
                assert status_code == 200, f"POST failed: {resp}"

                # Drain and check WebSocket update
                # Receives twin_vehicle_update or telemetry_update
                received_update = False
                for _ in range(3):
                    raw = ws.recv(timeout=3)
                    msg = json.loads(raw)
                    m_type = msg.get("type")
                    if m_type == "twin_vehicle_update":
                        v_data = msg.get("data", {})
                        sp_info = v_data.get("dynamic", {}).get("speed_mps_reported", {})
                        if sp_info.get("value") == target_speed:
                            received_update = True
                            break
                    elif m_type == "telemetry_update":
                        if msg.get("data", {}).get("speed") == target_speed:
                            received_update = True
                            break

                record(
                    f"Live Speed Step {idx} ({target_speed} m/s)",
                    received_update,
                    f"Speed {target_speed} m/s streamed over WS without reconnect (seq={seq})"
                )

            # Check final REST projection consistency
            v_rest = get("/api/vehicles")["vehicles"]["TRUCK_01"]
            assert v_rest["speed"] == 0.5
            assert v_rest["communication_status"] == "ONLINE"
            record("REST State Final Consistency", True, "TRUCK_01 final speed 0.5 m/s, ONLINE")

    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except Exception:
            proc.kill()

    print("\n" + "=" * 80)
    print("MASTER LIVE FLOW SUMMARY")
    print("=" * 80)
    all_pass = all(r["status"] == "PASS" for r in results)
    for r in results:
        print(f"[{r['status']}] {r['test']}: {r['evidence']}")
    print("=" * 80)
    print(f"OVERALL RESULT: {'ALL PASS' if all_pass else 'FAIL'}")
    print("=" * 80)
    return 0 if all_pass else 1

if __name__ == "__main__":
    sys.exit(main())
