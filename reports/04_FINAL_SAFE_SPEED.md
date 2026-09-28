# PHASE 7.3.2 — REPORT 04: FINAL SAFE SPEED AUDIT
## Canonical Safe Speed Calibration Across Perception Horizons (100m to 3m)
### FOG-ORCHESTRATOR 2.0 — SIH 2026-27

---

### 1. Definition of Effective Perception Range $R_{\text{effective}}$

The system strictly distinguishes:
* $V_{\text{fog}}$: Meteorological optical visibility distance measured by forward scatter transmissometers.
* $R_{\text{sensor}}$: Reliable detection range of onboard active sensors (radar/lidar surrogate models).
* $R_{\text{sight}}$: Human operator clear sight line distance.
* $S_{\text{margin}}$: Mandatory standoff safety buffer ($S_{\text{base}} = 5.0\text{ m}$).
* $R_{\text{available}}$: Usable stopping sight distance:
  $$R_{\text{available}} = \max(0.0, R_{\text{effective}} - S_{\text{margin}})$$

where:
$$R_{\text{effective}} = \min(V_{\text{fog}}, R_{\text{sensor}}, R_{\text{sight}})$$

---

### 2. Analytical Formulation

Safe speed is derived from the positive root of the kinematic boundary:
$$v_{\text{stop}} = -a_{\text{dec}} \tau + \sqrt{(a_{\text{dec}} \tau)^2 + 2 a_{\text{dec}} R_{\text{available}}}$$
$$v_{\text{safe}} = \min(v_{\text{stop}}, v_{\text{mine\_cap}})$$
where $v_{\text{mine\_cap}} = 20.0\text{ km/h} = 5.5556\text{ m/s}$ (DGMS open-cast mine speed limit).

---

### 3. Master Canonical Safe Speed Table

Evaluated under statistical P99 latency ($\tau = 0.4371\text{ s}$):

#### A. Emergency Deceleration Regime ($a_{\text{dec}} = 2.7466\text{ m/s}^2$)

| Visibility $R_{\text{eff}}$ ($\text{m}$) | $R_{\text{available}}$ ($\text{m}$) | $v_{\text{stop}}$ ($\text{m/s}$) | $v_{\text{stop}}$ ($\text{km/h}$) | $v_{\text{safe}}$ ($\text{m/s}$) | $v_{\text{safe}}$ ($\text{km/h}$) | $d_{\text{react}}$ ($\text{m}$) | $d_{\text{brake}}$ ($\text{m}$) | $S_{\text{stop}}$ ($\text{m}$) | Total Distance ($\text{m}$) | Primary Constraint | Modeled Production |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :--- | :--- |
| **100.0** | 95.0 | 21.6754 | 78.03 | **5.5556** | **20.00** | 2.4284 | 5.6191 | 8.0475 | 13.0475 | MINE_SPEED_LIMIT | NORMAL |
| **50.0** | 45.0 | 14.5679 | 52.44 | **5.5556** | **20.00** | 2.4284 | 5.6191 | 8.0475 | 13.0475 | MINE_SPEED_LIMIT | NORMAL |
| **25.0** | 20.0 | 9.3498 | 33.66 | **5.5556** | **20.00** | 2.4284 | 5.6191 | 8.0475 | 13.0475 | MINE_SPEED_LIMIT | NORMAL |
| **15.0** | 10.0 | 6.3268 | 22.78 | **5.5556** | **20.00** | 2.4284 | 5.6191 | 8.0475 | 13.0475 | MINE_SPEED_LIMIT | NORMAL |
| **12.0** | 7.0 | 5.1158 | 18.42 | **5.1158** | **18.42** | 2.2361 | 4.7643 | 7.0004 | 12.0004 | STOPPING_SIGHT_DIST | NORMAL |
| **10.0** | 5.0 | 4.1610 | 14.98 | **4.1610** | **14.98** | 1.8188 | 3.1519 | 4.9707 | 9.9707 | STOPPING_SIGHT_DIST | NORMAL |
| **8.0** | 3.0 | 3.0234 | 10.88 | **3.0234** | **10.88** | 1.3215 | 1.6641 | 2.9856 | 7.9856 | STOPPING_SIGHT_DIST | NORMAL |
| **5.0** | 0.0 | 0.0000 | 0.00 | **0.0000** | **0.00** | 0.0000 | 0.0000 | 0.0000 | 0.0000 | CONTROLLED_STAGING | **ZERO_TPH_STAGED** |
| **4.0** | 0.0 | 0.0000 | 0.00 | **0.0000** | **0.00** | 0.0000 | 0.0000 | 0.0000 | 0.0000 | CONTROLLED_STAGING | **ZERO_TPH_STAGED** |
| **3.0** | 0.0 | 0.0000 | 0.00 | **0.0000** | **0.00** | 0.0000 | 0.0000 | 0.0000 | 0.0000 | CONTROLLED_STAGING | **ZERO_TPH_STAGED** |

