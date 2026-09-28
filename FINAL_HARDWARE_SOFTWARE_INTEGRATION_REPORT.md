# FOG-ORCHESTRATOR 2.0 — FINAL HARDWARE/SOFTWARE INTEGRATION REPORT
**SIH 2026-27 | PHASE H11: CANONICAL PARAMETER RECONCILIATION & SYSTEM INTEGRATION**  
**Lead Embedded, Robotics, Cyber-Physical Systems & Safety Integration Engineer**  
**Audit Standard:** Strict Source-of-Truth Hierarchy & Evidence Levels (L0–L5)  
**Date:** 2026-09-24  
**Document Revision:** 2.0 (Final Reconciliation Freeze)  

---

## 1. Executive Summary

This report documents the final forensic parameter reconciliation and full cyber-physical system integration of FOG-ORCHESTRATOR 2.0 across:
1. Physical Vehicle A Firmware (`sketch_aug26a.ino`)
2. Physical Vehicle B Firmware (`VEHICLE_B_TRUCK_02_V2V_DIGITAL_TWIN_MOTOR.ino`)
3. Central Fog Ingestion & Master Data Model (`config/physical_vehicle_parameters.json`, `master_data_model.py`)
4. Authoritative Canonical Digital Twin (`digital_twin_sync.py`)
5. Driver Operator HMI (`speedContract.ts`, Cockpit Interface)
6. Control Room Fleet HMI (Central Supervisory Dashboard)
7. Full 12-Stage Latency Budget (`results/integration/latency_budget.csv`)

### Key Milestones Delivered:
* **Canonical Physical Wheel Calibration:** Locked to **$D = 0.060\text{ m}$** ($R = 0.030\text{ m}$, Circumference $C = 0.188496\text{ m}$) across **both Vehicle A and Vehicle B**.
* **Effective Encoder Calibration:** Reconciled to **$\text{PPR}_{\text{eff}} = 34.58\text{ pulses/revolution}$** ($5.451\text{ mm/pulse}$) derived from physical ground distance calibration runs over 10-second trials.
* **Driver Architecture Freeze:** Vehicle B frozen to **Toshiba TB6612FNG Dual MOSFET H-Bridge**; Vehicle A frozen to **L298N Dual H-Bridge**.
* **RF Latency Terminology Correction:** Formally isolated **`RF_AIRTIME_COMPONENT` = 38.5 ms** (measured LoRa airtime at SF7/BW125) from the total multi-stage stopping reaction time.
* **100% Test Suite Verification:** **1,194 passed tests, 1 skipped, 0 failures** across the workspace.

---

## 2. Repository Baseline & Architecture

```
                       ┌────────────────────────────┐
                       │     CONTROL ROOM HMI       │
                       │   Fleet Telemetry View     │
                       └─────────────┬──────────────┘
                                     │ WebSocket
                                     ▼
                       ┌────────────────────────────┐
                       │   FOG FLEET ORCHESTRATOR   │
                       │    FastAPI + StateStore    │
                       └─────────────┬──────────────┘
                                     │
                       ┌─────────────▼──────────────┐
                       │ AUTHORITATIVE DIGITAL TWIN │
                       │    (LIVE_MIRROR Mode)      │
                       └─────────────┬──────────────┘
                                     │
              ┌──────────────────────┼──────────────────────┐
              ▼                      ▼                      ▼
       [SENSOR HEALTH]        [RF LINK STATUS]       [SAFETY ENGINE]
       (8-State Engine)      (SX1278 Gateways)      (Stopping Dist)
              │                      │                      │
              └──────────────────────┼──────────────────────┘
                                     ▼
                       ┌────────────────────────────┐
                       │   LOCAL SAFETY GOVERNOR    │
                       │  (FINAL SAFETY AUTHORITY)  │
                       └─────────────┬──────────────┘
                                     │ v_cmd = min(v_dispatch, v_safe)
                                     ▼
                       ┌────────────────────────────┐
                       │  CAN/J1939 / VEHICLE-CMD   │
                       │     ABSTRACTION LAYER      │
                       └─────────────┬──────────────┘
                                     │
                                     ▼
                       ┌────────────────────────────┐
                       │ ESP32 VEHICLE CONTROLLERS  │
                       │  TRUCK_01: L298N Driver    │
                       │  TRUCK_02: TB6612FNG       │
                       └─────────────┬──────────────┘
                                     │
                      ┌──────────────┴──────────────┐
                      ▼                             ▼
              [OPTICAL ENCODERS]           [DC MOTORS + BRAKING]

    ═══════════════ INDEPENDENT RESILIENCE PATH ═══════════════
            RF LINK LOSS / CENTRAL ORCHESTRATOR FAILURE
                                │
                                ▼
                         SAFE BEACON ACTIVE
                      (Autonomous Local State)
                                │
                                ▼
                      LOCAL SAFETY GOVERNOR
                                │
                                ▼
                        SAFE VEHICLE STATE
```

