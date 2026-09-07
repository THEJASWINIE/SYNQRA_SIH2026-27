"""
P9 end-to-end verification: a REAL uvicorn process, real HTTP, a real WebSocket.

Unlike the pytest suites, which drive the ASGI app in-process, this starts the backend the
way the runbook does - from SYNQRA_SIH2026-27-HMI/backend/, not the repo root - so it also
proves configuration is found independently of the working directory.

    python verify_p9_end_to_end.py

Exits non-zero if any case fails.

ALL DATA IS SIMULATED / EMULATED. No physical ESP32 is involved, and nothing here
constitutes physical validation.
"""
import json, subprocess, sys, time, urllib.request, os

ROOT = os.path.dirname(os.path.abspath(__file__))
BACKEND = os.path.join(ROOT, "SYNQRA_SIH2026-27-HMI", "backend")
BASE = "http://127.0.0.1:8077"
results = []


def rec(name, ok, detail=""):
    results.append((name, "PASS" if ok else "FAIL", detail))


def get(path):
    with urllib.request.urlopen(BASE + path, timeout=5) as r:
        return json.loads(r.read())


def post(path, payload):
    req = urllib.request.Request(BASE + path, data=json.dumps(payload).encode(),
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=5) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read() or b"{}")


env = dict(os.environ, PYTHONPATH=ROOT + os.pathsep + os.path.join(ROOT, "SYNQRA_SIH2026-27-main"))
# Launched from a DIFFERENT directory on purpose: proves the P6.1/P9 CWD fix.
proc = subprocess.Popen([sys.executable, "-m", "uvicorn", "app.main:app",
                         "--host", "127.0.0.1", "--port", "8077", "--log-level", "warning"],
                        cwd=BACKEND, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
try:
    for _ in range(60):
        try:
            get("/api/health"); break
        except Exception:
            time.sleep(0.5)
    else:
        raise SystemExit("server never came up")

    # A. health
    h = get("/api/health"); rec("A health", h["status"] == "ok", str(h["service"]))

    # B. mode honest before hardware
    m = get("/api/mode")
    rec("B mode MOCK before hardware", m["mode"] == "MOCK" and m["hardware_seen"] is False, str(m))

    # C. observability wired
    o = get("/api/observability")
    rec("C observability wired", o["twin_attached"] and o["telemetry_ingest"] is not None,
        "twin_attached=%s" % o["twin_attached"])

    # D. malformed telemetry rejected, server survives
    st, _ = post("/api/telemetry", {"rpm": 1.0})
    rec("D malformed telemetry rejected", st == 400, "HTTP %d" % st)

    # E. mock ingress cannot self-declare LIVE
    st, _ = post("/api/telemetry", {"vehicle_id": "TRUCK_01", "sequence_number": 5,
                                    "rpm": 100.0, "timestamp": time.time(), "data_quality": "LIVE"})
    v = get("/api/vehicles")
    rec("E mock cannot declare LIVE",
        v["vehicles"]["TRUCK_01"]["data_quality"] == "SIMULATED" and v["mode"] == "MOCK",
        v["vehicles"]["TRUCK_01"]["data_quality"])

    # F. hardware ingress -> LIVE + Twin
    st, body = post("/api/hardware/telemetry", {
        "vehicle_id": "TRUCK_02", "sequence": 6_500_001, "source": "DIRECT_WIFI",
        "rpm": 210.0, "speed": 2.5, "ax": 0.1, "ay": 0.0, "az": 9.81,
        "gx": 0.0, "gy": 0.0, "gz": 0.0, "rssi": -60, "snr": 9.0})
    m = get("/api/mode")
    rec("F hardware ingress -> LIVE", st == 200 and m["mode"] == "LIVE" and m["hardware_connected"],
        "%s %s" % (body.get("status"), m["mode"]))

    # G. Twin snapshot carries provenance, no fabricated position
    snap = get("/api/twin/snapshot")
    dyn = snap["vehicles"]["TRUCK_02"]["dynamic"]
    rec("G twin provenance + no fabrication",
        dyn["rpm"]["source"] == "HARDWARE" and "position_s" not in dyn,
        "rpm.source=%s position_s_present=%s" % (dyn["rpm"]["source"], "position_s" in dyn))

    # H. unknown vehicle refused, counted
    before = get("/api/observability")["telemetry_ingest"]["unknown_vehicle"]
    post("/api/telemetry", {"vehicle_id": "GHOST", "sequence_number": 1, "rpm": 1.0,
                            "timestamp": time.time()})
    after = get("/api/observability")["telemetry_ingest"]["unknown_vehicle"]
    rec("H unknown vehicle counted", after == before + 1, "%d -> %d" % (before, after))

    # I. command rejection is counted in the AGGREGATE (the P9 counter fix)
    before = get("/api/observability")["command_gateway"]
    post("/api/commands", {"command_id": "SMOKE_1", "vehicle_id": "GHOST_TRUCK",
                           "action": "TARGET_SPEED", "target_speed": 5.0, "reason": "smoke"})
    after = get("/api/observability")["command_gateway"]
    rec("I command rejections aggregate", after["rejected"] > before["rejected"],
        "rejected %d -> %d" % (before["rejected"], after["rejected"]))

    # J. WebSocket: connect, receive, forged HARDWARE provenance refused
    try:
        from websockets.sync.client import connect
        with connect("ws://127.0.0.1:8077/api/ws", open_timeout=5) as ws:
            first = json.loads(ws.recv(timeout=5))
            ws.send(json.dumps({"type": "telemetry", "data": {
                "vehicle_id": "TRUCK_01", "sequence_number": 6_600_001, "rpm": 55.0,
                "source": "HARDWARE", "is_simulated": False}}))
            reply = None
            for _ in range(6):
                msg = json.loads(ws.recv(timeout=5))
                if msg.get("type") != "twin_vehicle_update":
                    reply = msg; break
            ws.send("not json")
            malformed = {}
            for _ in range(8):
                msg = json.loads(ws.recv(timeout=5))
                if msg.get("type") != "twin_vehicle_update":
                    malformed = msg; break
        rec("J websocket live + provenance not self-declared",
            first["type"] == "connection_established" and reply["source"] == "SIMULATION",
            "reply.source=%s" % reply.get("source"))
        rec("K malformed WS answered, socket alive", malformed.get("reason") == "MALFORMED_JSON",
            str(malformed.get("reason")))
    except ImportError:
        rec("J websocket live", False, "websockets package not installed - NOT TESTED")
        rec("K malformed WS answered", False, "websockets package not installed - NOT TESTED")

    # server still healthy after everything
    rec("L server survived the sweep", get("/api/health")["status"] == "ok")
finally:
    proc.terminate()
    try:
        proc.wait(timeout=10)
    except Exception:
        proc.kill()

width = max(len(n) for n, _, _ in results)
for n, s, d in results:
    print("%-*s  %-4s  %s" % (width, n, s, d))
passed = sum(1 for _, s, _ in results if s == "PASS")
print("\n%d/%d PASS" % (passed, len(results)))
sys.exit(0 if passed == len(results) else 1)
