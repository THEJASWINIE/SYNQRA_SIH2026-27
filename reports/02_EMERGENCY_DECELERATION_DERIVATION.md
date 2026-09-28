# PHASE 7.3.3 — EMERGENCY DECELERATION DERIVATION
**Module:** Physics & Safety Governor  
**Reference Machine:** BEML BH100 (100-Tonne Class Rear Dump Truck)  
**Location:** NMDC Bailadila Deposit 5 (-8% Ramp Grade)  
**Status:** DERIVED & RECONCILED (GREEN)

---

## 1. Problem Statement
The emergency deceleration value of **$2.7466\text{ m/s}^2$** has been used across Phases 7.2, 7.3.1, and 7.3.2 to calculate emergency safe speed ($5.1158\text{ m/s}$ at $12\text{ m}$ visibility with $\tau = 437.1\text{ ms}$).  
This audit provides the complete first-principles physical derivation of this deceleration from the longitudinal force balance of a fully loaded haul truck descending an unpaved haul road ramp.

---

## 2. First-Principles Longitudinal Force Balance

For a vehicle of mass $m$ descending an incline of grade angle $\theta$, the longitudinal equation of motion during braking is:

$$m \cdot a_{\text{net}} = F_{\text{net}} = F_{\text{brake}} + F_{\text{roll}} - F_{\text{grade}} - F_{\text{aero}}$$

Where:
- $m$: Gross Vehicle Weight ($165,500\text{ kg}$ canonical, $165,000\text{ kg}$ legacy).
- $\theta$: Ramp angle, defined by civil grade percentage $G = -8.0\%$:
  $$\theta = \arctan\left(\frac{|G|}{100}\right) = \arctan(0.08) = 0.079830\text{ rad} \approx 4.5739^\circ$$
  $$\cos(\theta) = 0.996815, \quad \sin(\theta) = 0.079745$$
- $g$: Gravitational acceleration ($9.80665\text{ m/s}^2$ canonical standard, $9.81\text{ m/s}^2$ legacy).
- $F_{\text{norm}}$: Normal force perpendicular to road surface:
  $$F_{\text{norm}} = m \cdot g \cdot \cos(\theta)$$
- $F_{\text{grade}}$: Downhill gravitational component (accelerating vehicle, opposing braking):
  $$F_{\text{grade}} = m \cdot g \cdot \sin(\theta)$$
- $F_{\text{roll}}$: Rolling resistance force:
  $$F_{\text{roll}} = C_{\text{rr}} \cdot F_{\text{norm}} = C_{\text{rr}} \cdot m \cdot g \cdot \cos(\theta)$$
- $F_{\text{brake}}$: Longitudinal rim braking force delivered at the tire-road interface.
- $F_{\text{aero}}$: Aerodynamic drag force ($F_{\text{aero}} = \frac{1}{2} \rho C_d A v^2$). At speeds below $6\text{ m/s}$ ($< 22\text{ km/h}$), aerodynamic drag is $< 250\text{ N}$ ($< 0.05\%$ of braking force) and is conservatively neglected ($F_{\text{aero}} \equiv 0$).

---

## 3. Tire-Road Adhesion Constraint

Longitudinal braking force at the tire-road contact patch cannot exceed the Coulomb friction adhesion limit without inducing wheel lockup and uncontrolled skidding:

$$F_{\text{adhesion}} = \mu \cdot F_{\text{norm}} = \mu \cdot m \cdot g \cdot \cos(\theta)$$

For wet hematite haul roads, nominal friction is $\mu = 0.35$.
- For canonical $m = 165,500\text{ kg}$, $g = 9.80665\text{ m/s}^2$:
  $$F_{\text{norm}} = 165500 \times 9.80665 \times 0.996815 = 1,617,831.8\text{ N}$$
  $$F_{\text{adhesion}} = 0.35 \times 1,617,831.8 = \mathbf{566,241.1\text{ N}} \quad (566.24\text{ kN})$$

Because the mechanical rated braking effort is $F_{\text{rim\_max}} = 550,000\text{ N}$ ($550\text{ kN}$):
$$F_{\text{brake}} = \min(F_{\text{rim\_max}}, F_{\text{adhesion}}) = \min(550000, 566241) = \mathbf{550,000.0\text{ N}}$$
Thus, the mechanical braking force is fully transmissible to the ground without exceeding tire adhesion on wet roads.

