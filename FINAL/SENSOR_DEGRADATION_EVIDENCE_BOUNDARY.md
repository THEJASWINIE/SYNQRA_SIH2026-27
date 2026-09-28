# SENSOR DEGRADATION EVIDENCE BOUNDARY & PROVENANCE REGISTER
## FOG-ORCHESTRATOR 2.0 — Sensor Degradation Extension
**Project:** SIH26007 — Fog & Low-Visibility Autonomous/Connected Fleet Orchestrator  
**Date:** 2026-09-21  
**Lead Auditor:** Systems Architect & Safety-Critical Verification Lead  
**Audit Standard:** Formal 10-Tier Evidence Hierarchy (L1 to L10). Strict anti-fabrication protocol.

---

## 1. The 10-Tier Evidence Hierarchy

Every claim, parameter, metric, and interface in FOG-ORCHESTRATOR 2.0 is assigned an immutable evidence tier:

| Tier | Name | Definition | Admissible Wording | Prohibited Wording |
|---|---|---|---|---|
| **L1** | Public Verified | Independent public record, physics constant, or law of nature | "governed by", "derived from" | N/A |
| **L2** | OEM Documented | Published manufacturer specification sheet (BEML BH100) | "specified by OEM", "modeled per OEM spec" | "tested on OEM truck", "physically measured on BH100" |
| **L3** | NMDC Documented | Operational safety guideline or standing order published by NMDC | "aligned with NMDC haulage rules" | "formally approved by NMDC" |
| **L4** | Standard | International/National standard specification (ISO, IEC, SAE) | "designed with reference to", "informed by" | "certified under", "ISO compliant" |
| **L5** | Literature | Peer-reviewed academic journal or conference publication | "consistent with findings in [Ref]" | "universally proven" |
| **L6** | Engineering Assumption | Parameter selected by systems engineering team for bounded prototype | "engineering assumption", "nominal parameter" | "empirically proven", "field calibrated" |
| **L7** | Bench / Lab Measured | Measured on physical prototype hardware in laboratory testbench | "bench measured on ESP32", "lab verified" | "field proven", "mine tested" |
| **L8** | Field Measured | Measured in an operating open-cast mine under active production | "field measured in pit" | USED ONLY IF ACTIVE MINE DATA EXISTS (NONE IN THIS REPO) |
| **L9** | Simulation | Derived from mathematical model execution (Monte Carlo / discrete event) | "demonstrated in simulation", "modeled" | "empirically observed", "field performance" |
| **L10** | Unknown / Unverified | Candidate interface or parameter whose physical existence is unverified | "candidate deployment interface", "unverified" | "integrated", "operational" |

---

## 2. Definitive Classification of Repository Components

### 2.1 Hardware Footprint Boundary
| Subsystem / Signal | Actual Physical Status | Evidence Tier | Permitted Statement |
|---|---|---|---|
| **ESP32 Dual-Truck V2V** | Physical hardware running on bench (LoRa + Wi-Fi) | **L7 (Bench Measured)** | Tested on physical ESP32 microcontrollers in laboratory bench setup. |
| **TRUCK_01 Speed** | Physical LM393 optical slot wheel pulse encoder | **L7 (Bench Measured)** | Encoder pulse count converted to SI speed on TRUCK_01 prototype. |
| **TRUCK_02 Speed** | PWM-commanded motor signal (firmware synthetic) | **L9 (Synthetic/Emulated)** | Derived from commanded PWM; NOT an encoder measurement. |
| **MPU6050 IMU** | Physical 6-DOF accelerometer / gyroscope on TRUCK_01 | **L7 (Bench Measured)** | Raw acceleration and angular rate measured on physical board. |
| **GNSS Receiver** | ABSENT on physical prototype (`GNSS_EQUIPPED_VEHICLES = frozenset()`) | **L9 (Simulated Harness)** | No physical GNSS exists on prototype; coordinate inputs are synthetic. |
| **Optical Visibility Sensor** | Central weather telemetry injection; NOT an on-vehicle physical sensor | **L9 (Simulation Input)** | Visibility is modeled as external telemetry from mine weather stations. |
| **BH100 Physical Brakes** | Pneumatic/hydraulic actuators on 165.5-tonne truck | **L2 / L9 (Modeled)** | Modeled using OEM deceleration parameters; zero physical actuation on truck. |
| **BEML BH100 J1939 CAN** | CAN-TWAI frame emulation in laboratory HIL | **L10 (Candidate Interface)** | Candidate deployment protocol; unverified against active BH100 ECU. |

---

