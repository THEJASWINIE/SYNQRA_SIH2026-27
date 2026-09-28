"""
P10 — cross-process contract verification: Python backend -> TypeScript frontend.

WHAT THIS CLOSES
    `verify_p10_final.py` proves the causal chain inside one Python process.
    `verify_p9_end_to_end.py` proves the REST/WebSocket surface of a real server.
    Neither proves that what the backend SENDS is what the frontend can PARSE - the
    frontend's contract tests read a hand-written fixture, so a backend field rename would
    leave them green.

    This script:
      1. starts a real uvicorn backend,
      2. drives telemetry through the canonical ingestion path,
      3. captures the verbatim `GET /api/twin/vehicles/TRUCK_02` response to
         `SYNQRA_SIH2026-27-HMI/contracts/fixtures/live/TwinVehicle.live.json`,
      4. runs the frontend's `liveContract.test.ts` against that capture, using the real
         Zod schema and the real normalizer.

    A mismatch between the two languages fails here rather than in a browser.

PROVENANCE
    SIMULATION / EMULATED. The telemetry is driven over the physical ingress by this
    script, not by an ESP32. No physical hardware is involved and no physical validation
    is claimed.

USAGE
    python verify_p10_live_contract.py
    Exit code 0 only if the capture succeeded AND the frontend contract test passed.
"""

import json
import os
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
MAIN_ROOT = os.path.join(PROJECT_ROOT, "SYNQRA_SIH2026-27-main")
HMI_ROOT = os.path.join(PROJECT_ROOT, "SYNQRA_SIH2026-27-HMI")
BACKEND_DIR = os.path.join(HMI_ROOT, "backend")
FRONTEND_DIR = os.path.join(HMI_ROOT, "frontend")
CAPTURE_DIR = os.path.join(HMI_ROOT, "contracts", "fixtures", "live")
CAPTURE_PATH = os.path.join(CAPTURE_DIR, "TwinVehicle.live.json")

PORT = 8078
BASE = "http://127.0.0.1:%d" % PORT
VEHICLE_ID = "TRUCK_02"

results = []


def record(name, ok, detail=""):
    results.append((name, "PASS" if ok else "FAIL", str(detail)))
    return ok


def get_json(path, timeout=5):
    with urllib.request.urlopen(BASE + path, timeout=timeout) as response:
        return json.loads(response.read())


def post_json(path, payload, timeout=5):
    request = urllib.request.Request(
        BASE + path, data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.status, json.loads(response.read())
    except urllib.error.HTTPError as error:
        return error.code, json.loads(error.read() or b"{}")


def start_backend():
    """
    Start uvicorn from the backend directory - NOT the repository root.

    Launching from elsewhere is what exposed the CWD-dependent configuration bug in P6.1,
    so this verification keeps doing it the awkward way on purpose.
    """
    env = dict(os.environ, PYTHONPATH=os.pathsep.join([PROJECT_ROOT, MAIN_ROOT]))
    process = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app.main:app",
         "--host", "127.0.0.1", "--port", str(PORT), "--log-level", "warning"],
        cwd=BACKEND_DIR, env=env,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
    )
    for _ in range(60):
        try:
            get_json("/api/health")
            return process
        except Exception:  # noqa: BLE001 - still starting
            time.sleep(0.5)
    process.terminate()
    raise SystemExit("backend never became healthy on port %d" % PORT)


