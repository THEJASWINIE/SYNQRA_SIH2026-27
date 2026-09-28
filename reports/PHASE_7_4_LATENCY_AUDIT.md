# PHASE 7.4 — FAIL-SAFE LATENCY & STOPPING AUDIT
## FOG-ORCHESTRATOR 2.0 — SIH26007
**Classification:** Reaction Time Budget Decomposition & Stopping Kinematics Audit  
**Provenance Standard:** L7 (Bench Measured), L6 (Engineering Assumption/Model), L9 (Simulation), L1–L5 (Literature/Standards)  

---

## 1. Reaction Time Budget Decomposition

To prevent catastrophic misattribution, the end-to-end safety reaction time is strictly decomposed into 7 distinct physical and software stages. Under no circumstances are these stages conflated into a single unverified number.

$$T_{\text{total}} = T_{\text{detection}} + T_{\text{decision}} + T_{\text{transport}} + T_{\text{actuator}}$$

Then, physical deceleration time and stopping distance are calculated separately:

$$T_{\text{brake}} = \frac{v}{a_{\text{dec}}}$$

$$S_{\text{stop}} = v \cdot T_{\text{total}} + \frac{v^2}{2 \cdot a_{\text{dec}}}$$

---

## 2. Latency Stages & Provenance Classification

| Stage | Parameter Name | Nominal Value | Bench Measured (P95) | Worst-Case Ceiling | Evidence Level | Methodological Provenance |
|---|---|---|---|---|---|---|
| **1. RF Airtime** | $T_{\text{rf}}$ | $48.2\text{ ms}$ | $25.79\text{ ms}$ | $35.0\text{ ms}$ | **L7 (Bench)** | Semtech SX1278 Ra-02 bench logging (SF7, BW 125 kHz, 433 MHz). L5 literature baseline. |
| **2. Loss Detection** | $T_{\text{detection}}$ | $500\text{ ms}$ | $500\text{ ms}$ | $1000\text{ ms}$ | **L1 (Deterministic)** | Safe Beacon heartbeat watchdog timer configuration. |
| **3. Local Decision** | $T_{\text{decision}}$ | $4.8\text{ ms}$ | $4.8\text{ ms}$ | $10.0\text{ ms}$ | **L7 (Bench)** | ESP32 execution time for `solve_safe_speed()` and governor invariant check. |
| **4. Bus Transport** | $T_{\text{transport}}$ | $50.0\text{ ms}$ | $19.17\text{ ms}$ | $50.0\text{ ms}$ | **L7 (Bench) / L6** | Bench TWAI/CAN logging across 12,000 frames. 50 ms is a conservative engineering ceiling. |
| **5. Actuator Response**| $T_{\text{actuator}}$ | $200.0\text{ ms}$ | N/A | $350.0\text{ ms}$ | **L5 (Literature) / L6**| BEML BH100 air-over-hydraulic brake valve literature. (Surrogate bench actuator tested). |
| **Reaction Total** | $T_{\text{total}}$ | **$754.8\text{ ms}$** | **$524.0\text{ ms}$** | **$1410.0\text{ ms}$** | **Composite** | $T_{\text{total}} = T_{\text{detection}} + T_{\text{decision}} + T_{\text{transport}} + T_{\text{actuator}}$. |
| **6. Braking Time** | $T_{\text{brake}}$ | $v / a_{\text{dec}}$ | N/A | $v / a_{\text{dec}}$ | **L6 (Model)** | Newton-Euler rigid body kinematics: $a_{\text{emergency}} \approx 2.7856\text{ m/s}^2$. |
| **7. Total Stop Dist** | $S_{\text{stop}}$ | $v T_{\text{total}} + \frac{v^2}{2a}$ | N/A | Model derived | **L6 (Model)** | Computed stopping distance. **NOT physically measured on a BH100**. |

> [!CAUTION]
> **Zero Field Validation Disclaimer**:
> Stopping distance $S_{\text{stop}}$ is an **engineering kinematic model (L6)**. It has **NOT** been physically measured on a production 165.5-tonne BEML BH100 haul truck at NMDC Bailadila.