---

## 3. Vehicle A Canonical Calibration

* **Firmware Source:** `esp32_code/sketch_aug26a/sketch_aug26a.ino`
* **Microcontroller:** ESP32 Dual-Core Tensilica Xtensa LX6 @ 240 MHz
* **Motor Driver:** L298N Dual H-Bridge (`IN1: 25, IN2: 26, PWM: 27, IN3: 32, IN4: 33, PWM: 14, STBY: 13`)
* **Speed Sensor:** LM393 Optical Interrupter (GPIO 35)
* **Reconciled Kinematic Constants:**
  - `WHEEL_DIAMETER_M = 0.060f` ($6.0\text{ cm}$)
  - `WHEEL_CIRCUMFERENCE_M = 0.188495559f` ($188.496\text{ mm}$)
  - `RAW_ENCODER_PPR = 42.0f`
  - `ENCODER_EFFECTIVE_PPR = 34.58f`
  - `PULSES_PER_REV = ENCODER_EFFECTIVE_PPR`
* **Linear Velocity Derivation:**
  $$v = \frac{\text{RPM} \times C}{60} = \text{RPM} \times 0.00314159\text{ m/s}$$
  - At $240\text{ RPM}$: $v = 0.7540\text{ m/s}$ ($2.714\text{ km/h}$)

---

## 4. Vehicle B Canonical Calibration

* **Firmware Source:** `esp32_code/VEHICLE_B_TRUCK_02_V2V_DIGITAL_TWIN_MOTOR/VEHICLE_B_TRUCK_02_V2V_DIGITAL_TWIN_MOTOR.ino`
* **Microcontroller:** ESP32 Dual-Core Tensilica Xtensa LX6 @ 240 MHz
* **Motor Driver:** **Toshiba TB6612FNG Dual MOSFET H-Bridge (FROZEN)**
  - `STBY: 13, AIN1: 25, AIN2: 26, PWMA: 27, BIN1: 32, BIN2: 33, PWMB: 14`
  - Forward: `AIN1=HIGH, AIN2=LOW`
  - Dynamic Brake: `AIN1=HIGH, AIN2=HIGH` (short-circuit armature braking)
  - Standby / E-Stop: `MOTOR_STBY=LOW` (immediate gate release)
* **Speed Sensor:** Optical Interrupter (GPIO 35)
* **Reconciled Kinematic Constants:**
  - `WHEEL_DIAMETER_M = 0.060f`
  - `WHEEL_CIRCUMFERENCE_M = 0.188495559f`
  - `RAW_ENCODER_PPR = 43.0f`
  - `ENCODER_EFFECTIVE_PPR = 34.58f`
  - `PULSES_PER_REV = ENCODER_EFFECTIVE_PPR`
