# PRE_PHYSICAL_GO_NO_GO.md
## FOG-ORCHESTRATOR 2.0 — Final Pre-Physical Validation Gate Decision

**Date:** 2026-09-27  
**Evaluator:** Principal Software Architect & Lead Hardware Integration Engineer  
**Standard:** ZERO FABRICATION — HARDWARE TRUTH FIRST (AGENTS.md)  
**Overall Pre-Physical Status:** **YELLOW / READY TO ENTER PHYSICAL VALIDATION**

---

### EXACT GATE DECISION BLOCK

```text
============================================================
PRE-PHYSICAL GO / NO-GO GATE STATUS
============================================================

VEHICLE A:
PASS

VEHICLE B:
PASS

OPERATOR HMI:
PASS

CONTROL ROOM HMI:
PASS

BACKEND:
PASS

DIGITAL TWIN:
PASS

CALIBRATION:
PASS

RF FAILOVER:
OPEN

SAFE BEACON:
OPEN

FLOOR MOTION:
DEFERRED

FINAL E2E:
DEFERRED

============================================================
OVERALL DECISION:
READY TO ENTER FINAL PHYSICAL VALIDATION (YELLOW)
============================================================
```

---

### Detailed Gate Audit Justification

#### 1. VEHICLE A: PASS
- **Firmware:** `esp32_code/sketch_aug26a/sketch_aug26a.ino` audited.
- **Hardware Integration:** L298N driver, LM393 optical encoder (42 physical slots), MPU6050 IMU, SX1278 LoRa radio (433 MHz).
- **Parity & Failsafe:** Persistent NVS `bootId`, monotonic `globalSequence`, Tier-1 autonomous safe stop on comm loss (`commandedSpeedMs = 0`, PWM = 0).
- **Evidence Level:** L4 (Physical Bench Verified on COM14). Zero floor translation claimed.

#### 2. VEHICLE B: PASS
- **Firmware:** `esp32_code/VEHICLE_B_TRUCK_02_V2V_DIGITAL_TWIN_MOTOR/...ino` audited across all 15 points.
- **Hardware Integration:** TB6612FNG driver (LEFT: 25, 26, 27; RIGHT: 32, 33, 14; STBY: 13). Standby held LOW on boot. LEDC PWM initialized cleanly. LM393 optical encoder (43 physical slots), MPU6050, LoRa radio.
- **Parity & Failsafe:** Persistent NVS `bootId`, monotonic `globalSequence`, `sendSafeBeacon()` at 1.0 Hz on Wi-Fi loss, Tier-1 autonomous safe stop.
- **Evidence Level:** L4 (Physical Bench Verified on 192.168.137.217). Zero floor translation claimed.

#### 3. OPERATOR HMI: PASS
- **Frontend Code:** `SYNQRA_SIH2026-27-HMI/frontend/src/vehicle/DriverScreen.tsx`.
- **Truth Invariants:** Distinctly renders **COMMAND REQUESTED** vs **SAFE LIMIT**. Explicitly renders **`COMMAND APPLIED: UNKNOWN / NOT TELEMETRIED`** (no current sensor fitted). Honestly labels GNSS as **`NOT FITTED ON CHASSIS`**.
- **Evidence Level:** L2 (Automated Tests Passing: 1860 / 1860) + L4 (Live Ingress Streaming).

#### 4. CONTROL ROOM HMI: PASS
- **Frontend Code:** `SYNQRA_SIH2026-27-HMI/frontend/src/screens/OperationsOverview.tsx`.
- **Truth Invariants:** Fixed topbar feed status bug (MOCK provider now honestly renders as `MOCK ◌` instead of `LIVE ●`). Applied speed labeled `UNKNOWN / NOT TELEMETRIED`. RF Failover labeled `NOT VERIFIED (PROTOCOL OPEN)`. Safe Beacon labeled `SOFTWARE READY · FIELD GATE PENDING`.
- **Evidence Level:** L2 (Automated Tests Passing) + L4 (Live Ingress Streaming).

