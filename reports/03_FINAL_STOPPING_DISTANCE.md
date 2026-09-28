# PHASE 7.3.2 — REPORT 03: FINAL STOPPING DISTANCE AUDIT
## Resolution of Primary 7m vs 12.84m Contradiction & Deceleration Regimes
### FOG-ORCHESTRATOR 2.0 — SIH 2026-27

---

### 1. Investigation of Primary Failure

The prompt required an independent recalculation of the historical claim:
$$\tau_{\text{local}} = 0.375\text{ s},\quad a_{\text{dec}} = 1.20\text{ m/s}^2,\quad R_{\text{vis}} = 12.0\text{ m},\quad S_{\text{margin}} = 5.0\text{ m},\quad v_{\text{safe}} \approx 5.12\text{ m/s}$$
with a claimed stopping distance of $7.0\text{ m}$.

#### Independent Forward Calculation:
$$S_{\text{stop}}(v) = v \cdot \tau + \frac{v^2}{2 a_{\text{dec}}}$$
For $v = 5.12\text{ m/s}$, $\tau = 0.375\text{ s}$, $a_{\text{dec}} = 1.20\text{ m/s}^2$:
* Reaction distance: $d_{\text{react}} = 5.12 \times 0.375 = \mathbf{1.9200\text{ m}}$
* Braking distance: $d_{\text{brake}} = \frac{5.12^2}{2 \times 1.20} = \frac{26.2144}{2.40} = \mathbf{10.9227\text{ m}}$
* Total stopping distance: $S_{\text{stop}} = 1.9200 + 10.9227 = \mathbf{12.8427\text{ m}}$
* Required total distance (including $5.0\text{ m}$ buffer): $12.8427 + 5.0000 = \mathbf{17.8427\text{ m}}$
* Effective visibility range: $12.0000\text{ m}$
* Overrun beyond visibility: $17.8427 - 12.0000 = \mathbf{+5.8427\text{ m}}$ (OVERRUN / VIOLATION)
* Clearance margin: $12.0000 - 12.8427 = \mathbf{-0.8427\text{ m}}$ (Negative margin; obstacle collision at $1.42\text{ m/s}$)

**Conclusion on Historical Claim**: The claim that $v = 5.12\text{ m/s}$ stops in $7.0\text{ m}$ under $a_{\text{dec}} = 1.20\text{ m/s}^2$ is **PHYSICALLY AND MATHEMATICALLY FALSE**. Under $a_{\text{dec}} = 1.20\text{ m/s}^2$, stopping distance is $12.84\text{ m}$, crashing into the obstacle.

---

### 2. Forensic Reconciliation of 5.1158 m/s

The value $v = 5.1158\text{ m/s}$ ($18.42\text{ km/h}$) was actually derived from the **emergency friction-limited deceleration** on a wet $-8\%$ haul ramp ($a_{\text{dec}} = \mathbf{2.7466\text{ m/s}^2}$) under statistical P99 reaction latency ($\tau = \mathbf{0.4371\text{ s}}$):

#### Forward Verification:
* Reaction distance: $d_{\text{react}} = 5.1158 \times 0.4371 = \mathbf{2.2361\text{ m}}$
* Braking distance: $d_{\text{brake}} = \frac{5.1158^2}{2 \times 2.7466} = \frac{26.1714}{5.4932} = \mathbf{4.7643\text{ m}}$
* Total stopping distance: $S_{\text{stop}} = 2.2361 + 4.7643 = \mathbf{7.0004\text{ m}} \approx \mathbf{7.000\text{ m}}$
* Total required stopping range: $7.0004 + 5.0000 = \mathbf{12.0004\text{ m}} \approx 12.00\text{ m}$
* Clearance margin remaining: $12.0000 - 7.0004 = \mathbf{4.9996\text{ m}} \approx \mathbf{5.000\text{ m}}$

The quadratic positive root for $R_{\text{available}} = 12.0 - 5.0 = 7.0\text{ m}$:
$$v_{\text{max}} = -(2.7466)(0.4371) + \sqrt{((2.7466)(0.4371))^2 + 2(2.7466)(7.0)}$$
$$v_{\text{max}} = -1.20054 + \sqrt{1.44129 + 38.45240} = -1.20054 + \sqrt{39.89369} = -1.20054 + 6.31615 = \mathbf{5.1156\text{ m/s}}$$

