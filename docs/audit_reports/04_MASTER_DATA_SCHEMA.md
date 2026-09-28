# 04 — MASTER DATA SCHEMA: CANONICAL VEHICLE STATE
## FOG-ORCHESTRATOR 2.0 | SIH 2026-27 (Problem Statement: SIH26007)
### NMDC Bailadila Low-Visibility HEMM Safety & Operational Intelligence System
**Document ID:** `04_MASTER_DATA_SCHEMA.md`  
**Phase:** 9 — Full Hardware + Software + HMI + Control Room + Digital Twin Integration  
**Status:** AUTHORITATIVE & FROZEN  

---

## 1. Executive Mandate: One Authoritative State Model, Multiple Views

In accordance with **Rule 5 (One authoritative Digital Twin)** and **Rule 6 (Frontend must not invent vehicle state)**:
1. There is **EXACTLY ONE** canonical vehicle state schema (`VehicleState`).
2. Competing state stores across the Operator HMI, Control Room HMI, Digital Twin, and Local Safety Governor are strictly forbidden.
3. Every subsystem consumes an authoritative projection generated directly from this single canonical state.

```
                     +=========================================+
                     |         CANONICAL VehicleState          |
                     |  Single Authoritative Source of Truth   |
                     +====================+====================+
                                          |
        +------------------+--------------+-------------+------------------+
        |                  |                            |                  |
        v                  v                            v                  v
+---------------+  +------------------+         +---------------+  +---------------+
| OPERATOR HMI  |  | CONTROL ROOM HMI |         | DIGITAL TWIN  |  | LOCAL SAFETY  |
|  Driver View  |  |    Fleet View    |         | Mirror & Sim  |  |   Governor    |
+---------------+  +------------------+         +---------------+  +---------------+
```

---

## 2. Canonical Schema Definition (`VehicleState`)

The master schema is implemented in Python as `integration_adapters.master_data_model.VehicleState` and defined below:

| Field Name | Type | Unit / Enum | Default / Valid Range | Subsystem Relevance | Description |
|:---|:---|:---|:---|:---|:---|
| `vehicle_id` | `str` | ASCII String | e.g. `"TRUCK_01"` | All | Unique identifier of physical/simulated HEMM |
| `data_source` | `Enum` | `HARDWARE`, `SIMULATION`, `HYBRID` | `HARDWARE` | All | Truthful data provenance tag (Rule 3) |
| `event_timestamp` | `float` | Seconds (Unix epoch / Monotonic) | $\ge 0.0$ | Timing Policy | Timestamp of raw sensor sampling at vehicle ECU |
| `receive_timestamp` | `float` | Seconds (Unix epoch UTC) | $\ge 0.0$ | Gateway / Uplink | Timestamp of packet reception at RF Gateway |
| `processing_timestamp` | `float` | Seconds (Unix epoch UTC) | $\ge 0.0$ | Orchestrator | Timestamp of state ingestion by central backend |
| `clock_source` | `str` | String Tag | `UTC_NTP`, `GPS_PPS`, `LOCAL_MONOTONIC` | All | Source of hardware timebase |
| `position` | `float` | Metres ($m$) | Segment relative $[0.0, L_{\text{seg}}]$ | Twin / HMI | Position along current haul road segment |
| `position_x` | `float` | Metres ($m$) | Mine grid Cartesian X | Twin / Control Room | Spatial mine grid coordinate |
| `position_y` | `float` | Metres ($m$) | Mine grid Cartesian Y | Twin / Control Room | Spatial mine grid coordinate |
| `segment_id` | `str` | Segment Identifier | e.g. `"RAMP_R1"` | All | Current haul road segment association |
| `heading` | `float` | Radians ($rad$) | $[-\pi, +\pi]$ | Twin / Navigation | Vehicle forward azimuth angle |
| `speed` | `float` | Metres / second ($m/s$) | $[0.0, 18.0]$ ($0-65\text{ km/h}$) | All | Measured physical wheel / odometry speed |
| `acceleration` | `float` | $m/s^2$ | $[-5.0, +3.0]$ | Governor / Twin | Longitudinal acceleration |
| `grade` | `float` | Percent ($\%$) | $[-15.0\%, +15.0\%]$ | Governor / Physics | Haul road slope (negative=downhill, positive=uphill) |
| `visibility` | `float` | Metres ($m$) | $[0.0, 500.0]$ | Governor / Twin / HMI | Effective fog optical visibility distance |
| `weather_state` | `str` | String Tag | `CLEAR`, `DENSE_FOG`, etc. | Twin / Dispatch | Environmental meteorological classification |
| `sensor_health` | `Enum` | 8-State SensorQuality | `VALID`, `DEGRADED`, `STALE`... | Governor / HMI | Diagnostic status of critical sensor stream |
| `sensor_confidence`| `float` | Scalar Ratio | $[0.0, 1.0]$ | Governor / Twin | Uncertainty metric derived by data-health engine |
| `gateway_id` | `str` | Gateway Tag | e.g. `"GW_01"`, `"GW_02"` | RF Management | Active serving communication gateway |
| `gateway_state` | `str` | Enum / String | `CONNECTED`, `DEGRADED`... | RF / Comms | Status of serving RF link |
| `correlation_score`| `float` | Normalized Correlation | $[0.0, 1.0]$ | RF Research Adapter | DSSS/PN or CSS correlation metric |
| `RSSI` | `float` | $dBm$ | $[-130.0, -30.0]$ | Diagnostics | Received RF Signal Strength Indicator |
| `SNR` | `float` | $dB$ | $[-20.0, +25.0]$ | Diagnostics | Signal-to-Noise Ratio |
| `packet_loss` | `float` | Ratio | $[0.0, 1.0]$ | RF Link Health | Sliding window packet loss rate |
| `CAN_state` | `Enum` | `NORMAL`, `DEGRADED`, `TIMEOUT`, `BUS_OFF` | `NORMAL` | Vehicle ECU / Gov | Onboard CAN / TWAI bus health |
| `CAN_latency` | `float` | Milliseconds ($ms$) | $[0.5, 50.0]$ | ECU Diagnostics | CAN frame arbitration + transmission latency |
| `commanded_speed` | `float` | Metres / second ($m/s$) | $[0.0, 18.0]$ | Governor | Target speed dispatched from central or driver |
| `safe_speed` | `float` | Metres / second ($m/s$) | $[0.0, 18.0]$ | All | Authoritative Tier-1 safe speed envelope limit |
| `brake_state` | `str` | Enum Tag | `RELEASED`, `ACTIVE`, `HOLD` | All | Service & retarder brake actuation status |
| `safety_state` | `Enum` | 6-State SafetyState | `NORMAL`, `WARNING`, `SAFE MODE` | All | Integrated system safety condition |
| `failsafe_state` | `str` | String Tag | `NOMINAL`, `SAFE_BEACON`... | Governor / HMI | Autonomous failsafe state-machine stage |
| `safe_beacon_state`| `str` | `INACTIVE`, `ACTIVE`, `RECOVERY` | `INACTIVE` | RF / Comms Loss | Autonomous failsafe RF beacon broadcast state |
| `fault_code` | `str` | DTC Code | e.g. `"NONE"`, `"F_SENSOR_DROP"` | Diagnostics | Active diagnostic trouble code |
| `digital_twin_sync_state`| `Enum` | `SYNCHRONIZED`, `DRIFTING`, `DIVERGENT` | `SYNCHRONIZED` | Twin / Control Room | Real-to-Twin synchronization metric |

