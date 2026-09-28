# 03 — HARDWARE-SOFTWARE INTERFACE CONTRACT
## FOG-ORCHESTRATOR 2.0 | SIH 2026-27 (Problem Statement: SIH26007)
### NMDC Bailadila Deposit-5 Low-Visibility HEMM Safety System
**Document ID:** `03_HARDWARE_SOFTWARE_INTERFACE_CONTRACT.md`  
**Phase:** 9 — Full Hardware + Software + HMI + Control Room + Digital Twin Integration  
**Status:** AUTHORITATIVE & FROZEN  

---

## 1. PURPOSE & ARCHITECTURAL SCOPE

This interface specification defines the immutable data contract between physical microcontrollers, sensors, vehicle networks, RF communication links, the central FOG-ORCHESTRATOR backend, human-machine interfaces, Digital Twin, and the onboard Local Vehicle Safety Governor.

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
  - `speed`: 0.0 to 18.0 m/s (0 to 65 km/h)
  - `ax, ay, az`: -19.62 to +19.62 m/s² (±2g nominal full scale)
  - `gx, gy, gz`: -250.0 to +250.0 °/s
- **Failure Value:**
  - Missing field / malformed CSV: packet dropped, packet_error counter incremented.
  - Out of range: clamped or flagged as `SENSOR_OUTLIER`.
- **Subsystem Owner:** Vehicle Embedded Telemetry Firmware (ESP32).
- **Safety Consequence:** Low-level odometry loss causes fallback to inertial dead-reckoning; total loss triggers communication timeout and autonomous Local Safe Mode.

---

### IF-02: Gateway Telemetry Uplink (Gateway to Orchestrator Backend)
- **Input:** Received 433 MHz RF packet from LoRa receiver.
- **Output:** HTTP POST JSON payload to `/api/hardware/telemetry`.
- **Protocol:** HTTP/1.1 REST over TCP/IP (Wi-Fi 802.11 b/g/n or Ethernet).
- **Message Format:**
```json
{
  "source": "HARDWARE",
  "vehicle_id": "TRUCK_01",
  "sequence": 14205,
  "rpm": 1250.0,
  "speed_mps": 6.8,
  "accel": {"ax": 0.05, "ay": -0.01, "az": 9.81},
  "gyro": {"gx": 0.0, "gy": 0.0, "gz": 0.02},
  "rf_metrics": {"rssi_dbm": -82.0, "snr_db": 6.5, "carrier": "CSS_LORA_433"},
  "event_timestamp": 1727136000.120,
  "receive_timestamp": 1727136000.145,
  "gateway_id": "GW_01"
}
```
- **Update Rate:** 10 Hz (100 ms).
- **Timeout:** 1000 ms. If no packet received in 1000 ms, backend marks vehicle link as `STALE`.
- **Subsystem Owner:** Gateway Ingestion Service.

---

### IF-06: Service & Retarder Brake (CAN / TWAI J1939)
- **Input:** CAN J1939 Electronic Brake Controller (EBC1) and Electronic Retarder Controller (ERC1).
- **Output:** Brake cylinder pressure, retarder active percentage, ABS intervention flag.
- **Protocol:** SAE J1939 over CAN 2.0B at 250 kbps.
- **CAN IDs:**
  - `0x18F0010B` (EBC1, PGN 61441): Service brake status, deceleration demand.
  - `0x18F00000` (ERC1, PGN 61440): Retarder torque absorption percent.
- **Update Rate:** 20 Hz (50 ms).
- **Timeout:** 150 ms.
- **Subsystem Owner:** Vehicle Brake ECU & Local Safety Governor.
- **Safety Consequence:** CAN bus failure or timeout latches maximum safe service braking deceleration without central override.

---

### IF-07: Speed Command Dispatch (Orchestrator to Local Safety Governor)
- **Input:** Central Dispatch Optimizer speed recommendation.
- **Output:** Incoming command structure delivered to Local Safety Governor.
- **Protocol:** J1939 Proprietary-B over CAN or authenticated JSON over secure telemetry downlink.
- **Message Format:**
```json
{
  "command_id": "CMD_TRUCK01_10492",
  "vehicle_id": "TRUCK_01",
  "timestamp": 1727136000.150,
  "target_speed": 7.5,
  "reason": "HAUL_ROAD_FOG_CRUISING",
  "validity_window_s": 0.5
}
```
- **Update Rate:** 10 Hz (100 ms).
- **Timeout:** 500 ms (commands older than 500 ms are rejected as stale).
- **Subsystem Owner:** Central Fleet Orchestrator.
- **Safety Consequence:** Advisory proposal only. The Local Safety Governor enforces $v_{\text{command}} = \min(v_{\text{target}}, v_{\text{safe}})$.

---

### IF-13: Safe Beacon Broadcast (Autonomous Failsafe RF Carrier)
- **Input:** Communication loss detector from Local Safety Governor.
- **Output:** Broadcast ASCII frame on 433 MHz LoRa.
- **Protocol:** ASCII fixed-format broadcast beacon.
- **Message Format:**
  `SAFE_BEACON,<vehicle_id>,<seq>,<state>,<v_safe>,<timestamp>,<zone_id>`
- **Update Rate:** 2 Hz to 5 Hz (200 ms to 500 ms interval).
- **Timeout:** Receiver timeout 1000 ms.
- **Subsystem Owner:** Autonomous Failsafe Module (`failsafe/safe_beacon.py`).
- **Safety Consequence:** Alerts neighboring vehicles and control room of communication blackout and autonomous safe mode transition.
