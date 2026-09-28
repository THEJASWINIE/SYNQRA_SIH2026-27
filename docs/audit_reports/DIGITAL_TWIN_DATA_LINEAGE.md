# DIGITAL TWIN DATA LINEAGE & VISUALIZATION ARCHITECTURE
**FOG-ORCHESTRATOR 2.0 — Final Presentation Integration Attack**
**Document ID:** DT-LIN-01  
**Status:** VERIFIED, RIGID & AUTHORITATIVE  
**Scope:** Architecture, Data Lineage, Coordinate Systems & Client Projections of the Authoritative Digital Twin

---

## 1. Executive Summary & Authoritative Role

The **Digital Twin** in FOG-ORCHESTRATOR 2.0 is the single authoritative software representation of the mine, haul roads, vehicles, environmental visibility, dynamic states, and safety constraints.

```
                          [Physical Vehicles]          [Simulation Engine]
                             (TRUCK_01, 02)              (Background Fleet)
                                   │                            │
                                   ▼                            ▼
                       [Hardware Telemetry Ingest]      [Step Integrator]
                                   │                            │
                                   └────────────┬───────────────┘
                                                │
                                                ▼
                                    ┌───────────────────────┐
                                    │  AUTHORITATIVE TWIN   │
                                    │    (Backend Core)     │
                                    └───────────┬───────────┘
                                                │
                     ┌──────────────────────────┼──────────────────────────┐
                     ▼                          ▼                          ▼
            [Control Room HMI]           [Operator HMI]            [3D Digital Twin]
          OperationsOverview.tsx        DriverScreen.tsx          ControlRoom3DTwin.tsx
             (Fleet & Map)              (Cab Speed & Gap)          (Three.js / WebGL)
                     │
                     ▼
            [Pygame Visualization]
                 (game_ui.py)
```

In strict compliance with `AGENTS.md` (Rules 5, 6, 7, and 13):
1. **Rule 5 (One Authoritative Twin):** There is exactly ONE authoritative state model (`fog_orchestrator/tier3_central/digital_twin.py` & `SYNQRA_SIH2026-27-HMI/backend/app/twin_store.py`). Neither the frontend React store, nor Three.js, nor Pygame are state owners.
2. **Rule 6 (Frontend Does Not Invent State):** No client calculates speed, position, safe speed, or visibility independently. Clients are pure presentation projections.
3. **Rule 13 (game_ui.py is a Viewer):** `game_ui.py` connects via an adapter to consume Twin state. It never simulates physics or computes safety limits.
4. **Physical & Simulation Coexistence:** Physical vehicles (`TRUCK_01`, `TRUCK_02`) and simulated fleet vehicles coexist seamlessly in the same Twin interface.

---

## 2. Coordinate Systems & Frame Transformations

The system operates across three strictly distinguished spatial representations:

| Coordinate Frame | Identifier | Base Origin / Units | Applicable Entities | Presentation Disclosure |
| :--- | :--- | :--- | :--- | :--- |
| **Local Odometry Frame** | `LOCAL_ODOMETRY` | Origin $(0, 0)$ at vehicle boot/startup; units in metres. | Physical Vehicles (`TRUCK_01`, `TRUCK_02`) | `LOCAL ODOMETRY · UNSURVEYED CHASSIS · NOT DRAWABLE ON GEOGRAPHIC MAP` |
| **Synthetic Scene Frame** | `SCENE_METRES` | Local mine origin $(0, 0, 0)$; units in metres ($3000\text{ m} \times 3000\text{ m} \times 600\text{ m}$). | Digital Twin 3D Scene / Simulated Fleet | `SYNTHETIC SCENE · SCENE_METRES · DEMONSTRATION · NOT GNSS` |
| **Geographic Mining Context** | `ASSUMED_WGS84_UNVERIFIED` | Bailadila Deposit-5 envelope ($18.67^\circ\text{N}, 81.23^\circ\text{E}$). | Site Background Layer | `ASSUMED_WGS84_UNVERIFIED · NOT AN OFFICIAL LEASE BOUNDARY` |

### 2.1 Why Physical Vehicles Are Not Drawn on Geographic WGS84 Maps
Physical prototype chassis (`TRUCK_01` and `TRUCK_02`) are fitted with wheel optical slot encoders and an MPU6050 6-DOF IMU. They **do not have GNSS receivers**.
- Drawing a vehicle at a fabricated GPS latitude/longitude is an engineering falsehood prohibited by Rule 3.
- When physical hardware connects, the HMI renders `LOCAL ODOMETRY (STANDBY)` and `NOT DRAWABLE (UNSURVEYED CHASSIS)` for map placement.
- When running in **Digital Twin Demo Scenario Mode**, the synthetic route coordinates are displayed in `SCENE_METRES` with explicit `SIMULATION · DIGITAL TWIN` labels.

