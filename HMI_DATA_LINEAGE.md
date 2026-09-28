# HMI DATA LINEAGE & CONTRACT TRACEABILITY
**FOG-ORCHESTRATOR 2.0 — Final Presentation Integration Attack**
**Document ID:** HMI-LIN-01  
**Status:** VERIFIED, RIGID & AUTHORITATIVE  
**Scope:** Complete End-to-End Data Lineage from Sensor / Simulation Source to Frontend Presentation

---

## 1. Executive Summary & Core Principles

In strict adherence to `AGENTS.md` (Rules 2, 3, 4, 5, 6, 7, 8, and 9):
1. **Zero Fabrication:** Simulated, emulated, and physical data are partitioned and never conflated. Simulation data is explicitly labelled `SIMULATION` / `DIGITAL_TWIN`. Physical hardware data is explicitly labelled `HARDWARE` / `HARDWARE (derived)`.
2. **One Authoritative Twin:** Frontend components consume state; they never calculate vehicle dynamics or invent authoritative speed, safe speed, or map positions.
3. **Explicit SI Units:** Units are explicitly declared (speed in $\text{m/s}$, acceleration in $\text{m/s}^2$, distance in $\text{m}$, grade in $\text{rad}$ / $\%$, angles in $\text{rad}$, timestamp in UTC ISO-8601).
4. **Data Lineage Transparency:** Every visual widget in the Operator HMI (`DriverScreen.tsx`), Control Room HMI (`OperationsOverview.tsx`), and 3D Digital Twin (`VehiclePanel.tsx`) maps to an unbroken lineage back to its physical sensor or twin calculation.
5. **Encoder Physical Truth:**
   - Vehicle A physical optical disc = **42 slots**.
   - Vehicle B physical optical disc = **43 slots**.
   - Empirical odometry calibration divisor = **$K_{cal} = 34.58\text{ pulses/revolution}$**.
   - **CRITICAL:** 34.58 is NOT the physical disc slot count; it is an empirical calibration factor accounting for tire deflection and optical aperture geometry. Never display "PPR = 34.58". Display as `Raw encoder slots` and `Empirical odometry calibration (K_cal)`.

---

## 2. Field-by-Field Data Lineage Matrix

