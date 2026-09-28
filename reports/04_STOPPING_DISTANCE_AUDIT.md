# 04 — RECOMPUTED STOPPING DISTANCE AUDIT REPORT

**Project:** FOG-ORCHESTRATOR 2.0 (SIH 2026-27 — SIH26007)  
**Classification:** Vehicle Longitudinal Dynamics & Stopping Distance Reconciliation  
**Dataset Reference:** [`data/phase7_3_stopping_distance.csv`](file:///c:/Users/JAGADEESH%20M/OneDrive/Documents/SIH-2026-27/data/phase7_3_stopping_distance.csv) (2,835 calculated configurations)  
**Date of Audit:** 2026-09-18  

---

## 1. Explicit Definition of $R_{\text{effective}}$ vs. Related Terms

To prevent conflation of sensory and geometric constraints, FOG-ORCHESTRATOR 2.0 establishes explicit physical boundaries:

1. **Atmospheric Visibility ($V_{\text{atm}}$):** Meteorological optical range defined by Koschmieder's Law (transmission contrast threshold $\epsilon = 0.05$).
2. **Line-of-Sight Range ($R_{\text{los}}$):** Unobstructed straight-line ray between vehicle sensor and target without terrain occlusion.
3. **Sensor Range ($R_{\text{sensor}}$):** Maximum operational detection range of onboard 77 GHz radar ($150\text{ m}$), LiDAR ($80\text{ m}$ in clear, $< 15\text{ m}$ in fog), or camera.
4. **Road Geometric Sight Distance ($S_{\text{geom}}$):** Maximum sightline allowed by horizontal bench switchbacks ($R_{\text{curve}} = 10.8\text{ m}$) or vertical crest curves.
5. **Stopping Range / Distance ($S_{\text{stop}}$):** Total kinematic distance traveled from perception trigger to standstill.
6. **Effective Visible Range ($R_{\text{effective}}$):**  
   $$R_{\text{effective}} = \min(V_{\text{atm}}, R_{\text{sensor}}, S_{\text{geom}})$$
   This is the true operational distance available for safe stopping.

---

## 2. Deceleration Modeling ($a_{\text{dec}}$) Across Canonical Surfaces

Effective retarding deceleration is governed by:

$$a_{\text{dec}} = \frac{F_{\text{brake\_effective}} + F_{\text{roll}} + F_{\text{aero}} - F_{\text{grade}}}{m}$$

Where:
- $F_{\text{brake\_effective}} \le \min(F_{\text{hardware\_max}}, \mu \cdot m \cdot g \cdot \cos\theta)$
- $F_{\text{grade}} = m \cdot g \cdot \sin\theta_{\text{physics}} = -m \cdot g \cdot \sin\theta_{\text{civil}}$
- On a **$-8.0\%$ downhill ramp**, gravity assists vehicle motion, reducing retarding deceleration.

| Surface Condition | Operating Mass ($m$, kg) | Civil Grade | Friction ($\mu$) | Rolling Coeff ($c_{\text{rr}}$) | Effective $a_{\text{dec}}$ ($\text{m/s}^2$) | Primary Braking Limit |
|:---|:---:|:---:|:---:|:---:|:---:|:---|
| **LADEN_DOWNHILL_DRY** | 165,500 | -8.0% | 0.50 | 0.025 | **$4.209\text{ m/s}^2$** | Retarder + Service Disc |
| **LADEN_DOWNHILL_WET** | 165,500 | -8.0% | 0.35 | 0.035 | **$2.738\text{ m/s}^2$** | Traction Friction Boundary |
| **EMPTY_DOWNHILL_WET** | 74,000 | -8.0% | 0.35 | 0.035 | **$2.748\text{ m/s}^2$** | Service Disc Friction |
| **LADEN_FLAT_WET** | 165,500 | 0.0% | 0.35 | 0.035 | **$3.432\text{ m/s}^2$** | Normal Friction Retarding |
| **LADEN_DOWNHILL_MUD** | 165,500 | -8.0% | 0.20 | 0.040 | **$1.267\text{ m/s}^2$** | Degraded Slurry Slip Limit |

---

## 3. Stopping Distance Matrix (Laden Downhill Wet: $-8.0\%$, $\mu = 0.35$, $a_{\text{dec}} = 2.738\text{ m/s}^2$)

| Speed (km/h) | Speed (m/s) | Latency Tier | Latency ($\tau$, s) | Reaction Dist $d_{\text{react}}$ (m) | Braking Dist $d_{\text{brake}}$ (m) | Total $S_{\text{stop}}$ (m) | Margin at 12 m ($R_{\text{eff}} - S_{\text{stop}}$) | Non-Colliding? |
|:---:|:---:|:---|:---:|:---:|:---:|:---:|:---:|:---:|
| **20.0** | 5.556 | Local P50 | 0.324 | 1.800 | 5.636 | **7.436 m** | **+4.564 m** | **YES** |
| **20.0** | 5.556 | Local Nominal | 0.375 | 2.083 | 5.636 | **7.719 m** | **+4.281 m** | **YES** |
| **20.0** | 5.556 | Local P95 | 0.399 | 2.217 | 5.636 | **7.853 m** | **+4.147 m** | **YES** |
| **20.0** | 5.556 | Local P99 | 0.437 | 2.428 | 5.636 | **8.064 m** | **+3.936 m** | **YES** |
| **20.0** | 5.556 | Local Worst Meas. | 0.489 | 2.717 | 5.636 | **8.353 m** | **+3.647 m** | **YES** |
| **20.0** | 5.556 | Local Conservative | 0.550 | 3.056 | 5.636 | **8.692 m** | **+3.308 m** | **YES** |
| **20.0** | 5.556 | **Human Baseline** | **1.200** | **6.667** | **5.636** | **12.303 m** | **-0.303 m** | **NO (COLLISION)** |
| **15.0** | 4.167 | Local Nominal | 0.375 | 1.563 | 3.170 | **4.733 m** | **+7.267 m** | **YES** |
| **15.0** | 4.167 | Local Conservative | 0.550 | 2.292 | 3.170 | **5.462 m** | **+6.538 m** | **YES** |
| **15.0** | 4.167 | Human Baseline | 1.200 | 5.000 | 3.170 | **8.170 m** | **+3.830 m** | **YES** |
| **10.0** | 2.778 | Local Nominal | 0.375 | 1.042 | 1.409 | **2.451 m** | **+9.549 m** | **YES** |
| **10.0** | 2.778 | Human Baseline | 1.200 | 3.333 | 1.409 | **4.742 m** | **+7.258 m** | **YES** |
| **5.0** | 1.389 | Local Nominal | 0.375 | 0.521 | 0.352 | **0.873 m** | **+11.127 m** | **YES** |
| **3.6 (1 m/s)** | 1.000 | Local Nominal | 0.375 | 0.375 | 0.183 | **0.558 m** | **+11.442 m** | **YES** |

---

## 4. Key Engineering Takeaways

1. **Human Operator Point of Inevitable Collision:**  
   At 20 km/h on a wet -8% haul road, a human operator with AASHTO standard reaction time ($1.20\text{ s}$) travels **$6.67\text{ m}$** before brake line pressure begins to build. Adding the mechanical braking distance of **$5.64\text{ m}$** yields **$12.30\text{ m}$ total stopping distance**, causing an unavoidable impact with any stationary obstacle detected at the regulatory 12 m sight limit.

2. **Autonomous Governor Headroom:**  
   Under identical physical conditions, the autonomous local safety governor with P99 reaction latency ($0.437\text{ s}$) stops the 165.5-tonne laden truck in **$8.06\text{ m}$**, preserving a **$+3.94\text{ m}$ safety cushion**. Even under the conservative worst-case scenario ($0.550\text{ s}$ latency), total stopping distance is **$8.69\text{ m}$**, leaving a **$+3.31\text{ m}$ safety margin**.