### 2.2 Mathematical & Safety Models
| Model Component | Formal Basis | Evidence Tier | Boundary Description |
|---|---|---|---|
| **Quadratic Stopping Envelope ($v_{\text{stop}}$)** | Closed-form Newtonian kinematics | **L1 (Physics Derived)** | Analytically exact solution for $S_{\text{stop}}(v) + S_{\text{base}} \le R_{\text{effective}}$. |
| **Deceleration on $-8\%$ Grade** | Rigid-body dynamic balance | **L1 (Physics Derived)** | Accounts for gravity component opposing deceleration on downhill slope. |
| **Retarder Thermal Dissipation** | Published BEML continuous power limit ($1200\text{ HP}$) | **L2 (OEM Documented)** | Retarder absorption curve analytically limits maximum downhill velocity. |
| **Multi-Constraint Safe Speed Solver** | Deterministic minimum selector ($v_{\text{safe}}$) | **L1 / L4** | Min(v_stop, v_retarder, v_traction, v_curve, v_mine). |
| **Local Vehicle Safety Governor** | Fail-safe clamp ($v_{\text{applied}} \le v_{\text{safe}}$) | **L7 (HIL Validated)** | Verified across 1,009 canonical test vectors and 60 HIL test cases. |

---

### 2.3 Environmental Data Health Layer
| Capability | Detection Mechanism | Evidence Tier | Rigorous Limit |
|---|---|---|---|
| **H1 Freshness ($T_{\text{degraded}}=30\text{s}, T_{\text{stale}}=60\text{s}$)** | Wall-clock elapsed time audit | **L6 / L7 (HIL Tested)** | Guaranteed detection of packet delivery cessation within $30.0\text{ s}$. |
| **H2 Schema & Non-Finite Guard** | Strict type & IEEE-754 finiteness validation | **L1 / L7 (Bench Verified)** | 100% rejection of NaN, +Inf, -Inf, strings, booleans, and malformed structures. |
| **H3 Plausibility Bounds ($[0.5\text{ m}, 2000\text{ m}]$)** | Hard boundary range clamping | **L6 / L7 (Bench Verified)** | Guaranteed rejection of negative, zero, or astronomical visibility values. |
| **H4 Sequence Monotonicity & Rollback** | Bounded sequence window tracker | **L7 (Bench Verified)** | Detects duplicate sequence numbers and backward sequence rollbacks. |
| **H5 Stuck-At Sensor Detection** | Rolling window standard deviation $< 0.05\text{ m}$ | **L6 / L9 (Simulated)** | Detects stuck output after $300\text{ s}$; prone to false alarms in truly constant fog. |
| **H5 Excessive Sensor Noise** | Rolling window standard deviation $> 20.0\text{ m}$ | **L6 / L9 (Simulated)** | Detects sensor noise corruption; degrades confidence to 0.65. |
| **H6 Cross-Source Disagreement** | Dual-source disparity $> 25.0\text{ m}$ | **L9 (Multi-Source Sim)** | Requires two independent physical sensors; inactive on single-source prototype. |
| **Class C (Plausible-But-Wrong)** | Single-source unreferenced measurement | **L10 (UNDETECTABLE)** | Mathematically undetectable by single-source rule layer. Explicitly acknowledged. |

---

## 3. Mandatory Prohibited Statements

The following phrases are permanently forbidden across all project deliverables, documentation, and evaluator presentations:

1. ❌ "Field-tested on BEML dump trucks"
2. ❌ "Guaranteed collision prevention in fog"
3. ❌ "Production-ready ASAMS software"
4. ❌ "Certified compliant with ISO 17757 / ISO 19014 / IEC 61508"
5. ❌ "Real-world mine deployment"
6. ❌ "Physical vehicle braking validated"
7. ❌ "Eliminates haul road queuing"
8. ❌ "Novel AI sensor fusion"

---

## 4. Legitimate Scientific Claims Summary

The defensible claims of FOG-ORCHESTRATOR 2.0 are strictly bounded as follows:

1. **Architecture:** A modular, auditable, rule-based data-health layer safely bridges environmental telemetry and physical stopping distance solvers without bypassing onboard Level 1 safety authority.
2. **Deterministic Clamping:** The local vehicle governor maintains $v_{\text{command}} \le v_{\text{safe}}$ with zero violations across all tested bench and simulation conditions.
3. **Graceful Degradation:** Stale, dropped, or noisy environmental telemetry results in conservative safe speed reductions and controlled staging, substantially mitigating stopping envelope violations under detectable failure modes (eliminating violations in D0, D1, D9, D12, and achieving 96.7% mitigation in D5 and D11).
4. **Transparent Boundaries:** The system explicitly formalizes the boundary where single-source data-health monitoring reaches its mathematical limit (Class C plausible-but-wrong data).
