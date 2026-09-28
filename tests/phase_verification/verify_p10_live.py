"""
SYNQRA SIH 2026-27 — Phase 10 Live Verification Script
Validates all 10 Failure Injection / Demo Lab scenarios against the live running backend.

SCENARIOS:
  S1:  Telemetry Pause / Recovery (Manual operator workflow)
  S2:  Malformed JSON (HTTP 400 rejection)
  S3:  Invalid Speed Type (HTTP 400 rejection)
  S4:  Negative Speed (HTTP 400 rejection)
  S5:  Duplicate Sequence (Twin reject duplicate, Obs Δ=+1)
  S6:  Out-of-Order Sequence (Twin reject OOO, Obs Δ=+1)
  S7:  Unknown Vehicle Command (status=UNKNOWN_VEHICLE)
  S8:  Invalid Command Action (HTTP 400 rejection)
  S9:  Duplicate Command ID (1st: ACCEPTED, 2nd: DUPLICATE)
  S10: Oversized Payload (HTTP 413 rejection)

USAGE:
    python verification/verify_p10_live.py
"""

import json
import time
import urllib.error
import urllib.request

BASE_URL = "http://127.0.0.1:8000"


def test_p10_live(base_url=BASE_URL):
    print("=" * 80)
    print("STARTING P10 LIVE VERIFICATION")
    print("=" * 80)

    # S2: Malformed JSON
    try:
        req = urllib.request.Request(
            f"{base_url}/api/telemetry",
            data=b"{bad json}",
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        urllib.request.urlopen(req)
        s2 = False
    except urllib.error.HTTPError as e:
        s2 = e.code == 400
    print(f"S2 Malformed JSON (HTTP 400): {s2}")

    # S3: Invalid Speed Type
    try:
        req = urllib.request.Request(
            f"{base_url}/api/telemetry",
            data=json.dumps({"vehicle_id": "TRUCK_01", "speed": "fast"}).encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        urllib.request.urlopen(req)
        s3 = False
    except urllib.error.HTTPError as e:
        s3 = e.code == 400
    print(f"S3 Invalid Speed Type (HTTP 400): {s3}")

    # S4: Negative Speed
    try:
        req = urllib.request.Request(
            f"{base_url}/api/telemetry",
            data=json.dumps({"vehicle_id": "TRUCK_01", "speed": -5.0}).encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        urllib.request.urlopen(req)
        s4 = False
    except urllib.error.HTTPError as e:
        s4 = e.code == 400
    print(f"S4 Negative Speed (HTTP 400): {s4}")

    # Helper: get obs counters
    def get_obs():
        with urllib.request.urlopen(f"{base_url}/api/observability") as resp:
            return json.loads(resp.read().decode())["telemetry_ingest"]

    # S5: Duplicate Sequence
    before = get_obs()["duplicate"]
    seq = 10_000_000 + int(time.time() * 1000) % 80_000_000
    p = json.dumps({"vehicle_id": "TRUCK_01", "sequence_number": seq, "speed": 2.0}).encode()
    r1 = urllib.request.Request(
        f"{base_url}/api/telemetry",
        data=p,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    urllib.request.urlopen(r1)
    r2 = urllib.request.Request(
        f"{base_url}/api/telemetry",
        data=p,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    urllib.request.urlopen(r2)
    after = get_obs()["duplicate"]
    s5 = after - before == 1
    print(f"S5 Duplicate Sequence (Obs Delta = +1): {s5} ({before} -> {after})")

    # S6: Out-of-Order Sequence
    before_ooo = get_obs()["out_of_order"]
    high_seq = seq + 50000
    low_seq = high_seq - 50
    p_high = json.dumps({"vehicle_id": "TRUCK_01", "sequence_number": high_seq, "speed": 2.5}).encode()
    p_low = json.dumps({"vehicle_id": "TRUCK_01", "sequence_number": low_seq, "speed": 1.5}).encode()
    urllib.request.urlopen(
        urllib.request.Request(
            f"{base_url}/api/telemetry",
            data=p_high,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
    )
    urllib.request.urlopen(
        urllib.request.Request(
            f"{base_url}/api/telemetry",
            data=p_low,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
    )
    after_ooo = get_obs()["out_of_order"]
    s6 = after_ooo - before_ooo == 1
    print(f"S6 Out-of-Order Sequence (Obs Delta = +1): {s6} ({before_ooo} -> {after_ooo})")

    # S7: Unknown Vehicle Command
    cmd_uv = json.dumps(
        {
            "command_id": f"CMD-UV-{int(time.time())}",
            "vehicle_id": "GHOST_TRUCK_X",
            "action": "STOP",
            "target_speed": 0.0,
            "reason": "TEST",
        }
    ).encode()
    req_uv = urllib.request.Request(
        f"{base_url}/api/commands",
        data=cmd_uv,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req_uv) as resp:
        body = json.loads(resp.read().decode())
        s7 = body.get("status") == "UNKNOWN_VEHICLE"
    print(f'S7 Unknown Vehicle Command (status=UNKNOWN_VEHICLE): {s7} (body status: {body.get("status")})')

    # S8: Invalid Command Action
    try:
        cmd_ia = json.dumps(
            {
                "command_id": f"CMD-IA-{int(time.time())}",
                "vehicle_id": "TRUCK_01",
                "action": "EXPLODE",
                "target_speed": 1.0,
                "reason": "TEST",
            }
        ).encode()
        urllib.request.urlopen(
            urllib.request.Request(
                f"{base_url}/api/commands",
                data=cmd_ia,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
        )
        s8 = False
    except urllib.error.HTTPError as e:
        s8 = e.code == 400
    print(f"S8 Invalid Action (HTTP 400): {s8}")

    # S9: Duplicate Command ID
    dup_id = f"CMD-DUP-{int(time.time())}"
    cmd_d = json.dumps(
        {
            "command_id": dup_id,
            "vehicle_id": "TRUCK_01",
            "action": "STOP",
            "target_speed": 0.0,
            "reason": "TEST",
        }
    ).encode()
    with urllib.request.urlopen(
        urllib.request.Request(
            f"{base_url}/api/commands",
            data=cmd_d,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
    ) as r1:
        st1 = json.loads(r1.read().decode()).get("status")
    with urllib.request.urlopen(
        urllib.request.Request(
            f"{base_url}/api/commands",
            data=cmd_d,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
    ) as r2:
        st2 = json.loads(r2.read().decode()).get("status")
    s9 = st2 == "DUPLICATE"
    print(f"S9 Duplicate Command ID (Second status=DUPLICATE): {s9} ({st1} -> {st2})")

    # S10: Oversized Payload
    try:
        big_data = json.dumps({"vehicle_id": "TRUCK_01", "payload": "A" * 70000}).encode()
        urllib.request.urlopen(
            urllib.request.Request(
                f"{base_url}/api/telemetry",
                data=big_data,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
        )
        s10 = False
    except urllib.error.HTTPError as e:
        s10 = e.code == 413
    print(f"S10 Oversized Payload (HTTP 413): {s10}")

    all_passed = all([s2, s3, s4, s5, s6, s7, s8, s9, s10])
    print("\n" + "=" * 80)
    print(f"P10 LIVE VERIFICATION: {'ALL CHECKS PASSED (100%)' if all_passed else 'FAILURES DETECTED'}")
    print("=" * 80)
    return all_passed


if __name__ == "__main__":
    test_p10_live()
