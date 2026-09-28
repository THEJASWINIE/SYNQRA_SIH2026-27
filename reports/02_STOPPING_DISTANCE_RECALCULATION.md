# 02 — STOPPING DISTANCE FORENSIC RECALCULATION
## FOG-ORCHESTRATOR 2.0 — PHASE 7.3.1 AUDIT REPORT

| Document ID | Canonical File Path | Date | Audit Status | Dataset Reference |
| :--- | :--- | :--- | :--- | :--- |
| **REP-731-02** | `reports/02_STOPPING_DISTANCE_RECALCULATION.md` | 2026-09-18 | **FROZEN / LOCKED** | `data/phase7_3_stopping_distance.csv` |

---

### 1. Primary Failure Investigation & Mathematical Dissection

The Phase 7.3 documentation contained a critical internal numerical contradiction:
- It stated a local nominal latency of $\tau_{\text{local}} = 0.375\text{ s}$.
- It listed a nominal stopping deceleration of $a_{\text{dec}} = 1.20\text{ m/s}^2$.
- It reported a safe speed of $v_{\text{safe}} \approx 5.12\text{ m/s}$ at $12.0\text{ m}$ visibility.
- It asserted that the resulting stopping distance was "approximately $7.0\text{ m}$", fitting within the available $7.0\text{ m}$ kinematic envelope ($12.0\text{ m} - 5.0\text{ m}$ buffer).

#### Independent Recalculation:
Using the authoritative Newtonian stopping distance equation:
$$S_{\text{stop}} = v \cdot \tau_{\text{local}} + \frac{v^2}{2 \cdot a_{\text{dec}}}$$

Evaluating for the stated values:
* Velocity: $v = 5.1200\text{ m/s}$ ($18.43\text{ km/h}$)
* Local Latency: $\tau_{\text{local}} = 0.3750\text{ s}$
* Deceleration: $a_{\text{dec}} = 1.2000\text{ m/s}^2$
* Mandatory Standstill Safety Margin: $S_{\text{margin}} = 5.0000\text{ m}$
* Effective Visibility: $R_{\text{effective}} = 12.0000\text{ m}$
* Available Kinematic Range: $R_{\text{available}} = R_{\text{effective}} - S_{\text{margin}} = 12.0 - 5.0 = \mathbf{7.0000\text{ m}}$

$$\text{Reaction Distance: } d_{\text{react}} = 5.1200 \times 0.3750 = \mathbf{1.9200\text{ m}}$$
$$\text{Braking Distance: } d_{\text{brake}} = \frac{5.1200^2}{2 \times 1.2000} = \frac{26.2144}{2.4000} = \mathbf{10.9227\text{ m}}$$
$$\text{Total Stopping Distance: } S_{\text{stop}} = 1.9200 + 10.9227 = \mathbf{12.8427\text{ m}}$$
$$\text{Total Stopping Distance Required: } S_{\text{total}} = S_{\text{stop}} + S_{\text{margin}} = 12.8427 + 5.0000 = \mathbf{17.8427\text{ m}}$$
$$\text{Clearance Margin Remaining: } R_{\text{effective}} - S_{\text{stop}} = 12.0000 - 12.8427 = \mathbf{-0.8427\text{ m}}$$

```
====================================================================================================
CRITICAL FORENSIC CONTRADICTION IDENTIFIED:
1. Stopping distance S_stop = 12.84 m EXCEEDS the available kinematic budget (7.00 m) by 5.84 m!
2. Total distance required (17.84 m) EXCEEDS the entire sightline (12.00 m) by 5.84 m!
3. If an evaluator evaluates a vehicle at 5.12 m/s with a_dec = 1.20 m/s^2, the truck will fail to stop
   and will collide into the obstacle at 12 m with an impact velocity of 1.42 m/s!
====================================================================================================
```

---

### 2. Root Cause of the Discrepancy

Where did $5.12\text{ m/s}$ come from?
In `fog_safe/safety.py`, the quadratic solver did **not** use $a_{\text{dec}} = 1.20\text{ m/s}^2$. It used the **physical net retarding deceleration on an $-8.0\%$ downhill grade**:
$$a_{\text{dec, net}} = \frac{F_{\text{brake, max}} + F_{\text{roll}} - F_{\text{grade}}}{m} \approx \mathbf{2.7466\text{ m/s}^2}$$

Evaluating $S_{\text{stop}}$ with the true physical deceleration ($a = 2.7466\text{ m/s}^2$) under P99 latency ($\tau = 0.437\text{ s}$):
$$d_{\text{react}} = 5.1158 \times 0.4370 = 2.2356\text{ m}$$
$$d_{\text{brake}} = \frac{5.1158^2}{2 \times 2.7466} = \frac{26.1714}{5.4932} = 4.7643\text{ m}$$
$$S_{\text{stop}} = 2.2356 + 4.7643 = \mathbf{7.000\text{ m}}$$
$$S_{\text{total}} = 7.000 + 5.000 = \mathbf{12.000\text{ m}} = R_{\text{effective}}$$

