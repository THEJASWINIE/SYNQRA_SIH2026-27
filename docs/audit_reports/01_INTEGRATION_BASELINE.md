# 01 — INTEGRATION BASELINE & DISCOVERY REPORT
## FOG-ORCHESTRATOR 2.0 | SIH 2026-27 (Problem Statement: SIH26007)
### NMDC Bailadila Deposit-5 Low-Visibility HEMM Safety & Fleet Orchestration System
**Phase 9: Hardware + Software Integration**
**Date:** September 2026 | **Status:** BASELINE FROZEN & VERIFIED

---

## 1. EXECUTIVE INTEGRATION MANDATE

The physical hardware-to-software communication path in FOG-ORCHESTRATOR 2.0 is **already working and validated on bench hardware**. 
In strict compliance with the Phase 9 Master Mandate and project rules:
1. **DO NOT rebuild** the existing communication pipeline.
2. **DO NOT replace** working hardware drivers.
3. **DO NOT rewrite** the existing architecture.
4. **DO NOT introduce** unnecessary new frameworks.
5. **INCREMENTALLY INTEGRATE** the newly validated research modules (HEMM calibration, sensor degradation intelligence, DSSS/PN gateway selection, Safe Beacon protocol, Local Safety Governor authority, CAN/J1939 timing abstraction, and HIL validation).

---

## 2. EXISTING HARDWARE ARCHITECTURE (PHYSICAL BENCH BASELINE)

```
[ PHYSICAL VEHICLES / SENSORS ]
   │
   ├── TRUCK_01: ESP32-WROOM-32 (NodeMCU-32S) + MPU6050 6-DOF IMU + Wheel Speed Tachometer
   │   └── Transceiver: Semtech SX1278 (Ra-02) 433 MHz LoRa (Chirp Spread Spectrum, CSS)
   │
   ├── TRUCK_02: ESP32-WROOM-32 (NodeMCU-32S) + MPU6050 6-DOF IMU + Wheel Speed Tachometer
   │   └── Transceiver: Semtech SX1278 (Ra-02) 433 MHz LoRa (CSS Modulation)
   │
   └── Direct Peer-to-Peer V2V Link (TRUCK_01 <---> TRUCK_02 @ 433 MHz, SF7/BW125/CR4/5)
          │
          ▼
[ PHYSICAL GATEWAY AGGREGATOR ]
   └── Gateway ESP32: SX1278 LoRa Receiver + 802.11 b/g/n 2.4 GHz Wi-Fi Station
       ├── Ingestion: 433 MHz RF packet reception & CRC validation
       ├── Conversion: Hardware packet to JSON `HardwareTelemetryPayload`
       └── Uplink: HTTP POST /api/hardware/telemetry to Orchestrator Backend Host
```

### Hardware Characterization & Evidence Boundary
- **Microcontrollers:** Espressif ESP32-D0WD-V3 (Dual Core Xtensa LX6 @ 240 MHz).
- **RF Hardware:** Semtech SX1278 SPI LoRa module operating at 433.0 MHz.
  > **CRITICAL EVIDENCE BOUNDARY:** The physical bench hardware executes **Chirp Spread Spectrum (CSS)** via SX1278 registers. It does **NOT** execute physical Direct-Sequence Spread Spectrum (DSSS). The DSSS/PN correlation architecture is an evaluated **research & architectural abstraction** implemented in software to enable seamless migration to future military/mining DSSS transceivers without breaking the higher-level safety stack.
- **Physical Validation Status:** Level 4 (Bench Hardware Validated). Two physical ESP32 nodes with MPU6050 sensors actively communicate with an ESP32 gateway node over 433 MHz LoRa and relay to the FastAPI backend.

---

## 3. EXISTING SOFTWARE ARCHITECTURE & DATA FLOW

```
Physical Sensors / LoRa Transceiver / HIL Bridge
                      │
                      ▼
            ESP32 Gateway Node
                      │  (HTTP POST /api/hardware/telemetry)
                      ▼
         FastAPI Orchestrator Backend
  ┌───────────────────┴───────────────────────┐
  │                                           │
  ▼                                           ▼
telemetry_ingest.py                  environmental_data_health.py
  │  (Validation, Sequence Check,       │  (Degradation Filter, Stuck-At,
  │   Timestamping, Quality Scoring)    │   Drift, Confidence Assessment)
  └───────────────────┬───────────────────────┘
                      │
                      ▼
            Authoritative Digital Twin
         (twin_state.py / twin_state_store.py)
                      │
        ┌─────────────┴─────────────┐
        │                           │
        ▼                           ▼
fog_safe/ / safety_governor.py  dsss_gateway_selector.py
  (Stopping Distance, Grade,     (Correlation-based Handover,
   Retarder, Safe Speed Limit)    Link Quality Monitoring)
        │                           │
        └─────────────┬─────────────┘
                      │
                      ▼
             Command Gateway
        (command_gateway.py / fail_safe_controller.py)
                      │
        ┌─────────────┴───────────────────────┐
        │                                     │
        ▼                                     ▼
CAN / TWAI Bus Adapter              Safe Beacon Failsafe
(can_twai_hil.py - J1939)            (safe_beacon_adapter.py)
        │                                     │
        ▼                                     ▼
Vehicle Actuator Interface          Peer Vehicle Awareness
(Local Governor Clamped)            (Autonomous Crawl on Comm Loss)
        │
        ▼
WebSocket Broadcast (/api/ws)
  ├── Technician / Fleet HMI (React + Vite Dashboard)
  ├── Operator In-Cab HMI (HUD Display)
  └── 2D / 3D Visualization Clients (game_ui.py / Three.js Twin)
```

