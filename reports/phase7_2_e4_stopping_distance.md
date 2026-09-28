# EXPERIMENT E4 — STOPPING DISTANCE VALIDATION REPORT

**Project:** FOG-ORCHESTRATOR 2.0 (SIH 2026-27 — SIH26007)  
**Vehicle Reference:** BEML BH100-class rigid rear dump truck  
**Validation Classification:** L6 (Calibrated Vehicle Dynamics / ISO 3450 Formulation)  
**Dataset Reference:** [`data/stopping_distance_matrix.csv`](file:///c:/Users/JAGADEESH%20M/OneDrive/Documents/SIH-2026-27/data/stopping_distance_matrix.csv) (150 configurations)  
**Figure:** [`figures/stopping_distance_vs_speed.png`](file:///c:/Users/JAGADEESH%20M/OneDrive/Documents/SIH-2026-27/figures/stopping_distance_vs_speed.png)  

---

## 1. Physical Governing Equations

Total stopping distance is calculated by summing reaction distance and braking deceleration distance:

$$S_{\text{stop}}(v) = d_{\text{react}} + d_{\text{brake}} = v \cdot \tau_{\text{local}} + \frac{v^2}{2 \cdot a_{\text{dec}}(v, \theta, \mu, m)}$$

Where:
- $v$: Initial vehicle velocity (m/s)
- $\tau_{\text{local}}$: Total local safety reaction latency (s)
- $a_{\text{dec}}$: Effective deceleration on grade $\theta$ with tire-ground friction coefficient $\mu$ and operating mass $m$:
  $$a_{\text{dec}} = g \cdot (\mu_{\text{effective}} \cos\theta - \sin\theta) + \frac{F_{\text{retard}}}{m}$$
  *(For -8% downhill civil grade, gravitational component opposes deceleration).*

---

## 2. Deceleration Capability Matrix ($a_{\text{dec}}$)

| Scenario Condition | Mass ($m$, kg) | Civil Grade | Friction ($\mu$) | Effective $a_{\text{dec}}$ ($\text{m/s}^2$) | Primary Braking Mechanism |
|:---|:---:|:---:|:---:|:---:|:---|
| **LADEN_DOWNHILL_WET** | 165,500 | -8.0% | 0.35 | **2.74** | Service Brakes + Retarder Blend |
| **EMPTY_DOWNHILL_WET** | 74,000 | -8.0% | 0.35 | **2.75** | Service Disc Brakes |
| **LADEN_FLAT_WET** | 165,500 | 0.0% | 0.35 | **3.43** | Service Disc Brakes |
| **EMPTY_FLAT_WET** | 74,000 | 0.0% | 0.35 | **3.43** | Service Disc Brakes |
| **LADEN_DOWNHILL_MUD** | 165,500 | -8.0% | 0.20 | **1.27** | Traction-Limited Deceleration |
| **EMPTY_DOWNHILL_MUD** | 74,000 | -8.0% | 0.20 | **1.27** | Traction-Limited Deceleration |

---

## 3. Stopping Distance Matrix Breakdown (Laden Downhill Wet: -8%, $\mu = 0.35$)

| Speed (km/h) | Speed (m/s) | Latency Tier ($\tau$, s) | $d_{\text{react}}$ (m) | $d_{\text{brake}}$ (m) | $S_{\text{stop}}$ (m) | Margin at 12 m Sight (m) | Collision Avoided? |
|:---:|:---:|:---|:---:|:---:|:---:|:---:|:---:|
| **20.0** | 5.56 | P50 (0.324 s) | 1.80 | 5.64 | **7.44** | +4.56 | YES |
| **20.0** | 5.56 | P95 (0.399 s) | 2.22 | 5.64 | **7.85** | +4.15 | YES |
| **20.0** | 5.56 | P99 (0.437 s) | 2.43 | 5.64 | **8.06** | +3.94 | YES |
| **20.0** | 5.56 | MAX (0.489 s) | 2.72 | 5.64 | **8.35** | +3.65 | YES |
| **20.0** | 5.56 | **HUMAN (1.20 s)** | **6.67** | 5.64 | **12.30** | **-0.30** | **NO (COLLISION)** |
| **15.0** | 4.17 | P50 (0.324 s) | 1.35 | 3.17 | **4.52** | +7.48 | YES |
| **15.0** | 4.17 | P99 (0.437 s) | 1.82 | 3.17 | **4.99** | +7.01 | YES |
| **15.0** | 4.17 | HUMAN (1.20 s) | 5.00 | 3.17 | **8.17** | +3.83 | YES |
| **10.0** | 2.78 | P50 (0.324 s) | 0.90 | 1.41 | **2.31** | +9.69 | YES |
| **10.0** | 2.78 | P99 (0.437 s) | 1.21 | 1.41 | **2.62** | +9.38 | YES |
| **5.0** | 1.39 | P50 (0.324 s) | 0.45 | 0.35 | **0.80** | +11.20 | YES |
| **3.6 (1 m/s)**| 1.00 | P50 (0.324 s) | 0.32 | 0.18 | **0.51** | +11.49 | YES |

---

## 4. Key Scientific Insights

1. **Human Perception Failure at 20 km/h:**  
   Under 12 m visibility on an 8% downhill ramp, a human operator reacting in 1.20 s travels **6.67 m** before the brakes are even applied. Adding 5.64 m braking distance results in **12.30 m total stopping distance**, causing an unavoidable impact with an obstacle at 12 m.

2. **Automated Governor Safety Margin:**  
   The autonomous local safety governor with $\tau_{\text{local}} = 0.437\text{ s}$ (P99) achieves a total stopping distance of **8.06 m**, providing a comfortable **+3.94 m safety margin** within the same 12 m sight envelope.
