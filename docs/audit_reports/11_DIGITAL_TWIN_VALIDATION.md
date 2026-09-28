# 11 — DIGITAL TWIN VALIDATION REPORT
## FOG-ORCHESTRATOR 2.0 | SIH 2026-27 (Problem Statement: SIH26007)
### NMDC Bailadila Low-Visibility HEMM Safety & Operational Intelligence System
**Document ID:** `11_DIGITAL_TWIN_VALIDATION.md`  
**Phase:** 9 — Full Hardware + Software + HMI + Control Room + Digital Twin Integration  
**Date:** September 2026 | **Classification:** LEVEL 2 / LEVEL 3 (Software & Simulation Validated)  
**Status:** COMPLETE & FROZEN  

---

## 1. Digital Twin Architecture & Role Demarcation (Section 14)

In strict adherence to **Rule 5 (One authoritative Digital Twin)** and the **System Authority Rule**:
1. **The Digital Twin is NOT an actuator controller.** It does not hold Tier-1 control authority.
2. The Digital Twin serves three distinct analytical functions:
   - **State Mirroring:** Authoritative digital reflection of physical haul roads, HEMMs, and atmospheric fog.
   - **Lookahead Prediction:** Kinematic projection of stopping sightlines and headway over a $3-5\text{ s}$ horizon.
   - **What-If Analysis:** Parametric stress-testing of environmental deterioration, grade changes, and communication dropouts.

```
REAL HEMM (BEML BH100)
       │
       │ (Physical Sensors & Odometry)
       ▼
TELEMETRY INGESTION (IF-01 & IF-02)
       │
       │ (Canonical VehicleState)
       ▼
DIGITAL TWIN STATE MIRROR (integration_adapters/digital_twin_sync.py)
       │
       ├─────────────────────────┬─────────────────────────┐
       ▼                         ▼                         ▼
FUNCTION 1: STATE MIRROR  FUNCTION 2: PREDICTION   FUNCTION 3: WHAT-IF
Live tracking of assets   $3-5\text{s}$ Stopping   Parametric simulation
and mine topology         Sightline Lookahead      of fog & RF loss
       │                         │                         │
       └─────────────────────────┼─────────────────────────┘
                                 │
                                 ▼
                     COMPARISON & DEVIATION AUDIT
                     (Position RMSE & Speed MAE)
                                 │
                                 ▼
                 RECOMMENDED SAFE SPEED CEILING
                                 │
                 (Advisory Only — Rule 7 & 17)
                                 ▼
                    LOCAL VEHICLE SAFETY GOVERNOR
                  (Sole Authority Over Actuators)
```

---

## 2. 5 Canonical Operating Modes (Section 16)

| Mode | Name | Data Driver | Computational Output | Use Case |
|:---:|:---|:---|:---|:---|
| **MODE 1** | **LIVE MIRROR** | Real hardware telemetry stream | Real-time twin state mirror & sync tracking | Operational monitoring during active hauling |
| **MODE 2** | **PREDICTIVE** | Current twin state + kinematic model | $T+3\text{s}$ stopping envelope & headway trajectory | Lookahead warning generation for dispatch |
| **MODE 3** | **WHAT-IF** | User-defined environmental inputs | Simulated safe speeds under hypothetical conditions | Engineering analysis & pre-shift planning |
| **MODE 4** | **REPLAY** | Recorded historical telemetry | Deterministic step-by-step trace reproduction | Incident post-mortem & regulatory audit |
| **MODE 5** | **FAULT INJECTION**| Historical stream + synthetic faults | Robustness evaluation under degraded conditions | Validation of safety governor fail-closed behavior|

---

## 3. Digital Twin What-If Demonstration Scenario (Section 32)

A primary end-to-end benchmark was executed on a simulated BEML BH100 approaching a steep downhill ramp:

### Phase A: Nominal Downhill Approach
- **Inputs:** Grade = $-8.0\%$, Visibility = $12.0\text{ m}$, Wet friction $\mu = 0.35$.
- **Twin Calculation:** Safe deceleration $a_{\text{dec}} = 2.12\text{ m/s}^2$, Available sightline $D = 7.0\text{ m}$.
- **Twin Safe Speed Recommendation:** $v_{\text{safe}} = 3.65\text{ m/s}$ ($13.1\text{ km/h}$).
- **State:** `ADVISORY` (speed reduced from nominal flat limit).

### Phase B: Severe Fog Incursion Injected
- **Injected Perturbation:** Visibility plunges from $12.0\text{ m} \longrightarrow 5.0\text{ m}$ (blindout threshold).
- **Twin Reaction:** Available sightline $D = 5.0 - 5.0 = 0.0\text{ m}$.
- **Twin Safe Speed Recommendation:** $v_{\text{safe}} \longrightarrow 0.0\text{ m/s}$ (controlled stop).
- **HMI Reaction:** Operator HMI flashes `DENSE FOG — SLOW DOWN`; Control Room logs `HIGH: VISIBILITY DETERIORATION`.
- **Vehicle Reaction:** Local Safety Governor immediately commands service brakes without waiting for remote authorization.

### Phase C: Simultaneous Total RF Loss Injected
- **Injected Perturbation:** Central gateway disconnected; zero telemetry uplink for $600\text{ ms}$.
- **System Reaction:**
  - Gateway link transitions to `DISCONNECTED`.
  - Vehicle activates **Safe Beacon** over 433 MHz LoRa.
  - Operator HMI displays: `COMMUNICATION LOST — SAFE MODE`.
  - Control Room displays: `TRUCK-01 OFFLINE — SAFE BEACON ACTIVE`.
  - Digital Twin displays: `COMMUNICATION STATE = LOST` (does NOT fabricate positions).
  - Local Safety Governor maintains complete independent control at crawling speed ($3.52\text{ m/s}$) or halt ($0.0\text{ m/s}$).

---

## 4. Multi-HEMM Mine Scenario Validation (Section 33)

Evaluated across three gateway zones in NMDC Deposit-5:
- **GW-01:** Crusher & Stockpile Area (Flat, high traffic).
- **GW-02:** Ramp R1 Switchback ($-8\%$ grade, persistent fog accumulation).
- **GW-03:** Pit Bottom Bench (Deep excavation, multipath RF shadow).

### Simulation Results:
- **Handover Continuity:** TRUCK_01 successfully executed seamless handover between GW-01 and GW-02 with zero command discontinuity.
- **Traffic Staging:** When TRUCK_01 crawled on Ramp R1, the Central Orchestrator dynamically held TRUCK_02 in the Crusher staging queue, preventing multi-truck pileups.
- **Provenance Transparency:** All simulated entities were explicitly tagged `SIMULATION` (Level 1/2) in accordance with Rule 3.

---

## 5. Digital Twin Failure Modes (Section 29)

1. **Digital Twin Crash:** If the 3D twin engine or background worker crashes, **THE PHYSICAL VEHICLE REMAINS 100% SAFE**. The onboard Local Safety Governor is completely decoupled from the Twin.
2. **Control Room Indication:** Control room display immediately flashes: `DIGITAL TWIN OFFLINE`.
3. **Staleness Protection:** If twin synchronization latency exceeds $1.0\text{ s}$, the twin state is watermarked `TWIN DATA STALE`. Predictive lookahead is suppressed to prevent false operator confidence.