---

## 4. Deceleration Derivation Across Configurations

### Configuration A: Canonical Machine ($165.5\text{ t}$, $C_{\text{rr}} = 0.025$, $g = 9.80665\text{ m/s}^2$)
- Mass: $m = 165,500\text{ kg}$
- Normal Force: $F_{\text{norm}} = 1,617,831.8\text{ N}$
- Downhill Gravity Force: $F_{\text{grade}} = 165500 \times 9.80665 \times 0.079745 = 129,426.5\text{ N}$
- Rolling Resistance Force: $F_{\text{roll}} = 0.025 \times 1,617,831.8 = 40,445.8\text{ N}$
- Gross Rim Braking Force: $F_{\text{brake}} = 550,000.0\text{ N}$
- Net Retarding Force:
  $$F_{\text{net}} = 550,000.0 + 40,445.8 - 129,426.5 = \mathbf{461,019.3\text{ N}}$$
- Net Longitudinal Deceleration:
  $$a_{\text{net}} = \frac{461,019.3\text{ N}}{165,500\text{ kg}} = \mathbf{2.785615\text{ m/s}^2} \approx \mathbf{2.7856\text{ m/s}^2}$$

### Configuration B: Legacy Simulation Model ($165.0\text{ t}$, $C_{\text{rr}} = 0.020$, $g = 9.81\text{ m/s}^2$)
- Mass: $m = 165,000\text{ kg}$
- Normal Force: $F_{\text{norm}} = 165000 \times 9.81 \times 0.996815 = 1,613,494.6\text{ N}$
- Downhill Gravity Force: $F_{\text{grade}} = 165000 \times 9.81 \times 0.079745 = 129,079.3\text{ N}$
- Rolling Resistance Force: $F_{\text{roll}} = 0.020 \times 1,613,494.6 = 32,269.9\text{ N}$
- Gross Rim Braking Force: $F_{\text{brake}} = 550,000.0\text{ N}$
- Net Retarding Force:
  $$F_{\text{net}} = 550,000.0 + 32,269.9 - 129,079.3 = \mathbf{453,190.6\text{ N}}$$
- Net Longitudinal Deceleration:
  $$a_{\text{net}} = \frac{453,190.6\text{ N}}{165,000\text{ kg}} = \mathbf{2.746609\text{ m/s}^2} \approx \mathbf{2.7466\text{ m/s}^2}$$

**Reconciliation Conclusion:**  
The reported value of **$2.7466\text{ m/s}^2$** is the exact analytical result of the legacy simulation parameter set ($165.0\text{ t}$, $C_{\text{rr}}=0.020$, $g=9.81$).  
The canonical machine parameter set ($165.5\text{ t}$, $C_{\text{rr}}=0.025$, $g=9.80665$) produces **$2.7856\text{ m/s}^2$** ($+1.4\%$ higher deceleration due to higher rolling resistance).  
Using $2.7466\text{ m/s}^2$ in the safety governor is slightly more conservative (predicts longer stopping distance), preserving a safe margin.

---

## 5. Three Distinct Deceleration Quantities

| Deceleration Quantity | Value | Status | Evidence Level | Rationale |
|:---|:---:|:---:|:---:|:---|
| **A. Physically Derived Deceleration** | $2.7856\text{ m/s}^2$ (Canonical) / $2.7466\text{ m/s}^2$ (Legacy) | **GREEN** | DERIVED_MODEL | Derived from first-principles longitudinal force balance on $-8\%$ ramp with $550\text{ kN}$ rim force. |
| **B. Measured Field Deceleration** | **UNAVAILABLE** | **OPEN** | FIELD_UNVALIDATED | Physical decelerometer testing on a live BEML BH100 at Bailadila has not been performed. |
| **C. Engineering Sensitivity Decelerations** | $1.20\text{ m/s}^2$ (Service comfort)<br>$2.49\text{ m/s}^2$ (Slick mud $\mu=0.30$)<br>$3.32\text{ m/s}^2$ (ISO 3450 level) | **YELLOW** | ENGINEERING_SCENARIO | Operational boundary envelopes for degraded surfaces and driver comfort. |

**Final Rule:** Emergency deceleration remains an **ENGINEERING DERIVED MODEL PARAMETER**, not a field-measured physical parameter.
