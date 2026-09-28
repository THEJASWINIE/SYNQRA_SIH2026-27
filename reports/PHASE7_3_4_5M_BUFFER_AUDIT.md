# PHASE 7.3.4 — ATTACK #4: 5-METRE SAFETY BUFFER PROVENANCE & SENSITIVITY
**Module:** Spatial Separation & Blindout Threshold  
**Dataset:** `data/phase7_3_4_safety_buffer_sensitivity.csv`  
**Classification:** **ENGINEERING SAFETY MARGIN (YELLOW / NOT STATUTORY)**  

---

## 1. Provenance Investigation of the 5.0-Metre Buffer

The project defines $S_{\text{base}} = 5.0000\text{ m}$ as the minimum standstill separation distance between vehicles or between a vehicle and a detected obstacle.  
The hostile audit investigated whether $5.0\text{ m}$ is statutory:
1. **DGMS Technical Circular 09/2008 & Coal Mines Regulations 2017:**
   - DGMS guidelines mandate that vehicles must maintain "sufficient clear distance" and recommend that moving dumpers maintain at least $30\text{ m}$ following distance during haulage.
   - For stationary staging in loading/dumping areas, DGMS recommends maintaining at least one vehicle width or a clear visible zone to prevent blind-spot collisions.
   - **DOES NOT CONTAIN:** An explicit statutory clause mandating exactly $5.0000\text{ metres}$.
2. **Physical Engineering Origin:**
   - $5.0\text{ m}$ was chosen as an **ENGINEERING DESIGN MARGIN** based on:
     - Half the vehicle body length of a BEML BH100 ($10.52\text{ m} / 2 \approx 5.26\text{ m}$).
     - The physical ground blind spot directly in front of the elevated BH100 cab bumper ($3.5\text{--}4.5\text{ m}$).
     - A spatial buffer absorbing GPS/V2V localization error ($\pm 0.5\text{--}1.0\text{ m}$) and pneumatic brake pressure variation.

**Formal Renaming:**  
$$S_{\text{base}} = \mathbf{5.0\;m\;ENGINEERING\;SAFETY\;BUFFER\;(NOT\;STATUTORY)}$$
It must never be claimed as a "statutory DGMS regulation."

---

## 2. Sensitivity of Safe Speed to Buffer Size ($S_{\text{base}}$)

The audit evaluated the impact of varying $S_{\text{base}}$ from $2.0\text{ m}$ to $10.0\text{ m}$ across visibility levels ($a = 2.7466\text{ m/s}^2$, $\tau = 0.4371\text{ s}$):

| Buffer Size ($S_{\text{base}}$) | $v_{\text{safe}}$ @ 100m | $v_{\text{safe}}$ @ 50m | $v_{\text{safe}}$ @ 25m | $v_{\text{safe}}$ @ 12m | $v_{\text{safe}}$ @ 10m | $v_{\text{safe}}$ @ 8m | $v_{\text{safe}}$ @ 5m | $v_{\text{safe}}$ @ 3m |
|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **2.0 m** | $5.56\text{ m/s}$ (20.0 km/h) | $5.56\text{ m/s}$ (20.0 km/h) | $5.56\text{ m/s}$ (20.0 km/h) | **6.26 m/s (22.5 km/h)** | **5.52 m/s (19.9 km/h)** | **4.68 m/s (16.8 km/h)** | **3.57 m/s (12.9 km/h)** | **1.77 m/s (6.4 km/h)** |
| **3.0 m** | $5.56\text{ m/s}$ (20.0 km/h) | $5.56\text{ m/s}$ (20.0 km/h) | $5.56\text{ m/s}$ (20.0 km/h) | **5.90 m/s (21.2 km/h)** | **5.12 m/s (18.4 km/h)** | **4.21 m/s (15.2 km/h)** | **2.88 m/s (10.4 km/h)** | **0.00 m/s** |
| **4.0 m** | $5.56\text{ m/s}$ (20.0 km/h) | $5.56\text{ m/s}$ (20.0 km/h) | $5.56\text{ m/s}$ (20.0 km/h) | **5.52 m/s (19.9 km/h)** | **4.68 m/s (16.8 km/h)** | **3.67 m/s (13.2 km/h)** | **1.96 m/s (7.1 km/h)** | **0.00 m/s** |
| **5.0 m** (Baseline) | $5.56\text{ m/s}$ (20.0 km/h) | $5.56\text{ m/s}$ (20.0 km/h) | $5.56\text{ m/s}$ (20.0 km/h) | **5.12 m/s (18.4 km/h)** | **4.21 m/s (15.2 km/h)** | **3.04 m/s (10.9 km/h)** | **0.00 m/s** | **0.00 m/s** |
| **6.0 m** | $5.56\text{ m/s}$ (20.0 km/h) | $5.56\text{ m/s}$ (20.0 km/h) | $5.56\text{ m/s}$ (20.0 km/h) | **4.68 m/s (16.8 km/h)** | **3.67 m/s (13.2 km/h)** | **2.24 m/s (8.1 km/h)** | **0.00 m/s** | **0.00 m/s** |
| **8.0 m** | $5.56\text{ m/s}$ (20.0 km/h) | $5.56\text{ m/s}$ (20.0 km/h) | $5.56\text{ m/s}$ (20.0 km/h) | **3.67 m/s (13.2 km/h)** | **2.24 m/s (8.1 km/h)** | **0.00 m/s** | **0.00 m/s** | **0.00 m/s** |
| **10.0 m** | $5.56\text{ m/s}$ (20.0 km/h) | $5.56\text{ m/s}$ (20.0 km/h) | $5.56\text{ m/s}$ (20.0 km/h) | **2.24 m/s (8.1 km/h)** | **0.00 m/s** | **0.00 m/s** | **0.00 m/s** | **0.00 m/s** |

---

## 3. Hostile Technical Assessment

1. **Shift of the Controlled Staging Boundary:**
   - If $S_{\text{base}}$ is reduced to $3.0\text{ m}$, the vehicle could legally move at $10.4\text{ km/h}$ in $5\text{ m}$ fog, but halting within $3.0\text{ m}$ of a detected obstacle leaves dangerously little room for localized wheel slip or bumper overhang.
   - If $S_{\text{base}}$ is expanded to $8.0\text{ m}$, controlled staging is triggered earlier (at $8.0\text{ m}$ visibility), shutting down haulage prematurely.
2. **Robustness of the 5.0m Selection:**
   - $5.0\text{ m}$ aligns with the real-world operational requirement in the problem statement: in $3\text{--}5\text{ m}$ monsoon fog, vehicles must halt ($v=0$). Setting $S_{\text{base}} = 5.0\text{ m}$ naturally enforces $v_{\text{safe}} = 0$ for all $V_{\text{fog}} \le 5.0\text{ m}$.
3. **Core Conclusion:**
   - The main conclusions remain valid across $S_{\text{base}} \in [4.0, 6.0]\text{ m}$.
   - The buffer is defensible, provided it is truthfully documented as an **ENGINEERING SAFETY MARGIN**, not an unverified statutory law.
