# HARDWARE → FRONTEND CONTRACT MAP

**Date:** 2026-09-08
**Scope:** the hardware integration pulled in commit `83d05d3`
(`feat(hardware): integrate Vehicle A direct Wi-Fi telemetry, session reset endpoints, and
documentation`, jagadeesh28-dev, 2026-09-08 12:40 +0530).
**Method:** repository inspection and one executed import test. Nothing assumed.

---

## 0. BLOCKER — THE PULLED COMMIT DOES NOT RUN AS COMMITTED

`83d05d3` adds `Optional[str]` (line 924) and `Optional[HardwareResetRequest]` (line 928)
to `backend/app/main.py`, but its import line is `from typing import Dict, Any, List`.

Verified by executing the committed file:

```
PULLED VERSION FAILS: NameError -> name 'Optional' is not defined
```

The backend cannot start from that commit. A one-line fix (adding `Optional` to the
`typing` import) **exists in the working tree but is NOT committed**. Anyone checking out
`83d05d3` clean gets a dead backend.

**Action required: commit that one-line fix.** No other change is needed.

---

## 1. WHAT THE PULL ACTUALLY INTRODUCED

| File | Change |
|---|---|
| `esp32_code/sketch_aug26a/sketch_aug26a.ino` | Vehicle A now posts telemetry **directly over Wi-Fi**, no longer only via LoRa relay |
| `backend/app/main.py` | `POST /api/hardware/reset`, `GET /api/hardware/sequence`, hardware-telemetry logging, `_BoundedDedupStore.clear_vehicle()` |
| `reset_hardware_session.py` | CLI to reset sequence state |
| `WIFI_HARDWARE_INTEGRATION.md`, `WIFI_HARDWARE_TEST_MATRIX.md`, `CONFIGURATION_EXAMPLE.md`, `docs/DEMO_RUNBOOK.md` | documentation |

**This resolves the A→B LoRa format mismatch previously identified.** Vehicle A no longer
depends on Vehicle B relaying `STATE,TRUCK_01,…`; it posts JSON to the backend itself.

---

## 2. THE ACTUAL PHYSICAL DATA PATH

Every stage verified in source.

| Stage | File | Detail |
|---|---|---|
| Sensors | — | LM393 encoder (ISR pulse count), MPU6050 @ `0x68` (I2C) |
| MCU | `sketch_aug26a.ino` | ESP32, Vehicle A = `TRUCK_01` |
| Sequence | `sketch_aug26a.ino:1578` | `telemetrySequence++` — strictly monotonic, per transmitted frame |
| Boot sync | `sketch_aug26a.ino:1512-1534` | `GET /api/hardware/sequence?vehicle_id=TRUCK_01`, seeds from `next_sequence` |
| Transport | `sketch_aug26a.ino:1582-1608` | `HTTPClient` POST, JSON, 1000 ms timeout, endpoint from `secrets.h` (`SECRET_HMI_TELEMETRY_URL`) |
| Ingress | `main.py:668` | `POST /api/hardware/telemetry`, `HardwareTelemetryPayload` |
| Validation | `main.py:676-734` | dedup by `(vehicle_id, sequence)`; source priority `DIRECT_WIFI > V2V_VIA_TRUCK_02`; `source` must be one of those two or **HTTP 400** |
| Canonical ingest | `main.py` | `is_simulated=False` → `telemetry_ingest.py` stamps `origin=HARDWARE` |
| Twin | `twin_projection.py` | per-field source/origin/quality/freshness |
| Push | `main.py` | `await broadcast_twin_update(vid)` → WebSocket |
| Frontend | `LiveDataProvider.ts` | one WebSocket; `ProviderHost.tsx:151` picks LIVE or MOCK **statically** |

**No LIVE→MOCK fallback exists.** `ProviderHost.tsx:151` is
`targetKind === "LIVE" ? liveProvider : mockProvider`, set once from `VITE_PROVIDER`. The
requirement "LIVE must never silently fall back to MOCK" is already satisfied.

---

## 3. FIELD MAP — ONLY FIELDS THAT EXIST

Firmware payload (`sketch_aug26a.ino:1603-1676`) against `HardwareTelemetryPayload`
(`main.py:78-98`). The payload uses the `accel_*` / `gyro_*` aliases; the backend resolves
them via `effective_ax` etc. **The two contracts match — no mismatch.**

