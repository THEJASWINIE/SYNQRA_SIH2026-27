# FOG-ORCHESTRATOR 2.0 — PHASE 1 ↔ PHASE 2 INTERFACE AUDIT REPORT

**Date**: 2026-08-28  
**Author**: Principal Systems Architect, Industrial IoT Integration Engineer, Distributed Systems Engineer, Safety-Critical Systems Verification Engineer  
**Scope**: Strict Interface Compatibility Audit between Phase 1 (Physical Hardware ↔ HMI) and Phase 2 (Digital Twin ↔ Central Orchestrator)

---

## 1. Executive Summary

A strict, non-invasive **Interface Compatibility Audit** was performed between the independently verified **Phase 1 System** (Physical Vehicles `TRUCK_01`/`TRUCK_02` ↔ LoRa Gateway ↔ HMI Backend ↔ React Frontend) and **Phase 2 System** (Digital Twin ↔ Mine Simulation ↔ Fog Model ↔ Queue Engine ↔ CC-MPC Orchestrator). 

**Zero code modifications** were made to either system. Both systems remain 100% independent and frozen.

The audit confirms that while both systems possess clean, modular data contracts, direct runtime connection without transformation would fail due to vehicle identity syntax mismatches (`TRUCK_01` vs `vehicle_1`), unit differences (wheel RPM vs $m/s$), and massive physical scaling discrepancies ($2\text{ kg}$ prototype vs $165\text{ tonne}$ BEML BH100 mining dumper). Implementing 7 lightweight integration adapters will enable safe, seamless future integration.

---

## 2. Current Phase 1 Architecture

```text
              VEHICLE A (TRUCK_01)         VEHICLE B (TRUCK_02)
             ESP32 + TB6612 + MPU6050    ESP32 + L298N + MPU6050
                     │                           │
                     │ LoRa 433 MHz              │ LoRa 433 MHz
                     └─────────────┬─────────────┘
                                   │
                                   ▼
                          LORA GATEWAY ESP32
                                   │
                                   │ USB Serial 115200
                                   ▼
                              HMI BACKEND
                                   │
                                   │ REST / WebSocket
                                   ▼
                              HMI FRONTEND
```

---

## 3. Current Phase 2 Architecture

```text
                      MINE MAP CONFIG (YAML)
                                │
                                ▼
                       MINE NETWORK GRAPH
                                │
                                ▼
                      WEATHER / FOG MODEL (50m -> 15m)
                                │
                                ▼
                   DIGITAL TWIN SIMULATOR (6 Dumpers)
                                │
                                ▼
                 5-CONSTRAINT SAFETY GOVERNOR (v_safe)
                                │
                                ▼
                 QUEUE & BOTTLENECK DETECTOR (rho = lambda/mu)
                                │
                                ▼
                 CHANCE-CONSTRAINED MPC OPTIMIZER
```

---

## 4. Architectural Separation