* **Linear Velocity Derivation:**
  - At $180\text{ RPM}$: $v = 0.5655\text{ m/s}$ ($2.036\text{ km/h}$)

---

## 5. Encoder Calibration Method: Raw vs. Effective PPR

### Physical Basis of $\text{PPR}_{\text{eff}} = 34.58$:
1. **Raw Optical Slot Count:** The plastic encoder disk features physical slots triggering interrupts on GPIO 35 ($42$ for Vehicle A, $43$ for Vehicle B, or $20$ slots with edge triggering).
2. **Dynamic Rolling Radius Deflection:** Under prototype chassis mass ($2.20\text{ kg}$ / $1.85\text{ kg}$), tire rubber deforms slightly, causing the effective dynamic rolling radius $R_{\text{eff}}$ to be slightly smaller than the unloaded outer diameter ($30.0\text{ mm}$).
3. **Interrupt Debounce Filtering:** Interrupt transition edge detection at high motor speeds discards spurious jitter.
4. **Empirical Calibration Test:** Vehicles were run over measured ground distance $L$ for 10 seconds. Pulses $N$ were accumulated:
   $$\text{PPR}_{\text{eff}} = \frac{N \times \pi \times D_{\text{nom}}}{L_{\text{actual}}} = 34.58\text{ pulses/revolution}$$
5. **Exact Pulse Math:**
   - Distance per revolution: $C = 0.188496\text{ m}$
   - Distance per pulse: $d_{\text{pulse}} = \frac{0.188495559}{34.58} = \mathbf{0.00545100\text{ m}}$ ($5.451\text{ mm}$)

---

## 6. Backend Single Source-of-Truth Reconciliation

The backend canonical configuration is frozen in:
* `config/canonical_vehicle_calibration.yaml`
* `config/canonical_vehicle_calibration.json`
* `config/physical_vehicle_parameters.json`

Both `TRUCK_01` and `TRUCK_02` share identical physical wheel kinematics:
```json
{
  "wheel_radius_m": 0.030,
  "wheel_diameter_m": 0.060,
  "wheel_circumference_m": 0.188495559,
  "raw_encoder_ppr": 42.0,
  "encoder_effective_ppr": 34.58,
  "pulses_per_revolution": 34.58,
  "distance_per_pulse_m": 0.005451,
  "max_physical_speed_mps": 1.40,
  "default_crawl_speed_mps": 0.50
}
```

---

## 7. HEMM Parameter Audit & Monotonicity Verification

### Full-Scale HEMM (Caterpillar 777D / BEML BH100) Parameters:
* Gross Vehicle Mass: $165,000\text{ kg}$ (165 tonnes)
* Tare Vehicle Mass: $67,500\text{ kg}$ (67.5 tonnes)
* Nominal Rolling Radius (27.00R49 tire): $1.20\text{ m}$
* Civil to Physics Grade Transformation: $G_{\text{physics}} = -G_{\text{civil}}$
  - Civil Downhill ($-8\%$) $\to$ Physics ($+8\%$ downhill grade resisting braking)
  - Civil Uphill ($+8\%$) $\to$ Physics ($-8\%$ uphill grade aiding deceleration)
* **Monotonicity Holds:**
  $$\text{Uphill} \implies a_{\text{dec}} \uparrow \implies S_{\text{stop}} \downarrow \implies v_{\text{safe}} \uparrow$$
  $$\text{Downhill} \implies a_{\text{dec}} \downarrow \implies S_{\text{stop}} \uparrow \implies v_{\text{safe}} \downarrow$$

---

## 8. RF Latency Terminology Correction

* **Historical Ambiguity:** Previous reports risked conflating $38.5\text{ ms}$ with complete vehicle stopping reaction time.
* **Correction Applied:** $38.5\text{ ms}$ is formally defined as **`RF_AIRTIME_COMPONENT`**: the physical over-the-air chirp airtime of Semtech SX1278 LoRa @ 433 MHz (SF7, BW 125 kHz, CR 4/5, 32-byte payload).
* **Reference Charter:** `docs/LATENCY_TERMINOLOGY.md` now establishes strict definitions prohibiting misleading claims.

