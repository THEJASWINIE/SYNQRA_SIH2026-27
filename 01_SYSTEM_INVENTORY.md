# 01_SYSTEM_INVENTORY.md
## FOG-ORCHESTRATOR 2.0 — Comprehensive System & Hardware/Software Inventory
**Date / Timestamp:** 2026-09-27T09:38:00+05:30  
**Evaluator Role:** Senior Embedded Systems Engineer, Robotics Test Engineer, Backend Integration Engineer, RF Engineer, Safety-Critical Systems Engineer  
**Absolute Principle:** NO FABRICATION — Full Physical & Digital System Inventory

---

### 1. PHYSICAL HARDWARE ASSETS & INTERFACES

| Hardware Component | Detected Hardware / Chipset | Physical Port / Interface | Operating State / Physical Connectivity |
| :--- | :--- | :--- | :--- |
| **LoRa Gateway Node** | ESP32-WROOM-32 + SX1278 (433 MHz) | USB `COM11` (`Silicon Labs CP210x`, `USB\VID_10C4&PID_EA60\0001`) | **ONLINE & WI-FI CONNECTED** (`192.168.137.185` on `SYNQRA_HOST`), polling backend `/api/health` at HTTP 200 OK. Port locked by active Arduino IDE Serial Monitor (PID 34944). |
| **Vehicle A (TRUCK_01)** | ESP32-WROOM-32 + L298N H-Bridge + MPU6050 + Optical Wheel Encoder | Wi-Fi (`SYNQRA_HOST`, IP: `192.168.137.43`), LoRa 433 MHz | **ONLINE OVER WI-FI**, ping RTT 140–221 ms. Transmitted initial telemetry sequence frames 1–15 to backend `/api/hardware/telemetry`. Odometry backend updates stalled due to odometry gap rejection bug. |
| **Vehicle B (TRUCK_02)** | ESP32-WROOM-32 + TB6612FNG Dual Driver + MPU6050 + Optical Wheel Encoder | Wi-Fi (`SYNQRA_HOST`, IP: `192.168.137.126`), LoRa 433 MHz | **ONLINE OVER WI-FI**, ping RTT 80–94 ms. Configured with `ENABLE_DIRECT_WIFI_TELEMETRY = false`; serves as V2V peer and local HTTP WebServer on port 80. |
| **Bench Node (Aux/Flash)** | ESP32-WROOM-32E (CH9102 USB-to-UART) | USB `COM14` (`USB\VID_1A86&PID_55D4\5B53023552`) | **CONNECTED BUT CORRUPT FLASH BOOTLOOP**: Serial output logs: `E (338) esp_image: Image hash failed - image is corrupt / No bootable app partitions`. In continuous reset loop `rst:0x3 (SW_RESET)`. |
| **Bench Node (Aux 2)** | ESP32 (Silicon Labs CP210x) | USB `COM21` (`USB\VID_10C4&PID_EA60\5&274D72C6&0&6`) | **CONNECTED & BUSY**: Port open in Arduino IDE / locked (`PermissionError 13: Access is denied`). |
| **Host Workstation Network** | Wi-Fi Client + Local Mobile Hotspot | Wi-Fi (`192.168.0.111`), Hotspot (`Local Area Connection* 2`, `192.168.137.1`) | **ACTIVE**: Hotspot SSID `SYNQRA_HOST` provides the local 192.168.137.0/24 subnet for all ESP32 nodes and host services. |

---

### 2. FIRMWARE MANIFEST & SOURCE LOCATIONS