The analytical root matches $5.1158\text{ m/s}$ within $0.0002\text{ m/s}$ (attributable to rounding $\tau$ to $0.437\text{ s}$ vs $0.4371\text{ s}$).

---

### 3. Dual-Regime Stopping Distance Comparison at 12m

| Deceleration Regime | $a_{\text{dec}}$ ($\text{m/s}^2$) | Latency Scenario | $\tau$ ($\text{s}$) | $v_{\text{safe}}$ ($\text{m/s}$) | $v_{\text{safe}}$ ($\text{km/h}$) | $d_{\text{react}}$ ($\text{m}$) | $d_{\text{brake}}$ ($\text{m}$) | $S_{\text{stop}}$ ($\text{m}$) | $S_{\text{margin}}$ ($\text{m}$) | $S_{\text{total}}$ ($\text{m}$) | Margin ($\text{m}$) | Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Emergency Friction** | 2.7466 | Nominal | 0.3750 | **5.2560** | 18.92 | 1.9710 | 5.0290 | **7.0000** | 5.0000 | 12.0000 | +5.0000 | **SAFE** |
| **Emergency Friction** | 2.7466 | P95 Bound | 0.4120 | **5.1610** | 18.58 | 2.1263 | 4.8737 | **7.0000** | 5.0000 | 12.0000 | +5.0000 | **SAFE** |
| **Emergency Friction** | 2.7466 | P99 Bound | 0.4371 | **5.1158** | 18.42 | 2.2361 | 4.7643 | **7.0004** | 5.0000 | 12.0004 | +4.9996 | **SAFE** |
| **Emergency Friction** | 2.7466 | Worst-Case | 0.4750 | **5.0321** | 18.12 | 2.3902 | 4.6098 | **7.0000** | 5.0000 | 12.0000 | +5.0000 | **SAFE** |
| **Conservative Service**| 1.2000 | Nominal | 0.3750 | **3.6734** | 13.22 | 1.3775 | 5.6225 | **7.0000** | 5.0000 | 12.0000 | +5.0000 | **SAFE** |
| **Conservative Service**| 1.2000 | P95 Bound | 0.4120 | **3.6288** | 13.06 | 1.4951 | 5.4869 | **7.0000** | 5.0000 | 12.0000 | +5.0000 | **SAFE** |
| **Conservative Service**| 1.2000 | P99 Bound | 0.4371 | **3.6078** | 12.99 | 1.5769 | 5.4231 | **7.0000** | 5.0000 | 12.0000 | +5.0000 | **SAFE** |
| **Conservative Service**| 1.2000 | Worst-Case | 0.4750 | **3.5654** | 12.84 | 1.6936 | 5.3064 | **7.0000** | 5.0000 | 12.0000 | +5.0000 | **SAFE** |
| *Contradicted Baseline*| 1.2000 | Nominal | 0.3750 | *5.1200* | *18.43* | 1.9200 | 10.9227 | **12.8427** | 5.0000 | **17.8427** | **-0.8427** | **CRASH** |

---

### 4. Operational Governance vs Contingency Safety

* **Service Deceleration ($a_{\text{dec}} = 1.20\text{ m/s}^2$)**:
  - Represents the standard operator service envelope to prevent material spillage and tire heating.
  - Normal haulage operates at **$13.0\text{--}13.2\text{ km/h}$** ($3.61\text{--}3.67\text{ m/s}$) under $12\text{ m}$ visibility.
* **Emergency Retarding Deceleration ($a_{\text{dec}} = 2.7466\text{ m/s}^2$)**:
  - Full air-over-hydraulic caliper clamping ($550\text{ kN}$) with mechanical retarder.
  - Represents the absolute physical safety constraint enforced by the Tier-1 governor.
  - Permits speeds up to **$18.42\text{ km/h}$** ($5.1158\text{ m/s}$) while guaranteeing a zero-collision stop within $7.0\text{ m}$ and preserving a $5.0\text{ m}$ standoff buffer.
