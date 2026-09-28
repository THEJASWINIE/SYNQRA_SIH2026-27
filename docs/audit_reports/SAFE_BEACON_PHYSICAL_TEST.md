# SAFE BEACON PHYSICAL TEST & ADVERSARIAL VALIDATION REPORT
**System:** FOG-ORCHESTRATOR 2.0  
**Audit Phase:** Final Adversarial Hardware Validation (Attack 3)  
**Date:** 2026-09-27  

---

## 1. Executive Verdict

```
================================================================================
SAFE BEACON SOFTWARE VERIFIED
SAFE BEACON PHYSICAL = NOT VERIFIED
================================================================================
```

### Forensic Ground Truth
1. **Software Layer (`failsafe/safe_beacon.py` & `integration_adapters/safe_beacon_adapter.py`):**
   - Fully implemented and verified across 43 unit tests (`tests/test_phase7_4_safe_beacon.py`).
   - Implements autonomous state transition: `NOMINAL` $\to$ `DEGRADED` ($500\text{ ms}$) $\to$ `ACTIVE_STANDALONE` ($1000\text{ ms}$) $\to$ `RECOVERY`.
   - Verified 100% actuator decoupling: Safe Beacon controller does NOT actuate motor PWM directly (informational alerting only).

2. **Physical Embedded Firmware (`esp32_code/sketch_aug26a/sketch_aug26a.ino`):**
   - The production ESP32 firmware on Vehicle A and Vehicle B broadcasts **only canonical V2V frames**:
     `STATE,TRUCK_01,seq,rpm,speed,ax,ay,az,gx,gy,gz`
   - The physical firmware **does NOT implement the `BEACON,<vid>,<seq>,<state>,<v_safe>,<timestamp>,<zone_id>` packet generator**.
   - The physical Semtech SX1278 transceiver is a **single half-duplex module** operating at 433 MHz. Transmitting emergency safe beacons would blind the receiver to incoming gateway abort frames for $38.5\text{ ms}$ (airtime).

3. **Backend Disconnect Mechanism:**
   - The backend does NOT receive an active "Safe Beacon" from an offline vehicle over Wi-Fi (a severed link cannot deliver packets).
   - The backend detects link loss strictly via **server-side telemetry silence (heartbeat gap)**:
     - $T_{\text{stale}} = 3.0\text{ s}$ (`COMMUNICATION_DEGRADED`)
     - $T_{\text{offline}} = 10.0\text{ s}$ (`OFFLINE`)

---

## 2. Empirical Timestamp Chain (Physical Hardware Run)

| Timestamp Marker | Elapsed Time ($t$) | Physical Subsystem | State / Event Observed | Measurement Evidence |
|:---|:---:|:---|:---|:---|
| **$T_0$** | `0.000 s` | Vehicle A (`COM14`) | Last healthy Wi-Fi telemetry packet received by backend | `POST /api/hardware/telemetry` HTTP 200 (Seq: 702) |
| **$T_1$** | `+0.500 s` | LoRa PHY (433 MHz) | Expected software Safe Beacon threshold ($500\text{ ms}$) | Software model triggers; **Physical ESP32 firmware sends no `BEACON` packet** |
| **$T_2$** | `+3.000 s` | FastAPI Backend | Ingestion watchdog hits `stale_threshold_s` (3.0s) | Vehicle state transitions to `is_stale: True`, `COMMUNICATION_DEGRADED` |
| **$T_3$** | `+10.000 s` | FastAPI Backend | Ingestion watchdog hits `offline_threshold_s` (10.0s) | Vehicle state transitions to `status: OFFLINE` |
| **$T_4$** | `+10.045 s` | Operator & Control HMI | WebSocket broadcast updates UI telemetry badge | Badge renders red `OFFLINE / COMMUNICATION_DEGRADED` |
| **$T_5$** | Continuous | Physical Vehicle (`COM14`) | Local ESP32 Motor Governor | Motor continues running at autonomous default ($0.50\text{ m/s}$) or stops if explicit command received |

---

## 3. Discrepancy & Adversarial Failure Mode

### Claim from Previous Report:
> *"Safe Beacon hardware path verified: 100% operational; alerts Control Room when link is severed."*

### Adversarial Reality:
1. **Contradiction:** An offline vehicle with a severed Wi-Fi link cannot transmit a packet to the backend Control Room. The Control Room alerts via **packet timeout**, not packet arrival.
2. **Firmware Absence:** `sketch_aug26a.ino` does not implement `BEACON` broadcast.
3. **RF Collision:** On a single SX1278 transceiver, transmitting a beacon disables RX mode for $38.5\text{ ms}$, creating half-duplex packet loss.
4. **Formal Classification:**
   - **Software Architecture:** **PASS** (Defensible, tested, decoupled)
   - **Physical Over-The-Air Hardware:** **NOT VERIFIED / NOT IMPLEMENTED IN CURRENT FLASHED FIRMWARE**