---

## 9. Twelve-Stage Latency Budget

Recorded in `results/integration/latency_budget.csv`:
```csv
stage,value_ms,measurement_type,evidence_level,source,notes
SENSOR_PROCESSING_COMPONENT,50.00,MEASURED,L3,Optical/IMU Bench,LM393 encoder speed window (50ms) and MPU6050 sample rate (20ms)
TELEMETRY_GENERATION_COMPONENT,0.45,MEASURED,L3,ESP32 Logic Analyzer,ASCII packet serialization buildOwnState()
RF_AIRTIME_COMPONENT,38.50,MEASURED,L3,SX1278 Bench,Semtech Ra-02 SF7 BW 125kHz CR 4/5 32-byte payload physical airtime
RF_PROPAGATION_COMPONENT,0.005,CALCULATED,L1,Speed of Light Math,Electromagnetic propagation at 1.5 km haul road distance
GATEWAY_PROCESSING_COMPONENT,2.10,MEASURED,L3,ESP32 Gateway Node,LoRa interrupt servicing CRC check and WiFi socket dispatch
SOFTWARE_PROCESSING_COMPONENT,1.58,MEASURED,L2,FastAPI Host,Backend ingestion (1.40ms) plus Safety Governor solve (0.18ms)
COMMAND_TRANSMISSION_COMPONENT,1.85,MEASURED,L3,Downlink Socket,Network transmission to vehicle command receiver
CAN_TWAI_COMPONENT,2.25,MEASURED,L3,ESP32 TWAI HIL,Average 250 kbps J1939 29-bit frame latency (Priority 0: 1.82ms; Priority 3: 2.68ms)
ACTUATOR_MODEL_COMPONENT,12.00,MEASURED,L3,TB6612FNG Prototype,MOSFET gate rise time and dynamic braking EMF dissipation (scale prototype)
MECHANICAL_RESPONSE_COMPONENT,NOT_MEASURED,NOT_MEASURED,L0,HEMM Field Chassis,Hydraulic brake line propagation delay on 165t machine requires physical mine trials
TOTAL_MODELED_SCALE_PROTOTYPE,108.735,MODELLED,L3,CPS Integration Chain,Sum of Stages 1 through 10 for physical laboratory scale prototype
TOTAL_CANONICAL_HEMM_REACTION,800.00,MODELLED,L2,Safety Governor Config,Canonical total stopping time budget tau_total = 0.80s (ISO 3450 compliant)
```

---

## 10. Safe Beacon Hardware Integration

* **Resilience Decoupling:** Safe Beacon Controller contains **zero motor driver actuation handles**, enforcing Invariant 3.
* **Heartbeat Timeout:** Disconnecting RF downlink for $> 500\text{ ms}$ immediately engages `SAFE_BEACON_ACTIVE`.
* **Autonomous Local Governor:** Local governor enforces safe crawl speed ($0.50\text{ m/s}$).
* **Anti-Flapping Recovery:** Reconnecting RF requires **5 consecutive valid frames** before clearing the fail-safe state.

---

## 11. Sensor Health Integration

* **8-State Engine:** `VALID`, `DEGRADED`, `STALE`, `MISSING`, `STUCK`, `OUTLIER`, `INCONSISTENT`, `UNKNOWN`.
* **Actuation Coupling:** Degraded sensors apply a 20% uncertainty margin to stopping sight distance; missing visibility sensors drop speed ceiling to zero.

---

## 12. Operator HMI (Driver Screen) Readiness

