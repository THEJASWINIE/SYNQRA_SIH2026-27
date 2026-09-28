# EXPERIMENT E10 — FLEET ORCHESTRATION & QUEUE RELOCATION REPORT

**Project:** FOG-ORCHESTRATOR 2.0 (SIH 2026-27 — SIH26007)  
**Classification:** Fleet Orchestration & Discrete Event Haulage Dynamics  
**Evidence Level:** L9 — Simulation & Queue Theory Formulation (Little's Law)  
**Dataset Reference:** [`data/fleet_results.csv`](file:///c:/Users/JAGADEESH%20M/OneDrive/Documents/SIH-2026-27/data/fleet_results.csv) (30 seeds $\times$ 3 policies = 90 runs)  
**Figure:** [`figures/queue_comparison.png`](file:///c:/Users/JAGADEESH%20M/OneDrive/Documents/SIH-2026-27/figures/queue_comparison.png)  

---

## 1. Central Hypothesis of FOG-Orchestrator

$$\text{Fog Entry} \longrightarrow v_{\text{safe}} \downarrow \longrightarrow \text{Headway} \uparrow \longrightarrow C_{\text{road}} \downarrow \longrightarrow \text{Arrival Rate } \lambda > C_{\text{road}} \longrightarrow \text{Bottleneck Queue}$$

When visibility drops, road capacity collapses below the fleet arrival rate. In an unmanaged system, dumpers travel down the haul ramp and queue on steep, slippery grades, creating a severe rear-end collision hazard and blocking return traffic.

FOG-Orchestrator enforces **arrival rate metering at the origin shovel pockets and holding bays**, ensuring vehicles only enter the haul road when a safe downstream slot exists.

---

## 2. Quantitative Comparison Across 3 Operating Policies (30 Seeds)

| Metric Description | Policy A: No Orchestration | Policy B: Vehicle Safety Only | Policy C: FOG-Orchestrator | Physical Effect of Orchestration |
|:---|:---:|:---:|:---:|:---|
| **Hazardous Road Queue Waiting ($W_{\text{road}}$)** | **848.2 s** (14.1 min) | **619.4 s** (10.3 min) | **141.6 s** (2.4 min) | **-77.1% reduction in road queue exposure** |
| **Safe Origin / Shovel Waiting ($W_{\text{origin}}$)**| 51.2 s (0.9 min) | 90.5 s (1.5 min) | 489.2 s (8.2 min) | Controlled holding in wide, flat benches |
| **Total System Waiting ($W_{\text{total}}$)** | **899.4 s** (15.0 min) | **709.9 s** (11.8 min) | **630.8 s** (10.5 min) | **-11.1% total delay reduction** |
| **Steady-State Throughput (TPH)** | 1,098.4 TPH | 1,381.2 TPH | **1,591.4 TPH** | Smooth flow approaches crusher capacity |
| **Peak Haul Road Queue Size** | 7.8 trucks | 5.6 trucks | **1.2 trucks** | Elimination of steep downhill queues |
| **Safety Invariant Violations** | 14.2 incidents | 0.0 | **0.0** | Perfect collision-free operation |

---

## 3. Little's Law & Queue Relocation Truthfulness

> [!IMPORTANT]
> **AUDIT CLARIFICATION ON "WAITING TIME REDUCTION"**  
> Total mine cycle time cannot be magically eliminated when haul road speed is reduced by fog.  
> 
> According to Little's Law ($L = \lambda W$), when road capacity decreases, total delay must increase unless vehicles are dispatched less frequently.  
> 
> **What FOG-Orchestrator actually accomplishes:**  
> It relocates **707 seconds of hazardous, stationary queueing on a narrow, foggy 8% downhill haul ramp** into **safe, stationary waiting at the wide shovel loading benches and designated holding loops**. Total delay decreases modestly (-11.1%) due to the elimination of stop-and-go shockwaves, while catastrophic collision risk on the haul road is virtually eliminated.
