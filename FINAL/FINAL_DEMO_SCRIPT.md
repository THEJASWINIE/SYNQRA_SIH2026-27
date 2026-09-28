# 90-SECOND EVALUATOR DEMONSTRATION SCRIPT
## FOG-ORCHESTRATOR 2.0 — SIH 2026-27 (Problem Statement SIH26007)
### Live Evaluator Walkthrough: Closed-Loop Causal Proof (DETECT → DECIDE → ACT → MEASURE)

---

## 1. Demonstration Protocol & Evaluator Grounding

This 90-second demonstration delivers verifiable visual and quantitative proof of the closed-loop causal chain:

$$\mathbf{DETECT}\ \longrightarrow\ \mathbf{DECIDE}\ \longrightarrow\ \mathbf{ACT}\ \longrightarrow\ \mathbf{MEASURE}$$

### Critical Spoken Distinction Required Throughout the Demo:
- **LIVE / PHYSICAL BENCH:** Real physical ESP32 running FreeRTOS, physical SX1278 LoRa 433 MHz RF link (99.1% PDR), and physical TWAI/CAN bus (0.512 ms wire delay).
- **HIL (Hardware-in-the-Loop):** Real ESP32 Tier-1 safety governor firmware interacting in real time with simulated vehicle dynamics, in-cab Operator HUD bridge, and parametric actuator build-up models.
- **SIMULATION:** 6-truck fleet queue dynamics, what-if bottleneck predictions, and 20-seed multi-hour haulage benchmarks.

---

## 2. Second-by-Second Execution Timeline (0 to 90 Seconds)

