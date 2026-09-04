# FOG-ORCHESTRATOR 2.0 — HMI BACKEND NETWORK BINDING CONFIGURATION

**Date**: 2026-08-29  
**Author**: Principal Systems Architect, Network & Integration Engineer  
**Scope**: Server Host Binding Configuration (`0.0.0.0:8000`) for Physical ESP32 Wi-Fi Telemetry Ingestion

---

## 1. Network Binding Summary

| Configuration Parameter | Previous Setting | New Configured Setting | Status |
|-------------------------|------------------|------------------------|--------|
| **Server Host Binding** | `127.0.0.1` (Loopback only) | **`0.0.0.0`** (All Network Interfaces) | **CONFIGURED** |
| **Server Listening Port** | `8000` | **`8000`** | **ACTIVE** |
| **Laptop IPv4 Address** | `10.126.54.41` | **`10.126.54.41`** | **VERIFIED** |
| **HMI Base URL** | `http://127.0.0.1:8000` | **`http://10.126.54.41:8000`** | **VERIFIED** |
| **Telemetry Ingestion Endpoint** | `/api/hardware/telemetry` | **`http://10.126.54.41:8000/api/hardware/telemetry`** | **VERIFIED** |
| **WebSocket Streaming Endpoint** | `/api/ws` | **`ws://10.126.54.41:8000/api/ws`** | **VERIFIED** |
| **CORS Middleware Status** | Enabled (`allow_origins=["*"]`) | Enabled (`allow_origins=["*"]`) | **VERIFIED** |

---

## 2. Server Startup Command

To launch the HMI backend server reachable over local and mobile-hotspot Wi-Fi:

```bash
cd c:\Users\JAGADEESH M\OneDrive\Documents\SIH-2026-27\SYNQRA_SIH2026-27-HMI\backend
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

---

## 3. Network Access Verification Evidence

### 1. `netstat` Socket Listening Verification:
```text
TCP    0.0.0.0:8000           0.0.0.0:0              LISTENING       27888
```

### 2. Local Loopback API Health Check (`http://127.0.0.1:8000/api/health`):
```json
{
  "status": "ok",
  "service": "fog-orchestrator-hmi-backend",
  "version": "0.1.0",
  "milestone": "M1"
}
```

### 3. Network IPv4 API Health Check (`http://10.126.54.41:8000/api/health`):
```json
{
  "status": "ok",
  "service": "fog-orchestrator-hmi-backend",
  "version": "0.1.0",
  "milestone": "M1"
}
```

### 4. Hardware Telemetry POST Test (`http://10.126.54.41:8000/api/hardware/telemetry`):
```json
{
  "status": "ACCEPTED",
  "vehicle_id": "TRUCK_01",
  "sequence": 28,
  "source": "DIRECT_WIFI",
  "is_duplicate": false,
  "communication_status": "ONLINE"
}
```

---

## 4. Minimal Recommended Windows Firewall Rule

If Windows Firewall blocks inbound TCP connections on port 8000 over Private/Mobile Hotspot networks, run the following PowerShell command as Administrator:

```powershell
New-NetFirewallRule -DisplayName "FOG-Orchestrator HMI Backend Port 8000" -Direction Inbound -Protocol TCP -LocalPort 8000 -Action Allow -Profile Private,Public
```

---

## 5. Software vs Physical Verification Status

- **SOFTWARE VERIFIED**:
  - `0.0.0.0:8000` socket binding listening verified via `netstat`.
  - HTTP `GET /api/health` verified on `127.0.0.1:8000` and `10.126.54.41:8000`.
  - HTTP `POST /api/hardware/telemetry` verified on `10.126.54.41:8000`.
  - Master wireless runner `verify_wireless_hmi.py` passed (**100%**).
  - Master regression runner `verify_all_regressions.py` passed (**100%**).
  - Pytest test suite `python -m pytest` passed (**95/95 PASS**).
- **PHYSICALLY VERIFIED**:
  - Pending physical ESP32 Wi-Fi hardware connection test on physical hotspot network.
