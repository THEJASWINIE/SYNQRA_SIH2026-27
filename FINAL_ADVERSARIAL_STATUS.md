# FOG-ORCHESTRATOR 2.0 — FINAL ADVERSARIAL HARDWARE VALIDATION REPORT
**Authoritative Architectural Review & Hostile Failure Audit**  
**Audit Date:** 2026-09-27  
**Operating Standard:** Rule 3 (Zero Telemetry Fabrication) & Rule 23 (Honesty About Hardware)  
**Final Verdict:** **YELLOW (Core Laboratory System Operational; Important Physical Gaps Documented)**

---

## 1. Subsystem Adversarial Audit Status

| Subsystem | Audit Status | Highest Evidence Demonstrated | Operational Boundary & Reality |
|:---|:---:|:---|:---|
| **Physical Hardware** | **BENCH VERIFIED** | L3 Physical Benchtop | Physical ESP32, MPU6050 (0x68), SX1278 (433 MHz), and slotted encoders running on bench. No floor ground truth. |
| **Software Backend** | **ALGORITHM PASS** | L1 / L2 Contract Test | 1,009 pytest automated assertions pass; FastAPI backend ingests telemetry and serves Digital Twin snapshots. |
| **RF / V2V PHY** | **PHYSICAL RF PASS** | L3 Over-The-Air RF | Peer-to-peer V2V at 433 MHz between Vehicle A and B verified (RSSI -74 to -76 dBm, SNR 9.25 to 9.75 dB). |
| **RF Failover** | **OPEN (P1 DEFECT)** | L3 RF + HTTP 409 Audit | Physical LoRa continues transmitting when Wi-Fi drops, but backend drops rebooted offline packets due to strict monotonic sequence check. |
| **Safe Beacon** | **SW PASS / HW UNVERIFIED**| L1 Software / L0 Physical | Software state machine passes 43 tests. Physical ESP32 firmware lacks `BEACON` ASCII packet formatter; single radio is half-duplex. |
| **Calibration** | **RECONCILED TRUTH** | L4 Forensic Audit | $34.58\text{ pulses/rev}$ is an empirical scaling divisor ($K_{\text{cal}}$), NOT an integer optical slot count (raw PPR is 42 on A, 43 on B). |
| **Vehicle A (`TRUCK_01`)**| **BENCH OPERATIONAL** | L3 Physical USB/Wi-Fi | Running `sketch_aug26a.ino` on `COM14`; live telemetry streaming at ~2 Hz, IMU active, L298N driver wired. |
| **Vehicle B (`TRUCK_02`)**| **BENCH OPERATIONAL** | L3 Physical Network | Connected at `192.168.137.217`; TB6612FNG driver wired; V2V state packets received by Vehicle A. |
| **Backend Orchestrator**| **OPERATIONAL** | L2 Integration Daemon | FastAPI on port 8000 handling WebSocket `/api/ws`, deduplication, and Twin state projection. |
| **Operator HMI** | **OPERATIONAL** | L2 Browser Client | Vite React application rendering speed limit, actual speed, and honest provenance badges (`LIVE`, `MOCK`, `REPLAY`). |
| **Control Room HMI** | **OPERATIONAL** | L2 Browser Client | Supervisory fleet view rendering dual vehicle status, link degradation alerts, and stale telemetry counters. |
| **Digital Twin** | **OPERATIONAL** | L2 State Projection | authoritative backend store; zero synthetic drift when disconnected; no position invented without telemetry. |
| **End-to-End Loop** | **COMPUTATIONAL PASS** | L2 Injected Environment | Injected visibility reduction ($100\text{ m} \to 15\text{ m}$) triggers physics solver in **$330.0\ \mu\text{s}$** ($0.330\text{ ms}$). |

---

## 2. Issues Register (P0 / P1 / P2)

### P0 (Safety-Critical Invariants)
- **None Active:** Local vehicle safety governor remains strictly authoritative (`sketch_aug26a.ino:1256`). Remote dispatch commands cannot exceed `MAX_PROTOTYPE_SPEED_MS` ($1.40\text{ m/s}$).

### P1 (Architectural / Physical Validation Gaps)
1. **ISSUE-P1-01: RF Failover Sequence Reset Barrier (OPEN)**
   - *Symptom:* When a vehicle reboots in an offline Wi-Fi area, its internal sequence resets to 1. Because the backend retains previous high sequence numbers (e.g., 702), the LoRa Gateway's forwarded packets are rejected with HTTP 409 `REJECTED_OUT_OF_ORDER`.
   - *Impact:* Prevents seamless automatic failover from Wi-Fi to LoRa unless the vehicle can query `/api/hardware/sequence` or the backend implements reboot-epoch tracking.
   - *Status:* **OPEN**. Cataloged in `RF_FAILOVER_TEST.csv`.

