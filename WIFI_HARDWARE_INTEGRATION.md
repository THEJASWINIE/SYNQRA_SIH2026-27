# FOG-ORCHESTRATOR 2.0 — DIRECT WI-FI HARDWARE INTEGRATION SPECIFICATION

**Author**: Principal Systems Architect, HMI Software Integration Lead  
**Scope**: Vehicle A (TRUCK_01) Direct Wi-Fi Telemetry $\to$ FastAPI Backend $\to$ Canonical TwinStateStore $\to$ React/Vite Supervisory HMI  
**Status**: VERIFIED & BENCH-VALIDATED  

---

## 1. Network Topology & System Architecture

```text
┌─────────────────────────────────────────────────────────────┐
│  VEHICLE A PHYSICAL HARDWARE (TRUCK_01)                     │
│  - ESP32 Dual-Core MCU (Wi-Fi 802.11 b/g/n)                 │
│  - LM393 Speed Encoder (42 pulses/rev, 10 cm wheel)         │
│  - MPU6050 6-DOF IMU (I2C 0x68: SDA=21, SCL=22)            │
│  - Ra-02 433 MHz LoRa Transceiver (V2V peer link)           │
│  - TB6612FNG Dual H-Bridge Motor Driver                     │
│  - Non-blocking loop: 500 ms speed calc, 2000 ms HMI TX     │
└──────────────────────────────┬──────────────────────────────┘
                               │ HTTP POST (Wi-Fi LAN)
                               │ Header: Content-Type: application/json
                               ▼
┌─────────────────────────────────────────────────────────────┐
│  FASTAPI SUPERVISORY BACKEND (Port 8000 on 0.0.0.0)         │
│  - Ingress: POST /api/hardware/telemetry                    │
│  - Enforces sequence monotonicity (sequence > last_seq)     │
│  - Enforces bounded memory deduplication                    │
│  - Invariant: Sets HMI_MODE = "LIVE"                        │
│  - Invariant: Blocks mock overwrites (HTTP 409 Conflict)    │
│  - Normalizes IMU LSB counts to SI (m/s², rad/s)            │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│  CANONICAL TELEMETRY INGESTION (telemetry_ingest.py)        │
│  - Atomic write into TwinStateStore                         │
│  - Stamped with source="HARDWARE", origin="HARDWARE"        │
│  - NEVER_FROM_HARDWARE: position, road_id, visibility, mu    │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│  CANONICAL TWIN PROJECTION (twin_projection.py)             │
│  - Builds standardized TwinVehicle envelope                 │
│  - Evaluates freshness (ONLINE <= 3s, STALE <= 10s, OFFLINE)│
└──────────────────────────────┬──────────────────────────────┘
                               │ WebSocket push
                               │ Frame: {"type": "twin_vehicle_update", "data": ...}
                               ▼
┌─────────────────────────────────────────────────────────────┐
│  REACT / VITE HMI FRONTEND (Port 5173)                      │
│  - LiveDataProvider.ts consumes WebSocket stream            │
│  - Zod rawTwinVehicleSchema validation                      │
│  - Central Zustand store (store.ts) state update            │
│  - Operator & Technician screens display TRUCK_01 LIVE      │
└─────────────────────────────────────────────────────────────┘
```

---

## 2. Addressing & Network Configuration

| Component | Interface / Host | Port | Protocol / Transport |
| :--- | :--- | :--- | :--- |
| **Vehicle A (TRUCK_01)** | Wi-Fi Station Mode (DHCP IP) | Ephemeral | HTTP/1.1 REST Client |
| **Local Wi-Fi Router / AP** | Gateway / Access Point | N/A | IEEE 802.11 b/g/n (WPA2) |
| **FastAPI Backend Host** | `0.0.0.0` (All LAN adapters) | `8000` | HTTP / WebSocket Server |
| **HMI Web Frontend** | `127.0.0.1` / `0.0.0.0` | `5173` | React 19 / Vite HTTP |
| **Backend REST Endpoint** | `http://<HOST_IP>:8000/api/hardware/telemetry` | `8000` | HTTP POST |
| **WebSocket Feed** | `ws://<HOST_IP>:8000/api/ws` | `8000` | WebSocket RFC 6455 |

---

## 3. Canonical Telemetry Data Contract

### Wire Schema (`POST /api/hardware/telemetry`)
```json
{
  "vehicle_id": "TRUCK_01",
  "sequence": 1001,
  "source": "DIRECT_WIFI",
  "rpm": 1250.00,
  "speed": 0.85,
  "accel_x": 120,
  "accel_y": -50,
  "accel_z": 16384,
  "gyro_x": 13,
  "gyro_y": 26,
  "gyro_z": -13,
  "rssi": -65,
  "snr": 9.50
}
```

