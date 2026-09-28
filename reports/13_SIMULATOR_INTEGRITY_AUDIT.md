# 13 — SIMULATOR NUMERICAL INTEGRITY AUDIT REPORT

**Project:** FOG-ORCHESTRATOR 2.0 (SIH 2026-27 — SIH26007)  
**Classification:** Numerical Verification, Unit Consistency & Discrete-Event Logic Audit  
**Date of Audit:** 2026-09-18  

---

## 1. Audit Scope & Verification Standard

A forensic line-by-line inspection of the simulation engine (`fog_orchestrator/simulation/simulator.py`, `fog_safe/`, and `integration_adapters/`) was executed to eliminate numerical integration artifacts, phantom throughput multipliers, and unit conversion discrepancies.

---

## 2. Integrity Audit Checklist

| Potential Simulator Defect | Code Location Inspected | Audit Finding & Verification | Integrity Status |
|:---|:---|:---|:---:|
| **Double Time-Stepping** | `fog_orchestrator/simulation/simulator.py:step()` | Verified: exactly one $\Delta t = 0.050\text{ s}$ advancement per simulation tick. Verified in [`tests/test_simulation_single_timestep.py`](file:///c:/Users/JAGADEESH%20M/OneDrive/Documents/SIH-2026-27/tests/test_simulation_single_timestep.py). | **CLEAN (PASS)** |
| **Double Velocity Integration** | `simulator.py` & `vehicle.py` | Verified: acceleration updates velocity once ($v_{t+1} = v_t + a \Delta t$); position updates once ($x_{t+1} = x_t + v_{t+1} \Delta t$). | **CLEAN (PASS)** |
| **Target Speed Clamping** | `fail_safe_controller.py:process_command()` | Invariant I1 enforced: $v_{\text{applied}} = \min(v_{\text{command}}, v_{\text{safe}})$. No target speed can exceed local governor limit. | **CLEAN (PASS)** |
| **Stale Target Speed Retention**| `fail_safe_controller.py` | Watchdog timer checks command age: commands older than $1.0\text{ s}$ are rejected (`STALE_COMMAND`), forcing local safe crawl. | **CLEAN (PASS)** |
| **Queue Duplication** | `TwinStateStore` & `queue_model.py` | Truck spatial occupancy is managed via single authoritative `TwinStateStore`. A vehicle cannot appear in multiple zones simultaneously. | **CLEAN (PASS)** |
| **Initial Queue Flush Artifact**| `run_killer_experiment_5_levels()` | Identified root cause of historical 3,294 TPH: 10-minute queue purge at startup. Reconciled steady-state production over 2,200 s horizon. | **RECONCILED (PASS)**|
| **Unrealistic Starting Points** | `simulator.py` | Trucks initialize at shovel loading bays and holding pockets, with zero pre-buffered trucks on haul ramps. | **CLEAN (PASS)** |
| **Unrealistic Route Lengths** | Haul circuit topology | Haul road ramp is $1,500\text{ m}$ ($1.5\text{ km}$); return ramp is $1,500\text{ m}$; total circuit is $3,000\text{ m}$ (realistic for Deposit-5). | **CLEAN (PASS)** |
| **Unrealistic Service Rates** | Crusher cycle parameters | Primary gyratory crusher slot fixed at $T_{\text{slot}} = 200.0\text{ s}$ ($18\text{ dumps/hr}$), matching NMDC mechanical tipping limits. | **CLEAN (PASS)** |
| **Hidden Production Multipliers**| Throughput calculation | Production is strictly calculated as $\sum \text{Dumps} \times 91.5\text{ tonnes}$. No synthetic scale factors or multipliers exist. | **CLEAN (PASS)** |
| **Accidental Unit Conversions** | Whole codebase | Strict SI internally: velocity in $\text{m/s}$, distance in $\text{m}$, mass in $\text{kg}$, force in $\text{N}$, time in $\text{s}$. $\text{km/h}$ used for display only. | **CLEAN (PASS)** |
| **Visibility Unit Discrepancy** | `EnvironmentState` & sensors | Visibility verified strictly in meters ($R_{\text{eff}} \in [3.0, 100.0]\text{ m}$). | **CLEAN (PASS)** |
| **Grade Sign Inversion** | `GradeAdapter` | External civil $-8.0\%$ mapped to internal physics $+8.0\%$ downhill. Physical force balance monotonicity verified. | **CLEAN (PASS)** |

---

## 3. Certified Simulation Invariants

1. **Mass Conservation:** Ore moved cannot exceed payload times completed dump cycles.
2. **Kinematic Deceleration Upper Bound:** Deceleration is strictly capped by tire-road friction $\mu g \cos\theta$ and hardware caliper limits.
3. **Little's Law Alignment:** Average queue length equals arrival rate times average waiting duration ($L = \lambda W$).