| Display Field | Physical / Model Source | Ingestion Protocol / Endpoint | Backend Model & Field | Normalization & Conversion Formula | SI Unit & Precision | Ingest Rate | Provenance Category | Fallback on Timeout (>2.0s) |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Vehicle Speed (A)** | `TRUCK_01` LM393 slot encoder | LoRa V2V / USB Serial Gateway / Wi-Fi POST `/api/hardware/telemetry` | `NormalizedTelemetry.speed_mps` $\to$ `TwinVehicle.speed_mps` | $v = \frac{\text{RPM} \times \pi \times 0.060}{60}$ | $\text{m/s}$ ($\pm 0.01$) | 10 Hz | `HARDWARE (derived)` / Quality: OK | `STALE` $\to$ `0.0 m/s` (after 5s) |
| **Vehicle Speed (B)** | `TRUCK_02` (Physical LM393 + Command) | Direct Wi-Fi POST `/api/hardware/telemetry` / LoRa V2V | `NormalizedTelemetry.speed_mps` $\to$ `TwinVehicle.speed_mps` | Raw encoder RPM / Commanded target | $\text{m/s}$ ($\pm 0.01$) | 10 Hz | `HARDWARE` / `UNKNOWN` | `UNKNOWN / NOT TELEMETRIED` |
| **Wheel Calibration** | Disc Slot Count + Calibration Divisor | Static Config `physical_vehicle_parameters.json` | `VehicleConfig.k_cal` | A: 42 slots, B: 43 slots, $K_{cal} = 34.58$ | $\text{pulses/rev}$ ($\pm 0.01$) | Static | `PHYSICAL_CALIBRATION` | A: 42 / B: 43 slots, $K_{cal}=34.58$ |
| **Wheel RPM** | LM393 optical slot sensor (A & B) | V2V CSV field 4 / JSON `rpm` | `NormalizedTelemetry.rpm` | $\text{RPM} = \frac{\text{ticks}}{\Delta t \times 34.58} \times 60$ | $\text{RPM}$ ($\pm 0.1$) | 10 Hz | `HARDWARE` (Direct sensor) | `STANDBY / NO TICKS` (0 RPM) |
| **3-Axis Acceleration** | MPU6050 Accelerometer | V2V CSV fields 6,7,8 / JSON `ax, ay, az` | `NormalizedTelemetry.ax, ay, az` | Raw LSB $\to \text{m/s}^2$ ($g \times 9.80665$) | $\text{m/s}^2$ ($\pm 0.01$) | 10 Hz | `HARDWARE` (Direct sensor) | `STANDBY / UNSTREAMED` |
| **3-Axis Gyroscope** | MPU6050 Gyroscope | V2V CSV fields 9,10,11 / JSON `gx, gy, gz` | `NormalizedTelemetry.gx, gy, gz` | Raw LSB $\to \text{rad/s}$ | $\text{rad/s}$ ($\pm 0.001$) | 10 Hz | `HARDWARE` (Direct sensor) | `STANDBY / UNSTREAMED` |
| **Safe Speed ($v_{\text{safe}}$)** | Central Physics Solver | Backend Internal Safety Pipeline | `SafetyStateMessage.v_safe` | $\min(v_{\text{stop}}, v_{\text{retarder}}, v_{\text{traction}}, v_{\text{curve}}, v_{\text{mine}})$ | $\text{m/s}$ ($\pm 0.1$) | 10 Hz | `CALCULATED / AUTHORITATIVE` | `STANDBY (ROAD CEILING)` / `0.0 m/s` |
| **Dispatch Target Speed** | Optimization Engine | Central Dispatch Scheduler | `DispatchCommandMessage.target_speed` | Segment max capability | $\text{m/s}$ ($\pm 0.1$) | 1 Hz | `DISPATCH / COMMAND` | `NO ACTIVE COMMAND` |
| **Applied Speed** | Motor Tachometer Feedback | None (Prototype chassis lacks sensor) | None | No physical feedback loop on chassis | $\text{m/s}$ | N/A | `NOT_INSTRUMENTED` | `UNKNOWN / NOT TELEMETRIED` |
| **Governor Status** | Vehicle Safety Governor | Local Safety Enforcement / Twin | `SafetyStateMessage.governor_active` | Clamps speed if $v_{actual} > v_{safe}$ | Categorical | 10 Hz | `AUTHORITATIVE_GOVERNOR` | `STANDBY` |
| **Effective Visibility** | Fog Simulation / Ambient Sensor | Road Model Ingest | `RoadStateMessage.visibility_m` | Meteorological optical range | Metres ($\pm 1.0$) | 1 Hz | `SIMULATION` / `INJECTED_SCENARIO` | `UNAVAILABLE` |
| **Safe Headway ($h_{\text{safe}}$)** | Proximity Engine | Central Safety Solver | `SafetyStateMessage.h_safe` | $S_{stop} + S_{margin}$ | Metres ($\pm 0.5$) | 10 Hz | `CALCULATED / DERIVED` | `UNAVAILABLE` |
| **Actual Headway (Gap)** | Radar / Coordinate Delta | Digital Twin Spatial Query | `SafetyStateMessage.headway_current` | Euclidean distance between vectors | Metres ($\pm 0.1$) | 10 Hz | `CALCULATED / DERIVED` | `UNAVAILABLE` |
| **Lead Vehicle** | Convoy Relationship Model | Digital Twin Graph / Scenario | `SafetyStateMessage.lead_vehicle_id` | Vehicle immediately ahead on segment | String | 10 Hz | `DIGITAL_TWIN / SIMULATION` | `UNAVAILABLE` |
| **Road Grade** | Mine Digital Elevation Model (DEM) | GIS Road Network Store | `RoadStateMessage.grade` | $\frac{\Delta z}{\Delta s} \times 100$ | $\text{rad}$ / $\%$ ($\pm 0.1$) | Static / 1 Hz | `SURVEY / SCENE MODEL` | `UNAVAILABLE` |
| **Friction Estimate** | Road Model Surface State | GIS Road Network Store | `RoadStateMessage.friction` | $\mu \pm \sigma$ | Dimensionless | 1 Hz | `SIMULATION / INJECTED` | `UNAVAILABLE` |
| **Boot ID** | ESP32 Non-Volatile Storage (NVS) | V2V CSV / JSON `boot_id` | `NormalizedTelemetry.boot_id` | Monotonic flash boot counter | Integer | On Boot / 1 Hz | `HARDWARE` | `RUN #01 (STANDBY)` |
| **Sequence Number** | ESP32 Monotonic Global Counter | V2V CSV field 3 / JSON `sequence` | `NormalizedTelemetry.sequence` | Incremented per packet sent | Integer | 10 Hz | `HARDWARE` | Stalled sequence flags warning |
| **Safe Beacon Active** | ESP32 Wi-Fi Dropout Monitor | LoRa V2V Broadcast (`BEACON,...`) | `NormalizedTelemetry.safe_beacon` | True if Wi-Fi disconnect $> 3.0\text{ s}$ | Boolean | 1.0 Hz | `HARDWARE / FIRMWARE_READY` | `STANDBY · FIELD GATE PENDING` |
| **RF Failover** | Dual-Radio Link Monitor | Failsafe Controller | `FailsafeState.rf_failover` | Switches Wi-Fi $\to$ LoRa on packet loss | Categorical | 10 Hz | `SOFTWARE_READY / FIELD_PENDING`| `AVAILABLE — FAILOVER VALIDATION PENDING` |
| **GNSS Position** | GPS/GLONASS/NavIC Module | None (Not fitted on chassis) | None | Prototype uses wheel/IMU odometry | Lat/Lon | N/A | `NOT_FITTED` | `NOT FITTED ON CHASSIS` |
| **V2I Communication** | Dedicated Short-Range Roadside Unit | None (No physical RSU deployed) | None | Prototype uses local Wi-Fi gateway | Categorical | N/A | `NOT_INSTRUMENTED` | `NOT INSTRUMENTED · NO PHYSICAL RSU` |

