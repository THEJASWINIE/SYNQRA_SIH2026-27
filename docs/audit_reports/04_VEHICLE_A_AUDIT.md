# 04_VEHICLE_A_AUDIT.md
## FOG-ORCHESTRATOR 2.0 — Vehicle A (TRUCK_01) Live Audit & Calibration Analysis
**Date / Timestamp:** 2026-09-27T09:42:00+05:30  
**Evaluator Role:** Robotics Test Engineer, Embedded Systems Engineer  
**Absolute Principle:** NO FABRICATION — Live Hardware Observation & Mathematical Consistency

---

### 1. VEHICLE A HARDWARE PROFILE

| Subsystem | Component / Specification | Hardware Verification |
| :--- | :--- | :--- |
| **Chassis / Mobile Node** | TRUCK_01 Scale Mining Dump Truck Chassis | Physical unit present on Wi-Fi hotspot (`192.168.137.43`). |
| **Microcontroller** | ESP32-WROOM-32 (Dual Core 240 MHz) | Running `esp32_code/sketch_aug26a/sketch_aug26a.ino`. |
| **Motor Driver** | L298N Dual Full-Bridge H-Bridge | Left: GPIO 25, 26, PWM 27; Right: GPIO 32, 33, PWM 14; STBY: 13. |
| **Wheel Diameter ($D$)** | $D = 0.060\text{ m}$ ($60\text{ mm}$) | Measured calibrated physical wheel diameter. |
| **Wheel Circumference ($C$)** | $C = \pi \cdot D = 0.18849556\text{ m}$ | Calibrated linear rolling distance per revolution. |
| **Optical Encoder Slot Count** | $\text{RAW\_ENCODER\_PPR} = 42.0\text{ pulses/rev}$ | Physical slotted optical encoder wheel on motor shaft. |
| **Effective Encoder Calibration** | $K = 34.58\text{ effective pulses/rev}$ | Empirical calibration constant defined in firmware. |
| **Inertial Measurement Unit** | MPU6050 6-DOF IMU (I2C `0x68`) | SDA: GPIO 21, SCL: GPIO 22. Live readings: $A_z \approx 14396$ raw ($8.62\text{ m/s}^2$). |
| **V2V Radio Transceiver** | SX1278 LoRa 433 MHz SPI Module | SCK: 18, MISO: 19, MOSI: 23, SS: 5, RST: 4, DIO0: 34. |

---

### 2. ENCODER MATHEMATICS & CALIBRATION FORENSICS

#### Discrepancy Found Between Firmware and Standalone Calibration Harness:
1. **Production Firmware (`sketch_aug26a.ino`):**
   ```cpp
   #define RAW_ENCODER_PPR       42.0f
   #define ENCODER_EFFECTIVE_PPR 34.58f
   #define PULSES_PER_REV        ENCODER_EFFECTIVE_PPR
   ```
   - Speed calculation:
     $$\text{wheelRPM} = \left(\frac{\text{pulsesPerSecond}}{34.58}\right) \times 60.0$$
     $$\text{vehicleSpeed} = \frac{\text{wheelRPM} \times \pi \times 0.060}{60.0} = \frac{\text{pulsesPerSecond} \times 0.188495}{34.58}$$
   - Scale factor: $\frac{34.58}{42.0} = 0.8233$ (an effective downscaling of 17.67% to account for optical pulse edge jitter and wheel slip).

2. **Standalone Speed Calibration Sketch (`esp32_code/VEHICLE_SPEED_CALIBRATION/VEHICLE A/...`):**
   - Defines raw `PPR = 42.0` and **OMITS** $K = 34.58$ entirely!
   - This causes standalone calibration readings to report a speed that is $17.67\%$ **lower** than the production firmware for the exact same pulse frequency!
   - **Severity:** **P2 (Calibration Discrepancy)**. Must unify the calibration harness to use `ENCODER_EFFECTIVE_PPR = 34.58`.

---

### 3. LIVE MOTOR & ENCODER TEST RESULTS

| Test Case | Commanded Speed / State | Observed Behavior | Measured Pulses | Distance (m) | Status | Evidence Source |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **TC-M-01** | STOP (0.0 m/s) | Vehicle stationary on bench | 0 | 0.00 | **PASS** | Telemetry frames 1–15 (`rpm: 0.00`, `speed: 0.00`) |
| **TC-M-02** | LOW PWM (Forward) | Not commanded via remote link | 0 | 0.00 | **NOT TESTED** | Bench stationary; remote dispatch command idle |
| **TC-M-03** | MED PWM (Forward) | Not commanded via remote link | 0 | 0.00 | **NOT TESTED** | Bench stationary; remote dispatch command idle |
| **TC-M-04** | HIGH SAFE PWM | Not commanded via remote link | 0 | 0.00 | **NOT TESTED** | Bench stationary; remote dispatch command idle |
| **TC-E-01** | Track Roll 0.5 m | No physical track run | N/A | N/A | **NOT TESTED** | No track rolling executed in current session |
| **TC-E-02** | Track Roll 1.0 m | No physical track run | N/A | N/A | **NOT TESTED** | No track rolling executed in current session |
| **TC-E-03** | Track Roll 2.0 m | No physical track run | N/A | N/A | **NOT TESTED** | No track rolling executed in current session |
| **TC-E-04** | Track Roll 3.0 m | No physical track run | N/A | N/A | **NOT TESTED** | No track rolling executed in current session |
| **TC-E-05** | Track Roll 5.0 m | No physical track run | N/A | N/A | **NOT TESTED** | No track rolling executed in current session |

---

### 4. TELEMETRY INGESTION & ODOMETRY INTEGRATION AUDIT

- **Direct Wi-Fi Streaming:** Verified. Sequence numbers incremented strictly monotonically ($1 \to 15$).
- **Odometry Ingestion Flaw:**
  - When packet 15 arrived after a brief delay, backend logged:
    `Invalid dt=110.615 for odometry update on TRUCK_01`
  - In `integration_adapters/wheel_imu_odometry.py`, the timestamp was not advanced, latching TRUCK_01's odometry into `STALE` status.
  - Fix documented in [06_BACKEND_AUDIT.md](file:///c:/Users/JAGADEESH%20M/OneDrive/Documents/SIH-2026-27/06_BACKEND_AUDIT.md).