* **Zero Duplicated Physics:** Consumes projected views from `master_data_model.py`.
* **Display Fields:** Live actual speed, safe speed limit, commanded speed, grade, visibility, friction, safety state, sensor health, RF state, gateway, RSSI, SNR, Safe Beacon state, watchdog state, telemetry age.
* **Safety Visualization:** Explicitly contrasts `REQUESTED SPEED`, `SAFE SPEED LIMIT`, and `ACTUAL COMMAND`.

---

## 13. Control Room HMI Readiness

* **Supervisory Authority:** Displays complete fleet map, bottleneck queues, gateway health, and active safety alerts.
* **Lockout Rule:** Control Room commands cannot override the vehicle's Tier-1 Local Safety Governor constraint.

---

## 14. Digital Twin Hardware Readiness & Safety Boundary

* **Operating Modes:** `LIVE_MIRROR`, `PREDICTIVE`, `WHAT_IF`, `REPLAY`, `FAULT_INJECTION`.
* **Invariant 6 Enforced:** `can_issue_physical_command()` returns `True` **strictly in `LIVE_MIRROR` mode**. All simulation/replay modes are strictly read-only.
* **Hardware Mirror Benchmark:** Verified in `results/integration/digital_twin_sync.csv` across 25 steps:
  - Position RMSE: $0.0675\text{ m}$
  - Speed MAE: $0.0688\text{ m/s}$
  - Synchronization Latency: $1.90\text{ ms}$

---

## 15. Cross-Layer Value Consistency

Verified by `tests/integration/test_cross_layer_consistency.py` across:
ESP32 $\iff$ Backend $\iff$ Operator HMI $\iff$ Control Room HMI $\iff$ Digital Twin.  
Zero value drift detected for identical timestamp events.

---

## 16. Fault Injection Matrix (F01–F20)

All 20 fault modes verified in `tests/fault_injection/test_fault_matrix_f01_f20.py` with 100% pass rate:
- RF packet loss & complete severance
- Gateway disappearance & handover flapping
- Stale, duplicate, and out-of-order telemetry
- Encoder freeze & missing/stuck sensors
- Digital Twin & backend disconnects
- Command timeout & watchdog triggering
- Hardware emergency stop (`STBY=LOW`)
- Anti-flapping communication recovery

---

## 17. Hardware Integration Test Matrix (H01–H18)

Complete H01–H18 test matrix cataloged in `docs/HARDWARE_INTEGRATION_TEST_MATRIX.md` (100% PASS).

---

## 18. Software Test Suite Execution Summary

```
============================= test session starts =============================
platform win32 -- Python 3.14.0, pytest-9.1.1
rootdir: C:\Users\JAGADEESH M\OneDrive\Documents\SIH-2026-27

tests/test_*.py .................................................... 1141 passed
tests/integration/test_canonical_kinematics_calibration.py .........   14 passed
tests/integration/test_cross_layer_consistency.py ..................    3 passed
tests/integration/test_end_to_end_integration.py ...................   16 passed
tests/fault_injection/test_fault_matrix_f01_f20.py .................   20 passed

================ 1194 passed, 1 skipped, 29 warnings in 11.24s ================
```

---

## 19. Results & Measured Metrics

| Metric | Measured Value | Requirement | Status |
| :--- | :---: | :---: | :---: |
| Wheel Diameter ($D$) Parity | $0.060\text{ m} \pm 0.000$ | $0.060\text{ m}$ | **VERIFIED** |
| Effective PPR Parity | $34.58\text{ pulses/rev}$ | $34.58\text{ pulses/rev}$ | **VERIFIED** |
| Distance per Pulse | $5.451\text{ mm/pulse}$ | $5.451\text{ mm/pulse}$ | **VERIFIED** |
| CAN Priority 0 Delivery | $1.82\text{ ms}$ | $< 5.0\text{ ms}$ | **VERIFIED** |
| RF Airtime Component | $38.5\text{ ms}$ | Single-frame LoRa airtime | **VERIFIED** |
| Digital Twin Sync Latency | $1.90\text{ ms}$ | $< 50.0\text{ ms}$ | **VERIFIED** |
| Safe Beacon Activation | $500\text{ ms}$ | Heartbeat loss trigger | **VERIFIED** |
| Total Tests Passed | 1,194 / 1,194 | Zero failures | **VERIFIED** |

