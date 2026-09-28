# FOG-ORCHESTRATOR 2.0 — Physical Hardware Prototype Architecture
**Document ID:** `DOC-03-HW-01` | **Audited Standard:** Level-4 Physical Inspection

---

## 1. Prototype Overview & Chassis Specifications

The physical prototype comprises two independently instrumented scale haulage vehicles designed to evaluate dual-vehicle V2V, V2I, and safety governor execution on physical test benches:

| Hardware Subsystem | Vehicle A (`TRUCK_01`) | Vehicle B (`TRUCK_02`) | Physical Specifications |
| :--- | :--- | :--- | :--- |
| **Microcontroller** | ESP32-WROOM-32 (Dual Core 240 MHz) | ESP32-WROOM-32 (Dual Core 240 MHz) | 520 KB SRAM, 4 MB SPI Flash, FreeRTOS |
| **Motor Driver** | **L298N Dual Full-Bridge** | **Toshiba TB6612FNG Dual MOSFET** | Independent power stages & thermal profiles |
| **Speed Sensor** | Slotted Optical Interrupter (LM393) | Slotted Optical Interrupter (LM393) | Single-beam IR slot detector (GPIO 35) |
| **Physical Disc Slots** | **42 slots** | **43 slots** | Raw mechanical disc slot count |
| **Effective Calibration ($K_{cal}$)**| **34.58 pulses/rev** | **34.58 pulses/rev** | Calibrated under load to compensate for slip |
| **Wheel Diameter ($D$)** | **0.060 m** (60 mm) | **0.060 m** (60 mm) | Tread outer diameter ($C = 0.188496\text{ m}$) |
| **IMU Sensor** | MPU6050 (6-DOF Accelerometer/Gyro) | MPU6050 (6-DOF Accelerometer/Gyro) | $I^2C$ address `0x68` (SDA: 21, SCL: 22) |
| **LoRa RF Transceiver** | Semtech SX1278 (433.0 MHz) | Semtech SX1278 (433.0 MHz) | SPI interface (SCK: 18, MISO: 19, MOSI: 23) |
| **CAN Bus Controller** | ESP32 TWAI Controller (250 kbps) | ESP32 TWAI Controller (250 kbps) | SAE J1939 commercial bus transceiver |
| **Power Architecture** | 7.4V 2S LiPo + LM2596 Step-Down | 7.4V 2S LiPo + LM2596 Step-Down | Isolated 5V digital logic & motor rails |

---

## 2. Mechanical Calibration & Optical Tachometer Formulae

- **Wheel Circumference**: $C = \pi \times D = \pi \times 0.060 = 0.188496\text{ m}$ (188.5 mm).
- **Effective Linear Distance per Pulse**: $\Delta s = \frac{C}{K_{cal}} = \frac{0.188496}{34.58} = 0.005451\text{ m/pulse}$ (5.451 mm/pulse).
- **Wheel RPM**: $\text{RPM} = \left(\frac{\text{pps}}{34.58}\right) \times 60.0$.
- **Linear Vehicle Speed ($m/s$)**: $v = \frac{\text{RPM} \times \pi \times D}{60.0} = \frac{\text{pps} \times C}{34.58}$.
