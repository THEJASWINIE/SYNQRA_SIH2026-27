# CALIBRATION TRUTH TABLE — FOG-ORCHESTRATOR 2.0
**Adversarial Parameter Audit & Reconciled Hardware Truth**
**Document Date:** 2026-09-27
**Audit Level:** Level-4 Forensic (Direct Code & Hardware Inspection)

---

## 1. Physical vs. Empirical Calibration Parameters

| Parameter | Vehicle A (`TRUCK_01`) | Vehicle B (`TRUCK_02`) | Physical & Mathematical Meaning | Definitive Source |
|:---|:---:|:---:|:---|:---|
| **Encoder Sensor Model** | Slotted Optical Interrupter (LM393) | Slotted Optical Interrupter (LM393) | Single-beam infrared slot detector (non-quadrature) | Physical Hardware Inspection |
| **Encoder Signal Pin** | GPIO 35 (`SPEED_SENSOR_PIN`) | GPIO 35 (`SPEED_SENSOR_PIN`) | Input pin on ESP32 | `sketch_aug26a.ino:50`<br>`VEHICLE_B_...ino:54` |
| **Interrupt Trigger Edge** | `RISING` | `RISING` | Triggered on leading edge of slotted wheel pulse | `sketch_aug26a.ino:2186`<br>`VEHICLE_B_...ino:2324` |
| **Physical Disc Slots / PPR ($\text{PPR}_{\text{raw}}$)** | **42.0 pulses/rev** | **43.0 pulses/rev** | Physical optical disc count per single 360° wheel rotation | `sketch_aug26a.ino:51`<br>`VEHICLE_B_...ino:55` |
| **Effective Calibration Divisor ($K_{\text{cal}}$)** | **34.58 pulses/rev** | **34.58 pulses/rev** | Empirical scaling factor derived from 10s bench run under load | `sketch_aug26a.ino:52`<br>`VEHICLE_B_...ino:56` |
| **Calibration Ratio ($K_{\text{cal}} / \text{PPR}_{\text{raw}}$)** | **0.82333** (-17.67%) | **0.80418** (-19.58%) | Empirical reduction to compensate for optical edge jitter & wheel slip | Derived: $34.58 / 42.0$<br>Derived: $34.58 / 43.0$ |
| **Wheel Diameter ($D$)** | **0.060 m** (6.0 cm) | **0.060 m** (6.0 cm) | Physical outer tire diameter on vehicle chassis | `sketch_aug26a.ino:54`<br>`VEHICLE_B_...ino:59` |
| **Wheel Circumference ($C = \pi D$)** | **0.188496 m** (188.5 mm) | **0.188496 m** (188.5 mm) | Linear distance traveled per 1 complete 360° wheel roll | $\pi \times 0.060\text{ m}$ |
| **Raw Distance per Pulse ($C / \text{PPR}_{\text{raw}}$)** | **0.004488 m/pulse** (4.488 mm) | **0.004384 m/pulse** (4.384 mm) | Theoretical geometric displacement per unscaled optical pulse | $0.188496 / 42.0$<br>$0.188496 / 43.0$ |
| **Effective Distance per Pulse ($C / K_{\text{cal}}$)** | **0.005451 m/pulse** (5.451 mm) | **0.005451 m/pulse** (5.451 mm) | Empirical software distance accumulation factor | $0.188496 / 34.58$ |
| **Wheel RPM Formula** | $\left(\frac{\text{pps}}{34.58}\right) \times 60.0$ | $\left(\frac{\text{pps}}{34.58}\right) \times 60.0$ | RPM derived from empirical pulses-per-second | Firmware `updateSpeed()` |
| **Vehicle Speed Formula** | $\frac{\text{wheelRPM} \times \pi \times D}{60.0}$ | $\frac{\text{wheelRPM} \times \pi \times D}{60.0}$ | Linear speed calculated from calibrated RPM | Firmware `updateSpeed()` |
| **Motor Driver Model** | L298N Dual H-Bridge | TB6612FNG Dual H-Bridge | Motor power stage & direction control | Hardware Inspection |

---

## 2. Definitive Semantic Clarification: Why $34.58$ is NOT "Physical PPR"

1. **Hardware Reality:** The physical optical disc mounted on the chassis has an integer number of mechanical slots generating **42 rising edge interrupts per wheel revolution on Vehicle A** and **43 rising edge interrupts on Vehicle B**.
2. **Empirical Reality:** Under physical motion, micro-slip between the rubber tread and test surface, combined with optical pulse debouncing, resulted in an empirical accumulation rate of **34.58 pulses per effective revolution**.
3. **Engineering Verdict:**
   - Labeling $34.58$ as "PPR" without qualification is an engineering misnomer.
   - The authoritative naming convention across the codebase is:
     - `RAW_ENCODER_PPR`: **42.0** (Vehicle A), **43.0** (Vehicle B)
     - `ENCODER_EFFECTIVE_PPR` (or $K_{\text{cal}}$): **34.58** (Both vehicles)
     - `PULSES_PER_REV`: Aliased strictly to `ENCODER_EFFECTIVE_PPR` for velocity calculation.
