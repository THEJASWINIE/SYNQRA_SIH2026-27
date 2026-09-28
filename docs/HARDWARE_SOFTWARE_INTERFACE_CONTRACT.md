# 02 — HARDWARE-SOFTWARE INTERFACE CONTRACT
## FOG-ORCHESTRATOR 2.0 | SIH 2026-27 (Problem Statement: SIH26007)
### NMDC Bailadila Deposit-5 Low-Visibility HEMM Safety System
**Phase 9: Hardware + Software Integration**
**Status:** AUTHORITATIVE & FROZEN

---

## 1. PURPOSE & ARCHITECTURAL SCOPE

This interface specification defines the immutable data contract between physical microcontrollers, sensors, vehicle networks, RF communication links, the central FOG-ORCHESTRATOR backend, and the onboard Local Vehicle Safety Governor.

Every interface defines:
1. **INPUT / OUTPUT**
2. **PROTOCOL & MESSAGE FORMAT**
3. **UPDATE RATE & TIMEOUT**
4. **TIMESTAMP & UNIT**
5. **VALID RANGE & FAILURE VALUE**
6. **SUBSYSTEM OWNER & SAFETY CONSEQUENCE**

---

## 2. INTERFACE MATRIX SUMMARY

| ID | Interface Name | Protocol | Physical Medium | Direction | Update Rate | Timeout |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **IF-01** | HEMM Raw Telemetry | Custom CSV / V2V | 433 MHz LoRa / UART | ESP32 $\to$ Gateway | 10 Hz (100 ms) | 500 ms |
| **IF-02** | Gateway Telemetry Uplink | HTTP POST JSON | Wi-Fi 802.11 b/g/n | Gateway $\to$ Backend | 10 Hz (100 ms) | 1000 ms |
| **IF-03** | Environmental Visibility | Modbus RTU / JSON | RS485 / Ethernet | Weather Station $\to$ Backend | 1 Hz (1000 ms) | 3000 ms |
| **IF-04** | Vehicle Wheel Speed | Pulse / CAN J1939 | Hall Effect / TWAI | Sensor $\to$ Local ECU | 20 Hz (50 ms) | 200 ms |
| **IF-05** | Haul Road Grade | DEM / Inclinometer | CAN J1939 / Memory | GIS / Sensor $\to$ Twin | 1 Hz (1000 ms) | 2000 ms |
| **IF-06** | Service & Retarder Brake | J1939 EBC1/ERC1 | CAN 250 kbps TWAI | Brake ECU $\leftrightarrow$ Local Gov | 20 Hz (50 ms) | 150 ms |
| **IF-07** | Speed Command Dispatch | J1939 Prop-B / JSON | Central Wi-Fi / CAN | Backend $\to$ Local Gov | 10 Hz (100 ms) | 500 ms |
| **IF-08** | GNSS / Local Positioning | NMEA 0183 / JSON | UART / Ethernet | GNSS Receiver $\to$ Twin | 5 Hz (200 ms) | 1000 ms |
| **IF-09** | RF Link Metrics | LoRa Packet Metadata | SX1278 Internal Reg | LoRa PHY $\to$ Gateway | 10 Hz (100 ms) | 500 ms |
| **IF-10** | DSSS / Gateway State | Internal Adapter | Software Pipe | Selector $\to$ Orchestrator | 10 Hz (100 ms) | 300 ms |
| **IF-11** | Sensor Health & Quality | Internal Typed Record| Software Pipe | Health Filter $\to$ Gov | 10 Hz (100 ms) | 200 ms |
| **IF-12** | Local Safety Governor State| CAN J1939 / WebSocket| CAN / TCP | Local Gov $\to$ HMI / Twin | 10 Hz (100 ms) | 500 ms |
| **IF-13** | Safe Beacon Broadcast | Custom ASCII Broadcast| 433 MHz LoRa PHY | Vehicle $\to$ Broadcast | 2 Hz – 5 Hz | 1000 ms |

---

## 3. DETAILED INTERFACE CONTRACTS