---

## 3. Data Pipeline & Normalization Lineage

```
1. Physical Hardware / Ingestion Gateway:
   - Wi-Fi POST /api/hardware/telemetry OR Serial LoRa Gateway STATE packet
   - Received raw: seq, rpm, speed, ax, ay, az, gx, gy, gz

2. Telemetry Ingest & Validation (telemetry_ingest.py):
   - Validates schema, timestamps, monotonic sequence, NaN/Inf checks
   - Deduplicates packets arriving over both Wi-Fi and LoRa
   - Normalizes to SI units (RPM -> m/s via 5.45 mm/pulse)

3. Central Twin Store (twin_store.py & digital_twin.py):
   - Stores NormalizedTelemetry record
   - Updates TwinVehicle record: position_s, speed_mps, communication_state, timestamp, freshness

4. Physics / Safety Solver (twin_projection.py & safety_governor.py):
   - Evaluates road geometry, grade, visibility, leading obstacles
   - Calculates v_safe = min(v_stop, v_retarder, v_traction, v_curve, v_mine)
   - Calculates h_safe = S_stop + margin
   - Generates SafetyStateMessage

5. Distribution:
   - Broadcast via FastAPI WebSocket (/ws/state) at 10 Hz
   - Consumed by LiveDataProvider.ts into AppStateStore.ts

6. Presentation Projections:
   - Control Room HMI (OperationsOverview.tsx)
   - Operator HMI (DriverScreen.tsx)
   - 3D Digital Twin (ControlRoom3DTwin.tsx & VehiclePanel.tsx)
   - Pygame (game_ui.py)
```

---

## 4. 3D Digital Twin Viewer Lineage (`ControlRoom3DTwin.tsx` & `src/minecast/`)

The 3D visualization is implemented in WebGL / Three.js. It adheres strictly to the read-only contract:
1. **No Actuation Path:** The 3D viewer contains no command controls, no dispatch endpoints, and no actuation logic.
2. **Zero Client-Side Physics:** Truck meshes are translated and rotated strictly based on positions received from the backend twin (`positionScene` in `SCENE_METRES`).
3. **Terrain Morphology:** The pit surface represents the Bailadila Deposit-5 morphological geometry at $2.5\times$ vertical exaggeration for visual slope clarity. Disclosed in top banner: `SYNTHETIC TERRAIN · NOT SURVEYED · VERTICAL SCALE 2.5x`.
4. **Coexistence of Sources:**
   - Simulated vehicles: Placed along synthetic haul roads based on backend route progress.
   - Physical vehicles: If unsurveyed, rendered in diagnostic panels as `LOCAL ODOMETRY`; if mapped to a demo route, tagged explicitly as `HYBRID (PHYSICAL TELEMETRY + SYNTHETIC SCENE)`.

---

## 5. Pygame Client Lineage (`game_ui.py`)

`game_ui.py` is the 2D visualizer for rapid integration testing:
1. Connects to backend WebSocket or Twin client adapter (`tests/test_game_ui_twin_client.py`).
2. Consumes `TwinVehicle` and `TwinSafety` objects.
3. Renders haul segments, switchbacks, and vehicle icons.
4. **Hostile Invariant:** Does NOT contain vehicle state variables (e.g., `truck_speed`, `truck_pos`). Reads `twin.get_vehicle(vehicle_id).speed_mps` on every redraw frame.

---

## 6. Truth Disclosures & Hostile Evaluator Defense

| Evaluator Question | Authoritative Architectural Defense |
| :--- | :--- |
| **"Where did the 3D map come from?"** | "The 3D map is a synthetic operational corridor model of Bailadila Deposit-5 generated from open elevation data for demonstration. It is not an official surveyed NMDC mine plan." |
| **"Are these physical trucks sending GPS?"** | "No. Physical prototypes A and B are instrumented with wheel encoders and MPU6050 IMUs. They have no GNSS. Their positions are local odometry only. When placed on the 3D scene, they are running in hybrid mode with synthetic scene coordinates." |
| **"Why is safe speed 12 km/h on one screen and standby on another?"** | "They read from the identical backend safety solver. When an active constraint applies (e.g., fog visibility 35m), safe speed is clamped. When unconstrained, it reports standby at the road ceiling." |
| **"Did the frontend calculate stopping distance?"** | "No. Stopping distance and headway are computed by the central physics solver in Python and dispatched over WebSocket. The frontend performs display formatting only." |