---

## 3. Timestamp and Time-Synchronization Policy (Section 5)

Every telemetry packet and state evaluation contains three distinct timestamps:
1. `event_timestamp`: Time of physical sensor measurement at the vehicle microcontroller ($t_0$).
2. `receive_timestamp`: Time of RF packet ingestion at the physical gateway ($t_1$).
3. `processing_timestamp`: Time of canonical validation and state update at the backend ($t_2$).

### Data Age and Freshness Display:
The system computes real-time data age as:
$$\Delta t_{\text{age}} = t_{\text{current}} - t_{\text{event}}$$

- **Live Data:** $\Delta t_{\text{age}} < 1000\text{ ms} \implies$ Displayed as `DATA AGE: xxx ms`
- **Stale Data:** $\Delta t_{\text{age}} \ge 1000\text{ ms} \implies$ Displayed as `STALE: x.x s` in amber/red with immediate transition to conservative holding envelope.
- **Rule of Display:** Under no circumstances shall stale telemetry be displayed as live data.

---

## 4. Specialized View Projections

### View 1: Operator HMI View (`to_operator_hmi_view()`)
- **Target:** Truck Cab Driver Display (`SYNQRA_SIH2026-27-HMI/frontend/src/vehicle/DriverScreen.tsx`).
- **Included Fields:**
  - `speed_kmh`, `safe_speed_kmh`
  - `visibility_m`, `grade_pct`
  - `brake_status`, `sensor_health`
  - `communication_status`, `gateway_status`
  - `safety_state`, `active_warning`, `data_age_label`
- **Design Philosophy:** Clean, uncluttered, focused exclusively on immediate situational guidance and speed envelope limits.

### View 2: Control Room HMI View (`to_control_room_view()`)
- **Target:** Mine Fleet Dispatch & Monitoring Console.
- **Included Fields:** Full vehicle kinematics, spatial coordinates, gateway signal strength (RSSI/SNR), packet loss, CAN latency, failsafe state, Safe Beacon status, Digital Twin synchronization state, and data age.
- **Design Philosophy:** Fleet-wide situational awareness, bottleneck tracking, and incident escalation.

### View 3: Digital Twin View (`to_digital_twin_view()`)
- **Target:** 3D/2D Spatial Mine Model & Predictive What-If Engine.
- **Included Fields:** Exact segment offset, heading, continuous velocity, grade, surface friction $\mu$, sensor quality, and synchronization error.
- **Design Philosophy:** High-fidelity simulation and lookahead prediction without control authority.

### View 4: Local Safety Governor View (`to_safety_governor_view()`)
- **Target:** Onboard Vehicle Tier-1 Safety Solver.
- **Included Fields:** Physical speed, commanded speed, real visibility, grade, sensor quality, and Safe Beacon trigger status.
- **Design Philosophy:** Hard real-time execution of the stopping envelope solver to determine actuator actuation.