### IF-01: HEMM Raw Telemetry (Over-the-Air V2V / Gateway)
- **Input:** Onboard MPU6050 accelerometer, gyro, optical wheel tachometer.
- **Output:** ASCII string transmitted over 433 MHz LoRa.
- **Protocol:** Custom ASCII comma-separated payload.
- **Message Format:**
  `STATE,<vehicle_id>,<seq>,<rpm>,<speed>,<ax>,<ay>,<az>,<gx>,<gy>,<gz>[,RSSI=<val>,SNR=<val>]`
- **Update Rate:** 10 Hz (100 ms nominal interval).
- **Timestamp:** Monotonic millisecond counter (`millis()`) in firmware; synchronized UTC epoch in gateway.
- **Units:**
  - `rpm`: Revolutions per minute (RPM)
  - `speed`: Metres per second (m/s)
  - `ax, ay, az`: Metres per second squared (m/s²)
  - `gx, gy, gz`: Degrees per second (°/s) or radians per second (rad/s)
- **Valid Range:**
  - `seq`: 0 to 4,294,967,295 (rolls over)
  - `rpm`: 0.0 to 2500.0 RPM
  - `speed`: 0.0 to 15.0 m/s (0.0 to 54.0 km/h)
  - `ax, ay`: -15.0 to +15.0 m/s²
  - `az`: -5.0 to +25.0 m/s² (1g vertical baseline nominal ~9.81 m/s²)
  - `gx, gy, gz`: -250.0 to +250.0 deg/s
- **Failure Value:** `NaN`, `INF`, or out-of-bounds sentinel.
- **Timeout:** 500 ms (5 dropped consecutive frames).
- **Owner:** Vehicle Telemetry Firmware (`TRUCK_01_TRANSMITTER.ino`).
- **Safety Consequence:** Packet drop triggers RF communication warning; persistent timeout triggers transition to `DEGRADED_COMMUNICATION` and activates Safe Beacon.

---

### IF-02: Gateway Telemetry Uplink (`POST /api/hardware/telemetry`)
- **Input:** Demodulated RF packet from SX1278 on ESP32 Gateway.
- **Output:** JSON HTTP request sent to Orchestrator Backend.
- **Protocol:** HTTP/1.1 POST with JSON payload.
- **Message Format:**
  ```json
  {
    "vehicle_id": "TRUCK_01",
    "sequence": 1045,
    "rpm": 1820.0,
    "speed": 5.42,
    "ax": -0.15,
    "ay": 0.02,
    "az": 9.81,
    "gx": 0.01,
    "gy": -0.01,
    "gz": 0.00,
    "rssi": -72.0,
    "snr": 7.5,
    "gateway_id": "GW_RAMP_01",
    "timestamp": 1727134000.125
  }
  ```
- **Update Rate:** 10 Hz (100 ms).
- **Timestamp:** Microsecond-precision epoch timestamp (seconds float).
- **Units:** SI units (m/s, m/s², RPM, dBm, dB).
- **Valid Range:** Matching IF-01; RSSI: -120 to -30 dBm; SNR: -20 to +15 dB.
- **Failure Value:** HTTP 422 Unprocessable Entity on validation failure; HTTP 500 on ingest crash.
- **Timeout:** 1000 ms.
- **Owner:** Gateway Receiver Firmware (`LORA_GATEWAY_RECEIVER.ino`) & Ingest Service (`telemetry_ingest.py`).
- **Safety Consequence:** Ingestion failure isolates central orchestrator from physical vehicle; local governor retains local control.

---

### IF-03: Environmental Visibility Interface
- **Input:** Optical scatter transmissometer / weather station sensor.
- **Output:** Meteorological Optical Range (MOR) visibility.
- **Protocol:** Modbus RTU / JSON over HTTP.
- **Message Format:**
  `{"sensor_id": "VIS_RAMP_02", "visibility_m": 12.5, "quality": "VALID", "timestamp": 1727134000.0}`
- **Update Rate:** 1 Hz (1000 ms).
- **Timestamp:** UTC ISO 8601 / Unix epoch seconds.
- **Units:** Metres (m).
- **Valid Range:** 0.0 to 1000.0 m.
- **Failure Value:** Negative value or `None`.
- **Timeout:** 3000 ms (3 missing cycles).
- **Owner:** Weather Station / Environmental Ingestion Module (`environmental_data_health.py`).
- **Safety Consequence:** Sensor failure triggers worst-case blindout conservative fallback ($R_{\text{vis}} = 5.0\text{ m} \implies v_{\text{safe}} = 0.0\text{ m/s}$ halt).

