# ACTUATOR FAILURE BOUNDARY & HYDRAULIC SENSITIVITY AUDIT
**FOG-ORCHESTRATOR 2.0 — SIH 2026-27 | Phase 9.1 Hostile Integration Validation**  
**Role:** Lead Safety-Critical Systems Red-Team Engineer / HEMM Controls Engineer  
**Date:** 2026-09-24  
**Audit Status:** AUDITED — HYDRAULIC LAG UNMASKED AS PRINCIPAL SAFETY CONSTRAINT

---

## 1. Actuator Classification & Evidence Reality Check

A central assertion in heavy equipment collision avoidance is that commanding full deceleration results in instantaneous or near-instantaneous retarder/friction braking.

### Honest Evidence Classification
- **Physical BEML / Caterpillar Hydraulic Braking:** **LEVEL F (Engineering Assumption)** / **LEVEL E (Literature Derived)**.
- **Repository Truth:** The physical test bench uses an **ESP32-S3 microcontroller coupled to an LED/MOSFET indicator and a Saleae logic analyzer on the TWAI CAN bus**. No 100-tonne hydraulic calipers, no air-over-hydraulic master cylinders, and no wet-disc brake packs were actuated.
- **Prohibited Claim:** The project MUST NOT claim *"Actual HEMM braking response physically validated at Bailadila"*.
- **Accurate Downgraded Claim:** *"HEMM braking dynamics modelled using OEM Caterpillar 777D / BEML literature parameters; electronic command generation validated in HIL; hydraulic lag treated as parametric variable."*

---

## 2. Downhill Deceleration Dynamics on -8% Mine Haul Road

Under DGMS safety guidelines, mine haul ramps operate at grades up to **-8%** (downhill). On wet or slippery crushed iron ore surfaces, the effective tire-road friction coefficient degrades to **$\mu = 0.35$**.

The net physical deceleration available to the vehicle is governed by:

$$a_{\text{dec}} = g \cdot (\mu \cdot \cos\theta - \sin\theta)$$

For a grade of $-8\%$ ($\theta \approx -4.57^{\circ}$, $\sin\theta \approx -0.0797$, $\cos\theta \approx 0.9968$):

$$a_{\text{dec}} = 9.81 \cdot (0.35 \cdot 0.9968 - 0.0797) = 9.81 \cdot (0.3489 - 0.0797) = 2.641\text{ m/s}^2$$

Compare this with flat dry ground where $a_{\text{dec}} = 0.70 \cdot 9.81 = 6.87\text{ m/s}^2$. **Gravity robs the truck of more than 61% of its braking effectiveness.**

The total stopping distance is:

$$S_{\text{stop}} = v_0 \cdot \tau_{\text{total}} + \frac{v_0^2}{2 \cdot a_{\text{dec}}}$$

where $\tau_{\text{total}} = T_{\text{electronic}} + T_{\text{actuator}} = 0.1871\text{ s} + T_{\text{actuator}}$.

---

## 3. Parametric Sensitivity Analysis

We evaluate stopping distance across actuator lag increments from **250 ms to 1000 ms** under two critical visibility conditions:
1. **Dense Fog Floor:** $R_{\text{eff}} = 8.0\text{ m}$ (Governed crawl speed $v_0 = 3.52\text{ m/s} = 12.67\text{ km/h}$, Standstill buffer $S_{\text{base}} = 5.0\text{ m}$, Max stopping budget $S_{\text{budget}} = 3.0\text{ m}$).
2. **Patchy Fog Condition:** $R_{\text{eff}} = 12.0\text{ m}$ (Governed speed $v_0 = 4.50\text{ m/s} = 16.20\text{ km/h}$, Standstill buffer $S_{\text{base}} = 5.0\text{ m}$, Max stopping budget $S_{\text{budget}} = 7.0\text{ m}$).

### Table 1: Dense Fog ($R_{\text{eff}} = 8.0\text{ m}$, $v_0 = 3.52\text{ m/s}$, $a_{\text{dec}} = 2.64\text{ m/s}^2$)

| Actuator Delay $T_{\text{act}}$ (ms) | Total Reaction $\tau_{\text{total}}$ (s) | Reaction Dist (m) | Braking Dist (m) | Total $S_{\text{stop}}$ (m) | Available Sightline (m) | Residual Buffer Margin (m) | Invariant Status |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **250 (Baseline)** | 0.4371 | 1.539 | 2.346 | **3.885** | 8.0 | **-0.885** (Buffer = 4.115 m) | **BUFFER ERODED** |
| **300** | 0.4871 | 1.715 | 2.346 | **4.061** | 8.0 | **-1.061** (Buffer = 3.939 m) | **BUFFER ERODED** |
| **350** | 0.5371 | 1.891 | 2.346 | **4.237** | 8.0 | **-1.237** (Buffer = 3.763 m) | **BUFFER ERODED** |
| **400** | 0.5871 | 2.067 | 2.346 | **4.413** | 8.0 | **-1.413** (Buffer = 3.587 m) | **BUFFER ERODED** |
| **500** | 0.6871 | 2.419 | 2.346 | **4.765** | 8.0 | **-1.765** (Buffer = 3.235 m) | **BUFFER ERODED** |
| **750** | 0.9371 | 3.299 | 2.346 | **5.645** | 8.0 | **-2.645** (Buffer = 2.355 m) | **BUFFER ERODED** |
| **1000** | 1.1871 | 4.179 | 2.346 | **6.525** | 8.0 | **-3.525** (Buffer = 1.475 m) | **BUFFER ERODED** |
| **1420 (Physical Impact)** | 1.6071 | 5.654 | 2.346 | **8.000** | 8.0 | **-5.000** (Buffer = 0.000 m) | **COLLISION** |