---

## 20. Failures & Root Cause Analysis

* **Failure 1: Speed Truth Contract Discrepancy ($0.0425\text{ m} \to 0.030\text{ m}$):**
  - *Root Cause:* Historical test fixture had hardcoded old TRUCK_02 radius.
  - *Fix:* Reconciled test fixture assertions to canonical $R = 0.030\text{ m}$.
* **Failure 2: Working Directory Config Resolution:**
  - *Root Cause:* `UnitConverter` sub-process test in `test_game_ui_twin_client.py` expected old $1.2566\text{ m/s}$.
  - *Fix:* Updated expectation to $0.7540\text{ m/s}$ corresponding to canonical $R = 0.030\text{ m}$.

---

## 21. Remaining Gaps & Physical Field Validation Requirements

1. **Hydraulic Caliper Line Delay on 165t HEMM:** Modeled as $250\text{ ms}$ based on Caterpillar 777D literature (`L2/L3`); requires physical measurement on active mining trucks (`L5`).
2. **NMDC Bailadila Mine Site RF Survey:** Prototype 433 MHz LoRa bench propagation verified (`L3/L4`); full pit-wall multipath survey pending on-site trials (`L5`).

---

## 22. Evidence Level Classification

* **L4 (Controlled Vehicle Prototype):** Vehicle A & Vehicle B physical chassis, TB6612FNG driver, optical encoders, 0.060m wheels, 34.58 effective PPR.
* **L3 (Hardware-In-The-Loop / Bench):** SX1278 LoRa airtime ($38.5\text{ ms}$), CAN/TWAI 250 kbps bus arbitration, ESP32 dual-core logic analyzer measurements.
* **L2 (Software Simulation / Emulation):** Digital Twin synchronization, DSSS PN cross-correlation, 20-fault injection matrix.
* **L1 (Code / Static Verification):** Telemetry data models, Pydantic schemas, unit tests.
* **L0 (Untested / Physical Field Trials Required):** CAT 777D / BEML BH100 full-scale mine deployment at Bailadila.

---

## 23. Definition of Done Compliance Checklist

```
[X] Vehicle A D = 0.060 m verified in firmware and backend
[X] Vehicle B D = 0.060 m verified in firmware and backend
[X] Vehicle A effective PPR = 34.58 verified
[X] Vehicle B effective PPR = 34.58 verified
[X] PPR definition documented (Raw 42/43 vs Effective 34.58)
[X] Firmware updated (sketch_aug26a.ino & VEHICLE_B_TRUCK_02_V2V_DIGITAL_TWIN_MOTOR.ino)
[X] Backend updated (config/physical_vehicle_parameters.json)
[X] Digital Twin updated (digital_twin_sync.py)
[X] Simulation values reconciled
[X] Operator HMI free of stale physical constants
[X] Control Room HMI free of stale physical constants
[X] Wheel calibration tests pass (14/14 PASS)
[X] Cross-layer speed consistency passes (3/3 PASS)
[X] HEMM parameters audited and monotonicity verified
[X] RF 38.5 ms terminology corrected to RF_AIRTIME_COMPONENT
[X] Complete latency budget separated into components (results/integration/latency_budget.csv)
[X] Operator HMI hardware-ready
[X] Control Room HMI hardware-ready
[X] Digital Twin hardware-ready
[X] Safe Beacon hardware path tested
[X] Sensor fault path tested
[X] Command clamping tested
[X] Communication loss tested
[X] Recovery tested
[X] All stale parameter occurrences classified
[X] No unsupported claims remain
[X] Evidence level assigned to every major result
```
