# HMI TRUTH MATRIX & PHYSICAL REALITY REGISTER
**FOG-ORCHESTRATOR 2.0 — Final Presentation Integration Attack**
**Document ID:** HMI-TRUTH-01  
**Status:** VERIFIED, RIGID & AUTHORITATIVE  
**Scope:** Definitive Ground Truth for Sensors, Parameters, Calibration, Safety Equations & Open Physical Gates

---

## 1. Physical Chassis Hardware Specifications

| Parameter | Vehicle A (`TRUCK_01`) | Vehicle B (`TRUCK_02`) | Verification Standard & Provenance |
| :--- | :--- | :--- | :--- |
| **Chassis Role** | Lead Autonomous Dumper | Following Autonomous Dumper | Field deployment role |
| **Microcontroller** | ESP32-WROOM-32 (240 MHz, Dual Core) | ESP32-WROOM-32 (240 MHz, Dual Core) | Physical Hardware Verified |
| **Motor Actuation** | Passive testbench / Rolling chassis | TB6612FNG Dual H-Bridge Driver | Physical Hardware Fitted (B) |
| **Inertial Measurement** | MPU6050 (6-DOF Accel + Gyro) | MPU6050 (6-DOF Accel + Gyro) | I2C Address `0x68`, Verified |
| **Wheel Encoder Sensor** | LM393 Optical Slot Comparator | LM393 Optical Slot Comparator | Digital Interrupt Pin `GPIO 18` |
| **Physical Disc Slots** | **42 physical slots** | **43 physical slots** | **Microscopic / Physical Count** |
| **Wheel Diameter ($D$)** | $0.060\text{ m}$ ($60\text{ mm}$) | $0.060\text{ m}$ ($60\text{ mm}$) | Vernier Caliper Measurement |
| **Wheel Circumference ($C$)** | $0.188496\text{ m}$ ($\pi \times D$) | $0.188496\text{ m}$ ($\pi \times D$) | Direct Geometry Calculation |
| **Odometry Divisor ($K_{cal}$)** | **$34.58\text{ pulses/revolution}$** | **$34.58\text{ pulses/revolution}$** | **Empirical Odometry Calibration** |
| **Linear Pulse Resolution** | $0.005451\text{ m/pulse}$ ($5.45\text{ mm/pulse}$) | $0.005451\text{ m/pulse}$ ($5.45\text{ mm/pulse}$) | $\frac{C}{K_{cal}} = \frac{0.1885}{34.58}$ |
| **Wi-Fi Telemetry** | 802.11 b/g/n (HTTP POST `/api/hardware/telemetry`) | 802.11 b/g/n (HTTP POST `/api/hardware/telemetry`) | Physically Demonstrated |
| **LoRa Telemetry** | SX1278 433 MHz SPI Module | SX1278 433 MHz SPI Module | Physically Demonstrated |
| **GNSS Module** | **NOT FITTED ON CHASSIS** | **NOT FITTED ON CHASSIS** | **Prototype Reality** |
| **V2I Roadside Unit** | **NO PHYSICAL RSU** | **NO PHYSICAL RSU** | **Prototype Reality** |
| **Motor Tachometer** | **NOT INSTRUMENTED** | **NOT INSTRUMENTED** | **Prototype Reality** |

> [!IMPORTANT]
> **CRITICAL SCIENTIFIC DISTINCTION:**
> $34.58$ is **NOT** the physical slot count of the disc.
> The physical disc on Vehicle A has **42 slots**, and Vehicle B has **43 slots**.
> $K_{cal} = 34.58\text{ pulses/rev}$ is an empirical calibration factor determined by rolling the vehicle over measured distances to account for tire squish, optical gate hysteresis, and chassis geometry.
> Never describe $34.58$ as "PPR = 34.58" or "34.58 slots".

---

## 2. The 5 Open Physical Gates (Unclosed in Software)

To ensure zero academic dishonesty and zero fabrication before hostile SIH evaluators, the following 5 gates remain explicitly classified as **OPEN PHYSICAL GATES**:

| Gate Identifier | Target Capability | Current Software / Firmware Status | Open Physical Verification Requirement | Current HMI Presentation |
| :--- | :--- | :--- | :--- | :--- |
| **GATE-01** | **RF Failover End-to-End Ingestion** | Failsafe controller, packet deduplication, and serial gateway reader implemented. | Cutting Wi-Fi during live physical motion and observing seamless continuation over 433 MHz LoRa in backend twin. | `AVAILABLE — FAILOVER VALIDATION PENDING` |
| **GATE-02** | **Safe Beacon Gateway Ingestion** | Firmware dropout watchdog ($>3.0\text{ s}$ Wi-Fi loss $\to$ emergency beacon broadcast) implemented. | Physical SX1278 hardware receiver capturing and logging autonomous `BEACON` packet on Wi-Fi loss. | `STANDBY · FIELD GATE PENDING` |
| **GATE-03** | **Floor-Distance Ground Truth Validation** | Odometry derivation ($5.45\text{ mm/pulse}$) implemented. | External physical tape-measure ground-truth run verifying cumulative distance error $<2\%$ over 5 metres. | `LOCAL ODOMETRY · UNSURVEYED CHASSIS` |
| **GATE-04** | **Dual-Vehicle Physical Closed-Loop Validation** | Both firmware compiled; backend pre-registers both trucks; twin supports multi-vehicle state. | Vehicle A and Vehicle B running simultaneously on the floor with active V2V speed clamping. | `PEER AVAILABLE / STANDBY` |
| **GATE-05** | **Physical Fog Sensor Experiment** | Meteorological optical range model and safety solver implemented. | Chamber-based physical aerosol fog test measuring actual optical beam attenuation. | `SIMULATION · INJECTED SCENARIO` |

---

## 3. Mathematical Safety Formulations & Latency Budget

### 3.1 Total System Latency Budget ($\tau_{total}$)
Safety calculations assume an authoritative worst-case latency budget:
$$\tau_{total} = \tau_{sensor} + \tau_{comm} + \tau_{decision} + \tau_{actuation}$$

- $\tau_{sensor} = 50\text{ ms}$ (Optical encoder pulse window + MPU6050 DMP sample time)
- $\tau_{comm} = 100\text{ ms}$ (Wi-Fi network transport + deduplication buffer)
- $\tau_{decision} = 50\text{ ms}$ (Central physics solver + twin state commit)
- $\tau_{actuation} = 100\text{ ms}$ (TB6612FNG PWM slew rate + motor mechanical inertia)
- **Authoritative Total:** $\tau_{total} = 300\text{ ms} = 0.300\text{ s}$

### 3.2 Stopping Distance Formula ($S_{stop}$)
$$S_{stop} = v \cdot \tau_{total} + \frac{v^2}{2 \cdot a_{dec}}$$

Where:
- $v$ = vehicle speed ($\text{m/s}$)
- $\tau_{total} = 0.300\text{ s}$
- $a_{dec}$ = effective deceleration ($\text{m/s}^2$) governed by road surface friction and grade:
  $$a_{dec} = \mu \cdot g \cdot \cos(\theta) - g \cdot \sin(\theta)$$
  ($\mu = \text{friction coefficient}$, $\theta = \text{grade in radians}$, $g = 9.80665\text{ m/s}^2$).

### 3.3 Safe Speed Multi-Constraint Solver ($v_{safe}$)
$$v_{safe} = \min\left(v_{stop}, v_{retarder}, v_{traction}, v_{curve}, v_{mine}\right)$$

Where:
- $v_{stop} = \sqrt{2 \cdot a_{dec} \cdot (V_{vis} - v \cdot \tau_{total})}$ (governed by visibility $V_{vis}$)
- $v_{retarder} = \text{thermal retarder speed ceiling on downhill grade}$
- $v_{traction} = \sqrt{\mu \cdot g \cdot R}$ (traction limit)
- $v_{curve} = \sqrt{a_{lat,max} \cdot R}$ (lateral rollover ceiling on bend radius $R$)
- $v_{mine} = 12\text{ km/h} = 3.33\text{ m/s}$ (maximum allowable mine road speed ceiling)

---

## 4. Canonical Data Provenance Vocabulary

Every displayed metric must carry one of the following authoritative provenance tokens:

| Provenance Token | Meaning & Applicability |
| :--- | :--- |
| `HARDWARE` | Directly measured by physical chassis sensors (ticks, RPM, acceleration, gyroscope). |
| `HARDWARE (derived)` | Computed from direct hardware measurements using physical wheel dimensions (e.g., odometry speed). |
| `CALCULATED / AUTHORITATIVE` | Authoritatively solved by the central physics/safety engine (e.g., $v_{safe}$, $h_{safe}$, stopping distance). |
| `SIMULATION` | Generated by the closed-loop scenario simulation engine for background vehicles. |
| `INJECTED_SCENARIO` | Environmental parameters injected for testing (e.g., fog visibility 35m, wet road $\mu=0.45$). |
| `SYNTHETIC / SCENE METRES` | Synthetic coordinate representation within the 3D digital twin scene; explicitly NOT geographic GPS. |
| `NOT_FITTED` | Capability that does not exist on the physical prototype chassis (e.g., GNSS). |
| `NOT_INSTRUMENTED` | Capability or feedback loop not measured on this hardware version (e.g., physical roadside RSU, motor tachometer). |
| `FIELD_GATE_PENDING` | Software and firmware are implemented and compiled, but awaiting final physical floor/gateway verification. |
