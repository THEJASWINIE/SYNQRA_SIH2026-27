# 06_BACKEND_AUDIT.md
## FOG-ORCHESTRATOR 2.0 — Live Backend Startup & API Layer Audit
**Date / Timestamp:** 2026-09-27T09:40:00+05:30  
**Evaluator Role:** Backend Integration Engineer, Safety-Critical Systems Engineer  
**Absolute Principle:** NO FABRICATION — Verified Live Backend State & Forensic Logs

---

### 1. LIVE BACKEND PROCESS AUDIT

- **Process Command:** `python -m uvicorn app.main:app --host 0.0.0.0 --port 8000`
- **Host Binding:** `0.0.0.0:8000` (Listening on loopback `127.0.0.1`, Wi-Fi `192.168.0.111`, and Hotspot `192.168.137.1`).
- **Startup Log Artifact:** [`results/02_backend_startup.log`](file:///c:/Users/JAGADEESH%20M/OneDrive/Documents/SIH-2026-27/results/02_backend_startup.log)
- **Startup State:** `INFO: Started server process [19908]` -> `Application startup complete.` -> `Uvicorn running on http://0.0.0.0:8000`.

---

### 2. ENDPOINT & COMMUNICATION VERIFICATION

| Endpoint / Protocol | Request / Caller | HTTP Status | Backend Response / State | Finding / Status |
| :--- | :--- | :--- | :--- | :--- |
| `GET /api/health` | Gateway (`192.168.137.185`) & Localhost | `200 OK` | `{"status":"ok"}` | **PASS** — Gateway actively heartbeats every 2–5s. |
| `GET /api/observability` | Frontend & Localhost | `200 OK` | Live metrics, ingest count, twin attached, client count. | **PASS** — Twin attached, hardware seen = true. |
| `GET /api/vehicles` | Localhost curl | `200 OK` | Returns TRUCK_01 state dictionary with live IMU & odometry. | **PASS** — Correct schema, SI units enforced. |
| `GET /api/hardware/sequence` | Vehicle A (`192.168.137.43`) | `200 OK` | `{"next_sequence": 1}` | **PASS** — Boot sequence synchronization verified. |
| `POST /api/hardware/telemetry` | Vehicle A (`192.168.137.43`) | `200 OK` | Accepts live JSON telemetry frames from mobile chassis. | **PASS** — Telemetry ingested up to frame 15. |
| `WS /api/ws` | Frontend Clients (Control Room / Operator) | `Accepted` | WebSocket open, broadcasting state at 10 Hz. | **PASS** — Real-time updates delivered to UI stores. |
| `GET /api/operator/context` | Operator HMI (`/truck01.html`) | `401 Unauthorized` | Rejected: Missing session authentication token. | **FAIL (P2)** — Frontend lacks automatic token handshake on direct page load. |

---

### 3. LIVE ANOMALIES & FORENSIC BUGS DISCOVERED

#### [CRITICAL BUG BK-001] Odometry dt Gap Locking Bug in `wheel_imu_odometry.py`
- **Location:** `integration_adapters/wheel_imu_odometry.py:89-95`
- **Observed Log:**
  ```text
  Invalid dt=110.615 for odometry update on TRUCK_01
  Invalid dt=112.616 for odometry update on TRUCK_01
  Invalid dt=114.620 for odometry update on TRUCK_01
  Invalid dt=116.620 for odometry update on TRUCK_01
  Invalid dt=118.668 for odometry update on TRUCK_01
  ```
- **Code Analysis:**
  ```python
  dt = timestamp - self.last_timestamp
  if dt <= 0.0 or not math.isfinite(dt) or dt > 10.0:
      logger.warning("Invalid dt=%.3f for odometry update on %s", dt, self.vehicle_id)
      return self.snapshot(status="STALE" if dt > 10.0 else "INVALID")
  ```
- **Root Cause:** Notice that when `dt > 10.0` (which naturally occurs if a vehicle takes 15 seconds to boot or reconnects after a brief pause), the function logs the warning and returns **WITHOUT** updating `self.last_timestamp = timestamp`. Consequently, every subsequent incoming packet (even arriving 2.0 seconds later) computes `dt = current_timestamp - original_pre_disconnect_timestamp`, which continues to grow indefinitely ($110\text{s} \to 112\text{s} \to 114\text{s}$). The vehicle's odometry tracker is permanently locked into `STALE` status and never recovers.
- **Severity:** **P1** (Permanent Odometry Latch-up on Disconnect).
- **Required Fix:** In `wheel_imu_odometry.py`, update `self.last_timestamp = timestamp` and `self.last_pulse_count = curr_pulses` on stale gap handling so that the subsequent packet resumes normal differential integration.

#### [DEFECT BK-002] Operator HMI Unauthorized 401 Polling Loop
- **Location:** `SYNQRA_SIH2026-27-HMI/backend/app/routers/operator.py` & Frontend `useVehicleStore.ts`
- **Observed Log:** Frontend generates continuous `GET /api/operator/context HTTP/1.1 401 Unauthorized` requests at ~2 Hz.
- **Root Cause:** The Operator HMI frontend requests `/api/operator/context` on mount before acquiring or negotiating an active operator session token (`/api/operator/session`).
- **Severity:** **P2** (Spamming backend logs, Operator context unpopulated).

---

### 4. SUBSYSTEM INTEGRATION STATUS

1. **Safety Governor:** Active in backend memory. Enforces $v_{\text{command}} = \min(v_{\text{dispatch}}, v_{\text{safe}})$.
2. **Sensor Health:** Monitors MPU6050 and wheel encoder. Flags communication degraded when packet age exceeds 3.0s, offline when packet age exceeds 10.0s.
3. **Communication Health:** Tracked per vehicle (`source: DIRECT_WIFI`, `rssi: -44 dBm`, `snr: 10.0 dB`).
4. **Authoritative Twin Sync:** Twin state attached. Backend acts as authoritative ingestion boundary.