---

## 3. Detailed Data Pipeline Flow

```
[Physical Sensors / ESP32]
  - LM393 Optical Encoder (Ticks)
  - MPU6050 IMU (ax, ay, az, gx, gy, gz)
  - NVS Flash (Boot ID, Sequence)
         │
         ├─── Wi-Fi (HTTP POST) ───► [FastAPI Gateway /api/hardware/telemetry]
         └─── LoRa (SX1278 433MHz) ─► [USB Serial Gateway Reader] ───────────────┐
                                                                                  │
                                                                                  ▼
                                                                     [telemetry_ingest.py]
                                                                       - Format validation
                                                                       - Deduplication
                                                                       - Unit normalization
                                                                                  │
                                                                                  ▼
                                                                        [Authoritative Twin]
                                                                       - vehicle_telemetry_store
                                                                       - twin_store
                                                                                  │
                                                                                  ▼
                                                                      [Physics / Safety Solver]
                                                                       - Stopping distance
                                                                       - v_safe, h_safe
                                                                       - Governor clamp
                                                                                  │
                                                                                  ▼
                                                                     [FastAPI WebSocket /ws/state]
                                                                                  │
                                                                                  ▼
                                                                        [LiveDataProvider.ts]
                                                                                  │
                                                                                  ▼
                                                                        [AppStateStore.ts]
                                                                                  │
                                                                                  ▼
                                                   ┌──────────────────────────────┼──────────────────────────────┐
                                                   ▼                              ▼                              ▼
                                        [OperationsOverview.tsx]          [DriverScreen.tsx]           [VehiclePanel.tsx (3D)]
                                           Control Room HMI                  Operator HMI                  Digital Twin
```

---

## 4. Contract Wire Protocols & Schemas

### 4.1 V2V LoRa Telemetry Protocol (Legacy & Physical Wire Standard)
Preserved without breaking changes under Rule 2:
```text
STATE,TRUCK_01,seq,rpm,speed,ax,ay,az,gx,gy,gz
STATE,TRUCK_02,seq,rpm,speed,ax,ay,az,gx,gy,gz
```
- **Field 1:** Header (`STATE`)
- **Field 2:** Vehicle Identifier (`TRUCK_01` or `TRUCK_02`)
- **Field 3:** Monotonic Sequence Counter (`uint32_t`)
- **Field 4:** Optical Slot Wheel Speed (`float RPM`)
- **Field 5:** Reported Speed (`float m/s`) — Note: TRUCK_01 derives from RPM; TRUCK_02 reports commanded prototype target
- **Fields 6–8:** 3-Axis Linear Acceleration ($a_x, a_y, a_z$ in $\text{m/s}^2$)
- **Fields 9–11:** 3-Axis Angular Velocity ($g_x, g_y, g_z$ in $\text{rad/s}$)

