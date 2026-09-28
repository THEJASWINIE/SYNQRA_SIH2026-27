# REPORT 15 — FINAL EVIDENCE MATRIX & VERIFICATION REGISTER
## FOG-ORCHESTRATOR 2.0 — PHASE 7.3 SCIENTIFIC AUDIT & EVIDENCE FREEZE

| Document ID | Canonical File Path | Date | Audit Status | Version |
| :--- | :--- | :--- | :--- | :--- |
| **REP-15-EVIDMAT** | `reports/15_FINAL_EVIDENCE_MATRIX.md` | 2026-09-18 | **FROZEN / AUDITED** | 2.1.0 |

---

### Master Evidence Matrix (Strict 11-Column Specification)

The following table comprehensively indexes all core engineering claims, mapping each requirement to physical evidence, quantitative metrics, verified confidence levels, and explicit limitations.

**Status Classification Definitions**:
* **GREEN**: Fully supported by reproducible, verifiable evidence within documented prototype, bench, or simulation scope.
* **YELLOW**: Supported by rigorous models, but dependent on engineering assumptions, surrogate hardware, or synthetic data.
* **RED**: Disproven, invalidated by physics, or removed due to scientific indefensibility.
* **OPEN**: Identified as a field-deployment requirement requiring future on-site physical measurement at Bailadila.

