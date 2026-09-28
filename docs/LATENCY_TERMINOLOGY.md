# FOG-ORCHESTRATOR 2.0 — LATENCY TERMINOLOGY & DELAY BREAKDOWN
**SIH 2026-27 | PHASE H11: TIMING & COMMUNICATIONS CLASSIFICATION**  
**Lead Embedded, Robotics, Cyber-Physical Systems & Safety Integration Engineer**  
**Audit Standard:** Strict Source-of-Truth Hierarchy & Evidence Levels (L0–L5)  
**Date:** 2026-09-24  

---

## 1. Principle of Strict Timing Integrity

A critical safety pitfall in cyber-physical systems is confusing single-hop radio airtime with complete sensor-to-mechanical-brake stopping latency.

In FOG-ORCHESTRATOR 2.0, the measurement of **$38.5\text{ ms}$** represents **EXCLUSIVELY**:
$$\mathbf{RF\_AIRTIME\_COMPONENT} \quad (\text{Measured SX1278 LoRa 433 MHz Airtime at SF7, BW 125 kHz for a 32-byte payload})$$

### PROHIBITED STATEMENTS:
* $\times$ *"38.5 ms is the worst-case end-to-end command latency"* — **FALSE / UNFOUNDED**.
* $\times$ *"38.5 ms is the complete sensor-to-actuator latency"* — **FALSE / UNFOUNDED**.
* $\times$ *"38.5 ms is the vehicle stopping response"* — **PHYSICALLY IMPOSSIBLE**.
* $\times$ *"38.5 ms is the mechanical braking latency"* — **PHYSICALLY IMPOSSIBLE**.

### AUTHORITATIVE CANONICAL DEFINITIONS:
* $\checkmark$ **"Measured RF airtime component (`RF_AIRTIME_COMPONENT` = 38.5 ms)"**
* $\checkmark$ **"LoRa single-frame transmission airtime (`T_packet` = 38.5 ms)"**

---

## 2. Twelve-Stage Latency Chain Breakdown

The complete physical pathway from obstacle detection to physical vehicle stopping consists of twelve distinct physical, computational, transport, and mechanical stages:

```
[1. Sensor Sampling] ──> [2. Telemetry Ingest] ──> [3. RF Airtime] ──> [4. RF Propagation]
                                                                               │
[8. Command Transmit] <── [7. Safety Governor] <── [6. Backend Sync] <── [5. Gateway Parsing]
        │
        ▼
[9. CAN/TWAI Transport] ──> [10. Electronic Actuation] ──> [11. Brake Buildup] ──> [12. Mechanical Stop]
```

### Stage Definitions & Classifications

| Stage # | Stage Name | Description | Value (ms) | Classification | Evidence Level |
| :---: | :--- | :--- | :---: | :---: | :---: |
| **1** | **Sensor Latency ($\tau_{\text{sensor}}$)** | Optical encoder integration window / MPU6050 I2C sample period / LiDAR/Radar filtering. | `20.0 - 100.0` | `MEASURED` (Bench) | **L3** |
| **2** | **Telemetry Generation Latency** | ESP32 ASCII packet serialization (`buildOwnState()`) and interrupt servicing. | `0.45` | `MEASURED` (Scope) | **L3** |
| **3** | **RF Airtime (`RF_AIRTIME_COMPONENT`)** | Semtech SX1278 physical chirp transmission over 433 MHz (SF7, BW 125 kHz, CR 4/5, 32 bytes). | **`38.5`** | **`MEASURED` (Bench)** | **L3** |
| **4** | **RF Propagation Latency** | Electromagnetic wave travel time over haul road distance ($d \le 1.5\text{ km}$). | `0.005` ($< 5\ \mu\text{s}$) | `CALCULATED` ($d/c$) | **L1** |
| **5** | **Gateway Processing Latency** | ESP32 LoRa Gateway packet reception, CRC check, and WiFi/UART formatting. | `2.10` | `MEASURED` (Bench) | **L3** |
| **6** | **Backend Processing Latency** | FastAPI REST ingestion, sequence verification, and Digital Twin state store projection. | `1.40` | `MEASURED` (Host) | **L2** |
| **7** | **Safety Governor Computation** | Multi-constraint safe speed root calculation ($v_{\text{safe}} = \min(v_{\text{stop}}, v_{\text{retarder}}, \dots)$). | `0.18` | `MEASURED` (Host) | **L2** |
| **8** | **Command Transmission Latency** | Downlink command serialization and network dispatch to vehicle controller. | `1.85` | `MEASURED` (Bench) | **L3** |
| **9** | **CAN/TWAI Transport (`CAN_TWAI_COMPONENT`)** | J1939 29-bit CAN frame arbitration and transfer on 250 kbps TWAI bus (Priority 0/3). | `1.82 - 2.68` | `MEASURED` (TWAI HIL) | **L3** |
| **10** | **Actuator Electronic Latency** | ESP32 GPIO toggle, TB6612FNG gate charge time, or OEM solenoid valve driver trigger. | `0.05` | `MEASURED` (Spec) | **L3** |
| **11** | **Mechanical Brake Pressure Buildup** | Hydraulic/pneumatic fluid pressure propagation to wet disc brake calipers. Prototype: electric motor back-EMF / dynamic braking. | `12.0` (Scale)<br>`250.0 - 400.0` (HEMM) | `MODELLED` (Physics)<br>`ASSUMED` (OEM) | **L3 (Scale)**<br>**L5 (HEMM Pending)**|
| **12** | **Physical Vehicle Deceleration** | Pure kinematic stopping distance travel ($d = v^2 / 2a_{\text{dec}}$) until forward velocity reaches zero. | Dynamic ($f(v, G, \mu)$) | `MODELLED` (Physics) | **L2 / L4** |

---

## 3. Strict Boundary Rules for Timing Reports

1. **Never sum incompatible timing domains:**
   - Communications round-trip latency ($\tau_{\text{comm}} = \tau_{\text{air}} + \tau_{\text{gw}} + \tau_{\text{proc}}$) must NEVER be conflated with total stopping sight distance reaction time ($\tau_{\text{total}} = \tau_{\text{sensor}} + \tau_{\text{comm}} + \tau_{\text{decision}} + \tau_{\text{brake}}$).
2. **Explicit Labeling:**
   - Every timing figure in reports, code comments, and publications MUST carry one of:
     - `MEASURED_ON_BENCH` (L3)
     - `MEASURED_ON_VEHICLE` (L4)
     - `MODELLED_FROM_SPEC` (L2/L3)
     - `ENGINEERING_ASSUMPTION` (L1)
     - `NOT_MEASURED` (L0)
3. **HEMM Chassis Demarcation:**
   - Hydraulic brake line propagation delays of 300 ms on a 165-tonne dump truck are **ENGINEERING ASSUMPTIONS** based on ISO 3450 / SAE J1473 literature until measured on an active BEML/CAT chassis at an open-cast mine site.