2. **ISSUE-P1-02: Safe Beacon Physical Firmware Omission (OPEN)**
   - *Symptom:* `failsafe/safe_beacon.py` passes 43 unit tests in Python, but production ESP32 firmware (`sketch_aug26a.ino`) does not contain the `BEACON` packet generator.
   - *Impact:* The Control Room detects offline state strictly via incoming telemetry silence (heartbeat gap), not by receiving an over-the-air safe beacon.
   - *Status:* **OPEN / DOWNGRADED**. Documented in `SAFE_BEACON_PHYSICAL_TEST.md`.

3. **ISSUE-P1-03: Physical Floor Translation Gap (OPEN)**
   - *Symptom:* All physical motor testing has been conducted with wheels elevated on the bench. No physical chassis translation across floor or gravel surfaces has been verified with external optical ground truth or tape measure.
   - *Impact:* Synthetic tables claiming sub-millimeter floor accuracy were mathematical models derived from $K_{\text{cal}}=34.58$, not independent floor trials.
   - *Status:* **OPEN / DOWNGRADED**. Cataloged in `vehicle_A_physical_motion.csv` and `vehicle_B_physical_motion.csv`.

### P2 (Documentation & Calibration Nomenclature)
1. **ISSUE-P2-01: "PPR = 34.58" Misnomer (CLOSED)**
   - *Root Cause:* An optical slotted wheel physically cannot have a fractional slot count.
   - *Resolution:* Formally reconciled in `CALIBRATION_TRUTH_TABLE.md`. Raw PPR is 42.0 (Vehicle A) and 43.0 (Vehicle B). $34.58$ is renamed and scoped strictly as `EFFECTIVE_CALIBRATION_K` ($K_{\text{cal}}$).

---

## 3. Attack 13: Audit of Claims from Previous Report

| Previous Report Claim | Actual Physical & Algorithmic Evidence | Evidence Level | Verdict | Overclaim Assessment |
|:---|:---|:---:|:---:|:---|
| **"100% operational"** | ESP32 nodes stream telemetry; backend and HMI render state; bench motors spin under command. | Benchtop Prototype | **PARTIALLY SUPPORTED** | **OVERCLAIM.** Prototype is bench-operational, but lacks floor-traction dynamic testing and steering odometry. |
| **"GREEN"** | 1,009 pytest and 1,860 vitest automated assertions pass. | Automated Software | **UNSUPPORTED** | **OVERCLAIM.** A software pass is not a physical hardware pass. Must be downgraded to **YELLOW**. |
| **"READY FOR LIVE SIH DEMONSTRATION"** | Live bench demonstration of V2V LoRa, Wi-Fi telemetry, Digital Twin, and HMI is robust and reproducible. | Benchtop Prototype | **SUPPORTED (BENCH ONLY)** | **ACCURATE FOR BENCH DEMO;** Overclaim if presented as a commercial autonomous haul truck. |
| **"100% closed-loop"** | Digital Twin visibility change computes safe speed and updates motor PWM in $0.330\text{ ms}$. | Injected Input / SIL | **PARTIALLY SUPPORTED** | **OVERCLAIM.** Closed-loop computational response works, but fog is an injected software parameter, not optical sensor feedback. |
| **"Redundant failover"** | When Wi-Fi is lost, LoRa broadcasts at 433 MHz and Gateway receives, but backend drops packets due to seq mismatch. | Over-The-Air RF | **UNSUPPORTED / OPEN** | **OVERCLAIM.** Physical link operates, but end-to-end failover ingestion fails due to sequence reset drop (HTTP 409). |
| **"Physical hardware verified"** | Verified live ESP32 on COM14, LoRa SX1278 SPI, MPU6050 I2C, and optical slotted encoder. | Physical Silicon / Bench | **SUPPORTED (BENCH LEVEL)** | **ACCURATE FOR BENCH.** Not verified for chassis floor dynamics. |
| **"Safe Beacon verified"** | `failsafe/safe_beacon.py` passes 43 tests; physical firmware does not transmit `BEACON` frames. | Software Unit Test | **UNSUPPORTED ON HARDWARE**| **OVERCLAIM.** Formally downgraded to: `SAFE BEACON SOFTWARE VERIFIED; SAFE BEACON PHYSICAL = NOT VERIFIED`. |
| **"Zero fabrication"** | Previous `encoder_calibration.csv` was mathematically synthesized from $K_{\text{cal}}=34.58$. | Mathematical Artifact | **RECTIFIED IN AUDIT** | **PAST OVERCLAIM RECTIFIED.** Replaced with empirical bench truth in `vehicle_A_physical_motion.csv`. |

