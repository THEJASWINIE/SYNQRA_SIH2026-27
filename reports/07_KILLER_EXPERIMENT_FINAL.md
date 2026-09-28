# 07 — KILLER EXPERIMENT FINAL RE-EVALUATION REPORT

**Project:** FOG-ORCHESTRATOR 2.0 (SIH 2026-27 — SIH26007)  
**Classification:** Closed-Loop Multi-Tier Fleet Haulage Benchmark (30 Independent Seeds)  
**Datasets:**  
- [`data/phase7_3_fleet.csv`](file:///c:/Users/JAGADEESH%20M/OneDrive/Documents/SIH-2026-27/data/phase7_3_fleet.csv) (150 runs)  
- [`data/phase7_3_queue.csv`](file:///c:/Users/JAGADEESH%20M/OneDrive/Documents/SIH-2026-27/data/phase7_3_queue.csv) (150 runs)  
- [`data/phase7_3_bottleneck.csv`](file:///c:/Users/JAGADEESH%20M/OneDrive/Documents/SIH-2026-27/data/phase7_3_bottleneck.csv) (150 runs)  
**Date of Audit:** 2026-09-18  

---

## 1. Experimental Scenario & Haulage Loop

The core validation experiment models a realistic closed-loop mining circuit under dense fog transition:
- **Haul Circuit:** Shovel Pit Face $\rightarrow$ 1.5 km Downhill Ramp (-8.0% grade) $\rightarrow$ Primary Gyratory Crusher $\rightarrow$ 1.5 km Uphill Empty Return Ramp (+8.0% grade).
- **Fleet:** 12 BEML BH100 rigid rear dump trucks ($165.5\text{ t}$ laden, $74.0\text{ t}$ tare, $91.5\text{ t}$ payload).
- **Fog Profile:** 
  - $t = 0\text{--}300\text{ s}$: Clear sightline ($R_{\text{eff}} = 100.0\text{ m}$).
  - $t = 300\text{--}400\text{ s}$: Fog ingress ($R_{\text{eff}}$ drops from $100\text{ m}$ to $12\text{ m}$).
  - $t = 400\text{--}1,400\text{ s}$: Heavy fog steady state ($R_{\text{eff}} = 12.0\text{ m}$, wet surface $\mu = 0.35$).
  - $t = 1,400\text{--}1,500\text{ s}$: Fog dissipation ($R_{\text{eff}}$ returns to $100\text{ m}$).
  - $t = 1,500\text{--}2,200\text{ s}$: System recovery and normal platooning flow.

---

## 2. Quantitative Comparison Across 5 Orchestration Levels (30 Seeds Mean)

```
LEVEL 0: No Orchestration (Conventional operation, blind dispatch)
LEVEL 1: Vehicle-Only Safe Speed Adaptation (Autonomous governor only; unmetered dispatch)
LEVEL 2: Vehicle + Road Capacity Awareness (Haul road entry metered to kinematic flux)
LEVEL 3: Vehicle + Capacity + Bottleneck Prediction (Lookahead queue detection)
LEVEL 4: Full FOG-Orchestrator (Arrival shaping at shovel bays + HOLD/RELEASE + crusher slot pacing)
```

| Performance Metric | Level 0: No Orchestration | Level 1: Vehicle Safety Only | Level 2: Road Capacity Aware | Level 3: Predictive Bottleneck | Level 4: Full FOG-Orchestrator | Level 4 vs. Level 1 Delta |
|:---|:---:|:---:|:---:|:---:|:---:|:---:|
| **Hazardous Road Queue Waiting ($W_{\text{road}}$)** | 860.2 s (14.3 min) | 625.4 s (10.4 min) | 410.1 s (6.8 min) | 245.3 s (4.1 min) | **141.6 s (2.4 min)** | **-77.4% (-483.8 s)** |
| **Safe Shovel / Bay Waiting ($W_{\text{origin}}$)** | 45.1 s (0.8 min) | 88.2 s (1.5 min) | 249.8 s (4.2 min) | 395.1 s (6.6 min) | **489.2 s (8.2 min)** | **+401.0 s (Relocated)** |
| **Total System Waiting ($W_{\text{total}}$)** | 905.3 s (15.1 min) | 713.6 s (11.9 min) | 659.9 s (11.0 min) | 640.4 s (10.7 min) | **630.8 s (10.5 min)** | **-11.6% (-82.8 s)** |
| **Steady-State Production (TPH)** | 1,085.2 TPH | 1,375.4 TPH | 1,460.1 TPH | 1,530.2 TPH | **1,591.4 TPH** | **+15.7% (+216.0 TPH)**|
| **Crusher Bottleneck Utilization** | 65.9% | 83.5% | 88.7% | 92.9% | **96.6%** | **+13.1% Utilization** |
| **Peak Haul Road Queue Size** | 8.2 trucks | 5.8 trucks | 3.9 trucks | 2.4 trucks | **1.2 trucks** | **-79.3% Peak Queue** |
| **Queue Duration ($T_{\text{queue}}$)** | 1,450 s | 1,180 s | 850 s | 520 s | **180 s** | **-84.7% Duration** |
| **Bottleneck Duration ($T_{\text{bottleneck}}$)**| 1,500 s | 1,220 s | 890 s | 540 s | **195 s** | **-84.0% Duration** |
| **Post-Fog Recovery Time ($T_{\text{recov}}$)** | 320 s | 210 s | 135 s | 78 s | **48 s** | **-77.1% Recovery** |
| **Safety / Overspeed Violations** | **12.4 incidents** | **0.0** | **0.0** | **0.0** | **0.0** | **100% Invariant Enforcement** |
| **HOLD Commands Issued** | 0 | 0 | 8.1 | 14.2 | **22.1** | Proactive Staging |
| **RELEASE Commands Issued** | 0 | 0 | 8.1 | 14.2 | **22.1** | Coordinated Pacing |
| **Slot Allocation Decisions** | 0 | 0 | 12.0 | 18.0 | **24.0** | Synchronized Feeds |

---

## 3. Scientific Analysis of the Hierarchy Progression

1. **Level 0 $\rightarrow$ Level 1 (Autonomous Safety Enforcement):**  
   Introducing the onboard local safety governor eliminates all 12.4 collision and overspeed violations. Trucks slow down safely to $v_{\text{safe}} = 5.12\text{ m/s}$ ($18.4\text{ km/h}$) under 12 m visibility. However, unmanaged shovel dispatches cause trucks to stack up into a **5.8-truck stationary jam on the -8% haul ramp**, causing 625.4 s of road delay.
2. **Level 1 $\rightarrow$ Level 2 (Road Capacity Awareness):**  
   Throttling dispatches to match road capacity cuts road queue waiting from 625.4 s to 410.1 s (-34.4%) by holding trucks at origin bays until downstream space is clear.
3. **Level 2 $\rightarrow$ Level 3 (Bottleneck Lookahead Prediction):**  
   Predicting arrival pileups before they form further reduces road queue waiting to 245.3 s and drops peak queue size to 2.4 trucks.
4. **Level 3 $\rightarrow$ Level 4 (Full FOG-Orchestrator Arrival Shaping):**  
   Synchronizing shovel releases directly with the crusher's 200-second acceptance slot collapses hazardous road queue waiting to **141.6 s** and peak queue to **1.2 trucks** (virtually free-flow movement). Stationary delay is safely stored at the shovel bays (489.2 s). Crusher utilization reaches **96.6% (1,591.4 TPH)**, and post-fog flow restoration drops from 210 s to **48 s**.
