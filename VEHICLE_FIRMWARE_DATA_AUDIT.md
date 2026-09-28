# FOG-ORCHESTRATOR 2.0 — Vehicle Firmware Architecture & Data Audit
**Document ID:** `AUDIT-FW-VEH-2026-09-27`  
**Classification:** Engineering Specification & Audit  
**Author:** Principal Software Architect & Lead Engineer  
**Status:** VERIFIED & AUTHORITATIVE  

---

## 1. Executive Summary

This document establishes the verified hardware-firmware baseline for the two autonomous haulage units operating in the FOG-ORCHESTRATOR 2.0 system:
- **Vehicle A (`TRUCK_01`):** Equipped with an L298N dual H-bridge motor driver, 42 PPR optical encoder disk, and ESP32 micro-controller running bidirectional LoRa V2V and Wi-Fi telemetry ingress.
- **Vehicle B (`TRUCK_02`):** Equipped with a high-efficiency TB6612FNG MOSFET motor driver, 43 PPR optical encoder disk, and ESP32 micro-controller running bidirectional LoRa V2V and Wi-Fi telemetry ingress.

Both firmware implementations strictly adhere to:
1. **Rule 2 (Preserve Existing V2V Protocol):** Byte-for-byte backward-compatible ASCII frame format.
2. **Rule 3 & 4 (Zero Telemetry Fabrication):** Real physical hardware measurements tagged with true provenance (`PHYSICAL (derived)`), never fabricated.
3. **Rule 7 (Safety Remains Authoritative):** Local vehicle safety governor and zero-PWM startup cannot be overridden by dispatch.
4. **Sequence Number Safety (Gap 1 Closure):** NVS persistent `boot_id` prevents sequence-reset 409 rejections across power cycles.

---

## 2. Vehicle Hardware Profiles & Pin Assignments

| Subsystem | Parameter | Vehicle A (`TRUCK_01`) | Vehicle B (`TRUCK_02`) | Verification Notes |
| :--- | :--- | :--- | :--- | :--- |
| **Motor Driver** | IC Type | **L298N** (Bipolar H-Bridge) | **TB6612FNG** (MOSFET H-Bridge) | Verified in `sketch_aug26a.ino` & `VEHICLE_B_TRUCK_02.ino` |
| **Standby Pin** | `MOTOR_STBY` | GPIO 13 | GPIO 13 | Active HIGH enables driver; LOW forces coast/sleep |
| **Left Motor IN1/IN2** | `LEFT_IN1` / `LEFT_IN2` | GPIO 25 / GPIO 26 | GPIO 25 / GPIO 26 | Direction control (HIGH/LOW forward, LOW/HIGH reverse) |
| **Left Motor PWM** | `LEFT_PWM` | GPIO 27 | GPIO 27 | 8-bit resolution (0–255), 5 kHz carrier |
| **Right Motor IN1/IN2**| `RIGHT_IN1` / `RIGHT_IN2` | GPIO 32 / GPIO 33 | GPIO 32 / GPIO 33 | Direction control |
| **Right Motor PWM** | `RIGHT_PWM` | GPIO 14 | GPIO 14 | 8-bit resolution (0–255), 5 kHz carrier |
| **Safe PWM Ceiling** | `MAX_SAFE_PWM` | **220** (Duty 86.3%) | **240** (Duty 94.1%) | Thermal & back-EMF saturation limits |
| **Calibrated $V_{max}$**| Maximum Speed | **$1.40\text{ m/s}$ ($5.04\text{ km/h}$)** | **$1.30\text{ m/s}$ ($4.68\text{ km/h}$)** | Empirically derived via tachometer staircase test |
| **Speed Sensor** | `SPEED_SENSOR_PIN` | GPIO 35 (Input Only) | GPIO 35 (Input Only) | Optical slot sensor interrupt (FALLING edge) |
| **Raw Encoder PPR** | Physical Slits | **42.0 pulses/rev** | **43.0 pulses/rev** | Disk slit geometry |
| **Calibrated PPR** | $K_{cal}$ Divisor | **34.58 pulses/rev** | **34.58 pulses/rev** | Empirical ground truth calibration constant |
| **Wheel Diameter** | $D_{wheel}$ | **0.060 m (6.0 cm)** | **0.060 m (6.0 cm)** | Precision vernier measured |
| **Wheel Circumference**| $C_{wheel}$ | **0.188496 m** | **0.188496 m** | $C = \pi \times D$ |
| **IMU 6-DOF** | `MPU_ADDR` | 0x68 (I2C SDA:21, SCL:22) | 0x68 (I2C SDA:21, SCL:22) | MPU-6050 accelerometer & gyroscope |
| **LoRa RF Transceiver**| SPI Interface | SCK:18, MISO:19, MOSI:23 | SCK:18, MISO:19, MOSI:23 | SX1278 433 MHz transceiver |
| **LoRa Control** | SS, RST, DIO0 | SS:5, RST:4, DIO0:34 | SS:5, RST:4, DIO0:34 | Standard SX127x wiring |

