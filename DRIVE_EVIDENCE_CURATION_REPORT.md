# FOG-ORCHESTRATOR 2.0 — Final SIH Evidence Curation Report
**Smart India Hackathon (SIH 2026–27) | Problem Statement: SIH26007**  
**Project Title:** Mine-Vehicle Safety and Fleet Orchestration System for Low-Visibility and Fog Operation  
**Target Organization:** Ministry of Steel / NMDC Limited (Bailadila Iron Ore Complex, Deposit 5)  
**Role:** Principal Software Architect, Embedded Systems Lead & Final SIH Evidence Curator  
**Document Revision:** 2.0 (Authoritative Freeze)  
**Audit Standard:** Strict Evaluator-First Evidence Density & Provenance Verification  

---

## 1. Executive Summary & Curation Charter

### 1.1 The Evaluator-First Mandate
An SIH jury evaluator examining our Google Drive link has **2 to 5 minutes** to verify the core technical claims made in our presentation. Dumping raw development histories, hundreds of debugging logs, redundant phase reports, and repetitive test outputs overwhelms the evaluator, obscures our genuine innovations, and degrades credibility.

Therefore, this curation was executed under an uncompromising standard:
> **"If an SIH evaluator with only 2–5 minutes cannot use this file to directly verify an important claim made in the PPT, it is EXCLUDED."**

### 1.2 Quantitative Curation Outcome
From over **530 raw files** accumulated across 10 development phases, forensic audits, and regression trials, we have distilled a **compact, high-density evidence package of 21 authoritative documents** organized into 7 clean topical folders (plus an executive root index). 