### Table 2: Moderate Fog ($R_{\text{eff}} = 12.0\text{ m}$, $v_0 = 4.50\text{ m/s}$, $a_{\text{dec}} = 2.64\text{ m/s}^2$)

| Actuator Delay $T_{\text{act}}$ (ms) | Total Reaction $\tau_{\text{total}}$ (s) | Reaction Dist (m) | Braking Dist (m) | Total $S_{\text{stop}}$ (m) | Available Sightline (m) | Residual Buffer Margin (m) | Invariant Status |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **250 (Baseline)** | 0.4371 | 1.967 | 3.835 | **5.802** | 12.0 | **+1.198** (Buffer = 6.198 m) | **SAFE** |
| **300** | 0.4871 | 2.192 | 3.835 | **6.027** | 12.0 | **+0.973** (Buffer = 5.973 m) | **SAFE** |
| **350** | 0.5371 | 2.417 | 3.835 | **6.252** | 12.0 | **+0.748** (Buffer = 5.748 m) | **SAFE** |
| **400** | 0.5871 | 2.642 | 3.835 | **6.477** | 12.0 | **+0.523** (Buffer = 5.523 m) | **SAFE** |
| **500** | 0.6871 | 3.092 | 3.835 | **6.927** | 12.0 | **+0.073** (Buffer = 5.073 m) | **SAFE** |
| **750** | 0.9371 | 4.217 | 3.835 | **8.052** | 12.0 | **-1.052** (Buffer = 3.948 m) | **BUFFER ERODED** |
| **1000** | 1.1871 | 5.342 | 3.835 | **9.177** | 12.0 | **-2.177** (Buffer = 2.823 m) | **BUFFER ERODED** |

---

## 4. Key Red-Team Findings & Quantitative Cliff Edges

### Finding 1: The Canonical Crawl Speed ($3.52\text{ m/s}$) Erodes the 5-Meter Buffer on Downhill Ramps
- In $8.0\text{ m}$ visibility on flat ground ($\mu=0.7$), $a_{\text{dec}} = 6.87\text{ m/s}^2$, and stopping distance is only $2.44\text{ m}$, leaving a generous $5.56\text{ m}$ buffer ($> 5.0\text{ m}$).
- However, on a **$-8\%$ downhill ramp with wet mud ($\mu=0.35$)**, stopping distance expands to **$3.885\text{ m}$**.
- While the truck **does not physically strike the obstacle** (it stops at $3.885\text{ m} < 8.0\text{ m}$, leaving a physical clearance of $4.115\text{ m}$), **the claimed $5.0\text{ m}$ safety buffer is violated by $88.5\text{ cm}$**.
- **Calculated Failure Threshold:** For $8.0\text{ m}$ sightline and $v_0 = 3.52\text{ m/s}$, the maximum allowable actuator delay to maintain a strict $5.0\text{ m}$ buffer is:

$$T_{\text{actuator\_crit}} = \frac{3.0 - 2.346}{3.52} - 0.1871 = 0.1858 - 0.1871 = \mathbf{-1.4\text{ ms}}$$

**Conclusion:** At $3.52\text{ m/s}$, the strict 5.0 m buffer is **mathematically impossible to maintain on a -8% wet ramp**, even with an instantaneous zero-latency actuator!

### Finding 2: Actual Physical Collision Boundary
- A physical collision with the obstacle ($S_{\text{stop}} > 8.0\text{ m}$) occurs when actuator lag exceeds:

$$T_{\text{collision\_threshold}} = \frac{8.0 - 2.346}{3.52} - 0.1871 = 1.606 - 0.1871 = \mathbf{1419\text{ ms}}$$

Any mechanical hydraulic failure, vapor lock, or thermal brake fade exceeding **1.42 seconds** results in an unrecoverable high-energy collision in dense fog.

---

## 5. Engineering Remedy & Parameter Revision

To guarantee the non-negotiable invariant $S_{\text{stop}} \le R_{\text{eff}} - S_{\text{base}}$ on a $-8\%$ downhill ramp with $T_{\text{actuator}} = 250\text{ ms}$, the crawl speed in $8.0\text{ m}$ fog must be revised downwards.

Solving for maximum speed $v_{\text{max\_safe}}$:

$$v_0 \cdot (0.4371) + \frac{v_0^2}{2 \cdot 2.641} \le 3.00$$

$$0.1893 \cdot v_0^2 + 0.4371 \cdot v_0 - 3.00 = 0$$

Using the quadratic formula:

$$v_0 = \frac{-0.4371 + \sqrt{0.4371^2 - 4 \cdot 0.1893 \cdot (-3.00)}}{2 \cdot 0.1893} = \frac{-0.4371 + \sqrt{0.1911 + 2.2716}}{0.3786} = \frac{-0.4371 + 1.5693}{0.3786} = \mathbf{2.990\text{ m/s}} = \mathbf{10.77\text{ km/h}}$$

### Proposed Parameter Revision: `CONFIG_REV_9_1_02`
- **Current Canonical Crawl Speed:** $3.52\text{ m/s}$ ($12.67\text{ km/h}$).
- **Revised Downhill (-8%) Crawl Speed:** **$2.99\text{ m/s}$ ($10.76\text{ km/h}$)**.
- **Result:** Fully preserves the $5.0\text{ m}$ DGMS standstill buffer under full hydraulic worst-case latency ($250\text{ ms}$).
