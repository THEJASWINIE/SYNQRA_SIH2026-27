# FOG-ORCHESTRATOR 2.0 — KINEMATIC SCALE SPECIFICATION

**Date**: 2026-08-28  
**Author**: Principal Systems Architect, Digital Twin Engineer  
**Scope**: Explicit Kinematic Scale Normalization Specification between Physical Prototype and Mining Digital Twin

---

## 1. Prototype vs Digital Twin Parameters

| Parameter | Physical Prototype (`TRUCK_01`) | Mining Digital Twin (`BEML BH100`) | Scale Ratio |
|-----------|----------------------------------|-----------------------------------|-------------|
| **Gross Mass** | $2.20\text{ kg}$ | $165,000\text{ kg}$ ($165\text{ tonnes}$) | $1 : 75,000$ |
| **Wheel Diameter** | $0.100\text{ m}$ ($10\text{ cm}$) | $2.700\text{ m}$ ($270\text{ cm}$) | $1 : 27.0$ |
| **Maximum Safe Velocity** | $3.00\text{ m/s}$ ($10.8\text{ km/h}$) | $11.11\text{ m/s}$ ($40.0\text{ km/h}$) | $1 : 3.70$ |
| **Scale Factor ($\lambda$)** | $1.00$ | $0.27$ ($\frac{3.00}{11.11}$) | $\lambda_{\text{scale}} = 0.27$ |

---

## 2. Speed Mapping Equations

### Physical to Twin Representation:

$$v_{\text{twin\_equivalent}} = \left(\frac{v_{\text{physical}}}{v_{\text{proto\_max}}}\right) \cdot v_{\text{twin\_max}}$$

### Twin Advisory to Physical Command:

$$v_{\text{physical\_command}} = \min\left(v_{\text{twin\_advisory}} \cdot \lambda_{\text{scale}}, v_{\text{proto\_max}}\right)$$

---

## 3. Mandatory Scaling Boundaries

- **WHERE SCALING IS USED**: Used in the `KinematicScaleAdapter` to convert Digital Twin advisory speed targets down to physical prototype scale ($3.0\text{ m/s}$) for HIL validation testing.
- **WHERE SCALING MUST NOT BE USED**: Never scale physical braking distance or physical motor safety limits using mining dumper mass. The physical ESP32 local safety governor relies strictly on unscaled local sensor measurements.
