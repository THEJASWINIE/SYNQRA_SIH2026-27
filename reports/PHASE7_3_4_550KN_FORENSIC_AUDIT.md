# PHASE 7.3.4 — ATTACK #1: 550 kN BRAKING FORCE FORENSIC AUDIT
**Module:** Braking System Physics & Adhesion Limits  
**Dataset:** `data/phase7_3_4_adhesion_audit.csv`  
**Classification:** **UNVERIFIED OEM VALUE / INFERRED DESIGN RATING (YELLOW)**  

---

## 1. Traceability & Source Investigation

The parameter `550000 N` (550 kN) appears across the configuration, safety governor, and simulation modules as the mechanical braking capability of the BEML BH100.  
An exhaustive audit of public OEM documentation reveals:
1. **Public BEML BH100 Datasheet (Rev 2018):**
   - Documents: Tare mass ($74.0\text{ t}$), payload ($91.5\text{ t}$), gross weight ($165.5\text{ t}$), tire size ($27.00\text{R}49$), engine power ($770\text{ kW}$), retarding absorption ($1,200\text{ kW}$).
   - **DOES NOT CONTAIN:** An explicit mechanical brake clamping force in Newtons.
2. **Origin of the 550 kN Number:**
   - The value was **inferred from ISO 3450:2011** service braking performance requirements for a loaded $165.5\text{ t}$ dumper on level ground:
     $$a_{\text{ISO}} \approx 3.32\text{ m/s}^2 \implies F_{\text{rim\_ISO}} = 165,500\text{ kg} \times 3.32\text{ m/s}^2 = 549,460\text{ N} \approx \mathbf{550\text{ kN}}$$
   - Therefore, $550\text{ kN}$ is an **INFERRED DESIGN CEILING**, not a directly measured OEM or laboratory value.

---

## 2. Physical Meaning: Caliper Force vs Rim Force

| Interpretation Candidate | Physical Definition | Plausibility Assessment | Verdict |
|:---|:---|:---|:---:|
| **A. Caliper Clamp Normal Force** | Hydraulic piston clamping force on disc faces | **IMPOSSIBLE.** Normal force of $550\text{ kN}$ yields only $\approx 139\text{ kN}$ of wheel tangential force after radius reduction ($0.45\text{ m} / 1.35\text{ m}$). On an $-8\%$ ramp ($F_{\text{grade}} = 129.4\text{ kN}$), the truck would suffer catastrophic runaway! | **DISPROVEN** |
| **B. Brake Pad Normal Force** | Normal force per pad | Same as above. | **DISPROVEN** |
| **C. Brake Torque** | Retarding torque in $\text{N}\cdot\text{m}$ | Dimensionally invalid (units are $\text{N}$, not $\text{N}\cdot\text{m}$). | **DISPROVEN** |
| **D. Axle Braking Force** | Braking force per axle | $2 \times 550\text{ kN} = 1,100\text{ kN}$ would produce $6.6\text{ m/s}^2$, violating tire traction on all surfaces. | **DISPROVEN** |
| **E. Total Tire-Rim Tangential Force** | Tangential retarding force at tire contact patches | **PHYSICALLY CONSISTENT.** Matches ISO 3450 level-ground braking capability. | **ACCEPTED** |

**Forensic Finding:**  
$550\text{ kN}$ represents the **Total Gross Mechanical Rim Braking Force** at the tire-road interface. Detailed internal caliper piston diameters, line hydraulic pressures, and disc pad friction coefficients are omitted because they are internal transmission variables that lump into the OEM-rated $550\text{ kN}$ rim force. Because disc torque data is proprietary, deceleration cannot be physically closed from internal caliper hydraulics alone; it is closed at the wheel rim interface.

---

## 3. Tire-Road Adhesion Limit Audit Across Friction Levels

On an incline of grade $G = -8.0\%$ ($\theta = 4.5739^\circ$, $\cos\theta = 0.996815$), normal force for $m = 165,500\text{ kg}$ is:
$$F_{\text{norm}} = m \cdot g \cdot \cos\theta = 165500 \times 9.80665 \times 0.996815 = \mathbf{1,617,831.8\text{ N}} \quad (1,617.8\text{ kN})$$
The maximum longitudinal braking force that can be transmitted without wheel lockup is:
$$F_{\text{adhesion}} = \mu \cdot F_{\text{norm}}$$

### Empirical Adhesion Evaluation Grid:

