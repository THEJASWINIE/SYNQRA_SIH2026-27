# FOG-ORCHESTRATOR 2.0 — INTEGRATION BASELINE
**SIH 2026-27 | Hardware ↔ Software End-to-End Integration (Phases H1–H10)**  
**Lead Integration Engineer:** Cyber-Physical Systems & Safety Integration Lead  
**Document Revision:** 1.0 (Phase H1 Baseline Freeze)  
**Date:** 2026-09-24  
**Classification Standard:** Strict Non-Negotiable Source-of-Truth Hierarchy  

---

## 1. Existing System Architecture Overview

FOG-ORCHESTRATOR 2.0 is an integrated cyber-physical fleet safety and low-visibility guidance platform designed for open-cast mining operations (specifically modeled around the NMDC Bailadila Iron Ore Mine, Deposit 5).

The target architecture operates on a strict multi-tier hierarchy:
1. **Tier 0 (Chassis Hardware & Microcontroller):** Dual ESP32 physical nodes (Vehicle A / TRUCK_01, Vehicle B / TRUCK_02) with optical wheel encoders, MPU6050 6-DOF IMUs, dual motor drivers (L298N on A, TB6612FNG on B), and SX1278 (Ra-02) 433 MHz LoRa transceivers.
2. **Tier 1 (Local Safety Governor):** An autonomous, fail-safe speed and stopping distance solver running directly on the vehicle microcontroller/ECU. It maintains absolute local safety authority and evaluates:
   $$v_{\text{command}} = \min(v_{\text{dispatch}}, v_{\text{safe}})$$
   where $v_{\text{safe}} = \min(v_{\text{stop}}, v_{\text{retarder}}, v_{\text{traction}}, v_{\text{curve}}, v_{\text{mine}})$.
3. **Tier 2 (Haul Road Infrastructure & Gateway):** Stationary ESP32 LoRa-to-WiFi gateway bridges, physical/emulated intersection RSUs, and DSSS/PN sequence correlation models.
4. **Tier 3 (Central Fog Orchestrator & Digital Twin):** A high-performance Python/FastAPI backend hosting the single authoritative canonical Digital Twin (`LIVE_MIRROR`, `PREDICTIVE`, `WHAT_IF`, `REPLAY`, `FAULT_INJECTION`), global slot reservation, bottleneck analyzer, and dispatcher.
5. **Tier 4 (HMI & Operator Displays):** Dual specialized user interfaces:
   - **Operator HMI:** Low-latency driver situational awareness screen.
   - **Control Room HMI:** Centralized fleet management, bottleneck tracking, and safety supervisory console.

---

## 2. Existing Physical Hardware Inventory & Parameter Classification

Every parameter in the system is classified under the strict Source-of-Truth rule:
- `VERIFIED`: Measured and confirmed on benchtop or prototype hardware.
- `MODEL_PARAMETER`: Standard physical or mathematical constant.
- `ENGINEERING_ASSUMPTION`: Design parameter grounded in engineering literature.
- `SIMULATION_SCENARIO`: Configurable parameter for scenario evaluation.
- `UNKNOWN`: Unmeasured or unverified (never promoted without empirical proof).

### 2.1 Vehicle A (TRUCK_01) Hardware Configuration
* **Microcontroller:** ESP32 Dual-Core Tensilica Xtensa LX6 @ 240 MHz (`VERIFIED`)
* **Chassis Architecture:** 4-wheel differential drive (`VERIFIED`)
* **Gross Vehicle Mass (Prototype):** $2.20\text{ kg}$ (`VERIFIED`)
* **Scale Target Mass (OEM HEMM):** $165,000\text{ kg}$ (165 tonnes loaded CAT 777D / BEML BH100) (`MODEL_PARAMETER`)
* **Motor Driver:** L298N Dual H-Bridge (`VERIFIED`)
  - `LEFT_IN1`: GPIO 25 (`VERIFIED`)
  - `LEFT_IN2`: GPIO 26 (`VERIFIED`)
  - `LEFT_PWM`: GPIO 27 (`VERIFIED`)
  - `RIGHT_IN1`: GPIO 32 (`VERIFIED`)
  - `RIGHT_IN2`: GPIO 33 (`VERIFIED`)
  - `RIGHT_PWM`: GPIO 14 (`VERIFIED`)
  - `MOTOR_STBY`: GPIO 13 (`VERIFIED`)
* **Speed Sensor:** LM393 Optical Interrupter with slotted encoder disk (`VERIFIED`)
  - `SPEED_SENSOR_PIN`: GPIO 35 (`VERIFIED`)
  - `PULSES_PER_REV`: $42.0\text{ PPR}$ (`VERIFIED`)
  - `WHEEL_DIAMETER_M`: $0.100\text{ m}$ ($10.0\text{ cm}$) (`VERIFIED`)
  - `WHEEL_CIRCUMFERENCE_M`: $\pi \times 0.100 = 0.31416\text{ m}$ (`MODEL_PARAMETER`)