---

## 4. Claims We Can Defend vs. Claims We Must Downgrade

### Claims We CAN Defend (Directly Supported by Evidence)
1. **Authoritative Digital Twin State Model:** There is strictly ONE backend Digital Twin state store. Neither HMI nor Pygame invents independent vehicle state.
2. **Deterministic Physics Solver Speed:** Safe speed calculation ($\min(v_{\text{stop}}, v_{\text{retarder}}, v_{\text{traction}}, v_{\text{curve}}, v_{\text{mine}})$) executes in **$313.8\ \mu\text{s}$**, and total computational pipeline from environment update to motor PWM mapping takes **$0.330\text{ ms}$**.
3. **Physical V2V PHY Communication:** Vehicle A and Vehicle B physically communicate over 433 MHz LoRa using Semtech SX1278 transceivers with measurable RF metrics ($\text{RSSI} = -74\text{ to } -76\text{ dBm}$, $\text{SNR} = 9.25\text{ to } 9.75\text{ dB}$).
4. **Local Safety Governor Authority:** Firmware enforces hard-coded speed clamping (`MAX_PROTOTYPE_SPEED_MS = 1.40 m/s`). Central orchestrator or remote peer speed commands cannot override local safety limits.
5. **Anti-Fabrication & Freshness Discipline:** When physical telemetry disconnects, the Digital Twin clamps position, increments `age_seconds`, and marks vehicle `OFFLINE` ($>10\text{ s}$) rather than synthesizing artificial drift.
6. **HMI Provenance Transparency:** Frontend components explicitly badge data sources (`LIVE`, `SIMULATION`, `MOCK`, `REPLAY`) and separate service availability from data freshness.

### Claims We MUST Downgrade (Overclaims Rectified)
1. **"Physical PPR = 34.58":** Downgraded to **Empirical Divisor ($K_{\text{cal}}$)**. Physical optical discs have 42 slots (Vehicle A) and 43 slots (Vehicle B).
2. **"Redundant RF Failover Complete":** Downgraded to **Physical RF Link Active; Ingestion Failover OPEN** due to the sequence reset rejection barrier (ISSUE-P1-01).
3. **"Safe Beacon Hardware Path Verified":** Downgraded to **Software Algorithm Verified; Physical Over-The-Air Frame Unimplemented** in flashed firmware (ISSUE-P1-02).
4. **"Sub-Millimeter Floor Distance Accuracy Verified":** Downgraded to **Bench Pulse Accumulation Verified; Physical Floor Translation Unmeasured** without an external ground-truth tracker (ISSUE-P1-03).
5. **"Physical Fog Closed Loop":** Downgraded to **Injected Environmental Parameter Closed Loop** (zero atmospheric water droplets or optical sensor attenuation).

---

## 5. Remaining Failure Modes

1. **Cold Boot Sequence Disconnect:** A vehicle booting in an offline zone cannot sync sequence from `/api/hardware/sequence` and will have its LoRa packets rejected by the backend if the backend has seen a higher sequence number.
2. **Single-Transceiver Half-Duplex Blindness:** Because each prototype vehicle has a single SX1278 module, transmitting high-rate V2V frames or emergency beacons blinds the receiver to incoming gateway commands for $38.5\text{ ms}$ per packet.
3. **Open-Loop Floor Slippage:** Slotted optical encoders count wheel rotations, but without IMU integration or ground-facing optical flow, wheel slip on wet or low-friction haul surfaces cannot be directly measured on the physical chassis.

---

## 6. Final Demo Readiness Rating

```
================================================================================
FINAL DEMO READINESS: YELLOW
================================================================================
```

### Rationale:
- **Why NOT GREEN:**
  A rating of GREEN requires all critical claims to be physically demonstrated in closed-loop operation. This adversarial audit proved that RF failover ingestion remains OPEN due to sequence resets, Safe Beacon is unimplemented in production firmware, and floor motion has not been measured with external physical ground truth. Selecting GREEN would violate Rule 3 and Rule 23.
- **Why NOT RED:**
  Core software architecture, single authoritative Digital Twin, 0.330 ms safety solver, physical 433 MHz LoRa V2V link, local safety governor clamping, and HMI telemetry rendering are 100% operational, robust, and demonstrable on the live bench prototype.
- **SIH Demonstration Posture:**
  Present the system honestly as an **advanced Cyber-Physical Digital Twin and V2V Benchtop Prototype with mathematically rigorous failsafe boundaries**, highlighting empirical constants, hardware provenance badges, and verified sub-millisecond reaction times.