```markdown
| ID | Requirement | Claim | Evidence | Evidence Level | Experiment | Metric | Result | Confidence | Limitation | Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **EVM-01** | Vehicle Mass Specification | BEML BH100 Gross Operating Weight is 165,500 kg (74.0 t tare + 91.5 t payload) | BEML OEM Technical Specification Brochure & Mining Equipment Catalog | OEM_DOCUMENTED | Spec Verification | Certified Machine Mass | 165,500 kg GVW (74.0 t tare, 91.5 t rated payload) | VERY_HIGH | Reflects rated factory payload; haulage overloads (up to 105 t) not modeled | **GREEN** |
| **EVM-02** | Haul Road Ramp Grade | Statutory maximum ramp gradient for haul road is 8.0% (1-in-12.5) | DGMS (Tech) Circular No. 09 of 2008 & Coal Mines Regulations | STANDARD_REGULATION | Regulatory Audit | Longitudinal Slope | Grade = -8.0% (Downhill), +8.0% (Uphill) | VERY_HIGH | Localized road washouts or poorly graded switchbacks may exceed 8.0% | **GREEN** |
| **EVM-03** | CAN Bus Transmission Time | J1939 CAN frame wire transmission time is 0.512 ms at 250 kbps | ESP32 TWAI controller laboratory testbed (128 bits / 250 kbps) | BENCH_MEASURED | E1 Bench CAN Test | Wire Transmission Time | 0.512 ms per frame | VERY_HIGH | Measures bit transmission time only; excludes ECU internal queueing | **GREEN** |
| **EVM-04** | Total CAN Delivery Latency | J1939 CAN priority latency bounded by 50.0 ms under heavy 70–80% bus load | ESP32 TWAI bus bench test across 12,000 frames under heavy traffic | BENCH_MEASURED | E1 Bench CAN Test | P99 Delivery Latency | P99 = 24.1 ms (@ 70% load); Bounded ≤ 50.0 ms | HIGH | Measured on laboratory bench; not logged on an active operating BH100 | **GREEN** |
| **EVM-05** | Actuator Response Time | Air-over-hydraulic brake actuator pressure rise averages 200.16 ms | Instrumented pneumatic-hydraulic laboratory surrogate bench apparatus | SURROGATE_BENCH | E2 Actuator Bench Test | Pressure Rise Time | Mean = 200.16 ms, P99 = 237.1 ms, Max = 258.7 ms | HIGH_SURROGATE | Tested on commercial proportional valve; real BH100 actuator stroke unmeasured | **YELLOW** |
| **EVM-06** | Conservative Actuator Scenario | Worst-case cold oil / worn friction actuator latency bounded at 350.0 ms | Analytical sensitivity model incorporating high fluid viscosity and pad travel | ENGINEERING_SCENARIO | Analytical Sensitivity | Actuator Scenario Upper Bound | 350.0 ms | MEDIUM | Retained as conservative boundary; not an ISO 3450 statutory upper limit | **YELLOW** |
| **EVM-07** | Local Safety Loop Latency | Vehicle local emergency stopping reaction latency is 375.0 ms nominal | Decomposed physical sum: Sensor (25ms) + Gov (50ms) + CAN (50ms) + Actuator (250ms) | BENCH_DERIVED | E3 Timing Decomposition | Local Safety Latency (tau_local) | Nominal = 375.0 ms, P99 = 437.1 ms, Worst = 475.0 ms | HIGH | Local loop operates purely onboard; completely independent of cloud/gateway | **GREEN** |
| **EVM-08** | Fleet Loop Latency Decoupling | Central fleet optimization command cycle latency is 685.0 ms | End-to-end cloud pipeline: ESP32 -> LoRa -> Gateway -> Wi-Fi -> FastAPI -> Optimizer | BENCH_MEASURED | E3 Timing Decomposition | Fleet Command Latency (tau_fleet) | P50 = 685.0 ms, P99 = 1,120.0 ms | HIGH | Fleet latency strictly excluded from emergency physical stopping equation | **GREEN** |
| **EVM-09** | Safe Speed Kinematic Envelope | Safe speed recomputed from canonical local latency; stops within sightline | Multi-parameter kinematic solver enforcing S_stop(v) + 5.0m <= R_eff | DERIVED_MODEL | E5 Safe Speed Solver | Safe Operating Speed (v_safe) | 5.12–5.26 m/s (18.4–18.9 km/h) at 12m; 0.00 m/s at 3–5m | VERY_HIGH | Legacy 4.3815 m/s superseded; governed by sightline & available adhesion | **GREEN** |
| **EVM-10** | Physical Crusher Capacity | Maximum steady-state crusher throughput ceiling is 1,647.0 TPH | Analytical calculation: 200s dump cycle per truck = 18 dumps/hr * 91.5 t | PHYSICAL_CALCULATED | Crusher Engineering Audit | Steady-State Capacity | 1,647.0 TPH (Primary Gyratory Crusher) | VERY_HIGH | Single tipping pocket bottleneck; cannot exceed 18 dumps/hr continuously | **GREEN** |
| **EVM-11** | Transient Capacity Flush Artifact | Historical claims of 3,294 TPH are transient queue-flush artifacts | Forensic trace audit of 10-minute dumping spikes after queue release | DISPROVEN_ARTIFACT | E12 Capacity Audit | Transient Peak Throughput | 3,294.0 TPH (6 trucks dumped in 10 min) | DISPROVEN | Transient burst only; physically impossible as sustained mine capacity | **RED** |
| **EVM-12** | Sustained Fleet Production | FOG-Orchestrator delivers 1,591.4 TPH steady-state production under fog | 30-seed closed-loop discrete event simulation under dynamic Bailadila fog | SIMULATION_AUDITED | E10 Fleet Killer Test | Sustained Hourly Throughput | 1,591.4 TPH (96.6% crusher bottleneck utilization) | HIGH_SIMULATION | Verified across 30 random seeds; represents +35.9% gain over Level 0 | **GREEN** |
| **EVM-13** | Hazardous Queue Redistribution | Waiting on hazardous -8% haul ramp reduced by 77.4% (relocated to safe bays) | Closed-loop queue profile tracking across 30 seeds (625.4s -> 141.6s) | SIMULATION_AUDITED | E10 Fleet Killer Test | Hazardous Road Waiting | 141.6 s (Level 4) vs 625.4 s (Level 1) [-77.4%] | HIGH_SIMULATION | Total cycle waiting reduced by -11.6% (-82.8s); road waiting relocated to shovel bay | **GREEN** |
| **EVM-14** | Direct LoRa V2V Link Quality | SX1278 433 MHz CSS-LoRa delivers 99.1% PDR at 150m in open line-of-sight | Laboratory RF bench with calibrated step attenuators across 10,000 packets | BENCH_MEASURED | E6 RF Characterization | Packet Delivery Ratio (PDR) | PDR = 99.1% @ 150m free-space equivalent | HIGH | Tested on laboratory RF bench; open-pit hematite bench multipath unmeasured | **YELLOW** |
| **EVM-15** | Safety Invariant Under RF Loss | Zero overspeed or collision violations occur across 0% to 99% packet loss | Hardware-in-the-loop stress testing: 3,000 commands across 6 loss tiers | HARDWARE_VERIFIED | E7 Loss Invariant Test | Safety Invariant Preservation | 100.0% Preserved (Zero Overspeed / Zero Violations) | VERY_HIGH | Preserved because local governor falls back to v_safe autonomously upon timeout | **GREEN** |
| **EVM-16** | Fail-Safe Fault Reaction Time | Onboard governor detects communication timeout and clamps command in <55 ms | ESP32 hardware timer and watchdog interrupt capture | HARDWARE_VERIFIED | E8 Failure Injection | Fault Detection & Clamp Time | Mean = 52.4 ms, Max = 54.8 ms (Bounded < 100 ms) | VERY_HIGH | Measures onboard software detection; does not include physical vehicle stopping | **GREEN** |
| **EVM-17** | Monte Carlo Operating Envelope | Zero stopping margin violations across 10,000 randomized parameter sets | 10,000-sample numerical simulation varying mass, grade, friction, and latency | MONTE_CARLO | E14 Monte Carlo Run | Stopping Margin Violations | 0 Violations (100.0% safe within parameter space) | VERY_HIGH | Confirms kinematic envelope validity across all specified ranges | **GREEN** |
| **EVM-18** | Controlled Staging in Dense Fog | In 3–5m fog, system safely holds vehicles (v_safe = 0.00 m/s); zero collisions | Kinematic envelope calculation and fleet staging simulation | SIMULATION_AUDITED | E5 & E10 Fog Evaluation | Safe Speed at 3–5m Visibility | v_safe = 0.00 m/s; 100% trucks staged safely | VERY_HIGH | Proves honest safety enforcement; no fake production claimed at zero visibility | **GREEN** |
| **EVM-19** | Pit-Bench Multipath Propagation | Actual Bailadila Deposit-5 RF propagation and multipath attenuation | Requires on-site spectrum analyzer survey across tiered iron ore benches | UNKNOWN_OPEN | Bailadila Pit Survey | In-Situ RF Channel Profile | PENDING FUTURE FIELD MEASUREMENT | OPEN | Cannot claim verified Bailadila pit RF performance without physical site visit | **OPEN** |
| **EVM-20** | In-Situ BH100 Brake Deceleration | Physical wheel-speed and brake pressure telemetry logged from real BH100 | Requires instrumented test on active machine at NMDC Bacheli workshop | UNKNOWN_OPEN | Bacheli Maintenance Depot | Real Chassis Deceleration | PENDING FUTURE FIELD MEASUREMENT | OPEN | Laboratory surrogate bench data must be validated against real BH100 chassis | **OPEN** |
```

---

### Evidence Level Summary Statistics

* **Total Tracked Claims / Metrics**: 20
* **GREEN (Verified & Reproducible)**: 13 (65.0%)
* **YELLOW (Surrogate / Analytical Bound)**: 3 (15.0%)
* **RED (Disproven Historical Artifact)**: 1 (5.0%) — *3,294 TPH transient queue flush*
* **OPEN (Field Deployment Dependency)**: 3 (15.0%) — *In-situ RF, real BH100 brake log, real J1939 ECU sniffing*

All claims presented in official SIH evaluation materials are strictly restricted to **GREEN** and **YELLOW (with explicit qualification)**.
