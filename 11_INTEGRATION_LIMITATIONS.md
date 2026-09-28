# 11 — INTEGRATION LIMITATIONS & HARDWARE BOUNDARIES
## FOG-ORCHESTRATOR 2.0 | SIH 2026-27 (Problem Statement: SIH26007)
### NMDC Bailadila Deposit-5 Low-Visibility HEMM Safety System
**Phase 9: Hardware + Software Integration**
**Date:** September 2026 | **Classification:** AUTHORITATIVE LIMITATIONS REGISTRATION

---

## 1. MANDATORY SCIENTIFIC & ENGINEERING HONESTY PRINCIPLE

In strict adherence to the project rules and the Phase 9 Master Mandate:
**DO NOT CLAIM SUCCESS JUST BECAUSE THE SOFTWARE RUNS.**
If a capability or parameter has not been physically validated on live mining equipment, it must be explicitly declared as:
`NOT YET VALIDATED — REQUIRES HARDWARE EXPERIMENT`

---

## 2. EXPLICIT HARDWARE & ARCHITECTURAL LIMITATIONS

### Limitation 1: Physical RF Transceiver is CSS-LoRa, NOT Physical DSSS
- **Physical Reality:** The physical bench prototype uses Semtech SX1278 (Ra-02) 433 MHz transceivers executing Chirp Spread Spectrum (CSS) modulation.
- **Architectural Scope:** The DSSS/PN gateway selection and correlation architecture is an evaluated **research and software simulation model**.
- **Prohibited Claim:** We do NOT claim that physical ESP32 nodes are executing Direct-Sequence spreading sequences at the PHY baseband.
- **Required Future Hardware:** Software-Defined Radios (AD9361 / HackRF) or military-grade DSSS transceivers executing direct hardware PN despreading.

### Limitation 2: Hydraulic Brake Actuator Delay (250 ms) is an Engineering Assumption
- **Physical Reality:** BEML BH100 chassis hydraulic brake fluid pressure build-up timing has **NOT** been measured with high-pressure transducers on a live mining truck.
- **Basis:** Derived from ISO 3450 / SAE J1452 heavy off-highway equipment standards (250 ms nominal, 350 ms worst-case).
- **Prohibited Claim:** We do NOT claim that brake response time has been verified on physical mining vehicle calipers.
- **Required Future Hardware:** Dynamic pressure transducers (0–250 bar) plumbed into BH100 service and retarder brake hydraulic circuits.

### Limitation 3: Actuator Acknowledgment Feedback
- **Physical Reality:** Closed-loop actuator acknowledgment ($t_{\text{ACTUATOR\_ACK}}$) is **UNAVAILABLE** in the physical prototype.
- **Status:** **NOT MEASURED — HARDWARE LIMITATION**.
- **Mitigation:** Local governor models the open-loop worst-case envelope ($350\text{ ms}$) and relies on wheel speed deceleration feedback.

### Limitation 4: Single-Channel Systematic Sensor Bias Unobservability
- **Physical Reality:** If a single optical transmissometer suffers from gradual optical lens contamination or miscalibration and reports $+20\text{ m}$ visibility when true visibility is $5\text{ m}$, this error is **FUNDAMENTALLY UNOBSERVABLE** by statistical single-channel filters.
- **Status:** Documented mathematical limitation.
- **Required Future Hardware:** Dual-wavelength forward scatter sensors paired with solid-state mining LiDAR and automatic lens air-purge systems.

### Limitation 5: Single-Vehicle Field Deployment Scope
- **Physical Reality:** Bench hardware testing validates 2 physical ESP32 vehicle nodes and 1 gateway node communicating over 433 MHz LoRa and Wi-Fi.
- **Evidence Level:** **LEVEL 4 (Bench Hardware Validated)** and **LEVEL 3 (HIL Simulation)**.
- **Prohibited Claim:** We do NOT claim field trial deployment on live open-pit haul ramps at NMDC Bailadila Deposit-5.
- **Required Future Hardware:** Full field pilot test on 5 BEML BH100 dumpers operating on Bailadila Deposit-5 bench haul ramps with DGMS safety observer sign-off.

---

## 3. SUMMARY OF REQUIRED FUTURE HARDWARE EXPERIMENTS

| # | Hardware Experiment Required | Target Subsystem | Required Equipment | Success Criteria |
| :- | :--- | :--- | :--- | :--- |
| **EXP-01** | Physical DSSS Baseband Evaluation | RF Communications | 4x SDR transceivers @ 868/915 MHz | Hardware PN despreading gain $>12\text{ dB}$ |
| **EXP-02** | Hydraulic Brake Caliper Transducer Test | Chassis Braking | High-speed 250-bar pressure transducers | Empirical $t_{\text{actuator}}$ distribution measured |
| **EXP-03** | Dual Optical Transmissometer Cross-Check | Environmental Sensing | 2x Sentry Visibility Sensors + LiDAR | Cross-correlation fault detection under monsoon fog |
| **EXP-04** | J1939 Production CAN Tap Validation | Powertrain Telemetry | Vector CANoe / PEAK CAN Pro on BH100 | Live PGN 61444 & 65265 decoding on haul truck |
| **EXP-05** | Controlled Deposit-5 Ramp Trial | Full Safety System | 2x Instrument BEML BH100 dump trucks | Zero overshoots on -8% grade in dense monsoon fog |
