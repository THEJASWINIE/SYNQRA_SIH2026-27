# HARDWARE ↔ SOFTWARE END-TO-END INTEGRATION SPECIFICATION
**FOG-ORCHESTRATOR 2.0 — SIH 2026-27 | Phases H1–H10**  
**Lead Embedded & CPS Integration Engineer**  
**Document Revision:** 1.0 (Phase H1 Interface Freeze)  
**Date:** 2026-09-24  

---

## 1. Hardware Interface Freeze (Phase H1)

This specification locks and freezes the physical pinouts, electrical interfaces, and kinematic parameters for both physical prototype vehicles.

### 1.1 Vehicle A (TRUCK_01) Hardware Interface
- **Microcontroller:** ESP32 NodeMCU-32S / ESP32-WROOM-32.
- **Motor Driver:** L298N Dual H-Bridge Driver.
  - `LEFT_IN1`: GPIO 25 (Left Motor Direction A)
  - `LEFT_IN2`: GPIO 26 (Left Motor Direction B)
  - `LEFT_PWM`: GPIO 27 (Left Motor Speed — ESP32 LEDC Channel 0)
  - `RIGHT_IN1`: GPIO 32 (Right Motor Direction A)
  - `RIGHT_IN2`: GPIO 33 (Right Motor Direction B)
  - `RIGHT_PWM`: GPIO 14 (Right Motor Speed — ESP32 LEDC Channel 1)
  - `MOTOR_STBY`: GPIO 13 (Hardware Enable/Standby Pin)
- **Speed Sensor / Encoder:**
  - `SPEED_SENSOR_PIN`: GPIO 35 (Input-Only, internal pullup disabled; requires external pullup resistor)
  - Interrupt Mode: `RISING` edge trigger
  - `PULSES_PER_REV`: $42.0\text{ PPR}$
  - `WHEEL_DIAMETER_M`: $0.100\text{ m}$ ($10\text{ cm}$)
  - `WHEEL_CIRCUMFERENCE_M`: $0.31416\text{ m}$
- **IMU:** InvenSense MPU6050 (6-axis Accel + Gyro)
  - `MPU_SDA`: GPIO 21, `MPU_SCL`: GPIO 22, I2C Address: `0x68`, Sample Rate: 50 Hz.
- **LoRa Transceiver:** Semtech SX1278 (Ra-02, 433 MHz)
  - `SCK`: GPIO 18, `MISO`: GPIO 19, `MOSI`: GPIO 23, `SS`: GPIO 5, `RST`: GPIO 4, `DIO0`: GPIO 34.

---

### 1.2 Vehicle B (TRUCK_02) Hardware Interface — TB6612FNG Freeze
Vehicle B utilizes a **Toshiba TB6612FNG Dual MOSFET H-Bridge**. It MUST NOT be reverted to L298N.

#### TB6612FNG Pin Mapping & Truth Table
| ESP32 Pin | TB6612 Pin | Function | Logic Level | Behavioral Result |
| :---: | :---: | :---: | :---: | :--- |
| **GPIO 13** | `STBY` | Standby / Hardware E-Stop | `LOW` | **All H-Bridges disabled (Coast to Stop)** |
| **GPIO 13** | `STBY` | Normal Operation | `HIGH` | H-Bridges enabled |
| **GPIO 25** | `AIN1` | Left Motor Direction Bit 1 | `HIGH` | Forward rotation (when AIN2=LOW) |
| **GPIO 26** | `AIN2` | Left Motor Direction Bit 2 | `LOW` | Forward rotation (when AIN1=HIGH) |
| **GPIO 25 & 26** | `AIN1 & AIN2` | Dynamic Brake | `HIGH & HIGH` | **Short-circuit dynamic brake (Active Braking)** |
| **GPIO 27** | `PWMA` | Left Motor Speed (LEDC Ch 0) | `0 - 255` | Duty cycle controls motor torque/speed |
| **GPIO 32** | `BIN1` | Right Motor Direction Bit 1 | `HIGH` | Forward rotation (when BIN2=LOW) |
| **GPIO 33** | `BIN2` | Right Motor Direction Bit 2 | `LOW` | Forward rotation (when BIN1=HIGH) |
| **GPIO 32 & 33** | `BIN1 & BIN2` | Dynamic Brake | `HIGH & HIGH` | **Short-circuit dynamic brake (Active Braking)** |
| **GPIO 14** | `PWMB` | Right Motor Speed (LEDC Ch 1) | `0 - 255` | Duty cycle controls motor torque/speed |

#### Vehicle B Kinematic Calibration Parameters
- **Wheel Diameter:** $D = 0.060\text{ m}$ ($6.0\text{ cm}$)
- **Wheel Radius:** $R = 0.030\text{ m}$
- **Wheel Circumference:** $C = \pi \times D = 3.14159265 \times 0.060 = \mathbf{0.188496\text{ m}}$
- **Encoder Resolution:** $\text{PPR} = \mathbf{43.0\text{ pulses/revolution}}$
- **Maximum Scale Prototype Speed:** $v_{\text{max}} = 1.40\text{ m/s}$ ($5.04\text{ km/h}$)
- **Default Power-On Speed:** $v_{\text{default}} = 0.50\text{ m/s}$ ($1.80\text{ km/h}$)
- **Maximum PWM Limit:** $220$ (Preserves motor driver longevity and prevents back-EMF spikes)

