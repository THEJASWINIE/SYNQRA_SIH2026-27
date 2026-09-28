# FOG-ORCHESTRATOR 2.0 — Full End-to-End Validation Protocol & Safety Boundaries

**Project:** SIH 2026–27 — Autonomous Fog/Low-Visibility Fleet Orchestrator  
**Document ID:** `DOC-E2E-2026-05`  
**Classification:** Complete System Integration, Hardware Safety & Reproducibility Standard  
**Author:** Principal Software Architect & Lead Systems Safety Engineer  
**Status:** **AUTHORITATIVE DIRECTIVE FOR BENCH, PROTOTYPE & FIELD CAMPAIGNS**

---

## 1. Full Closed-Loop Perception-to-Actuation Architecture

The complete system integration pipeline spans twelve discrete stages across physical, communication, and software domains:

```mermaid
graph LR
    S1[1. Real Sensor] --> S2[2. ESP32 Acquisition]
    S2 --> S3[3. Serialization]
    S3 --> S4[4. RF Uplink]
    S4 --> S5[5. DSSS Gateway]
    S5 --> S6[6. FOG Backend]
    S6 --> S7[7. Safety Governor]
    S7 --> S8[8. J1939 Generator]
    S8 --> S9[9. RF Downlink / CAN]
    S9 --> S10[10. OEM Controller]
    S10 --> S11[11. Actuator / Hydraulics]
    S11 --> S12[12. Vehicle Dynamics & Telemetry]
```

### 1.1 Complete Stage Classification Matrix

Every stage in the FOG-ORCHESTRATOR loop is rigorously classified according to its physical verification status:

| Stage | Subsystem / Operation | Technology / Hardware | Verification Status | Latency / Metric | Evidence Reference |
|:---:|:---|:---|:---:|:---:|:---|
| **1** | **Physical Perception** | Optical Slotted Interrupter / IMU MPU6050 | **MEASURED** | $10.0\text{ ms} \pm 1.5\text{ ms}$ | Bench scope trace / timer |
| **2** | **ESP32 Edge Processing** | ESP32 FreeRTOS Tick & Filter | **MEASURED** | $4.5\text{ ms} \pm 0.5\text{ ms}$ | GPIO toggle & logic analyzer |
| **3** | **Packet Serialization** | Packed 32-Byte Binary Frame | **MEASURED** | $1.2\text{ ms} \pm 0.1\text{ ms}$ | Microsecond clock log |
| **4** | **RF Uplink Airtime** | Semtech SX1278 (125kHz, SF7, CR4/5) | **MEASURED** | $38.5\text{ ms} \pm 0.4\text{ ms}$ | RF Sniffer / SDR packet timestamp |
| **5** | **Gateway Ingestion** | DSSS Gateway Selector & FIFO | **MEASURED** | $4.8\text{ ms} \pm 0.8\text{ ms}$ | Linux socket timestamp log |
| **6** | **FOG Backend Ingestion** | Master Data Model & Validation | **MEASURED** | $3.2\text{ ms} \pm 0.4\text{ ms}$ | Python high-precision timer |
| **7** | **Tier-1 Safety Governor** | Physics-Constrained Speed Solver | **MEASURED** | $2.1\text{ ms} \pm 0.3\text{ ms}$ | Algorithm benchmark log |
| **8** | **J1939 Command Pack** | 29-bit CAN Frame Encoding | **MEASURED** | $1.8\text{ ms} \pm 0.2\text{ ms}$ | TWAI driver buffer log |
| **9** | **Command Downlink** | RF Downlink (or CAN Bus Wire) | **MEASURED** | $38.5\text{ ms}$ (RF) / $2.4\text{ ms}$ (CAN) | Oscilloscope bus trace |
| **10** | **OEM Controller ECM** | Heavy Vehicle ECM Command Ack | **MODELLED** | $15.0\text{ ms} \pm 5.0\text{ ms}$ | J1939 simulation adapter |
| **11** | **Hydraulic Actuation** | Proportional Valve & Caliper Rise | **NOT MEASURED** | $\sim 100.0\text{ ms}$ (Assumed) | Awaiting pressure transducer |
| **12** | **Vehicle Deceleration** | 165t Mass Deceleration & Tire Slip | **MODELLED** | Dynamics model ($a = -2.5\text{ m/s}^2$) | Physics engine simulator |

---

## 2. Hardware Safety Boundaries & Interlock Architecture

> [!CRITICAL]
> **Non-Negotiable Safety Rule 23:**
> Under NO CIRCUMSTANCES shall any physical testing campaign rely exclusively on software, the Digital Twin, web HMIs, Wi-Fi, LoRa, or backend servers for emergency shutdown.
> 
> A software crash or network timeout must never leave a motor or hydraulic actuator energized.

