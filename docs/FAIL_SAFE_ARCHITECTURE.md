# FAIL-SAFE ARCHITECTURE & DETERMINISTIC STATE MACHINE
**FOG-ORCHESTRATOR 2.0 — SIH 2026-27 | Phases H1–H10**  
**Lead Safety-Critical Systems & CPS Integration Engineer**  
**Document Revision:** 1.0  
**Date:** 2026-09-24  

---

## 1. Executive Summary & Design Principles

The primary requirement of FOG-ORCHESTRATOR 2.0 is that **no single failure, communication drop, sensor glitch, or cloud crash can cause a heavy dump truck to operate outside its physical safety envelope**.

### Core Safety Invariants
1. **Invariant 1 (Local Safety Authority):** The central orchestrator may only recommend or command. The onboard vehicle Tier-1 Safety Governor remains the final and absolute safety authority.
2. **Invariant 2 (Communication Decoupling):** Complete loss of RF, WiFi, or cellular backhaul MUST NOT disable local safety governance.
3. **Invariant 3 (Safe Beacon Boundary):** The Safe Beacon is an informational and alerting broadcast; it MUST NOT directly command or actuate vehicle motors.
4. **Invariant 4 (Stale Command Rejection):** No command older than `MAX_COMMAND_AGE = 1000.0 ms` can be executed.
5. **Invariant 5 (Recovery Validation):** Returning from a degraded or fail-safe state to `NORMAL` requires healthy signal persistence across a minimum validation window ($N \ge 5$ cycles).

---

## 2. Complete Fail-Safe State Machine

The system executes a deterministic 10-state finite state machine (FSM):

```
                        ┌──────────────┐
                        │    NORMAL    │
                        └──────┬───────┘
                               │
               ┌───────────────┼───────────────┐
               │ Minor Jitter  │ Sensor Fault  │
               ▼               ▼               ▼
        ┌────────────┐  ┌─────────────┐ ┌──────────────┐
        │  DEGRADED  │  │ SENSOR_FAULT│ │   EMERGENCY  │
        └──────┬─────┘  └──────┬──────┘ └──────┬───────┘
               │               │               │
      Heartbeat Silence        │        E-Stop / Blindout
        (> 500 ms)             │               │
               ▼               ▼               │
      ┌─────────────────┐      │               │
      │COMMUNICATION_LOSS│     │               │
      └────────┬────────┘      │               │
               │               │               │
        Trigger Beacon         │               │
               ▼               ▼               │
      ┌──────────────────┐     │               │
      │SAFE_BEACON_ACTIVE│     │               │
      └────────┬─────────┘     │               │
               │               │               │
        Isolate Remote         │               │
               ▼               ▼               │
      ┌───────────────────────────────┐        │
      │       LOCAL_SAFE_MODE         │◄───────┘
      │ (Local Governor Autonomous)   │
      └──────────────┬────────────────┘
                     │
         5 Consecutive Valid Pkts
                     ▼
             ┌──────────────┐
             │   RECOVERY   │
             └──────┬───────┘
                    │ Complete Handshake
                    ▼
             ┌──────────────┐
             │  CONNECTED   │
             └──────────────┘
```

---

## 3. Explicit State Transition Rules & Budgets

| Current State | Trigger Event | Target State | Operational Reaction | Command Action |
| :--- | :--- | :--- | :--- | :--- |
| **NORMAL** | Packet loss $> 10\%$ or latency $> 100\text{ ms}$ | **DEGRADED** | Log warning; increase headway margin $h_{\text{safe}}$ by $+20\%$ | **CLAMP** |
| **NORMAL** | Heartbeat silence $> 500.0\text{ ms}$ | **COMMUNICATION_LOSS** | Start fail-safe timer; alert operator via in-cab audio chime | **REJECT REMOTE** |
| **COMMUNICATION_LOSS** | Immediate upon declaring comm loss | **SAFE_BEACON_ACTIVE** | Activate 433 MHz peer-to-peer V2V broadcast @ 2 Hz | **REJECT REMOTE** |
| **SAFE_BEACON_ACTIVE** | Immediate | **LOCAL_SAFE_MODE** | Speed governed strictly by onboard optical sensors ($v \le 3.52\text{ m/s}$) | **REJECT REMOTE** |
| **LOCAL_SAFE_MODE** | Obstacle detected at $S \le R_{\text{eff}} - 5.0\text{ m}$ | **EMERGENCY_STOP** | Command $v_{\text{applied}} = 0.0\text{ m/s}$; full dynamic/service brake applied | **CLAMP TO 0.0** |
| **LOCAL_SAFE_MODE** | Valid gateway link restored ($N \ge 1$) | **RECOVERY** | Hold current safe crawl speed; start persistence counter ($N=1$) | **HOLD SAFE** |
| **RECOVERY** | Healthy telemetry persists for $N = 5$ cycles | **CONNECTED** | Handshake completed with gateway; clear yellow HMI watermark | **ACCEPT** |
| **ANY STATE** | Physical E-Stop pressed or CAN silence $> 150\text{ ms}$ | **EMERGENCY_STOP** | Instantaneous dynamic brake (AIN1/2=HIGH); cut PWM to 0 | **CLAMP TO 0.0** |

---

## 4. The Independent Resilience Path

When primary long-range infrastructure fails, the vehicle falls back through a completely isolated local resilience path:

```
[INFRASTRUCTURE COLLAPSE]
(LoRa Gateway Power Failure / Fiber Backhaul Cut)
               │
               ▼
[HEARTBEAT SILENCE TIMER EXPIRES]
(Firmware Watchdog: 500 ms on LoRa, 150 ms on CAN)
               │
               ▼
[SAFE BEACON ENGAGED]
(433 MHz LoRa Broadcast: "TRUCK_02 COMM_LOSS AT SEGMENT_4")
               │
               ▼
[LOCAL SAFETY AWARENESS]
(Adjacent peer trucks receive packet via direct V2V LoRa)
               │
               ▼
[LOCAL TIER-1 SAFETY GOVERNOR]
(Onboard ESP32 solves stopping distance using local MPU6050 & Encoders)
               │
               ▼
[AUTONOMOUS CONTROLLED HALT]
(Vehicle halts safely on haul road shoulder; holds service brake)
```

---

## 5. Watchdog Timing & Deterministic Recovery

### 5.1 Watchdog Hierarchy
1. **CAN / TWAI Hardware Watchdog:** $150.0\text{ ms}$ timeout. If no heartbeat frame is received from the brake controller within 150 ms, the system clamps throttle to 0.
2. **LoRa Telemetry Watchdog:** $500.0\text{ ms}$ timeout ($200.0\text{ ms}$ in dense fog). If no gateway downlink arrives, vehicle enters `LOCAL_SAFE_MODE`.
3. **Command Expiration Watchdog:** $1000.0\text{ ms}$ timeout. Any dispatch packet with `timestamp < (now - 1.0s)` is discarded as stale.

### 5.2 Anti-Flapping Recovery Hysteresis
To prevent "ping-ponging" between fail-safe braking and rapid acceleration when driving through intermittent RF shadowing:
- Entering fail-safe requires **1 failure** (single timeout of 500 ms).
- Exiting fail-safe requires **5 consecutive valid, in-order packets** with $\text{RSSI} > -95\text{ dBm}$ and valid sequence increments over $\ge 2.5\text{ seconds}$.
- Commanded acceleration during recovery is rate-limited to $a_{\text{recover}} \le 0.5\text{ m/s}^2$.
