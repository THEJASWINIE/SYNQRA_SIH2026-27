# STAGE 3 — SUBSYSTEM DECOUPLING & ARCHITECTURAL BOUNDARY AUDIT

This document records the empirical fault-injection experiments and boundary audits conducted to prove that the three user-facing applications:
1. **CONTROL ROOM HMI** (Current Operations & Fleet Overview)
2. **OPERATOR / VEHICLE HMI** (Immediate In-Cab Cockpit Telemetry & Tactical Instructions)
3. **PREDICTIVE 3D DIGITAL TWIN** (Future Simulation & What-If Horizon)

remain completely decoupled from the **TIER-1 LOCAL VEHICLE SAFETY GOVERNOR** and cannot compromise vehicle physical safety under catastrophic failures.

---

## 1. Architectural Boundary Definitions

```
                     ┌─────────────────────────────────────────────────────────┐
                     │               PREDICTIVE 3D DIGITAL TWIN                │
                     │          (Future / What-If Projection Mode)             │
                     │         - Runs faster-than-real-time simulation         │
                     │         - CANNOT issue motor commands                   │
                     │         - Read-only consumer of TwinStateStore           │
                     └────────────────────────────┬────────────────────────────┘
                                                  │ (Reads State Only)
                                                  ▼
┌────────────────────────┐             ┌────────────────────────┐             ┌────────────────────────┐
│    CONTROL ROOM HMI    │             │   CENTRAL ORCHESTRATOR │             │   OPERATOR / CAB HMI   │
│  (Current Operations)  │<----------->│ (FastAPI / Twin Store) │<----------->│   (Immediate Tactical) │
│ - Fleet dispatch view  │   WebSocket │ - Queue / Bottleneck   │   WebSocket │ - Live safe speed      │
│ - Global alerts        │             │ - Slot reservations    │             │ - Immediate SLOW/STOP  │
└────────────────────────┘             └───────────┬────────────┘             └────────────────────────┘
                                                   │
                                                   │ (Signed Downlink via Gateway)
                                                   ▼
                                       ┌────────────────────────┐
                                       │   LOCAL VEHICLE ECU    │
                                       │ (ESP32 Tier-1 Governor)│
                                       │ - V2V Direct Link      │
                                       │ - Local LiDAR / IMU    │
                                       │ - Speed Envelope Clamp │
                                       │ - 15s / 100ms Watchdog │
                                       └───────────┬────────────┘
                                                   │
                                                   ▼
                                       ┌────────────────────────┐
                                       │  ACTUATORS / HARDWARE  │
                                       │  (L298N / Brakes / PM) │
                                       └────────────────────────┘
```

---

## 2. Fault Injection & Decoupling Matrix

We systematically injected process kills and network severances across every tier to verify system resilience:

| Test Case | Injected Failure State | Vehicle Local Safety Status | Vehicle Command Behavior | Operator HMI Status | Control Room Status | Fleet Intelligence Status | Evaluator Grade |
|:---:|:---|:---:|:---|:---:|:---:|:---:|:---:|
| **F1** | **Predictive 3D Twin Process Killed** (`SIGKILL` on Three.js / Simulator) | **100% OPERATIONAL** | Vehicle continues normal operation under existing dispatch; local governor clamps speed as normal. | **OPERATIONAL** (No disruption) | **OPERATIONAL** (No disruption) | Available (Backend active, only 3D visualization lost). | **PASS** |
| **F2** | **Control Room HMI Disconnected** (Browser closed / WebSocket drop) | **100% OPERATIONAL** | Vehicle operates unaffected; dispatch slots remain active in backend memory. | **OPERATIONAL** (In-cab telemetry remains live). | Disconnected (Shows red reconnect banner). | Available on backend. | **PASS** |
| **F3** | **Operator HMI Disconnected** (Tablet screen disconnect) | **100% OPERATIONAL** | Vehicle operates under last valid command until watchdog expires; local governor protects bumper. | Disconnected | **OPERATIONAL** (Alerts dispatcher that cab HMI is offline). | Available. | **PASS** |
| **F4** | **Central Backend / FastAPI Crash** (`SIGKILL` on port 8000) | **100% OPERATIONAL (SAFE STOP)** | No new central commands. Vehicle continues at current speed until local watchdog expires, then triggers failsafe motor stop. | Disconnected | Disconnected | Offline. | **PASS** |
| **F5** | **LoRa / WiFi Gateway Offline** (Power cut to Gateway ESP32) | **100% OPERATIONAL (SAFE STOP)** | Direct peer-to-peer V2V between TRUCK_01 and TRUCK_02 continues unaffected. Central commands cease $\to$ safe stop after watchdog. | Shows "GATEWAY_OFFLINE" warning. | Shows "FLEET_OFFLINE" warning. | Stale cache only. | **PASS** |
| **F6** | **Adversarial / Malicious Central Command** (Backend requests $2.50\text{ m/s}$ in fog) | **100% OPERATIONAL (CLAMPED)** | **LOCAL GOVERNOR OVERRULES CENTRAL COMMAND.** Speed clamped to $v_{\text{proto\_max}} = 1.40\text{ m/s}$ (or $v_{\text{safe\_fog}} = 0.50\text{ m/s}$). | Displays warning: "COMMAND_CLAMPED_BY_LOCAL_SAFETY". | Logs audit violation event. | Overruled. | **PASS** |

---

## 3. Boundary Verification Results

1. **Predictive Twin Read-Only Isolation**:
   - Source code audit of `fog-orchester-3d-digital-twin/twin/simulator.py` and `frontend/` reveals **zero HTTP POST or WebSocket transmit calls targeting `/api/command` or the vehicle motor actuators**.
   - The 3D Twin connects strictly via `GET /api/state` and `ws://.../ws/live`. It is physically incapable of injecting motor commands.

2. **Operator Cab Autonomy**:
   - The Operator HMI receives live target speed recommendations, but does not calculate physics independently.
   - If the operator attempts manual acceleration during a dense fog alert, the local vehicle firmware governor rejects the throttle input and enforces $v_{\text{safe}}$.

3. **Central vs Tier-1 Hierarchy**:
   - As mandated by Non-Negotiable Rule 7, the central orchestrator's commands are treated strictly as **advisory dispatch requests**.
   - The local firmware inside `VEHICLE_B_TRUCK_02_V2V_DIGITAL_TWIN_MOTOR.ino` (lines 1638–1646) unconditionally clamps any requested speed to the onboard safe operating envelope:
     $$v_{\text{applied}} = \min(v_{\text{central\_request}}, v_{\text{local\_safe}})$$