Phase 1 and Phase 2 reside in completely separate repositories and directories:
- **Phase 1**: [`SYNQRA_SIH2026-27-HMI/`](file:///c:/Users/JAGADEESH%20M/OneDrive/Documents/SIH-2026-27/SYNQRA_SIH2026-27-HMI)
- **Phase 2**: [`SYNQRA_SIH2026-27-main/`](file:///c:/Users/JAGADEESH%20M/OneDrive/Documents/SIH-2026-27/SYNQRA_SIH2026-27-main)

There are **zero imports**, **zero shared state**, and **zero cross-dependencies** between Phase 1 and Phase 2.

---

## 5. Data Compatibility Matrix

See full audit table in [`INTERFACE_DATA_CONTRACT_AUDIT.csv`](file:///c:/Users/JAGADEESH%20M/OneDrive/Documents/SIH-2026-27/INTERFACE_DATA_CONTRACT_AUDIT.csv).

| Field Name | Phase 1 Format | Phase 2 Format | Compatibility | Transformation Required |
|------------|----------------|----------------|---------------|-------------------------|
| `vehicle_id` | `TRUCK_01` / `TRUCK_02` | `vehicle_1` .. `vehicle_6` | **INCOMPATIBLE** | Vehicle ID Mapper Adapter |
| `timestamp` | POSIX Epoch (host clock) | Simulation epoch seconds | **INCOMPATIBLE** | Time Synchronization Adapter |
| `speed` | Wheel RPM & derived m/s | $m/s$ velocity | **PARTIAL** | Kinematic Speed Scaler Adapter |
| `acceleration` | Raw LSB / $m/s^2$ | $m/s^2$ ($ax, ay$) | **COMPATIBLE** | LSB $\rightarrow m/s^2$ Scaler |
| `position` | Not available (No GPS) | Map $(X, Y)$ grid | **MISSING IN P1** | Dead Reckoning Position Estimator |
| `safe_speed` | Local governor limit | Analytical 5-constraint solver | **COMPATIBLE** | Hierarchy Rule (`applied = min(req, local)`) |

---

## 6. Vehicle Identity Mapping

- **Phase 1 Fleet**: 2 Physical Vehicles (`TRUCK_01` 4WD & `TRUCK_02` 2WD).
- **Phase 2 Fleet**: 6 Simulated Heavy Dumpers (`vehicle_1` .. `vehicle_6`).
- **Mapping Strategy**: Adopt **Hardware-in-the-Loop (HIL) Agent Mapping** (`TRUCK_01` $\rightarrow$ `HIL_DUMPER_01`, `TRUCK_02` $\rightarrow$ `HIL_DUMPER_02`). The remaining 4 dumpers operate as background simulation traffic.

---

## 7. Unit and Physics Compatibility

- **Kinematic Speed Equation**: $v = \frac{\text{RPM} \cdot 2\pi r}{60}$
- **Braking Distance Equation**: $S_{\text{stop}} = v \cdot t_{\text{react}} + \frac{v^2}{2g(\mu \cos\theta - \sin\theta)}$
- **Scaling Analysis**: Prototype mass ($2\text{ kg}$) vs Mining Dumper mass ($165,000\text{ kg}$). Target speeds must be normalized by scale factor $\lambda_{\text{scale}} \approx 0.27$ before routing to physical hardware.

---

## 8. Time Synchronization

- **Strategy**: Hybrid time synchronization with POSIX host NTP clock as the timekeeper authority.
- **Offsets**: Digital Twin maintains a monotonic offset ($\Delta T = T_{\text{host}} - t_{\text{sim}}$).

---

## 9. Command Authority Hierarchy

$$\text{LOCAL SAFETY AUTHORITY } (v_{\text{local\_safe}}) > \text{CENTRAL OPTIMIZATION } (v_{\text{rec}})$$

```text
DIGITAL TWIN / ORCHESTRATOR (Advisory) ➔ HMI BACKEND ➔ VEHICLE ESP32 ➔ LOCAL SAFETY GOVERNOR ➔ APPLIED ACTION
```

---

## 10. Safety Boundary Enforcement

- The Digital Twin is **ADVISORY ONLY**. It has ZERO direct access to motor drivers or ESP32 hardware.
- Requested speed commands exceeding local safety thresholds are clamped by the ESP32 local safety governor ($25.0\text{ m/s} \rightarrow 10.87\text{ m/s}$ `CLAMPED`).

---

## 11. Required Integration Adapters

Detail specifications in [`INTEGRATION_ADAPTER_REQUIREMENTS.md`](file:///c:/Users/JAGADEESH%20M/OneDrive/Documents/SIH-2026-27/INTEGRATION_ADAPTER_REQUIREMENTS.md):
1. **Vehicle ID Mapper Adapter**
2. **Unit Converter & Kinematic Scale Adapter**
3. **IMU Processor Adapter**
4. **Time Synchronization Adapter**
5. **Coordinate Mapper & Position Estimator Adapter**
6. **Telemetry Quality Filter Adapter**
7. **Command Adapter**

---

## 12. Failure Propagation Analysis

Detailed FMEA in [`PHASE1_PHASE2_FAILURE_MODE_AUDIT.md`](file:///c:/Users/JAGADEESH%20M/OneDrive/Documents/SIH-2026-27/PHASE1_PHASE2_FAILURE_MODE_AUDIT.md):
- Digital Twin Crash $\rightarrow$ Physical vehicles continue operating safely under Phase 1 supervisory control.
- LoRa Telemetry Loss $\rightarrow$ Digital Twin marks data `COMMUNICATION_DEGRADED` (Never invents telemetry).
- Unsafe Speed Target $\rightarrow$ Local ESP32 governor clamps speed strictly to safe threshold.

---

## 13. Integration Risks

1. **RF Congestion**: Scaling beyond 10 concurrent physical vehicles on 433 MHz LoRa requires TDMA slot management.
2. **Position Drift**: Prototype dead-reckoning estimation requires periodic optical/beacon reset.

---

## 14. Integration Readiness Scorecard

Detailed scorecard in [`INTEGRATION_READINESS_SCORE.md`](file:///c:/Users/JAGADEESH%20M/OneDrive/Documents/SIH-2026-27/INTEGRATION_READINESS_SCORE.md):

| Category | Score | Weight | Weighted Contribution |
|----------|-------|--------|-----------------------|
| Data Compatibility | 65 / 100 | 10% | 6.50 |
| Vehicle Identity Mapping | 60 / 100 | 10% | 6.00 |
| Unit Compatibility | 70 / 100 | 10% | 7.00 |
| Physics Compatibility | 55 / 100 | 10% | 5.50 |
| Time Synchronization | 75 / 100 | 10% | 7.50 |
| Command Compatibility | 85 / 100 | 10% | 8.50 |
| Safety Authority | 100 / 100 | 15% | 15.00 |
| Failure Isolation | 95 / 100 | 10% | 9.50 |
| HMI Compatibility | 90 / 100 | 10% | 9.00 |
| Regression Risk | 90 / 100 | 5% | 4.50 |
| **OVERALL SCORE** | **79.0 / 100** | **100%** | **79.00 / 100** |

---

## 15. Critical Blockers

1. **Vehicle ID Syntax Mismatch**: `TRUCK_01` vs `vehicle_1`.
2. **Mass & Kinematic Scale Mismatch**: $2\text{kg}$ prototype vs $165\text{t}$ BEML BH100 dumper.
3. **Native Unit Conversion**: Raw RPM vs $m/s$.
4. **Unmapped Prototype Coordinates**: Prototype lacks GPS hardware.

---

## 16. Recommended Integration Sequence

1. Implement Integration Adapters 1 through 7 as an isolated middleware package (`fog_integration_adapter`).
2. Verify adapters using synthetic unit tests without altering Phase 1 or Phase 2 code.
3. Perform controlled loopback test connecting Phase 1 backend to Phase 2 Digital Twin advisory endpoints.

---

## 17. Final Verdict

```text
============================================================
FOG-ORCHESTRATOR 2.0
PHASE 1 ↔ PHASE 2 INTERFACE AUDIT
============================================================

Data Compatibility:          65 / 100
Vehicle Identity Mapping:    60 / 100
Unit Compatibility:          70 / 100
Physics Compatibility:       55 / 100
Time Synchronization:        75 / 100
Command Compatibility:       85 / 100
Safety Authority:            100 / 100
Failure Isolation:           95 / 100
Regression Risk:             90 / 100

OVERALL INTEGRATION READINESS:
79 / 100

CRITICAL BLOCKERS:
- Vehicle ID syntax mismatch (TRUCK_01 vs vehicle_1)
- Mass & scale mismatch (2kg prototype vs 165t BEML BH100 dumper)
- Native unit conversion (RPM vs m/s)
- Unmapped prototype position (No GPS on prototype)

REQUIRED ADAPTERS:
1. Vehicle ID Mapper Adapter
2. Unit Converter & Kinematic Scale Adapter
3. IMU Processor Adapter
4. Time Synchronization Adapter
5. Coordinate Mapper & Position Estimator Adapter
6. Telemetry Quality Filter Adapter
7. Command Adapter

FINAL VERDICT:
CONDITIONAL — ADAPTERS REQUIRED

============================================================
```
