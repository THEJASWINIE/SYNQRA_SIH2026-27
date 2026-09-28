# VEHICLE_B_UPDATE_REPORT.md
## FOG-ORCHESTRATOR 2.0 — Vehicle B Production Firmware Update Report
**Date / Timestamp:** 2026-09-27T13:11:00+05:30  
**Evaluator:** Principal Software Architect & Lead Embedded Engineer  
**Target Unit:** Vehicle B (`TRUCK_02`)  
**Firmware Path:** [`esp32_code/VEHICLE_B_TRUCK_02_V2V_DIGITAL_TWIN_MOTOR/VEHICLE_B_TRUCK_02_V2V_DIGITAL_TWIN_MOTOR.ino`](file:///c:/Users/JAGADEESH%20M/OneDrive/Documents/SIH-2026-27/esp32_code/VEHICLE_B_TRUCK_02_V2V_DIGITAL_TWIN_MOTOR/VEHICLE_B_TRUCK_02_V2V_DIGITAL_TWIN_MOTOR.ino)  
**Status:** COMPLETED & BENCH-VERIFIED (PHYSICAL FLOOR VALIDATION DEFERRED)

---

### 1. SUMMARY OF UPDATES
Vehicle B (`TRUCK_02`) production firmware has been brought into full architectural parity with the reference model established by Vehicle A (`TRUCK_01`), strictly adhering to the project rules:
1. **Driver Integrity Preserved:** TB6612FNG dual H-bridge motor driver wiring and ESP32 Arduino Core 3.x LEDC PWM architecture were preserved; no conversion to L298N occurred.
2. **Empirical Calibration Preserved:** Physical slotted optical disc identified as 43 slots (`RAW_ENCODER_PPR 43.0f`), with the empirical calibration factor explicitly maintained as $K_{\text{cal}} = 34.58\text{ pulses/rev}$ (`ENCODER_EFFECTIVE_PPR 34.58f`).
3. **Session & Sequence Unification:** NVS persistent `bootId` tracking implemented via `Preferences.h` (`synqra` namespace). Monotonic `globalSequence` unified across 433 MHz LoRa and 802.11 direct Wi-Fi transmissions.
4. **Production Safe Beacon:** Integrated 1.0 Hz emergency LoRa broadcast (`sendSafeBeacon()`) emitting `BEACON,TRUCK_02,<seq>,DEGRADED,<millis>,PIT_ZONE_A` upon primary Wi-Fi link disconnection, accompanied by immediate local safe deceleration and TB6612FNG standby decoupling (`MOTOR_STBY = LOW`).
5. **Direct Wi-Fi Telemetry Activated:** Direct Wi-Fi streaming enabled (`ENABLE_DIRECT_WIFI_TELEMETRY true`) targeting `/api/hardware/telemetry` with full JSON schema alignment including `boot_id`, `sequence`, `rpm`, `speed`, IMU readings, RSSI, SNR, and source tags.
6. **Serial Diagnostic Test Harness:** Integrated serial commands (`WIFI_DROP`, `WIFI_RECONNECT`, `REBOOT`, `DRIVE`) to enable reproducible bench testing without manual code rewrites.

---

### 2. HARDWARE WIRING & PIN DEFINITIONS

| Subsystem | Pin Name | GPIO Number | Function / Electrical Standard |
| :--- | :--- | :--- | :--- |
| **TB6612FNG** | `LEFT_IN1` | GPIO 25 | Direction control Left A |
| **TB6612FNG** | `LEFT_IN2` | GPIO 26 | Direction control Left B |
| **TB6612FNG** | `LEFT_PWM` | GPIO 27 | Speed PWM Left (Core 3.x `ledcAttach`) |
| **TB6612FNG** | `RIGHT_IN1` | GPIO 32 | Direction control Right A |
| **TB6612FNG** | `RIGHT_IN2` | GPIO 33 | Direction control Right B |
| **TB6612FNG** | `RIGHT_PWM` | GPIO 14 | Speed PWM Right (Core 3.x `ledcAttach`) |
| **TB6612FNG** | `MOTOR_STBY` | GPIO 13 | Standby enable (Active HIGH, LOW = Safe Stop) |
| **Encoder** | `SPEED_SENSOR_PIN` | GPIO 35 | Optocoupler pulse interrupt (`RISING`) |
| **MPU6050** | `MPU_SDA` | GPIO 21 | $I^2C$ Data |
| **MPU6050** | `MPU_SCL` | GPIO 22 | $I^2C$ Clock |
| **LoRa SX1278** | `LORA_SCK` | GPIO 18 | SPI Clock |
| **LoRa SX1278** | `LORA_MISO` | GPIO 19 | SPI Master In Slave Out |
| **LoRa SX1278** | `LORA_MOSI` | GPIO 23 | SPI Master Out Slave In |
| **LoRa SX1278** | `LORA_SS` | GPIO 5 | SPI Slave Select |
| **LoRa SX1278** | `LORA_RST` | GPIO 4 | Hardware Reset |
| **LoRa SX1278** | `LORA_DIO0` | GPIO 34 | Packet Rx/Tx Interrupt |

---

### 3. KINEMATIC & CALIBRATION SPECIFICATIONS

- **Wheel Diameter ($D$):** $0.060\text{ m}$ ($6.0\text{ cm}$)
- **Wheel Circumference ($C$):** $C = \pi \times D = 3.14159265 \times 0.060 = 0.188495\text{ m}$
- **Raw Physical Optical Disc:** **43 slots** (`#define RAW_ENCODER_PPR 43.0f`)
- **Empirical Calibration Factor ($K_{\text{cal}}$):** **$34.58\text{ pulses/rev}$** (`#define ENCODER_EFFECTIVE_PPR 34.58f`)
- **Distance Resolution ($d_{\text{pulse}}$):** $d_{\text{pulse}} = C / K_{\text{cal}} = 0.188495 / 34.58 = 5.451\text{ mm/pulse}$
- **Speed Derivation Formula:**
  $$\text{RPS} = \frac{\Delta\text{pulses}}{K_{\text{cal}} \times \Delta t}$$
  $$\text{RPM} = \text{RPS} \times 60.0$$
  $$\text{Speed (m/s)} = \text{RPS} \times C$$

---

### 4. STARTUP SAFETY AUDIT (BENCH-VERIFIED)

- **Configuration:** `#define CONTINUOUS_FORWARD_TEST false`
- **Boot State Sequence:**
  1. GPIO 13 (`MOTOR_STBY`) initialized as `OUTPUT` and immediately written `LOW`.
  2. All direction pins (`LEFT_IN1`, `LEFT_IN2`, `RIGHT_IN1`, `RIGHT_IN2`) initialized as `OUTPUT` and written `LOW`.
  3. LEDC PWM initialized with frequency 1000 Hz, 8-bit resolution.
  4. `stopVehicle()` explicitly executed, ensuring PWM = 0 and `MOTOR_STBY = LOW`.
  5. `commandedSpeedMs = 0.0f; targetMotorPWM = 0; appliedMotorPWM = 0; appliedSpeedMs = 0.0f;`
- **Bench Observation:** Motor remains in high-impedance freewheel / braked state upon boot. Zero pulse generation or wheel rotation detected prior to explicit command reception.

---

### 5. BENCH VERIFICATION & COMPILATION STATUS

- **Toolchain:** `arduino-cli` with `esp32:esp32:esp32` (Core 3.3.11)
- **Status:** **PASS** (Zero compiler errors, zero warnings)
- **Storage Metrics:**
  - Flash Memory: 978,655 bytes (74% of 1,310,720 bytes)
  - RAM (Global): 49,404 bytes (15% of 327,680 bytes)
- **Floor Motion Gate:** **DEFERRED** (Physical floor distance measurement and final adversarial E2E validation deferred to final physical gate).
