# FINAL ENGINEERING LIMITATIONS & PROVENANCE BOUNDARIES
## FOG-ORCHESTRATOR 2.0 — SIH 2026-27 (Problem Statement SIH26007)
### Forensic Boundary Audit: What is Validated vs What Remains Unvalidated

---

## 1. Non-Negotiable Research Honesty Rule

In compliance with **Rule 0.3 (No Fabrication)** and **Rule 23 (Honesty About Hardware)** of the project governance rules, this document explicitly details the physical boundaries, engineering assumptions, surrogate models, and operational limitations of FOG-ORCHESTRATOR 2.0.

Under NO circumstances is software simulation or benchtop emulation reported as real-world mine deployment.

---

## 2. Comprehensive Subsystem Boundary Audit

### 2.1 Vehicle Braking & Actuation
- **What Was Tested:** The software command pipeline, local safety governor envelope solver, CAN bus command transmission, and an electro-pneumatic actuator delay model ($\tau \in [200, 350]\text{ ms}$) running in closed-loop HIL simulation.
- **What Remains Surrogate:** The actuator model is a mathematical first-order lag based on SAE J1452 and ISO 3450 literature.
- **What Was NOT Tested:** The project did NOT physically brake a 165.5-tonne BH100, did NOT instrument an actual BH100 hydraulic brake circuit, did NOT measure real truck stopping distance on a -8% mine ramp, did NOT validate actual OEM brake controller behavior, and did NOT validate real OEM retarder commands.
- **Authoritative Limitation Statement:** Brake dynamics were represented through analytical and HIL models; physical brake actuation on a production mining truck remains future validation work.
- **Demonstrated Claim Boundary:** The system demonstrates within the modeled scope that safe commands are generated and transmitted within $216.05\text{ ms}$ median, NOT that physical brake pads contact real steel drums in 216 ms.

### 2.2 CAN / TWAI Bus & J1939 Powertrain Integration
- **What Was Tested:** ESP32 TWAI peripheral connected to an external SN65HVD230 transceiver operating at 250 kbps with 29-bit extended identifiers, encoding and decoding 6 project-defined J1939-compatible PGNs.
- **What Remains Surrogate:** Signal definitions conform to SAE J1939 framing structures (bit packing, PGN addressing, resolution), but were evaluated on a laboratory test bench.
- **What Was NOT Tested:** The system was NOT tapped into the factory wiring harness of an active Cummins QST30 engine ECU, Allison transmission controller, or BEML vehicle management system. OEM proprietary diagnostic seed-key security protocols, bus load contention from secondary chassis sensors, and 24V industrial surge transients remain uncharacterized.
- **Allowed Terminology:** *"project-defined J1939-style HIL frames over ESP32 TWAI at 250 kbps"* or *"J1939-compatible frame structure used in the HIL environment."*
- **Forbidden Terminology:** *"BH100 J1939 integration validated"*, *"Cummins ECU access"*, *"Allison ECU access"*, *"production CAN integration"*.

### 2.3 RF Telemetry & Pit Wireless Propagation
- **What Was Tested:** Dual ESP32 nodes with Semtech SX1278 transceivers operating at 433 MHz, achieving 99.1% packet delivery ratio (PDR) over 150m outdoor line-of-sight (LOS) open terrain with 41.2 ms roundtrip latency.
- **What Remains Surrogate:** Pit-wide radio propagation and deep-pit shadowing were evaluated using empirical log-distance path loss models with shadow fading ($\sigma = 6.5\text{ dB}$) in simulation.
- **What Was NOT Tested:** Physical RF propagation inside an active open-cast iron ore mine pit. Hematite dust attenuation, Fresnel zone obstruction by 15-meter bench highwalls, multipath reflections from massive shovel steel structures, and electrical interference from 6.6 kV electric rope shovels were not physically measured.
- **Demonstrated Claim Boundary:** The system demonstrates **99.1% PDR over 150m outdoor LOS bench conditions**, NOT 99.1% reliability across all mining pits.

### 2.4 Sensor Ingress & Frozen Analog Values (HIL-23)
- **What Was Tested:** Sensor sampling pipeline, IEEE-754 exception handling (`NaN`, `Inf`, negative values), out-of-range plausibility checks (speed $>60\text{ m/s}$, RPM $>8000$), and frame silence timeout watchdogs ($150\text{ ms}$).
- **What Was NOT Tested:** A physical optical/hall wheel speed encoder installed on an actual mining truck wheel hub.
- **Known Limitation Status:** **PARTIAL**. A single-channel sensor repeatedly transmitting a static, plausible value cannot always be distinguished from a valid steady-state signal using only range and timeout checks. Complete frozen-sensor containment requires redundant physical dual-channel sensing and cross-channel plausibility.

### 2.5 Actuator Non-Response Detection (HIL-27)
- **What Was Tested:** Software watchdog monitoring actuator feedback signals. When a command is dispatched but feedback fails to track within 500 ms, the software transitions to `ACTUATOR_FAULT_NON_RESPONSIVE` and clamps the velocity ceiling to $0.0\text{ m/s}$.
- **What Was NOT Tested:** Mechanical seizure containment. If a physical air brake valve mechanically sticks open, software clamping cannot physically stop the vehicle. Real-world fail-safe operation requires redundant dual-circuit air-over-hydraulic brake piping and an independent spring-applied parking brake (emergency maxi-pot).
- **Authoritative Statement:** Software-level actuator non-response detection was demonstrated through the HIL watchdog; physical mechanical seizure containment remains unvalidated.

### 2.6 Autonomy Level & Vehicle Control Scope
- **What Was Tested:** Longitudinal speed advisory, command velocity clamping, origin staging dispatch pacing, and fail-safe deceleration.
- **Scope Boundary:** FOG-ORCHESTRATOR 2.0 is an **Advanced Driver Assistance System (ADAS) / Speed Advisory & Tier-1 Governor Clamp**, NOT a Level 4 or Level 5 autonomous driving system.
- **Steering Control:** Lateral steering and obstacle avoidance remain 100% under the manual control of the human haul truck operator.

---

## 3. Summary Scorecard of Demonstrated Capabilities

| Dimension | Classification | Demonstrated In | Boundary / Unvalidated Element |
|---|---|---|---|
| **Authoritative Local Governor** | `CLASS_B` | Software & Embedded HIL | Firmware must run on uncompromised onboard hardware. |
| **Stopping Distance Physics** | `CLASS_D` | Analytical Math & Monte Carlo | Assumes 1D longitudinal model; lateral tire slip unmodeled. |
| **CAN / TWAI Protocol** | `CLASS_A` | ESP32 Benchtop | Project-defined PGNs; not plugged into live OEM engine bus. |
| **LoRa RF Telemetry** | `CLASS_A` | 150m Outdoor LOS Bench | Mine pit multipath and hematite dust attenuation unmeasured. |
| **Hazardous Ramp Waiting (-77%)**| `CLASS_C` | Matched 20-Seed Shift Sim | Valid for 6-truck closed fleet on Bailadila Deposit-5 ramp model. |
| **Modeled Throughput (+35.9%)** | `CLASS_C` | Matched 20-Seed Shift Sim | Paces delivery to crusher; strictly capped at 1647 TPH ceiling. |
| **Physical Brake Actuation** | `UNVALIDATED` | None (Simulated Surrogate) | Requires physical truck chassis integration and OEM authorization. |
