# REPORT 16 — SIH EVALUATOR CLAIM SHEET
## FOG-ORCHESTRATOR 2.0 — CANONICAL EVIDENCE & PERFORMANCE SUMMARY
### Problem Statement: Safe & Efficient Operation of Mine Vehicles in Fog (SIH 2026-27 / NMDC Bailadila)

---

### SECTION 1: PROVEN WITHIN PROTOTYPE / SIMULATION SCOPE
*Claims fully substantiated by reproducible hardware testbeds, bench experiments, or audited multi-seed simulation models.*

| # | Claim Statement | Metric Value | Unit | Primary Experiment | Evidence Level | Documented Limitation |
| :- | :--- | :--- | :--- | :--- | :--- | :--- |
| **1** | Safety Invariant Preservation Under Extreme Packet Loss | 100.0 (Zero Overspeed) | % | E7 Loss Invariant Test | HARDWARE_VERIFIED | Local governor autonomously clamps command upon heartbeat timeout; RF communication is degraded, not lossless. |
| **2** | Hardware Fail-Safe Detection & Command Clamping Latency | 52.4 (Max 54.8) | ms | E8 Failure Injection | HARDWARE_VERIFIED | Measures onboard software fault detection and PWM cut-off; does not include physical hydraulic or tire stopping time. |
| **3** | SAE J1939 Physical CAN Transmission Time at 250 kbps | 0.512 | ms | E1 CAN Bench Test | BENCH_MEASURED | Measures raw physical wire transmission of 128-bit frame; excludes ECU task scheduling and buffer queues. |
| **4** | CAN Bus Priority Latency Under 70% Bus Load | 24.1 (Bounded ≤ 50.0) | ms | E1 CAN Bench Test | BENCH_MEASURED | Bench-characterized on ESP32 TWAI testbed; not measured on active production BH100 chassis. |
| **5** | Sustained Mine Haulage Production Under Fog | 1,591.4 | TPH | E10 Fleet Killer Test | SIMULATION_AUDITED | Delivers 96.6% utilization of the primary gyratory crusher bottleneck (1,647.0 TPH) across 30 random seeds. |
| **6** | Relocation of Hazardous Haul Ramp Queue Waiting | -77.4 (625.4 → 141.6) | % (s) | E10 Fleet Killer Test | SIMULATION_AUDITED | Relocates stationary waiting from steep -8% ramp to flat shovel bay; net total cycle delay reduces by -11.6% (-82.8 s). |
| **7** | Monte Carlo Kinematic Safety Invariant Preservation | 0 Violations (10,000 / 10,000) | Count | E14 Monte Carlo Test | MONTE_CARLO | Valid across specified parameter ranges (mass 74–165.5t, grade -8 to +8%, mu 0.25–0.40, tau 0.35–0.48s). |
| **8** | Autonomous Vehicle Staging in Dense Fog (3–5 m Visibility) | 0.00 (100% Staged) | m/s | E5 & E10 Fog Analysis | SIMULATION_AUDITED | In extreme fog (3–5m), stopping distance exceeds sightline; trucks are safely held in bays without fabricating throughput. |

---

### SECTION 2: CONDITIONALLY SUPPORTED
*Claims supported by empirical laboratory surrogate experiments, analytical physical calculations, or engineering sensitivity models.*

| # | Claim Statement | Metric Value | Unit | Primary Experiment | Evidence Level | Documented Limitation |
| :- | :--- | :--- | :--- | :--- | :--- | :--- |
| **9** | Air-over-Hydraulic Actuator Response Time | 200.16 (P99 = 237.1) | ms | E2 Actuator Bench Test | SURROGATE_BENCH | Measured on commercial industrial proportional pneumatic-hydraulic valve; real BH100 brake cylinder displacement unmeasured. |
| **10** | Conservative Actuator Latency Upper Bound | 350.0 | ms | Analytical Sensitivity | ENGINEERING_SCENARIO | Modeled as conservative worst-case for high-viscosity oil and worn linings; not a verified ISO 3450 statutory clause. |
| **11** | SX1278 433 MHz CSS-LoRa Direct V2V PDR at 150 m | 99.1 | % | E6 RF Bench Test | BENCH_MEASURED | Tested with step attenuators representing free-space line-of-sight; pit iron ore reflection and diffraction unmeasured. |
| **12** | Wet Ramp Rolling / Dynamic Friction Boundary | 0.30 (Worst Case 0.25) | Dimensionless | Friction Sensitivity | LITERATURE_SUPPORTED | Derived from literature on saturated iron-ore clay haul roads; dynamic site-specific friction varies with precipitation. |
| **13** | Local Emergency Stopping Reaction Latency | 375.0 (P99 = 437.1) | ms | E3 Timing Decomposition | BENCH_DERIVED | Sum of sensor (25ms), governor (50ms), CAN (50ms), and surrogate actuator (250ms); real ECU cycle times unlogged. |

---

### SECTION 3: REQUIRES FIELD VALIDATION
*Critical operational parameters identified as field dependencies that cannot be validated without physical equipment access at NMDC Bailadila.*

| # | Parameter / Subsystem | Required Field Activity | Target Facility | Field Validation Status |
| :- | :--- | :--- | :--- | :--- |
| **14** | Active Pit RF Multipath & Attenuation Profile | Continuous RF signal logging and spectrum analysis across tiered benches | NMDC Bailadila Deposit-5 Open Pit | **PENDING FIELD MEASUREMENT** |
| **15** | BEML BH100 Full-Stroke Hydraulic Brake Rise | High-speed pressure transducer logging on BH100 front/rear brake ports | NMDC Central Mining Workshop, Bacheli | **PENDING FIELD MEASUREMENT** |
| **16** | Production Machine J1939 ECU Traffic Sniffing | CAN logger capture during active haulage (retarder request, engine brake) | Active Haul Road, Deposit-5 | **PENDING FIELD MEASUREMENT** |
| **17** | In-Situ Heavy Haul Road Dynamic Friction ($\mu$) | Instrumented decelerometer stopping test on wet iron ore haul ramps | South Ramp, Deposit-5 Mine | **PENDING FIELD MEASUREMENT** |
| **18** | Mine-Wide Gateway Mesh RF Coverage | Multi-gateway LoRa coverage survey under dense monsoon and fog conditions | Haul Road Ridge & Crusher Vantage | **PENDING FIELD MEASUREMENT** |

---

### Evaluator Verification Statement
This project strictly rejects performance exaggeration. Throughput gains are bounded by the physical crusher bottleneck ($1,647.0\text{ TPH}$); queue reductions represent spatial redistribution governed by Little's Law; and communication latencies are strictly separated from local vehicle stopping dynamics.