| HMI field | Backend field | Producer | Source | Unit | Provenance | Freshness | Status |
|---|---|---|---|---|---|---|---|
| Vehicle ID | `vehicle_id` | firmware | `"TRUCK_01"` literal | — | CONFIGURED | n/a | **AVAILABLE** |
| Sequence | `sequence` | firmware | monotonic counter | int | DERIVED | n/a | **AVAILABLE** |
| Wheel RPM | `rpm` | LM393 + ISR | measured | rev/min | **PHYSICAL** | CURRENT/STALE | **AVAILABLE** |
| Actual speed | `speed` | RPM × π × D / 60 | firmware | m/s | **PHYSICAL (derived)** | CURRENT/STALE | **AVAILABLE** |
| Accel X/Y/Z | `accel_x/y/z` | MPU6050 | measured (raw LSB) | LSB → SI | **PHYSICAL** | CURRENT/STALE | **AVAILABLE** |
| Gyro X/Y/Z | `gyro_x/y/z` | MPU6050 | measured (raw LSB) | LSB → SI | **PHYSICAL** | CURRENT/STALE | **AVAILABLE** |
| Wi-Fi RSSI | `rssi` | `WiFi.RSSI()` | measured | dBm | **PHYSICAL** | CURRENT | **AVAILABLE** |
| SNR | `snr` | LoRa if valid, else `9.5` | mixed | dB | **DERIVED / CONFIGURED** | — | **AVAILABLE, but see §5** |
| Telemetry path | `source` | firmware | `DIRECT_WIFI` | — | CONFIGURED | n/a | **AVAILABLE** |
| Comm state | derived | backend | link health | — | DERIVED | — | **AVAILABLE** |

### Fields the specification asks for that HAVE NO PRODUCER

| HMI field | Why unavailable |
|---|---|
| position, heading | In `NEVER_FROM_HARDWARE` (`telemetry_ingest.py:83`). **No GNSS on this vehicle.** |
| GNSS | **No receiver exists.** |
| visibility, fog state, road condition | **No sensor exists.** `/api/twin/snapshot` returns `environment: {}` |
| v_safe, H_safe, gap, stopping margin, risk, active constraint | No safety solver runs in the HMI backend process |
| BottleneckScore, queue, arrival/service rate, capacity, utilization | Contract exists; **MOCK/REPLAY producers only** |
| Orchestrator HOLD/RELEASE/REROUTE | Contract exists; **MOCK/REPLAY producers only** |
| V2V/V2I latency, packet loss | Contract exists; **MOCK/REPLAY producers only** |
| `HARDWARE_RECEIVED`, `EXECUTION_CONFIRMED`, `PHYSICAL_STATE_CONFIRMED` | Backend command lifecycle has `ACCEPTED / SENT / ACKNOWLEDGED / EXECUTED / REJECTED / TIMEOUT` only |

All of these must render **UNAVAILABLE with the reason**, never a number.

---

## 4. VEHICLE B IS NOT ON THIS PATH

The pull upgraded **Vehicle A only**. `TRUCK_02`'s speed remains PWM-derived
(`PWM_DERIVED_SPEED_VEHICLES = {"TRUCK_02"}`, `telemetry_ingest.py:80`) and **must not be
presented as encoder-measured**. The existing truth table already enforces this.

---

## 5. HONESTY DEFECT IN THE PULLED FIRMWARE — SNR

`sketch_aug26a.ino:1692`:

```cpp
json += "\"snr\":";
json += String(remoteDataValid ? remoteSNR : 9.5f, 2);
```

When no valid LoRa packet has been received, the firmware transmits a **hard-coded
`9.5` dB** as if measured. The backend's default is also `9.5`, so the two are
indistinguishable downstream.

This is a fabricated measurement on a direct-Wi-Fi frame, where LoRa SNR is not meaningful.
**The HMI must not present SNR as physical for `source=DIRECT_WIFI`.** Recommended fix is
in the firmware (omit the field when invalid); the smallest frontend-side mitigation is to
render SNR as UNAVAILABLE when the path is `DIRECT_WIFI`. Flagged, not silently worked
around.

---

## 6. WHAT CAN BE HONESTLY CLAIMED

**Physically measured and displayable today:** wheel RPM, a speed derived from it,
MPU6050 accel and gyro, Wi-Fi RSSI — for `TRUCK_01` only, when the ESP32 is powered and on
the network.

**Cannot be claimed:** GNSS/position/heading, visibility or fog sensing, friction,
`TRUCK_02` encoder speed, safety-solver output in LIVE, orchestrator decisions in LIVE,
V2V link metrics in LIVE, and any command state beyond `ACKNOWLEDGED`.