**The Editorial Error**: Phase 7.3 accidentally copied $a_{\text{dec}} = 1.20\text{ m/s}^2$ (an unverified service retarding / comfort assumption) into the canonical summary table while simultaneously reporting the safe speed ($5.12\text{ m/s}$) that physically required $a_{\text{dec}} = 2.75\text{ m/s}^2$.

---

### 3. Canonical Dual-Deceleration Framework

To eliminate all ambiguity, the system formalizes two explicit operational deceleration regimes:

* **REGIME A — Conservative Service Braking ($a_{\text{dec}} = 1.20\text{ m/s}^2$)**:  
  Used when operating under gentle service braking or degraded tire adhesion where high deceleration is unacceptable. Under this regime, safe speed at $12\text{ m}$ visibility **must be clamped to $3.6734\text{ m/s}$ ($13.22\text{ km/h}$)** to stop within $7.0\text{ m}$.
* **REGIME B — Emergency Friction-Limited Retarding ($a_{\text{dec}} = 2.7466\text{ m/s}^2$)**:  
  Used during full emergency service braking where all available tire-road adhesion ($\mu = 0.35$) is commanded. Under this regime, safe speed at $12\text{ m}$ visibility is **$5.1158\text{ m/s}$ ($18.42\text{ km/h}$)** under P99 latency, stopping exactly in $7.00\text{ m}$.

---

### 4. Comprehensive Stopping Distance Table (at 12.0 m Visibility)

| Scenario / Deceleration Regime | $a_{\text{dec}}$ ($\text{m/s}^2$) | Latency Scenario | $\tau_{\text{local}}$ (s) | Velocity $v$ ($\text{m/s}$) | $d_{\text{react}}$ (m) | $d_{\text{brake}}$ (m) | $S_{\text{stop}}$ (m) | $S_{\text{margin}}$ (m) | $S_{\text{total}}$ (m) | Clearance Margin (m) | Safety Status |
| :--- | :---: | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Phase 7.3 Erroneous Claim** | 1.2000 | Nominal | 0.375 | 5.1200 | 1.9200 | 10.9227 | **12.8427** | 5.0000 | 17.8427 | **-0.8427** | **COLLISION** |
| **Corrected Service Regime** | 1.2000 | Nominal | 0.375 | **3.6734** | 1.3775 | 5.6225 | **7.0000** | 5.0000 | 12.0000 | +5.0000 | **SAFE** |
| **Corrected Service Regime** | 1.2000 | P95 Bound | 0.412 | **3.6334** | 1.4970 | 5.5030 | **7.0000** | 5.0000 | 12.0000 | +5.0000 | **SAFE** |
| **Corrected Service Regime** | 1.2000 | P99 Bound | 0.437 | **3.6078** | 1.5766 | 5.4234 | **7.0000** | 5.0000 | 12.0000 | +5.0000 | **SAFE** |
| **Corrected Service Regime** | 1.2000 | Worst-Case | 0.475 | **3.5682** | 1.6949 | 5.3051 | **7.0000** | 5.0000 | 12.0000 | +5.0000 | **SAFE** |
| **Emergency Friction Regime**| 2.7466 | Nominal | 0.375 | **5.2560** | 1.9710 | 5.0290 | **7.0000** | 5.0000 | 12.0000 | +5.0000 | **SAFE** |
| **Emergency Friction Regime**| 2.7466 | P95 Bound | 0.412 | **5.1610** | 2.1263 | 4.8737 | **7.0000** | 5.0000 | 12.0000 | +5.0000 | **SAFE** |
| **Emergency Friction Regime**| 2.7466 | P99 Bound | 0.437 | **5.1158** | 2.2356 | 4.7644 | **7.0000** | 5.0000 | 12.0000 | +5.0000 | **SAFE** |
| **Emergency Friction Regime**| 2.7466 | Worst-Case | 0.475 | **5.0321** | 2.3903 | 4.6097 | **7.0000** | 5.0000 | 12.0000 | +5.0000 | **SAFE** |
| **Slick Wet Ramp Regime** | 2.4926 | P99 Bound | 0.437 | **4.9176** | 2.1490 | 4.8510 | **7.0000** | 5.0000 | 12.0000 | +5.0000 | **SAFE** |
| **Dry Clean Ramp Regime** | 2.7856 | P99 Bound | 0.437 | **5.1451** | 2.2484 | 4.7516 | **7.0000** | 5.0000 | 12.0000 | +5.0000 | **SAFE** |
| **ISO 3450 Flat Ground** | 3.3230 | P99 Bound | 0.437 | **5.5214** | 2.4129 | 4.5871 | **7.0000** | 5.0000 | 12.0000 | +5.0000 | **SAFE** |

Every row has been verified against `data/phase7_3_stopping_distance.csv`. The mathematical contradiction is permanently closed.
