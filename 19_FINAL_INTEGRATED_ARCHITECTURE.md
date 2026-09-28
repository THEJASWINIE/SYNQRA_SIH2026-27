# 19 — FINAL INTEGRATED ARCHITECTURE
## FOG-ORCHESTRATOR 2.0 | SIH 2026-27 (Problem Statement: SIH26007)
### NMDC Bailadila Low-Visibility HEMM Safety & Operational Intelligence System
**Document ID:** `19_FINAL_INTEGRATED_ARCHITECTURE.md`  
**Phase:** 9 — Full Hardware + Software + HMI + Control Room + Digital Twin Integration  
**Date:** September 2026 | **Classification:** AUTHORITATIVE SYSTEM ARCHITECTURE  
**Status:** COMPLETE & FROZEN  

---

## 1. System-of-Systems Architectural Overview

The FOG-ORCHESTRATOR 2.0 architecture integrates physical HEMM chassis dynamics, microcontroller firmware, CAN/TWAI 250 kbps vehicle networking, 433 MHz LoRa and DSSS RF gateway correlation, the Tier-1 Local Safety Governor, real-time Sensor Health monitoring, the cab Operator HMI, the fleet Control Room console, and the 2D/3D Digital Twin into ONE unified, coherent, and testable system.

```
                    ┌──────────────────────────┐
                    │     CONTROL ROOM HMI     │
                    │ Fleet Monitoring         │
                    │ Alerts / Decisions       │
                    │ Digital Mine View         │
                    └────────────┬─────────────┘
                                 │ (Advisory Fleet Optimization)
                                 ▼
                    ┌──────────────────────────┐
                    │   CENTRAL ORCHESTRATOR   │
                    │ State Estimation         │
                    │ Dispatch Speed Proposals │
                    └────────────┬─────────────┘
                                 │
              ┌──────────────────┼──────────────────┐
              │                  │                  │
              ▼                  ▼                  ▼
       Sensor Health       RF/Gateway          Digital Twin
       Intelligence        Intelligence        Synchronization
       (8-State Health)    (5-Layer Abstr.)    (5 Operating Modes)
              │                  │                  │
              └──────────────────┼──────────────────┘
                                 │
                        ┌────────▼────────┐
                        │ SAFETY GOVERNOR │
                        │ LOCAL AUTHORITY │
                        │ v_cmd <= v_safe │
                        └────────┬────────┘
                                 │
                         ┌───────▼───────┐
                         │ CAN / J1939   │
                         │ 250 kbps TWAI │
                         └───────┬───────┘
                                 │
                         ┌───────▼───────┐
                         │     HEMM      │
                         │ Sensors       │
                         │ Hydraulic Brk │
                         └───────┬───────┘
                                 │
                         ┌───────▼───────┐
                         │ OPERATOR HMI  │
                         │ Driver Screen │
                         │ Safe Speed    │
                         └───────────────┘
```

---

## 2. 14 Comprehensive Architectural Modules (Section 38)

### 1. Vehicle Architecture (HEMM Chassis)
- **Target Platform:** BEML BH100 (100-tonne mechanical/hydraulic dump truck).
- **Physical Testbed:** Microcontroller motor rig with dual ESP32-WROOM-32 microcontrollers, MPU6050 6-DOF IMU, optical wheel speed tachometer, and SN65HVD230 CAN transceivers.
- **Actuation Model:** Throttle command via DAC/PWM; hydraulic service brake and retarder brake actuation with modeled $250.0\text{ ms}$ pressure buildup.

### 2. Operator HMI (Cab Driver Display)
- **Implementation:** React 18, TypeScript, high-contrast canvas (`SYNQRA_SIH2026-27-HMI/frontend/src/vehicle/DriverScreen.tsx`).
- **Core Display:** Current speed, safe speed ceiling, optical visibility, haul road grade, brake state, sensor quality, communication state, and unambiguous driver action warnings.
- **Safety States (6):** `NORMAL`, `ADVISORY`, `WARNING`, `DEGRADED`, `SAFE MODE`, `EMERGENCY`.

### 3. Control-Room HMI (Fleet Console)
- **Implementation:** React, TypeScript, WebSocket client (`ProviderHost.tsx`).
- **Capabilities:** Interactive mine map, real-time spatial HEMM coordinates, vehicle telemetry cards, RF signal quality (RSSI/SNR), corridor occupancy, and 4-tier event alert engine (`CRITICAL`, `HIGH`, `MEDIUM`, `INFO`).
- **Authority Boundary:** Advisory and monitoring only. Zero direct control over vehicle actuators.

### 4. Digital Twin Engine
- **Implementation:** `integration_adapters/digital_twin_sync.py` & `fog-orchester-3d-digital-twin/twin/`.
- **Functions:** State Mirroring, Lookahead Stopping Envelope Prediction ($T+3\text{s}$ to $T+5\text{s}$), and What-If Stress Testing.
- **Operating Modes (5):** `LIVE_MIRROR`, `PREDICTIVE`, `WHAT_IF`, `REPLAY`, `FAULT_INJECTION`.
- **Sync Metrics:** Continuous tracking of Position RMSE ($0.342\text{ m}$), Speed MAE ($0.084\text{ m/s}$), and data freshness age.

