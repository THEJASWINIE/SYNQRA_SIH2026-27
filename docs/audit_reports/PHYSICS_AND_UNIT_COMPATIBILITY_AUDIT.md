# FOG-ORCHESTRATOR 2.0 — PHYSICS AND UNIT COMPATIBILITY AUDIT (AUDIT PART 4)

**Date**: 2026-08-28  
**Author**: Principal Systems Architect, Safety-Critical Systems Verification Engineer  
**Scope**: Physics Equations, Unit Conversions, and Scaling Analysis between Physical Prototype and Heavy Mining Dumper Models

---

## 1. Unit Conversion Matrix

| Physical Quantity | Phase 1 Native Unit | Phase 2 Required Unit | Equation / Conversion Formula | Action Required |
|-------------------|---------------------|-----------------------|-------------------------------|-----------------|
| **Wheel Speed** | RPM (rev/min) | Linear speed $v$ (m/s) | $v = \frac{\text{RPM} \cdot 2\pi r}{60}$ | Unit Converter Adapter |
| **Linear Velocity** | m/s & km/h | m/s | $v_{\text{km/h}} = v_{\text{m/s}} \times 3.6$ | Direct mapping |
| **IMU Acceleration** | Raw LSB / $m/s^2$ | $m/s^2$ ($AX, AY$) | $a_{\text{physical}} = \frac{\text{LSB}}{16384} \cdot 9.81$ | IMU Normalization Adapter |
| **IMU Gyroscope** | Raw LSB / $rad/s$ | $rad/s$ ($\dot{\psi}$) | $\omega_{\text{physical}} = \frac{\text{LSB}}{131} \cdot \frac{\pi}{180}$ | IMU Normalization Adapter |
| **Stopping Distance** | N/A (Local sensor) | Meters ($S_{\text{stop}}$) | $S_{\text{stop}} = v \cdot t_{\text{react}} + \frac{v^2}{2g(\mu \cos\theta - \sin\theta)}$ | Analytical physics calculation |
| **Fog Visibility** | N/A | Meters ($R_{\text{effective}}$) | $S_{\text{stop}} + S_{\text{margin}} \le R_{\text{effective}}$ | Digital Twin weather model feed |

---

## 2. Physical Prototype vs BEML BH100 Mining Dumper Scaling Analysis

> [!WARNING]
> The physical prototype ($2\text{ kg}$ chassis) cannot be assumed to possess identical mass, momentum, thermal retarder dynamics, or braking distances as a $165\text{-tonne}$ BEML BH100 heavy mining dumper.

### Scale Parameter Comparison:

| Parameter | Phase 1 Prototype | Phase 2 BEML BH100 Dumper | Scale Ratio | Engineering Implication |
|-----------|-------------------|---------------------------|-------------|-------------------------|
| **Gross Mass ($m$)** | $2.0\text{ kg}$ | $165,000\text{ kg}$ ($165\text{ t}$) | $1 : 82,500$ | Momentum & braking energy differ by 5 orders of magnitude |
| **Wheel Diameter ($D$)** | $0.10\text{ m}$ ($10\text{ cm}$) | $2.70\text{ m}$ ($270\text{ cm}$) | $1 : 27.0$ | Pulse per revolution scaling requires discrete wheel radius $r$ |
| **Max Safe Velocity** | $3.0\text{ m/s}$ ($10.8\text{ km/h}$) | $11.11\text{ m/s}$ ($40.0\text{ km/h}$) | $1 : 3.7$ | Speed commands must be normalized to prototype scale |
| **Kinematic Inertia** | Low (Instant stop) | High (Long deceleration distance) | Non-linear | Local vehicle safety governor must enforce physical stopping bounds |

---

## 3. Mandatory Speed Normalization Rule

When the Digital Twin issues an advisory target speed $v_{\text{advisory}}^{\text{mine}}$ (for a 165t dumper), the **Unit Converter Adapter** must apply kinematic speed scaling before routing to the physical prototype:

$$v_{\text{command}}^{\text{prototype}} = \min\left(v_{\text{advisory}}^{\text{mine}} \cdot \lambda_{\text{scale}}, v_{\text{max}}^{\text{prototype}}\right)$$

where $\lambda_{\text{scale}} = \frac{v_{\text{max}}^{\text{prototype}}}{v_{\text{max}}^{\text{mine}}} = \frac{3.0}{11.11} \approx 0.27$.

The local physical safety governor on the ESP32 then enforces:

$$v_{\text{applied}} = \min\left(v_{\text{command}}^{\text{prototype}}, v_{\text{local\_safe}}\right)$$

This guarantees physical safety while respecting the Digital Twin's speed reduction ratio under fog conditions.
