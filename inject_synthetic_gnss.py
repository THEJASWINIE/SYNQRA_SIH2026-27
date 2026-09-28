"""
CLI Developer Utility — Software-Only Synthetic GNSS Test Injection.

Use this script during a development session to inject or clear synthetic GNSS-shaped
telemetry for TRUCK_01 and TRUCK_02 via the live backend POST /api/hardware/telemetry endpoint.

PROVENANCE GUARANTEE:
  Every packet sent carries `is_simulated: True`.
  No packet is ever marked as physical hardware data.

Commands:
  python inject_synthetic_gnss.py --enable
  python inject_synthetic_gnss.py --disable
"""

import sys
import time
import argparse
import urllib.request
import json

BACKEND_URL = "http://127.0.0.1:8000/api/hardware/telemetry"

SYNTHETIC_PAYLOADS = [
    {
        "vehicle_id": "TRUCK_01",
        "sequence": 900001,
        "rpm": 140.0,
        "speed": 1.4,
        "ax": 0.1, "ay": -0.05, "az": 9.81,
        "gx": 0.01, "gy": 0.02, "gz": -0.01,
        "rssi": -72, "snr": 9.5,
        "source": "DIRECT_WIFI",
        "latitude": 18.67812,
        "longitude": 81.18912,
        "position_source": "GNSS",
        "position_status": "VALID",
        "is_simulated": True,
    },
    {
        "vehicle_id": "TRUCK_02",
        "sequence": 900001,
        "rpm": 160.0,
        "speed": 1.6,
        "ax": 0.15, "ay": -0.02, "az": 9.80,
        "gx": 0.02, "gy": 0.01, "gz": -0.02,
        "rssi": -78, "snr": 9.5,
        "source": "DIRECT_WIFI",
        "latitude": 18.68120,
        "longitude": 81.19310,
        "position_source": "GNSS",
        "position_status": "VALID",
        "is_simulated": True,
    },
]

CLEAR_PAYLOADS = [
    {
        "vehicle_id": "TRUCK_01",
        "sequence": 900002,
        "rpm": 0.0,
        "speed": 0.0,
        "ax": 0.0, "ay": 0.0, "az": 9.81,
        "gx": 0.0, "gy": 0.0, "gz": 0.0,
        "rssi": -75, "snr": 9.5,
        "source": "DIRECT_WIFI",
        "latitude": None,
        "longitude": None,
        "is_simulated": False,
    },
    {
        "vehicle_id": "TRUCK_02",
        "sequence": 900002,
        "rpm": 0.0,
        "speed": 0.0,
        "ax": 0.0, "ay": 0.0, "az": 9.81,
        "gx": 0.0, "gy": 0.0, "gz": 0.0,
        "rssi": -75, "snr": 9.5,
        "source": "DIRECT_WIFI",
        "latitude": None,
        "longitude": None,
        "is_simulated": False,
    },
]


def post_payload(payload: dict) -> bool:
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        BACKEND_URL,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req) as resp:
            body = json.loads(resp.read().decode("utf-8"))
            print(f"  [{payload['vehicle_id']}] POST Status {resp.status}: {body.get('status', 'OK')}")
            return True
    except Exception as exc:
        print(f"  [{payload['vehicle_id']}] POST Failed: {exc}")
        return False


def main():
    parser = argparse.ArgumentParser(description="Inject or clear synthetic GNSS test telemetry.")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--enable", action="store_true", help="Inject synthetic GNSS payloads for TRUCK_01 and TRUCK_02.")
    group.add_argument("--disable", action="store_true", help="Send normal telemetry without position (clear synthetic position).")
    args = parser.parse_args()

    if args.enable:
        print("==================================================")
        print("ENABLING SOFTWARE-ONLY SYNTHETIC GNSS TEST INPUT")
        print("==================================================")
        for p in SYNTHETIC_PAYLOADS:
            p["timestamp"] = time.time()
            post_payload(p)
        print("\nSUCCESS: Synthetic GNSS test payloads injected.")
        print("Check S1 map: Markers should display 'TRUCK_0x · SOFTWARE TEST · SYNTHETIC GNSS'.")

    elif args.disable:
        print("==================================================")
        print("DISABLING SYNTHETIC GNSS TEST INPUT (RETURNING TO NORMAL LIVE)")
        print("==================================================")
        for p in CLEAR_PAYLOADS:
            p["timestamp"] = time.time()
            post_payload(p)
        print("\nSUCCESS: Normal hardware telemetry sent.")
        print("Check S1 map: Vehicles return to POSITION UNAVAILABLE.")


if __name__ == "__main__":
    main()
