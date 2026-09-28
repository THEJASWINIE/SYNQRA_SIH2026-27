#!/usr/bin/env python3
"""
FOG-ORCHESTRATOR 2.0 — Safe Manual Motor Diagnostic Tool (Phase 2).

Commands physical vehicles (TRUCK_01, TRUCK_02) via the authoritative backend command path
or direct HTTP vehicle endpoint to test:
    - FORWARD 0.20 m/s
    - FORWARD 0.40 m/s
    - FORWARD 0.60 m/s
    - STOP

Maintains single authoritative protocol and reports:
    - vehicle_id
    - sequence
    - direction
    - requested_speed_mps
    - safe_speed_mps
    - applied_speed_mps
    - pwm
    - rpm
    - encoder_state
    - motor_state
    - governor_state
    - timestamp
"""

import sys
import os
import argparse
import json
import time
import urllib.request
import urllib.error


def parse_args():
    parser = argparse.ArgumentParser(
        description="FOG-ORCHESTRATOR 2.0: Safe Motor Diagnostic Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python tools/test_motor.py --vehicle TRUCK_01 --action FORWARD --speed 0.20
  python tools/test_motor.py --vehicle TRUCK_01 --action FORWARD --speed 0.40
  python tools/test_motor.py --vehicle TRUCK_01 --action FORWARD --speed 0.60
  python tools/test_motor.py --vehicle TRUCK_01 --action STOP
  python tools/test_motor.py --vehicle TRUCK_02 --action FORWARD --speed 0.40
  python tools/test_motor.py --vehicle ALL --action STOP
  python tools/test_motor.py --vehicle TRUCK_01 --action FORWARD --speed 0.40 --direct-ip 192.168.137.43
        """,
    )
    parser.add_argument(
        "--vehicle",
        type=str,
        default="TRUCK_01",
        help="Target vehicle: TRUCK_01, TRUCK_02, or ALL (default: TRUCK_01)",
    )
    parser.add_argument(
        "--action",
        type=str,
        choices=["FORWARD", "STOP", "TARGET_SPEED"],
        default="FORWARD",
        help="Command action: FORWARD, STOP, or TARGET_SPEED (default: FORWARD)",
    )
    parser.add_argument(
        "--speed",
        type=float,
        default=0.40,
        help="Target speed in m/s (default: 0.40)",
    )
    parser.add_argument(
        "--backend-url",
        type=str,
        default=os.environ.get("FOG_BACKEND_URL", "http://127.0.0.1:8000"),
        help="HMI Backend base URL (default: http://127.0.0.1:8000)",
    )
    parser.add_argument(
        "--direct-ip",
        type=str,
        default=None,
        help="Optional: Send command directly to vehicle ESP32 IP instead of backend",
    )
    parser.add_argument(
        "--operator-id",
        type=str,
        default="OP-DEMO-01",
        help="Operator ID for backend session authorization (default: OP-DEMO-01)",
    )
    parser.add_argument(
        "--operator-secret",
        type=str,
        default=os.environ.get("FOG_OPERATOR_SECRET", "dev_secret"),
        help="Operator secret for backend session authorization",
    )
    return parser.parse_args()


def get_operator_token(backend_url: str, operator_id: str, secret: str) -> str | None:
    """Acquires a bearer token from the backend operator registry."""
    url = f"{backend_url.rstrip('/')}/api/operator/session"
    payload = json.dumps({"operator_id": operator_id, "secret": secret}).encode("utf-8")
    req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=3.0) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data.get("token")
    except Exception as exc:
        print(f"[WARN] Operator session login failed ({exc}); trying direct command dispatch...")
        return None


def send_backend_command(backend_url: str, vehicle_id: str, action: str, speed_mps: float, token: str | None) -> dict:
    """Dispatches command to the canonical backend /api/commands."""
    url = f"{backend_url.rstrip('/')}/api/commands"
    cmd_id = f"DIAG-{vehicle_id}-{int(time.time() * 1000) % 100000}"
    payload = {
        "command_id": cmd_id,
        "vehicle_id": vehicle_id,
        "action": action,
        "target_speed": speed_mps if action != "STOP" else 0.0,
        "reason": f"DIAGNOSTIC_MOTOR_TEST_{action}",
    }
    data = json.dumps(payload).encode("utf-8")
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, data=data, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=3.0) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as he:
        err_body = he.read().decode("utf-8")
        return {"error": f"HTTP {he.code}", "detail": err_body}
    except Exception as exc:
        return {"error": str(exc)}


def send_direct_command(vehicle_ip: str, vehicle_id: str, action: str, speed_mps: float) -> dict:
    """Sends command directly to ESP32 WebServer on port 80."""
    url = f"http://{vehicle_ip}/api/command"
    cmd_id = f"DIRECT-{vehicle_id}-{int(time.time() * 1000) % 100000}"
    payload = {
        "command_id": cmd_id,
        "vehicle_id": vehicle_id,
        "action": action,
        "target_speed": speed_mps if action != "STOP" else 0.0,
        "target_speed_ms": speed_mps if action != "STOP" else 0.0,
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=2.0) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception as exc:
        return {"error": str(exc)}


def fetch_vehicle_state(backend_url: str, vehicle_id: str) -> dict | None:
    """Fetches the latest authoritative vehicle state from /api/vehicles."""
    url = f"{backend_url.rstrip('/')}/api/vehicles"
    try:
        with urllib.request.urlopen(url, timeout=3.0) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data.get("vehicles", {}).get(vehicle_id)
    except Exception:
        return None


def fetch_direct_status(vehicle_ip: str) -> dict | None:
    """Fetches diagnostic status directly from ESP32 /api/command/status."""
    url = f"http://{vehicle_ip}/api/command/status"
    try:
        with urllib.request.urlopen(url, timeout=2.0) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception:
        return None


def print_diagnostic_report(vehicle_id: str, action: str, speed: float, cmd_resp: dict, state: dict | None, direct_status: dict | None):
    print("\n============================================================")
    print(f"       MOTOR DIAGNOSTIC REPORT — {vehicle_id}")
    print("============================================================")
    print(f"Command Action:          {action}")
    print(f"Requested Speed:         {speed:.2f} m/s" if action != "STOP" else "0.00 m/s (STOP)")
    print(f"Command Response Status: {cmd_resp.get('status', cmd_resp.get('error', 'UNKNOWN'))}")

    if direct_status:
        print("\n--- ESP32 PHYSICAL VEHICLE DIRECT TELEMETRY ---")
        print(f"Vehicle ID:              {direct_status.get('vehicle_id', vehicle_id)}")
        print(f"Direction:               {direct_status.get('direction', 'UNKNOWN')}")
        print(f"Commanded Speed:         {direct_status.get('commanded_speed_ms', 0.0):.3f} m/s")
        print(f"Applied Speed:           {direct_status.get('applied_speed_ms', 0.0):.3f} m/s")
        print(f"Target PWM:              {direct_status.get('target_pwm', 0)}")
        print(f"Applied PWM:             {direct_status.get('applied_pwm', 0)}")
        print(f"Wheel RPM:               {direct_status.get('wheel_rpm', 0.0):.2f}")
        print(f"Motor Driver:            {direct_status.get('driver', 'TB6612FNG')}")

    if state:
        print("\n--- DIGITAL TWIN & HMI AUTHORITATIVE STATE ---")
        print(f"Sequence:                {state.get('sequence_number', state.get('sequence', 0))}")
        print(f"Communication Status:    {state.get('communication_status', 'OFFLINE')}")
        print(f"Safe Speed (v_safe):     {state.get('v_safe_mps', 0.0):.3f} m/s")
        print(f"Governor State:          {state.get('governor_state', 'NORMAL')}")
        print(f"Fog Factor:              {state.get('fog_factor', 1.0):.2f}")
        print(f"Weather Condition:       {state.get('weather_condition', 'CLEAR')}")
        print(f"Visibility:              {state.get('visibility_m', 1000.0):.1f} m")
        print(f"Telemetry Freshness:     {state.get('data_quality', 'UNKNOWN')} (Age: {state.get('age_seconds', 0.0)}s)")

    print("============================================================\n")


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    args = parse_args()

    vehicles = ["TRUCK_01", "TRUCK_02"] if args.vehicle.upper() == "ALL" else [args.vehicle.upper()]

    token = None
    if not args.direct_ip:
        token = get_operator_token(args.backend_url, args.operator_id, args.operator_secret)

    for vid in vehicles:
        print(f"[DIAGNOSTIC] Commanding {vid} -> Action: {args.action}, Speed: {args.speed:.2f} m/s...")

        direct_ip = args.direct_ip
        if not direct_ip:
            # Check standard known vehicle IPs
            known_ips = {"TRUCK_01": "192.168.137.43", "TRUCK_02": "192.168.137.126"}
            direct_ip = known_ips.get(vid)

        if args.direct_ip:
            resp = send_direct_command(args.direct_ip, vid, args.action, args.speed)
        else:
            resp = send_backend_command(args.backend_url, vid, args.action, args.speed, token)

        # Allow time for vehicle loop to process and report
        time.sleep(0.5)

        state = fetch_vehicle_state(args.backend_url, vid) if not args.direct_ip else None
        direct_status = fetch_direct_status(direct_ip) if direct_ip else None

        print_diagnostic_report(vid, args.action, args.speed, resp, state, direct_status)


if __name__ == "__main__":
    main()
