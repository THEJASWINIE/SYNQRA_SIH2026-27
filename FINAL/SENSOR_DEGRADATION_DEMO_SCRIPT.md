# SENSOR DEGRADATION EVALUATOR DEMONSTRATION SCRIPT (90 SECONDS)
## FOG-ORCHESTRATOR 2.0 — Closed-Loop Fault-to-Orchestration Showcase
**Project:** SIH26007 — Safe Haulage in Fog / Low Visibility  
**Date:** 2026-09-21  
**Target Audience:** Scientific Evaluators, SIH Jury, DGMS Safety Auditors  
**Duration:** Exactly 90 Seconds  

---

## 1. Demonstration Philosophy
The purpose of this demonstration is **not visual animation**.  
The demonstration proves the complete deterministic causal chain:
$$\text{RAW DATA} \to \text{DATA HEALTH} \to \text{SAFETY STATE} \to v_{\text{safe}} \to \text{ROAD CAPACITY} \to \text{QUEUE PREDICTION} \to \text{FLEET ACTION}$$

---

## 2. Second-by-Second Chronological Timeline

### Phase 1: Nominal High-Speed Operation (00:00 – 00:10)
- **Telemetry State:**  
  - Weather Station: $R_{\text{vis}} = 50.0\text{ m}$, age $= 0.2\text{ s}$, sequence monotonic.  
  - Vehicle Telemetry: TRUCK_01 speed $= 8.5\text{ m/s}$ ($30.6\text{ km/h}$), mass $= 165.5\text{ t}$.  
- **Data Health Output:** `DataState.HEALTHY`, `confidence = 1.0`, $R_{\text{effective\_applied}} = 50.0\text{ m}$.  
- **Physics Solver:** $v_{\text{safe}} = 8.52\text{ m/s}$ (governed by site limit and stopping distance).  
- **Fleet Orchestration:** Road capacity $= 4\text{ trucks}$, flow rate $= 100\%$, ramp free-flowing.

---

### Phase 2: Sensor Telemetry Degradation Injected (00:10 – 00:20)
- **Failure Injected:** At $t=10\text{ s}$, the optical visibility sensor connection halts (Scenario D5/D10); simultaneously, physical fog density thickens (ground truth visibility drops to $12.0\text{ m}$).  
- **Baseline B0 Reaction:** Baseline system holds stale $50.0\text{ m}$ indefinitely. Speed remains $8.52\text{ m/s}$, creating a fatal stopping margin deficit of $-18.4\text{ m}$.  
- **Treatment B1 Observation:** Telemetry timer elapses: packet age increments from $1\text{ s} \to 10\text{ s}$.

---

### Phase 3: Data Health Layer Detects Degradation (00:20 – 00:30)
- **Trigger Event:** At $t=20\text{ s}$, age exceeds $T_{\text{DEGRADED\_ENV}} = 30.0\text{ s}$ threshold.  
- **Data Health Transition:**  
  $$\text{DataState: HEALTHY} \to \text{DEGRADED}$$  
  `fault_code: TIMEOUT`, `confidence: 0.70`.  
  Conservative fallback applied:
  $$R_{\text{effective\_conservative}} = 50.0 \times 0.70 = 35.0\text{ m}$$

---

### Phase 4: Local Safety State Transition (00:30 – 00:40)
- **Local Vehicle Safety Governor:**  
  State updates from `NORMAL` to `RESTRICTED`.  
  Operator HMI displays:  
  `[ADVISORY: VISIBILITY TELEMETRY DEGRADED — REDUCING OPERATIONAL ENVELOPE]`

---

### Phase 5: Safe Speed $v_{\text{safe}}$ Recalculation (00:40 – 00:50)
- **Physics Solver Recalculation:**  
  Solver evaluates stopping constraint:
  $$v_{\text{stop}} = -a_{\text{dec}} \tau + \sqrt{a_{\text{dec}}^2 \tau^2 + 2 a_{\text{dec}} (35.0 - 5.0)} = 6.28\text{ m/s}$$  
  Safe speed decreases from $8.52\text{ m/s} \to 6.28\text{ m/s}$ ($22.6\text{ km/h}$).  
- **Local Governor Clamping:** Vehicle commanded speed immediately clamped to $\le 6.28\text{ m/s}$. Zero overshoot.

---

### Phase 6: Road Capacity Dynamically Contracts (00:50 – 01:00)
- **Capacity Calculation:**  
  Required headway scales with stopping distance:
  $$S_{\text{headway}} = 2 \times S_{\text{stop}}(6.28) \approx 72\text{ m}$$  
  Haul road capacity contracts from $4\text{ trucks} \to 2\text{ trucks}$.

---

### Phase 7: Queue Prediction Identifies Chokepoint (01:00 – 01:10)
- **Predictive Engine:** Predicts queue bottleneck at the downhill ramp entry within $180\text{ seconds}$ if dispatch continues at nominal rate.  
- **Risk Identified:** Downhill ramp congestion on $-8\%$ slope under degrading sightlines.

---

### Phase 8: Central Orchestration Intervenes (Controlled Staging) (01:10 – 01:20)
- **Orchestration Dispatch Decision:**  
  Instead of letting following trucks (TRUCK_03, TRUCK_04) crowd onto the active downhill ramp, the orchestrator issues a `HOLD_AT_STAGING` advisory.  
- **Traffic Realignment:** Trucks wait safely in the wide, flat loading staging zone.  
- **Metric Proved:** Hazardous road waiting $= 0\text{ s}$; Staging waiting $= 65\text{ s}$.

---

### Phase 9: Full Sensor Loss & Safe Crawl Fallback (01:20 – 01:30)
- **Failure Escalation:** Age exceeds $T_{\text{GRACE\_PERIOD}} = 120.0\text{ s}$ (or sensor blackout D12 occurs).  
- **Data Health Transition:**  
  $$\text{DataState} \to \text{UNAVAILABLE}$$  
  $$R_{\text{effective}} \to R_{\text{UNAVAILABLE\_MIN}} = 8.0\text{ m}, \quad \text{confidence} = 0.0$$  
- **Final Safety Envelope:**  
  $v_{\text{safe}}$ drops to $1.88\text{ m/s}$ ($6.7\text{ km/h}$ crawl speed).  
  Trucks maintain full stopping capability within headlight illumination distance.  
- **Evaluator Takeaway:** System exhibits graceful deterministic degradation without emergency lockups or collisions.
