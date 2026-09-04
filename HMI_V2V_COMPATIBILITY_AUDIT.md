# FOG-ORCHESTRATOR 2.0 — HMI V2V TELEMETRY COMPATIBILITY AUDIT

**Date**: 2026-08-29  
**Author**: Industrial HMI Validation Engineer, Backend Engineer, Verification & Validation Lead  
**Scope**: Software-Only HMI Audit for V2V Telemetry Packet Ingestion (`STATE,TRUCK_01,...` & `STATE,TRUCK_02,...`)

---

## 1. Existing HMI Architecture Overview

```text
       V2V / HARDWARE / MOCK EMULATOR STREAM
                         │
                         ▼
        ┌──────────────────────────────────┐
        │ V2V TELEMETRY INGESTION ADAPTER │
        │ (v2v_packet_parser.py)          │
        └────────────────┬─────────────────┘
                         │
                         │ Canonical Telemetry Payload
                         ▼
        ┌──────────────────────────────────┐
        │ HMI BACKEND TELEMETRY STORE      │
        │ (vehicle_telemetry_store)        │
        └────────────────┬─────────────────┘
                         │
                         ├─────────────────┐
                         ▼                 ▼
                  REST /api/vehicles    WebSocket /api/ws
                         │                 │
                         └────────┬────────┘
                                  ▼
                         HMI FRONTEND (React)
```

### Component Details:
1. **Backend**: FastAPI app (`SYNQRA_SIH2026-27-HMI/backend/app/main.py`).
2. **Frontend**: React 19 + Vite 7 TypeScript application (`SYNQRA_SIH2026-27-HMI/frontend`).
3. **Communication Endpoints**: REST `/api/health`, `/api/vehicles`, `/api/commands`, `/api/telemetry`, `/api/mode`, and WebSocket `/api/ws`.
4. **Data Store**: In-memory dictionary `vehicle_telemetry_store` in HMI backend.
5. **Supported Modes**: `MODE=MOCK`, `MODE=HARDWARE_SIM`, `MODE=HARDWARE`.

---

## 2. Frozen V2V Telemetry Packet Specification

V2V Radio Protocol Packet Format:
```text
STATE,<VEHICLE_ID>,<SEQ>,<RPM>,<SPEED>,<AX>,<AY>,<AZ>,<GX>,<GY>,<GZ>
```

### Example Packets:
- **Vehicle A (`TRUCK_01` — PULSES_PER_REV = 42)**:
  `STATE,TRUCK_01,28,240.00,0.00,-496,132,16696,703,342,191`
- **Vehicle B (`TRUCK_02` — PULSES_PER_REV = 43)**:
  `STATE,TRUCK_02,30,0.00,0.00,1096,3968,15932,-584,183,-59`

---

## 3. Field-by-Field Compatibility Matrix

| V2V Packet Field | V2V Data Type | HMI Store Target | HMI Data Type | Unit / Scale | Compatibility Status | Action Required |
|------------------|---------------|------------------|---------------|--------------|----------------------|-----------------|
| `MESSAGE_TYPE` | String (`STATE`) | `type` | String | - | **COMPATIBLE** | Validate `STATE` type string |
| `VEHICLE_ID` | String (`TRUCK_01` / `TRUCK_02`) | `vehicle_id` | String | - | **COMPATIBLE** | Direct mapping to vehicle store |
| `SEQ` | Integer | `sequence_number` | Integer | count | **COMPATIBLE** | Sequence continuity tracking |
| `RPM` | Float | `rpm` | Float | rpm | **COMPATIBLE** | Direct measured telemetry mapping |
| `SPEED` | Float | `speed_value` | Float / null | uncalibrated | **UNCALIBRATED** | Set `speed_calibrated: false` |
| `AX` | Int (Raw LSB) | `acceleration.x` | Float | $m/s^2$ | **COMPATIBLE** | Normalize LSB $\rightarrow \text{m/s}^2$ ($AX/16384 \cdot 9.81$) |
| `AY` | Int (Raw LSB) | `acceleration.y` | Float | $m/s^2$ | **COMPATIBLE** | Normalize LSB $\rightarrow \text{m/s}^2$ ($AY/16384 \cdot 9.81$) |
| `AZ` | Int (Raw LSB) | `acceleration.z` | Float | $m/s^2$ | **COMPATIBLE** | Normalize LSB $\rightarrow \text{m/s}^2$ ($AZ/16384 \cdot 9.81$) |
| `GX` | Int (Raw LSB) | `gyroscope.x` | Float | $rad/s$ | **COMPATIBLE** | Normalize LSB $\rightarrow \text{rad/s}$ ($GX/131 \cdot \pi/180$) |
| `GY` | Int (Raw LSB) | `gyroscope.y` | Float | $rad/s$ | **COMPATIBLE** | Normalize LSB $\rightarrow \text{rad/s}$ ($GY/131 \cdot \pi/180$) |
| `GZ` | Int (Raw LSB) | `gyroscope.z` | Float | $rad/s$ | **COMPATIBLE** | Normalize LSB $\rightarrow \text{rad/s}$ ($GZ/131 \cdot \pi/180$) |
| `RSSI` | Int (Gateway metadata) | `communication.rssi` | Int | dBm | **COMPATIBLE** | Map to communication metadata |
| `SNR` | Float (Gateway metadata) | `communication.snr` | Float | dB | **COMPATIBLE** | Map to communication metadata |

---

## 4. Potential Regression Risks & Isolation Controls

1. **Backend Crash on Malformed V2V Packet**: Solved by non-crashing parser (`v2v_packet_parser.py`) with fail-safe error logging.
2. **Vehicle Identity Cross-Contamination**: Solved by strict vehicle store isolation between `TRUCK_01` and `TRUCK_02`.
3. **Mock Mode Disturbance**: Solved by preserving mode toggle (`MODE=MOCK`, `MODE=HARDWARE_SIM`, `MODE=HARDWARE`).
4. **Digital Twin Dependency**: Solved by 100% boundary isolation. Zero Digital Twin files touched.
