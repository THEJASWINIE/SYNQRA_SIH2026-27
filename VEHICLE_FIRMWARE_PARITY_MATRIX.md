# VEHICLE_FIRMWARE_PARITY_MATRIX.md
## FOG-ORCHESTRATOR 2.0 — Vehicle A vs Vehicle B Parity Matrix
**Date / Timestamp:** 2026-09-27T13:10:00+05:30  
**Evaluator:** Principal Software Architect & Lead Embedded Engineer  
**Scope:** Architectural Alignment and Parity Verification between Vehicle A (`TRUCK_01`) and Vehicle B (`TRUCK_02`)

---

### 1. SUMMARY COMPARISON MATRIX

| Function | Vehicle A (`TRUCK_01`) | Vehicle B (`TRUCK_02`) | Expected Parity Standard | Status | Notes |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Telemetry Transport** | Direct Wi-Fi + LoRa V2V | Direct Wi-Fi + LoRa V2V | Dual-link transport parity | **PARITY** | Both stream to `/api/hardware/telemetry` |
| **Telemetry JSON Schema** | `HardwareTelemetryPayload` (`vehicle_id`, `boot_id`, `sequence`, `rpm`, `speed`, IMU, `rssi`, `snr`, `source`) | `HardwareTelemetryPayload` (`vehicle_id`, `boot_id`, `sequence`, `rpm`, `speed`, IMU, `rssi`, `snr`, `source`) | Identical canonical schema | **PARITY** | Fully aligned Pydantic schema |
| **Sequence Counter** | Unified `globalSequence` | Unified `globalSequence` | Monotonic, non-competing sequence across Wi-Fi & LoRa | **PARITY** | No sequence collision on failover |
| **Session Tracking** | NVS Flash `bootId` (`Preferences.h`) | NVS Flash `bootId` (`Preferences.h`) | Persistent session index incremented on reboot | **PARITY** | Allows backend to detect intentional reboots |
| **Wi-Fi Ingestion URL** | `http://192.168.137.1:8000/api/hardware/telemetry` | `http://192.168.137.1:8000/api/hardware/telemetry` | Strict 1000 ms timeout | **PARITY** | Non-blocking to motor control loop |
| **LoRa Transceiver** | SX1278 (433.0 MHz, SF7, BW 125 kHz) | SX1278 (433.0 MHz, SF7, BW 125 kHz) | Parity RF configuration | **PARITY** | Identical SPI pins (18, 19, 23, 5, 4, 34) |
| **V2V Wire Format** | `STATE,TRUCK_01,seq,rpm,speed,ax,ay,az,gx,gy,gz` | `STATE,TRUCK_02,seq,rpm,speed,ax,ay,az,gx,gy,gz` | 11 comma-separated fields (Rule 2 frozen) | **PARITY** | Backward compatible |
| **V2V TDM Slot** | 500 ms in 2000 ms cycle | 1000 ms in 2000 ms cycle | TDM collision avoidance | **PARITY** | 500 ms staggered slotting |
| **Safe Beacon** | Emitted at 1.0 Hz on Wi-Fi loss (`BEACON,TRUCK_01,...`) | Emitted at 1.0 Hz on Wi-Fi loss (`BEACON,TRUCK_02,...`) | Emergency 433 MHz LoRa beacon on Wi-Fi drop | **PARITY** | Local safe stop latched |
| **Physical Optical Disc** | **42 slots** (`RAW_ENCODER_PPR 42.0f`) | **43 slots** (`RAW_ENCODER_PPR 43.0f`) | Raw physical optical disc slot count | **HARDWARE SPECIFIC** | Verified physical hardware differences |
| **Calibration Factor ($K_{\text{cal}}$)** | **$34.58\text{ pulses/rev}$** (`ENCODER_EFFECTIVE_PPR`) | **$34.58\text{ pulses/rev}$** (`ENCODER_EFFECTIVE_PPR`) | Same empirical calibration factor | **PARITY** | Consistent kinematic scale |
| **Wheel Diameter ($D$)** | $0.060\text{ m}$ ($6.0\text{ cm}$) | $0.060\text{ m}$ ($6.0\text{ cm}$) | Calibrated wheel diameter | **PARITY** | $C = \pi \times D = 0.188495\text{ m}$ |
| **Distance per Pulse** | $5.451\text{ mm/pulse}$ | $5.451\text{ mm/pulse}$ | $C / K_{\text{cal}}$ | **PARITY** | Linear distance scaling identical |
| **Motor Driver Hardware** | **L298N Dual H-Bridge** | **TB6612FNG Dual H-Bridge** | Driver-specific hardware wiring preserved | **HARDWARE SPECIFIC** | Preserved per architecture rules |
| **Motor Driver Pins** | `IN1`: 25, `IN2`: 26, `PWM`: 27<br>`IN3`: 32, `IN4`: 33, `PWM`: 14<br>`STBY`: 13 | `LEFT_IN1`: 25, `LEFT_IN2`: 26, `LEFT_PWM`: 27<br>`RIGHT_IN1`: 32, `RIGHT_IN2`: 33, `RIGHT_PWM`: 14<br>`MOTOR_STBY`: 13 | Pin-level mapping preserved | **HARDWARE SPECIFIC** | TB6612FNG standby pin active |
| **Motor PWM Engine** | ESP32 LEDC PWM (Core 3.x) | ESP32 LEDC PWM (Core 3.x) | Core 3.x `ledcAttach` / `ledcWrite` API | **PARITY** | 1000 Hz, 8-bit resolution |
| **IMU Sensor** | MPU6050 ($I^2C$ `0x68`) | MPU6050 ($I^2C$ `0x68`) | 3-axis accelerometer + 3-axis gyroscope | **PARITY** | SDA=21, SCL=22 |
| **Startup Safety** | Safe boot: PWM=0, `stopVehicle()` | `CONTINUOUS_FORWARD_TEST = false`, STBY=LOW, PWM=0 | Standby pulled LOW, zero motor movement on boot | **PARITY** | Zero unintended movement on boot |
| **Safety Governor** | Local Tier-1 failsafe stops vehicle on timeout | Local Tier-1 failsafe stops vehicle on timeout | Local governor remains authoritative (Rule 7) | **PARITY** | Fail-safe clamp to 0 m/s |
| **Communication Timeout** | 5000 ms remote packet timeout | 15000 ms command link timeout | Fail-safe deceleration on link loss | **PARITY** | Bounded failsafe limits |
| **Serial Test Harness** | `WIFI_DROP`, `WIFI_RECONNECT`, `REBOOT`, `DRIVE` | `WIFI_DROP`, `WIFI_RECONNECT`, `REBOOT`, `DRIVE` | Diagnostic test command parser on USB UART | **PARITY** | Enables repeatable bench tests |
| **Firmware Framework** | ESP32 Arduino Core 3.3.11 | ESP32 Arduino Core 3.3.11 | Shared toolchain and dependencies | **PARITY** | Tested with `arduino-cli` |
| **HMI Compatibility** | Direct `/api/hardware/telemetry` | Direct `/api/hardware/telemetry` | Operator & Control Room ingest live feeds | **PARITY** | TRUCK_01 and TRUCK_02 supported |

