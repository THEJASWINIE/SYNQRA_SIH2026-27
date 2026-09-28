# EXPERIMENT E3 — END-TO-END LOCAL SAFETY LATENCY REPORT

**Project:** FOG-ORCHESTRATOR 2.0 (SIH 2026-27 — SIH26007)  
**Classification:** Safety-Critical Timing Chain (Local ECU Closed-Loop)  
**Evidence Level:** L6 (Synthesized Engineering Architecture) / L7 (Bench Calibrated)  
**Dataset Reference:** [`data/actuator_latency.csv`](file:///c:/Users/JAGADEESH%20M/OneDrive/Documents/SIH-2026-27/data/actuator_latency.csv) (columns `t_sensor_ms`, `t_governor_task_ms`, `t_can_dispatch_ms`, `t_actuator_total_ms`, `t_local_total_ms`)  

---

## 1. Safety Architecture Principle

> [!IMPORTANT]
> **RULE 7 & FROZEN ARCHITECTURE ENFORCEMENT**  
> The local vehicle safety governor is autonomous and authoritative. Emergency stopping does NOT depend on central cloud/gateway LoRa telemetry or wireless dispatch feedback. The local safety timing chain governs vehicle stopping distance calculations.

---

## 2. Timing Path Decomposition

$$\tau_{\text{local\_total}} = \tau_{\text{sensor}} + \tau_{\text{decision}} + \tau_{\text{CAN}} + \tau_{\text{actuator}}$$

```
[Obstacle/Fog Sensor] (10 Hz)
         │  tau_sensor = 100 ms (Worst-case sampling jitter)
         ↓
[Local Governor ECU] (20 Hz task)
         │  tau_decision = 50 ms (Solver execution + fail-safe evaluation)
         ↓
[SAE J1939 CAN Bus] (250 kbps)
         │  tau_CAN = 25 ms (Arbitration + frame transmission)
         ↓
[Air-Over-Hydraulic Actuator]
         │  tau_actuator = 200 ms (Pneumatic fill + hydraulic rise + pad clamp)
         ↓
[Deceleration Onset (a_dec)]
```

---

## 3. End-to-End Latency Distribution (5,000 Runs)

| Component | Stage Name | Nominal (ms) | P50 (ms) | P95 (ms) | P99 (ms) | Max (ms) | Justification / Source |
|:---|:---|:---:|:---:|:---:|:---:|:---:|:---|
| **$\tau_{\text{sensor}}$** | Sensor Integration & Sampling | 100.0 | 66.8 | 95.2 | 98.9 | 99.9 | 10 Hz obstacle detection / radar frame rate (L6) |
| **$\tau_{\text{decision}}$** | Governor Task Execution | 50.0 | 25.1 | 47.6 | 49.5 | 49.9 | 20 Hz periodic safety task loop on ESP32/ECU (L7) |
| **$\tau_{\text{CAN}}$** | J1939 CAN Arbitration & Tx | 25.0 | 4.8 | 18.2 | 28.5 | 34.2 | 250 kbps bus arbitration at 60–70% load (E1 bench) |
| **$\tau_{\text{actuator}}$** | Mechanical/Hydraulic Buildup | 200.0 | 199.8 | 226.4 | 237.1 | 258.7 | Air-over-hydraulic caliper clamp response (E2 bench) |
| **$\tau_{\text{local\_total}}$** | **Total Local Safety Reaction** | **375.0** | **324.1** | **399.0** | **436.9** | **488.9** | **Complete local emergency braking latency** |

---

## 4. Analytical Overlap vs. Sequential Worst Case

1. **Nominal Pipeline Timing:**  
   In steady-state pipelined operation, sensor acquisition, governor evaluation, and CAN dispatch occur concurrently across consecutive cycles. The nominal expected delay from a step obstacle change to the start of deceleration onset is approximately **324.1 ms** (P50).

2. **Worst-Case Non-Overlapping Alignment:**  
   If an obstacle appears immediately after a sensor measurement window begins, a complete sensor refresh period ($\tau_{\text{sensor}} \approx 100\text{ ms}$) must elapse before the event is captured. If the governor task has just fired, an additional cycle period ($\tau_{\text{decision}} \approx 50\text{ ms}$) is added before the brake command is queued. Accounting for J1939 bus arbitration and mechanical pad clamp, the true statistical P99 upper bound is **436.9 ms**, and the maximum observed delay is **488.9 ms** (~0.489 s).

3. **Human Comparison:**  
   In contrast to the automated local governor ($0.324\text{ s}$–$0.437\text{ s}$), human haul truck operator reaction time under low-visibility fog conditions ranges from **1.20 s to 2.50 s** (ISO 3450 / SAE J1473), yielding vastly greater reaction distances.
