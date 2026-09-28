# FINAL ARCHITECTURAL SPECIFICATION
## FOG-ORCHESTRATOR 2.0 — SIH 2026-27 (Problem Statement SIH26007)
### Authoritative System Architecture, Three Authority Layers & Invariant Hierarchy

---

## 1. Locked System Architecture

The fundamental control loop of FOG-ORCHESTRATOR 2.0 couples physics-constrained local vehicle safety with predictive fleet-level macro-orchestration across the open-cast haulage network:

```
ENVIRONMENT (Fog / Rain / Dust / Road Slurry)
    ↓
VEHICLE PHYSICS (Mass, Grade, Crr, Friction, Retarder, Air-Hydraulic Brakes)
    ↓
SAFE OPERATING ENVELOPE (v_stop, S_stop, S_base, v_safe)
    ↓
ROAD CAPACITY (Kinematic Flux: C_road = 3600 * v_safe / H_space)
    ↓
QUEUE / BOTTLENECK FORMATION (Inflow > Capacity on Ramp)
    ↓
PREDICTION / WHAT-IF SOLVER (Bottleneck Severity Horizon)
    ↓
FLEET ORCHESTRATION (Dynamic Staging at Flat Shovel Bays)
    ↓
ROAD / VEHICLE ACTIONS (HOLD, RELEASE, SLOT, DISPATCH)
    ↓
TELEMETRY INGESTION (CAN / TWAI 250 kbps, LoRa SX1278 V2V)
    ↺ DIGITAL TWIN (Authoritative Real-Time State Store)
```

---

## 2. Three Hierarchical Authority Layers

To enforce fail-safe operation under degraded visibility or total communication failure, the architecture maintains a strict three-tier hierarchy of authority:

```
+-----------------------------------------------------------------------------+
| LAYER 3: CENTRAL FLEET INTELLIGENCE                                         |
| Role: Macro-Optimization, Predictive Bottleneck Prevention, Origin Metering |
| Authority: Advisory / Proactive Dispatch Proposals (v_dispatch, HOLD, SLOT)  |
| Subsystems: Digital Twin Core, What-If Solver, Origin Staging Orchestrator  |
+-----------------------------------------------------------------------------+
                                      │
                                      ▼ (Advisory Proposals)
+-----------------------------------------------------------------------------+
| LAYER 2: ROAD / INFRASTRUCTURE ARBITRATION                                  |
| Role: Spatial Conflict Resolution, Narrow Road Metering, Switchback Priority|
| Authority: Segment Reservation / Virtual Slot Allocation                    |
| Subsystems: Infrastructure Beacons, Virtual Slot Manager, Road Capacity Mdl |
+-----------------------------------------------------------------------------+
                                      │
                                      ▼ (Corridor Authorization)
+-----------------------------------------------------------------------------+
| LAYER 1: VEHICLE LOCAL SAFETY (UNCONDITIONAL HIGHEST AUTHORITY)             |
| Role: Life-Critical Kinematic Protection & Emergency Braking Containment     |
| Authority: ABSOLUTE. Central commands CANNOT override Tier-1 governor.      |
| Subsystems: Wheel Speed IMU, Physics Solver, Actuator Watchdog, Fallback    |
| Invariant: v_command = min(v_dispatch, v_safe)                              |
+-----------------------------------------------------------------------------+
```

### Layer 1: Vehicle Safety (Local Autonomy)
- **Authority:** Absolute over all vehicle motion actuators.
- **Components:** Onboard ESP32 microcontroller, dual-core FreeRTOS task, CCVS wheel speed sampling, IMU acceleration monitoring, analytical quadratic solver (`calculate_v_stop`), pneumatic actuator watchdog.
- **Non-Negotiable Rule:** The local vehicle safety governor independently calculates $v_{\text{safe}}$ from onboard perception and physical parameters. If central dispatch requests $30.0\text{ m/s}$ on a foggy ramp where $v_{\text{safe}} = 5.12\text{ m/s}$, the governor immediately clamps the command:
  $$v_{\text{applied}} = \min(30.0, 5.12) = 5.12\text{ m/s}$$

### Layer 2: Road & Infrastructure Arbitration
- **Authority:** Spatial occupancy and corridor entry permissions.
- **Components:** Virtual slot reservations, single-lane narrow road tokens, switchback hairpin priority logic.
- **Function:** Prevents multi-truck opposing deadlocks and ensures that haulers entering steep -8% gradients maintain the required $22.52\text{ m}$ space headway envelope.

