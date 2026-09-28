# 18 — INTEGRATION LIMITATIONS & HARDWARE BOUNDARIES
## FOG-ORCHESTRATOR 2.0 | SIH 2026-27 (Problem Statement: SIH26007)
### NMDC Bailadila Low-Visibility HEMM Safety & Operational Intelligence System
**Document ID:** `18_INTEGRATION_LIMITATIONS.md`  
**Phase:** 9 — Full Hardware + Software + HMI + Control Room + Digital Twin Integration  
**Date:** September 2026 | **Classification:** AUTHORITATIVE LIMITATIONS REGISTRATION  
**Status:** COMPLETE & FROZEN  

---

## 1. Mandatory Scientific & Engineering Honesty Principle (Section 23 & 36)

In strict adherence to **Rule 3 (Never fabricate telemetry)**, **Rule 23 (Honesty about hardware)**, and **Section 36**:
- **NEVER CLAIM FIELD VALIDATION WITHOUT LIVE MINE FIELD DATA.**
- Every capability, parameter, and test result carries an unambiguous evidence level tag:
  - **L1 Simulation:** Pure mathematical / Monte Carlo simulator.
  - **L2 Software-in-the-Loop:** Distributed backend services, state machine, and algorithms.
  - **L3 Hardware-in-the-Loop:** Microcontroller TWAI CAN bus and RF emulation harness.
  - **L4 Bench Hardware:** Physical ESP32 nodes, Semtech SX1278 transceivers, MPU6050 IMU sensors on testbench.
  - **L5 Controlled Field Test:** Instrument vehicle testing in proving ground or test pit.
  - **L6 Actual Mine Deployment:** Production hauling operations at NMDC Bailadila Deposit-5.

---

## 2. Explicit Hardware & Architectural Boundaries

### Boundary 1: Physical RF Hardware is CSS-LoRa, NOT Physical DSSS
- **Physical Reality (L4):** The physical bench hardware executes **Chirp Spread Spectrum (CSS)** on Semtech SX1278 (Ra-02) 433 MHz transceivers.
- **Research Abstraction (L2):** Direct-Sequence Spread Spectrum (DSSS) with PN code chipping is an evaluated **research and software simulation model**.
- **Prohibited Claim:** We do **NOT** claim that physical ESP32 nodes perform direct hardware PN despreading at the physical radio baseband.
- **Required Future Equipment:** Software-Defined Radios (AD9361 / HackRF) or military-grade DSSS modems.

### Boundary 2: Hydraulic Brake Actuator Buildup Lag is Modeled / Assumed
- **Physical Reality (L3):** BEML BH100 chassis hydraulic caliper pressure buildup has **NOT** been measured with electronic transducers on a live mining haul truck.
- **Basis (L2):** $250.0\text{ ms}$ nominal / $350.0\text{ ms}$ worst-case derived from ISO 3450 / SAE J1452 standards.
- **Prohibited Claim:** We do **NOT** claim that brake hydraulic lag has been empirically measured on physical BH100 brake discs.
- **Required Future Equipment:** 250-bar dynamic pressure transducers plumbed into hydraulic brake lines.

### Boundary 3: Actuator Acknowledgment Feedback
- **Physical Reality:** Closed-loop electronic brake actuator acknowledgment ($t_{\text{ACTUATOR\_ACK}}$) is **UNAVAILABLE** in the prototype bench testbed.
- **Status:** **NOT MEASURED — HARDWARE LIMITATION**.
- **Mitigation:** The Local Safety Governor calculates stopping sightlines using the conservative $350\text{ ms}$ upper bound and verifies deceleration via wheel speed tachometers.

### Boundary 4: Unobservability of Single-Channel Systematic Sensor Bias
- **Physical Reality:** If a single optical transmissometer suffers from gradual optical lens contamination and reports $30\text{ m}$ visibility when true visibility is $8\text{ m}$, this error is **MATHEMATICALLY UNOBSERVABLE** by single-channel statistical filters.
- **Status:** Documented engineering boundary.
- **Required Future Equipment:** Dual-wavelength optical transmissometers combined with solid-state mining LiDAR and automatic lens air-purge systems.

### Boundary 5: Physical Field Trial Scope
- **Physical Reality (L4):** Dual physical ESP32 vehicle nodes communicating with an ESP32 gateway node over 433 MHz LoRa and Wi-Fi.
- **Prohibited Claim:** We do **NOT** claim live open-pit haul ramp deployment on active mine production shifts at NMDC Bailadila Deposit-5.
- **Required Future Equipment:** DGMS-supervised pilot trial on 5 BEML BH100 dump trucks operating in Deposit-5 monsoon fog conditions.

---

## 3. Required Future Hardware Experiments

| ID | Future Experiment Required | Subsystem | Required Equipment | Success Criteria |
|:---|:---|:---|:---|:---|
| **EXP-01** | Physical DSSS Baseband Evaluation | RF Communications | 4x SDR Transceivers (AD9361) | Hardware PN processing gain $>12\text{ dB}$ |
| **EXP-02** | Hydraulic Brake Caliper Transducer Test | Chassis Braking | High-speed 250-bar pressure sensors | Empirical measurement of $t_{\text{actuator}}$ distribution |
| **EXP-03** | Dual Optical Transmissometer Cross-Check | Environmental Sensing | 2x Sentry Visibility Sensors + LiDAR | Cross-correlation fault detection under monsoon fog |
| **EXP-04** | J1939 Production CAN Tap Validation | Powertrain Telemetry | Vector CANoe / PEAK CAN Pro on BH100 | Live PGN 61444 & 65265 decoding on haul truck |
| **EXP-05** | Controlled Deposit-5 Ramp Trial | Full Safety System | 2x Instrument BEML BH100 dump trucks | Zero overshoots on -8% grade in dense monsoon fog |