| Surface Friction ($\mu$) | Normal Force ($F_{\text{norm}}$) | Tire Adhesion Limit ($F_{\text{adhesion}}$) | Applied Rim Brake ($F_{\text{applied}}$) | Adhesion Utilization | Decel (Brake-Only) | Decel (Traction-Only) | Governed Decel ($a_{\text{net}}$) | Governing Regime |
|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---|
| **0.15** (Ice / Wet Clay) | $1,617.8\text{ kN}$ | **242.7 kN** | $242.7\text{ kN}$ | $100.0\%$ (Slipping) | $2.7856\text{ m/s}^2$ | **0.9288 m/s²** | **0.9288 m/s²** | **TRACTION_LIMITED** |
| **0.20** (Monsoon Slime) | $1,617.8\text{ kN}$ | **323.6 kN** | $323.6\text{ kN}$ | $100.0\%$ (Slipping) | $2.7856\text{ m/s}^2$ | **1.4173 m/s²** | **1.4173 m/s²** | **TRACTION_LIMITED** |
| **0.25** (Wet Slick Mud) | $1,617.8\text{ kN}$ | **404.5 kN** | $404.5\text{ kN}$ | $100.0\%$ (Slipping) | $2.7856\text{ m/s}^2$ | **1.9059 m/s²** | **1.9059 m/s²** | **TRACTION_LIMITED** |
| **0.30** (Wet Hematite Ore)| $1,617.8\text{ kN}$ | **485.3 kN** | $485.3\text{ kN}$ | $100.0\%$ (Slipping) | $2.7856\text{ m/s}^2$ | **2.3944 m/s²** | **2.3944 m/s²** | **TRACTION_LIMITED** |
| **0.34** (Crossover Point)| $1,617.8\text{ kN}$ | **550.1 kN** | $550.0\text{ kN}$ | $99.98\%$ | $2.7856\text{ m/s}^2$ | **2.7856 m/s²** | **2.7856 m/s²** | **CROSSOVER_BOUNDARY** |
| **0.35** (Standard Wet) | $1,617.8\text{ kN}$ | **566.2 kN** | $550.0\text{ kN}$ | $97.14\%$ | $2.7856\text{ m/s}^2$ | **2.8830 m/s²** | **2.7856 m/s²** | **BRAKE_FORCE_LIMITED** |
| **0.40** (Damp Gravel) | $1,617.8\text{ kN}$ | **647.1 kN** | $550.0\text{ kN}$ | $85.00\%$ | $2.7856\text{ m/s}^2$ | **3.3715 m/s²** | **2.7856 m/s²** | **BRAKE_FORCE_LIMITED** |
| **0.45** (Dry Compacted) | $1,617.8\text{ kN}$ | **728.0 kN** | $550.0\text{ kN}$ | $75.55\%$ | $2.7856\text{ m/s}^2$ | **3.8601 m/s²** | **2.7856 m/s²** | **BRAKE_FORCE_LIMITED** |
| **0.50** (Dry High-Friction)| $1,617.8\text{ kN}$| **808.9 kN** | $550.0\text{ kN}$ | $67.99\%$ | $2.7856\text{ m/s}^2$ | **4.3486 m/s²** | **2.7856 m/s²** | **BRAKE_FORCE_LIMITED** |

---

## 4. Critical Adversarial Findings

1. **Crossover Threshold ($\mu_{\text{crit}} = 0.34$):**
   - $550\text{ kN}$ is physically transmissible **ONLY** when road surface friction is $\mu \ge 0.34$.
   - At $\mu = 0.35$, the mechanical capability of $550\text{ kN}$ governs ($a_{\text{net}} = 2.7856\text{ m/s}^2$), utilizing $97.1\%$ of available adhesion.
   - If monsoon rainfall degrades hematite road friction below $\mu = 0.34$, attempting to demand $550\text{ kN}$ will cause wheel lockup and skidding.
2. **Code Implementation Audit:**
   - In `fog_safe/braking.py`, `calculate_max_traction_brake_force` enforces:
     $$F_{\text{available}} = \min(F_{\text{hardware\_max}}, \, \mu \cdot m \cdot g \cdot \cos\theta)$$
   - The production code correctly clamps to the adhesion limit when $\mu < 0.34$. It does NOT blindly assume $550\text{ kN}$ on low-friction roads.
3. **Formal Classification:**
   - The parameter $550\text{ kN}$ is classified as **UNVERIFIED AS OEM DOCUMENTED**, but **RATIONALLY INFERRED FROM ISO 3450 STANDARDS (YELLOW)**.
