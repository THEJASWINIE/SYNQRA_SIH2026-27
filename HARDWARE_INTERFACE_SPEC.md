# HARDWARE INTERFACE SPECIFICATION (HIL BRIDGE)
**PROJECT**: FOG-ORCHESTRATOR 2.0  
**TARGET HARDWARE**: ESP32 Microcontrollers + LoRa Transceivers + IMU + Wheel Speed Sensors  
**MODULE**: `hardware_emulator.py`  
**DATE**: 2026-08-28  

---

## 1. SPECIFICATION OVERVIEW

This document specifies the software-hardware interface contract between the central **FOG-ORCHESTRATOR 2.0 Digital Twin / HMI** and the physical on-vehicle microcontrollers (ESP32).

To validate the architecture before physical hardware connection, the system utilizes the **Hardware Interface Emulator** (`hardware_emulator.py`) implementing Vehicle A and Vehicle B emulators. The emulator implements the exact binary/JSON serialization protocol, safety governor clamping, and network degradation behavior specified below.

---

## 2. INBOUND COMMAND SPECIFICATION (Central $\to$ Vehicle ESP32)

### DispatchCommand Message Contract

```json
{
  "command_id": "CMD_20260828_001",
  "vehicle_id": "TRUCK_01",
  "timestamp": 1788000.0,
  "target_speed": 6.0,
  "route_id": "ROUTE_MAIN_HAUL",
  "departure_time": 1788200.0,
  "slot_id": "SLOT_INTERSECTION_A2",
  "action": "TARGET_SPEED",
  "reason_code": "ARRIVAL_RATE_EXCEEDS_CAPACITY"
}
```

#### Field Specifications:
- `command_id` (string): Unique identifier for command tracking and ACK matching.
- `vehicle_id` (string): Target vehicle hardware identifier (`TRUCK_01` = Vehicle A, `TRUCK_02` = Vehicle B).
- `timestamp` (float): Central dispatch creation timestamp in seconds.
- `target_speed` (float): Recommended target speed in meters per second (m/s).
- `action` (string): Enum: `TARGET_SPEED`, `HOLD`, `RELEASE`, `STOP`, `ROUTE`.
- `reason_code` (string): Explainable optimization decision code (e.g. `ARRIVAL_RATE_EXCEEDS_CAPACITY`, `SWITCHBACK_SLOT_RESERVATION`).

---

## 3. OUTBOUND TELEMETRY SPECIFICATION (Vehicle ESP32 $\to$ Central)

### 3.1 VehicleState Message Contract

```json
{
  "vehicle_id": "TRUCK_01",
  "timestamp": 1788001.0,
  "position": 245.8,
  "segment_id": "ROAD_1",
  "speed_mps": 5.4,
  "acceleration_mps2": 0.1,
  "heading": 0.0,
  "mode": "traveling",
  "communication_state": "HEALTHY",
  "is_loaded": true,
  "total_tonnes_hauled": 182.0
}
```

### 3.2 SafetyState Message Contract

```json
{
  "vehicle_id": "TRUCK_01",
  "timestamp": 1788001.0,
  "actual_speed": 5.4,
  "v_safe": 5.4,
  "h_safe": 22.5,
  "risk_level": 0.15,
  "active_constraint": "Visibility",
  "v_stop": 5.4,
  "v_retarder": 15.0,
  "v_curve": 15.0,
  "v_mine": 13.89,
  "a_dec": 2.1,
  "s_stop": 17.5,
  "s_margin": 5.0,
  "is_safe": true
}
```

### 3.3 CommandAck Message Contract

```json
{
  "command_id": "CMD_20260828_001",
  "vehicle_id": "TRUCK_01",
  "timestamp": 1788001.0,
  "status": "CLAMPED",
  "applied_speed": 5.4,
  "reason": "Command speed (8.00 m/s) exceeded safe ceiling (5.40 m/s). Clamped by local governor."
}
```

### 3.4 Health Message Contract

```json
{
  "component_id": "VEHICLE_EMULATOR_TRUCK_01",
  "timestamp": 1788001.0,
  "state": "HEALTHY",
  "latency_ms": 15.0,
  "age_ms": 25.0,
  "error_code": 0
}
```

---

## 4. LOCAL SAFETY GOVERNOR RULES ON HARDWARE

1. **Non-Negotiable Speed Clamp**:
   $$\text{applied\_speed} = \min(v_{\rm command}, v_{\rm safe})$$
2. **Multi-Constraint Safe Speed Solver**:
   $$v_{\rm safe} = \min(v_{\rm stop}, v_{\rm retarder}, v_{\rm curve}, v_{\rm mine})$$
3. **Telemetry Age & Stale Data Timeout**:
   - If telemetry age $> 5.0\text{ s}$ or LoRa signal is lost, vehicle hardware drops central control and activates `COMMUNICATION_DEGRADED_FALLBACK` mode with $v_{\rm safe} \le 2.78\text{ m/s}$ ($10\text{ km/h}$).

---

## 5. PHYSICAL ESP32 HARDWARE MAPPING (NEXT STEP)

When real hardware is integrated in the next phase, the C++ firmware in `esp32_code/sketch_aug26a/sketch_aug26a.ino` and `esp32_code/vehicle_B/vehicle_B.ino` will handle physical sensing:
- **Wheel Speed Sensor / Encoder**: Measures $v_{\text{act}}$ (m/s).
- **MPU6050 / IMU**: Measures acceleration $a_x$ ($m/s^2$) and road grade angle $\theta$ (rad).
- **SX1276 LoRa Transceiver**: Transmits/receives JSON payloads at 433/868 MHz.
- **Motor / Retarder Driver**: Receives PWM signal corresponding to `applied_speed`.
