# FINAL HARDWARE–SOFTWARE INTEGRATION AUDIT REPORT
**FOG-ORCHESTRATOR 2.0 | SIH 2026–27**
**Document Reference:** `FINAL_INTEGRATION_AUDIT_REPORT.md`
**Authoritative Evidence Standard:** DGMS Circular 06/2020 | ISO 3450:2011 | SAE J1939
**Date of Audit Closure:** September 24, 2026

---

## 1. AUDIT OBJECTIVE

This hostile audit was initiated to stress-test, forensic-audit, and attempt to break the integrated FOG-ORCHESTRATOR 2.0 cyber-physical safety architecture following the Phase H1–H11 parameter reconciliations.
The specific mission objectives:
1. Subject every kinematic, RF, timing, and safety parameter to adversarial validation.
2. Uncover and document any parameter drift, unit inconsistencies, or stale legacy constants.
3. Attack the command hierarchy to prove that central dispatch and HMIs cannot bypass the local vehicle Safety Governor.
4. Correct misleading latency terminology (isolating $38.5\text{ ms}$ exclusively to `RF_AIRTIME_COMPONENT`).
5. Enforce rigorous evidence classification (L0 to L5) and retract unsupported claims regarding OEM HEMM and Bailadila field validation.
6. Verify all 14 architectural invariants under hostile failure injection.

---

## 2. SYSTEM UNDER TEST

The audited cyber-physical system spans 5 hierarchical layers:

```
[ PHYSICAL LAYER: Vehicle A (L298N) & Vehicle B (TB6612FNG) with ESP32, Encoders, IMUs, LoRa ]
                                       │ (433 MHz Semtech LoRa V2V & Gateway Uplink)
                                       ▼
[ TELEMETRY & GATEWAY LAYER: Linux Serial Reader, DSSS Selector, PN Correlator, Packet Validator ]
                                       │ (UDP / REST Ingestion Pipeline)
                                       ▼
[ BACKEND ORCHESTRATOR & TWIN CORE: MasterDataModel, UnitConverter, EnvironmentalDataHealth, Twin ]
                                       │ (WebSocket State Broadcasts & Command Clamping)
                                       ▼
[ APPLICATION & DUAL HMI VIEWS: Operator In-Cab HMI, Control Room Fleet HMI, Pygame game_ui.py ]
```

---

## 3. PARAMETER RECONCILIATION

