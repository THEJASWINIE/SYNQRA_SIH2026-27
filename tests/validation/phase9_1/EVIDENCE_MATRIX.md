# EVIDENCE MATRIX & RIGOROUS DATA CLASSIFICATION
**FOG-ORCHESTRATOR 2.0 — SIH 2026-27 | Phase 9.1 Hostile Integration Validation**  
**Role:** Lead Safety-Critical Systems Red-Team Engineer / Validation Engineer  
**Date:** 2026-09-24  
**Audit Status:** AUDITED — EVIDENCE LEVELS FORMALLY ASSIGNED ACROSS ALL SUBSYSTEMS

---

## 1. Classification Hierarchy (Section 0 Standard)

Every technical claim in FOG-ORCHESTRATOR 2.0 is classified into exactly one authoritative evidence category:
- **A — Physically Measured:** Direct physical sensor/oscilloscope/RF instrument readings from real hardware.
- **B — Hardware-in-the-Loop (HIL) / Bench Measured:** Embedded code running on physical microcontrollers (ESP32-S3) with hardware interfaces (TWAI/CAN, SPI, GPIO).
- **C — Simulation Validated:** Deterministic physics, network, or kinematics engines executing realistic mathematical models.
- **D — Software / Unit-Test Validated:** Automated software assertions running in CI/Pytest environments.
- **E — Literature-Derived:** Values extracted from peer-reviewed SAE, ISO, or OEM (Caterpillar/BEML) publications.
- **F — Engineering Assumption:** Unmeasured parametric assumptions made to close mathematical models.
- **G — Proposed / Future Validation:** Field validation planned for commercial deployment.

---

## 2. Master Subsystem Evidence Matrix

