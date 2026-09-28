# FOG-ORCHESTRATOR 2.0 — SIH EVALUATOR EVIDENCE PACKAGE
**Smart India Hackathon (SIH 2026-27) | Problem Statement: SIH26007**
**Theme:** Mine-Vehicle Safety and Fleet Orchestration System for Low-Visibility and Fog Operation
**Target Organization:** Ministry of Steel / NMDC Limited (Bailadila Complex, Deposit 5)

---

## 1. Executive Summary & Evaluator Quick Start

In heavy open-cast mining operations, dense seasonal valley fog regularly reduces sightline visibility to **under 15 meters**. Standard haulage speeds for 165.5-tonne BEML BH100 haul dumpers require emergency stopping distances of **35 to 50 meters** on 8% to 12% downhill grades. Mine operators are forced to either operate blindly (severe collision risk) or halt production entirely (costing millions of INR per hour).

**SYNQRA / FOG-ORCHESTRATOR 2.0** solves this crisis through an integrated cyber-physical architecture:
1. **Physical Prototype**: Dual ESP32 vehicles with optical wheel tachometers, MPU6050 IMU, L298N/TB6612FNG H-bridges, 433 MHz LoRa, and SAE J1939 CAN interfaces.
2. **Authoritative 3D Digital Twin**: Geospatially synchronized 3D model of NMDC Bailadila Deposit 5 haul roads, road friction, grades, and real-time fleet dynamics.
3. **5-Constraint Physics Safety Governor**: Computes continuous, monotonic safe speed limits based on stopping distance, road friction, retarder power, switchback radius, and mine regulations.
4. **Driver-Assistance In-Cab Guidance**: Color-coded cockpit console (`truck01.html`, `truck02.html`) providing real-time speed guidance and audible warnings. **The driver remains in full physical control**; the system advises rather than autonomously braking.
5. **Dual-Link RF Communication**: 433 MHz LoRa peer-to-peer V2V and 2.4 GHz Wi-Fi V2I with automatic Safe Beacon failover.

---

## 2. PPT Claim-to-Evidence Verification Matrix

Use this index to verify every claim made in our presentation directly in the evidence room:

