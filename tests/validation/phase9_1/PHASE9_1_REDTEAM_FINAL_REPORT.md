# MASTER RED-TEAM FINAL AUDIT REPORT
**FOG-ORCHESTRATOR 2.0 — SIH 2026-27 | PHASE 9.1 HOSTILE INTEGRATION VALIDATION**  
**Lead Authors:** Lead Safety-Critical Systems Red-Team Engineer, HEMM Controls Engineer, CAN/J1939 Engineer, RF Systems Engineer, Distributed Systems Engineer, Digital-Twin Validation Engineer, and Hostile SIH Judge Panel  
**Date:** 2026-09-24  
**Audit Standard:** Strict Non-Negotiable Source-of-Truth & Evidence Hierarchy (Levels A–G)  
**Overall Project Score:** **OMITTED PER RED-TEAM CHARTER (RULE 21)**

---

## 1. Executive Summary

Phase 9.1 represents the hostile validation and claim-breaking phase of the FOG-ORCHESTRATOR 2.0 mining safety architecture. Rather than executing tests designed to confirm success, this red-team audit systematically applied maximum mechanical, electrical, RF, and distributed systems stress to expose the **exact boundaries where the system breaks**.

### Core Findings
1. **The Core Physical Fail-Safe Architecture Is Robust:** Under no circumstances can cloud failures, gateway dropouts, or malicious dispatch commands override the physical onboard Tier-1 safety governor. When communication is severed, the vehicle executes an autonomous fail-safe stop.
2. **Hydraulic Caliper Lag Is the Dominant Unmeasured Risk:** While digital electronics and CAN arbitration complete within $\approx 50\text{ ms}$, assumed hydraulic brake buildup ($250 - 350\text{ ms}$) accounts for over **60% of the reaction time**.
3. **Downhill Stopping Buffer Erosion Discovered:** On a $-8\%$ downhill haul ramp with wet friction ($\mu = 0.35$), the canonical crawl speed of $3.52\text{ m/s}$ in $8.0\text{ m}$ visibility results in a stopping distance of $3.885\text{ m}$. While physical collision is prevented, the claimed $5.0\text{ m}$ safety buffer is eroded to $4.115\text{ m}$ (shortfall: $88.5\text{ cm}$).
4. **Cascade Timing Breach Identified:** Under simultaneous comm loss and blindout, waiting for the $500\text{ ms}$ remote heartbeat timeout pushes total brake engagement to **$935.0\text{ ms}$**, exceeding the DGMS 800 ms ceiling by $135.0\text{ ms}$.
5. **Open RF Safety Dependency Declared:** Prototype operation of both primary telemetry and Safe Beacon on a single half-duplex 433 MHz SX1278 transceiver creates co-channel receiver blocking during beacon transmissions.

---

## 2. What Survived the Attack

1. **Tier-1 Local Safety Authority:** Injected malicious cloud overrides ($v_{\text{dispatch}} = 15.0\text{ m/s}$) were 100% rejected by the onboard governor (`vehicle_physics.py`).
2. **CAN J1939 Framing & Priority Preemption:** Priority 0 emergency braking frames won bus arbitration within $1.2\text{ ms}$ even under $95\%$ synthetic bus saturation.
3. **CAN Watchdog Silence Detection:** Physical severance of the CAN bus triggered emergency brake clamping within $154.5\text{ ms}$ (watchdog: $150\text{ ms}$).
4. **Stale Data Ingestion Rejection:** Replay attacks, duplicate sequence numbers, and expired timestamps were rejected across all gateway and HMI layers.
5. **In-Cab Stale Data Watermarking:** Killing telemetry feeds triggered flashing amber "DATA STALE" watermarks at $300\text{ ms}$ and full numerical masking at $500\text{ ms}$.
6. **Physical Collision Avoidance:** Across all simulated cascade failures and downhill braking tests, the vehicle halted before striking obstacles ($S_{\text{stop}} < R_{\text{eff}}$ in 100% of non-biased runs).

---

## 3. What Broke Under Attack

1. **Downhill Standstill Buffer Invariant (INV-01):** On a $-8\%$ ramp with $\mu=0.35$, stopping distance was $3.885\text{ m}$ against a $3.0\text{ m}$ budget, eroding the $5.0\text{ m}$ buffer to $4.115\text{ m}$.
2. **DGMS Cascade Reaction Ceiling (INV-08):** Combined comm loss timeout ($500\text{ ms}$), governor solve ($40\text{ ms}$), CAN queueing ($45\text{ ms}$), and hydraulic buildup ($350\text{ ms}$) totaled **$935.0\text{ ms} > 800.0\text{ ms}$**.
3. **Safe Beacon RF Independence (INV-09):** Single SX1278 transceiver operation caused $38.5\text{ ms}$ receiver blinding per beacon packet.
4. **Single-Channel Sensor Bias Detection (INV-10):** Systematic positive bias $+1.0\text{ m}$ to $+50.0\text{ m}$ was **100% undetectable** by single-channel statistical filters.
5. **DSSS Handover Stability:** Multipath noise $\sigma_{\text{noise}} \ge 0.15$ induced ping-pong handover flapping ($10\text{ flaps} / 1000\text{ cycles}$).