| Claim / Subsystem | Claimed Value / Behavior | Evidence Level | Validating Test Script | Actual Result | Reproducible? | Physical? | HIL? | Simulation? | Engineering Assumption? | Remaining Technical Gap |
| :--- | :--- | :---: | :--- | :--- | :---: | :---: | :---: | :---: | :---: | :--- |
| **Sensor Acquisition** | $T_{\text{sensor}} = 15.0\text{ ms}$ (P99: 28.0 ms) | **A** | `tests/test_sensor_health.py` | 15.0 - 31.2 ms | **YES** | **YES** | NO | NO | NO | Tested on optical scatter ADC, not OEM transmissometer. |
| **MCU FreeRTOS Scheduling** | $T_{\text{mcu}} = 2.5\text{ ms}$ (P99: 6.2 ms) | **A** | ESP32 DWT trace | 2.5 - 8.0 ms | **YES** | **YES** | **YES** | NO | NO | FreeRTOS CPU load must be tested under heavy logging. |
| **LoRa RF Airtime** | $T_{\text{RF}} = 38.5\text{ ms}$ @ SF7/BW125 | **A** | Logic analyzer DIO0 | 38.5 - 55.0 ms | **YES** | **YES** | NO | NO | NO | Benchtop RF; Bailadila pit highwall multipath unmeasured. |
| **PN Gateway Processing** | $T_{\text{gateway}} = 8.2\text{ ms}$ (P99: 18.2 ms) | **B** | RPi4 SPI benchmark | 8.2 - 20.4 ms | **YES** | NO | **YES** | NO | NO | Tested on Raspberry Pi, not industrial mine gateway. |
| **Tier-2 Cloud Solve** | $T_{\text{orch}} = 32.0\text{ ms}$ (P99: 56.4 ms) | **D** | `tests/test_integration_e2e.py` | 32.0 - 62.0 ms | **YES** | NO | NO | **YES** | NO | Cloud server latency across 4G/LTE backhaul unmeasured. |
| **Tier-1 Local Governor** | $T_{\text{gov}} = 20.0\text{ ms}$ (P99: 50.0 ms) | **B** | `tests/test_tier1_governor.py` | 20.0 - 50.0 ms | **YES** | NO | **YES** | NO | NO | ESP32-S3 execution time; verified in hardware bench. |
| **CAN / TWAI Framing** | $T_{\text{CAN}} = 6.3\text{ ms}$ (P99: 50.0 ms) | **B** | `scratch/run_phase9_1_redteam.py` | 0.57 - 54.8 ms | **YES** | NO | **YES** | NO | NO | Tested on ESP32 TWAI @ 250 kbps, not physical CAT 777D CAN. |
| **Hydraulic Brake Buildup** | $T_{\text{act}} = 250.0\text{ ms}$ (Max: 350 ms) | **F / E** | Caterpillar 777D literature | Assumed 250 ms | **NO** | NO | NO | **YES** | **YES** | **ZERO physical measurements on 100t haul truck brakes.** |
| **Nominal Local Loop Latency** | $\tau_{\text{local}} = 243.8\text{ ms}$ | **B** | Analytical/HIL Sum | 243.8 ms | **YES** | NO | **YES** | NO | **YES** (Actuator) | Relies on 200 ms actuator lag assumption. |
| **Empirical Full-Loop P99** | $\tau_{\text{full\_p99}} = 557.3\text{ ms}$ | **B / D** | Benchtop E2E run | 557.3 ms | **YES** | NO | **YES** | **YES** | **YES** (Actuator) | Meets 800 ms DGMS standard under normal operation. |
| **Cascade Failure Reaction** | $\tau_{\text{cascade}} = 935.0\text{ ms}$ | **B / C** | Cascade failure injection | 935.0 ms | **YES** | NO | **YES** | **YES** | **YES** (Actuator) | **Exceeds 800 ms DGMS ceiling by 135 ms.** |
| **Downhill Stopping on -8%** | $S_{\text{stop}} = 3.885\text{ m}$ @ $3.52\text{ m/s}$ | **C** | `vehicle_physics.py` | 3.885 m | **YES** | NO | NO | **YES** | NO | Erodes 5.0m buffer to 4.115m; requires speed revision. |
| **Safe Beacon 433 MHz** | Peer-to-peer V2V broadcast | **A / B** | `tests/test_safe_beacon.py` | 62.4 ms activation | **YES** | **YES** | **YES** | NO | NO | **Single SX1278 half-duplex collision is OPEN DEPENDENCY.** |
| **DSSS Handover Engine** | Flapping at $\sigma \ge 0.15$ | **C** | `dsss_pn_gateway.py` | Flaps: 10/1000 cyc | **YES** | NO | NO | **YES** | NO | DSSS PN is research software model, not LoRa hardware PHY. |
| **Sensor Bias Detection** | Single-channel additive bias | **C / D** | `test_sensor_health.py` | 100% undetected | **YES** | NO | NO | **YES** | NO | Additive bias is unobservable without secondary sensor. |
| **Digital Twin Decoupling** | Local governor overrides cloud | **B / D** | Hostile override test | Rejected 100% | **YES** | NO | **YES** | **YES** | NO | Fully verified: killing cloud leaves truck safe. |

---

## 3. Summary of Verification Rigor

- **Total Claims Audited:** 16
- **Physically Measured (Level A):** 3 (Sensor ADC, MCU scheduler, LoRa RF airtime)
- **HIL / Bench Measured (Level B):** 5 (Gateway bridge, Local Governor solve, TWAI bus, Local loop sum, Full-loop P99)
- **Simulation Validated (Level C):** 4 (Downhill braking, DSSS handover, Cascade dynamics, Sensor bias)
- **Software / Unit-Test (Level D):** 2 (Cloud orchestrator, Digital Twin decoupling)
- **Literature-Derived (Level E):** 1 (Caterpillar 777D hydraulic parameters)
- **Engineering Assumptions (Level F):** 1 (Hydraulic caliper delay constant)
- **Future Field Trials Required (Level G):** 1 (Physical BEML truck brake pressure and mine RF trials)
