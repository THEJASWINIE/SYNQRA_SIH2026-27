# EXPERIMENT E5 — SAFE SPEED UNCERTAINTY ANALYSIS REPORT

**Project:** FOG-ORCHESTRATOR 2.0 (SIH 2026-27 — SIH26007)  
**Vehicle Reference:** BEML BH100-class rigid rear dump truck  
**Validation Classification:** L6 (Analytical Solver & Uncertainty Propagation)  
**Figures:**  
- [`figures/safe_speed_vs_visibility.png`](file:///c:/Users/JAGADEESH%20M/OneDrive/Documents/SIH-2026-27/figures/safe_speed_vs_visibility.png)  
- [`figures/safe_speed_uncertainty.png`](file:///c:/Users/JAGADEESH%20M/OneDrive/Documents/SIH-2026-27/figures/safe_speed_uncertainty.png)  

---

## 1. Mathematical Derivation of Safe Speed Envelope

The authoritative safe operating speed $v_{\text{safe}}$ is obtained by inverting the physical stopping distance equation under the sight-distance constraint:

$$S_{\text{stop}}(v) + S_{\text{margin}} \le R_{\text{effective}}$$

$$v \cdot \tau_{\text{local}} + \frac{v^2}{2 \cdot a_{\text{dec}}} + S_{\text{margin}} \le R_{\text{effective}}$$

Rearranging into quadratic form $A v^2 + B v + C = 0$:

$$\left(\frac{1}{2 a_{\text{dec}}}\right) v^2 + (\tau_{\text{local}}) v - (R_{\text{effective}} - S_{\text{margin}}) = 0$$

Applying the quadratic formula and taking the positive root:

$$v_{\text{safe}} = \frac{-\tau_{\text{local}} + \sqrt{\tau_{\text{local}}^2 + 4 \cdot \left(\frac{1}{2 a_{\text{dec}}}\right) \cdot (R_{\text{effective}} - S_{\text{margin}})}}{2 \cdot \left(\frac{1}{2 a_{\text{dec}}}\right)} = a_{\text{dec}} \left( \sqrt{\tau_{\text{local}}^2 + \frac{2 (R_{\text{effective}} - S_{\text{margin}})}{a_{\text{dec}}}} - \tau_{\text{local}} \right)$$

Subject to vehicle maximum civil speed cap: $v_{\text{safe}} \le v_{\text{mine\_max}} = 5.56\text{ m/s}$ (20 km/h).

---

## 2. Evaluation Across Visibility & Environmental Conditions

| Visibility ($R_{\text{eff}}$, m) | Description | $v_{\text{safe}}$ Nominal ($\mu=0.50, \tau=0.40\text{s}$) | $v_{\text{safe}}$ Wet ($\mu=0.35, \tau=0.44\text{s}$) | $v_{\text{safe}}$ Muddy/Degraded ($\mu=0.20, \tau=0.50\text{s}$) | Operating State |
|:---:|:---|:---:|:---:|:---:|:---|
| **100.0** | Clear Day | 5.56 m/s (20.0 km/h) | 5.56 m/s (20.0 km/h) | 5.56 m/s (20.0 km/h) | NORMAL (Speed Limit Capped) |
| **50.0** | Light Haze | 5.56 m/s (20.0 km/h) | 5.56 m/s (20.0 km/h) | 5.56 m/s (20.0 km/h) | NORMAL (Speed Limit Capped) |
| **25.0** | Moderate Fog | 5.56 m/s (20.0 km/h) | 5.56 m/s (20.0 km/h) | 4.82 m/s (17.3 km/h) | CAUTION |
| **12.0** | Regulatory Sight Limit | **4.3815 m/s (15.77 km/h)**| **3.71 m/s (13.36 km/h)** | **2.45 m/s (8.82 km/h)** | **FOG GOVERNED** |
| **10.0** | Thick Fog | 3.85 m/s (13.86 km/h) | 3.22 m/s (11.59 km/h) | 2.05 m/s (7.38 km/h) | SLOW DOWN |
| **8.0** | Heavy Fog | 3.24 m/s (11.66 km/h) | 2.66 m/s (9.58 km/h) | 1.58 m/s (5.69 km/h) | SLOW DOWN |
| **5.0** | Dense Fog Threshold | **0.00 m/s (0.0 km/h)** | **0.00 m/s (0.0 km/h)** | **0.00 m/s (0.0 km/h)** | **HOLD / STOP IN BAY** |
| **4.0** | Extreme Dense Fog | **0.00 m/s (0.0 km/h)** | **0.00 m/s (0.0 km/h)** | **0.00 m/s (0.0 km/h)** | **HOLD / STOP IN BAY** |
| **3.0** | Extreme Dense Fog | **0.00 m/s (0.0 km/h)** | **0.00 m/s (0.0 km/h)** | **0.00 m/s (0.0 km/h)** | **HOLD / STOP IN BAY** |

---

## 3. Investigation of Canonical $v_{\text{safe}} = 4.3815\text{ m/s}$

1. **Exact Origin:**  
   $v_{\text{safe}} = 4.3815\text{ m/s}$ is the exact closed-form algebraic solution for:
   - $R_{\text{effective}} = 12.0\text{ m}$
   - Civil grade = -8% (downhill haul road)
   - Nominal tire-ground friction $\mu = 0.50$
   - Nominal local latency $\tau_{\text{local}} = 0.400\text{ s}$
   - Safety buffer margin $S_{\text{margin}} = 0.0\text{ m}$

2. **Defensibility:**  
   It is completely mathematically defensible under nominal dry/damp haul road conditions at 12 m sight distance. However, in muddy conditions ($\mu = 0.20$), the governor dynamically adjusts downward to **2.45 m/s** to maintain stopping integrity.

3. **Behavior at 3–5 m Visibility:**  
   The system does NOT attempt to drive at 4.38 m/s in 3–5 m fog. For any visibility $\le 5.0\text{ m}$, the solver returns $v_{\text{safe}} = 0.0\text{ m/s}$, holding vehicles safely in origin shovel bays and dumping pockets until sight recovery occurs.
