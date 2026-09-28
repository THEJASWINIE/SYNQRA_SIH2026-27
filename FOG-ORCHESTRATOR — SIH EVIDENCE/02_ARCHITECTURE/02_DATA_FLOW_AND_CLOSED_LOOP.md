# FOG-ORCHESTRATOR 2.0 — Data Flow & Closed-Loop Dynamics
**Document ID:** `DOC-02-ARCH-02` | **Audited Standard:** End-to-End Causal Verification

---

## 1. The Three Primary Information Loops

The system operates across three tightly decoupled data flows:

### Loop 1: Environmental Fog to Driver Action Loop
```
Weather Station (Fog Injection: F_fog 0.0 -> 1.0)
       ↓ (REST POST /api/environment/fog)
FastAPI Backend & Telemetry Ingestion
       ↓ (Update environmental model)
Authoritative Digital Twin (twin_state_store.py)
       ↓ (Trigger safety recalculation)
Physics Safety Governor (v_safe = min(V_max, v_baseline) * F_fog)
       ↓ (WebSocket push <15 ms)
Driver Operator HMI (truck01.html / truck02.html)
       ↓ (Visual AMBER/RED alert + Audible Chime)
Human Driver Applies Service Brake / Retarder
```

### Loop 2: Vehicle-to-Vehicle (V2V) Peer-to-Peer Loop
```
Vehicle A (TRUCK_01) [TDM Slot: 500 ms]
       ↓ (433 MHz LoRa Packet: STATE,TRUCK_01,seq,rpm,speed,ax,ay,az,gx,gy,gz)
Vehicle B (TRUCK_02) [TDM Slot: 1000 ms] (Direct RX & Relative Range Check)
       ↓ (Forward / Gateway Ingestion)
Host Digital Twin (Inter-vehicle Headway Monitoring & Collision Alert)
```

### Loop 3: Vehicle-to-Infrastructure (V2I) Supervisory Loop
```
ESP32 Vehicles (Wi-Fi 802.11 b/g/n)
       ↓ (HTTP REST POST /api/hardware/telemetry @ 10 Hz)
FastAPI Validation & Normalization Engine
       ↓ (Push to State Store)
Control Room Console (Port 5173 React 19 / Three.js 3D Corridor)
```

---

## 2. Timing and Latency Budget

Across the full closed loop, total latency is strictly budgeted to guarantee timely operator warnings:
- Sensor sampling & encoder interrupt debounce: **10.0 ms**
- ESP32 packet formatting & Wi-Fi transmission: **12.4 ms**
- Backend validation, state store ingestion & physics solving: **5.5 ms**
- WebSocket broadcast to frontend consoles: **14.5 ms**
- Frontend rendering & driver perception time allowance: **40.0 ms**
- **Total End-to-End Latency**: **82.4 ms** (Well below the 250 ms industrial threshold).
