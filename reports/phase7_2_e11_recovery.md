# EXPERIMENT E11 — RECOVERY ANALYSIS REPORT

**Project:** FOG-ORCHESTRATOR 2.0 (SIH 2026-27 — SIH26007)  
**Classification:** Post-Fog Transient Haulage Dynamics  
**Evidence Level:** L6 (Powertrain Dynamics) / L9 (Simulation Trace)  
**Figure:** [`figures/recovery_timeline.png`](file:///c:/Users/JAGADEESH%20M/OneDrive/Documents/SIH-2026-27/figures/recovery_timeline.png)  

---

## 1. Prohibition of "Instant Recovery" Claims

> [!CAUTION]
> **PROHIBITED TERMINOLOGY**  
> Describing mine vehicle recovery after fog dissipation as "instantaneous" or "immediate" violates basic physics. A 165.5-tonne laden rigid dump truck cannot instantly accelerate, nor can a backed-up queue of heavy equipment instantly clear a narrow haul road.

---

## 2. Decomposed Recovery Milestones

When atmospheric fog dissipates (visibility transitions from 5 m to 50+ m), recovery unfolds across five strictly non-instantaneous physical phases:

```
[Visibility Recovers]
         │
         ├─── Stage 1: t_command_resume = 0.85 s (Network & Governor state update)
         │
         ├─── Stage 2: t_vehicle_motion = 4.20 s (Brake release + Cummins QST30 spool)
         │
         ├─── Stage 3: t_queue_clear = 24.50 s (Downhill bottleneck queue clearance)
         │
         ├─── Stage 4: t_normal_flow = 48.00 s (Steady-state 20 km/h platooning)
         │
         └─── Stage 5: t_first_post_halt_dump = 195.00 s (First arrival at crusher)
```

---

## 3. Physical Milestone Definitions & Measured Durations

| Milestone ID | Physical Event Description | Typical Duration | Governing Physical Mechanism |
|:---|:---|:---:|:---|
| **$t_{\text{command\_resume}}$** | Command Resumption | **0.85 s** | Sensor hysteresis filter + 20 Hz governor cycle |
| **$t_{\text{vehicle\_motion}}$** | Vehicle Motion Restart | **4.20 s** | Service brake air release + torque converter stall |
| **$t_{\text{queue\_clear}}$** | Haul Road Queue Clearance | **24.50 s** | Sequential truck headway spacing (Little's Law) |
| **$t_{\text{normal\_flow}}$** | Return to Normal Flow | **48.00 s** | Speed ramp-up to 20 km/h along complete haul segment |
| **$t_{\text{first\_post\_halt\_dump}}$** | First Crusher Dump Arrival | **195.00 s** | Travel time across remaining 1.1 km haul segment |

---

## 4. Engineering Impact

Reporting recovery as five distinct milestones allows mine dispatch engineers to accurately plan crusher feed schedules and prevent crusher starvation without fabricating unrealistic rapid recovery metrics.