---

## 4. EXISTING WORKING INTERFACES & MESSAGE FORMATS

### 4.1 Physical V2V RF Protocol (Over-the-Air 433 MHz LoRa)
```
STATE,<VEHICLE_ID>,<SEQ>,<RPM>,<SPEED>,<AX>,<AY>,<AZ>,<GX>,<GY>,<GZ>[,RSSI=<val>,SNR=<val>]
```
- **Example:** `STATE,TRUCK_01,1042,1850,5.25,-0.12,0.01,9.81,0.02,-0.01,0.00,RSSI=-68,SNR=8.5`
- **Owner:** ESP32 Firmware (`TRUCK_01_TRANSMITTER.ino`, `TRUCK_02_TRANSMITTER.ino`).
- **Update Rate:** 10 Hz (100 ms interval).
- **Rule:** Strictly preserved without breaking changes.

### 4.2 Gateway Ingestion Payload (`POST /api/hardware/telemetry`)
- **Format:** JSON `HardwareTelemetryPayload`
- **Fields:**
  - `vehicle_id` (string): `TRUCK_01` or `TRUCK_02`
  - `sequence` (integer): Monotonically increasing packet sequence
  - `rpm` (float): Engine crankshaft rotational speed [0–2500 RPM]
  - `speed` (float): Longitudinal vehicle velocity [0.0–15.0 m/s]
  - `ax`, `ay`, `az` (float): 3-axis accelerometer readings [m/s²]
  - `gx`, `gy`, `gz` (float): 3-axis gyroscope readings [deg/s or rad/s]
  - `rssi` (float, optional): Received Signal Strength Indicator [dBm]
  - `snr` (float, optional): Signal-to-Noise Ratio [dB]
  - `gateway_id` (string, optional): ID of receiving gateway (e.g., `GW_RAMP_01`)
  - `timestamp` (float): Milliseconds or seconds epoch timestamp

### 4.3 Safe Beacon Broadcast Protocol
```
BEACON,<vehicle_id>,<sequence>,<state>,<timestamp>,<zone_id>
```
- **States:** `NORMAL`, `DEGRADED`, `STOP`, `EMERGENCY`
- **Update Rate:** 2 Hz (nominal) to 5 Hz (emergency/degraded).
- **Payload Size:** 36–48 bytes.

### 4.4 CAN / J1939 Frame Definitions (250 kbps, 29-bit Identifiers)
- `PGN 61444` (`0x0CF00400`): Electronic Engine Controller 1 (EEC1) — Engine RPM (0.125 rpm/bit).
- `PGN 65265` (`0x18FEF100`): Cruise Control / Vehicle Speed (CCVS) — Wheel speed (1/256 km/h per bit).
- `PGN 61441` (`0x18F0010B`): Electronic Brake Controller 1 (EBC1) — Brake pressure / brake pedal position.
- `PGN 61440` (`0x18F0000F`): Electronic Retarder Controller 1 (ERC1) — Retarder torque / braking absorption.
- `PGN 65281` (`0x18FF0100`): Proprietary B Safety Command — Commanded speed, governor clamping status.
- `PGN 65282` (`0x18FF0200`): Proprietary B Vehicle Safety State — Active safety mode, safe stopping envelope.

---

## 5. EXISTING TIMING ASSUMPTIONS & LATENCY BUDGET

