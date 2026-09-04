# FOG-ORCHESTRATOR 2.0 — IMU PROCESSING SPECIFICATION

**Date**: 2026-08-28  
**Author**: Principal Systems Architect, Embedded Systems Engineer  
**Scope**: MPU6050 LSB Conversion, Units Normalization, and Calibration Quality Exposure

---

## 1. MPU6050 Conversion Formulas

- **Acceleration ($\text{m/s}^2$)**:

$$a_i = \left(\frac{\text{Ac}_i}{16384}\right) \cdot 9.81 \quad (i \in \{X, Y, Z\})$$

- **Angular Velocity ($\text{rad/s}$)**:

$$\omega_i = \left(\frac{\text{Gy}_i}{131}\right) \cdot \left(\frac{\pi}{180}\right) \quad (i \in \{X, Y, Z\})$$

---

## 2. Canonical IMU Output Schema

```json
{
  "acceleration_mps2": { "x": 0.12, "y": -0.05, "z": 9.81 },
  "angular_velocity_rads": { "x": 0.02, "y": 0.01, "z": -0.03 },
  "estimated_pitch": null,
  "estimated_roll": null,
  "quality": "NOT_CALIBRATED"
}
```

 orientation estimate is explicitly set to `null` and `quality` set to `"NOT_CALIBRATED"` unless full multi-axis sensor fusion is active.