A comprehensive forensic audit scanned 2,883 parameter occurrences across the codebase ([`results/final_audit/repository_parameter_search.csv`](file:///c:/Users/JAGADEESH%20M/OneDrive/Documents/SIH-2026-27/results/final_audit/repository_parameter_search.csv)), establishing a single source of truth:

```
========================================================================================
                      CANONICAL PHYSICAL CALIBRATION PARAMETERS
========================================================================================
  WHEEL DIAMETER (D):             0.060 m (R = 0.030 m)         [FROZEN ON ALL VEHICLES]
  WHEEL CIRCUMFERENCE (C):        0.188495559 m                 [EXACT ANALYTICAL MATH]
  EFFECTIVE CALIBRATION (K_enc):  34.58 pulses/rev              [EMPIRICAL GROUND ROLL]
  DISTANCE PER PULSE:             0.00545100 m/pulse            [C / 34.58]
  VEHICLE A RAW DISK PPR:         42.0 pulses/rev               [HARDWARE OPTICAL SLOTS]
  VEHICLE B RAW DISK PPR:         43.0 pulses/rev               [HARDWARE OPTICAL SLOTS]
  VEHICLE A MOTOR DRIVER:         L298N Dual H-Bridge           [FROZEN]
  VEHICLE B MOTOR DRIVER:         Toshiba TB6612FNG MOSFET      [FROZEN]
  RF AIRTIME COMPONENT:           38.5 ms (SF7/BW125/32B)       [MEASURED L3]
  SAFETY REACTION CEILING:        800.0 ms                      [DGMS STATUTORY LIMIT]
========================================================================================
```

---

## 4. CALIBRATION VERIFICATION

Kinematic equations were mathematically tested from 0 to 1,000,000 pulses and across multiple speed ranges ([`results/final_audit/calibration_consistency.csv`](file:///c:/Users/JAGADEESH%20M/OneDrive/Documents/SIH-2026-27/results/final_audit/calibration_consistency.csv)):
- Distance per mechanical wheel revolution: $C = \pi \times 0.060 = 0.188496\text{ m}$.
- Distance per effective pulse: $d_{\text{pulse}} = 0.188495559 / 34.58 = 0.00545100\text{ m}$.
- At 240 RPM: $v = (240 \times C) / 60 = 0.7540\text{ m/s}$ (both vehicles identical, relative error $0.0024\%$).
- At top prototype speed (445.63 RPM): $v = 1.4000\text{ m/s}$ (relative error $0.0000\%$).
- Over 1,000,000 pulse accumulation: analytical distance $= 5,451.00\text{ m}$, numerical drift $= 0.000\text{ mm}$.

---

## 5. UNIT VERIFICATION

Unit consistency was verified across all active files ([`results/final_audit/unit_consistency.csv`](file:///c:/Users/JAGADEESH%20M/OneDrive/Documents/SIH-2026-27/results/final_audit/unit_consistency.csv)):
1. **Speed:** Explicitly kept in SI units ($\text{m/s}$) for all physical solvers, filters, and safety limits. Conversion to $\text{km/h}$ ($v_{\text{km/h}} = v_{\text{mps}} \times 3.6$) is strictly isolated to UI display views.
2. **Grade:** Civil grade ($G_{\text{civil}} = -8.0\%$) is formally converted to forward longitudinal physics coordinates ($G_{\text{physics}} = -G_{\text{civil}} = +8.0\%$). Slope angle $\theta = \arctan(G_{\text{physics}} / 100) \approx 0.07983\text{ rad}$ ($4.57^\circ$). Never mixed with raw percentages.
3. **Mass:** Prototype chassis ($2.2\text{ kg}$ Truck 01, $1.85\text{ kg}$ Truck 02) separated from full-scale HEMM ($74,000\text{ kg}$ tare, $91,500\text{ kg}$ payload, $165,500\text{ kg}$ GVW).
4. **Time & Delays:** All internal timestamps use UTC epoch seconds; latency durations use milliseconds ($\text{ms}$).

---

## 6. VEHICLE A AUDIT

- **Chassis Architecture:** 4-wheel differential drive, ESP32 NodeMCU.
- **Motor Driver:** L298N Dual H-Bridge (`IN1: 25, IN2: 26, PWM: 27, IN3: 32, IN4: 33, PWM: 14, STBY: 13`).
- **Encoders:** LM393 optical slotted disk, GPIO 35. Hardware disk slots $= 42.0$, calibrated effective factor $= 34.58$.
- **Firmware Status:** [`esp32_code/sketch_aug26a/sketch_aug26a.ino`](file:///c:/Users/JAGADEESH%20M/OneDrive/Documents/SIH-2026-27/esp32_code/sketch_aug26a/sketch_aug26a.ino) compiles cleanly with zero uncalibrated constants.

---

## 7. VEHICLE B AUDIT

- **Chassis Architecture:** 2-wheel differential drive with caster, ESP32 NodeMCU.
- **Motor Driver:** **Toshiba TB6612FNG Dual MOSFET H-Bridge** (`PWMA: 27, AIN1: 25, AIN2: 26, PWMB: 14, BIN1: 32, BIN2: 33, STBY: 13`).
- **Driver Verification:** Hardware standby pin on GPIO 13 verified. All historical L298N mentions for Vehicle B were quarantined to legacy backup files. Regression test strictly prohibits L298N on Vehicle B.
- **Encoders:** LM393 optical slotted disk, GPIO 35. Hardware disk slots $= 43.0$, calibrated effective factor $= 34.58$.
- **Firmware Status:** [`esp32_code/VEHICLE_B_TRUCK_02_V2V_DIGITAL_TWIN_MOTOR/VEHICLE_B_TRUCK_02_V2V_DIGITAL_TWIN_MOTOR.ino`](file:///c:/Users/JAGADEESH%20M/OneDrive/Documents/SIH-2026-27/esp32_code/VEHICLE_B_TRUCK_02_V2V_DIGITAL_TWIN_MOTOR/VEHICLE_B_TRUCK_02_V2V_DIGITAL_TWIN_MOTOR.ino) frozen on TB6612FNG.

---

## 8. BACKEND AUDIT

- **Master Data Model:** [`integration_adapters/master_data_model.py`](file:///c:/Users/JAGADEESH%20M/OneDrive/Documents/SIH-2026-27/integration_adapters/master_data_model.py) acts as the sole authoritative repository of vehicle state.
- **Provenance Enforcement:** Explicitly tracks `HARDWARE`, `SIMULATION`, `DERIVED`, and `HYBRID`. Hardware fields can never be overwritten by simulated mock loops.
- **Unit Converter:** Single backend converter [`integration_adapters/unit_converter.py`](file:///c:/Users/JAGADEESH%20M/OneDrive/Documents/SIH-2026-27/integration_adapters/unit_converter.py) dynamically reads `config/physical_vehicle_parameters.json` and enforces canonical $R = 0.030\text{ m}$.

---

## 9. SENSOR HEALTH AUDIT

- **Diagnostic Filter:** [`integration_adapters/environmental_data_health.py`](file:///c:/Users/JAGADEESH%20M/OneDrive/Documents/SIH-2026-27/integration_adapters/environmental_data_health.py) actively evaluates sensor data stream states: `VALID`, `DEGRADED`, `STUCK`, `OUTLIER`, `STEP_DISCONTINUITY`, `UNAVAILABLE`.
- **Conservative Safety Floor:** When visibility sensor drops or spikes to impossible values ($5000\text{ m}$), system immediately clamps to the conservative $8.0\text{ m}$ floor.
- **Degradation Propagation:** Sensor faults propagate deterministically to the Safety Governor, which forces vehicle deceleration or standstill crawl.

---

## 10. RF AUDIT

- **Gateway Selector:** [`integration_adapters/dsss_gateway_selector.py`](file:///c:/Users/JAGADEESH%20M/OneDrive/Documents/SIH-2026-27/integration_adapters/dsss_gateway_selector.py) employs a $+0.15$ score hysteresis margin and 3-frame persistence debounce to eliminate gateway ping-pong flapping.
- **Link State Machine:** Seamlessly transitions across `CONNECTED`, `DEGRADED`, and `COMMUNICATION_LOSS`.
- **Recovery Persistence:** Single transient packets cannot exit failsafe mode. Multi-packet confirmation is strictly required to restore `NORMAL`.

---

## 11. SAFE BEACON AUDIT

- **Failsafe Controller:** [`failsafe/safe_beacon.py`](file:///c:/Users/JAGADEESH%20M/OneDrive/Documents/SIH-2026-27/failsafe/safe_beacon.py) monitors gateway heartbeat.
- **Autonomous Activation:** Upon $500\text{ ms}$ silence (or $200\text{ ms}$ in dense fog), standalone Safe Beacon mode engages at 2.0 Hz broadcast.
- **Actuation Isolation Verified:** Inspection of Safe Beacon code proves zero motor actuator register access. Safe Beacon broadcasts RF status frames only; motor deceleration is commanded strictly by the vehicle's local failsafe controller.

---

## 12. SAFETY GOVERNOR AUDIT

- **Hierarchical Priority:** Local Tier-1 Safety Governor ([`integration_adapters/fail_safe_controller.py`](file:///c:/Users/JAGADEESH%20M/OneDrive/Documents/SIH-2026-27/integration_adapters/fail_safe_controller.py)) remains unconditionally authoritative over central commands:
  $$v_{\text{command}} = \min(v_{\text{dispatch}}, v_{\text{safe}})$$
- **Adversarial Resilience:** Tested against excessive ($15.0\text{ m/s}$), negative ($-10.0\text{ m/s}$), NaN, infinity, and stale timestamps. In all cases, commands were rejected or safely clamped within the physical stopping ceiling.

---

## 13. OPERATOR HMI AUDIT

- **Role:** Pure presentation and driver advisory layer.
- **Live State Consumption:** Receives live projected state via WebSocket. Does NOT calculate braking distance, friction, or safe speed independently.
- **Separation of Concerns:** Displays requested speed, safe speed limit, and actual applied command in distinct fields to make safety clamping visible to the operator.
- **Staleness Protection:** If telemetry age exceeds $600\text{ ms}$, speed displays are masked with dashes and watermarked `DATA STALE`.

---

## 14. CONTROL ROOM HMI AUDIT

- **Fleet Observability:** Aggregates multi-vehicle telemetry, gateway signal metrics (RSSI, SNR), Safe Beacon states, and system health.
- **Bypass Prevention:** Dispatchers can send target speeds, but commands flow through the central Safety Governor and local vehicle governor. Central dispatch cannot override vehicle safety.
- **Multi-Vehicle Isolation:** Unsafe or degraded conditions on `TRUCK_01` do not contaminate `TRUCK_02`.

---

## 15. DIGITAL TWIN AUDIT

- **Authoritative Mirror:** Synchronizes with backend state stream in `LIVE_MIRROR` mode.
- **Safety Boundary Enforcement:** In `WHAT_IF`, `REPLAY`, and `FAULT_INJECTION` modes, physical command generation is blocked (`can_issue_physical_command() == False`).
- **Isolation Resilience:** Disconnecting or crashing the Digital Twin has zero impact on physical vehicle safety.

---

## 16. CAN / J1939 AUDIT

- **Scope Clarification:** The project implements a **CAN / J1939-compatible abstraction layer** on ESP32 TWAI transmitting 29-bit extended frames at 500 kbps.
- **Honesty Demarcation:** The system has **NOT been plugged into an active OEM production HEMM** (Caterpillar 777D or BEML BH100). All claims claiming "OEM machine validated" have been downgraded to `L3 (CAN/TWAI Prototype Validated)`.

---

## 17. LATENCY AUDIT

- **Terminology Corrected:** $38.5\text{ ms}$ is strictly designated `RF_AIRTIME_COMPONENT`.
- **Budget Decomposition:** Full 14-stage latency budget cataloged in [`results/final_audit/latency_budget.csv`](file:///c:/Users/JAGADEESH%20M/OneDrive/Documents/SIH-2026-27/results/final_audit/latency_budget.csv).
- **Prototype Response:** Measured local loop reaction $= 37.3\text{ ms}$; full remote command loop $= 124.4\text{ ms}$ (L3 Evidence).
- **HEMM Full Scale:** Modeled hydraulic pressure rise ($250.0\text{ ms}$) brings total estimated response to $424.4\text{ ms}$ under normal operation.

---

## 18. FAULT INJECTION

The 20-fault matrix (F01–F20) in [`tests/fault_injection/test_fault_matrix_f01_f20.py`](file:///c:/Users/JAGADEESH%20M/OneDrive/Documents/SIH-2026-27/tests/fault_injection/test_fault_matrix_f01_f20.py) and adversarial attacks in [`tests/integration/test_final_hostile_attacks.py`](file:///c:/Users/JAGADEESH%20M/OneDrive/Documents/SIH-2026-27/tests/integration/test_final_hostile_attacks.py) verified 100% deterministic safety transitions:
- RF Loss $\rightarrow$ Failsafe Safe Beacon ($500\text{ ms}$).
- Sensor Outlier / Loss $\rightarrow$ Conservative $8.0\text{ m}$ visibility floor.
- Hardware E-Stop $\rightarrow$ TB6612 STBY pin LOW in $1.2\text{ ms}$.
- CAN Silence $\rightarrow$ Watchdog timeout in $300\text{ ms}$.

---

## 19. CROSS-LAYER CONSISTENCY

Snapshot verification across ESP32, Backend, Operator HMI, Control Room HMI, and Twin showed **0.0% parameter drift** ([`results/final_audit/cross_layer_truth.csv`](file:///c:/Users/JAGADEESH%20M/OneDrive/Documents/SIH-2026-27/results/final_audit/cross_layer_truth.csv)). All 18 key metrics (speed, safe speed, commanded speed, grade, visibility, link state, sensor health, safety state) matched across all views within allowable network display latency.

---

## 20. EVIDENCE CLASSIFICATION

All project artifacts and claims are classified strictly per the 6-level evidence taxonomy ([`results/final_audit/evidence_audit.csv`](file:///c:/Users/JAGADEESH%20M/OneDrive/Documents/SIH-2026-27/results/final_audit/evidence_audit.csv)):
- **L0 (Untested):** Physical Bailadila open-pit deployment.
- **L1 (Code / Static):** ISO 3450 braking formulas, DGMS 800ms standard, geometric derivations.
- **L2 (Software Simulation):** Digital Twin scenario engine, 20-fault injection suite, Monte Carlo models.
- **L3 (HIL / Benchtop):** Semtech SX1278 RF airtime ($38.5\text{ ms}$), ESP32 TWAI CAN bus ($2.4\text{ ms}$), TB6612FNG oscilloscope measurements.
- **L4 (Controlled Vehicle Prototype):** Dual ESP32 chassis wheel calibration ($D = 0.060\text{ m}$, $K_{\text{enc}} = 34.58$), differential drive ground tests.
- **L5 (Actual Mine Field):** None claimed. Marked pending physical mine trials.

---

## 21. UNSUPPORTED CLAIMS FOUND

A ruthless review of historical documentation identified 4 unsupported or ambiguous claims ([`results/final_audit/claim_audit.csv`](file:///c:/Users/JAGADEESH%20M/OneDrive/Documents/SIH-2026-27/results/final_audit/claim_audit.csv)):
1. *Claim:* "Bailadila Deposit 5 mine validated." $\rightarrow$ **UNSUPPORTED.** Only simulated with mine elevation contours.
2. *Claim:* "OEM production HEMM J1939 validated." $\rightarrow$ **UNSUPPORTED.** Only tested on benchtop TWAI / CANoe emulator.
3. *Claim:* "38.5 ms worst-case end-to-end command latency." $\rightarrow$ **MISLABELED.** Represents RF airtime component only.
4. *Claim:* "108.74 ms measured stopping response." $\rightarrow$ **UNSUPPORTED.** Single row in Monte Carlo simulation dataset.

---

## 22. CORRECTIONS MADE

1. Isolated `RF_AIRTIME_COMPONENT = 38.5 ms` across all active documentation and test assertions.
2. Updated terminology from "OEM HEMM Validated" to "CAN/TWAI 29-bit J1939 Abstraction (L3 Bench)".
3. Renamed Bailadila claims to "NMDC Bailadila Deposit 5 Haulage Reference Model (Simulated L2)".
4. Clarified $34.58$ as an empirical calibration coefficient rather than raw hardware encoder PPR.
5. Added automated adversarial test suite proving command clamping and actuation isolation.

---

## 23. REMAINING FAILURES

- **Pytest Suite:** 1,189 PASSED, 0 FAILED.
- **1 Skipped Test:** `tests/test_defect_002_curve_radius.py` (quarantined upstream test fixture pending curve radius benchmark update).
- **Active Code Defects:** **ZERO.**

---

## 24. REMAINING PHYSICAL VALIDATION

The following milestones require physical access and are documented as open physical engineering tasks:
1. Physical deployment of 433 MHz gateway masts in an active open-pit mine (Bailadila benches) to evaluate non-line-of-sight multipath and rockface diffraction.
2. Physical J1939 CAN transceiver connection into the electronic control system of an operating BEML BH100 or Caterpillar 777D dumper.
3. Physical pressure transducer instrumentation on mining dumper hydraulic brake calipers to record actual fluid line rise time.

---

## 25. HOSTILE JUDGE QUESTIONS

All 20 hostile judge questions have been fully answered with empirical citations, test results, evidence levels, and documented physical boundaries in Section 8 of [`docs/FINAL_HOSTILE_AUDIT.md`](file:///c:/Users/JAGADEESH%20M/OneDrive/Documents/SIH-2026-27/docs/FINAL_HOSTILE_AUDIT.md).

---

## 26. FINAL ENGINEERING POSITION

The FOG-ORCHESTRATOR 2.0 system has successfully survived the hostile hardware-software integration audit. Every physical parameter is reconciled to a single canonical value, units are rigorously consistent, and safety is strictly distributed and authoritative on the vehicle.

### Final Traffic-Light Verdict Matrix

```
========================================================================================
                               FINAL AUDIT STATUS VERDICT
========================================================================================

  [ GREEN ] VERIFIED & REPRODUCIBLE (L1 / L2 / L3 / L4):
    - Wheel Calibration: D = 0.060 m, Effective PPR = 34.58 (0 drift across 1,000,000 pulses)
    - Vehicle Separation: Vehicle A (L298N) and Vehicle B (TB6612FNG) pinouts and drivers
    - Local Safety Governor: Clamps all malicious, extreme, negative, and stale commands
    - Sensor Diagnostics: Conservative 8.0 m visibility floor under failure
    - Gateway Selection: DSSS correlation score, +0.15 margin hysteresis, 3-frame debounce
    - Safe Beacon: Autonomous comm loss fallback at 2.0 Hz; 100% motor actuation isolation
    - Digital Twin Safety Boundary: Blocks physical actuation in WHAT_IF and REPLAY modes
    - RF Airtime Component: 38.5 ms verified via DSO / Semtech LoRa calculations
    - Cross-Layer Parity: 18 metrics match across ESP32, Backend, Operator, Control Room, Twin
    - Automated Regression: 1,189 PASS, 1 SKIPPED, 0 FAILURES

  [ YELLOW ] PROTOTYPE / HIL / CONTROLLED VALIDATION ONLY (L3 / L4):
    - CAN / TWAI J1939 Framing: Validated on ESP32 TWAI bus + Saleae Logic Analyzer
    - Small Chassis Dynamics: Measured on 2.2 kg and 1.85 kg DC motor prototype chassis
    - Lab-Bench RF Propagation: Measured over laboratory line-of-sight distances

  [ RED ] REQUIRES FIELD / PHYSICAL VALIDATION (L0):
    - Full-Scale OEM HEMM J1939 Interface: Tapping physical ECM/TCU of active 100t dumper
    - Full-Scale Hydraulic Brake Buildup: Physical pressure logging on OEM brake lines
    - Bailadila Open-Pit Field Validation: Physical RF coverage trials across mine benches
========================================================================================
```
