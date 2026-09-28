# 09_HMI_AUDIT.md
## FOG-ORCHESTRATOR 2.0 — Operator & Control Room HMI Audit
**Date / Timestamp:** 2026-09-27T09:44:30+05:30  
**Evaluator Role:** Backend Integration Engineer, Frontend Systems Architect  
**Absolute Principle:** NO FABRICATION — Live UI Inspection & Invariant Enforcement

---

### 1. HMI SUBSYSTEM OVERVIEW

The HMI suite is built with Vite, TypeScript, and React/Tailwind/Vanilla CSS, hosted at port `5173`:

| Interface | URL Path | Intended Audience | Core Informational Display |
| :--- | :--- | :--- | :--- |
| **Control Room Dashboard** | `http://localhost:5173/index.html` | Mine Dispatchers & Safety Supervisors | Fleet map, vehicle cards, system health, safe vs commanded speeds, bottleneck warnings. |
| **TRUCK_01 Operator HMI** | `http://localhost:5173/truck01.html` | Vehicle Operator (In-Cab Display) | Current Speed, Safe Speed, Commanded Speed, Visibility ($m$), Operational Advice (`NORMAL`, `CAUTION`, `SLOW DOWN`, `STOP`), Safe Beacon Indicator. |
| **TRUCK_02 Operator HMI** | `http://localhost:5173/truck02.html` | Vehicle Operator (In-Cab Display) | Dedicated in-cab view for Vehicle B. |
| **MineCast 3D Digital Twin** | `http://localhost:5173/mine-cast.html` | Control Room / Spatial Monitoring | Full 3D spatial terrain, hauler mesh rendering, fog volumetric bounds. |

---

### 2. INVARIANT AUDIT: NON-INVENTION OF VEHICLE STATE (RULE 6)

$$\text{Rule 6: Frontend must NOT independently calculate or invent authoritative vehicle state.}$$

An audit of the frontend TypeScript source code (`SYNQRA_SIH2026-27-HMI/frontend/src/`):
- **Speed & Pose:** Derived strictly from the WebSocket stream payload (`/api/ws`) and `/api/vehicles`. No client-side kinematics or synthetic odometry calculation exists in the UI.
- **Safety Mode:** Consumed directly from `vehicle.safety_state` and `vehicle.data_quality`.
- **Visibility:** Consumed from `vehicle.visibility_m` or backend environment model.
- **Result:** **PASS (STRICT COMPLIANCE)**. The frontend functions exclusively as a reactive projection client.

---

### 3. LIVE HMI TEST RESULTS & OBSERVATIONS

| Feature / Scenario | Test Procedure | Observed UI Behavior | Status | Severity |
| :--- | :--- | :--- | :--- | :--- |
| **WebSocket Connectivity** | Connect client to `/api/ws` | Connection accepted. Server emits state packets at 10 Hz. | **PASS** | None |
| **Vehicle Telemetry Rendering** | Stream TRUCK_01 frames | Displays TRUCK_01, speed = 0.0 m/s, raw IMU values, RSSI = -44 dBm. | **PASS** | None |
| **Freshness & Stale Detection** | Cease packet arrival (>3.0s) | Banner turns Yellow: `COMMUNICATION DEGRADED`, badge changes to `STALE`. | **PASS** | None |
| **Offline Safe Stop Indication** | Cease packet arrival (>10.0s) | Banner turns Red: `VEHICLE OFFLINE / SAFE STOP ENFORCED`. | **PASS** | None |
| **Page Refresh Resilience** | F5 Refresh during live session | Reconnects WebSocket within 450 ms. Re-fetches initial snapshot. | **PASS** | None |
| **MineCast 3D Map Rendering** | Load `/mine-cast.html` | Three.js canvas initializes cleanly. Shaders and terrain render without WebGL errors. | **PASS** | None |
| **Operator Context Session Handshake** | Mount `/truck01.html` | Fails with `GET /api/operator/context 401 Unauthorized`. | **FAIL** | **P2** |

---

### 4. ROOT CAUSE OF 401 UNAUTHORIZED IN OPERATOR HMI

- **File:** `SYNQRA_SIH2026-27-HMI/frontend/src/hooks/useVehicleStore.ts`
- **Symptom:** Constant repeating `401 Unauthorized` requests logged in backend.
- **Root Cause:** The frontend requests operator context before establishing a session. The backend endpoint `/api/operator/context` requires an `Authorization: Bearer <session_token>` header, but the frontend on cold load had no token in `localStorage`.
- **Fix:** Add automatic anonymous session creation (`POST /api/operator/session`) on page load if no valid token exists.
