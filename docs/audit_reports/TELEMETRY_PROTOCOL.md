# FOG-ORCHESTRATOR 2.0 — CANONICAL TELEMETRY PROTOCOL SPECIFICATION

**Date**: 2026-08-28  
**Author**: Senior Embedded Systems Engineer, IoT Integration Engineer, Backend Engineer  
**Scope**: Physical Vehicle LoRa Telemetry, Gateway Serial Forwarding, and Backend Normalization Schema

---

## 1. LoRa Air Interface Packet Format (ESP32 → Gateway)

To minimize LoRa airtime, payload length, and transmission latency, Vehicle A (`TRUCK_01`) and Vehicle B (`TRUCK_02`) transmit a compact key-value comma-separated ASCII string.

### Standard Packet Syntax:
```text
V=<VEHICLE_ID>,RPM=<WHEEL_RPM>,SPD=<SPEED_MPS>,AX=<ACC_X>,AY=<ACC_Y>,AZ=<ACC_Z>,GX=<GYRO_X>,GY=<GYRO_Y>,GZ=<GYRO_Z>
```

### Field Definitions:

| Parameter | Key | Data Type | Units | Description | Example |
|-----------|-----|-----------|-------|-------------|---------|
| **Vehicle ID** | `V` | String | - | Unique vehicle identifier (`TRUCK_01` or `TRUCK_02`) | `TRUCK_01` |
| **Wheel Speed** | `RPM` | Float | rpm | Measured wheel rotation per minute | `240.0` |
| **Linear Speed** | `SPD` | Float | m/s | Calibrated linear speed in meters per second | `2.50` |
| **Accel X** | `AX` | Float/Int | LSB or $m/s^2$ | Longitudinal acceleration | `0.12` |
| **Accel Y** | `AY` | Float/Int | LSB or $m/s^2$ | Lateral acceleration | `-0.05` |
| **Accel Z** | `AZ` | Float/Int | LSB or $m/s^2$ | Vertical acceleration | `9.81` |
| **Gyro X** | `GX` | Float/Int | LSB or $rad/s$ | Roll rate | `0.02` |
| **Gyro Y** | `GY` | Float/Int | LSB or $rad/s$ | Pitch rate | `0.01` |
| **Gyro Z** | `GZ` | Float/Int | LSB or $rad/s$ | Yaw rate | `-0.03` |

---

## 2. Example Packets

### Vehicle A (`TRUCK_01` — Nominal Operational Telemetry):
```text
V=TRUCK_01,RPM=240.0,SPD=2.51,AX=0.12,AY=-0.05,AZ=9.81,GX=0.02,GY=0.01,GZ=-0.03
```

### Vehicle B (`TRUCK_02` — Operational Telemetry):
```text
V=TRUCK_02,RPM=180.5,SPD=1.89,AX=-0.08,AY=0.02,AZ=9.78,GX=-0.01,GY=0.00,GZ=0.01
```

---

## 3. LoRa Gateway Serial Protocol (Gateway ESP32 → USB Serial → Backend)

The Gateway ESP32 listens continuously on `433.0 MHz` LoRa frequency. Upon receiving a valid packet with RSSI and SNR metadata, it appends RSSI/SNR and forwards the string to the host backend via USB Serial at **115200 baud**:

```text
V=TRUCK_01,RPM=240.0,SPD=2.51,AX=0.12,AY=-0.05,AZ=9.81,GX=0.02,GY=0.01,GZ=-0.03,RSSI=-65,SNR=9.2
```

---

## 4. Backend Canonical Translation Schema (`VehicleStateMessage`)

The HMI Backend `gateway_serial_reader.py` parses incoming USB Serial text, validates fields, and transforms raw ESP32 MPU6050 LSB values into standard physical units ($m/s^2$ for acceleration, $rad/s$ for gyroscope):

```json
{
  "vehicle_id": "TRUCK_01",
  "timestamp": 1787934500.125,
  "rpm": 240.0,
  "speed_mps": 2.51,
  "speed_kmh": 9.04,
  "acceleration": {
    "x": 0.12,
    "y": -0.05,
    "z": 9.81
  },
  "gyroscope": {
    "x": 0.02,
    "y": 0.01,
    "z": -0.03
  },
  "communication": {
    "status": "ONLINE",
    "last_seen": 1787934500.125,
    "rssi": -65,
    "snr": 9.2
  },
  "mode": "traveling",
  "safety_state": "NORMAL"
}
```

---

## 5. Malformed Packet & Error Handling Rules

1. **Missing Vehicle ID (`V=`)**: Reject packet silently, log error counter, do not throw backend exception.
2. **Out-of-Bound Sensor Values**: Clamp $RPM \ge 0$, raw acceleration values to physical $\pm 16g$ bounds.
3. **Partial Transmission / Garbled Noise**: If string parsing fails key-value tokenization, discard line immediately.
4. **Communication Dropout**: If no valid packet arrives from `TRUCK_01` or `TRUCK_02` within $3.0\text{s}$, transition state from `ONLINE` $\rightarrow$ `STALE` $\rightarrow$ `OFFLINE` ($>10\text{s}$). The backend remains 100% stable.
