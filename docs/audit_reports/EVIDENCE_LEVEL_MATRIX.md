# EVIDENCE_LEVEL_MATRIX.md
## FOG-ORCHESTRATOR 2.0 — Pre-Physical Hostile Audit: Subsystem Evidence Levels

**Date:** 2026-09-27  
**Authoritative Status:** **AUDITED & RIGOROUSLY CLASSIFIED**  
**Classification Standard:** L1 through L5 Hierarchy (Non-Negotiable Rule 3 & Rule 23)

---

### 1. Evidence Level Definitions

To eliminate false claims of physical validation, all evidence across the project is categorized strictly according to the following 5-tier standard:

* **L1 — Source-Code Inspection:** Static inspection of source code, pinouts, algorithms, and configuration definitions.
* **L2 — Automated Software Test:** Unit tests, integration tests, and invariant property tests executed in software test runners (Vitest, Pytest).
* **L3 — HIL / Emulation:** Simulated packet streams, mock serial ports, virtual hardware emulators, and software-in-the-loop state machines.
* **L4 — Physical Bench:** Real physical hardware operating on an elevated testbench (ESP32 microcontrollers, TB6612FNG / L298N motor drivers, MPU6050 IMUs, optical encoders, LoRa transceivers). Wheels rotate, but chassis is elevated.
* **L5 — Physical Floor:** Real vehicle driving across floor, gravel, or ramp surfaces with ground-truth distance measured by an external reference (e.g. calibrated steel tape measure).

> [!IMPORTANT]
> **Strict Engineering Rule:** Under no circumstances may L1, L2, or L3 evidence be presented as physical validation. Elevated bench testing (L4) verifies electrical, protocol, and rotational sanity, but does NOT constitute ground translation validation (L5).

---

### 2. Evidence Classification Matrix

| Subsystem / Component | Current Readiness Status | Verified Evidence Levels | Highest Verified Level | Evidence Description & Limitations | Next Required Physical Level |
| :--- | :---: | :---: | :---: | :--- | :---: |
| **Vehicle A (`TRUCK_01`)** | **READY** | L1, L2, L3, L4 | **L4 (Physical Bench)** | Firmware (`sketch_aug26a.ino`) compiled and verified on physical ESP32 (COM14). L298N motor driver, optical encoder (42 slots), MPU6050, and LoRa verified on elevated bench. Zero floor motion measured. | **L5 (Physical Floor)** |
| **Vehicle B (`TRUCK_02`)** | **READY** | L1, L2, L3, L4 | **L4 (Physical Bench)** | Firmware (`VEHICLE_B_...ino`) verified on physical ESP32 (192.168.137.217). TB6612FNG motor driver, optical encoder (43 slots), MPU6050, and Wi-Fi/LoRa verified on elevated bench. Zero floor motion measured. | **L5 (Physical Floor)** |
| **Backend (FastAPI)** | **READY** | L1, L2, L3, L4 | **L4 (Physical Bench)** | FastAPI server running on port 8000. Ingests live telemetry from physical ESP32 over Wi-Fi and Gateway serial. Deduplication, boot ID tracking, and WebSocket feeds tested under 135 unit/regression tests. | **L4/L5 Bench End-to-End** |
| **Digital Twin Core** | **READY** | L1, L2, L3, L4 | **L4 (Physical Bench)** | Pygame 3D engine on port 8080. Authoritative state store maintains vehicle kinematic state, road network, and safety envelopes. Feeds live HMI projections without UI physics invention. | **L4/L5 Bench End-to-End** |
| **Operator HMI (`DriverScreen`)** | **READY** | L1, L2, L3, L4 | **L4 (Physical Bench)** | React frontend on port 5173. 1860 frontend tests passing. Displays live telemetry, separated command requested vs safe limit, and honestly shows `UNKNOWN / NOT TELEMETRIED` for unmeasured motor speed. | **L4/L5 Bench End-to-End** |
| **Control Room HMI (`OperationsOverview`)** | **READY** | L1, L2, L3, L4 | **L4 (Physical Bench)** | React frontend on port 5173. Fleet monitoring, haul road morphology, failover status. Fixed MOCK provider bug; displays honest provenance and unmeasured sensor indicators. | **L4/L5 Bench End-to-End** |
| **Encoder Calibration ($K_{\text{cal}} = 34.58$)** | **READY** | L1, L2, L3, L4 | **L4 (Physical Bench)** | Optical pulse accumulation verified on bench ($5.451\text{ mm/pulse}$). Physical slots (42 vs 43) disambiguated from empirical calibration factor. Tape-measured floor distance deferred. | **L5 (Physical Floor)** |
| **RF Failover Protocol** | **OPEN** | L1, L2, L3 | **L3 (Software / HIL)** | Monotonic sequence counters, NVS `boot_id`, sequence re-anchoring, and deduplication verified in software/HIL. Over-the-air physical switchover and packet drop under real RF pending bench. | **L4 (Physical Bench RF)** |
| **Safe Beacon Subsystem** | **OPEN** | L1, L2, L3 | **L3 (Software / HIL)** | Failsafe broadcast generator, gateway parser, and backend `/api/hardware/beacon` route verified in 54 software tests. Over-the-air SX1278 broadcast to physical gateway pending bench. | **L4 (Physical Bench RF)** |
| **Floor Motion Distance** | **DEFERRED** | L1, L2, L4 | **L4 (Bench Pulses Only)** | Pulse accumulation matches theoretical model; physical floor distance translation unmeasured with tape measure. Explicitly categorized as `UNMEASURED`. | **L5 (Physical Floor)** |
| **Final Physical E2E** | **DEFERRED** | L1, L2, L3 | **L3 (Software / HIL)** | Full closed loop proven in simulation and HIL; deferred to physical demonstration session. | **L5 (Physical Floor)** |

---

### 3. Summary of Evidence Integrity

1. **No Software Claimed as Physical:**
   All unit tests, simulated streams, and Pytest suites are strictly marked as L1, L2, or L3.
2. **Bench Testing Isolated:**
   Elevated bench testing (L4) on COM14, COM11, and 192.168.137.217 is recognized solely for electrical, firmware, and telemetry ingress validation. It is **never conflated with physical floor motion (L5)**.
3. **Open Gates Maintained:**
   RF Failover and Safe Beacon are held at **L3 (OPEN)** until physical RF over-the-air validation on the physical hardware bench is conducted.