| PPT Claim / Feature | Primary Evidence Document | Verification Method | Evidence Provenance |
| :--- | :--- | :--- | :--- |
| **Physical Microcontroller Prototype** | `03_HARDWARE_AND_COMMUNICATION/01_HARDWARE_ARCHITECTURE.pdf` | Dual ESP32, optical encoder, IMU, LoRa, H-bridge hardware inspection | **PHYSICAL** |
| **Firmware Parity & Independent Dual Chassis** | `03_HARDWARE_AND_COMMUNICATION/02_VEHICLE_FIRMWARE_PARITY.pdf` | Side-by-side firmware audit (`sketch_aug26a.ino` vs Vehicle B) | **PHYSICAL** |
| **Complete Wiring & Pin Assignments** | `03_HARDWARE_AND_COMMUNICATION/03_CURRENT_WIRING_TRUTH.pdf` | GPIO mapping, pull-downs, SPI bus, H-bridge truth tables | **PHYSICAL** |
| **Dual-Link V2V & V2I Telemetry** | `03_HARDWARE_AND_COMMUNICATION/04_V2V_V2I_COMMUNICATION_RESULTS.pdf` | TDM schedule, 11-field V2V packets, 38.5 ms LoRa airtime | **PHYSICAL (BENCH)** |
| **LoRa Gateway & Autonomous Safe Beacon** | `03_HARDWARE_AND_COMMUNICATION/05_LORA_GATEWAY_RESULTS.pdf` | RSSI/SNR metrics, Wi-Fi loss trigger, 1 Hz emergency beacon | **PHYSICAL (BENCH)** |
| **Authoritative Live Digital Twin** | `04_DIGITAL_TWIN/01_LIVE_DIGITAL_TWIN.pdf` | Single authoritative state store, 10 Hz telemetry sync | **SOFTWARE VERIFIED** |
| **Predictive Decision-Support Twin** | `04_DIGITAL_TWIN/02_PREDICTIVE_DIGITAL_TWIN.pdf` | What-if fog lookahead, queueing prediction, advisory dispatch | **PREDICTIVE / SIMULATION** |
| **Geospatial NMDC Deposit 5 Twin Results** | `04_DIGITAL_TWIN/03_DIGITAL_TWIN_RESULTS.pdf` | Digitized Bailadila 8-12% ramps, multi-seed determinism | **SIMULATION (DETERMINISTIC)**|
| **5-Constraint Physics Safety Governor** | `05_FOG_SPEED_GOVERNOR/01_FOG_SPEED_GOVERNOR_ARCHITECTURE.pdf` | Stopping sight distance, retarder thermal limits, friction envelope | **MATHEMATICAL / PHYSICS** |
| **Empirical Speed Calibration Truth** | `05_FOG_SPEED_GOVERNOR/02_VEHICLE_SPEED_CALIBRATION.pdf` | Optical encoder staircase, $K_{cal}=34.58$, 42/43 disc PPR | **PHYSICAL (DERIVED)** |
| **Monotonic Fog Speed Response** | `05_FOG_SPEED_GOVERNOR/03_FOG_GOVERNOR_RESULTS.pdf` | 5-tier fog policy ($F_{fog} 1.0 \to 0.0$), safe crawl/stop behavior | **INJECTED + HARDWARE LOOP** |
| **Driver-Assistance In-Cab Guidance** | `05_FOG_SPEED_GOVERNOR/04_DRIVER_ASSISTANCE_LOGIC.pdf` | Cockpit UI, warnings, driver in control (no autonomous braking) | **SOFTWARE / HUMAN-IN-LOOP** |
| **Master System Verification Summary** | `06_RESULTS_AND_VALIDATION/01_FINAL_VALIDATION_RESULTS.pdf` | 1,213 backend tests (100% pass), 1,860 frontend tests (100% pass) | **SOFTWARE VERIFIED** |
| **Hardware Bench Calibration Traces** | `06_RESULTS_AND_VALIDATION/02_HARDWARE_INTEGRATION_RESULTS.pdf` | Motor staircase calibration curves, PWM ceilings (220 / 240) | **PHYSICAL (BENCH)** |
| **Closed-Loop Fog Response Traces** | `06_RESULTS_AND_VALIDATION/03_FOG_SPEED_RESPONSE_RESULTS.pdf` | Weather API injection, twin transition, safe speed clamp latency | **INJECTED + CLOSED-LOOP** |
| **Fleet Productivity Retention Metrics** | `06_RESULTS_AND_VALIDATION/04_DIGITAL_TWIN_RESULTS.pdf` | 68.4% throughput retained in fog vs 0% baseline shutdown | **SIMULATION BENCHMARK** |
| **Standards & Research Grounding** | `07_RESEARCH_SUPPORT/01_SELECTED_RESEARCH_REFERENCES.pdf` | DGMS circulars, SAE J1939-71, ISO 26262, BEML BH100 curves | **LITERATURE / STANDARDS** |

---

## 3. Five-Minute Evaluator Navigation Order

If you have only 5 minutes to audit our solution, we recommend reviewing in this order:
1. **Start Here**: Review the claim table above to identify the specific component under evaluation.
2. **01_SYSTEM_OVERVIEW/01_FOG_ORCHESTRATOR_SYSTEM_OVERVIEW.pdf**: Understand the end-to-end solution in 2 pages.
3. **03_HARDWARE_AND_COMMUNICATION/01_HARDWARE_ARCHITECTURE.pdf**: Inspect the physical dual-vehicle prototype.
4. **05_FOG_SPEED_GOVERNOR/03_FOG_GOVERNOR_RESULTS.pdf**: Verify how environmental fog decreases safe speed monotonically.
5. **06_RESULTS_AND_VALIDATION/01_FINAL_VALIDATION_RESULTS.pdf**: Verify test pass rates, latencies, and physical data provenance.