def capture_projection():
    """Drive telemetry in, then save exactly what the backend serves for that vehicle."""
    status, body = post_json("/api/hardware/telemetry", {
        "vehicle_id": VEHICLE_ID, "sequence": 11_500_001, "source": "DIRECT_WIFI",
        "rpm": 198.0, "speed": 2.5, "ax": 0.12, "ay": -0.05, "az": 9.81,
        "gx": 0.02, "gy": 0.01, "gz": -0.03, "rssi": -68, "snr": 9.4,
    })
    record("1 telemetry accepted on the physical ingress",
           status == 200 and body.get("status") == "ACCEPTED",
           "HTTP %s %s" % (status, body.get("status")))

    projection = get_json("/api/twin/vehicles/%s" % VEHICLE_ID)
    record("2 the backend serves a Twin projection for the vehicle",
           projection.get("vehicle_id") == VEHICLE_ID and bool(projection.get("dynamic")),
           "fields=%d" % len(projection.get("dynamic", {})))

    # The capture must be the response AS SENT. Nothing is normalised, filled in or tidied
    # up here - a capture the script had corrected would prove nothing about the backend.
    os.makedirs(CAPTURE_DIR, exist_ok=True)
    with open(CAPTURE_PATH, "w", encoding="utf-8") as handle:
        json.dump(projection, handle, indent=2, sort_keys=False)
        handle.write("\n")

    record("3 capture written verbatim",
           os.path.exists(CAPTURE_PATH) and os.path.getsize(CAPTURE_PATH) > 0,
           os.path.relpath(CAPTURE_PATH, PROJECT_ROOT))
    return projection


def check_no_fabrication(projection):
    """Guard the capture itself before handing it to the frontend."""
    dynamic = projection.get("dynamic", {})
    record("4 no unmeasured field was fabricated in the capture",
           "position_s" not in dynamic and "heading_rad" not in dynamic,
           "position_s=%s heading_rad=%s" % ("position_s" in dynamic, "heading_rad" in dynamic))

    envelope = {"value", "timestamp", "source", "origin", "quality",
                "age_s", "available", "clock_domain", "freshness"}
    missing = {name: sorted(envelope - set(field))
               for name, field in dynamic.items() if not envelope <= set(field)}
    record("5 every captured field carries the full provenance envelope",
           not missing, missing or "all %d fields complete" % len(dynamic))

    rpm = dynamic.get("rpm", {})
    record("6 the physical ingress is labelled HARDWARE in the capture",
           rpm.get("source") == "HARDWARE" and rpm.get("origin") == "HARDWARE",
           "rpm source=%s origin=%s" % (rpm.get("source"), rpm.get("origin")))

    # TRUCK_02's speed is PWM-derived, so it must stay DERIVED-from-HARDWARE and must
    # never be presented as a measured speed.
    speed = dynamic.get("speed_mps", {})
    if speed:
        record("7 PWM-derived speed stays DERIVED, with a HARDWARE origin",
               speed.get("source") == "DERIVED" and speed.get("origin") == "HARDWARE",
               "speed_mps source=%s origin=%s" % (speed.get("source"), speed.get("origin")))


def run_frontend_contract_test():
    """Validate the capture with the frontend's REAL schema and normalizer."""
    npx = shutil.which("npx") or shutil.which("npx.cmd")
    if npx is None:
        record("8 frontend contract test", False, "npx not found on PATH - NOT TESTED")
        return

    completed = subprocess.run(
        [npx, "vitest", "run", "src/contracts/liveContract.test.ts", "--reporter=dot"],
        cwd=FRONTEND_DIR, capture_output=True, text=True, timeout=600,
    )
    output = (completed.stdout or "") + (completed.stderr or "")
    ok = completed.returncode == 0
    summary = next(
        (line.strip() for line in output.splitlines() if "Tests" in line and "passed" in line),
        "exit %d" % completed.returncode,
    )
    record("8 the frontend parses the live capture with its real schema", ok, summary)
    if not ok:
        print(output[-3000:])


def main():
    print("P10 CROSS-PROCESS CONTRACT VERIFICATION  (Python backend -> TypeScript frontend)")
    print("PROVENANCE: SIMULATION / EMULATED. No physical ESP32. No physical validation.")
    print("-" * 78)

    process = start_backend()
    try:
        projection = capture_projection()
        check_no_fabrication(projection)
    finally:
        process.terminate()
        try:
            process.wait(timeout=10)
        except Exception:  # noqa: BLE001
            process.kill()

    # The frontend test reads the captured file, so the server is no longer needed.
    run_frontend_contract_test()

    width = max(len(name) for name, _, _ in results)
    for name, status, detail in results:
        print("%-*s  %-4s  %s" % (width, name, status, detail))

    passed = sum(1 for _, status, _ in results if status == "PASS")
    print("-" * 78)
    print("%d/%d PASS" % (passed, len(results)))
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