| Subsystem / Sketch | Path | MCU / Target | Key Parameters & Pinouts | Role |
| :--- | :--- | :--- | :--- | :--- |
| **Vehicle A Firmware** | `esp32_code/sketch_aug26a/sketch_aug26a.ino` | ESP32 (`esp32:esp32:esp32`) | $D=0.060\text{ m}$, $K=34.58\text{ PPR}$ (`ENCODER_EFFECTIVE_PPR`), Raw PPR 42.0. Pins: Left IN1: 25, IN2: 26, PWM: 27; Right IN1: 32, IN2: 33, PWM: 14; STBY: 13. Encoder: GPIO 35. IMU: SDA 21, SCL 22. LoRa: SCK 18, MISO 19, MOSI 23, SS 5, RST 4, DIO0 34 (433 MHz). | Bidirectional V2V + Direct Wi-Fi telemetry to backend `http://192.168.137.1:8000/api/hardware/telemetry`. |
| **Vehicle B Firmware** | `esp32_code/VEHICLE_B_TRUCK_02_V2V_DIGITAL_TWIN_MOTOR/VEHICLE_B_TRUCK_02_V2V_DIGITAL_TWIN_MOTOR.ino` | ESP32 (`esp32:esp32:esp32`) | $D=0.060\text{ m}$, $K=34.58\text{ PPR}$, Raw PPR 43.0. TB6612FNG pins: Left IN1: 25, IN2: 26, PWM: 27; Right IN1: 32, IN2: 33, PWM: 14; STBY: 13. Encoder: GPIO 35. LoRa 433 MHz. `WebServer commandServer(80)`. `ENABLE_DIRECT_WIFI_TELEMETRY = false`. | Local motor speed follower + V2V transmitter/receiver + Digital Twin HTTP command receiver. |
| **LoRa Gateway Receiver** | `esp32_code/LORA_GATEWAY_RECEIVER/LORA_GATEWAY_RECEIVER.ino` | ESP32 (`esp32:esp32:esp32`) | LoRa 433 MHz, CRC Enabled, RX Mode. Wi-Fi connects to `SYNQRA_HOST`. Forwards received V2V packets to `http://192.168.137.1:8000/api/hardware/telemetry`. | Hardware Gateway forwarding mobile RF packets to backend REST API. |
| **Calibration Sketches** | `esp32_code/VEHICLE_SPEED_CALIBRATION/VEHICLE A/...` and `VEHICLE B/...` | ESP32 | Raw PPR 42 (Vehicle A), Raw PPR 43 (Vehicle B). | Standalone tachometer & calibration measurement test harnesses. |
| **Frozen Backups** | `esp32_code/backup/VEHICLE_A_HMI_FIRMWARE_BACKUP_V2V_FROZEN.ino`, `..._VEHICLE_B_...` | ESP32 | Frozen baselines preserved for emergency regression fallback. | Historical reference firmware. |

---

### 3. LIVE SOFTWARE SERVICES & RUNTIME ARCHITECTURE

| Service | Runtime / Framework | Host / Port Binding | Active PID / Task ID | Endpoints & Assets |
| :--- | :--- | :--- | :--- | :--- |
| **HMI Backend** | Python 3.14 + FastAPI + Uvicorn | `0.0.0.0:8000` (Bound to `127.0.0.1`, `192.168.137.1`, `192.168.0.111`) | PID 19908 / Task-5016 | `/api/health`, `/api/observability`, `/api/vehicles`, `/api/hardware/telemetry`, `/api/hardware/sequence`, `/api/commands`, `/api/ws` (WebSocket live telemetry stream). |
| **HMI Frontend** | Node.js + TypeScript + Vite | `0.0.0.0:5173` | PID 27952 / Task-5018 | Control Room Dashboard (`/index.html`), TRUCK_01 Operator HMI (`/truck01.html`), TRUCK_02 Operator HMI (`/truck02.html`), MineCast 3D Canvas (`/mine-cast.html`). |
| **3D Digital Twin Engine** | Python 3.14 + FastAPI + Three.js Bridge | `0.0.0.0:8080` | PID 23832 / Task-5020 | Twin state engine, kinematic trajectory integration, spatial road model, `/dashboard`, `/docs`. |

---

### 4. CORE ENGINE MODULES & ADAPTERS

- **Telemetry Ingestion & Quality Filtering:** `telemetry_ingest.py`, `v2v_packet_parser.py`, `integration_adapters/wheel_imu_odometry.py`. Validates sequences, filters out-of-order frames, detects sensor staleness (>3.0s degraded, >10.0s offline).
- **Authoritative Safety Governor:** `fog_safe/governor.py`, `tests/test_safety_governor.py`. Computes deterministic stopping distance $S_{\text{stop}} = v \cdot \tau_{\text{total}} + \frac{v^2}{2 a_{\text{dec}}}$, sets safe speed clamping $v_{\text{command}} = \min(v_{\text{dispatch}}, v_{\text{safe}})$.
- **Command Gateway:** `command_gateway.py`. Enforces monotonic sequence numbers, stale command rejection, and Tier-1 safety limits before sending commands to vehicle actuators.
- **Digital Twin State Store:** `fog_orchestrator/state/twin_state.py`, `fog-orchester-3d-digital-twin/core/twin_engine.py`. Authoritative representation of mine topology, haul roads, vehicle poses, visibility envelope, and hazards.
- **CAN / TWAI Abstraction:** `fog_safe/can_interface.py`, `tests/test_phase8_hil.py`. ISO 11898-1 29-bit CAN frame abstraction, PGN/SPN parsing for J1939 emulation. (Note: physical OEM HEMM vehicle bus is EMULATED / UNTESTED on real mine vehicles).

---

### 5. DATABASE & PERSISTENCE
- **In-Memory Authoritative Stores:** FastAPI app state dictionaries, `TwinStateStore`, thread-safe sliding telemetry buffers.
- **File Artifacts & Traces:** CSV trace files in `results/`, JSON mission dumps in `results/fault_injection/`, configuration in `config/`.