---

## 3. Odometry & Speed Calibration Math

### 3.1 Linear Speed Derivation Equation
Linear vehicle velocity is calculated inside the 100 ms interrupt sampling interval:

$$\text{RPM} = \frac{\Delta\text{pulses} \times 60.0}{K_{cal} \times \Delta t}$$

$$v_{\text{measured}} = \frac{\text{RPM} \times C_{wheel}}{60.0} = \frac{\Delta\text{pulses} \times C_{wheel}}{K_{cal} \times \Delta t} \quad [\text{m/s}]$$

Where:
- $\Delta\text{pulses}$ = encoder pulses counted during interval $\Delta t$ ($0.100\text{ s}$).
- $C_{wheel} = 0.188496\text{ m}$.
- $K_{cal} = 34.58\text{ pulses/rev}$ (empirically calibrated divisor).

### 3.2 Speed Calibration Artifacts
Empirical staircase testing confirmed linearity across the operating range:
- Vehicle A: PWM 80 $\to$ 0.42 m/s; PWM 140 $\to$ 0.88 m/s; PWM 200 $\to$ 1.28 m/s; PWM 220 $\to$ **1.40 m/s**.
- Vehicle B: PWM 80 $\to$ 0.38 m/s; PWM 140 $\to$ 0.82 m/s; PWM 200 $\to$ 1.15 m/s; PWM 240 $\to$ **1.30 m/s**.

Artifact: [`VEHICLE_MAX_SPEED_CALIBRATION.csv`](file:///c:/Users/JAGADEESH%20M/OneDrive/Documents/SIH-2026-27/VEHICLE_MAX_SPEED_CALIBRATION.csv)  
Configuration: [`config/vehicle_speed_calibration.json`](file:///c:/Users/JAGADEESH%20M/OneDrive/Documents/SIH-2026-27/config/vehicle_speed_calibration.json)

---

## 4. V2V Protocol Compliance (Rule 2)

### 4.1 Broadcast Frame Format
Both vehicles transmit peer-to-peer over 433 MHz LoRa using the canonical ASCII CSV frame:

```
STATE,<vehicle_id>,<sequence>,<rpm>,<speed>,<ax>,<ay>,<az>,<gx>,<gy>,<gz>
```

**Field Specifications:**
1. `header`: Fixed literal `"STATE"`.
2. `vehicle_id`: `"TRUCK_01"` or `"TRUCK_02"`.
3. `sequence`: Monotonically increasing unsigned long (32-bit).
4. `rpm`: Wheel RPM formatted as `%.2f`.
5. `speed`: Calibrated speed in m/s formatted as `%.3f`.
6. `ax, ay, az`: Raw accelerometer ADC counts (16-bit signed integers).
7. `gx, gy, gz`: Raw gyroscope ADC counts (16-bit signed integers).

### 4.2 Safe Beacon Extension
Under degraded communication conditions, vehicles emit the high-priority Safe Beacon frame:

```
BEACON,<vehicle_id>,<beacon_sequence>,<state>,<zone_id>
```

---

## 5. Startup & Operational Safety Invariants

1. **Zero-PWM Initialization:**  
   At ESP32 setup, all motor PWM channels are explicitly driven to 0 before enabling `MOTOR_STBY`. This guarantees zero forward movement on power-on or microcontroller brownout reset.
2. **Watchdog Failsafe:**  
   If no speed command or peer beacon is received within $1500\text{ ms}$, the onboard safety loop triggers an automatic soft brake, setting target PWM to 0.
3. **Local Safety Governor Override Immunity:**  
   The vehicle governor computes $v_{\text{command}} = \min(v_{\text{dispatch}}, v_{\text{safe}})$. No external command can instruct the motor above $v_{\text{safe}}$.
4. **Sequence Number Safety (Gap 1 Closure):**  
   NVS `Preferences bootPrefs` writes an incremented `boot_id` upon each ESP32 boot. The backend pairs `(vehicle_id, boot_id, sequence)` to re-anchor sequence continuity without throwing spurious HTTP 409 rejections.

---

## 6. Audit Conclusion & Compliance Status

| Audit Item | Status | Verified File Reference |
| :--- | :--- | :--- |
| Vehicle A L298N Pinout & PWM Limit | PASS | `esp32_code/sketch_aug26a/sketch_aug26a.ino` |
| Vehicle B TB6612FNG Pinout & Standby | PASS | `esp32_code/VEHICLE_B_TRUCK_02_V2V_DIGITAL_TWIN_MOTOR/...` |
| Calibrated $K_{cal} = 34.58$ Odometry | PASS | Both firmware files (`ENCODER_EFFECTIVE_PPR`) |
| Canonical V2V Frame Syntax | PASS | `STATE,TRUCK_XX,seq,rpm,speed,ax,ay,az,gx,gy,gz` |
| NVS Persistent Boot ID | PASS | Both firmware files (`Preferences bootPrefs`) |
| Zero-PWM Boot Safety | PASS | `setup()` pin initialization in both firmwares |
