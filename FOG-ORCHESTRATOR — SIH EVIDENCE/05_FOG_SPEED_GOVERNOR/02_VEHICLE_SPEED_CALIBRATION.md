# FOG-ORCHESTRATOR 2.0 — Vehicle Speed Calibration Truth Table
**Document ID:** `DOC-05-FSG-02` | **Audited Standard:** Empirical Hardware Calibration

---

## 1. Definitive Semantic Clarification: $34.58$ is NOT Physical PPR

- **Physical Optical Hardware**:
  - Vehicle A (`TRUCK_01`): Slotted optical disc with **42 mechanical slots** (`RAW_ENCODER_PPR = 42.0`).
  - Vehicle B (`TRUCK_02`): Slotted optical disc with **43 mechanical slots** (`RAW_ENCODER_PPR = 43.0`).
- **Empirical Calibration Divisor ($K_{cal}$)**:
  - Under physical motion under load, optical edge debounce and tire micro-slip yield an effective accumulation of **$34.58\text{ pulses/revolution}$**.
  - Calling 34.58 "physical PPR" is an engineering misnomer. The correct authoritative term is **$K_{cal} = \text{Empirical Calibration Divisor}$**.

---

## 2. Reconciled Motor Calibration Truth Table

| Calibration Parameter | Vehicle A (`TRUCK_01`) | Vehicle B (`TRUCK_02`) | Provenance & Source |
| :--- | :---: | :---: | :--- |
| **Motor Driver Hardware** | **L298N Dual H-Bridge** | **Toshiba TB6612FNG MOSFET** | Physical Hardware Inspection |
| **Wheel Diameter ($D$)** | **0.060 m** (60 mm) | **0.060 m** (60 mm) | Direct Vernier Caliper Measurement |
| **Wheel Circumference ($C$)** | **0.188496 m** | **0.188496 m** | $\pi \times 0.060\text{ m}$ |
| **Physical Disc Slots / PPR** | **42 slots** | **43 slots** | Raw Optical Slot Count |
| **Empirical Calibration Divisor ($K_{cal}$)**| **34.58 pulses/rev** | **34.58 pulses/rev** | 10-Second Physical Bench Test under load |
| **Linear Resolution per Pulse** | **5.451 mm/pulse** | **5.451 mm/pulse** | $C / K_{cal} = 0.188496 / 34.58$ |
| **Safe PWM Ceiling** | **220** (out of 255) | **240** (out of 255) | Thermal & Motor Saturation Limits |
| **Calibrated Max Speed ($V_{max}$)** | **1.40 m/s** | **1.30 m/s** | Physical Optical Tachometer Staircase |
| **Baseline Haul Road Limit ($v_{baseline}$)**| **0.80 m/s** | **0.80 m/s** | Configured Road Speed Ceiling |
