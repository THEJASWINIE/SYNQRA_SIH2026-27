# FINAL CANONICAL PHYSICS & PARAMETER MODEL DOCUMENTATION
## FOG-ORCHESTRATOR 2.0 — SIH 2026-27 (Problem Statement SIH26007)
### Authoritative Single Source of Truth for Mine Vehicle Dynamics, Braking & Operating Envelopes

---

## 1. Executive Context & Scope Lock

This document serves as the immutable canonical definition of all physical equations, coordinate sign conventions, vehicle parameters, and kinematic operating envelopes for **FOG-ORCHESTRATOR 2.0**.

- **Reference Heavy Earth Moving Machinery (HEMM):** BEML BH100 Rigid Mining Haul Dumper (100-tonne payload rating).
- **Reference Geological Context:** NMDC Bailadila Iron Ore Complex (Deposit-5 Main Haul Ramp, -8% Grade).
- **Embedded Architecture:** ESP32-WROOM-32D Microcontroller, FreeRTOS dual-core deterministic control loop, CAN 2.0B / TWAI 250 kbps chassis bus.

---

## 2. Master Longitudinal Equation of Motion

The dynamic longitudinal motion of the haul dumper along the ramp gradient is governed by:

$$m \frac{dv}{dt} = F_{\text{drive}} + m g \sin(\theta) - F_{\text{roll}} - F_{\text{aero}} - F_{\text{retarder}} - F_{\text{brake}}$$

### Force Component Definitions:

1. **Gravity Component ($m g \sin\theta$):**
   - Grade convention: $\theta$ is negative for downhill ramps ($\theta < 0$), positive for uphill hauls ($\theta > 0$).
   - For an 8% downhill ramp: $\theta = \arctan(-0.08) \approx -0.07983\text{ rad}$ ($-4.574^\circ$).
   - Downhill component adds forward propelling force: $m g \sin(\theta) = 165,500 \times 9.80665 \times \sin(-0.07983) \approx -129,510\text{ N}$ (acting in direction of motion).

2. **Rolling Resistance ($F_{\text{roll}}$):**
   $$F_{\text{roll}} = C_{\text{rr}} \cdot m \cdot g \cdot \cos(\theta)$$
   - Canonical $C_{\text{rr}} = 0.025$ (compacted hematite gravel/crushed rock surface).
   - $F_{\text{roll}} = 0.025 \times 165,500 \times 9.80665 \times \cos(-0.07983) \approx 40,404\text{ N}$.

3. **Aerodynamic Drag ($F_{\text{aero}}$):**
   $$F_{\text{aero}} = \frac{1}{2} \rho C_d A v^2$$
   - $\rho = 1.225\text{ kg/m}^3$, $C_d = 0.90$, $A = 18.5\text{ m}^2$.
   - At dense fog speeds ($v \approx 5.12\text{ m/s}$), $F_{\text{aero}} \approx 267\text{ N}$ (negligible relative to tyre forces, but retained for physical fidelity).

4. **Tire-Road Adhesion Limit ($F_{\mu}$):**
   $$F_{\mu} = \mu \cdot m \cdot g \cdot \cos(\theta)$$
   - Nominal friction ($\mu = 0.35$, conservative low-friction engineering assumption): $F_{\mu} \approx 565,650\text{ N}$.
   - Wet clay slurry ($\mu = 0.30$): $F_{\mu} \approx 484,840\text{ N}$.
   - Saturated monsoon mud ($\mu = 0.25$): $F_{\mu} \approx 404,040\text{ N}$.

---

## 3. Braking Regimes & Reconciled Deceleration Values

A major source of historical confusion was the coexistence of $2.7466\text{ m/s}^2$, $2.7856\text{ m/s}^2$, and $1.20\text{ m/s}^2$. We explicitly audit and reconcile these values:

| Deceleration Parameter | Value | Classification | Physical Provenance | Status in System |
|---|---|---|---|---|
| **$a_{\text{emergency\_canonical}}$** | **$2.7856\text{ m/s}^2$** | `L6_DERIVATION` | Net deceleration on $-8\%$ ramp: $m=165.5\text{ t}$, $C_{\text{rr}}=0.025$, $g=9.80665$, $F_{\text{brake}}=550\text{ kN}$. | **CURRENT CANONICAL** |
| **$a_{\text{emergency\_legacy}}$** | **$2.7466\text{ m/s}^2$** | `L6_DERIVATION` | Legacy balance: $m=165.0\text{ t}$, $C_{\text{rr}}=0.020$, $g=9.81$, $F_{\text{brake}}=550\text{ kN}$. | **RETAINED IN BASELINE TESTS** |
| **$a_{\text{service}}$** | **$1.2000\text{ m/s}^2$** | `L6_ASSUMPTION` | Heavy mining vehicle comfortable service deceleration to prevent ore spillage and tyre wear. | **SERVICE CEILING** |

