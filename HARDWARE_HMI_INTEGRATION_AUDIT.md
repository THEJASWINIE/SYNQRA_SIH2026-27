# FOG-ORCHESTRATOR 2.0 — HARDWARE → HMI INTEGRATION AUDIT

**Date**: 2026-08-28  
**Author**: Senior Embedded Systems Engineer, IoT Integration Engineer, Backend Engineer, System Verification Engineer  
**Scope**: Physical Vehicle A (`TRUCK_01`) & Vehicle B (`TRUCK_02`) Hardware Telemetry → LoRa Gateway → HMI Backend → HMI Frontend Integration Audit

---

## 1. System Component Audit Registry

| Component | Current Status | Required Change | Risk |
|-----------|---------------|-----------------|------|
| **Vehicle A Firmware (`sketch_aug26a.ino`)** | Working 4-wheel differential drive (TB6612FNG), LM393 speed sensor (42 pulses/rev), MPU6050, Ra-02 LoRa | Update LoRa packet formatting to canonical `V=TRUCK_01,RPM=...,AX=...` protocol; preserve motor control & GPIO assignments | **LOW** |
| **Vehicle B Firmware (`vehicle_B.ino`)** | Working L298N motor control, LM393 speed sensor, MPU6050, Ra-02 LoRa | Configure unique vehicle ID `V=TRUCK_02` and standard compact LoRa packet format; preserve motor control & GPIO assignments | **LOW** |
| **LoRa Gateway Receiver (`LORA_GATEWAY_RECEIVER.ino`)** | Hardware Ra-02 receiver module on Gateway ESP32 | Implement continuous LoRa listener forwarding valid telemetry lines over USB Serial at 115200 baud | **LOW** |
| **HMI Backend (`SYNQRA_SIH2026-27-HMI/backend`)** | FastAPI app with REST & WebSocket telemetry endpoints | Add USB Serial Gateway Reader (`gateway_serial_reader.py`) with telemetry parser, validator, state normalizer, and communication health tracker (`ONLINE`, `STALE`, `OFFLINE`) | **MEDIUM** |
| **HMI Frontend (`SYNQRA_SIH2026-27-HMI/frontend`)** | React TypeScript supervisory dashboard | Extend vehicle state store to visualize live hardware telemetry for `TRUCK_01` and `TRUCK_02` alongside communication health indicators | **LOW** |
| **Mock Mode Infrastructure (`mock_vehicle_generator.py`)** | Standalone mock telemetry generator | Preserve full mock mode capability (`MODE=MOCK` vs `MODE=HARDWARE`) without regression | **LOW** |
| **Digital Twin (`SYNQRA_SIH2026-27-main`, `fog_orchestrator`, `fog_safe`)** | Independent physics & simulation engines | **100% UNTOUCHED** (Zero imports, zero code changes, zero runtime dependencies) | **NONE** |

---

## 2. Pinout & GPIO Preservation Verification

### Vehicle A (`TRUCK_01` — ESP32 Dev Module + TB6612FNG)
- **Left Motors**: `LEFT_IN1 = 25`, `LEFT_IN2 = 26`, `LEFT_PWM = 27`
- **Right Motors**: `RIGHT_IN1 = 32`, `RIGHT_IN2 = 33`, `RIGHT_PWM = 14`
- **Motor Standby**: `MOTOR_STBY = 13`
- **Speed Sensor**: `SPEED_SENSOR_PIN = 35` (Interrupt driven, `PULSES_PER_REV = 42.0`)
- **IMU MPU6050**: I2C `SDA = 21`, `SCL = 22` (`0x68`)
- **LoRa Ra-02**: SPI `SCK = 18`, `MISO = 19`, `MOSI = 23`, `SS = 5`, `RST = 4`, `DIO0 = 34`
- **GPIO Changes Made**: **NONE**

### Vehicle B (`TRUCK_02` — ESP32 + L298N)
- **Motor Pins**: Preserved existing L298N control configuration
- **Speed Sensor**: Preserved existing LM393 input pin
- **IMU MPU6050**: I2C `SDA = 21`, `SCL = 22` (`0x68`)
- **LoRa Ra-02**: SPI `SCK = 18`, `MISO = 19`, `MOSI = 23`, `SS = 5`, `RST = 4`, `DIO0 = 34`
- **GPIO Changes Made**: **NONE**

---

## 3. Communication Health & Timeout Policy

- **`ONLINE`**: Telemetry packet received within `< 3.0` seconds.
- **`STALE`**: No packet received for `3.0s` to `10.0s`. Visualized in HMI as communication degraded.
- **`OFFLINE`**: No packet received for `> 10.0` seconds. Safety fallback activated.

---

## 4. Audit Conclusion

All hardware motor control logic, sensor calibration constants (`PULSES_PER_REV = 42.0`), and pinouts are preserved without modification. The integration path is clean and fully isolated from the Digital Twin.
