# PHASE 8 — OPERATOR & CONTROL ROOM HMI INTEGRATION REPORT
## FOG-ORCHESTRATOR 2.0 — SIH26007
### In-Cab Situational Awareness, Operational Separation & Driver Restriction Disclosure

---

## 1. Architectural Role Separation (Prompt Section 13)

A fundamental principle of FOG-ORCHESTRATOR 2.0 is the strict separation between vehicle cab safety awareness, control room fleet logistics, and predictive digital twinning:

```
┌─────────────────────────────────┐   ┌─────────────────────────────────┐   ┌─────────────────────────────────┐
│          OPERATOR HMI           │   │        CONTROL ROOM HMI         │   │     PREDICTIVE DIGITAL TWIN     │
│   (truck01.html / In-Cab HUD)   │   │       (Dispatch Console)        │   │       (game_ui.py / Pygame)     │
│                                 │   │                                 │   │                                 │
│ • Local Driver Safety Awareness │   │ • Fleet Logistics & Dispatch    │   │ • Offline / What-If Projections │
│ • Current, Safe & Commanded Spd │   │ • Ore Routing & Bottleneck Mgmt │   │ • Micro-Simulation Dynamics     │
│ • Immediate Action & Reason     │   │ • Fleet Health & Road Capacity  │   │ • 3D Spatial Visualizer         │
│ • RF Comm & Sensor Status       │   │ • Origin Holding Policies       │   │ • Scenario Replay Engine        │
└─────────────────────────────────┘   └─────────────────────────────────┘   └─────────────────────────────────┘
```

> **STRICT ARCHITECTURAL RULE:**  
> The frontends **never** independently calculate safe speed, vehicle kinematics, or friction limits. All three tiers consume authoritative projections from the central Digital Twin and onboard Local Safety Governor.

---

## 2. Operator HMI Data Contract (Prompt Section 12)

The Operator HMI answers the single life-critical question:  
**"What does the dumper operator need to know RIGHT NOW?"**

### Required In-Cab Display Fields:
1. `CURRENT SPEED` — Live vehicle wheel speed from CAN/TWAI odometry.
2. `SAFE SPEED` — Authoritative physical safe ceiling from Tier-1 solver.
3. `COMMANDED SPEED` — Dispatch command clamped by onboard governor.
4. `VISIBILITY` — Current optical sight distance from forward transmissometer/camera.
5. `GRADE` — Road inclination in percent ($\pm 8\%$).
6. `SAFETY STATE` — Live governor operational mode.
7. `COMMUNICATION STATE` — RF link status (`ONLINE`, `DEGRADED`, `LOST`).
8. `BEACON STATE` — Peer V2V safety beacon status (`ACTIVE`, `NONE`).
9. `GATEWAY STATE` — Central LoRa gateway link status (`CONNECTED`, `LOST`).
10. `V2V STATE` — Peer-to-peer 868 MHz link status (`CONNECTED`, `LOST`).
11. `CAN STATE` — Heavy-duty 250 kbps vehicle bus state (`OK`, `BUS_OFF`, `TIMEOUT`).
12. `LOCAL GOVERNOR` — Confirmation of onboard autonomous governor authority (`ACTIVE`).
13. `ACTION` — Immediate driver advisory (`NORMAL`, `CAUTION`, `REDUCE_SPEED`, `SLOW_DOWN`, `STOP`, `EMERGENCY_STOP`).
14. `REASON` — Explicit plain-language explanation of why speed is constrained.

---

## 3. Concrete In-Cab Display Renderings

### Example 1: Severe Fog Onset on Ramp R1 (-8% Downhill)
```
=====================================================
            SYNQRA — OPERATOR SAFETY HUD
=====================================================
CURRENT SPEED        4.0 m/s  (14.4 km/h)
SAFE SPEED           2.4 m/s  ( 8.6 km/h)
COMMAND              2.4 m/s  ( 8.6 km/h)
VISIBILITY            12 m
GRADE               -8.0%
SAFETY STATE         RESTRICTIVE_FOG
COMMUNICATION        ONLINE
BEACON               ACTIVE
GATEWAY              CONNECTED
V2V                  CONNECTED
CAN                  OK
LOCAL GOVERNOR       ACTIVE
-----------------------------------------------------
ACTION               REDUCE SPEED
REASON               LOW_VISIBILITY_FOG (12m sight distance on -8% grade)
=====================================================
```

### Example 2: Total RF Communication Failure
```
=====================================================
            SYNQRA — OPERATOR SAFETY HUD
=====================================================
CURRENT SPEED        3.8 m/s  (13.7 km/h)
SAFE SPEED           3.8 m/s  (13.7 km/h)
COMMAND              3.8 m/s  (13.7 km/h)
VISIBILITY            10 m
GRADE               +0.0%
SAFETY STATE         DEGRADED_TOTAL_COMM_LOSS
COMMUNICATION        LOST
BEACON               NONE
GATEWAY              LOST
V2V                  LOST
CAN                  OK
LOCAL GOVERNOR       ACTIVE
-----------------------------------------------------
ACTION               CAUTION
REASON               TOTAL_RF_FAILURE_LOCAL_GOVERNOR_ACTIVE
=====================================================
```

---

## 4. Reason Disclosure Logic & Traceability

Drivers reject automated safety systems when restrictions appear arbitrary. FOG-ORCHESTRATOR 2.0 dynamically evaluates binding constraints and discloses the exact physical cause:

| Operating Condition | Binding Constraint | Displayed Action | Plain-Language Driver Reason |
|---|---|---|---|
| Visibility drops below 15m | Optical Stopping Distance | `REDUCE_SPEED` | `LOW_VISIBILITY_FOG` |
| Grade exceeds $\pm 6\%$ | Thermal Retarder / Adhesion | `CAUTION` | `STEEP_GRADE_-8.0%` |
| Friction drops to $\mu=0.15$ | Wheel Adhesion / Traction Limit | `SLOW_DOWN` | `SLIPPERY_HAUL_ROAD_REDUCED_TRACTION` |
| Peer Truck Ahead Halts | Peer STOP Beacon (PGN 65281) | `STOP` | `PEER_STOP_BEACON: TRUCK_02 STOPPED IN ZONE_A` |
| Central Dispatch Overspeed | Local Governor Over-speed Clamp | `NORMAL` | `CENTRAL_COMMAND_EXCEEDED_PHYSICAL_LIMIT` |
| Sensor Disconnect | Watchdog Timeout | `EMERGENCY_STOP` | `SENSOR_FAULT: STALE_VEHICLE_SPEED_FRAME` |

---

## 5. Verification & Frontend Consistency

The Python bridge [`OperatorHmiBridge.derive_hmi_state`](file:///c:/Users/JAGADEESH%20M/OneDrive/Documents/SIH-2026-27/integration_adapters/hil_simulator.py) mirrors the frontend logic in [`SYNQRA_SIH2026-27-HMI/frontend/src/screens/OperatorView.tsx`](file:///c:/Users/JAGADEESH%20M/OneDrive/Documents/SIH-2026-27/SYNQRA_SIH2026-27-HMI/frontend/src/screens/OperatorView.tsx). Automated tests in [`tests/test_phase8_hil.py`](file:///c:/Users/JAGADEESH%20M/OneDrive/Documents/SIH-2026-27/tests/test_phase8_hil.py) verify that:
1. Every HUD field is populated without `undefined` or `null`.
2. The reason for restriction is never blank when speed is constrained below free-flow limits.
3. If communication drops, the HUD displays `LOST` but maintains live physical safe speed and confirmation that the local governor is `ACTIVE`.
