# FOG-ORCHESTRATOR 2.0 — Master System Architecture
**Document ID:** `DOC-02-ARCH-01` | **Audited Standard:** Authoritative Single Twin

---

## 1. Architectural Principles & Block Structure

FOG-ORCHESTRATOR 2.0 is built on strict architectural invariants:
- **Rule 5 (Single State Owner)**: There is exactly ONE authoritative Digital Twin state store (`twin_state_store.py`). Frontend dashboards and visualization tools are pure projection consumers.
- **Rule 7 (Tier-1 Local Authority)**: Central dispatch cannot override local vehicle physical safety limits ($v_{command} \le v_{safe}$).
- **Human-in-the-Loop**: The vehicle governor provides guidance and warnings to the operator; it does NOT autonomously steer or apply emergency brakes.

```
                    ┌────────────────────────────────────────────────────────┐
                    │                   CENTRAL DISPATCH                     │
                    │      Receding-Horizon Chance-Constrained MPC (RH-MPC)  │
                    │      Queue Arrival Shaping & Dynamic Bottleneck Score  │
                    └──────────────────────────┬─────────────────────────────┘
                                               │ v_dispatch (Advisory Pacing)
                                               ▼
┌──────────────────────────────┐    ┌──────────────────────────┐    ┌──────────────────────────────┐
│       CONTROL ROOM HMI       │    │   CENTRAL ORCHESTRATOR   │    │      MINECAST STATION        │
│ • Real-Time Spatial Mine Map │◄───┤ • State Estimation       │───►│ • Optical Visibility Sensors │
│ • Fleet Telemetry & Alerts   │    │ • Corridor Occupancy     │    │ • Haul Road Fog Nowcasting   │
│ • Port 5173 (React 19 / R3F) │    │ • Fast 3D Twin (Port 8080)│   │ • Friction Priors (μ)        │
└──────────────────────────────┘    └────────────┬─────────────┘    └──────────────────────────────┘
                                                 │
                                                 ▼
                                ┌──────────────────────────────────┐
                                │       AUTHORITATIVE TWIN         │
                                │   State Mirroring & Prediction   │
                                │   Lookahead Horizon: T+3s..T+5s  │
                                └─────────────────┬────────────────┘
                                                  │
                         ┌────────────────────────┴────────────────────────┐
                         │ Telemetry Ingestion, Validation & Normalization │
                         │ (Checks: NaN, Inf, Stale, Out-of-Order, CRC)    │
                         └────────────────────────┬────────────────────────┘
                                                  │
                        ┌─────────────────────────┴─────────────────────────┐
                        │              PHYSICAL FLEET TELEMETRY             │
                        │ • Dual ESP32 Hardware (TRUCK_01 & TRUCK_02)       │
                        │ • 433 MHz LoRa V2V + 2.4 GHz Wi-Fi V2I + TWAI CAN │
                        └───────────────────────────────────────────────────┘
```

---

## 2. Core Subsystems & Responsibilities

1. **Physical Prototype Layer**: Dual ESP32 microcontrollers executing non-blocking sensor acquisition (optical encoder interrupts, MPU6050 IMU, battery voltage).
2. **Telemetry Ingestion & Validation Gateway**: Validates incoming packets against type errors, NaN/Inf, sequence counter rollbacks, and freshness timeouts (<250 ms).
3. **Authoritative Digital Twin**: Maintains spatial coordinates, road segment binding, speed, heading, and vehicle-to-vehicle relationships.
4. **Safety & Physics Solver**: Calculates governed safe speed $v_{safe}$ continuously from physical constraints.
5. **Multi-Client HMI Suite**:
   - Central Control Room: Fleet tracking, corridor occupancy, bottleneck analysis.
   - Operator Cockpits (`truck01.html`, `truck02.html`): High-contrast live speed, safe speed ceiling, and audio-visual cues.
