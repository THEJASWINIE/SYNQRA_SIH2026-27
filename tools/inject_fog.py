#!/usr/bin/env python3
"""
FOG-ORCHESTRATOR 2.0 — External Environmental Fog Injection Tool.

Submits simulated/injected environmental condition updates to the authoritative
Digital Twin Backend via POST /api/environment/fog.

Engineering Invariant (AGENTS.md):
- Does NOT duplicate governor or physics logic inside the CLI.
- The CLI only submits the environmental condition and receives the authoritative
  Digital Twin and fleet governor response.
- Explicit provenance: INJECTED (never fabricated as hardware/physical sensor measurement).
"""

import sys
import os
import argparse
import json
import time
from datetime import datetime, timezone
import urllib.request
import urllib.error


def parse_args():
    parser = argparse.ArgumentParser(
        description="FOG-ORCHESTRATOR 2.0: External Environmental Condition Ingestion CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python tools/inject_fog.py --intensity 0.00
  python tools/inject_fog.py --intensity 0.25
  python tools/inject_fog.py --intensity 0.50
  python tools/inject_fog.py --intensity 0.75
  python tools/inject_fog.py --intensity 1.00
  python tools/inject_fog.py --condition clear
  python tools/inject_fog.py --condition light
  python tools/inject_fog.py --condition moderate
  python tools/inject_fog.py --condition heavy
  python tools/inject_fog.py --condition severe
  python tools/inject_fog.py --condition critical --severe-stop
        """
    )
    parser.add_argument(
        "--intensity",
        type=float,
        default=None,
        help="Fog intensity fraction between 0.00 (CLEAR) and 1.00 (MAX DENSE FOG)",
    )
    parser.add_argument(
        "--condition",
        type=str,
        default=None,
        help="Named condition (clear, light, moderate, heavy, severe, critical)",
    )
    parser.add_argument(
        "--severe-stop",
        action="store_true",
        default=False,
        help="Enforce emergency complete stop (v_safe = 0.0 m/s) on severe/critical fog",
    )
    parser.add_argument(
        "--endpoint",
        type=str,
        default=os.environ.get("FOG_BACKEND_URL", "http://127.0.0.1:8000/api/environment/fog"),
        help="Target backend environment API endpoint (default: http://127.0.0.1:8000/api/environment/fog)",
    )
    parser.add_argument(
        "--source",
        type=str,
        default="CLI_INJECTION",
        help="Environmental injection source tag (default: CLI_INJECTION)",
    )
    return parser.parse_args()


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    args = parse_args()

    if args.intensity is None and args.condition is None:
        print("[ERROR] Must specify either --intensity (0.0 to 1.0) or --condition (clear, light, moderate, heavy, severe, critical)", file=sys.stderr)
        sys.exit(1)

    if args.intensity is not None:
        if args.intensity < 0.0 or args.intensity > 1.0:
            print(f"[ERROR] --intensity {args.intensity} out of valid range [0.0, 1.0]", file=sys.stderr)
            sys.exit(1)

    cond_clean = args.condition.upper() if args.condition else None
    if cond_clean:
        valid_conditions = {"CLEAR", "LIGHT", "LIGHT_FOG", "MODERATE", "MODERATE_FOG", "HEAVY", "HEAVY_FOG", "SEVERE", "SEVERE_FOG", "CRITICAL"}
        if cond_clean not in valid_conditions:
            print(f"[ERROR] Invalid --condition '{args.condition}'. Must be one of: CLEAR, LIGHT, MODERATE, HEAVY, SEVERE, CRITICAL", file=sys.stderr)
            sys.exit(1)

    payload = {
        "fog_intensity": args.intensity,
        "condition": cond_clean,
        "source": args.source,
        "severe_stop_policy": args.severe_stop or (cond_clean == "CRITICAL"),
    }
    # Clean None values
    payload = {k: v for k, v in payload.items() if v is not None}

    req_data = json.dumps(payload).encode("utf-8")

    # Endpoint retry candidates (prevents Windows WinError 10013 IPv6 localhost connection access issues)
    candidates = [args.endpoint]
    if "localhost" in args.endpoint:
        candidates.append(args.endpoint.replace("localhost", "127.0.0.1"))
    elif "127.0.0.1" in args.endpoint:
        candidates.append(args.endpoint.replace("127.0.0.1", "localhost"))

    t_start = time.time()
    iso_ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    data = None
    last_err = None
    for target_url in candidates:
        for attempt in range(4):
            req = urllib.request.Request(
                target_url,
                data=req_data,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            try:
                with urllib.request.urlopen(req, timeout=5.0) as resp:
                    resp_bytes = resp.read()
                    status_code = resp.status
                    data = json.loads(resp_bytes.decode("utf-8"))
                    break
            except urllib.error.HTTPError as e:
                err_msg = e.read().decode("utf-8")
                print(f"[ERROR] Backend HTTP {e.code}: {err_msg}", file=sys.stderr)
                sys.exit(2)
            except urllib.error.URLError as e:
                last_err = e
                time.sleep(0.15)
                continue
            except Exception as e:
                last_err = e
                time.sleep(0.15)
                continue
        if data is not None:
            break

    if data is None:
        reason_str = str(last_err.reason) if hasattr(last_err, "reason") else str(last_err)
        print(f"[ERROR] Could not connect to backend endpoint '{args.endpoint}': {reason_str}", file=sys.stderr)
        print("        Ensure the FOG-ORCHESTRATOR FastAPI backend is running (uvicorn app.main:app --port 8000).", file=sys.stderr)
        sys.exit(3)

    latency_ms = (time.time() - t_start) * 1000.0

    env = data.get("environment", {})
    vehicles = data.get("vehicles", {})
    events = data.get("causal_events", [])

    print("=" * 72)
    print(" FOG-ORCHESTRATOR 2.0 — EXTERNAL ENVIRONMENT INJECTION")
    print("=" * 72)
    print(f" [TIMESTAMP]     {iso_ts} (Latency: {latency_ms:.1f}ms)")
    print(f" [SOURCE]        {env.get('source', args.source)} · PROVENANCE: INJECTED")
    print(f" [CONDITION]     {env.get('weather_condition', 'UNKNOWN')}")
    print(f" [FOG INTENSITY] {env.get('fog_intensity', 0.0):.2f} ({(env.get('fog_intensity', 0.0) * 100.0):.0f}%)")
    print(f" [VISIBILITY]    {env.get('visibility_m', 0.0):.1f} m")
    print(f" [FOG FACTOR]    {env.get('fog_factor', 1.0):.2f} ({(env.get('fog_factor', 1.0) * 100.0):.0f}% speed factor)")
    print(f" [ACTIVE POLICY] {env.get('active_policy', 'FOG_VISIBILITY_CONSTRAINT')}")
    print("-" * 72)
    print(" AUTHORITATIVE FLEET GOVERNOR STATUS:")
    for vid, vrep in vehicles.items():
        vmax = vrep.get("vmax_mps", 0.0)
        v_safe = vrep.get("v_safe_mps", 0.0)
        v_applied = vrep.get("applied_speed_mps", 0.0)
        gov_state = vrep.get("governor_state", "UNKNOWN")
        driver = vrep.get("motor_driver", "UNKNOWN")
        print(f"   * {vid} ({driver}): Vmax={vmax:.2f} m/s | v_safe={v_safe:.2f} m/s | applied={v_applied:.2f} m/s | {gov_state}")
    print("-" * 72)
    if events:
        print(f" CAUSAL AUDIT EVENTS GENERATED ({len(events)}):")
        for ev in events:
            cat = ev.get("category", "EVENT")
            desc = ev.get("description", "")
            eid = ev.get("event_id", "")
            print(f"   [{cat}] ({eid}): {desc}")
    print("=" * 72)
    print(f" RESULT: SUCCESS (HTTP {status_code})")
    print("=" * 72)


if __name__ == "__main__":
    main()
