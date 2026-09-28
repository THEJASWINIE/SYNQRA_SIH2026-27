# FOG-ORCHESTRATOR 2.0 — HMI INDEPENDENT RUN GUIDE (SYSTEM A)

This guide provides exact step-by-step commands to run and operate System A (HMI Supervisory Dashboard) in total isolation without Digital Twin or physical hardware dependencies.

---

## Architecture Overview

```
Browser
   │
   ▼
React Frontend (Port 5173 / Vite)
   │
   ▼
FastAPI Backend (Port 8000 / REST + WebSocket)
   │
   ▼
Mock Telemetry Generator (mock_vehicle_generator.py)
```

---

## Prerequisites

1. **Python 3.10+** with `fastapi`, `uvicorn`, `pydantic`, `websockets`, `requests` installed.
2. **Node.js v18+ & npm** installed.

---

## Step 1: Start HMI Backend Service

Open Terminal 1 and execute:

```powershell
cd "c:\Users\JAGADEESH M\OneDrive\Documents\SIH-2026-27\SYNQRA_SIH2026-27-HMI\backend"
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

Verification:
- Open browser or curl: `http://127.0.0.1:8000/api/health`
- Expected response: `{"status":"ok","service":"fog-orchestrator-hmi-backend",...}`

---

## Step 2: Start HMI Frontend Application

Open Terminal 2 and execute:

```powershell
cd "c:\Users\JAGADEESH M\OneDrive\Documents\SIH-2026-27\SYNQRA_SIH2026-27-HMI\frontend"
npm run dev
```

Verification:
- Open browser to `http://localhost:5173`
- The React Supervisory HMI Dashboard loads.

---

## Step 3: Run Mock Telemetry Generator (MOCK_MODE)

Open Terminal 3 and execute:

```powershell
cd "c:\Users\JAGADEESH M\OneDrive\Documents\SIH-2026-27"
python mock_vehicle_generator.py
```

The generator will stream simulated vehicle telemetry frames:
- **Vehicle A (`TRUCK_01`)**: Nominal operation with dynamic speed, RPM, and acceleration changes.
- **Vehicle B (`TRUCK_02`)**: Communication degradation and stale timestamp testing.

---

## Step 4: Execute Independent HMI Acceptance Test

To execute the automated 10-check verification suite for System A:

```powershell
cd "c:\Users\JAGADEESH M\OneDrive\Documents\SIH-2026-27"
python verify_hmi_independent.py
```

Expected Output:

```
==================================================
HMI INDEPENDENT VERIFICATION
==================================================
CHECK 1 ........ PASS
CHECK 2 ........ PASS
CHECK 3 ........ PASS
CHECK 4 ........ PASS
CHECK 5 ........ PASS
CHECK 6 ........ PASS
CHECK 7 ........ PASS
CHECK 8 ........ PASS
CHECK 9 ........ PASS
CHECK 10 ........ PASS

FINAL RESULT:

HMI INDEPENDENT SYSTEM: PASS
```