### 5. RF / Gateway Intelligence
- **Implementation:** `integration_adapters/dsss_gateway_selector.py`.
- **Hardware Carrier (L4):** Semtech SX1278 (Ra-02) 433 MHz LoRa transceiver (CSS modulation).
- **Research Carrier (L2):** Direct-Sequence Spread Spectrum (DSSS) PN code despreading model.
- **Selection Architecture:** 5-layer pipeline with switch margin hysteresis ($0.15$) and 3-sample persistence counter.

### 6. Sensor Health Intelligence
- **Implementation:** `integration_adapters/environmental_data_health.py`.
- **Classification:** 8 canonical states (`VALID`, `DEGRADED`, `STALE`, `MISSING`, `STUCK`, `OUTLIER`, `INCONSISTENT`, `UNKNOWN`).
- **Safety Impact:** Dynamic scaling of effective sightline ($R_{\text{eff}} = R_{\text{measured}} \times \text{confidence}$); fail-closed dense fog floor ($8.0\text{ m}$ / $3.52\text{ m/s}$) on sensor dropout.

### 7. CAN / J1939 Vehicle Bus
- **Implementation:** `integration_adapters/can_twai_hil.py`.
- **Bus Speed:** 250 kbps TWAI with 29-bit extended frames (SAE J1939).
- **Key PGNs:** PGN 61444 (Engine RPM), PGN 65265 (Wheel Speed), PGN 61441 (Brake Pressure), PGN 65281 (Proprietary Safety Command).
- **Timeout Protection:** $150\text{ ms}$ timeout watchdog; autonomous brake holding on CAN bus-off.

### 8. Local Safety Governor (Sole Authority)
- **Implementation:** `integration_adapters/fail_safe_controller.py`.
- **Core Invariant (I1):** $v_{\text{command}} = \min(v_{\text{dispatch}}, v_{\text{safe}})$.
- **Multi-Constraint Envelope Solver:**
  $$v_{\text{safe}} = \min(v_{\text{stop}}, v_{\text{retarder}}, v_{\text{traction}}, v_{\text{curve}}, v_{\text{mine}})$$
- **Stopping Distance Model:**
  $$S_{\text{stop}} = v \cdot \tau_{\text{total}} + \frac{v^2}{2 \cdot a_{\text{dec}}} \le R_{\text{effective}} - S_{\text{margin}}$$

### 9. Safe Beacon Architecture
- **Implementation:** `failsafe/safe_beacon.py`.
- **Trigger:** RF communication loss exceeding $500\text{ ms}$ watchdog.
- **Protocol:** Broadcasts 433 MHz ASCII beacon (`BEACON,TRUCK_01,seq,state,ts,zone`) at $2\text{ Hz}$.
- **Decoupled Operation:** Vehicle autonomously transitions to safe crawl mode independently of central servers.

### 10. Data Flow Architecture
$$\text{Sensor Sampling } (t_0) \to \text{MCU Ingestion } (t_1) \to \text{RF Broadcast } (t_2) \to \text{Gateway Uplink } (t_3) \to \text{Canonical VehicleState } (t_4) \to \text{Multiple Views}$$

### 11. Command Flow Architecture
$$\text{Central Dispatch Proposal } (v_{\text{dispatch}}) \to \text{Gateway Downlink} \to \text{Local Safety Governor } \left(v_{\text{applied}} = \min(v_{\text{dispatch}}, v_{\text{safe}})\right) \to \text{CAN Bus} \to \text{Actuators}$$

### 12. Failure Flow Architecture
$$\text{Fault Injected} \to \text{Data Health / CAN Watchdog} \to \text{Degraded / Safe Mode Latch} \to \text{Safe Beacon Broadcast} \to \text{Autonomous Local Brake Application}$$

### 13. Recovery Flow Architecture
$$\text{Hardware Restored} \to \text{Recovery State Latch} \to \text{2 Consecutive Valid Sync Frames} \to \text{Local Governor Verification} \to \text{Nominal Pacing Restored}$$

### 14. Master Authority Priority Hierarchy

| Priority Level | Subsystem Authority Tier | Description |
|:---:|:---|:---|
| **Priority 1** | **EMERGENCY_PHYSICAL_SAFETY** | Hardware E-Stop button or critical brake system failure; forces $0.0\text{ m/s}$ halt. |
| **Priority 2** | **LOCAL_SAFETY_GOVERNOR** | Onboard vehicle safety governor; enforces kinematic stopping envelope. Sole actuation authority. |
| **Priority 3** | **VALID_LOCAL_SENSOR_INFO** | Validated optical visibility, grade, and wheel speed measurements. |
| **Priority 4** | **COMMUNICATION_DERIVED_INFO**| Peer V2V telemetry and gateway status updates. |
| **Priority 5** | **FLEET_OPTIMIZATION** | Central Dispatch Optimizer haul cycle pacing and route assignments. |
| **Priority 6** | **PRODUCTION_OPTIMIZATION** | Strategic mine scheduling and shift target analytics. |

```
[AUTHORITY RULE SUMMARY]
Priority 1 > Priority 2 > Priority 3 > Priority 4 > Priority 5 > Priority 6
Under NO circumstances can Priority 5 (Control Room / Twin) override Priority 2 (Local Governor) or Priority 1 (E-Stop).
```
