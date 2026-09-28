# VEHICLE_A_REFERENCE.md
## FOG-ORCHESTRATOR 2.0 — Vehicle A Baseline & Architecture Reference Contract
**Target Vehicle:** `TRUCK_01` (Vehicle A)  
**Firmware File:** [`esp32_code/sketch_aug26a/sketch_aug26a.ino`](file:///c:/Users/JAGADEESH%20M/OneDrive/Documents/SIH-2026-27/esp32_code/sketch_aug26a/sketch_aug26a.ino)  
**Date / Timestamp:** 2026-09-27T13:02:00+05:30  
**Status:** REFERENCE ARCHITECTURE (FROZEN — DO NOT UNNECESSARILY MODIFY)  

---

### 1. SPECIFICATION SUMMARY TABLE

| Parameter | Specification / Value | Engineering Context |
| :--- | :--- | :--- |
| **Vehicle ID** | `TRUCK_01` | Canonical vehicle identifier |
| **Remote Peer ID** | `TRUCK_02` | Direct peer-to-peer V2V remote vehicle |
| **Microcontroller** | ESP32-WROOM-32 (CH9102 / CP2102) | USB Port `COM14`, dual-core 240 MHz, 4MB Flash |
| **Firmware Framework** | ESP32 Arduino Core 3.3.11 | C++ / Arduino |
| **Motor Driver** | **L298N Dual H-Bridge** | **DO NOT COPY TO VEHICLE B (Vehicle B is TB6612FNG)** |
| **Motor Driver Pins** | `LEFT_IN1` (25), `LEFT_IN2` (26), `LEFT_PWM` (27)<br>`RIGHT_IN1` (32), `RIGHT_IN2` (33), `RIGHT_PWM` (14)<br>`MOTOR_STBY` (13) | Standard direction + PWM analog pins |
| **Motor Limits** | `MAX_MOTOR_PWM = 220`, `MIN_MOTOR_PWM = 0` | Mapped to `MAX_PROTOTYPE_SPEED_MS = 1.40f` |
| **Speed Sensor Pin** | GPIO 35 (`SPEED_SENSOR_PIN`) | Input with external pull-up on chassis |
| **Encoder Interrupt** | `RISING` edge (`attachInterrupt`) | Single interrupt per slot transition |
| **Physical Optical Disc** | **42 slots** (`RAW_ENCODER_PPR 42.0f`) | Physical hardware observation |
| **Empirical Calibration** | **$K_{\text{cal}} = 34.58\text{ pulses/rev}$** | `ENCODER_EFFECTIVE_PPR 34.58f` |
| **Wheel Diameter** | $D = 0.060\text{ m}$ ($6.0\text{ cm}$) | Circumference $C = 0.188495\text{ m}$ |
| **Distance per Pulse** | $d_{\text{pulse}} = 5.451\text{ mm/pulse}$ | $C / K_{\text{cal}}$ |
| **Wi-Fi Transport** | 802.11 b/g/n Station Mode | Hotspot credentials loaded from `secrets.h` |
| **Wi-Fi Ingestion URL** | `http://192.168.137.1:8000/api/hardware/telemetry` | Strict bounded 1000 ms HTTP timeout |
| **Wi-Fi Interval** | 2000 ms (`HMI_INTERVAL`) | Non-blocking millis() schedule |
| **Session Tracking** | Persistent NVS `bootId` (`Preferences.h`) | Incremented once per boot cycle in flash |
| **Sequence Counter** | Unified `globalSequence` | Shared strictly monotonic counter for LoRa & Wi-Fi |
| **LoRa Transceiver** | Semtech SX1278 (SPI) | 433.0 MHz, SF7, BW 125 kHz, CR 4/5, CRC ON |
| **LoRa Pins** | SCK (18), MISO (19), MOSI (23), SS (5), RST (4), DIO0 (34) | Standard SPI bus configuration |
| **V2V TDM Slot** | `V2V_START_DELAY = 500 ms` | Transmits at 500 ms into 2000 ms V2V cycle |
| **V2V Wire Format** | `STATE,TRUCK_01,seq,rpm,speed,ax,ay,az,gx,gy,gz` | 11 comma-separated fields (Rule 2 frozen) |
| **Safe Beacon Wire Format**| `BEACON,TRUCK_01,seq,DEGRADED,millis,PIT_ZONE_A` | 6 fields emitted at 1.0 Hz when Wi-Fi drops |
| **Startup Safety** | `targetMotorPWM = 0; stopVehicle();` | Standby LOW on boot, zero forward drive |

---

### 2. CANONICAL WI-FI TELEMETRY JSON SCHEMA
```json
{
  "vehicle_id": "TRUCK_01",
  "boot_id": 2,
  "sequence": 104,
  "rpm": 45.20,
  "speed": 0.42,
  "accel_x": 3268,
  "accel_y": 5808,
  "accel_z": 15528,
  "gyro_x": 646,
  "gyro_y": 341,
  "gyro_z": 210,
  "rssi": -42,
  "snr": 9.75,
  "source": "DIRECT_WIFI"
}
```

---

### 3. MANDATORY PARITY CONTRACT FOR VEHICLE B
Vehicle B must achieve exact architectural parity with this reference implementation by adopting:
1. **NVS Persistent `boot_id`** via `Preferences.h` (`synqra` namespace).
2. **Unified monotonic `globalSequence`** across LoRa and Wi-Fi.
3. **Identical JSON telemetry structure** when posting to `/api/hardware/telemetry` (with `vehicle_id: "TRUCK_02"`).
4. **Production Safe Beacon generator (`sendSafeBeacon()`)** when Wi-Fi is lost (`BEACON,TRUCK_02,<seq>,DEGRADED,<millis>,PIT_ZONE_A`).
5. **Exact Calibration Factor:** $K_{\text{cal}} = 34.58\text{ pulses/rev}$ (with its physical 43-slot disc clearly designated as `RAW_ENCODER_PPR 43.0f`).
6. **TB6612FNG Driver Integrity:** Must preserve its own TB6612FNG driver logic and LEDC PWM core API.
