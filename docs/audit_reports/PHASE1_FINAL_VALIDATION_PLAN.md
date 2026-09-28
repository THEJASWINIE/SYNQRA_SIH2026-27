# FOG-ORCHESTRATOR 2.0 — PHASE 1 FINAL VALIDATION PLAN

**Date**: 2026-08-28  
**Author**: Senior Embedded Systems Verification Engineer, Distributed Systems Test Engineer, Industrial HMI Validation Engineer  
**Scope**: Final Architecture Freeze & Validation Gates for Physical Hardware ↔ LoRa Gateway ↔ Backend ↔ HMI

---

## 1. System Architecture Under Validation

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

## 2. Validation Gate Specifications & Acceptance Criteria

### Gate 1: End-to-End Latency Measurement
- **Latency Model**: $T_{E2E} = T_{LoRa} + T_{Gateway} + T_{Serial} + T_{Backend} + T_{WebSocket}$
- **Sample Target**: $\ge 100$ telemetry packets per vehicle (`TRUCK_01` & `TRUCK_02`).
- **Target Thresholds**: Mean Latency $< 50\text{ ms}$, P95 Latency $< 75\text{ ms}$, Max Latency $< 150\text{ ms}$.

### Gate 2: Packet Loss and Stale Telemetry Handling
- **Failure Tests**:
  - Test A: Vehicle A powered OFF $\rightarrow$ `ONLINE` $\rightarrow$ `STALE` (3s) $\rightarrow$ `COMMUNICATION DEGRADED` $\rightarrow$ `OFFLINE` (10s). Vehicle B remains `ONLINE`.
  - Test B: Vehicle B LoRa interrupted $\rightarrow$ `TRUCK_02` stale/offline, `TRUCK_01` unaffected.
  - Test C: Communication restored $\rightarrow$ `OFFLINE` $\rightarrow$ `RECOVERING` $\rightarrow$ `ONLINE` (after health confirmation).
  - Test D: Packet loss sweep (0%, 10%, 25%, 50%). Measure detection time, stale timeout, and recovery time.

### Gate 3: HMI → Vehicle Command + ACK Path
- **Commands**: `TARGET_SPEED`, `HOLD`, `STOP`, `RELEASE`.
- **ACK Statuses**: `ACCEPTED`, `CLAMPED`, `REJECTED`, `FAILED`, `TIMEOUT`.
- **Safety Clamping Test**: Request $25.0\text{ m/s}$ ($90\text{ km/h}$) $\rightarrow$ Local safety governor clamps to $10.87\text{ m/s}$ $\rightarrow$ Return ACK `CLAMPED`. Display requested speed, applied speed, and ACK status in HMI.
- **Duplicate Protection**: Reject duplicate `command_id` re-execution.

### Gate 4: Two-Vehicle Concurrent Extended Run
- **Simultaneous Operation**: `TRUCK_01` + `TRUCK_02` active concurrently.
- **Isolation Requirement**: Failure of `TRUCK_01` must NOT interrupt `TRUCK_02` telemetry, change `TRUCK_02` state, or misroute commands.
- **Stability Targets**: Zero vehicle ID cross-contamination, zero memory leak, 100% WebSocket uptime.

---

## 3. What Was NOT Modified

- **Digital Twin**: 100% untouched (`SYNQRA_SIH2026-27-main`, `fog_orchestrator`, `fog_safe`). Zero imports, zero code modifications.
- **Motor Control Logic**: Physical motor direction, PWM drivers (TB6612 & L298N), and interrupt-driven encoder logic (`PULSES_PER_REV = 42.0`) preserved.
- **GPIO Pins**: All hardware pinouts preserved (`GPIO 25, 26, 27, 32, 33, 14, 13, 35, 21, 22, 18, 19, 23, 5, 4, 34`).