```
+---------------------------------------------------------------------------------------------------------+
| TIMELINE | SCENARIO PHASE      | HUD / DASHBOARD PRESENTATION           | SPOKEN EXPLANATION & EVIDENCE |
+---------------------------------------------------------------------------------------------------------+
| 00–15 s  | NORMAL              | • Visibility: 100.0 m (Clear)          | "We begin under normal clear  |
|          |                     | • Safe Speed: 11.11 m/s (40.0 km/h)   | weather. Notice in SIMULATION |
|          |                     | • Comm State: NORMAL_DSSS_GATEWAY     | the fleet hauls smoothly at   |
|          |                     | • Ramp Queue: 0 trucks                | 40 km/h. Theoretical capacity |
|          |                     | • HUD: GREEN 'NOMINAL_DISPATCH'       | is 817.8 VPH. Crusher receives|
|          |                     |                                       | steady 200s feeds."           |
+---------------------------------------------------------------------------------------------------------+
| 15–30 s  | FOG ARRIVES         | • Visibility slider: 100m -> 12m      | "At t=15s, dense fog rolls into|
|          |                     | • Transmissometer alerts trigger      | the pit. Ambient visibility   |
|          |                     | • Fog icon pulses amber on HUD        | drops to 12m. The Digital Twin|
|          |                     | • Digital Twin environment updates    | updates the environment layer.|
|          |                     |                                       | Watch the immediate reaction."|
+---------------------------------------------------------------------------------------------------------+
| 30–45 s  | SAFE SPEED FALLS    | • Commanded Speed: 11.11 -> 5.12 m/s  | "Notice the safe speed falls  |
|          |                     | • Safe Speed: 5.12 m/s (18.4 km/h)    | to 5.12 m/s. This is governed |
|          |                     | • Stopping Distance: 6.94 m           | by the LIVE PHYSICAL BENCH on |
|          |                     | • S_stop + 5m <= 12m strictly held    | our ESP32 solving the stopping|
|          |                     | • HUD: AMBER 'GOVERNOR_CLAMPED'       | quadratic root in real time." |
+---------------------------------------------------------------------------------------------------------+
| 45–55 s  | ROAD CAPACITY FALLS | • Space Headway: 14.5 -> 22.52 m      | "Slower speeds require wider  |
|          |                     | • Road Capacity: 818 -> 450 VPH       | 22.5m headway. Kinematic road |
|          |                     | • Shovel arrival demand: 18 trucks/hr | capacity collapses to 450 VPH |
|          |                     | • Ramp inflow exceeds capacity        | in SIMULATION. Inflow now     |
|          |                     |                                       | exceeds safe ramp discharge." |
+---------------------------------------------------------------------------------------------------------+
| 55–65 s  | QUEUE / BOTTLENECK  | • Ramp queue ticks up (1..2 trucks)   | "Without intervention, queues |
|          | PREDICTED           | • Bottleneck Severity Index > 0.3     | form on the -8% slope. But our|
|          |                     | • Digital Twin predicts ramp gridlock | what-if predictor identifies  |
|          |                     | • Dashboard flags: BOTTLENECK_WARNING | the bottleneck 5 minutes ahead|
|          |                     |                                       | before gridlock can cascade." |
+---------------------------------------------------------------------------------------------------------+
| 65–75 s  | HOLD / SLOT /       | • TRUCK_01 allocated: SLOT_RAMP_01    | "The orchestrator acts: it    |
|          | RELEASE             | • TRUCK_02 HUD: 'HOLD_AT_STAGING_BAY' | holds trailing trucks at flat |
|          |                     | • Ramp queue collapses to 1.2 trucks! | shovel staging bays and meters|
|          |                     | • Waiting relocated to flat ground    | single-truck slots. Hazardous |
|          |                     | • Steady 200s crusher arrival matched | ramp waiting drops by 77.36%!"|
+---------------------------------------------------------------------------------------------------------+
| 75–82 s  | COMMUNICATION       | • LoRa Gateway link severed           | "Now we inject a total RF comm|
|          | FAILURE             | • Comm State: COMM_LOSS (Red Alert)   | loss in HIL. Watch: does the  |
|          |                     | • Safe Beacon: TIMEOUT                | truck runaway or crash? No."  |
+---------------------------------------------------------------------------------------------------------+
| 82–87 s  | LOCAL SAFETY        | • Comm State: COMM_LOSS (Explicit)    | "Here is the architectural key|
|          | FALLBACK            | • Motion State: SAFE_LOCAL_AUTONOMOUS | Communication is decoupled from|
|          |                     | • Speed remains locked at 5.12 m/s    | motion. The Tier-1 governor   |
|          |                     | • Headway doubles to 45m defensively  | keeps the truck safe even when|
|          |                     | • Zero collisions, zero runaways      | all wireless links are dead." |
+---------------------------------------------------------------------------------------------------------+
| 87–90 s  | RECOVERY            | • Visibility restored to 100m         | "Fog clears. The gateway resyncs|
|          |                     | • Gateway: RECOVERY_SYNC (N>=2 frames)| after 2 valid frames. Trucks  |
|          |                     | • Metered release clears staging bay  | release with metered spacing. |
|          |                     | • Fleet returns smoothly to 40 km/h   | Shift production recovers to  |
|          |                     | • Zero gridlock shockwaves generated  | 1591.4 TPH modeled throughput."|
+---------------------------------------------------------------------------------------------------------+
```

---

## 3. Evaluator Talking Points & Live Evidence Grounding

1. **Figure 1 (`FINAL/figures/e2e_causal_chain.png`):**
   *"Notice how the red ramp queue line drops the instant the orchestrator issues the HOLD command at $t=65\text{ s}$, while the purple origin staging queue absorbs the wait on flat, safe ground."*
2. **Table 1 (`FINAL/FINAL_BENCHMARK.md`):**
   *"Evaluated across 20 matched seeds: hazardous ramp waiting dropped from 625.4s to 141.6s (77.36% reduction, $p < 10^{-30}$), while modeled throughput increased from 1171.2 to 1591.4 TPH (+35.88% relative to L0; +27.46% relative to L1) by pacing arrivals to the 1647 TPH crusher ceiling."*
3. **Hardware Provenance Boundary (`FINAL/FINAL_EVIDENCE_BOUNDARY.md`):**
   *"We are fully transparent: the ESP32 Tier-1 governor, 250 kbps TWAI CAN bus (0.512 ms wire delay), and 99.1% LoRa PDR are physically measured on bench hardware. The BH100 hydraulic brakes and pit multipath are evaluated in HIL and simulation. We do not claim physical field validation."*
