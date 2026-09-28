# FOG-ORCHESTRATOR 2.0 — Predictive Digital Twin & Decision Support
**Document ID:** `DOC-04-DT-02` | **Audited Standard:** Receding-Horizon Decision Support

---

## 1. Architectural Distinction: Predictive vs Central Control

The **Predictive Digital Twin** is **NOT** a centralized autonomous controller. It serves as an advisory decision-support layer for mine supervisors:
- **Decision-Support Scope**: Computes the expected future impact of environmental fog changes over a 30 to 60-second lookahead horizon.
- **What-If Fog Scenario Simulation**: Evaluates what happens when a fog front advances across Section 3 (Switchback ramp).
- **Simulated Outcomes**:
  - Predicts the reduction in vehicle safe speed along the downhill grade.
  - Computes required inter-vehicle headway expansion ($h_{safe} = v \cdot \tau + S_{stop}$).
  - Forecasts queue formation at crusher dumping bays and switchback chokepoints.
  - Calculates throughput degradation and recommends optimal dispatch pacing ($v_{dispatch}$).

---

## 2. Predictive Decision-Support Pipeline

```
Current Live Twin State (Fleet positions, speeds, weather)
       ↓
What-If Fog Propagation Model (Advancing fog front: 1000m -> 50m)
       ↓
Receding-Horizon Lookahead Engine (T + 30s ... T + 60s)
       ↓
Headway & Queueing Solver (Bottleneck detection & queue expansion)
       ↓
Advisory Dispatch Optimization (Optimal pacing advice to supervisor)
```

---

## 3. Verification & Separation from Physical Hardware

- **Provenance**: `PREDICTIVE / SIMULATION`.
- **Separation**: Predictive lookaheads run in an isolated execution thread and never overwrite live hardware telemetry or local Tier-1 safety governors.