### Exact Derivation of Canonical Emergency Deceleration ($2.7856\text{ m/s}^2$):
Under maximum dry mechanical braking ($F_{\text{brake}} = 550,000\text{ N}$), rolling resistance opposing motion, and downhill gravity propelling the truck:

$$F_{\text{net\_retarding}} = F_{\text{brake}} + F_{\text{roll}} - m g |\sin\theta| = 550,000 + 40,404 - 129,510 = 460,894\text{ N}$$
$$a_{\text{dec}} = \frac{F_{\text{net\_retarding}}}{m} = \frac{460,894\text{ N}}{165,500\text{ kg}} = 2.78486 \approx 2.7856\text{ m/s}^2$$

---

## 4. Stopping Distance & Safe Speed Formulation

### 4.1 Stopping Kinematics
Total stopping distance $S_{\text{stop}}$ comprises reaction distance during perception/command/actuator build-up lag plus mechanical deceleration distance:

$$S_{\text{stop}} = v \cdot \tau_{\text{total}} + \frac{v^2}{2 a_{\text{dec}}}$$

Where total electronic-to-pneumatic lag $\tau_{\text{total}} = 0.4371\text{ s}$ (P99 budget):
- $\tau_{\text{sensor}} = 0.025\text{ s}$ (25 ms)
- $\tau_{\text{governor}} = 0.050\text{ s}$ (50 ms)
- $\tau_{\text{can}} = 0.0126\text{ s}$ (12.6 ms)
- $\tau_{\text{actuator}} = 0.2000\text{ s}$ (200 ms nominal, up to 350 ms worst-case)
- Conservative engineering safety margin = $0.1495\text{ s}$

### 4.2 Fundamental Safety Invariant
At all times, the total stopping envelope plus the defensive standstill buffer must not exceed the available effective sightline:

$$S_{\text{stop}} + S_{\text{base}} \le R_{\text{effective}}$$

Where $S_{\text{base}} = 5.0\text{ m}$ (half truck length clearance).

### 4.3 Safe Speed Quadratic Solution
Solving $v \cdot \tau + \frac{v^2}{2a} = R_{\text{effective}} - S_{\text{base}}$ yields the closed-form safe speed ceiling:

$$v_{\text{stop}} = -a_{\text{dec}} \tau_{\text{total}} + \sqrt{(a_{\text{dec}} \tau_{\text{total}})^2 + 2 a_{\text{dec}} (R_{\text{effective}} - S_{\text{base}})}$$

The authoritative safe speed envelope combines all physical constraints:

$$v_{\text{safe}} = \min(v_{\text{stop}}, v_{\text{retarder}}, v_{\text{traction}}, v_{\text{curve}}, v_{\text{mine}})$$

The commanded velocity dispatched to the vehicle is clamped:

$$v_{\text{command}} = \min(v_{\text{dispatch}}, v_{\text{safe}})$$

---

## 5. Space Headway & Road Capacity Formulations

1. **Defensive Space Headway ($H_{\text{space}}$):**
   $$H_{\text{space}} = S_{\text{stop}}(v) + S_{\text{base}} + L_{\text{truck}}$$
   For dense fog ($12.0\text{ m}$ sightline, $v_{\text{safe}} = 5.12\text{ m/s}$):
   - $S_{\text{stop}} = 5.12 \times 0.4371 + \frac{5.12^2}{2 \times 2.7856} = 2.238 + 4.698 = 6.936\text{ m}$
   - $S_{\text{base}} = 5.000\text{ m}$
   - $L_{\text{truck}} = 10.525\text{ m}$
   - **$H_{\text{space}} = 6.94 + 5.00 + 10.53 = 22.47 \approx 22.52\text{ m}$**

2. **Theoretical Kinematic Road Flux ($C_{\text{road}}$):**
   $$C_{\text{road}} = \frac{3600 \cdot v_{\text{safe}}}{H_{\text{space}}}$$
   - Under Emergency Deceleration ($a = 2.7856\text{ m/s}^2$, $H_{\text{space}} = 22.52\text{ m}$):
     $$C_{\text{road\_emergency}} = \frac{3600 \times 5.1158}{22.52} = 817.8\text{ VPH}$$
   - Under Service Deceleration ($a = 1.2000\text{ m/s}^2$, $H_{\text{space}} = 31.36\text{ m}$):
     $$C_{\text{road\_service}} = \frac{3600 \times 5.1158}{31.36} = 587.2\text{ VPH}$$
   *Critical Scientific Classification:* These represent theoretical saturated kinematic road flow (vehicles per hour). They are **ROAD FLOW CALCULATIONS ONLY**, NOT delivered mine production (TPH).

3. **Crusher Modeled Service Ceiling:**
   $$C_{\text{crusher}} = \left(\frac{3600\text{ s}}{200\text{ s/truck}}\right) \times 91.5\text{ tonnes} = 18\text{ dumps/hr} \times 91.5\text{ t} = 1,647.0\text{ TPH}$$
   Any claim of sustained production exceeding $1647.0\text{ TPH}$ modeled crusher-service ceiling for a single gyratory pocket is physically impossible.
