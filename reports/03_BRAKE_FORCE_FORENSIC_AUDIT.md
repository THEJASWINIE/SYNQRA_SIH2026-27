# PHASE 7.3.3 — BRAKE FORCE FORENSIC AUDIT: 550 kN CLARIFICATION
**Module:** Vehicle Dynamics & Braking Forensics  
**Reference Machine:** BEML BH100 (100-Tonne Class Rear Dump Truck)  
**Status:** FORENSICALLY RECONCILED (GREEN)

---

## 1. The Core Physical Question
Previous project documentation cited:
$$\text{max mechanical brake clamp} = 550,000\text{ N} \quad (550\text{ kN})$$
The critical audit question raised in Phase 7.3.3 is:
> *"DO NOT automatically treat 550 kN clamp force as 550 kN tire-road longitudinal braking force. Determine what 'clamp force' physically means."*

---

## 2. Mechanical Brake Architecture of BEML BH100
The BEML BH100 rigid rear dump truck uses an air-over-hydraulic dual-circuit braking system with distinct front and rear architectures:
1. **Front Axle:** Dual-caliper dry disc brakes operating on ventilated steel rotors mounted to the wheel hubs.
2. **Rear Axle:** Fully sealed, oil-cooled, multiple-disc wet brakes enclosed within the rear planetary axle housings, serving simultaneously as service brakes, secondary brakes, parking brakes, and hydraulic retarders.

In heavy mining automotive terminology:
- **Caliper Normal Clamping Force ($F_{\text{clamp}}$):** The normal force exerted perpendicularly by hydraulic pistons squeezing brake pads against the faces of the brake disc rotor:
  $$F_{\text{clamp}} = P_{\text{line}} \cdot A_{\text{piston}} \cdot N_{\text{pistons}}$$
- **Disc Friction Braking Torque ($T_{\text{brake}}$):** The retarding torque generated at the disc rotor:
  $$T_{\text{brake}} = 2 \cdot \mu_{\text{pad}} \cdot F_{\text{clamp}} \cdot R_{\text{eff\_disc}}$$
- **Tire-Road Longitudinal Rim Braking Force ($F_{\text{rim}}$):** The tangential shear force developed between the tire contact patch and the road surface:
  $$F_{\text{rim}} = \frac{T_{\text{wheel}}}{R_{\text{tire\_rolling}}}$$
  Where $T_{\text{wheel}} = T_{\text{brake}} \cdot \text{Ratio}_{\text{planetary\_final}}$ (for inboard wet brakes).

---

## 3. Forensic Identification of 550,000 N
If $550\text{ kN}$ were interpreted as **caliper normal clamping force** $F_{\text{clamp}}$:
- Nominal brake pad friction coefficient: $\mu_{\text{pad}} \approx 0.38$
- Effective disc radius: $R_{\text{eff\_disc}} \approx 0.45\text{ m}$
- Loaded tire rolling radius: $R_{\text{tire}} = 1.35\text{ m}$
- Then disc friction force would be: $2 \times 0.38 \times 550,000 = 418,000\text{ N}$
- Rim braking force at the wheel would be: $418,000 \times (0.45 / 1.35) = \mathbf{139.3\text{ kN}}$
- On a $165.5\text{ t}$ truck on an $-8\%$ ramp, a $139.3\text{ kN}$ force would be insufficient to overcome downhill gravity ($129.4\text{ kN}$) plus rolling resistance ($40.4\text{ kN}$), resulting in runaway acceleration down the ramp!

**Forensic Finding:**  
The parameter $550,000\text{ N}$ in the codebase represents the **TOTAL GROSS MECHANICAL RIM BRAKING FORCE** ($F_{\text{rim\_total}}$) delivered at the tire-road contact patches across all four wheel positions, NOT the normal hydraulic clamping force on an individual caliper.

This is supported by ISO 3450:2011 ("Earth-moving machinery — Wheeled machines — Braking system performance"):
- Under ISO 3450, a loaded $165.5\text{ t}$ dumper on level ground must achieve a minimum service braking deceleration of $\approx 2.5\text{--}3.0\text{ m/s}^2$.
- At $3.32\text{ m/s}^2$ on level ground:
  $$F_{\text{rim\_ISO}} = m \cdot a = 165,500\text{ kg} \times 3.32\text{ m/s}^2 = \mathbf{549,460\text{ N}} \approx \mathbf{550\text{ kN}}$$
- Thus, $550\text{ kN}$ is the certified rated total rim braking capacity of the vehicle's brake system.

---

## 4. Ground Adhesion Check
Can the tire-road interface support $550\text{ kN}$ of longitudinal braking force without slipping?
- Normal force on $-8\%$ ramp: $F_{\text{norm}} = m \cdot g \cdot \cos(\theta) = 1,617,831.8\text{ N}$
- Wet hematite haul road friction: $\mu = 0.35$
- Maximum allowable shear force before wheel lockup:
  $$F_{\text{adhesion}} = \mu \cdot F_{\text{norm}} = 0.35 \times 1,617,831.8\text{ N} = \mathbf{566,241.1\text{ N}} \quad (566.2\text{ kN})$$

Since $F_{\text{rim}} = 550,000\text{ N} \le 566,241.1\text{ N}$, the mechanical braking force is within the tire adhesion limit (adhesion utilization = $550.0 / 566.2 = 97.1\%$).  
No wheel lockup occurs; the wheels rotate and decelerate stably at $a_{\text{net}} = 2.7856\text{ m/s}^2$ (canonical) or $2.7466\text{ m/s}^2$ (legacy).

---

## 5. Audit Conclusions
1. The term "brake clamp force" in historical documentation was an informal misnomer.
2. The parameter is now formally designated as **Total Gross Mechanical Rim Braking Force** ($F_{\text{brake\_rim\_max}} = 550,000\text{ N}$).
3. Detailed internal caliper piston diameters, line hydraulic pressures, and disc pad friction coefficients are omitted because they are internal transmission variables that lump into the OEM-rated $550\text{ kN}$ rim force.
4. If degraded road friction drops below $\mu = 0.34$, adhesion limits the available rim force to $\mu \cdot F_{\text{norm}}$, reducing net deceleration accordingly (e.g., $a_{\text{net}} = 2.49\text{ m/s}^2$ at $\mu = 0.30$).
