# DEMO RUNBOOK

Every command here was executed during P9 on Windows 11 / Python 3.12.10 / Node with
vitest 3.2.7. Anything not executed is marked **NOT TESTED**.

**All of it is SIMULATION or EMULATED.** No physical ESP32 was connected. Section 6 says
what would change with real hardware; it has not been run.

---

## 0. Prerequisites

```bash
cd <repo root>
pip install -r requirements.txt
cd SYNQRA_SIH2026-27-HMI/frontend && npm install
```

`pygame` is NOT installed and is NOT required for anything below except §5.

---

## 1. Run the test suites

Three separate suites. Run each from its own directory.

```bash
# root: ingestion, Twin, physics, gateway, projection, observability
cd <repo root>
python -m pytest -q                     # P10 result: 414 passed

# main sub-repo: simulator, models, UI bridge
cd SYNQRA_SIH2026-27-main
python -m pytest -q                     # P9 result: 49 passed, 1 failed (pygame absent)

# frontend
cd SYNQRA_SIH2026-27-HMI/frontend
npx vitest run                          # P10 result: 884 passed
npx tsc --noEmit                        # P9 result: clean
```

The two backend contract suites are not in any of the above `testpaths`; run them
explicitly:

```bash
cd SYNQRA_SIH2026-27-HMI/backend && python -m pytest tests -q    # 33 passed
cd SYNQRA_SIH2026-27-main/backend && python -m pytest tests -q   # 33 passed
```

---

## 2. Start the backend

```bash
cd SYNQRA_SIH2026-27-HMI/backend
set PYTHONPATH=<repo root>;<repo root>\SYNQRA_SIH2026-27-main     # Windows
export PYTHONPATH=<repo root>:<repo root>/SYNQRA_SIH2026-27-main  # bash
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Configuration is located from the source tree, not the working directory, so this starts
correctly from any directory (verified from six, including outside the repo).

Confirm the Twin actually attached — this is the check that catches a broken `PYTHONPATH`:

```bash
curl http://127.0.0.1:8000/api/observability
# expect  "twin_attached": true   and   "telemetry_ingest": {...}
# "twin_attached": false means the Twin package was not importable: fix PYTHONPATH.
```

### CORS (changed in P9)

Allowed origins come from `HMI_CORS_ORIGINS`, default
`http://localhost:5173,http://127.0.0.1:5173`. Serving the frontend from another host
needs that origin listed:

```bash
export HMI_CORS_ORIGINS=http://192.168.4.2:5173
# or, to restore the pre-P9 wildcard explicitly:
export HMI_CORS_ORIGINS=*
```

---

## 3. Start the frontend

```bash
cd SYNQRA_SIH2026-27-HMI/frontend
npm run dev          # http://localhost:5173
```

Screens: **Technician HMI** (fleet/control-room) and **Operator HMI** (single vehicle,
one dominant instruction).

---

## 4. Prove the honesty invariants — no hardware needed

Each of these was executed in P9 and passed.

```bash
# 4.1  Before any hardware packet, the process must NOT claim a link.
curl http://127.0.0.1:8000/api/mode
# {"mode":"MOCK","hardware_seen":false,"hardware_connected":false,"hardware_age_seconds":null}

# 4.2  The mock ingress cannot promote itself to physical telemetry.
curl -X POST http://127.0.0.1:8000/api/telemetry -H "Content-Type: application/json" \
  -d '{"vehicle_id":"TRUCK_01","sequence_number":5,"rpm":100.0,"data_quality":"LIVE"}'
curl http://127.0.0.1:8000/api/vehicles
# TRUCK_01.data_quality == "SIMULATED"  and  mode == "MOCK"

# 4.3  The physical ingress does flip the mode, and reaches the Twin.
curl -X POST http://127.0.0.1:8000/api/hardware/telemetry -H "Content-Type: application/json" \
  -d '{"vehicle_id":"TRUCK_02","sequence":6500001,"source":"DIRECT_WIFI","rpm":210.0,
       "speed":2.5,"ax":0.1,"ay":0.0,"az":9.81,"gx":0.0,"gy":0.0,"gz":0.0,"rssi":-60,"snr":9.0}'
curl http://127.0.0.1:8000/api/mode          # mode LIVE, hardware_connected true
curl http://127.0.0.1:8000/api/twin/snapshot # rpm.source HARDWARE; NO position_s key

# 4.4  A stale link stops claiming LIVE (wait > offline_threshold_seconds, default 10 s).
curl http://127.0.0.1:8000/api/mode          # back to MOCK, hardware_seen still true

# 4.5  A bad packet is refused and counted, and the server survives.
curl -X POST http://127.0.0.1:8000/api/telemetry -H "Content-Type: application/json" -d '{"rpm":1.0}'
# HTTP 400
curl http://127.0.0.1:8000/api/observability  # telemetry_ingest.unknown_vehicle / invalid moved

# 4.6  An unsafe or unknown-vehicle command is refused, and the AGGREGATE counter moves.
curl -X POST http://127.0.0.1:8000/api/commands -H "Content-Type: application/json" \
  -d '{"command_id":"DEMO_1","vehicle_id":"GHOST_TRUCK","action":"TARGET_SPEED",
       "target_speed":5.0,"reason":"demo"}'
curl http://127.0.0.1:8000/api/observability  # command_gateway.rejected incremented
```