### 4.2 Safe Beacon Protocol (Emergency Broadcast)
Emitted by vehicle autonomously at 1.0 Hz whenever primary V2I connection is lost for $>3.0\text{ s}$:
```text
BEACON,TRUCK_02,seq,boot_id,last_known_speed,uptime_ms
```

### 4.3 Direct Wi-Fi Telemetry JSON (`POST /api/hardware/telemetry`)
```json
{
  "vehicle_id": "TRUCK_02",
  "boot_id": 4,
  "sequence": 1492,
  "timestamp": 1774889201.12,
  "rpm": 124.5,
  "speed_mps": 0.39,
  "ax": 0.08,
  "ay": -0.02,
  "az": 9.81,
  "gx": 0.01,
  "gy": -0.01,
  "gz": 0.00,
  "transport": "WIFI",
  "safe_beacon": false
}
```

### 4.4 WebSocket Live Broadcast Schema (`/ws/state`)
```json
{
  "type": "TWIN_STATE_UPDATE",
  "timestamp": 1774889201.15,
  "vehicles": [
    {
      "vehicle_id": "TRUCK_01",
      "speed_mps": 0.42,
      "position_s": 145.2,
      "segment_id": "HAUL_ROAD_SOUTH_02",
      "communication_state": "HEALTHY",
      "provenance": {
        "source": "HARDWARE (derived)",
        "timestamp": 1774889201.12,
        "freshness_ms": 30,
        "boot_id": 12,
        "sequence": 8412
      }
    }
  ],
  "safety": [
    {
      "vehicle_id": "TRUCK_01",
      "v_safe": 2.50,
      "h_safe": 18.5,
      "risk_level": 0.12,
      "active_constraint": "FOG_VISIBILITY_35M"
    }
  ],
  "environment": {
    "visibility_m": 35.0,
    "fog_state": "FOG_PATCH"
  }
}
```

---

## 5. Odometry Calibration Physics & Disclosures

### 5.1 Physical Disc Slot Count
- **Vehicle A Disc:** 42 physical slots.
- **Vehicle B Disc:** 43 physical slots.
- **Wheel Diameter ($D$):** $0.060\text{ m}$ ($60\text{ mm}$).
- **Nominal Wheel Circumference ($C$):** $\pi \times D = 0.188496\text{ m}$.

### 5.2 Empirical Calibration Factor ($K_{cal}$)
- **Empirical Value:** $K_{cal} = 34.58\text{ pulses/revolution}$.
- **Resolution:** $\Delta s = \frac{C}{K_{cal}} = \frac{0.188496}{34.58} = 0.005451\text{ m/pulse} = 5.45\text{ mm/pulse}$.
- **Speed Calculation:**
  $$v = \frac{\text{RPM} \times C}{60} = \frac{\text{ticks} \times \Delta s}{\Delta t}$$
- **Disclose to Evaluators:** $34.58$ is strictly the empirical divisor calibrated against floor ground truth, NOT the physical disc slot count (which is 42 or 43).

---

## 6. Freshness & Staleness Lifecycle

```
[Packet Ingestion]
        │  t = 0.0s  (Status: FRESH · Green)
        ▼
   [0.0s - 2.0s]      (Normal Operational Window)
        │
        ▼
   [2.0s - 5.0s]      (Status: DEGRADED / STALE · Amber)
        │              - HMI renders "STALE" badge with measured age
        │              - Physics solver expands safety margin
        │              - Speed comparison preserved with staleness warning
        ▼
     [> 5.0s]         (Status: LOST / TIMEOUT · Red)
                       - HMI renders "OFFLINE"
                       - Safety solver commands safe stop (0.0 m/s)
                       - Central Dispatch removes vehicle from active haul slot
```

---

## 7. Architectural Compliance Sign-Off

- **Rule 3 & 23 Audit:** Physical vs Simulation vs Hybrid cleanly separated across every field.
- **Rule 4 Audit:** Zero live sensor values hardcoded in frontend components or API responses.
- **Rule 5 Audit:** One authoritative Digital Twin state store; frontend is purely a projection.
- **Rule 6 Audit:** Frontend derives no vehicle speed, position, or safe speed.
- **Rule 8 Audit:** Explicit SI units enforced across all wire protocols and models.
- **Rule 9 Audit:** Every dynamic entity carries timestamp, source, sequence, and freshness.