* **IMU:** InvenSense MPU6050 6-axis accelerometer + gyroscope over I2C (`VERIFIED`)
  - `SDA`: GPIO 21, `SCL`: GPIO 22, I2C Address: `0x68` (`VERIFIED`)
* **RF Transceiver:** Semtech SX1278 (Ai-Thinker Ra-02) 433 MHz LoRa (`VERIFIED`)
  - `SCK`: 18, `MISO`: 19, `MOSI`: 23, `SS`: 5, `RST`: 4, `DIO0`: 34 (`VERIFIED`)
  - Frequency: 433.0 MHz, SF7, BW 125 kHz, CR 4/5 (`VERIFIED`)

### 2.2 Vehicle B (TRUCK_02) Hardware Configuration
* **Microcontroller:** ESP32 Dual-Core Tensilica Xtensa LX6 @ 240 MHz (`VERIFIED`)
* **Chassis Architecture:** 2-wheel drive + castor prototype (`VERIFIED`)
* **Gross Vehicle Mass (Prototype):** $1.85\text{ kg}$ (`VERIFIED`)
* **Motor Driver:** **Toshiba TB6612FNG Dual MOSFET H-Bridge** (`VERIFIED` — FROZEN, NEVER REVERT TO L298N)
  - `LEFT_IN1`: GPIO 25 (`VERIFIED`)
  - `LEFT_IN2`: GPIO 26 (`VERIFIED`)
  - `LEFT_PWM`: GPIO 27 (`VERIFIED`)
  - `RIGHT_IN1`: GPIO 32 (`VERIFIED`)
  - `RIGHT_IN2`: GPIO 33 (`VERIFIED`)
  - `RIGHT_PWM`: GPIO 14 (`VERIFIED`)
  - `MOTOR_STBY`: GPIO 13 (`VERIFIED`)
  - Direction Logic: Forward = IN1 HIGH / IN2 LOW; Brake = IN1 HIGH / IN2 HIGH; Coast = STBY LOW (`VERIFIED`)
  - PWM Frequency: 1000 Hz, 8-bit resolution (`VERIFIED`)
* **Speed Sensor:** Hall-effect / optical slotted encoder (`VERIFIED`)
  - `SPEED_SENSOR_PIN`: GPIO 35 (`VERIFIED`)
  - `PULSES_PER_REV`: $43.0\text{ PPR}$ (`VERIFIED`)
  - `WHEEL_DIAMETER_M`: $0.060\text{ m}$ ($6.0\text{ cm}$) (`VERIFIED`)
  - `WHEEL_CIRCUMFERENCE_M`: $\pi \times 0.060 = 0.18850\text{ m}$ (`MODEL_PARAMETER`)
* **Speed Limits:**
  - Maximum Safe Prototype Speed: $1.40\text{ m/s}$ ($5.04\text{ km/h}$) (`VERIFIED`)
  - Default Safe Crawl Speed: $0.50\text{ m/s}$ ($1.80\text{ km/h}$) (`VERIFIED`)
* **Calibration Provenance Note:** Prototype bench firmware (`VEHICLE_B_TRUCK_02_V2V_DIGITAL_TWIN_MOTOR.ino`) uses $D = 0.060\text{ m}, \text{PPR} = 43.0$, while the backend canonical model (`config/physical_vehicle_parameters.json`) maintains $R = 0.0425\text{ m}, D = 0.085\text{ m}, \text{PPR} = 20.0$ for `UnitConverter` and speed truth tests (`test_speed_truth_contract.py`). Both are tracked as `MODEL_PARAMETER`.

### 2.3 Stationary Infrastructure Gateway
* **Hardware:** ESP32 Gateway Node with Ra-02 LoRa transceiver + 802.11 b/g/n WiFi uplink (`VERIFIED`)
* **Uplink Protocol:** HTTP REST POST / WebSocket to backend `/api/v1/telemetry/ingest` (`VERIFIED`)

---

## 3. Existing Software Services & Architectural Boundaries

### 3.1 Backend Application Services (`SYNQRA_SIH2026-27-HMI/backend/app/main.py`)
- **FastAPI Core Framework:** Handles REST API routes, CORS middleware, and WebSocket connections.
- **WebSocket Streaming (`/ws/telemetry`):** 10 Hz broadcast of live Digital Twin vehicle and fleet states.
- **Gateway Serial / Network Ingest (`gateway_serial_reader.py`):** Ingests raw CSV and JSON telemetry from physical gateway ESP32.

### 3.2 Digital Twin Core (`integration_adapters/digital_twin_sync.py`, `canonical_twin_client.py`)
- Authoritative state store maintaining canonical vehicle states.
- Multi-mode operational support:
  - `LIVE_MIRROR`: Real-time streaming from physical hardware.
  - `PREDICTIVE`: Dead-reckoning and kinematic trajectory projection.
  - `WHAT_IF`: Sandboxed branch for dispatch optimization without hardware commands.
  - `REPLAY`: Historical incident playback with strict hardware command isolation.
  - `FAULT_INJECTION`: Synthetic fault simulation without affecting physical safety governors.

