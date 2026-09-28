# PHASE 8 — AUTHORITATIVE CLAIM REGISTER
## FOG-ORCHESTRATOR 2.0 — SIH26007
### Strict Epistemic Classification of System Capabilities & Evidence Boundaries

---

## 1. Classification Scheme

Every capability, parameter, and performance metric is categorized into one of six mutually exclusive evidentiary classes:

- **FACT:** Unambiguous mathematical, logical, or architectural truths verified by deterministic code execution.
- **MEASURED:** Empirically recorded from microcontroller hardware, physical bench timers, or physical transceivers.
- **MODELED:** Numerically integrated from validated Newtonian physical equations.
- **ASSUMED:** Engineering approximations based on mining industry standards, civil design codes, or OEM manuals.
- **SIMULATED:** Emulated synthetic scenarios generated in software without physical hardware in the loop.
- **UNKNOWN:** Physical real-world parameters that cannot be determined without instrumenting an actual production vehicle on site.

---

## 2. Authoritative Phase 8 Claim Register

| ID | System Dimension | Exact Claim Statement | Epistemic Classification | Evidentiary Basis | Known Limitations / Gaps |
|---|---|---|---|---|---|
| **CLR-01** | Safety Invariant | $v_{\text{applied}} \le v_{\text{safe}}$ strictly holds under all operating conditions. | **FACT** | 100% verified across 105 automated HIL scenarios and 1009 regression tests. | Holds for software command path; does not prevent mechanical brake component failure. |
| **CLR-02** | Local Authority | Central fleet dispatch commands cannot override local Tier-1 safety ceilings. | **FACT** | Architectural clamp in `LocalVehicleSafetyGovernor.process_command()`. | Local vehicle controller firmware must be trusted and intact. |
| **CLR-03** | CAN/TWAI Transport | 250 kbps TWAI bus provides 0.512 ms wire transmission and ~12.55 ms round-trip transport. | **MEASURED** | Bench-tested on ESP32 TWAI peripheral registers; logged in CSV. | Measured on lab bench wiring, not inside a high-vibration truck chassis loom. |
| **CLR-04** | J1939 Interoperability | Emulates standard J1939 PGNs (EEC1, CCVS, EBC1, ERC1, PropB) with 29-bit IDs. | **SIMULATED** | Encoded and decoded in Python/C++ CAN emulator. | **NOT** an OEM Cummins/Allison factory proprietary CAN bus interface. |
| **CLR-05** | Vehicle Dynamics | Longitudinal motion of 165.5-tonne hauler on $\pm 8\%$ grade with rolling resistance $C_{rr}=0.02$. | **MODELED** | Newtonian equations of motion in `SimulatedVehicleECU`. | Does not model multi-body suspension pitch, dynamic axle weight transfer, or tyre slip angles. |
| **CLR-06** | Actuator Delay | Electro-pneumatic brake valve delay is modeled with $\tau \in [200, 350]\text{ ms}$. | **MODELED** | Parametric delay filter with watchdog timeout ($500\text{ ms}$). | Not measured on physical BEML BH100 air-over-hydraulic brake booster valves. |
| **CLR-07** | Stopping Deceleration | Emergency braking achieves $2.7856\text{ m/s}^2$; service braking achieves $1.20\text{ m/s}^2$. | **MODEL_DERIVED / ASSUMED** | $2.7856\text{ m/s}^2$ derived from DGMS stopping rules; $1.20\text{ m/s}^2$ engineering assumption. | **UNKNOWN** on wet/muddy NMDC Bailadila iron ore haul roads until dynamometer tested. |
| **CLR-08** | Physical BH100 Braking | Mechanical stopping distance of actual BEML BH100 dump truck at Bailadila. | **UNKNOWN** | None (No physical BEML BH100 truck has been instrumented). | **Prohibited from claiming physical validation.** |
| **CLR-09** | Comm Failover | Complete loss of Gateway and V2V leaves local governor 100% active and fail-safe. | **FACT / DEMONSTRATED** | Proven in Scenario HIL-18 and 90-second evaluator demonstration. | Vehicle operates autonomously on local sensor envelope; dispatch optimization halted. |
| **CLR-10** | Sensor Corruption | Corrupted sensor telemetry (NaN, negative, Inf, frozen) forces fail-safe defensive stop. | **FACT** | Verified in Scenarios HIL-22 to HIL-25; $v_{\text{safe}} = 0.0\text{ m/s}$ in 100% of cases. | Recovery requires explicit reset and sequence resynchronization. |
| **CLR-11** | Operator HMI | Driver cab HUD displays live speeds, visibility, grade, and explicit restriction reason. | **DEMONSTRATED** | Verified via `OperatorHmiBridge` and automated UI tests. | Presentation layer verified; physical cab installation remains a field task. |
| **CLR-12** | RF Security | Forged over-speed central command is clamped; unauthenticated RF permits nuisance STOP. | **FACT** | Verified in HIL adversarial injection tests. | Full cryptographic authentication (HMAC/AES-128) is a planned production hardening step. |
| **CLR-13** | DSSS Modulation | Direct Sequence Spread Spectrum for heavy RF multi-path penetration in open pit. | **SIMULATED** | Modeled in `dsss_gateway_selector.py` with 10.2 dB processing gain. | **NOT** validated on custom physical DSSS ASIC basebands. |

---

## 3. Summary of Negative Knowledge (What We Know We Don't Know)

1. **BEML BH100 Valve Response:** The exact pneumatic valve opening curve, hysteresis, and mechanical brake shoe contact latency on a BH100 are **UNKNOWN**.
2. **True Bailadila Ore Haul Road Adhesion:** True physical friction coefficient $\mu$ across seasonal wet laterite clay and iron ore fines is **ASSUMED** ($\mu \in [0.15, 0.35]$), not measured with a decelerometer on site.
3. **Proprietary J1939 CAN Security:** Whether modern BEML/Cummins haul truck ECUs enforce secure gateway boot or permit external brake torque requests via J1939 PGN 61441 without proprietary diagnostic unlocking is **UNKNOWN**.
