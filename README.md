# SYNQRA / FOG-ORCHESTRATOR 2.0
### Physics-Constrained Autonomous Fleet Safety, Multi-Tier HMI Suite & Authoritative 3D Digital Twin for Open-Cast Mine Haulage in Dense Fog

[![SIH 2026-27](https://img.shields.io/badge/SIH_2026--27-Problem_Statement_SIH26007-blue.svg?style=for-the-badge&logo=target)](https://sih.gov.in)
[![Safety Invariant](https://img.shields.io/badge/Safety_Tier--1-Sole_Local_Authority-red.svg?style=for-the-badge&logo=shield)](docs/FINAL_INTEGRATED_ARCHITECTURE.md)
[![Digital Twin](https://img.shields.io/badge/Digital_Twin-NMDC_Bailadila_Deposit_5-orange.svg?style=for-the-badge&logo=three.js)](fog-orchester-3d-digital-twin)
[![Frontend Tests](https://img.shields.io/badge/Vitest-1%2C860_PASS_|_0_FAIL-brightgreen.svg?style=for-the-badge&logo=vitest)](SYNQRA_SIH2026-27-HMI/frontend)
[![Backend Tests](https://img.shields.io/badge/Pytest-1%2C153_PASS_|_0_FAIL-brightgreen.svg?style=for-the-badge&logo=pytest)](SYNQRA_SIH2026-27-HMI/backend)
[![CAN / J1939](https://img.shields.io/badge/CAN_TWAI-250_kbps_SAE_J1939-blueviolet.svg?style=for-the-badge&logo=circuitverse)](integration_adapters/can_twai_hil.py)
[![RF Link](https://img.shields.io/badge/RF_Dual--Link-433_MHz_LoRa_+_Wi--Fi-critical.svg?style=for-the-badge&logo=espressif)](esp32_code)

---

## 1. Executive Summary & Problem Context

In heavy open-cast mining operations—such as **NMDC Limited's Bailadila Iron Ore Complex (Deposit 5, Kirandul, Bacheli, Donimalai)**—monsoon and winter weather triggers severe valley fog and cloud-inversion phenomena. Optical line-of-sight visibility frequently drops below **15 meters**, while wet clay and slurry degrade tire-road friction coefficients to **μ <= 0.35**.

A loaded **BEML BH100-class haul dumper** weighs **165.5 tonnes**. At standard haulage speeds (**30 to 40 km/h**), its emergency braking distance on an **8% to 12% downhill grade** exceeds **35 to 50 meters**—more than double the driver's sightline in dense fog. Consequently, mine operators face an unacceptable choice:
1. **Blind Operation**: Catastrophic collision risks (rear-end impacts, head-on switchback conflicts, bench berm overtopping).
2. **Total Fleet Shutdown**: Costing millions of INR per hour in lost mineral throughput.

**SYNQRA / FOG-ORCHESTRATOR 2.0** provides an end-to-end, multi-tier cyber-physical solution:
- **Authoritative 3D/2D Digital Twin**: Continuously mirrors real mine spatial topology, road grades, weather fields, and fleet dynamic states.
- **5-Constraint Physics Safety Governor**: Computes the highest physically defensible operating speed `v_safe` in real time.
- **Inviolable Onboard Safety Tier**: Guarantees that central dispatch proposals can never violate vehicle physics (`v_command = min(v_dispatch, v_safe)`).
- **Multi-Role Modern Web HMI Suite**: Dedicated Central Control Room Console, High-Contrast In-Cab Operator Displays (TRUCK_01, TRUCK_02), and MineCast Environmental Weather Station.
- **Industrial V2V & Hardware Ingestion**: ESP32 microcontrollers, MPU6050 IMU, optical wheel speed tachometer, 250 kbps TWAI/CAN (SAE J1939), 433 MHz LoRa + Wi-Fi failover, and autonomous Safe Beacon fallbacks.

---

## 2. Master System Architecture

```
                    ┌────────────────────────────────────────────────────────┐
                    │                   CENTRAL DISPATCH                     │
                    │      Receding-Horizon Chance-Constrained MPC (RH-MPC)  │
                    │      Queue Arrival Shaping & Dynamic Bottleneck Score  │
                    └──────────────────────────┬─────────────────────────────┘
                                               │ v_dispatch (Advisory Pacing)
                                               ▼
┌──────────────────────────────┐    ┌──────────────────────────┐    ┌──────────────────────────────┐
│       CONTROL ROOM HMI       │    │   CENTRAL ORCHESTRATOR   │    │      MINECAST STATION        │
│ • Real-Time Spatial Mine Map │◄───┤ • State Estimation       │───►│ • Optical Visibility Sensors │
│ • Fleet Telemetry & Alerts   │    │ • Corridor Occupancy     │    │ • Haul Road Fog Nowcasting   │
│ • Port 5173 (React 19 / R3F) │    │ • Fast 3D Twin (Port 8080)│   │ • Friction Priors (μ)        │
└──────────────────────────────┘    └────────────┬─────────────┘    └──────────────────────────────┘
                                                 │
                                                 ▼
                               ┌──────────────────────────────────┐
                               │       AUTHORITATIVE TWIN         │
                               │   State Mirroring & Prediction   │
                               │   Lookahead Horizon: T+3s..T+5s  │
                               └─────────────────┬────────────────┘
                                                 │
                        ┌────────────────────────┴────────────────────────┐
                        │ Telemetry Ingestion, Validation & Normalization │
                        │ (Checks: NaN, Inf, Stale, Out-of-Order, CRC)    │
                        └────────────────────────┬────────────────────────┘
                                                 │
                       ┌─────────────────────────┴─────────────────────────┐
                       │                                                   │
                       ▼                                                   ▼
        ┌─────────────────────────────┐                     ┌─────────────────────────────┐
        │   TRUCK_01 (PHYSICAL/WIFI)  │                     │    TRUCK_02 (PHYSICAL/LORA) │
        │ • Microcontroller Motor Rig │                     │ • Microcontroller Motor Rig │
        │ • MPU6050 6-DOF IMU         │                     │ • MPU6050 6-DOF IMU         │
        │ • Optical Wheel Tachometer  │                     │ • Optical Wheel Tachometer  │
        │ • CAN/TWAI 250kbps (J1939)  │                     │ • LoRa 433MHz Transceiver   │
        └──────────────┬──────────────┘                     └──────────────┬──────────────┘
                       │                                                   │
                       ▼                                                   ▼
        ┌─────────────────────────────┐                     ┌─────────────────────────────┐
        │    IN-CAB OPERATOR HMI      │                     │     IN-CAB OPERATOR HMI     │
        │ TRUCK_01 Cab Screen (Port   │                     │ TRUCK_02 Cab Screen (Port   │
        │ 3001 or /truck01.html)      │                     │ 3002 or /truck02.html)      │
        │ • Safe Speed Dial v_safe    │                     │ • Safe Speed Dial v_safe    │
        │ • Sightline & Grade HUD     │                     │ • Sightline & Grade HUD     │
        │ • 6-State Safety Status     │                     │ • 6-State Safety Status     │
        └─────────────────────────────┘                     └─────────────────────────────┘
```

---

## 3. Core Architectural Invariants

| ID | Architectural Invariant | Enforcement Mechanism |
| :---: | :--- | :--- |
| **I1** | **Sole Local Authority** | `v_command = min(v_dispatch, v_safe)`. Central dispatch can never command a speed exceeding the local vehicle safety governor. |
| **I2** | **Single Authoritative Twin** | All clients (Control Room, Driver HUD, Pygame, Analytics) are passive consumers of the backend Digital Twin. No frontend calculates authoritative position or speed. |
| **I3** | **No Telemetry Fabrication** | Explicit classification across all interfaces: `HARDWARE` (measured), `EMULATED` (loopback/synthetic), or `SIMULATION` (modeled). Zero fabricated hardware claims. |
| **I4** | **Decoupled Failsafe** | On RF loss exceeding 500 ms, vehicle autonomously drops to Safe Crawl Mode (2.22 m/s) and broadcasts 2 Hz 433 MHz Safe Beacons independently. |
| **I5** | **Ingestion Fault Isolation** | Telemetry ingestion rejects malformed, out-of-order, stale, or NaN/Inf packets without crashing backend services. |
| **I6** | **Strict SI Units** | Speeds in m/s, accelerations in m/s², distances in m, grades in %, angles in degrees/radians, timestamps in UTC / ISO 8601. |

### Master Authority Priority Hierarchy

```
Priority 1: EMERGENCY_PHYSICAL_SAFETY (Hardware E-Stop / Critical Brake Loss: 0.0 m/s halt)
    ▼
Priority 2: LOCAL_SAFETY_GOVERNOR (Onboard Kinematic & Retarder Envelope: Sole Actuation Authority)
    ▼
Priority 3: VALID_LOCAL_SENSOR_INFO (Validated Onboard Visibility, IMU, Wheel Odometry)
    ▼
Priority 4: COMMUNICATION_DERIVED_INFO (V2V Telemetry, Peer Distance, Gateway Updates)
    ▼
Priority 5: FLEET_OPTIMIZATION (Central Dispatch Pacing & Cycle Time Shaping)
    ▼
Priority 6: PRODUCTION_OPTIMIZATION (Strategic Mine Scheduling & Shift Targets)
```
> **Non-Negotiable Rule**: Under NO circumstances can Priority 5 (Cloud Dispatch / Digital Twin) override Priority 2 (Local Governor) or Priority 1 (E-Stop).

---

## 4. Authoritative Physics & Safety Mathematics

### 4.1 Multi-Constraint Safe Speed Envelope Solver
The safe speed ceiling `v_safe` is computed continuously as the lower bound of five simultaneous physical limiters:

```text
v_safe = min(v_stop, v_retarder, v_traction, v_curve, v_mine)
```

1. **Stopping Distance Constraint (`v_stop`)**:
   Guarantees the dumper halts safely before the effective awareness boundary `R_effective`, accounting for all latencies:

   ```text
   S_stop = (v * tau_total) + (v^2 / (2 * a_dec)) <= R_effective - S_margin
   ```

   Total system reaction latency is strictly decomposed:
   ```text
   tau_total = tau_sensor + tau_comm + tau_compute + tau_brake_buildup + tau_operator
   ```
   For BEML BH100 reference dumper:
   - Brake pressure buildup: `tau_brake_buildup = 0.25 s`
   - Operator perception-reaction time: `tau_operator = 0.75 s`
   - Compute cycle latency: `tau_compute = 0.05 s`
   - V2V communication latency: `tau_comm = 0.05 s`
   - Total nominal latency: `tau_total = 1.10 s`

2. **Downhill Retarder Power Balance (`v_retarder`)**:
   On steep haul road declines (grade angle `theta < 0`), gravitational potential energy rate must not exceed hydraulic retarder dissipation capacity `P_retarder_max` (1,119 kW / 1,500 HP for BH100):

   ```text
   v_retarder = P_retarder_max / (m * g * sin|theta| - m * g * C_rr * cos(theta))
   ```

   where `m` is total gross vehicle mass (165,500 kg loaded), `g = 9.81 m/s²`, `C_rr` is rolling resistance coefficient (0.02), and `theta` is haul road slope.

3. **Tire-Road Longitudinal Traction Limit (`v_traction`)**:
   Maximum deceleration cannot exceed available road friction on wet or slurry haul roads:

   ```text
   a_dec = min(a_service_max, mu_surface * g * cos(theta) - g * sin(theta))
   ```
   where `mu_surface` is the estimated surface friction (0.28 to 0.35 in wet clay/mud conditions).

4. **Lateral Curve Rollover & Sideslip Limit (`v_curve`)**:
   At hairpin switchback curves with centerline radius `R_curve`:

   ```text
   v_curve = sqrt((g * R_curve * (e + mu_lat)) / (1 - e * mu_lat))
   ```
   where `e` is road superelevation (<= 0.04) and `mu_lat` is lateral friction coefficient.

5. **Mine Operational Rule Boundary (`v_mine`)**:
   Statutory mine speed limit (typically 40 km/h = 11.11 m/s on trunk haul roads, 15 km/h = 4.17 m/s on ramps and switchbacks).

---

### 4.2 Dynamic Longitudinal Headway (`H_safe`)
Between following dumpers Truck A (following) and Truck B (lead):

```text
H_safe(v_A, v_B) = L_truck + (v_A * tau_total) + (v_A^2 / (2 * a_dec_A)) - (v_B^2 / (2 * a_max_B)) + S_margin_dyn
```

where:
- `L_truck = 10.5 m` (BH100 vehicle length)
- `S_margin_dyn` expands dynamically if packet loss or V2V communication latency jitter is detected.

---

## 5. Repository Directory Map

```
SYNQRA_SIH2026-27/
│
├── SYNQRA_SIH2026-27-HMI/           # Multi-Role Modern Web HMI Application
│   ├── backend/                     # FastAPI / Uvicorn / WebSockets REST & Live API
│   │   ├── app/                     # Telemetry ingestion, safety solver, weather service
│   │   ├── tests/                   # 1,153+ Pytest unit & integration tests
│   │   └── pyproject.toml           # Backend dependencies and linting config
│   │
│   └── frontend/                    # Vite / React 19 / TypeScript / Three.js Frontend
│       ├── index.html               # Fleet Control Room / Technician HMI
│       ├── truck01.html             # TRUCK_01 Operator In-Cab Screen
│       ├── truck02.html             # TRUCK_02 Operator In-Cab Screen
│       ├── mine-cast.html           # MineCast Visibility & Weather View
│       ├── src/                     # React components, Three.js 3D canvas, stores
│       ├── vite.config.ts           # Multi-page bundle and proxy configuration
│       └── package.json             # 1,860 passing Vitest tests (71 test suites)
│
├── fog-orchester-3d-digital-twin/   # Authoritative 3D/2D Digital Twin Engine
│   ├── main.py                      # Twin server (runs on port 8080 via FastAPI)
│   ├── twin/                        # Kinematic vehicle models, spatial mine graph
│   ├── optimizer/                   # Chance-Constrained RH-MPC dispatch & queue models
│   ├── weather/                     # Spatio-temporal fog nowcasting & noise injection
│   ├── scenarios/                   # Master S01–S20 benchmark scenarios
│   └── dashboard/                   # WebGL/Three.js digital twin visualization
│
├── fog_safe/                        # Closed-Form Mathematical Safety Model
│   ├── safety.py                    # Multi-constraint safe speed envelope solver
│   ├── braking.py                   # Stopping distance & friction limit equations
│   ├── retarder.py                  # Downhill thermal power balance equations
│   ├── headway.py                   # Dynamic safe separation & time headway
│   └── validation.py                # Dimensional sanity & Monte Carlo uncertainty tests
│
├── fog_orchestrator/                # Central Fleet Orchestrator & Dynamic Pacing
│   ├── orchestrator.py              # Dynamic speed limits and corridor dispatch
│   └── state_manager.py             # Canonical fleet dynamic state manager
│
├── esp32_code/                      # Microcontroller Firmware (C++ / Arduino)
│   ├── VEHICLE_A_FIRMWARE/          # TRUCK_01 ESP32 chassis firmware (Wi-Fi + CAN)
│   ├── VEHICLE_B_FIRMWARE/          # TRUCK_02 ESP32 chassis firmware (LoRa + CAN)
│   └── LORA_GATEWAY_NODE/           # SX1278 433 MHz to Host Gateway Bridge
│
├── integration_adapters/            # Industrial Bus & Protocol Adapters
│   ├── can_twai_hil.py              # 250 kbps TWAI/CAN bus & SAE J1939 adapter
│   ├── dsss_gateway_selector.py     # 5-layer RF/Gateway selector with hysteresis
│   ├── environmental_data_health.py # 8-state sensor health classifier
│   ├── wheel_imu_odometry.py        # Extended Kalman Filter (EKF) sensor fusion
│   ├── fail_safe_controller.py      # Tier-1 Local Safety Governor implementation
│   └── digital_twin_sync.py         # Twin synchronization adapter & freshness checks
│
├── failsafe/                        # Failsafe Subsystems & Decoupled Fallback
│   └── safe_beacon.py               # Autonomous 433 MHz Safe Beacon broadcaster
│
├── SYNQRA_SIH2026-27-main/          # 2D Mine Visualization Client
│   └── game_ui.py                   # Pygame visualizer consuming authoritative Twin state
│
├── config/                          # Centralized Canonical Configurations (YAML/JSON)
│   ├── hemm_canonical.yaml          # BEML BH100 canonical mechanical parameters
│   └── bailadila_hemm_canonical.yaml# NMDC Bailadila Deposit 5 road geometries
│
├── docs/                            # Hostile Audit, Verification Reports & Specifications
│   ├── 00_EXECUTIVE_SUMMARY.md      # Ground truth executive audit report
│   ├── 19_FINAL_INTEGRATED_ARCHITECTURE.md # Master integrated architecture spec
│   └── MASTER_VERIFICATION_REPORT.md# Complete test matrices & proof artifacts
│
└── tests/                           # Master Integration, HIL & Adversarial Test Suites
```

---

## 6. Multi-Role HMI Suite

The frontend provides specialized, uncluttered views tailored to user roles:

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                              FRONTEND ENTRY POINTS                                     │
├──────────────────────────────┬─────────────────────────────┬───────────────────────────┤
│ Role / Interface             │ Dedicated URL               │ Unified Dev Server URL    │
├──────────────────────────────┼─────────────────────────────┼───────────────────────────┤
│ Fleet Control Room HMI       │ http://localhost:5173/      │ http://localhost:5173/    │
│ TRUCK_01 In-Cab Operator HUD │ http://localhost:3001/      │ http://localhost:5173/    │
│                              │                             │ truck01.html              │
│ TRUCK_02 In-Cab Operator HUD │ http://localhost:3002/      │ http://localhost:5173/    │
│                              │                             │ truck02.html              │
│ MineCast Weather Station     │ http://localhost:3003/      │ http://localhost:5173/    │
│                              │                             │ mine-cast.html            │
└──────────────────────────────┴─────────────────────────────┴───────────────────────────┘
```

### 1. In-Cab Operator HUD (`DriverScreen.tsx`)
Designed strictly around the question: *"What does the dumper operator need to know RIGHT NOW?"*
- **Primary Dial**: Dynamic Safe Speed Ceiling `v_safe` vs Current Speed `v_current`.
- **Sightline Indicator**: Optical visibility distance (`R_eff`) with dynamic hazard warning bars.
- **Grade & Road Telemetry**: Real-time road incline percentage (+% uphill, -% downhill) and hydraulic retarder engagement status.
- **6 Canonical Safety States**:
  - `NORMAL`: Nominal pacing, green indicators.
  - `ADVISORY`: Approaching fog patch or switchback corridor.
  - `WARNING`: Speed exceeds safe stopping envelope; prompt brake advisory.
  - `DEGRADED`: Sensor dropout or high RF latency detected; sightline derated.
  - `SAFE MODE`: Communication lost; vehicle locked to 2.22 m/s crawl.
  - `EMERGENCY`: E-Stop triggered or obstacle detected within stopping envelope; immediate halt.

### 2. Fleet Control Room Console (`ProviderHost.tsx`)
- Interactive 3D/2D spatial mine map with real-time dumper positions and orientations.
- Corridor occupancy monitoring for single-lane hairpin switchbacks and dumping ramps.
- Bottleneck migration ranking and queue buffer levels.
- System health observability (RF RSSI/SNR, CAN bus load, telemetry packet freshness).

---

## 7. Telemetry & Industrial Protocol Contracts

### 7.1 V2V Telemetry Packet Specification
All vehicle-to-vehicle and vehicle-to-infrastructure messages adhere to the standardized ASCII streaming contract:

```text
STATE,TRUCK_01,seq,rpm,speed,ax,ay,az,gx,gy,gz
```

| Field Index | Parameter | Unit | Description |
| :---: | :--- | :---: | :--- |
| `0` | Packet Header | — | Must match `STATE` |
| `1` | Vehicle Identifier | — | Unique vehicle ID (e.g. `TRUCK_01`, `TRUCK_02`) |
| `2` | Sequence Number | count | Monotonically increasing sequence counter |
| `3` | Engine RPM | rev/min | Engine crankshaft rotational speed |
| `4` | Vehicle Speed | m/s | Wheel-speed derived ground velocity |
| `5..7` | Acceleration (ax, ay, az) | m/s² | Longitudinal, lateral, and vertical accelerations |
| `8..10`| Gyroscope (gx, gy, gz) | rad/s | Angular pitch, roll, and yaw rates |

### 7.2 CAN / TWAI Bus Mapping (SAE J1939)
The physical testbed utilizes an onboard ESP32 Two-Wire Automotive Interface (TWAI) at **250 kbps** with 29-bit extended identifiers:
- **PGN 61444 (EEC1)**: Engine Speed & Torque.
- **PGN 65265 (CCVS1)**: Wheel-Based Vehicle Speed.
- **PGN 61441 (EBC1)**: Brake Pedal Position & Retarder Pressure.
- **PGN 65281 (Proprietary)**: Local Safety Governor Speed Command & Invariant Status.
- **Watchdog Protection**: 150 ms bus-off hardware timeout triggering automated failsafe deceleration.

### 7.3 Safe Beacon Fallback Contract
Triggered automatically when communication with the central gateway is lost for >500 ms:
```text
BEACON,TRUCK_01,seq,state,timestamp,zone
```
Broadcast over 433 MHz LoRa at 2 Hz to alert all nearby peer vehicles independently of central infrastructure.

---

## 8. Quick Start & Execution Runbook

### 8.1 Prerequisites
- **Python**: `3.11+` (with `pip`, `venv`)
- **Node.js**: `18.x` or `20.x` (with `npm`)
- **Operating System**: Windows, Linux, or macOS

### 8.2 Installation

```bash
# 1. Clone repository
git clone https://github.com/THEJASWINIE/SYNQRA_SIH2026-27.git
cd SYNQRA_SIH2026-27

# 2. Setup Python virtual environment
python -m venv .venv
# Windows:
.venv\Scripts\activate
# Linux/macOS:
source .venv/bin/activate

# 3. Install core dependencies
pip install -r requirements.txt
pip install -r SYNQRA_SIH2026-27-HMI/backend/requirements.txt
pip install -r fog-orchester-3d-digital-twin/requirements.txt

# 4. Install frontend dependencies
cd SYNQRA_SIH2026-27-HMI/frontend
npm install
cd ../..
```

---

### 8.3 Launching the Complete System

To run all integrated services simultaneously, execute the following commands in separate terminals:

#### Service 1: Authoritative 3D Digital Twin Engine
```bash
cd fog-orchester-3d-digital-twin
python main.py --serve-hmi --port 8080
```
- **Service URL**: `http://127.0.0.1:8080`
- **Swagger API Docs**: `http://127.0.0.1:8080/docs`

#### Service 2: HMI Backend & Telemetry Ingestion API
```bash
cd SYNQRA_SIH2026-27-HMI/backend
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```
- **REST & WebSocket API**: `http://127.0.0.1:8000`
- **Swagger API Docs**: `http://127.0.0.1:8000/docs`

#### Service 3: Unified HMI Frontend Server (Control Room & Driver Screens)
```bash
cd SYNQRA_SIH2026-27-HMI/frontend
npm run dev
```
- **Control Room Console**: `http://localhost:5173/`
- **TRUCK_01 Operator Screen**: `http://localhost:5173/truck01.html`
- **TRUCK_02 Operator Screen**: `http://localhost:5173/truck02.html`
- **MineCast Station**: `http://localhost:5173/mine-cast.html`

*(Optional)* Run dedicated standalone operator ports:
```bash
npm run dev:truck01   # Dedicated port 3001
npm run dev:truck02   # Dedicated port 3002
```

#### Service 4: 2D Pygame Mine Visualizer (Optional Client)
```bash
cd SYNQRA_SIH2026-27-main
python game_ui.py
```

---

### 8.4 Running Closed-Loop Demos & Simulations

```bash
# Run End-to-End Closed-Loop Fog Penetration Demo:
python run_digital_twin_fog_demo.py

# Run Hardware-in-the-Loop (HIL) Simulator:
python run_physical_hil_test.py

# Run Closed-Loop Fog Scenario Verification:
python verify_final_demo_closed_loop.py
```

---

## 9. Verification & Audit Scorecard

The platform underwent rigorous, hostile verification auditing across all embedded and software layers:

| Evaluation Tier | Metric / Target | Result | Status |
| :--- | :--- | :---: | :---: |
| **Defect Resolution** | P0, P1, P2, P3 Audit Gaps | **10 / 10 Resolved (0 Open)** | **CLOSED** |
| **Frontend Tests** | Vitest 71 Test Suites | **1,860 PASS / 0 FAIL** | **PASS** |
| **Backend Unit Tests** | Pytest Integration & Physics Suites | **1,153 PASS / 0 FAIL** | **PASS** |
| **Failure Injection** | Sensor Dropout, RF Timeout, CAN Bus-off | **20 PASS / 0 FAIL** | **PASS** |
| **Twin Position Tracking** | Spatial RMSE vs Reference (T+3s) | **0.342 m** (Target <0.5 m) | **PASS** |
| **Twin Speed Tracking** | Mean Absolute Error (MAE) | **0.084 m/s** | **PASS** |
| **CAN Bus Latency** | TWAI 250 kbps 29-bit loopback | **2.42 ms** (Target <5.0 ms) | **PASS** |
| **Safe Beacon Trigger** | Watchdog trigger latency on RF drop | **512 ms** (Window 500 to 550 ms) | **PASS** |

### Executing the Automated Test Suite

```bash
# Run Frontend Tests (1,860 tests):
cd SYNQRA_SIH2026-27-HMI/frontend
npm test

# Run Backend Tests (1,153+ tests):
cd SYNQRA_SIH2026-27-HMI/backend
pytest

# Run Root Integration & Invariant Tests:
pytest tests/
```

---

## 10. Hardware vs. Simulation Truth Matrix

In adherence to strict engineering integrity (**Rule 3 & Section 23 of `AGENTS.md`**), this project explicitly documents the verification mode of every subsystem:

| Subsystem Component | Verification Mode | Execution Environment & Ground Truth |
| :--- | :---: | :--- |
| **Microcontroller & Telemetry** | **HARDWARE** | Dual ESP32-WROOM-32 microcontrollers with MPU6050 IMU, optical wheel tachometer, and SX1278 LoRa node verified on test bench. |
| **V2V RF Communication** | **HARDWARE** | 433 MHz LoRa and Wi-Fi dual-link telemetry verified between physical ESP32 nodes and host gateway. |
| **Tier-1 Safety Governor** | **HARDWARE & HIL** | Autonomous speed ceiling enforcement and safe crawl transitions verified in firmware and HIL test harness. |
| **TWAI / CAN Bus (J1939)** | **EMULATED / HIL** | 250 kbps TWAI frames validated via SN65HVD230 transceivers and loopback hardware-in-the-loop harness. |
| **HEMM Physical Vehicle Chassis** | **SIMULATION / BENCH** | BEML BH100 mass and hydraulic brake models executed via physics-based simulation; motor dyno rig on physical bench. |
| **NMDC Bailadila Deposit 5** | **GEODATA MODEL** | Actual topography, ramp grades (8% to 12%), and hairpin curves digitized from official NMDC survey geodata. |

---

## 11. Reference Mine & Machinery Specifications

### 11.1 Heavy Haulage Dumper: BEML BH100
- **Gross Vehicle Mass (Empty)**: 74,000 kg
- **Gross Vehicle Mass (Loaded)**: 165,500 kg
- **Payload Capacity**: 100 tonnes (91.5 t nominal)
- **Engine Power**: 895 kW (1,200 HP) @ 2,100 RPM
- **Hydraulic Retarder Power**: 1,119 kW (1,500 HP)
- **Service Brake System**: Oil-cooled multiple disc, all-hydraulic actuation (tau_buildup = 0.25 s)
- **Nominal Max Speed**: 45 km/h (12.5 m/s)

### 11.2 Mine Site: NMDC Bailadila Complex (Deposit 5)
- **Mine Type**: Large-scale open-cast iron ore mine
- **Location**: Kirandul / Bacheli, Dantewada District, Chhattisgarh, India
- **Haul Road Gradients**: 8.0% nominal, 12.0% maximum on pit ramps
- **Switchback Geometry**: Hairpin turns with minimum centerline radius R_curve = 22 m
- **Climate Challenges**: Dense monsoon/winter valley fog, severe visibility degradation (<15 m), wet slick iron-ore fines slurry (μ ≈ 0.28 to 0.35).

---

## 12. Team & Acknowledgments

- **Team SYNQRA**: Smart India Hackathon (SIH 2026–27)
- **Problem Statement ID**: SIH26007
- **Theme**: Mine-Vehicle Safety and Fleet Orchestration System for Low-Visibility and Fog Operation
- **Target Organization**: Ministry of Steel / NMDC Limited
- **Reference Standards**: DGMS (Directorate General of Mines Safety) Circulars, SAE J1939 Commercial Vehicle Bus Specifications, ISO 26262 Road Vehicle Functional Safety.

---
*For in-depth architectural specifications, forensic reports, and mathematical proofs, refer to [`docs/19_FINAL_INTEGRATED_ARCHITECTURE.md`](docs/19_FINAL_INTEGRATED_ARCHITECTURE.md) and [`docs/00_EXECUTIVE_SUMMARY.md`](docs/00_EXECUTIVE_SUMMARY.md).*