---

## 4. Master Numerical Failure Boundaries

```
CRITICAL NUMERICAL CLIFF EDGES:
-----------------------------------------------------------------------------------------
Subsystem                  Parameter / Condition           Numerical Failure Boundary
-----------------------------------------------------------------------------------------
Haul Ramp Braking          Actuator Delay (Strict 5m Buf)  T_act <= -1.4 ms (Buffer eroded)
Haul Ramp Braking          Actuator Delay (Phys Collision) T_act >= 1419.0 ms
CAN J1939 Bus              Synthetic Bus Load              Load >= 96.5% (Exceeds 50ms budget)
CAN Watchdog               Bus Cable Severance             T_silence > 150.0 ms
Cascade Comm-Loss          Total Perception-to-Brake       T_cascade = 935.0 ms (> 800ms DGMS)
DSSS Gateway Handover      Multipath Gaussian Noise        sigma_noise >= 0.15 (Flapping)
Optical Sensor Bias        Single-Channel Additive Drift   b >= +0.5 m (Undetected)
Optical Sensor Collision   Positive Additive Drift in Fog  b >= +7.0 m (Direct Collision)
HMI Stale Marking          Telemetry Drop                  T_age >= 300.0 ms
Safe Beacon Coexistence    Half-Duplex TX Blocking         Airtime = 38.5 ms / packet
-----------------------------------------------------------------------------------------
```

---

## 5. Contradictions Cataloged

1. **Reaction Latency Figures:** Resolved distinction between theoretical analytical budget ($437.1\text{ ms}$), nominal target ($450.0\text{ ms}$), empirical P99 ($557.3\text{ ms}$), DGMS standard ($800.0\text{ ms}$), and cascade worst-case ($935.0\text{ ms}$).
2. **CAN Latency Budget:** $50\text{ ms}$ budget violated at $99\%$ load ($54.8\text{ ms}$); resolved via Priority 0 preemption.
3. **Actuator Delay Truthfulness:** 250 ms assumption unmasked as unmeasured Level F.
4. **433 MHz Dual-Use Conflict:** Single SX1278 telemetry + beacon conflict cataloged as Open Safety Dependency.
5. **DSSS vs. LoRa CSS:** LoRa CSS is hardware PHY; DSSS PN is software research model.
6. **Bailadila Validation Claims:** Presentation claims downgraded from "Field Validated" to "HIL/Simulation Validated".
7. **Downhill Crawl Speed:** $3.52\text{ m/s}$ crawl erodes 5m buffer on $-8\%$ slope; lowered to $2.99\text{ m/s}$.
8. **Safe Beacon Control Room Notification:** Circular dependency eliminated; Control Room alerts via passive heartbeat loss.
9. **Friction Parameters:** Separated dry hardpack ($\mu=0.70$) from wet crushed ore ($\mu=0.35$).
10. **Watchdog Timeouts:** 500 ms LoRa comm loss lowered to 200 ms in dense fog.

---

## 6. Official Claim Downgrade Register

In compliance with Rule 16, the following project claims are permanently downgraded:

| Original Wording | Downgraded / Defensible Wording | Justification |
| :--- | :--- | :--- |
| *"Validated at NMDC Bailadila Iron Ore Mine"* | *"Validated in Hardware-in-the-Loop (HIL) and software simulation using Bailadila terrain models; physical mine trials pending."* | Zero physical 100t trucks were actuated in the pit during Phase 9. |
| *"Full J1939 CAN protocol validated on HEMM"* | *"J1939 29-bit framing and priority arbitration validated on ESP32-S3 TWAI benchtop hardware at 250 kbps."* | Lab bench test, not physical OEM Caterpillar/BEML backbone. |
| *"DSSS PN gateway correlation implemented"* | *"DSSS PN gateway correlation mathematically modeled in simulation; physical layer utilizes Semtech LoRa CSS."* | Prototype hardware is LoRa CSS, not custom DSSS ASIC. |
| *"Safe Beacon guarantees communication recovery"* | *"Safe Beacon provides an autonomous local V2V hazard broadcast for adjacent vehicles under tested conditions."* | Circular dependency removed; single-transceiver RF conflict noted. |
| *"Sensor degradation architecture detects all sensor faults"* | *"Architecture detects freeze, dropouts, noise, and outliers; systematic single-channel additive bias remains an unobservable limitation."* | Mathematical proof of additive bias unobservability. |