### Field Definitions & Physical Units

| Field Name | Type | Unit | Measured vs Derived | Description |
| :--- | :--- | :--- | :--- | :--- |
| `vehicle_id` | `str` | N/A | Static | Target vehicle ID (`"TRUCK_01"`). |
| `sequence` | `uint32_t` | Count | Measured | Strictly monotonic counter; incremented once per frame. |
| `source` | `str` | Enum | Static | Transport origin indicator (`"DIRECT_WIFI"`). |
| `rpm` | `float` | rev/min | Measured | Wheel RPM measured by LM393 slot sensor & ISR. |
| `speed` | `float` | m/s | **Derived** | Encoder linear speed: $v = (\text{RPM}/60) \cdot \pi D$ ($D=0.10\text{ m}$). |
| `accel_x` | `int16_t` | LSB | Measured | Raw MPU6050 X-axis acceleration count ($\pm 2g$, 16384 LSB/g). |
| `accel_y` | `int16_t` | LSB | Measured | Raw MPU6050 Y-axis acceleration count ($\pm 2g$, 16384 LSB/g). |
| `accel_z` | `int16_t` | LSB | Measured | Raw MPU6050 Z-axis acceleration count ($\pm 2g$, 16384 LSB/g). |
| `gyro_x` | `int16_t` | LSB | Measured | Raw MPU6050 X-axis angular rate ($\pm 250^\circ/\text{s}$, 131 LSB/(°/s)). |
| `gyro_y` | `int16_t` | LSB | Measured | Raw MPU6050 Y-axis angular rate ($\pm 250^\circ/\text{s}$, 131 LSB/(°/s)). |
| `gyro_z` | `int16_t` | LSB | Measured | Raw MPU6050 Z-axis angular rate ($\pm 250^\circ/\text{s}$, 131 LSB/(°/s)). |
| `rssi` | `int` | dBm | Measured | Wi-Fi Station signal strength (`WiFi.RSSI()`). |
| `snr` | `float` | dB | Measured/Relay | Signal-to-noise ratio from V2V LoRa relay or default 9.5 dB. |

---

## 4. Hardware Source-of-Truth & Honesty Invariants

1. **Measured Quantities**:
   - Wheel pulses and derived RPM.
   - Raw MPU6050 accelerometer and gyroscope readings.
   - Wi-Fi RSSI and transmission sequence.
2. **Derived Quantities**:
   - `vehicleSpeed` in $\text{m/s}$ is derived from RPM:
     $$\text{speed}_{\rm m/s} = \frac{\text{RPM}}{60.0} \cdot \pi \cdot 0.10$$
   - In accordance with project audit rules, this is designated **DERIVED FROM MEASUREMENT** and is not represented as an independent ground-speed measurement.
3. **NEVER_FROM_HARDWARE Invariants**:
   - The ESP32 does **NOT** measure and must **NEVER** transmit:
     - Map coordinates (`position_s`, `x`, `y`)
     - Road network context (`road_id`, `node_id`, `heading_rad`)
     - Environmental parameters (`visibility_m`, `friction_mu`)
   - The backend actively prevents populating these fields from physical telemetry packets, and the HMI presents them as null/contextual to avoid fabricating sensor data.

---

## 5. Sequence, Freshness, & Fault Handling

1. **Monotonic Sequence Enforcement**:
   - Each packet must have $\text{sequence} > \text{last\_sequence}$.
   - Exact duplicates ($\text{sequence} == \text{last\_sequence}$) return `HTTP 409 Accepted Duplicate`.
   - Out-of-order packets ($\text{sequence} < \text{last\_sequence}$) return `HTTP 409 Rejected Out-of-Order`.
2. **Freshness State Machine**:
   - $t_{\rm age} \le 3.0\text{ s}$: State is `ONLINE`, data quality is `LIVE`.
   - $3.0\text{ s} < t_{\rm age} \le 10.0\text{ s}$: State is `STALE` (freshness warning indicated).
   - $t_{\rm age} > 10.0\text{ s}$: State is `OFFLINE` (hardware connection dropped).
3. **Simulation Overwrite Lockout**:
   - Active physical telemetry creates a $10.0\text{ s}$ lockout window during which any simulated packets targeting `TRUCK_01` on `/api/telemetry` are rejected with `HTTP 409 Conflict` (`IGNORED_MOCK_OVERWRITE`).
4. **Resilient Non-Blocking Wi-Fi Loop**:
   - HTTP request timeout is bounded to $1000\text{ ms}$.
   - If Wi-Fi disconnects, the vehicle state transitions to `COMM_DISCONNECTED`, failure counters increment, and background non-blocking reconnect attempts occur every $5000\text{ ms}$.
   - Motor control and ISR routines are completely decoupled and never stalled by network latency.