### 3.3 Safety Governor Engine (`fog_orchestrator/tier1_governor/`, `integration_adapters/fail_safe_controller.py`)
- Canonical physical deceleration model:
  $$a_{\text{dec}} = g \cdot (\mu \cdot \cos\theta - \sin\theta)$$
- Stopping distance with multi-stage reaction latency:
  $$S_{\text{stop}} = v \cdot \tau_{\text{total}} + \frac{v^2}{2 \cdot a_{\text{dec}}}$$
- Grade-aware speed clamp: Enforces $S_{\text{stop}} + S_{\text{margin}} \le R_{\text{effective}}$.

---

## 4. Existing Communication Paths & Telemetry Protocols

### 4.1 Physical Radio & Network Topology
```
[VEHICLE A (TRUCK_01)] <--- 433 MHz LoRa Peer-to-Peer V2V ---> [VEHICLE B (TRUCK_02)]
         |                                                                |
         +------------------- 433 MHz LoRa Uplink ------------------------+
                                         |
                                         v
                            [LORA GATEWAY AGGREGATOR]
                                         |
                                    WiFi / IP
                                         v
                         [FOG-ORCHESTRATOR BACKEND]
                                         |
                   +---------------------+---------------------+
                   |                                           |
            WebSocket                                      WebSocket
                   v                                           v
          [OPERATOR HMI]                              [CONTROL ROOM HMI]
```

### 4.2 Raw V2V Packet Contract (Preserved under Rule 2)
```text
STATE,TRUCK_01,seq,rpm,speed,ax,ay,az,gx,gy,gz
```
Example:
```text
STATE,TRUCK_01,104,120.5,0.63,0.02,-0.01,0.98,0.01,0.00,-0.02
```

### 4.3 Canonical Master Telemetry Schema (`integration_adapters/master_data_model.py`)
- `vehicle_id` (str)
- `data_source` ("HARDWARE" | "SIMULATION" | "HYBRID")
- `event_timestamp`, `receive_timestamp`, `processing_timestamp` (float)
- `position`, `position_x`, `position_y`, `heading`, `speed`, `acceleration`, `grade` (float)
- `visibility`, `weather_state` (float, str)
- `sensor_health` (8 states: VALID, DEGRADED, STALE, MISSING, STUCK, OUTLIER, INCONSISTENT, UNKNOWN)
- `sensor_confidence` (float 0.0 - 1.0)
- `gateway_id`, `gateway_state`, `correlation_score`, `RSSI`, `SNR`, `packet_loss`
- `CAN_state`, `CAN_latency`
- `commanded_speed`, `safe_speed`, `brake_state`, `safety_state`, `failsafe_state`, `safe_beacon_state`

---

## 5. Existing Safety States & Fail-Safe State Machine

The system enforces 10 discrete operational safety states:
1. `NORMAL`: Full communication, all sensors valid, dispatch speeds allowed up to sightline limits.
2. `CONNECTED`: Verified link with infrastructure gateway.
3. `DEGRADED`: Transient packet loss or increased sensor variance.
4. `COMMUNICATION_LOSS`: Heartbeat silence $> 500\text{ ms}$; vehicle autonomous fail-safe triggered.
5. `SENSOR_DEGRADED`: Optical/encoder drift detected; conservative safety limits applied.
6. `SENSOR_FAULT`: Optical/encoder blackout; visibility floored to $8.0\text{ m}$.
7. `SAFE_BEACON_ACTIVE`: 433 MHz local hazard broadcast enabled at 2 Hz.
8. `LOCAL_SAFE_MODE`: Local Tier-1 governor in full control; remote commands rejected.
9. `EMERGENCY_STOP`: Clamped to $0.0\text{ m/s}$ (service/emergency brakes locked).
10. `RECOVERY`: Persistence validation required (5 consecutive healthy packets) before returning to NORMAL.

---

## 6. Known System Limitations & Evidence Boundaries

1. **Actuator Hydraulic Delay ($250\text{ ms}$):**
   - **Classification:** `ENGINEERING_ASSUMPTION` (Literature derived from CAT 777D data).
   - **Evidence Level:** `L3 (HIL/Bench)`.
   - **Limitation:** Physical 100-tonne hydraulic brake calipers have not been instrumented in an operating mine pit.
2. **Single-Transceiver 433 MHz Half-Duplex Conflict:**
   - **Classification:** `VERIFIED`.
   - **Evidence Level:** `L3 (HIL/Bench)`.
   - **Limitation:** The single SX1278 transceiver cannot receive gateway downlink commands while transmitting Safe Beacons ($38.5\text{ ms}$ airtime blocking).
3. **Single-Channel Optical Sensor Bias:**
   - **Classification:** `MODEL_PARAMETER`.
   - **Limitation:** Single-channel transmissometers cannot self-validate constant additive drift without independent 77 GHz radar or stereo vision.
4. **DSSS / PN Gateway handovers:**
   - **Classification:** `SIMULATION_SCENARIO` / `MODEL_PARAMETER`.
   - **Limitation:** Physical layer uses Semtech LoRa CSS; DSSS Gold code correlation is evaluated in simulation.