---

### IF-04: Vehicle Wheel Speed Interface
- **Input:** Dual variable-reluctance / Hall-effect wheel sensors.
- **Output:** Validated longitudinal vehicle speed.
- **Protocol:** CAN 2.0B / J1939 (PGN 65265, SPN 84).
- **Message Format:** 8-byte CAN frame, resolution 1/256 km/h per bit.
- **Update Rate:** 20 Hz (50 ms).
- **Timestamp:** CAN TX/RX epoch timestamps ($\mu s$).
- **Units:** Metres per second (m/s).
- **Valid Range:** 0.0 to 15.0 m/s (0.0 to 54.0 km/h).
- **Failure Value:** `0xFFFE` (Error), `0xFFFF` (Not Available).
- **Timeout:** 200 ms (4 missing frames).
- **Owner:** Onboard Brake / Transmission ECU & CAN Adapter (`can_twai_hil.py`).
- **Safety Consequence:** Speed loss prevents closed-loop headway governing; forces vehicle crawl to standstill.

---

### IF-05: Haul Road Grade Interface
- **Input:** Road centerline digital terrain model (DTM) + dual-axis chassis inclinometer.
- **Output:** Longitudinal road inclination percentage ($\%$).
- **Protocol:** Pre-mapped spatial profile query + J1939 Pitch Angle (PGN 61445).
- **Message Format:** Float grade percentage.
- **Update Rate:** 1 Hz (1000 ms) or spatial position lookup.
- **Timestamp:** UTC epoch seconds.
- **Units:** Percent grade ($\% = \tan(\theta) \times 100$).
  > **GRADE CONVENTION:** Bijective convention: Downhill ramp = negative grade (e.g. $-8.0\%$). Uphill climb = positive grade ($+8.0\%$).
- **Valid Range:** -15.0% to +15.0%.
- **Failure Value:** `NaN`.
- **Timeout:** 2000 ms.
- **Owner:** Grade Adapter (`grade_adapter.py`) & Digital Twin.
- **Safety Consequence:** Erroneous grade calculation biases retarder calculation; conservative fallback applies $-8\%$ worst-case downhill assumption.

---

### IF-06: Service & Retarder Brake Interface
- **Input:** Local safety governor torque / deceleration request.
- **Output:** Hydraulic brake pressure & retarder hydraulic valve actuation.
- **Protocol:** CAN J1939 PGN 61441 (EBC1) and PGN 61440 (ERC1).
- **Message Format:**
  - EBC1: Byte 1 Brake demand [0–100%], Byte 2 Brake status bitmap.
  - ERC1: Byte 1 Retarder torque demand [0–100%].
- **Update Rate:** 20 Hz (50 ms).
- **Timestamp:** Controller execution timestamp ($\mu s$).
- **Units:** Percentage demand ($0.0–100.0\%$), Pressure ($0–150\text{ bar}$).
- **Valid Range:** 0.0 to 100.0%.
- **Failure Value:** `0xFF` (CAN error).
- **Timeout:** 150 ms.
- **Owner:** Chassis Actuator Controller & HIL Emulator (`hil_simulator.py`).
- **Safety Consequence:** Actuation timeout triggers mechanical spring-applied fail-safe emergency brakes (parking/secondary brake drop).

---

### IF-07: Central Speed Command Dispatch
- **Input:** Central Orchestrator dispatch optimizer.
- **Output:** Target speed recommendation sent to vehicle.
- **Protocol:** HTTP JSON / CAN J1939 Proprietary B (PGN 65281).
- **Message Format:**
  `{"vehicle_id": "TRUCK_01", "sequence": 502, "timestamp": 1727134000.5, "requested_speed_mps": 8.0, "reason": "FOG_HEADWAY"}`