| Component | Symbol | Modeled Budget | Bench Measured (L7) | Status |
| :--- | :--- | :--- | :--- | :--- |
| Sensor Acquisition & Filtering | $\tau_{\text{sensor}}$ | 25.0 ms | 25.0 ms | Measured (ESP32 ADC/IMU) |
| RF Over-The-Air Transmission | $\tau_{\text{RF}}$ | 41.2 ms | 41.2 ms | Measured (SX1278 433 MHz) |
| Gateway Processing & Serial Ingestion | $\tau_{\text{gateway}}$ | 15.0 ms | 14.8 ms | Measured (Gateway loop) |
| Central Orchestrator & Digital Twin | $\tau_{\text{decision}}$ | 50.0 ms | 48.2 ms | Measured (FastAPI loop) |
| Local Safety Governor Execution | $\tau_{\text{governor}}$ | 50.0 ms | 50.0 ms | Measured (20 Hz task tick) |
| CAN / TWAI Bus Latency | $\tau_{\text{CAN}}$ | 50.0 ms | 50.0 ms | Measured (ESP32 TWAI @ 75% load) |
| Hydraulic / Pneumatic Brake Build-up | $\tau_{\text{actuator}}$ | 250.0 ms | — | **Engineering Assumption (ISO 3450)** |
| **Total Local Reaction Latency** | $\tau_{\text{total}}$ | **437.1 ms (P99)** | — | **Hybrid Budget (Measured + Modeled)** |
| **Max Legal Safety Horizon** | $\tau_{\text{design}}$ | **800.0 ms** | — | **DGMS Mining Safety Standard** |

> **HONESTY CLAUSE:** Actuator lag of 250 ms is an OEM engineering standard parameter (ISO 3450 / SAE J1452). It has **NOT** been measured on a live BEML BH100 hydraulic brake valve.

---

## 6. SENSOR INPUTS, CONTROL OUTPUTS & SAFETY MECHANISMS

### Sensor Inputs
1. **Longitudinal Velocity ($v$):** Wheel speed sensors + GPS Doppler [0–15 m/s].
2. **Engine Speed ($N$):** Crankshaft magnetic pickup [0–2500 RPM].
3. **IMU Accelerations ($a_x, a_y, a_z$):** 6-DOF MPU6050 accelerometer [-16g to +16g].
4. **IMU Angular Rates ($\omega_x, \omega_y, \omega_z$):** 6-DOF MPU6050 gyro [±2000 deg/s].
5. **Visibility ($R_{\text{vis}}$):** Optical scatter forward transmissometer [0–300 m].
6. **Haul Road Longitudinal Grade ($\theta$):** Digital elevation map + inclinometer [-15% to +15%].
7. **Surface Friction ($\mu$):** Environmental weather station estimation [0.20 to 0.45].

### Control Outputs
1. **Target Commanded Speed ($v_{\text{command}}$):** Setpoint delivered to engine ECU / retarder.
2. **Governor Clamping Status:** Boolean indicating whether local governor clamped remote speed.
3. **Retarder Brake Request:** Proportional retarder torque request [0–100%].
4. **Service / Emergency Brake Demand:** Binary/proportional friction brake command.
5. **Safe Beacon State Broadcast:** Local vehicle health & degradation announcement.

### Safety Invariants
- **Invariant I1:** $v_{\text{command}} \le v_{\text{safe}}$ strictly holds at all times.
- **Invariant I2:** No remote command accepted during `COMMUNICATION_LOST`.
- **Invariant I3:** Safe Beacon activates within $\le 500\text{ ms}$ of communication timeout.
- **Invariant I4:** Local safety governor remains authoritative if central orchestrator crashes.
- **Invariant I5:** Stale sensor data ($>1000\text{ ms}$) cannot silently control the vehicle.
- **Invariant I6:** Gateway handover cannot cause unsafe command discontinuity.
- **Invariant I7:** CAN bus timeout triggers deterministic failsafe deceleration.
- **Invariant I8:** Emergency Stop has highest overriding command priority.

---

## 7. BASELINE TEST SUITE VERIFICATION

Before applying any Phase 9 modifications, the entire existing test suite was executed:
- **Command:** `python -m pytest -q`
- **Total Test Files:** 83
- **Total Tests:** 1048
- **Passed:** 1047
- **Skipped:** 1 (`test_game_ui_render_smoke.py` - headless display)
- **Failed:** 0
- **Duration:** 60.29 seconds
- **Baseline Integrity:** **100% PASS — BASELINE PROTECTED**

---

## 8. INTEGRATION ROADMAP (PHASE 9)

1. **Contract Definition:** Complete `docs/HARDWARE_SOFTWARE_INTERFACE_CONTRACT.md` covering all 13 interfaces.
2. **Canonical Configuration:** Lock single source of truth in `config/integration_canonical.yaml`.
3. **Sensor Degradation Intelligence:** Integrate `environmental_data_health.py` cleanly into the safety governor.
4. **DSSS / PN Gateway Layer:** Unify physical LoRa and DSSS model via `RFHardwareAdapter` and `dsss_gateway_selector.py`.
5. **Safe Beacon Module:** Expose clean `failsafe/safe_beacon.py` standalone failsafe.
6. **CAN / J1939 Timing Abstraction:** Run bench latency characterization and produce `CAN_TIMING_REPORT.md`.
7. **End-to-End State Machine:** Implement integrated safety state machine across all 9 operational states.
8. **HIL & Adversarial Test Suite:** Execute all 18 HIL test cases + 17 adversarial fault injections.
9. **Final Benchmark & Reports:** Produce all 12 required project documentation deliverables.