#### B. Conservative Service Deceleration Regime ($a_{\text{dec}} = 1.2000\text{ m/s}^2$)

| Visibility $R_{\text{eff}}$ ($\text{m}$) | $R_{\text{available}}$ ($\text{m}$) | $v_{\text{stop}}$ ($\text{m/s}$) | $v_{\text{stop}}$ ($\text{km/h}$) | $v_{\text{safe}}$ ($\text{m/s}$) | $v_{\text{safe}}$ ($\text{km/h}$) | $d_{\text{react}}$ ($\text{m}$) | $d_{\text{brake}}$ ($\text{m}$) | $S_{\text{stop}}$ ($\text{m}$) | Total Distance ($\text{m}$) | Primary Constraint | Modeled Production |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :--- | :--- |
| **100.0** | 95.0 | 14.5956 | 52.54 | **5.5556** | **20.00** | 2.4284 | 12.8604 | 15.2888 | 20.2888 | MINE_SPEED_LIMIT | NORMAL |
| **50.0** | 45.0 | 9.8872 | 35.59 | **5.5556** | **20.00** | 2.4284 | 12.8604 | 15.2888 | 20.2888 | MINE_SPEED_LIMIT | NORMAL |
| **25.0** | 20.0 | 6.4328 | 23.16 | **5.5556** | **20.00** | 2.4284 | 12.8604 | 15.2888 | 20.2888 | MINE_SPEED_LIMIT | NORMAL |
| **15.0** | 10.0 | 4.4079 | 15.87 | **4.4079** | **15.87** | 1.9267 | 8.0956 | 10.0223 | 15.0223 | STOPPING_SIGHT_DIST | NORMAL |
| **12.0** | 7.0 | 3.6078 | 12.99 | **3.6078** | **12.99** | 1.5769 | 5.4231 | 7.0000 | 12.0000 | STOPPING_SIGHT_DIST | NORMAL |
| **10.0** | 5.0 | 2.9818 | 10.73 | **2.9818** | **10.73** | 1.3033 | 3.7046 | 5.0079 | 10.0079 | STOPPING_SIGHT_DIST | NORMAL |
| **8.0** | 3.0 | 2.2132 | 7.97 | **2.2132** | **7.97** | 0.9674 | 2.0410 | 3.0084 | 8.0084 | STOPPING_SIGHT_DIST | NORMAL |
| **5.0** | 0.0 | 0.0000 | 0.00 | **0.0000** | **0.00** | 0.0000 | 0.0000 | 0.0000 | 0.0000 | CONTROLLED_STAGING | **ZERO_TPH_STAGED** |
| **4.0** | 0.0 | 0.0000 | 0.00 | **0.0000** | **0.00** | 0.0000 | 0.0000 | 0.0000 | 0.0000 | CONTROLLED_STAGING | **ZERO_TPH_STAGED** |
| **3.0** | 0.0 | 0.0000 | 0.00 | **0.0000** | **0.00** | 0.0000 | 0.0000 | 0.0000 | 0.0000 | CONTROLLED_STAGING | **ZERO_TPH_STAGED** |

---

### 4. Dense Fog Blindout Mandate (3m – 5m)

* **Physical Impossibility of Motion**: Because the mandatory standstill buffer is $S_{\text{base}} = 5.0\text{ m}$, any visibility $\le 5.0\text{ m}$ leaves zero available stopping distance ($R_{\text{available}} \le 0$).
* **Fail-Safe Response**: The vehicle enters **CONTROLLED STAGING / HOLD**.
* **Zero Production Integrity**: The model strictly reports **0.0 TPH** haulage production during blindout. No artificial crawl speed ($0.5\text{ m/s}$ or $1.0\text{ m/s}$) is fabricated to show partial throughput.
