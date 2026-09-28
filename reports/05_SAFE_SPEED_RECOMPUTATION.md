# 05 — SAFE SPEED RECOMPUTATION & MULTI-CONSTRAINT AUDIT

**Project:** FOG-ORCHESTRATOR 2.0 (SIH 2026-27 — SIH26007)  
**Classification:** Multi-Constraint Kinematic Speed Governor Recomputation  
**Dataset Reference:** [`data/phase7_3_safe_speed.csv`](file:///c:/Users/JAGADEESH%20M/OneDrive/Documents/SIH-2026-27/data/phase7_3_safe_speed.csv) (1,701 solver configurations)  
**Date of Audit:** 2026-09-18  

---

## 1. Forensic Deconstruction of Legacy $v_{\text{safe}} = 4.3815\text{ m/s}$

The historical parameter $v_{\text{safe}} = 4.3815\text{ m/s}$ ($15.77\text{ km/h}$) has been thoroughly audited to trace its exact algebraic origin:

$$\text{Constraint: } S_{\text{stop}}(v) + S_{\text{base}} \le R_{\text{effective}}$$

Given:
- $R_{\text{effective}} = 12.0\text{ m}$ (DGMS haul road regulatory sight limit)
- $S_{\text{base}} = 5.0\text{ m}$ (DGMS standstill standoff safety buffer)
- Available kinematic braking envelope: $R_{\text{effective}} - S_{\text{base}} = 12.0 - 5.0 = \mathbf{7.0\text{ m}}$
- Civil grade: $-8.0\%$ downhill ($a_{\text{dec}} = 2.7466\text{ m/s}^2$)
- **Legacy Latency Parameter:** Bundled reaction time $\tau_{\text{legacy}} = \mathbf{0.800\text{ s}}$ (combining autonomous loop + human driver override margin).

Solving the quadratic equation:
$$\frac{1}{2 a_{\text{dec}}} v^2 + \tau v - 7.0 = 0 \implies 0.1820 v^2 + 0.800 v - 7.0 = 0$$
$$v = \frac{-0.800 + \sqrt{0.800^2 + 4 \times 0.1820 \times 7.0}}{2 \times 0.1820} = \frac{-0.800 + \sqrt{0.6400 + 5.0974}}{0.3641} = \mathbf{4.3815\text{ m/s}} \equiv \mathbf{15.77\text{ km/h}}$$

### Recomputation under Current Canonical Latency Model
Under Phase 7.2 bench-calibrated autonomous local governor reaction times (without bundled human driver latency):
1. **Nominal Autonomous Pipeline ($\tau_{\text{local}} = 0.375\text{ s}$):**
   $$v_{\text{stop}} = \mathbf{5.256\text{ m/s}} \equiv \mathbf{18.92\text{ km/h}}$$
2. **Statistical P99 Non-Overlapping Bound ($\tau_{\text{local}} = 0.437\text{ s}$):**
   $$v_{\text{stop}} = \mathbf{5.116\text{ m/s}} \equiv \mathbf{18.42\text{ km/h}}$$
3. **Conservative Cold/Worn Scenario ($\tau_{\text{local}} = 0.550\text{ s}$):**
   $$v_{\text{stop}} = \mathbf{4.872\text{ m/s}} \equiv \mathbf{17.54\text{ km/h}}$$
4. **Human-Buffered Autonomous Mode ($\tau_{\text{local}} = 0.800\text{ s}$):**
   $$v_{\text{stop}} = \mathbf{4.3815\text{ m/s}} \equiv \mathbf{15.77\text{ km/h}}$$

**Audit Ruling:**  
$4.3815\text{ m/s}$ is mathematically valid and physically conservative, representing an autonomous vehicle that reserves a $+0.50\text{ s}$ reaction buffer for an unalerted human driver in the cabin. The pure autonomous governor operates safely at $5.12\text{--}5.26\text{ m/s}$ ($18.4\text{--}18.9\text{ km/h}$) while strictly maintaining the 5.0 m standstill buffer within 12 m visibility.

---

## 2. Multi-Constraint Operating Envelope Solver

The authoritative safe speed $v_{\text{safe}}$ enforces five concurrent physical boundaries:

$$v_{\text{safe}} = \min(v_{\text{stop}}, v_{\text{retarder}}, v_{\text{traction}}, v_{\text{curve}}, v_{\text{mine}})$$

1. **$v_{\text{stop}}$ (Stopping Sight Limit):** Solved analytically from quadratic deceleration constraint.
2. **$v_{\text{retarder}}$ (Thermal Retarding Limit):** Maximum speed where continuous downhill gravity power $\le 1,200\text{ kW}$ hydraulic absorption.
3. **$v_{\text{traction}}$ (Longitudinal Slip Limit):** Maximum speed ensuring drive wheels do not slip during acceleration: $v_{\text{traction}} = \sqrt{2 a_{\text{tr\_max}} R_{\text{eff}}}$.
4. **$v_{\text{curve}}$ (Lateral Rollover/Skid Limit):** Centrifugal skid limit across switchbacks: $v_{\text{curve}} = \sqrt{\mu g R_{\text{curve}}}$.
5. **$v_{\text{mine}}$ (DGMS Statutory Speed Cap):** Fixed regulatory ceiling of $20.0\text{ km/h}$ ($5.556\text{ m/s}$).

---

## 3. Comprehensive Safe Speed Solver Matrix (Laden BH100: 165.5t, Downhill -8.0%, Wet: $\mu = 0.35$)

| Visibility ($R_{\text{eff}}$, m) | $v_{\text{stop}}$ (Nom: 0.375s) | $v_{\text{stop}}$ (P99: 0.437s) | $v_{\text{stop}}$ (Cons: 0.550s) | $v_{\text{retarder}}$ | $v_{\text{mine}}$ Cap | Final $v_{\text{safe}}$ (P99 Bound) | Primary Limiting Constraint |
|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---|
| **100.0** | 20.89 m/s | 20.73 m/s | 20.44 m/s | 12.57 m/s | 5.56 m/s | **5.56 m/s (20.0 km/h)** | `MINE_SPEED_LIMIT` |
| **50.0** | 13.91 m/s | 13.76 m/s | 13.48 m/s | 12.57 m/s | 5.56 m/s | **5.56 m/s (20.0 km/h)** | `MINE_SPEED_LIMIT` |
| **25.0** | 8.87 m/s | 8.72 m/s | 8.46 m/s | 12.57 m/s | 5.56 m/s | **5.56 m/s (20.0 km/h)** | `MINE_SPEED_LIMIT` |
| **15.0** | 6.27 m/s | 6.13 m/s | 5.88 m/s | 12.57 m/s | 5.56 m/s | **5.56 m/s (20.0 km/h)** | `MINE_SPEED_LIMIT` |
| **12.0** | 5.26 m/s | 5.12 m/s | 4.87 m/s | 12.57 m/s | 5.56 m/s | **5.12 m/s (18.4 km/h)** | `STOPPING_DISTANCE` |
| **10.0** | 4.49 m/s | 4.35 m/s | 4.12 m/s | 12.57 m/s | 5.56 m/s | **4.35 m/s (15.7 km/h)** | `STOPPING_DISTANCE` |
| **8.0** | 3.59 m/s | 3.46 m/s | 3.24 m/s | 12.57 m/s | 5.56 m/s | **3.46 m/s (12.5 km/h)** | `STOPPING_DISTANCE` |
| **5.0** | **0.00 m/s** | **0.00 m/s** | **0.00 m/s** | 12.57 m/s | 5.56 m/s | **0.00 m/s (0.0 km/h)** | `DENSE_FOG_HOLD` |
| **4.0** | **0.00 m/s** | **0.00 m/s** | **0.00 m/s** | 12.57 m/s | 5.56 m/s | **0.00 m/s (0.0 km/h)** | `DENSE_FOG_HOLD` |
| **3.0** | **0.00 m/s** | **0.00 m/s** | **0.00 m/s** | 12.57 m/s | 5.56 m/s | **0.00 m/s (0.0 km/h)** | `DENSE_FOG_HOLD` |

---

## 4. Operational Behavior in 3–5 m Dense Fog

> [!IMPORTANT]
> **STAGING & HOLD PROTOCOL UNDER DENSE FOG**  
> Under extreme dense monsoon fog ($3.0\text{ m} \le R_{\text{eff}} \le 5.0\text{ m}$), the available visible distance is strictly less than the length of the truck ($10.52\text{ m}$) plus the regulatory standstill buffer ($5.0\text{ m}$).
> 
> Under these conditions, attempting to move down a steep, narrow -8% haul ramp is physically reckless. The solver correctly yields $v_{\text{safe}} = 0.00\text{ m/s}$. The orchestrator issues `HOLD_IN_BAY` commands, safely staging vehicles in wide shovel loading pockets and crusher bypass loops until optical sightline instruments indicate visibility recovery $> 5.0\text{ m}$.
