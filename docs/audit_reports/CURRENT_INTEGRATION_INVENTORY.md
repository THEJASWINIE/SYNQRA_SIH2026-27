# CURRENT_INTEGRATION_INVENTORY.md
## FOG-ORCHESTRATOR 2.0 — Current Repository & Integration Inventory
**Date / Timestamp:** 2026-09-27T13:01:00+05:30  
**Evaluator:** Principal Software Architect & Lead Embedded Engineer  
**Absolute Principle:** NO ASSUMPTIONS — CODEBASE TRUTH FIRST  

---

### 1. VEHICLE A FIRMWARE INVENTORY

- **Source File:** [`esp32_code/sketch_aug26a/sketch_aug26a.ino`](file:///c:/Users/JAGADEESH%20M/OneDrive/Documents/SIH-2026-27/esp32_code/sketch_aug26a/sketch_aug26a.ino)
- **Role & Vehicle Identity:** Vehicle A / `TRUCK_01` (Peer transmitter/receiver with TRUCK_02; Direct Wi-Fi + LoRa node)
- **MCU & Hardware Platform:** ESP32-WROOM-32 (CH9102 / CP2102, USB `COM14`)
- **Motor Driver:** L298N Dual H-Bridge
  - Left Pins: `LEFT_IN1` (25), `LEFT_IN2` (26), `LEFT_PWM` (27)
  - Right Pins: `RIGHT_IN1` (32), `RIGHT_IN2` (33), `RIGHT_PWM` (14)
  - Standby Pin: `MOTOR_STBY` (13) held HIGH in run, LOW on stop
  - Speed-to-PWM: Linear mapping up to `MAX_MOTOR_PWM = 220` (max prototype speed 1.40 m/s)
- **Wheel & Encoder Specifications:**
  - Speed Sensor Pin: GPIO 35 (`SPEED_SENSOR_PIN`)
  - Interrupt Mode: `RISING` edge on optocoupler disc
  - Physical Slotted Disc: **42 slots** (`RAW_ENCODER_PPR 42.0f`)
  - Empirical Calibration Factor: **$K_{\text{cal}} = 34.58\text{ pulses/rev}$** (`ENCODER_EFFECTIVE_PPR 34.58f`)
  - Wheel Diameter: $D = 0.060\text{ m}$ (Circumference: $C = \pi \times 0.060 = 0.188495\text{ m}$)
  - Calculation: $\text{Speed (m/s)} = (\text{RPM} \times C) / 60.0$
- **Wi-Fi & Ingestion Logic:**
  - Network: Hotspot via [`secrets.h`](file:///c:/Users/JAGADEESH%20M/OneDrive/Documents/SIH-2026-27/esp32_code/sketch_aug26a/secrets.h) (`WIFI_SSID`, `WIFI_PASSWORD`)
  - Target URL: `POST http://192.168.137.1:8000/api/hardware/telemetry`
  - Transmission Interval: 2000 ms (`HMI_INTERVAL`)
  - Timeout: Strict 1000 ms HTTP timeout to prevent motor loop stall
  - Payload Format: JSON carrying `vehicle_id`, `boot_id`, `sequence`, `rpm`, `speed`, `accel_x/y/z`, `gyro_x/y/z`, `rssi`, `snr`, `source` (`DIRECT_WIFI`)
- **Session & Sequence Management:**
  - NVS Flash Persistent Boot ID: `Preferences.h` (`synqra` namespace) increments `bootId` on each boot cycle
  - Monotonic Sequence: Unified `globalSequence` counter shared across LoRa and Wi-Fi transmissions
- **LoRa & V2V Configuration:**
  - Transceiver: Semtech SX1278 (433.0 MHz, SF7, BW 125 kHz, CR 4/5, CRC Enabled)
  - SPI Pins: SCK (18), MISO (19), MOSI (23), SS (5), RST (4), DIO0 (34)
  - Transmission Slot: `V2V_START_DELAY = 500 ms` in 2000 ms cycle
  - Wire Format: `STATE,TRUCK_01,seq,rpm,speed,ax,ay,az,gx,gy,gz` (11 fields, Rule 2 preserved)
- **Safety & Failsafe Logic:**
  - Tier-1 Local Safe State: `stopVehicle()` immediately zeroes PWM and resets direction pins
  - Production Safe Beacon: When `wifiState == COMM_DISCONNECTED`, emits `BEACON,TRUCK_01,<seq>,DEGRADED,<millis>,PIT_ZONE_A` on 433 MHz LoRa at 1.0 Hz
  - Serial Diagnostic Commands: `WIFI_DROP`, `WIFI_RECONNECT`, `REBOOT`, `DRIVE <pwm> <duration>`

---

### 2. VEHICLE B FIRMWARE INVENTORY

- **Source File:** [`esp32_code/VEHICLE_B_TRUCK_02_V2V_DIGITAL_TWIN_MOTOR/VEHICLE_B_TRUCK_02_V2V_DIGITAL_TWIN_MOTOR.ino`](file:///c:/Users/JAGADEESH%20M/OneDrive/Documents/SIH-2026-27/esp32_code/VEHICLE_B_TRUCK_02_V2V_DIGITAL_TWIN_MOTOR/VEHICLE_B_TRUCK_02_V2V_DIGITAL_TWIN_MOTOR.ino)
- **Role & Vehicle Identity:** Vehicle B / `TRUCK_02`
- **MCU & Hardware Platform:** ESP32-WROOM-32 (Untethered on Wi-Fi battery power, IP `192.168.137.217`)
- **Motor Driver: TB6612FNG** (CRITICAL HARDWARE DIFFERENCE FROM VEHICLE A)
  - Left Motor: `LEFT_IN1` (25), `LEFT_IN2` (26), `LEFT_PWM` (27)
  - Right Motor: `RIGHT_IN1` (32), `RIGHT_IN2` (33), `RIGHT_PWM` (14)
  - Standby Pin: `MOTOR_STBY` (13)
  - PWM Engine: ESP32 Arduino Core 3.x LEDC API (`ledcWrite(LEFT_PWM, pwm)`)
- **Wheel & Encoder Specifications:**
  - Speed Sensor Pin: GPIO 35 (`SPEED_SENSOR_PIN`)
  - Interrupt Mode: `RISING` edge
  - Physical Slotted Disc: **43 slots** (`RAW_ENCODER_PPR 43.0f`)
  - Empirical Calibration Factor: **$K_{\text{cal}} = 34.58\text{ pulses/rev}$** (`ENCODER_EFFECTIVE_PPR 34.58f`)
  - Wheel Diameter: $D = 0.060\text{ m}$
- **Startup Safety State:**
  - `CONTINUOUS_FORWARD_TEST false` (Verified)
  - At boot: `commandedSpeedMs = 0.0f; targetMotorPWM = 0; appliedMotorPWM = 0; stopVehicle();`
  - `digitalWrite(MOTOR_STBY, LOW);` (H-Bridge in high-impedance shutdown)
- **LoRa & V2V Configuration:**
  - Semtech SX1278 (433.0 MHz, identical pins to Vehicle A)
  - Transmission Slot: `V2V_START_DELAY = 1000 ms` in 2000 ms cycle (TDM collision avoidance)
  - Wire Format: `STATE,TRUCK_02,seq,rpm,speed,ax,ay,az,gx,gy,gz` (11 fields)
- **Gaps Requiring Alignment with Vehicle A:**
  1. Lacks NVS `Preferences.h` persistent `boot_id`
  2. Separate `txSequence` and `telemetrySequence` require unification into `globalSequence`
  3. Lacks `sendSafeBeacon()` production generator for Wi-Fi loss emergency broadcast
  4. `#define ENABLE_DIRECT_WIFI_TELEMETRY false` needs parity enable and schema alignment

---

### 3. BACKEND SERVICES & APIS INVENTORY

- **Entry Point:** [`SYNQRA_SIH2026-27-HMI/backend/app/main.py`](file:///c:/Users/JAGADEESH%20M/OneDrive/Documents/SIH-2026-27/SYNQRA_SIH2026-27-HMI/backend/app/main.py)
- **Runtime:** FastAPI on Uvicorn (`0.0.0.0:8000`)
- **Telemetry Ingestion Endpoints:**
  - `POST /api/hardware/telemetry`: Canonical hardware ingress. Enforces Pydantic `HardwareTelemetryPayload`, bounded request size, speed/timestamp validation, deduplication (`_BoundedDedupStore`), session tracking (`last_boot_by_vehicle`), reboot re-anchoring, and source tracking (`DIRECT_WIFI`, `LORA_GATEWAY`).
  - `POST /api/hardware/beacon`: Canonical Safe Beacon ingress from LoRa Gateway. Enforces `SafeBeaconPayload`, replay rejection (`REJECTED_DUPLICATE_BEACON`), state latching (`safe_beacon_active = True`), and WebSocket broadcasting.
  - `POST /api/telemetry`: Simulated/mock telemetry ingress (strictly stamped as `SIMULATED`).
- **Core Architecture & Single Authoritative Digital Twin:**
  - State Store: [`fog_safe/digital_twin/state_store.py`](file:///c:/Users/JAGADEESH%20M/OneDrive/Documents/SIH-2026-27/fog_safe/digital_twin/state_store.py) (Authoritative in-memory state repository)
  - Ingestion Engine: [`telemetry_ingest.py`](file:///c:/Users/JAGADEESH%20M/OneDrive/Documents/SIH-2026-27/telemetry_ingest.py) (`CanonicalTelemetryIngestor` validating types, ranges, sequences, and stale data)
  - Twin Projection: [`twin_projection.py`](file:///c:/Users/JAGADEESH%20M/OneDrive/Documents/SIH-2026-27/twin_projection.py) (`build_vehicle_projection`)
  - Safety & Physics Solver: [`fog_safe/physics/`](file:///c:/Users/JAGADEESH%20M/OneDrive/Documents/SIH-2026-27/fog_safe/physics/) (Braking distance, retarder, traction, curve limits)
  - Command Gateway: [`command_gateway.py`](file:///c:/Users/JAGADEESH%20M/OneDrive/Documents/SIH-2026-27/command_gateway.py) (Command validation, token auth, timeout fallback, operator registry)
- **Supervisory & Context APIs:**
  - `GET /api/vehicles`: Authoritative vehicle list with staleness, communication status, safe beacon status, and Twin projections
  - `GET /api/mode`: Operational mode reporting (`LIVE` vs `MOCK`) based strictly on physical packet arrival within `HARDWARE_PRESENCE_TIMEOUT_S = 10.0s`
  - `GET /api/observability`: Telemetry ingest counters, gateway stats, WebSocket client count
  - `GET /api/operator/context`: Authenticated operator session and active vehicle assignment
  - `GET /api/fleet/summary`: Fleet-level count, health, and aggregate status
- **Real-Time Data Flow:**
  - WebSocket: `/ws` broadcasting `twin_vehicle_update`, `telemetry_update`, `SAFE_BEACON_ALERT`, and `command_event`

---

### 4. FRONTEND HMI ARCHITECTURE INVENTORY

- **Frontend Tech Stack:** React 18, TypeScript, Vite 7.3.6, Vanilla CSS (Design token system in `index.css`)
- **Multi-Entry HTML Endpoints:**
  1. [`index.html`](file:///c:/Users/JAGADEESH%20M/OneDrive/Documents/SIH-2026-27/SYNQRA_SIH2026-27-HMI/frontend/index.html) $\to$ [`src/main.tsx`](file:///c:/Users/JAGADEESH%20M/OneDrive/Documents/SIH-2026-27/SYNQRA_SIH2026-27-HMI/frontend/src/main.tsx): Control Room HMI & Supervisory Dashboard
  2. [`truck01.html`](file:///c:/Users/JAGADEESH%20M/OneDrive/Documents/SIH-2026-27/SYNQRA_SIH2026-27-HMI/frontend/truck01.html) $\to$ [`src/truck01.tsx`](file:///c:/Users/JAGADEESH%20M/OneDrive/Documents/SIH-2026-27/SYNQRA_SIH2026-27-HMI/frontend/src/truck01.tsx): Dedicated Vehicle A Operator HMI
  3. [`truck02.html`](file:///c:/Users/JAGADEESH%20M/OneDrive/Documents/SIH-2026-27/SYNQRA_SIH2026-27-HMI/frontend/truck02.html) $\to$ [`src/truck02.tsx`](file:///c:/Users/JAGADEESH%20M/OneDrive/Documents/SIH-2026-27/SYNQRA_SIH2026-27-HMI/frontend/src/truck02.tsx): Dedicated Vehicle B Operator HMI
  4. [`mine-cast.html`](file:///c:/Users/JAGADEESH%20M/OneDrive/Documents/SIH-2026-27/SYNQRA_SIH2026-27-HMI/frontend/mine-cast.html) $\to$ [`src/minecast.tsx`](file:///c:/Users/JAGADEESH%20M/OneDrive/Documents/SIH-2026-27/SYNQRA_SIH2026-27-HMI/frontend/src/minecast.tsx): Broad-scale mine situation broadcast
- **Operator HMI Components ([`src/vehicle/`](file:///c:/Users/JAGADEESH%20M/OneDrive/Documents/SIH-2026-27/SYNQRA_SIH2026-27-HMI/frontend/src/vehicle/)):**
  - [`VehicleHmiApp.tsx`](file:///c:/Users/JAGADEESH%20M/OneDrive/Documents/SIH-2026-27/SYNQRA_SIH2026-27-HMI/frontend/src/vehicle/VehicleHmiApp.tsx): Operator App Container, WebSocket subscriber, and vehicle state context
  - [`DriverScreen.tsx`](file:///c:/Users/JAGADEESH%20M/OneDrive/Documents/SIH-2026-27/SYNQRA_SIH2026-27-HMI/frontend/src/vehicle/DriverScreen.tsx): Primary vehicle-centric display (Speedometer, Safe Speed governor, Instruction banner, Warning matrix)
  - [`panels.tsx`](file:///c:/Users/JAGADEESH%20M/OneDrive/Documents/SIH-2026-27/SYNQRA_SIH2026-27-HMI/frontend/src/vehicle/panels.tsx): Diagnostics, IMU, V2V/LoRa link quality, and speed command panels
- **Control Room Components ([`src/screens/`](file:///c:/Users/JAGADEESH%20M/OneDrive/Documents/SIH-2026-27/SYNQRA_SIH2026-27-HMI/frontend/src/screens/)):**
  - [`OperationsOverview.tsx`](file:///c:/Users/JAGADEESH%20M/OneDrive/Documents/SIH-2026-27/SYNQRA_SIH2026-27-HMI/frontend/src/screens/OperationsOverview.tsx): Fleet status grid, vehicle cards, quick alerts
  - [`DigitalTwin.tsx`](file:///c:/Users/JAGADEESH%20M/OneDrive/Documents/SIH-2026-27/SYNQRA_SIH2026-27-HMI/frontend/src/screens/DigitalTwin.tsx): 2D/3D mine site representation, vehicle positions, haul road segments
  - [`SafetyEnvironment.tsx`](file:///c:/Users/JAGADEESH%20M/OneDrive/Documents/SIH-2026-27/SYNQRA_SIH2026-27-HMI/frontend/src/screens/SafetyEnvironment.tsx): Visibility conditions, fog boundary tracking, risk indicators
  - [`Diagnostics.tsx`](file:///c:/Users/JAGADEESH%20M/OneDrive/Documents/SIH-2026-27/SYNQRA_SIH2026-27-HMI/frontend/src/screens/Diagnostics.tsx): Ingestion latency, packet rates, WebSocket health, sensor health
  - [`AlertList.tsx`](file:///c:/Users/JAGADEESH%20M/OneDrive/Documents/SIH-2026-27/SYNQRA_SIH2026-27-HMI/frontend/src/screens/AlertList.tsx): Prioritized event list (COMM_LOSS, SAFE_BEACON, SENSOR_FAULT)