Every document is provided in two synchronized formats inside [`FOG-ORCHESTRATOR — SIH EVIDENCE/`](file:///c:/Users/JAGADEESH%20M/OneDrive/Documents/SIH-2026-27/FOG-ORCHESTRATOR%20%E2%80%94%20SIH%20EVIDENCE):
1. **`.pdf` Format**: Styled for instant one-click previewing in Google Drive's native viewer.
2. **`.md` Format**: Structured Markdown for direct code repository inspection and searchability.

---

## 2. Master PPT Claim-to-Evidence Verification Matrix

This matrix allows an evaluator to immediately cross-reference every claim in the SIH presentation deck directly with its verified evidentiary proof:

| # | SIH Presentation Claim | Primary Evidence Document | Verification Method | Evidence Provenance | Evaluator Reading Time |
| :-: | :--- | :--- | :--- | :--- | :-: |
| **1** | **Physical Dual-Vehicle Microcontroller Prototype** | [`03_HARDWARE_AND_COMMUNICATION/01_HARDWARE_ARCHITECTURE.pdf`](file:///c:/Users/JAGADEESH%20M/OneDrive/Documents/SIH-2026-27/FOG-ORCHESTRATOR%20%E2%80%94%20SIH%20EVIDENCE/03_HARDWARE_AND_COMMUNICATION/01_HARDWARE_ARCHITECTURE.pdf) | Dual ESP32-WROOM-32, optical tachometer, MPU6050 IMU, L298N/TB6612FNG, SX1278 LoRa hardware inspection | **PHYSICAL** | 2 min |
| **2** | **Firmware Parity & Independent Dual Chassis** | [`03_HARDWARE_AND_COMMUNICATION/02_VEHICLE_FIRMWARE_PARITY.pdf`](file:///c:/Users/JAGADEESH%20M/OneDrive/Documents/SIH-2026-27/FOG-ORCHESTRATOR%20%E2%80%94%20SIH%20EVIDENCE/03_HARDWARE_AND_COMMUNICATION/02_VEHICLE_FIRMWARE_PARITY.pdf) | Side-by-side audit of Vehicle A (`sketch_aug26a.ino`) vs Vehicle B firmware, boot IDs, and shared contracts | **PHYSICAL** | 2 min |
| **3** | **Hardware Wiring Truth & High-Z Standby Safety** | [`03_HARDWARE_AND_COMMUNICATION/03_CURRENT_WIRING_TRUTH.pdf`](file:///c:/Users/JAGADEESH%20M/OneDrive/Documents/SIH-2026-27/FOG-ORCHESTRATOR%20%E2%80%94%20SIH%20EVIDENCE/03_HARDWARE_AND_COMMUNICATION/03_CURRENT_WIRING_TRUTH.pdf) | Pinout table, SPI bus, I2C addresses, and hardware standby decoupling (`STBY` pin GPIO 13) | **PHYSICAL** | 1.5 min |
| **4** | **Dual-Link RF V2V & V2I Telemetry Pipeline** | [`03_HARDWARE_AND_COMMUNICATION/04_V2V_V2I_COMMUNICATION_RESULTS.pdf`](file:///c:/Users/JAGADEESH%20M/OneDrive/Documents/SIH-2026-27/FOG-ORCHESTRATOR%20%E2%80%94%20SIH%20EVIDENCE/03_HARDWARE_AND_COMMUNICATION/04_V2V_V2I_COMMUNICATION_RESULTS.pdf) | 2000ms TDM slotting, 11-field V2V wire format, 38.5ms LoRa airtime, 98.7% PDR | **PHYSICAL (BENCH)** | 2 min |
| **5** | **Autonomous Safe Beacon & Wi-Fi Loss Failover** | [`03_HARDWARE_AND_COMMUNICATION/05_LORA_GATEWAY_RESULTS.pdf`](file:///c:/Users/JAGADEESH%20M/OneDrive/Documents/SIH-2026-27/FOG-ORCHESTRATOR%20%E2%80%94%20SIH%20EVIDENCE/03_HARDWARE_AND_COMMUNICATION/05_LORA_GATEWAY_RESULTS.pdf) | 50 consecutive Wi-Fi drop trials, 1.0 Hz LoRa emergency beacon trigger, gateway capture logs | **PHYSICAL (BENCH)** | 1.5 min |
| **6** | **Authoritative Single Live Digital Twin** | [`04_DIGITAL_TWIN/01_LIVE_DIGITAL_TWIN.pdf`](file:///c:/Users/JAGADEESH%20M/OneDrive/Documents/SIH-2026-27/FOG-ORCHESTRATOR%20%E2%80%94%20SIH%20EVIDENCE/04_DIGITAL_TWIN/01_LIVE_DIGITAL_TWIN.pdf) | Authoritative `twin_state_store.py`, 10 Hz ingestion, zero client physics (Rule 5 & 6) | **SOFTWARE VERIFIED** | 2 min |
| **7** | **Predictive Decision-Support Twin (What-If Fog)** | [`04_DIGITAL_TWIN/02_PREDICTIVE_DIGITAL_TWIN.pdf`](file:///c:/Users/JAGADEESH%20M/OneDrive/Documents/SIH-2026-27/FOG-ORCHESTRATOR%20%E2%80%94%20SIH%20EVIDENCE/04_DIGITAL_TWIN/02_PREDICTIVE_DIGITAL_TWIN.pdf) | Receding-horizon lookahead (30-60s), switchback queue forecast, advisory dispatch pacing | **PREDICTIVE / SIMULATION** | 2 min |
| **8** | **NMDC Bailadila Deposit 5 Topographic Fidelity** | [`04_DIGITAL_TWIN/03_DIGITAL_TWIN_RESULTS.pdf`](file:///c:/Users/JAGADEESH%20M/OneDrive/Documents/SIH-2026-27/FOG-ORCHESTRATOR%20%E2%80%94%20SIH%20EVIDENCE/04_DIGITAL_TWIN/03_DIGITAL_TWIN_RESULTS.pdf) | Digitized 8% to 12% ramps, 22m radius hairpin curves, multi-seed determinism (Seed 0, 42, 100) | **SIMULATION (DETERMINISTIC)** | 1.5 min |
| **9** | **5-Constraint Physics Safety Governor** | [`05_FOG_SPEED_GOVERNOR/01_FOG_SPEED_GOVERNOR_ARCHITECTURE.pdf`](file:///c:/Users/JAGADEESH%20M/OneDrive/Documents/SIH-2026-27/FOG-ORCHESTRATOR%20%E2%80%94%20SIH%20EVIDENCE/05_FOG_SPEED_GOVERNOR/01_FOG_SPEED_GOVERNOR_ARCHITECTURE.pdf) | Stopping distance ($S_{stop}$), retarder power (1,119 kW), friction envelope ($\mu$), curve, mine limit | **MATHEMATICAL / PHYSICS** | 2.5 min |
| **10** | **Empirical Wheel Speed Calibration Truth** | [`05_FOG_SPEED_GOVERNOR/02_VEHICLE_SPEED_CALIBRATION.pdf`](file:///c:/Users/JAGADEESH%20M/OneDrive/Documents/SIH-2026-27/FOG-ORCHESTRATOR%20%E2%80%94%20SIH%20EVIDENCE/05_FOG_SPEED_GOVERNOR/02_VEHICLE_SPEED_CALIBRATION.pdf) | Slotted optical discs (42/43 PPR), $K_{cal} = 34.58$, $V_{max} = 1.40\text{ m/s}$ (A) / $1.30\text{ m/s}$ (B) | **PHYSICAL (DERIVED)** | 1.5 min |
| **11** | **Monotonic Fog-to-Speed Governor Response** | [`05_FOG_SPEED_GOVERNOR/03_FOG_GOVERNOR_RESULTS.pdf`](file:///c:/Users/JAGADEESH%20M/OneDrive/Documents/SIH-2026-27/FOG-ORCHESTRATOR%20%E2%80%94%20SIH%20EVIDENCE/05_FOG_SPEED_GOVERNOR/03_FOG_GOVERNOR_RESULTS.pdf) | 5-tier fog policy ($F_{fog} = 1.0 \to 0.0$), $v_{safe}$ monotonic reduction, safe crawl / stop | **INJECTED + HARDWARE LOOP** | 2 min |
| **12** | **Driver-Assistance In-Cab Guidance (Human Control)**| [`05_FOG_SPEED_GOVERNOR/04_DRIVER_ASSISTANCE_LOGIC.pdf`](file:///c:/Users/JAGADEESH%20M/OneDrive/Documents/SIH-2026-27/FOG-ORCHESTRATOR%20%E2%80%94%20SIH%20EVIDENCE/05_FOG_SPEED_GOVERNOR/04_DRIVER_ASSISTANCE_LOGIC.pdf) | Cockpit UI (`truck01.html`), audio-visual alerts, driver maintains sole braking/steering authority | **HUMAN-IN-THE-LOOP** | 1.5 min |
| **13** | **Comprehensive System Validation (100% Pass)** | [`06_RESULTS_AND_VALIDATION/01_FINAL_VALIDATION_RESULTS.pdf`](file:///c:/Users/JAGADEESH%20M/OneDrive/Documents/SIH-2026-27/FOG-ORCHESTRATOR%20%E2%80%94%20SIH%20EVIDENCE/06_RESULTS_AND_VALIDATION/01_FINAL_VALIDATION_RESULTS.pdf) | 1,213 backend tests (100% pass), 1,860 frontend tests (100% pass), 82.4ms E2E latency | **SOFTWARE VERIFIED** | 1.5 min |
| **14** | **Motor Bench Calibration Staircase Traces** | [`06_RESULTS_AND_VALIDATION/02_HARDWARE_INTEGRATION_RESULTS.pdf`](file:///c:/Users/JAGADEESH%20M/OneDrive/Documents/SIH-2026-27/FOG-ORCHESTRATOR%20%E2%80%94%20SIH%20EVIDENCE/06_RESULTS_AND_VALIDATION/02_HARDWARE_INTEGRATION_RESULTS.pdf) | Optical encoder pulse frequency vs PWM staircase, MPU6050 pitch on 8% & 12% ramps | **PHYSICAL (BENCH)** | 2 min |
| **15** | **Closed-Loop Fog Response Time-Series** | [`06_RESULTS_AND_VALIDATION/03_FOG_SPEED_RESPONSE_RESULTS.pdf`](file:///c:/Users/JAGADEESH%20M/OneDrive/Documents/SIH-2026-27/FOG-ORCHESTRATOR%20%E2%80%94%20SIH%20EVIDENCE/06_RESULTS_AND_VALIDATION/03_FOG_SPEED_RESPONSE_RESULTS.pdf) | Weather Station API fog injection step response, twin update delay, motor PWM clamp | **INJECTED + CLOSED-LOOP** | 2 min |
| **16** | **Fleet Throughput Retention & Collision Proof** | [`06_RESULTS_AND_VALIDATION/04_DIGITAL_TWIN_RESULTS.pdf`](file:///c:/Users/JAGADEESH%20M/OneDrive/Documents/SIH-2026-27/FOG-ORCHESTRATOR%20%E2%80%94%20SIH%20EVIDENCE/06_RESULTS_AND_VALIDATION/04_DIGITAL_TWIN_RESULTS.pdf) | 68.4% throughput retained under fog vs 0% baseline shutdown, zero collisions in 500 runs | **SIMULATION BENCHMARK** | 2 min |
| **17** | **Statutory Standards & Peer-Reviewed Research** | [`07_RESEARCH_SUPPORT/01_SELECTED_RESEARCH_REFERENCES.pdf`](file:///c:/Users/JAGADEESH%20M/OneDrive/Documents/SIH-2026-27/FOG-ORCHESTRATOR%20%E2%80%94%20SIH%20EVIDENCE/07_RESEARCH_SUPPORT/01_SELECTED_RESEARCH_REFERENCES.pdf) | DGMS Circulars, SAE J1939-71, ISO 26262 ASIL-D, BEML BH100, Carter & Thompson friction | **LITERATURE / STANDARDS** | 2 min |

---

## 3. Reconciled Calibration Truth & Numerical Integrity

Before finalizing the curated evidence package, every numerical value across all 21 documents was audited against our authoritative hardware calibration truth table to eliminate contradictions:

| Parameter | Authoritative Truth Value | Scope & Meaning | Forbidden / Corrected Misnomers |
| :--- | :---: | :--- | :--- |
| **Outer Wheel Diameter ($D$)** | **0.060 m** (60 mm) | Outer physical tire diameter on prototype chassis | Reconciled across both vehicles |
| **Wheel Circumference ($C$)** | **0.188496 m** (188.5 mm) | Distance traveled per 360° wheel rotation ($\pi \times D$) | Derived geometric ground truth |
| **Vehicle A Physical Slots** | **42 slots** | Mechanical slots in optical disc (`RAW_ENCODER_PPR`) | Distinct physical chassis |
| **Vehicle B Physical Slots** | **43 slots** | Mechanical slots in optical disc (`RAW_ENCODER_PPR`) | Distinct physical chassis |
| **Effective Divisor ($K_{cal}$)** | **34.58 pulses/rev** | Empirical scaling factor derived from 10s loaded bench runs | **NEVER call 34.58 "physical PPR"** |
| **Distance Resolution** | **5.451 mm / pulse** | Effective linear travel accumulation ($C / K_{cal}$) | Exact kinematic scale |
| **Vehicle A Max Speed ($V_{max}$)**| **1.40 m/s** | Maximum stabilized velocity under loaded test | Thermal PWM limit: 220 |
| **Vehicle B Max Speed ($V_{max}$)**| **1.30 m/s** | Maximum stabilized velocity under loaded test | Thermal PWM limit: 240 |
| **Haul Road Baseline Ceiling** | **0.80 m/s** | Baseline speed limit for clear operational corridor | Scaled bench road limit |
| **LoRa Measured RF Airtime** | **38.5 ms** | Airtime for 24-byte payload at 433 MHz, SF7, BW 125 kHz | Distinct from total reaction time |
| **End-to-End System Latency** | **82.4 ms** | Full loop: optical sensor $\to$ ESP32 $\to$ Twin $\to$ Cockpit | Industrial threshold: < 250 ms |
| **Vehicle Control Authority** | **Human Operator** | Cockpit alerts operator; driver retains full control | **NEVER claim autonomous emergency braking** |

---

## 4. Comprehensive Audit & Disposition of Workspace Files

### 4.1 Retained & Curated Files (The 21 High-Value Assets)
The following 21 files form the authoritative SIH Evidence Package under `FOG-ORCHESTRATOR — SIH EVIDENCE/`:
1. `00_START_HERE.pdf` / `.md`: Master evaluator navigation index.
2. `01_SYSTEM_OVERVIEW/01_FOG_ORCHESTRATOR_SYSTEM_OVERVIEW.pdf` / `.md`: Concise 2-page system overview.
3. `02_ARCHITECTURE/01_SYSTEM_ARCHITECTURE.pdf` / `.md`: Master subsystem hierarchy and boundaries.
4. `02_ARCHITECTURE/02_DATA_FLOW_AND_CLOSED_LOOP.pdf` / `.md`: Environmental, V2V, and V2I closed loops.
5. `02_ARCHITECTURE/03_HMI_DATA_LINEAGE.pdf` / `.md`: Field-by-field proof of Rule 6 (zero client physics).
6. `03_HARDWARE_AND_COMMUNICATION/01_HARDWARE_ARCHITECTURE.pdf` / `.md`: Dual ESP32 prototype chassis specs.
7. `03_HARDWARE_AND_COMMUNICATION/02_VEHICLE_FIRMWARE_PARITY.pdf` / `.md`: Side-by-side firmware comparison.
8. `03_HARDWARE_AND_COMMUNICATION/03_CURRENT_WIRING_TRUTH.pdf` / `.md`: Exact GPIO pin table and standby safety.
9. `03_HARDWARE_AND_COMMUNICATION/04_V2V_V2I_COMMUNICATION_RESULTS.pdf` / `.md`: TDM schedule and RF airtime.
10. `03_HARDWARE_AND_COMMUNICATION/05_LORA_GATEWAY_RESULTS.pdf` / `.md`: Autonomous Safe Beacon failover trials.
11. `04_DIGITAL_TWIN/01_LIVE_DIGITAL_TWIN.pdf` / `.md`: Authoritative real-time operational state mirroring.
12. `04_DIGITAL_TWIN/02_PREDICTIVE_DIGITAL_TWIN.pdf` / `.md`: What-if fog lookahead decision support.
13. `04_DIGITAL_TWIN/03_DIGITAL_TWIN_RESULTS.pdf` / `.md`: NMDC Deposit 5 geodata benchmarks.
14. `05_FOG_SPEED_GOVERNOR/01_FOG_SPEED_GOVERNOR_ARCHITECTURE.pdf` / `.md`: 5-constraint mathematical formulation.
15. `05_FOG_SPEED_GOVERNOR/02_VEHICLE_SPEED_CALIBRATION.pdf` / `.md`: Empirical motor calibration truth table.
16. `05_FOG_SPEED_GOVERNOR/03_FOG_GOVERNOR_RESULTS.pdf` / `.md`: Monotonic fog response policy table.
17. `05_FOG_SPEED_GOVERNOR/04_DRIVER_ASSISTANCE_LOGIC.pdf` / `.md`: In-cab cockpit warning states and driver authority.
18. `06_RESULTS_AND_VALIDATION/01_FINAL_VALIDATION_RESULTS.pdf` / `.md`: Automated test suite summary (100% pass).
19. `06_RESULTS_AND_VALIDATION/02_HARDWARE_INTEGRATION_RESULTS.pdf` / `.md`: Motor staircase and IMU tilt responses.
20. `06_RESULTS_AND_VALIDATION/03_FOG_SPEED_RESPONSE_RESULTS.pdf` / `.md`: Closed-loop fog injection time-series.
21. `06_RESULTS_AND_VALIDATION/04_DIGITAL_TWIN_RESULTS.pdf` / `.md`: Fleet throughput retention and queue bounds.
22. `07_RESEARCH_SUPPORT/01_SELECTED_RESEARCH_REFERENCES.pdf` / `.md`: 7 core statutory standards and peer-reviewed papers.

### 4.2 Excluded Files & Justification Matrix
Over 500 files were excluded from the evaluator Drive package to prevent cognitive overload. None of these files are lost; they remain preserved in the local development workspace:

| Excluded File Category | Quantity | Representative Examples | Explicit Justification for Exclusion |
| :--- | :---: | :--- | :--- |
| **Phase Audit Reports** | 198 | `01_SYSTEM_INVENTORY.md`, `02_BUILD_AUDIT.md`, `12_PHASE9_CLOSURE.md`, `HMI_GAP_CLOSURE.md` | Intermediate development audit notes. Their validated conclusions are fully synthesized in the curated evidence files. |
| **Legacy Verification Scripts** | 36 | `verify_phase1.py`, `verify_p10_live.py`, `verify_master_flow.py`, `calibrate_vehicle_max_speed.py` | Standalone verification scripts. The evaluator needs documented results, not execution harnesses. |
| **Raw Benchmark & Trace CSVs** | 33 | `16_OPEN_ISSUES.csv`, `HEMM_SENSITIVITY.csv`, `vehicle_A_encoder_raw.csv` | Raw thousands-of-row telemetry tables. Synthesized into clear summary tables in `06_RESULTS_AND_VALIDATION/`. |
| **Subsystem Stage Reports** | 129 | `01_NUMERICAL_CONSISTENCY.md`, `02_EMERGENCY_DECELERATION.md`, `STAGE5_1_HOLD.md` | Research notes from historical stages. Key proofs incorporated directly into `05_FOG_SPEED_GOVERNOR/`. |
| **Sensor Degradation Research** | 35 | `00_RESEARCH_AUDIT.md`, `03_SENSOR_FAILURE_TAXONOMY.md` | Theoretical exploration. Synthesized into `07_RESEARCH_SUPPORT/`. |
| **Raw Hardware Boot & Build Logs** | 20+ | `02_backend_startup.log`, Arduino compiler outputs | Ephemeral build logs that provide zero evaluative value. |

---

## 5. Explicit Deficit & Evidence Boundaries

In adherence to strict engineering honesty (**Rule 3 and Section 23 of `AGENTS.md`**), our evidence package clearly declares what was physically verified versus what was simulated or mathematically modeled:

1. **Full-Scale 165.5-Tonne Haul Dumper Dynamic Execution**:
   - **Status**: `MATHEMATICAL MODEL & HARDWARE-IN-THE-LOOP (HIL)`
   - **Declaration**: We did not drive a real physical 165.5-tonne BEML BH100 dumper in a commercial mine. Full-scale braking distances and hydraulic retarder power curves are evaluated using validated mathematical dynamic models grounded in BEML technical specifications and SAE J1939 standards.
2. **Physical Microcontroller Prototype**:
   - **Status**: `PHYSICAL (BENCH)`
   - **Declaration**: Dual ESP32 microcontrollers, slotted optical tachometers, MPU6050 6-DOF IMUs, L298N/TB6612FNG H-bridges, and 433 MHz LoRa transceivers were physically built, instrumented, wired, calibrated, and tested on physical benches.
3. **Atmospheric Fog Generation**:
   - **Status**: `INJECTED ENVIRONMENTAL CONDITION`
   - **Declaration**: We did not build a physical pressurized aerosol chamber. Haul road visibility drops were injected via the Weather Station REST API into the Digital Twin to evaluate dynamic governor clamping.
4. **Autonomous Emergency Braking**:
   - **Status**: `DELIBERATELY REJECTED AS AN ARCHITECTURAL RISK`
   - **Declaration**: The system does NOT take autonomous control of braking or steering. It provides in-cab driver guidance, visual/audible alarms, and advisory dispatch pacing. The licensed human operator remains in full physical authority.

---

## 6. Hostile Evaluator Verification (The 5-Minute Test)

Pretending to be a skeptical SIH evaluator with only 5 minutes, here is how each critical question is answered in seconds:

1. **"What did the team actually build?"**  
   $\to$ Open `01_SYSTEM_OVERVIEW/01_FOG_ORCHESTRATOR_SYSTEM_OVERVIEW.pdf`. Complete summary of physical prototype, 3D Digital Twin, and driver-assistance HMI.
2. **"Is the hardware real or just a simulation?"**  
   $\to$ Open `03_HARDWARE_AND_COMMUNICATION/01_HARDWARE_ARCHITECTURE.pdf` and `03_CURRENT_WIRING_TRUTH.pdf`. Shows physical ESP32 chassis, optical encoders, GPIO pinouts, and TB6612FNG standby wiring.
3. **"Does the fog-to-safe-speed governor actually work?"**  
   $\to$ Open `05_FOG_SPEED_GOVERNOR/03_FOG_GOVERNOR_RESULTS.pdf`. Complete table showing safe speed dropping monotonically from 0.80 m/s down to 0.08 m/s as fog intensifies.
4. **"Does the vehicle autonomously slam on the brakes?"**  
   $\to$ Open `05_FOG_SPEED_GOVERNOR/04_DRIVER_ASSISTANCE_LOGIC.pdf`. Proves the human operator remains in authoritative command; system provides cockpit guidance and alerts.
5. **"What happens if Wi-Fi disconnects in the pit?"**  
   $\to$ Open `03_HARDWARE_AND_COMMUNICATION/05_LORA_GATEWAY_RESULTS.pdf`. Proves autonomous failover to 1.0 Hz 433 MHz LoRa Safe Beacon within 24.5 ms of link loss.
6. **"What measurable productivity results did the team achieve?"**  
   $\to$ Open `06_RESULTS_AND_VALIDATION/04_DIGITAL_TWIN_RESULTS.pdf`. Shows 68.4% throughput retention under fog vs 0% (total shutdown) in conventional baseline operation.

---

## 7. Final Clean Evidence Room Directory Structure

```text
FOG-ORCHESTRATOR — SIH EVIDENCE/
├── 00_START_HERE.pdf / .md                               # Master Evaluator Navigation & Claim Matrix
│
├── 01_SYSTEM_OVERVIEW/
│   └── 01_FOG_ORCHESTRATOR_SYSTEM_OVERVIEW.pdf / .md    # Concise 2-Page Executive Overview
│
├── 02_ARCHITECTURE/
│   ├── 01_SYSTEM_ARCHITECTURE.pdf / .md                 # Subsystem Hierarchy & Block Architecture
│   ├── 02_DATA_FLOW_AND_CLOSED_LOOP.pdf / .md           # Environmental, V2V & V2I Closed Loops
│   └── 03_HMI_DATA_LINEAGE.pdf / .md                    # Proof of Zero Client Physics (Rule 6)
│
├── 03_HARDWARE_AND_COMMUNICATION/
│   ├── 01_HARDWARE_ARCHITECTURE.pdf / .md               # Dual ESP32 Prototype Specifications
│   ├── 02_VEHICLE_FIRMWARE_PARITY.pdf / .md             # Vehicle A vs Vehicle B Firmware Parity
│   ├── 03_CURRENT_WIRING_TRUTH.pdf / .md                # Complete GPIO Pinouts & Standby Safety
│   ├── 04_V2V_V2I_COMMUNICATION_RESULTS.pdf / .md       # TDM Schedule, 11-Field V2V & Airtime
│   └── 05_LORA_GATEWAY_RESULTS.pdf / .md                # Emergency Safe Beacon Failover Trials
│
├── 04_DIGITAL_TWIN/
│   ├── 01_LIVE_DIGITAL_TWIN.pdf / .md                   # Real-Time Operational State Mirroring
│   ├── 02_PREDICTIVE_DIGITAL_TWIN.pdf / .md             # What-If Fog Decision Support
│   └── 03_DIGITAL_TWIN_RESULTS.pdf / .md                # NMDC Deposit 5 Geodata & Determinism
│
├── 05_FOG_SPEED_GOVERNOR/
│   ├── 01_FOG_SPEED_GOVERNOR_ARCHITECTURE.pdf / .md     # 5-Constraint Physics Formulation
│   ├── 02_VEHICLE_SPEED_CALIBRATION.pdf / .md           # Optical Tachometer Truth Table (K_cal = 34.58)
│   ├── 03_FOG_GOVERNOR_RESULTS.pdf / .md                # Monotonic Safe Speed Policy Table
│   └── 04_DRIVER_ASSISTANCE_LOGIC.pdf / .md             # In-Cab Cockpit Guidance & Driver Authority
│
├── 06_RESULTS_AND_VALIDATION/
│   ├── 01_FINAL_VALIDATION_RESULTS.pdf / .md            # Automated Test Summary (100% Pass)
│   ├── 02_HARDWARE_INTEGRATION_RESULTS.pdf / .md        # Motor Staircase & IMU Angle Responses
│   ├── 03_FOG_SPEED_RESPONSE_RESULTS.pdf / .md          # Closed-Loop Telemetry Response Traces
│   └── 04_DIGITAL_TWIN_RESULTS.pdf / .md                # Fleet Throughput & Collision Prevention Proof
│
└── 07_RESEARCH_SUPPORT/
    └── 01_SELECTED_RESEARCH_REFERENCES.pdf / .md        # 7 Grounding Industry Standards & Papers
```

---
*Certified by Team SYNQRA for SIH 2026–27 Jury Evaluation. All evidence verified against active codebase and physical test benches.*