> **Calibration Provenance Note:**  
> The physical bench prototype uses $D = 0.060\text{ m}, \text{PPR} = 43.0$ (`VEHICLE_B_TRUCK_02_V2V_DIGITAL_TWIN_MOTOR.ino`). The backend canonical configuration (`config/physical_vehicle_parameters.json`) maintains $R = 0.0425\text{ m}, D = 0.085\text{ m}, \text{PPR} = 20.0$ for `UnitConverter` and speed truth contracts (`test_speed_truth_contract.py`). Both parameter sets are maintained and classified as `MODEL_PARAMETER`.

#### Kinematic Derivations & Firmware Formulas
```c
// Executed every SPEED_CALC_INTERVAL = 100 ms
unsigned long currentPulses = pulseCount;
unsigned long deltaPulses = currentPulses - previousPulseCount;
previousPulseCount = currentPulses;

// RPM Calculation:
wheelRPM = ((float)deltaPulses / PULSES_PER_REV) * (60000.0f / (float)deltaTimeMs);

// Linear Forward Speed (m/s):
measuredVehicleSpeed = (wheelRPM * WHEEL_CIRCUMFERENCE_M) / 60.0f;

// Total Odometry Distance (m):
totalDistanceM = ((float)currentPulses / PULSES_PER_REV) * WHEEL_CIRCUMFERENCE_M;
```

---

## 2. End-to-End Telemetry & Command Flow (Phases H2 & H7)

### 2.1 The Upstream Telemetry Path
```
[Wheels & IMU] 
      │ 50 Hz Hardware Sampling
      ▼
[ESP32 FreeRTOS Firmware] 
      │ Kinematic Odometry & V2V Formatting
      ▼
[SX1278 433 MHz LoRa Radio] 
      │ 38.5 ms Airtime Broadcast
      ▼
[ESP32 LoRa Gateway Aggregator] 
      │ SPI Ingest & WiFi HTTP POST
      ▼
[FastAPI Ingestion Boundary (/api/v1/telemetry/ingest)] 
      │ Sequence Validation & Quality Filtering
      ▼
[Canonical Master Data Model (VehicleState)] 
      │ Triple Timestamping & Freshness Check
      ▼
[Authoritative Digital Twin (TwinStateStore)] 
      │ WebSocket 10 Hz Broadcast
      ▼
[Operator HMI & Control Room HMI]
```

### 2.2 The Downstream Command Path (Strict Authority Enforcement)
```
[Dispatcher / Central Orchestrator Request]
      │
      ▼
[Target Speed Recommendation (v_dispatch)]
      │
      ▼
[TIER-1 LOCAL SAFETY GOVERNOR (Authoritative Level 1)]
      │ Evaluates v_safe = min(v_stop, v_retarder, v_traction, v_curve, v_mine)
      │ Invariant: v_applied = min(v_dispatch, v_safe)
      ▼
[CAN / TWAI Vehicle Command Frame (PGN 0xF001)]
      │ Priority 0x0 Arbitration
      ▼
[ESP32 Chassis Microcontroller]
      │ Local Firmware Watchdog Check (Age < 1000 ms)
      ▼
[TB6612FNG Motor Driver H-Bridge]
      │ PWM Duty Cycle Modulated
      ▼
[Physical DC Traction Motors]
```

---

## 3. Sensor Health & Data Quality Integration (Phase H3)

The system embeds an **8-State Sensor Quality Machine** for all incoming kinematic and environmental feeds:
- `VALID`: Sensor within physical limits and expected variance $\implies$ Full dispatch authority.
- `DEGRADED`: Noise or temporary jitter detected $\implies$ Additive uncertainty buffer $\sigma_{\text{vis}}$ applied to headway $h_{\text{safe}}$.
- `STALE`: Telemetry age $> 300\text{ ms}$ $\implies$ Speed clamped to visual sightline crawl; HMI displays yellow watermark.
- `MISSING`: Telemetry age $> 500\text{ ms}$ or null signal $\implies$ Visibility floored to $8.0\text{ m}$; fail-safe crawl enforced.
- `STUCK`: Floating point value repeated identical $> 10$ cycles $\implies$ Flagged degraded; driver warned.
- `OUTLIER`: Physically impossible value ($\Delta v / \Delta t > 9.81\text{ m/s}^2$) $\implies$ Sample rejected; Kalman dead-reckoning used.
- `INCONSISTENT`: Left/Right wheel speed disagreement or IMU vs. wheel speed mismatch $> 25\%$ $\implies$ Minimum speed adopted; slip warning issued.
- `UNKNOWN`: Uninitialized state $\implies$ Conservative default safe mode.

---

## 4. Communication & RF Architecture (Phase H5)

### Hardware Reality vs. Research Modeling
- **Physical Prototype Hardware:** **Semtech SX1278 (Ra-02) LoRa Transceiver** operating under Chirp Spread Spectrum (CSS) frequency modulation at 433.0 MHz.
- **Research Infrastructure Simulation:** Direct Sequence Spread Spectrum (DSSS) Pseudo-Noise (PN) Gold Code cross-correlation gateway selector.
- **Link State Transitions:**
  - `CONNECTED`: $\text{RSSI} > -95\text{ dBm}$, $\text{SNR} > 0\text{ dB}$, $\text{Packet Loss} < 5\%$.
  - `DEGRADED`: $-110\text{ dBm} < \text{RSSI} \le -95\text{ dBm}$ or $\text{Packet Loss} \ge 10\%$.
  - `HANDOVER_PENDING`: Candidate gateway correlation beats current gateway by $\ge 0.18$ for 5 consecutive cycles.
  - `DISCONNECTED`: Silence $> 500\text{ ms}$.
  - `NO_GATEWAY`: All reachable gateways below correlation floor ($0.65$).
