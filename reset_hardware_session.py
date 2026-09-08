"""
FOG-ORCHESTRATOR 2.0 — Hardware Session Reset Utility

Resets the hardware sequence tracking and deduplication state on the backend
for TRUCK_01 (or all vehicles), allowing a physical ESP32 to establish a fresh
monotonic sequence lifecycle without restarting the backend process.

Usage:
    python reset_hardware_session.py
    python reset_hardware_session.py --url http://127.0.0.1:8000 --vehicle TRUCK_01
"""

import argparse
import json
import sys
import urllib.request
import urllib.error

DEFAULT_URL = "http://127.0.0.1:8000"


def reset_hardware_session(base_url: str = DEFAULT_URL, vehicle_id: str = "TRUCK_01") -> bool:
    endpoint = f"{base_url.rstrip('/')}/api/hardware/reset"
    payload = json.dumps({"vehicle_id": vehicle_id}).encode("utf-8")
    req = urllib.request.Request(
        endpoint,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST"
    )

    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            print(f"[RESET SUCCESS] HTTP {resp.status}: {data}")
            return True
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8")
        print(f"[RESET FAILED] HTTP {e.code}: {body}", file=sys.stderr)
        return False
    except Exception as exc:
        print(f"[RESET ERROR] Failed to connect to {endpoint}: {exc}", file=sys.stderr)
        return False


def get_sequence_state(base_url: str = DEFAULT_URL, vehicle_id: str = "TRUCK_01") -> None:
    endpoint = f"{base_url.rstrip('/')}/api/hardware/sequence?vehicle_id={vehicle_id}"
    req = urllib.request.Request(endpoint, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            print(f"[SEQUENCE STATE] {data}")
    except Exception as exc:
        print(f"[SEQUENCE QUERY ERROR] {exc}", file=sys.stderr)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Reset hardware telemetry sequence tracking")
    parser.add_argument("--url", default=DEFAULT_URL, help=f"Backend base URL (default: {DEFAULT_URL})")
    parser.add_argument("--vehicle", default="TRUCK_01", help="Vehicle ID to reset (default: TRUCK_01)")
    args = parser.parse_args()

    success = reset_hardware_session(args.url, args.vehicle)
    if success:
        get_sequence_state(args.url, args.vehicle)
    sys.exit(0 if success else 1)
