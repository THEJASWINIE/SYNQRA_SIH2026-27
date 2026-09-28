# 05_VEHICLE_B_AUDIT.md
## FOG-ORCHESTRATOR 2.0 — Vehicle B (TRUCK_02) Live Audit & Calibration Analysis
**Date / Timestamp:** 2026-09-27T09:42:30+05:30  
**Evaluator Role:** Robotics Test Engineer, Embedded Systems Engineer  
**Absolute Principle:** NO FABRICATION — Live Hardware Observation & Mathematical Consistency

---

### 1. VEHICLE B HARDWARE PROFILE

| Subsystem | Component / Specification | Hardware Verification |
| :--- | :--- | :--- |
| **Chassis / Mobile Node** | TRUCK_02 Scale Mining Dump Truck Chassis | Physical unit detected on Wi-Fi hotspot (`192.168.137.126`). |
| **Microcontroller** | ESP32-WROOM-32 (Dual Core 240 MHz) | Running `esp32_code/VEHICLE_B_TRUCK_02_V2V_DIGITAL_TWIN_MOTOR/...`. |
| **Motor Driver** | Toshiba TB6612FNG Dual H-Bridge | Left: AIN1 25, AIN2 26, PWMA 27; Right: BIN1 32, BIN2 33, PWMB 14; STBY: 13. |
| **Wheel Diameter ($D$)** | $D = 0.060\text{ m}$ ($60\text{ mm}$) | Measured calibrated physical wheel diameter. |
| **Wheel Circumference ($C$)** | $C = \pi \cdot D = 0.18849556\text{ m}$ | Calibrated linear rolling distance per revolution. |
| **Optical Encoder Slot Count** | $\text{RAW\_ENCODER\_PPR} = 43.0\text{ pulses/rev}$ | Physical optical disk slot count (Vehicle B has 43 slots vs 42 on Vehicle A). |
| **Effective Encoder Calibration** | $K = 34.58\text{ effective pulses/rev}$ | Empirical calibration constant defined in firmware. |
| **Inertial Measurement Unit** | MPU6050 6-DOF IMU (I2C `0x68`) | SDA: GPIO 21, SCL: GPIO 22. |
| **V2V Radio Transceiver** | SX1278 LoRa 433 MHz SPI Module | SCK: 18, MISO: 19, MOSI: 23, SS: 5, RST: 4, DIO0: 34. |

---

### 2. ENCODER MATHEMATICS & CALIBRATION FORENSICS

#### Asymmetry Between Vehicle A and Vehicle B:
- **Vehicle A Raw PPR:** 42.0
- **Vehicle B Raw PPR:** 43.0
- **Both use identical effective calibration:** $K = 34.58$.
- **Scale Factor Analysis:**
  - Vehicle A: $\frac{34.58}{42.0} = 0.8233$ ($17.67\%$ reduction)
  - Vehicle B: $\frac{34.58}{43.0} = 0.8042$ ($19.58\%$ reduction)
- **Standalone Speed Calibration Sketch (`esp32_code/VEHICLE_SPEED_CALIBRATION/VEHICLE B/...`):**
  - Defines raw `PPR = 43.0` and **OMITS** $K = 34.58$.
  - Standalone sketch reports speed $19.58\%$ lower than production firmware for the identical pulse frequency.
  - **Severity:** **P2 (Calibration Discrepancy)**. Standalone calibration harnesses must be aligned with production $K = 34.58$.

---

### 3. LIVE MOTOR & ENCODER TEST RESULTS

| Test Case | Commanded Speed / State | Observed Behavior | Measured Pulses | Distance (m) | Status | Evidence Source |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **TC-MB-01** | Power-On Standby | Stationary on bench | 0 | 0.00 | **PASS** | Ping active (80–94 ms), no motion observed |
| **TC-MB-02** | Forward Continuous (PWM 80) | Not mechanically loaded | 0 | 0.00 | **NOT TESTED** | Bench stationary; motor drive uncoupled |
| **TC-MB-03** | Reverse | Not commanded | 0 | 0.00 | **NOT TESTED** | Reverse test unexercised |
| **TC-MB-04** | Standby Pin High-Z Trip | STBY pulled LOW on timeout | N/A | N/A | **PASS (LOGIC)** | Verified in firmware logic: STBY low on failsafe |
| **TC-EB-01** | Track Roll 0.5 m | No physical track run | N/A | N/A | **NOT TESTED** | No track rolling executed in current session |
| **TC-EB-02** | Track Roll 1.0 m | No physical track run | N/A | N/A | **NOT TESTED** | No track rolling executed in current session |
| **TC-EB-03** | Track Roll 2.0 m | No physical track run | N/A | N/A | **NOT TESTED** | No track rolling executed in current session |
| **TC-EB-04** | Track Roll 3.0 m | No physical track run | N/A | N/A | **NOT TESTED** | No track rolling executed in current session |
| **TC-EB-05** | Track Roll 5.0 m | No physical track run | N/A | N/A | **NOT TESTED** | No track rolling executed in current session |

---

### 4. CRITICAL FIRMWARE FLAGS IDENTIFIED

1. **`CONTINUOUS_FORWARD_TEST true` Hardcoded:**
   - In `VEHICLE_B_TRUCK_02_V2V_DIGITAL_TWIN_MOTOR.ino:45`, `CONTINUOUS_FORWARD_TEST` is enabled by default with PWM 80.
   - **Risk:** If Vehicle B is powered on with wheels on the ground, it will immediately begin driving forward at PWM 80 without waiting for a backend command!
   - **Severity:** **P0 / P1 Safety Hazard**. Must be changed to `false` for safe orchestrator-controlled operations.
2. **`ENABLE_DIRECT_WIFI_TELEMETRY false`:**
   - In `VEHICLE_B_TRUCK_02_V2V_DIGITAL_TWIN_MOTOR.ino:183`, direct HTTP telemetry is disabled to avoid competing sequence numbers with the LoRa Gateway. Vehicle B relies entirely on 433 MHz LoRa V2V.
