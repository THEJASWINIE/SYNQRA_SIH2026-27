# DEBUG_BASELINE.md
## FOG-ORCHESTRATOR 2.0 — Pre-Debug & Pre-Fix System Baseline
**Date / Timestamp:** 2026-09-27T09:56:00+05:30  
**Evaluator Role:** Lead Systems Debug Engineer, Safety Systems Engineer  
**Baseline State:** Frozen prior to applying fixes to P0, P1, and P2 defects.

---

### 1. REPOSITORY & RUNTIME STATE

- **Git Commit (HEAD):** `4a3aa4721912f04ecb34f31d8b718e6b352fecd4`
- **Git Branch:** `main`
- **Host Platform:** Windows 11, PowerShell, Python 3.14.0, Node.js v20.x, Arduino CLI v1.5.1
- **Active Hotspot Subnet:** `192.168.137.0/24` (SSID: `SYNQRA_HOST`, Host: `192.168.137.1`)

---

### 2. PRE-FIX ARTIFACT SHA256 HASHES

| Component / File Path | Pre-Fix SHA256 Hash | Defect Addressed |
| :--- | :--- | :--- |
| `esp32_code/VEHICLE_B_TRUCK_02_V2V_DIGITAL_TWIN_MOTOR/...ino` | `75f7f44b5cae82b6451c935c594c770c8052d3776ecb249d3325204c509e12e4` | **P-005 (P0):** `CONTINUOUS_FORWARD_TEST true` hardcoded |
| `esp32_code/sketch_aug26a/sketch_aug26a.ino` | `0303df0d22808496076a9c3d667ea66e82853abfd8a612d21c378d852978fda5` | Production Vehicle A firmware |
| `esp32_code/LORA_GATEWAY_RECEIVER/LORA_GATEWAY_RECEIVER.ino` | `7f506fa3ea9f604dd5813590d6fbd1365ca7cd150b5561db1e5f18deb317e7a8` | Gateway firmware on COM11 |
| `integration_adapters/wheel_imu_odometry.py` | `3132a4668bee9ddff47fb5ec751b3f45f658f63f0af858e3520ed737261a38d0` | **P-001 (P1):** Odometry $dt > 10.0\text{ s}$ gap latch bug |
| `SYNQRA_SIH2026-27-HMI/frontend/src/vehicle/VehicleHmiApp.tsx` | (Unmodified) | **P-002 (P2):** Operator HMI 401 polling flood |
| `esp32_code/VEHICLE_SPEED_CALIBRATION/VEHICLE A/...ino` | (Unmodified) | **P-004 (P2):** Omission of $K=34.58$ in calibration |
| `esp32_code/VEHICLE_SPEED_CALIBRATION/VEHICLE B/...ino` | (Unmodified) | **P-004 (P2):** Omission of $K=34.58$ in calibration |

---

### 3. LIVE PROCESS INVENTORY PRIOR TO FIXES

- **Backend Daemon:** PID 19908 / Task-5016 (`uvicorn app.main:app --port 8000`)
- **Frontend Dev Server:** PID 27952 / Task-5018 (`vite dev --port 5173`)
- **3D Digital Twin Engine:** PID 23832 / Task-5020 (`python main.py --serve-hmi --port 8080`)
- **Connected USB Bridges:**
  - COM11: Silicon Labs CP210x (LoRa Gateway)
  - COM14: CH9102 USB Bridge (Corrupted Bootloader)
  - COM21: CP210x USB Bridge (Locked by IDE)
