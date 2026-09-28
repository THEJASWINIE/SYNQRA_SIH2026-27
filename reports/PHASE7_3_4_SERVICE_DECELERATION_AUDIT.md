# PHASE 7.3.4 — ATTACK #3: SERVICE DECELERATION AUDIT & PROVENANCE
**Module:** Routine Braking & Driver Comfort  
**Dataset:** `data/phase7_3_4_service_decel_sensitivity.csv`  
**Classification:** **ENGINEERING ASSUMPTION (YELLOW / NOT STATUTORY)**  

---

## 1. Provenance Investigation of 1.20 m/s²

The project uses $a_{\text{service}} = 1.2000\text{ m/s}^2$ to calculate routine, comfortable haulage speeds ($v_{\text{service}} = 3.6078\text{ m/s} = 12.99\text{ km/h}$ at $12\text{ m}$ visibility).  
The hostile audit examined the provenance of this value:
1. **Is it a BEML BH100 OEM specification?** **NO.** OEM datasheets specify gross retarder absorption power ($1,200\text{ kW}$) and engine power ($770\text{ kW}$), but do not prescribe a service deceleration rate.
2. **Is it an ISO 3450 statutory mandate?** **NO.** ISO 3450 specifies **minimum emergency braking capability** (stopping distance formulas equivalent to $\ge 2.5\text{--}3.0\text{ m/s}^2$ on level ground). It does NOT define a service deceleration comfort ceiling.
3. **Is it a DGMS regulation?** **NO.** DGMS Technical Circular 09/2008 sets haul road speed limits ($20\text{--}30\text{ km/h}$) and ramp gradient limits ($1:12.5 = 8\%$), but does not regulate operational service deceleration.
4. **Where does 1.2 m/s² originate?**  
   It is derived from **mining haulage literature and human factors engineering standards** (e.g., SME Mining Engineering Handbook and heavy commercial vehicle dynamic stability studies). In loaded rigid dumpers carrying blasted iron ore, sustained deceleration $> 1.5\text{ m/s}^2$ risks spilling boulder payload over the canopy or sides, shifting axle loads, and causing severe operator neck and torso fatigue.

**Formal Renaming:**  
$$a_{\text{service}} = \mathbf{ENGINEERING\;ASSUMPTION\;(DRIVER\;COMFORT\;LIMIT)}$$

---

## 2. Sensitivity of Safe Speed to Service Deceleration

To evaluate how strongly the operational safety envelope depends on this assumption, an independent sensitivity sweep was performed across $a_{\text{service}} \in [0.8, 2.0]\text{ m/s}^2$ at visibility levels from $5\text{ m}$ to $100\text{ m}$ ($\tau = 0.4371\text{ s}$, $S_{\text{base}} = 5.0\text{ m}$):

| Service Deceleration ($a_{\text{service}}$) | $v_{\text{safe}}$ @ 100m | $v_{\text{safe}}$ @ 50m | $v_{\text{safe}}$ @ 25m | $v_{\text{safe}}$ @ 12m | $v_{\text{safe}}$ @ 10m | $v_{\text{safe}}$ @ 8m | $v_{\text{safe}}$ @ 5m |
|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **0.80 m/s²** (Ultra-Gentle) | $5.56\text{ m/s}$ (20.0 km/h) | $5.56\text{ m/s}$ (20.0 km/h) | $5.32\text{ m/s}$ (19.1 km/h) | **3.01 m/s (10.8 km/h)** | $2.50\text{ m/s}$ (9.0 km/h) | $1.86\text{ m/s}$ (6.7 km/h) | **0.00 m/s** |
| **1.00 m/s²** (Conservative) | $5.56\text{ m/s}$ (20.0 km/h) | $5.56\text{ m/s}$ (20.0 km/h) | $5.56\text{ m/s}$ (20.0 km/h) | **3.33 m/s (12.0 km/h)** | $2.79\text{ m/s}$ (10.0 km/h) | $2.11\text{ m/s}$ (7.6 km/h) | **0.00 m/s** |
| **1.20 m/s²** (Baseline) | $5.56\text{ m/s}$ (20.0 km/h) | $5.56\text{ m/s}$ (20.0 km/h) | $5.56\text{ m/s}$ (20.0 km/h) | **3.61 m/s (13.0 km/h)** | $3.04\text{ m/s}$ (10.9 km/h) | $2.32\text{ m/s}$ (8.4 km/h) | **0.00 m/s** |
| **1.50 m/s²** (Firm Retarding) | $5.56\text{ m/s}$ (20.0 km/h) | $5.56\text{ m/s}$ (20.0 km/h) | $5.56\text{ m/s}$ (20.0 km/h) | **3.98 m/s (14.3 km/h)** | $3.36\text{ m/s}$ (12.1 km/h) | $2.59\text{ m/s}$ (9.3 km/h) | **0.00 m/s** |
| **2.00 m/s²** (Aggressive Brake) | $5.56\text{ m/s}$ (20.0 km/h) | $5.56\text{ m/s}$ (20.0 km/h) | $5.56\text{ m/s}$ (20.0 km/h) | **4.50 m/s (16.2 km/h)** | $3.83\text{ m/s}$ (13.8 km/h) | $2.97\text{ m/s}$ (10.7 km/h) | **0.00 m/s** |

---

## 3. Hostile Audit Insights

1. **High Impact in Low Visibility ($8\text{--}12\text{ m}$):**
   - At $12\text{ m}$ visibility, varying $a_{\text{service}}$ from $0.80\text{ m/s}^2$ to $1.50\text{ m/s}^2$ shifts safe speed from $10.8\text{ km/h}$ to $14.3\text{ km/h}$ ($\pm 16.5\%$).
   - The chosen value ($1.20\text{ m/s}^2 \implies 12.99\text{ km/h}$) sits centrally within the viable haulage envelope.
2. **Invariance in Moderate Fog ($\ge 25\text{ m}$):**
   - Above $25\text{ m}$ visibility, the regulatory mine speed cap ($20.0\text{ km/h} = 5.5556\text{ m/s}$) dominates across all service decelerations.
3. **Invariance in Dense Fog ($\le 5\text{ m}$):**
   - At $\le 5.0\text{ m}$, $v_{\text{safe}} = 0.0000\text{ m/s}$ regardless of service deceleration, because available stopping range is $0\text{ m}$.
4. **Audit Conclusion:**
   - The assumption $a_{\text{service}} = 1.20\text{ m/s}^2$ is defensible as an engineering comfort threshold, but must **NEVER** be cited as statutory or certified.