- **Update Rate:** 10 Hz (100 ms).
- **Timestamp:** Microsecond Unix timestamp.
- **Units:** Metres per second (m/s).
- **Valid Range:** 0.0 to 11.11 m/s (0 to 40 km/h).
- **Failure Value:** `action: STOP`.
- **Timeout:** 500 ms.
- **Owner:** Central Command Gateway (`command_gateway.py`).
- **Safety Consequence:** If rejected by Local Governor or stale, command is dropped; local governor clamps to local $v_{\text{safe}}$.

---

### IF-08: GNSS / Local Positioning Interface
- **Input:** Multi-constellation GNSS RTK receiver (GPS + NavIC/IRNSS).
- **Output:** UTM coordinate $(X, Y, Z)$ or mine-grid $(E, N, RL)$.
- **Protocol:** NMEA 0183 (GGA / RMC) / Binary UBX over RS232/Ethernet.
- **Message Format:** `{"easting": 584320.5, "northing": 2068410.2, "rl": 1120.5, "fix_quality": 4, "hdop": 0.8}`
- **Update Rate:** 5 Hz (200 ms).
- **Timestamp:** GPS Time synchronized to UTC.
- **Units:** Metres (m).
- **Valid Range:** Mine spatial bounding box.
- **Failure Value:** `fix_quality: 0` (No Fix), `hdop > 5.0`.
- **Timeout:** 1000 ms.
- **Owner:** Positioning Adapter (`coordinate_mapper.py`).
- **Safety Consequence:** Loss of RTK fix triggers dead-reckoning fallback (wheel odometry + IMU); if dead-reckoning drifts $>5.0\text{ m}$, vehicle speed is capped to crawl.

---

### IF-09: RF Telemetry & Link Quality
- **Input:** Semtech SX1278 transceiver internal registers.
- **Output:** Physical link quality metrics.
- **Protocol:** SPI register read in ESP32 firmware.
- **Message Format:** Internal struct `RfLinkMetrics { float rssi_dbm; float snr_db; float packet_loss_pct; }`
- **Update Rate:** 10 Hz (100 ms).
- **Timestamp:** Microsecond timestamp of packet RX.
- **Units:** `rssi`: dBm, `snr`: dB, `packet_loss`: $\%$.
- **Valid Range:** RSSI: -125.0 to -20.0 dBm; SNR: -20.0 to +15.0 dB; Loss: 0.0 to 100.0%.
- **Failure Value:** `RSSI = -140.0 dBm`, `SNR = -30.0 dB`.
- **Timeout:** 500 ms.
- **Owner:** ESP32 Gateway Firmware & Selector Adapter (`dsss_gateway_selector.py`).
- **Safety Consequence:** Degraded RF link triggers proactive gateway handover or safe beacon warning.

---

### IF-10: DSSS / Gateway Selection State
- **Input:** Evaluated link correlation scores across multiple gateways.
- **Output:** Active gateway ID and connection state machine state.
- **Protocol:** Internal Python Adapter (`dsss_gateway_selector.py`).
- **Message Format:**
  `{"active_gateway": "GW_RAMP_01", "state": "CONNECTED", "correlation_score": 0.94, "handover_in_progress": false}`
- **Update Rate:** 10 Hz (100 ms).
- **Timestamp:** Unix timestamp.
- **Units:** Correlation score [0.0 to 1.0].
- **Valid Range:** States: `NO_GATEWAY`, `CONNECTED`, `DEGRADED`, `HANDOVER_PENDING`, `DISCONNECTED`.
- **Failure Value:** `NO_GATEWAY`.
- **Timeout:** 300 ms.
- **Owner:** DSSS Gateway Selector (`integration_adapters/dsss_gateway_selector.py`).
- **Safety Consequence:** Disconnection removes central command authority; triggers local governor autonomy.

---

### IF-11: Sensor Health & Degradation State
- **Input:** Raw telemetry streams and environmental measurements.
- **Output:** Quality enumeration, confidence score, and active fault codes.
- **Protocol:** Typed Data Health Record (`integration_adapters/environmental_data_health.py`).
- **Message Format:**
  ```python
  @dataclass
  class SensorHealthRecord:
      sensor_id: str
      timestamp: float
      value: float
      quality: SensorQuality      # VALID, DEGRADED, STALE, MISSING, STUCK, OUTLIER, INCONSISTENT, UNKNOWN
      confidence: float          # [0.0, 1.0]
      fault_code: str            # NONE, ERR_STUCK, ERR_DRIFT, ERR_SPIKE, ERR_TIMEOUT
      last_valid_timestamp: float
  ```