---

### 2. ARCHITECTURAL DISTINCTION: COMMON BEHAVIOR VS HARDWARE SPECIFICS

#### A. Common Behavioral Contract (Identical Across Fleet)
1. **Unified Monotonic Sequence (`globalSequence`):** Both vehicles increment the same counter regardless of whether the packet is dispatched over 433 MHz LoRa or direct 802.11 Wi-Fi.
2. **Persistent Boot Identification (`bootId`):** Both vehicles read and increment their session ID from ESP32 NVS flash (`Preferences.h` under the `synqra` namespace), ensuring backend rejection logic does not falsely flag reboots as out-of-order attacks.
3. **Emergency Safe Beacon:** When Wi-Fi connectivity drops (`wifiState == COMM_DISCONNECTED`), both vehicles trigger a 1.0 Hz half-duplex LoRa beacon and engage their Tier-1 local safety brake.
4. **Empirical Calibration Scale:** Both vehicles apply the exact same calibration factor $K_{\text{cal}} = 34.58\text{ pulses/rev}$ with $D = 0.060\text{ m}$, yielding an identical $5.451\text{ mm/pulse}$ distance resolution.

#### B. Hardware-Specific Implementations (Preserved Intentionally)
1. **Motor Driver Topologies:**
   - **Vehicle A:** L298N Dual H-Bridge. Requires direct bipolar transistor control; operates with standard drive PWM logic.
   - **Vehicle B:** TB6612FNG Dual H-Bridge. MOSFET-based driver requiring explicit control of the Standby (`MOTOR_STBY` GPIO 13) pin. Must hold STBY LOW on startup and failsafe to maintain high-impedance motor decoupling.
2. **Physical Encoder Discs:**
   - **Vehicle A:** 42-slot optical disc (`RAW_ENCODER_PPR 42.0f`).
   - **Vehicle B:** 43-slot optical disc (`RAW_ENCODER_PPR 43.0f`).
   - *Parity Note:* Neither vehicle uses raw disc slots as $K_{\text{cal}}$. Both use $K_{\text{cal}} = 34.58\text{ pulses/rev}$.
3. **V2V Transmit Time Slotting:**
   - **Vehicle A:** Transmits at $t = 500\text{ ms}$ into the 2000 ms V2V cycle.
   - **Vehicle B:** Transmits at $t = 1000\text{ ms}$ into the 2000 ms V2V cycle.
   - This ensures zero RF packet collision over the half-duplex 433 MHz channel.
