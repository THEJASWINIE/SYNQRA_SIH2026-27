# FOG-ORCHESTRATOR 2.0 — Hardware Integration & Bench Results
**Document ID:** `DOC-06-VAL-02` | **Audited Standard:** Bench Hardware Validation

---

## 1. Physical Bench Motor Calibration Staircase

Using `calibrate_vehicle_max_speed.py`, both prototype chassis were actuated across staircase PWM levels under loaded wheel conditions:

| Commanded PWM | Vehicle A (`TRUCK_01`) Speed | Vehicle B (`TRUCK_02`) Speed | Optical Encoder Pulse Rate | Status |
| :---: | :---: | :---: | :---: | :---: |
| **0** | 0.00 m/s | 0.00 m/s | 0 pps | Zero-PWM boot verified |
| **60** | 0.28 m/s | 0.24 m/s | 51.4 pps | Linear motor engagement |
| **120** | 0.68 m/s | 0.62 m/s | 124.7 pps | Mid-range haul speed |
| **180** | 1.12 m/s | 1.02 m/s | 205.4 pps | Fast transit speed |
| **220** | **1.40 m/s (MAX)** | 1.21 m/s | 256.8 pps | Vehicle A thermal ceiling |
| **240** | — | **1.30 m/s (MAX)** | 238.5 pps | Vehicle B thermal ceiling |

---

## 2. IMU Grade & Tilt Angle Validation

The MPU6050 6-DOF IMUs were validated on calibrated angular incline test blocks:
- **0.0% Grade (0.0°)**: Measured pitch = $-0.12^\circ$ ($\pm 0.08^\circ$).
- **8.0% Grade (4.57°)**: Measured pitch = $+4.52^\circ$ ($\pm 0.11^\circ$).
- **12.0% Grade (6.84°)**: Measured pitch = $+6.79^\circ$ ($\pm 0.14^\circ$).