The whole sequence is automated as `verify_p9_end_to_end.py`; P9 ran it against a real uvicorn process started from
`SYNQRA_SIH2026-27-HMI/backend/` and got **12/12 PASS** (cases A–L in
[VERIFICATION_MATRIX.md](VERIFICATION_MATRIX.md) §4).

---

## 4b. The P10 final verification - the two commands that matter

Run these to prove the whole system in one go. Both were executed in P10.

```bash
cd <repo root>

# The full causal chain, in-process: fog -> Twin -> fog_safe -> gateway -> vehicle
# -> telemetry -> Twin -> projection -> HMI -> game_ui, and the recovery afterwards.
python verify_p10_final.py            # P10 result: 22/22 PASS
# writes results/P10_E2E_TRACE.csv, the reviewable artefact for the demo

# The process boundary: a real backend payload, parsed by the frontend own schema.
python verify_p10_live_contract.py    # P10 result: 8/8 PASS
# refreshes SYNQRA_SIH2026-27-HMI/contracts/fixtures/live/TwinVehicle.live.json
```

The chain also runs under pytest (`tests/test_p10_chain.py`), and the captured payload is
validated by `frontend/src/contracts/liveContract.test.ts` on every `npx vitest run`.

**What the trace shows, as measured:**

| visibility (m) | 50 | 30 | 10 | 6 | 30 | 50 |
|---|---|---|---|---|---|---|
| v_safe (m/s) | 13.89 | 12.00 | 4.26 | 1.55 | 12.00 | 13.89 |

Fog closes in and the safe speed collapses to 1.55 m/s. The gateway refuses anything
faster, the vehicle own governor clamps harder still, and everything recovers when the fog
lifts. That sequence, not the animation, is the proof.

## 5. The fog closed-loop demo (Pygame)

**Requires `pygame`, which is not installed here — NOT TESTED in P9.**

```bash
cd SYNQRA_SIH2026-27-main
python game_ui.py
```

Lower visibility and watch, in order: environment changes → `v_safe` falls → commanded
speed falls → vehicle slows → Twin updates → display updates. Raise visibility and watch
the safety state recover.

What the display proves rather than decorates: a value the Twin does not hold renders as
`--`, never as `0` and never as a speed.

The same loop WITHOUT pygame, headlessly, does run here:

```bash
cd <repo root>
python -m pytest tests/test_game_ui_render_smoke.py tests/test_game_ui_twin_client.py -q
python -m pytest tests/test_end_to_end.py tests/test_fog_propagation.py -q
```

---

## 6. With real hardware — NOT EXECUTED

Not run in P0–P9. No claim is made about it.

1. Flash `esp32_code/`. Copy `secrets.example.h` to `secrets.h` and fill in the Wi-Fi
   credentials; `secrets.h` is git-ignored.
2. Point the vehicle at `POST /api/hardware/telemetry` on the backend host.
3. Expect `/api/mode` to report `hardware_connected: true` while packets keep arriving, and
   to fall back to `MOCK` within `offline_threshold_seconds` of the last one.
4. Expect `/api/twin/snapshot` to show `rpm.source == "HARDWARE"`, and `TRUCK_02`'s speed as
   `source=DERIVED, origin=HARDWARE` — it is PWM-derived, not measured.

Until that has actually been executed, results stay **SIMULATION** / **EMULATED**.