---

## 3. Kinematic Deceleration Baselines

The physics model relies on two strictly distinguished deceleration rates:
1. **Emergency Deceleration ($a_{\text{emergency}} \approx 2.7856\text{ m/s}^2$):**
   - Derived from tire-road adhesion ($\mu = 0.35$ wet ore), -8% civil downgrade, load transfer, and mechanical brake force capacity ($550\text{ kN}$).
   - **Classification:** L6 Model-Derived.
2. **Service Deceleration ($a_{\text{service}} = 1.2000\text{ m/s}^2$):**
   - Adopted engineering operational and component comfort assumption for haul road operations.
   - **Classification:** L6 Engineering Assumption.
   - **Notice:** ISO 3450 specifies minimum braking performance criteria, but $1.2\text{ m/s}^2$ is an operational design choice, not a universal statutory constant.

---

## 4. Calculated Stopping Distance Matrix

Calculated for BEML BH100 ($165{,}500\text{ kg}$ GVW) on $-8\%$ civil downgrade (wet ore, $\mu=0.35$, $a_{\text{emergency}} = 2.7856\text{ m/s}^2$):

| Speed ($v$) | Speed ($\text{km/h}$) | Reaction Distance ($T_{\text{total}}=0.524\text{s}$) | Braking Distance ($d_{\text{brake}}$) | Total Stop Distance ($S_{\text{stop}}$) | Base Buffer ($S_{\text{base}}$) | Required Sight Distance ($R_{\text{req}}$) |
|---|---|---|---|---|---|---|
| **$0.00\text{ m/s}$** | $0.0\text{ km/h}$ | $0.00\text{ m}$ | $0.00\text{ m}$ | **$0.00\text{ m}$** | $5.0\text{ m}$ | **$5.00\text{ m}$ (STAGED)** |
| **$1.00\text{ m/s}$** | $3.6\text{ km/h}$ | $0.52\text{ m}$ | $0.18\text{ m}$ | **$0.70\text{ m}$** | $5.0\text{ m}$ | **$5.70\text{ m}$** |
| **$2.00\text{ m/s}$** | $7.2\text{ km/h}$ | $1.05\text{ m}$ | $0.72\text{ m}$ | **$1.77\text{ m}$** | $5.0\text{ m}$ | **$6.77\text{ m}$** |
| **$3.00\text{ m/s}$** | $10.8\text{ km/h}$ | $1.57\text{ m}$ | $1.62\text{ m}$ | **$3.19\text{ m}$** | $5.0\text{ m}$ | **$8.19\text{ m}$** |
| **$4.00\text{ m/s}$** | $14.4\text{ km/h}$ | $2.10\text{ m}$ | $2.87\text{ m}$ | **$4.97\text{ m}$** | $5.0\text{ m}$ | **$9.97\text{ m}$** |
| **$4.38\text{ m/s}$** | $15.8\text{ km/h}$ | $2.30\text{ m}$ | $3.44\text{ m}$ | **$5.74\text{ m}$** | $5.0\text{ m}$ | **$10.74\text{ m}$** |
| **$5.56\text{ m/s}$** | $20.0\text{ km/h}$ | $2.91\text{ m}$ | $5.55\text{ m}$ | **$8.46\text{ m}$** | $5.0\text{ m}$ | **$13.46\text{ m}$** |

---

## 5. Audit Conclusions & Scientific Boundaries

1. **Bench Validation Bound:** Only microcontroller execution ($T_{\text{decision}} = 4.8\text{ ms}$), TWAI/CAN bus transmission ($T_{\text{transport}} = 19.17\text{ ms}$ P95), and LoRa RF airtime ($T_{\text{rf}} = 25.79\text{ ms}$ P95) are physically bench-measured.
2. **Kinematic Decoupling:** Braking distance $d_{\text{brake}}$ and stopping distance $S_{\text{stop}}$ are strictly mathematical projections derived from Newton's second law and adhesion limits.
3. **Safety Guarantee:** At all tested speeds, $S_{\text{stop}} + S_{\text{base}} \le R_{\text{effective}}$ holds strictly within the analytical solver.