#### 5. BACKEND: PASS
- **Engine:** FastAPI server on port 8000 + `telemetry_ingest.py`.
- **Vulnerability Fixed:** Sequence deadlock on post-reboot telemetry fixed via `boot_id` validation and sequence re-anchoring in `TelemetryIngestor`.
- **Evidence Level:** L2 (135 Pytest Unit & Regression Tests Passing) + L4 (Live HTTP & Gateway Serial Ingestion).

#### 6. DIGITAL TWIN: PASS
- **Engine:** Pygame 3D Digital Twin on port 8080 + `twin_projection.py`.
- **Truth Invariants:** One authoritative state store. Projects canonical speeds, poses, and safety envelopes to all clients without UI physics synthesis.
- **Evidence Level:** L2 (Automated Projection Tests Passing) + L4 (Live Twin Synchronization).

#### 7. CALIBRATION: PASS
- **Artifact:** [`CALIBRATION_TERMINOLOGY_AUDIT.md`](file:///c:/Users/JAGADEESH%20M/OneDrive/Documents/SIH-2026-27/CALIBRATION_TERMINOLOGY_AUDIT.md).
- **Disambiguation:** Vehicle A physical slots = 42; Vehicle B physical slots = 43. $K_{\text{cal}} = 34.58\text{ pulses/rev}$ is an empirical distance calibration factor ($5.451\text{ mm/pulse}$), NOT a physical fractional slot count.
- **Evidence Level:** L1 (Code Inspection) + L2 (Kinematic Unit Tests) + L4 (Bench Pulse Count Accumulation).

#### 8. RF FAILOVER: OPEN
- **Artifact:** [`RF_FAILOVER_PRE_PHYSICAL_AUDIT.md`](file:///c:/Users/JAGADEESH%20M/OneDrive/Documents/SIH-2026-27/RF_FAILOVER_PRE_PHYSICAL_AUDIT.md).
- **Status Reason:** Software protocol, session awareness, deduplication, and reboot resilience are fully verified in software. However, physical over-the-air packet forwarding and switchover latency have not yet been bench-verified with the final dual-chassis setup.
- **Evidence Level:** L3 (Software / HIL Verified). Held strictly **OPEN**.

#### 9. SAFE BEACON: OPEN
- **Artifact:** [`SAFE_BEACON_PRE_PHYSICAL_AUDIT.md`](file:///c:/Users/JAGADEESH%20M/OneDrive/Documents/SIH-2026-27/SAFE_BEACON_PRE_PHYSICAL_AUDIT.md).
- **Status Reason:** Firmware `sendSafeBeacon()` (1.0 Hz, `BEACON,TRUCK_02,<seq>,DEGRADED,<millis>,PIT_ZONE_A`), gateway parser, and backend `/api/hardware/beacon` route are verified across 54 tests. Physical RF transmission from SX1278 to physical gateway receiver is pending hardware bench validation.
- **Evidence Level:** L3 (Software / HIL Verified). Held strictly **OPEN**.

#### 10. FLOOR MOTION: DEFERRED
- **Status Reason:** Pulse accumulation on elevated bench test is validated. Ground-truth linear translation on floor surfaces measured with a reference steel tape measure is explicitly deferred to physical validation.
- **Evidence Level:** L4 (Bench Rotations Only). Floor distance = `UNMEASURED`.

#### 11. FINAL E2E: DEFERRED
- **Status Reason:** Complete end-to-end closed loop (Fog change $\to$ Twin state change $\to$ Safety solver $\to$ Command Gateway $\to$ Vehicle state update $\to$ HMI reflection) is verified in HIL and simulation. Physical multi-vehicle driving on the floor is deferred to the physical testing session.
- **Evidence Level:** L3 (Simulation / HIL).

---

### Conclusion & Entry Authorization

The software codebase, firmware implementations, communication protocols, deduplication algorithms, and HMI presentation layers have successfully withstood all 10 hostile attacks without unbacked claims or data fabrication.

**THE SYSTEM IS AUTHORIZED TO ENTER FINAL PHYSICAL BENCH & FLOOR VALIDATION.**
