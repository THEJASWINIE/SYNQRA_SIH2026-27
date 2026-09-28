# EXPERIMENT E8 — COMPREHENSIVE FAILURE INJECTION REPORT

**Project:** FOG-ORCHESTRATOR 2.0 (SIH 2026-27 — SIH26007)  
**Classification:** Fault Injection & Fail-Safe Verification  
**Evidence Level:** L1 — Automated Deterministic Verification / L7 — Bench Tested  
**Dataset Reference:** [`data/failure_injection_matrix.csv`](file:///c:/Users/JAGADEESH%20M/OneDrive/Documents/SIH-2026-27/data/failure_injection_matrix.csv)  

---

## 1. Safety Invariant Objective

Every possible single-point failure (RF loss, gateway severed, malicious or corrupted packet injection, sensor dropout, sudden dense fog) must result in a safe, deterministic vehicle state transition with **zero overspeed or collision hazard**.

---

## 2. Failure Injection Matrix & Verified Response

| Failure Mode ID | Injected Fault Description | Detection Time (s) | Resulting Fallback State | Enforced Speed ($v$, m/s) | Safety Invariant Preserved? |
|:---|:---|:---:|:---|:---:|:---:|
| **GATEWAY_TOTAL_LOSS** | Central gateway radio link severed | 1.050 | `NO_GATEWAY` | 0.00 | **PASS (I5)** |
| **V2V_BEACON_DROP** | Peer dumper direct beacon lost | 0.350 | `DEGRADED_COMMUNICATION` | 4.50 (Safe Headway) | **PASS (I6)** |
| **STALE_COMMAND_INJECTION**| Injected command with timestamp $\Delta t > 1.0\text{s}$ | 0.050 | `STALE_COMMAND` | 4.50 (Clamped) | **PASS (I2)** |
| **DUPLICATE_REPLAY** | Sequence number duplicate / roll-back | 0.050 | `INVALID_COMMAND` | 4.50 (Clamped) | **PASS (I3)** |
| **OUT_OF_ORDER_PACKET** | Sequence jumped backward ($seq < last$) | 0.050 | `INVALID_COMMAND` | 4.50 (Clamped) | **PASS (I4)** |
| **CORRUPTED_PAYLOAD** | Bit-flip in telemetry payload / CRC fail | 0.020 | `INVALID_COMMAND` | 4.50 (Clamped) | **PASS (I10)** |
| **NEGATIVE_SPEED_CMD** | Command requesting negative speed (-5 m/s) | 0.050 | `NORMAL` (Clamped) | 0.00 | **PASS (I11)** |
| **NAN_SPEED_CMD** | Injected `NaN` float in target speed field | 0.050 | `INVALID_COMMAND` | 0.00 | **PASS (I10)** |
| **SENSOR_DROPOUT** | Visibility sensor telemetry lost / invalid | 0.100 | `EMERGENCY_STOP` | 0.00 | **PASS (I8)** |
| **DOWN_GRADE_RUNAWAY** | Road friction suddenly drops ($\mu = 0.15$) | 0.050 | `UNSAFE_COMMAND` | 1.50 | **PASS (I1)** |
| **SUDDEN_DENSE_FOG** | Visibility drops from 50 m to 3 m | 0.100 | `EMERGENCY_STOP` | 0.00 | **PASS (I8)** |
| **BACKEND_DISCONNECT** | Central FastAPI server crashes / drops | 1.050 | `NO_GATEWAY` | 4.50 | **PASS (I5)** |

---

## 3. Engineering Audit Summary

1. **Zero Unsafe Accelerations:**  
   Across all 12 fault scenarios, no injected fault caused the vehicle to exceed its locally governed safe speed limit.

2. **Immediate Rejection:**  
   Corrupted, out-of-order, stale, or malformed packets are rejected at the parsing boundary on the ESP32 firmware in $< 50\text{ ms}$, leaving the previously validated speed profile intact.