### Layer 3: Central Fleet Intelligence
- **Authority:** Macro-schedule pacing, shovel-to-crusher route assignments, and origin staging holding.
- **Components:** Authoritative Digital Twin (`twin_state.py`), what-if bottleneck predictor, crusher intake pacer.
- **Function:** Detects that downhill ramp capacity has collapsed due to fog ($817.8 \to 450\text{ VPH}$) and proactively holds trailing haulers at flat shovel loading benches, preventing dangerous queue formation on steep slopes.

---

## 3. The Digital Twin as Single Authoritative Source of Truth

The Digital Twin is **NOT** a visualization client or a passive 3D animation. It is the authoritative software state store of the physical mine:

```
PHYSICAL SENSORS (ESP32, IMU, CAN) / SIMULATED VEHICLE ECU
                     │
                     ▼
         TELEMETRY INGESTION PIPELINE
  (Decode -> Validate Types -> Plausibility -> Normalize)
                     │
                     ▼
           DIGITAL TWIN CORE STORE
   - Vehicles: ID, Position, Speed, RPM, Comm State, Freshness
   - Roads: Geometry, Grade, Capacity, Occupancy, Visibility
   - Environment: Fog Level, Surface Friction, Uncertainty
   - Relationships: LocatedOn, Following, StagedAt
                     │
         ┌───────────┴───────────┐
         ▼                       ▼
    OPERATOR HUD           CONTROL ROOM HMI
(In-Cab Presentation)   (Macro-Fleet Dashboard)
```

### Core Twin Ingestion Rules:
1. **Rule 4 & 5 Compliance:** Frontend dashboards and Pygame clients **NEVER** invent vehicle speed, position, or safe speed. They query the Digital Twin via WebSocket.
2. **Freshness & Provenance:** Every state entity carries a timestamp, source identifier (`HARDWARE`, `SIMULATION`, `HIL`), and freshness status (`LIVE`, `STALE`, `TIMEOUT`).
3. **Fail-Closed Decoupling:** One malformed telemetry frame (e.g. `NaN` speed or CRC failure) is discarded at the validation stage and never corrupts the central Twin state.

---

## 4. Communication Failure & Fallback Hierarchy

To eliminate single points of failure, the communication infrastructure employs a 4-tier failover mechanism:

1. **Tier 1 (Primary): DSSS / LoRa Gateway Network:**
   - Long-range coordination between central fleet dispatch and haul trucks. Transmits macro-staging commands and route assignments.
2. **Tier 2 (Secondary Fallback): Peer-to-Peer V2V Broadcast:**
   - When the central gateway fails, haulers exchange direct 10 Hz `STATE` packets containing position, speed, and acceleration. Vehicles automatically form cooperative platoons.
3. **Tier 3 (Defensive Fallback): Safe Beacons:**
   - If peer V2V drops, asynchronous 2 Hz Safe Beacons broadcast emergency zone warnings (`STOP`, `EMERGENCY`, `SLOW`). The receiver immediately increases space headway by $2\times$.
4. **Tier 4 (Ultimate Fallback): Onboard Sensor Autonomy:**
   - In total RF silence (all wireless dead), the vehicle operates completely independently using local wheel encoders and optical sightlines. Speed is clamped to local $v_{\text{safe}}$, and the truck safely crawls or stages without risk of runaway.

---

## 5. Summary of System Invariants

| Invariant ID | Mathematical Expression | Architectural Enforcement |
|---|---|---|
| **I1** | $v_{\text{applied}} \le v_{\text{safe}}$ | Enforced in firmware on onboard Tier-1 safety governor. |
| **I2** | $S_{\text{stop}} + S_{\text{base}} \le R_{\text{effective}}$ | Stopping quadratic root solved before command actuation. |
| **I3** | $R_{\text{effective}} \le 5.0\text{ m} \implies v_{\text{safe}} = 0.0$ | Blindout boundary forces controlled halt / staging. |
| **I4** | $\text{COMM\_LOSS} \implies \text{Governor Active}$ | Transport loss derates speed; does not cause vehicle runaway. |
| **I5** | $\text{Sensor Corrupt (NaN, Inf)} \implies v_{\text{safe}} = 0.0$ | Fail-closed exception handling in telemetry pipeline. |
| **I6** | $C_{\text{crusher}} \le 1647.0\text{ TPH}$ | Physical crusher tipping pocket intake barrier strictly bounded. |