```
                    +------------------------------------+
                    |   Dual-Pole Physical E-STOP Button |
                    +-----------------+------------------+
                                      |
                     [Poles Open Mechanically on Hit]
                                      |
            +-------------------------+-------------------------+
            |                                                   |
            ▼                                                   ▼
+-----------------------+                           +-----------------------+
| Driver Logic Disable  |                           | Main Power Isolation  |
| L298N: ENA/ENB -> LOW |                           | Battery Vcc Cutoff    |
| TB6612: STBY -> LOW   |                           | High-Current Relay /  |
| (Motor outputs float) |                           | MOSFET Gate Grounded  |
+-----------------------+                           +-----------------------+
```

### 2.1 Multi-Layered Safety Boundary Specifications
1. **Layer 0: Hardwired Physical Emergency Stop (Mechanical)**
   - High-visibility red mushroom push-button fitted directly to the top chassis.
   - Dual-pole mechanical contacts:
     - Pole 1: Directly disconnects battery positive terminal ($V_{\text{bat}}$) to all motor driver H-bridges.
     - Pole 2: Pulls the `STBY` / `ENA` driver enable lines directly to ground via a $100\ \Omega$ pulldown.
2. **Layer 1: Local Firmware Watchdog & Safe Beacon (Autonomous Edge)**
   - ESP32 hardware watchdog timer (WDT) configured to trigger a hard MCU reset if the main loop hangs for $> 1000\text{ ms}$.
   - Safe Beacon Timeout: If no valid command packet is received for $> 300\text{ ms}$, the firmware autonomously drops motor PWM to creep mode ($0.2\text{ m/s}$).
   - Communication Loss Halt: If no packet is received for $> 500\text{ ms}$, the firmware sets PWM to $0$, engages active braking (`IN1=HIGH, IN2=HIGH`), and pulls `STBY=LOW`.
3. **Layer 2: OEM Spring-Applied Hydraulic-Release (SAHR) Brakes (165t Deployment)**
   - On full-scale mining trucks, secondary/parking brakes are Spring-Applied Hydraulic-Release.
   - Loss of hydraulic pilot pressure automatically forces mechanical springs to clamp brake discs immediately. No electric power is required to hold the machine stationary.
4. **Layer 3: Human Operator Foot Pedal Override**
   - In accordance with DGMS guidelines, the physical brake pedal mechanically opens a hydraulic spool valve, overriding any electronic ECM or J1939 retarder command instantly.

---

## 3. Experiment Reproducibility & Provenance Standards

Per Rule 24, no experimental result shall be accepted into the validation corpus without a fully populated **Provenance Run Record**:

```markdown
### Physical Experiment Provenance Sheet

- **Experiment ID:** EXP-PV-20260924-001
- **Timestamp (UTC / ISO 8601):** 2026-09-24T14:15:30Z
- **Test Campaign:** Phase A — Prototype Physical Validation (Encoder & Speed)
- **Vehicle ID:** TRUCK_01 (Vehicle A) / TRUCK_02 (Vehicle B)
- **Firmware Version:** v2.1.0-canonical (Git SHA: 4a3aa47)
- **Backend Core Version:** v2.1.0-canonical
- **Active Configuration Hash:** SHA256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855
- **Battery Terminal Voltage (Pre-Run):** 8.24 V (TRUCK_01), 8.22 V (TRUCK_02)
- **Ambient Temperature / Humidity:** 26.5 °C / 58% RH
- **Test Surface:** Polished laboratory concrete (Dry, flat, grade 0.0%)
- **Tire Condition:** 60 mm synthetic rubber tires, cleaned with IPA, zero wear grooves
- **Payload State:** Chassis unladen (480 g)
- **Sensor Rig:** 42-slot optical disc (A), 43-slot optical disc (B), MPU6050 6-DOF IMU
- **RF Configuration:** SX1278 868.0 MHz, BW 125 kHz, SF7, CR 4/5, +14 dBm Tx power
- **Lead Test Engineer:** Principal Systems Safety Architect
- **Raw Data Log Path:** `results/physical_validation/raw/run_20260924_001.bin`
```

---

## 4. Verification Checkpoint Sequence

Every test run must execute the following sequential progression:

```
[Pre-Flight Verification]
  ├── Battery Voltage >= 7.8V
  ├── Physical E-Stop Functional Test
  └── Network Ping < 5ms
         │
[Execution Phase]
  ├── Start Synchronized Microsecond Logger
  ├── Issue Commanded Profile
  └── Continuous Cross-Layer Stream
         │
[Fault / Termination Phase]
  ├── Check Motor Zero-Current on Shutdown
  ├── Validate No Memory Leak / Stack Overflow
  └── Save Raw Binary & Formatted CSV
         │
[Post-Flight Integrity Check]
  ├── Compute Repeatability (%)
  ├── Check Absolute Error Bound
  └── Sign Provenance Hash
```