---

## 7. Master Claim-by-Claim Go / No-Go Classification

| Claim ID | Subsystem & Subject | Red-Team Classification | Commercial Go / No-Go Status |
| :---: | :--- | :---: | :---: |
| **CLM-01** | Nominal Reaction Time Budget ($\le 450\text{ ms}$) | **PARTIALLY DEFENSIBLE** | **CONDITIONAL GO** (Local loop is 243.8 ms; full loop P99 is 557.3 ms) |
| **CLM-02** | Physical Actuator Response ($250\text{ ms}$) | **NOT YET VALIDATED** | **NO-GO FOR UNATTENDED AUTONOMY** (Field trials required) |
| **CLM-03** | Standstill Buffer Invariant ($5.0\text{ m}$ on $-8\%$ Grade) | **CONTRADICTED** | **GO AFTER PARAMETER REVISION** (Revise crawl to $2.99\text{ m/s}$) |
| **CLM-04** | J1939 CAN Priority & Timing ($T_{\text{CAN}} \le 50\text{ ms}$) | **DEFENSIBLE (HIL ONLY)** | **GO FOR BENCH INTEGRATION** |
| **CLM-05** | CAN Watchdog Fail-Safe Action ($150\text{ ms}$) | **DEFENSIBLE** | **GO** (154.5 ms measured shutdown) |
| **CLM-06** | DSSS Gateway Multipath Handover | **PARTIALLY DEFENSIBLE** | **GO AFTER HYSTERESIS REVISION** (`SWITCH_MARGIN` $\to 0.18$) |
| **CLM-07** | LoRa Physical Radio Link (433 MHz) | **DEFENSIBLE (BENCH)** | **GO** (38.5 ms airtime measured) |
| **CLM-08** | Safe Beacon Fail-Safe Transmission | **PARTIALLY DEFENSIBLE** | **NO-GO ON SINGLE RADIO** (Open Safety Dependency) |
| **CLM-09** | Sensor Degradation 8-State Classification | **DEFENSIBLE** | **GO FOR STUCK/OUTLIER FAULTS** |
| **CLM-10** | Single-Channel Sensor Bias Detection | **UNSUPPORTED** | **NO-GO FOR UNREDUNDANT VISIBILITY** (Requires radar fusion) |
| **CLM-11** | Digital Twin Non-Authoritative Decoupling | **DEFENSIBLE** | **GO** (100% decoupled from Tier-1 safety) |
| **CLM-12** | In-Cab HMI Stale Data Protection | **DEFENSIBLE** | **GO** (Watermarking verified) |
| **CLM-13** | End-to-End Cascade Failure Survival | **PARTIALLY DEFENSIBLE** | **GO AFTER TIMEOUT REVISION** (Reduce comm timeout to 200 ms) |
| **CLM-14** | Bailadila Mine Site Validation | **NOT YET VALIDATED** | **FIELD DEPLOYMENT PENDING** |
| **CLM-15** | DGMS 800 ms Reaction Compliance (Cascade) | **CONTRADICTED** | **GO AFTER PARAMETER REVISION** (Revise timeout to 200 ms) |

---

## 8. Mandatory Engineering Action Plan

1. **Parameter Revision `CONFIG_REV_9_1_02`:** Reduce dense-fog crawl speed on $-8\%$ grade from $3.52\text{ m/s}$ to **$2.99\text{ m/s}$ ($10.76\text{ km/h}$)** to preserve the strict $5.0\text{ m}$ buffer.
2. **Parameter Revision `CONFIG_REV_9_1_04`:** Reduce `COMM_LOSS_TIMEOUT_DENSE_FOG_MS` from $500.0\text{ ms}$ to **$200.0\text{ ms}$** to cap cascade reaction time at $595.0\text{ ms} < 800.0\text{ ms}$.
3. **Hardware Revision `HW_REV_2_1`:** Mandate dual transceivers (Radio 1 for Gateway, Radio 2 for Safe Beacon) to eliminate the Open RF Safety Dependency.
4. **Perception Redundancy:** Pair optical visibility sensors with 77 GHz radar or V2V consensus to trap positive additive sensor drift.
5. **Phase 10 Field Validation:** Instrument physical BEML/CAT dump truck hydraulic lines with 0-25 MPa pressure transducers at Bailadila to replace Level F assumptions with Level A physical data.