- **Update Rate:** 10 Hz (100 ms).
- **Timestamp:** Microsecond Unix timestamp.
- **Units:** Dimensionless confidence $[0.0, 1.0]$.
- **Valid Range:** Enum values and float confidence $[0.0, 1.0]$.
- **Failure Value:** `quality: MISSING`, `confidence: 0.0`.
- **Timeout:** 200 ms.
- **Owner:** Data Health Engine (`environmental_data_health.py`).
- **Safety Consequence:** Degradation reduces confidence weight in state estimator; unrecoverable failure drops to conservative safe speed.

---

### IF-12: Local Vehicle Safety Governor State
- **Input:** Vehicle speed, road grade, visibility, sensor health, and incoming central command.
- **Output:** Applied speed setpoint, clamp reason, and failsafe state.
- **Protocol:** CAN J1939 Proprietary B (PGN 65282) / Internal Struct (`fail_safe_controller.py`).
- **Message Format:**
  `{"applied_speed": 4.38, "v_safe": 4.38, "action": "CLAMP", "state": "NORMAL", "reason": "FOG_STOPPING_GOVERNED"}`
- **Update Rate:** 20 Hz (50 ms control loop).
- **Timestamp:** Microsecond epoch timestamp.
- **Units:** Metres per second (m/s).
- **Valid Range:** $v_{\text{applied}} \in [0.0, v_{\text{safe}}]$.
- **Failure Value:** $v_{\text{applied}} = 0.0\text{ m/s}$ (Emergency Stop).
- **Timeout:** 100 ms (Firmware watchdog).
- **Owner:** Local Safety Governor (`fail_safe_controller.py`).
- **Safety Consequence:** Ultimate operational safety authority. Invariant $v_{\text{applied}} \le v_{\text{safe}}$ is strictly enforced.

---

### IF-13: Safe Beacon Broadcast
- **Input:** Onboard failsafe status from Local Safety Governor.
- **Output:** Autonomous over-the-air RF safety heartbeat.
- **Protocol:** Custom ASCII Broadcast over 433 MHz LoRa PHY.
- **Message Format:**
  `BEACON,<vehicle_id>,<sequence>,<state>,<timestamp>,<zone_id>`
- **Update Rate:** 2 Hz (nominal) to 5 Hz (emergency/degraded).
- **Timestamp:** Monotonic timestamp + UTC seconds.
- **Units:** ASCII state tokens: `NORMAL`, `DEGRADED`, `STOP`, `EMERGENCY`.
- **Valid Range:** Vehicle IDs: `TRUCK_01` to `TRUCK_99`.
- **Failure Value:** Silent broadcast (detected as beacon loss by peers).
- **Timeout:** 1000 ms.
- **Owner:** Safe Beacon Adapter (`safe_beacon_adapter.py` / `failsafe/safe_beacon.py`).
- **Safety Consequence:** Alerts peer vehicles in dense fog; enables peer-to-peer headway protection when central network is down.

---

## 4. PHYSICAL VALUE CERTIFICATION & HONESTY DISCLOSURE

```
[MEASUREMENT STATUS DECLARATION]
- Wheel Speed, Engine RPM, IMU (ax, ay, az, gx, gy, gz): MEASURED (ESP32 + MPU6050 Bench Testbed)
- RF Latency, Packet Loss, RSSI, SNR: MEASURED (SX1278 433 MHz Bench Testbed)
- CAN / TWAI Bus Latency: MEASURED (ESP32 TWAI Driver 250 kbps Bench Testbed)
- Brake Actuator Delay (250 ms): ENGINEERING ASSUMPTION (ISO 3450 / SAE J1452 Standard)
  * Hardware limitation: Physical BH100 hydraulic brake valve timing is UNMEASURED ON PHYSICAL TRUCK.
- DSSS Direct-Sequence Spreading: ARCHITECTURAL SIMULATION MODEL (Physical RF is SX1278 LoRa CSS).
```
