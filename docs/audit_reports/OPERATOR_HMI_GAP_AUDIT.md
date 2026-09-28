# OPERATOR HMI GAP AUDIT
**FOG-ORCHESTRATOR 2.0 — Pre-Final Integration Closure**
**Document ID:** HMI-AUD-OP-01  
**Target Vehicle:** `TRUCK_01` / `TRUCK_02` (Operator Cab HMI)  
**Component:** `SYNQRA_SIH2026-27-HMI/frontend/src/vehicle/DriverScreen.tsx`  
**Status:** COMPLETE / CLOSED

---

## 1. Executive Summary & Design Philosophy

The Operator HMI (`DriverScreen.tsx`) is designed specifically for the in-cab display of haul truck operators operating in low-visibility open-pit mining environments (e.g., NMDC Donimalai / synthetic pit mine).

Under Rule 6 and Section 12 of `AGENTS.md`:
> *"The Operator HMI is different from the control-room dashboard. It should answer: 'What does the dumper operator need to know RIGHT NOW?' Prioritize: current speed, safe speed, commanded speed, visibility, warning / safety state, road / grade, communication state, immediate operational instruction."*

The Operator HMI maintains a strict vehicle-centric focus. It does not replicate supervisory fleet orchestration views, switchback capacity planners, or global GIS route managers. Instead, it provides actionable, glanceable, high-contrast operational awareness and safety governor telemetry.

---

## 2. Screen Region Audit & Data Lineage

| Region / Widget | Purpose & Operational Question | Data Source / Field | Unit / Format | Refresh Rate | Degraded / Disconnect Behavior |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Header Status Bar** | "Am I connected to the Twin & what is my vehicle ID?" | `useHmiStore.getState().isConnected`, `vehicleId`, `networkState` | Text / Status Badge | 10 Hz (WS) | Displays `OFFLINE / DISCONNECTED` in red; shows reconnect counter |
| **Speedometer Cluster** | "How fast am I moving right now?" | `vehicle.speedMps` (Twin authoritative state) | km/h & m/s (Primary display: m/s with km/h subtext) | 10 Hz | If stale (>2.0s), displays `STALE (last valid)`; if no signal, displays `0.0 m/s` with warning |
| **Speed Governor Triad** | "What speed is requested, what is my safe limit, and what is commanded?" | 1. Requested: `dispatch_target_mps`<br>2. Safe Limit: `safety.vSafe`<br>3. Commanded: `UNKNOWN / NOT TELEMETRIED` | m/s | 10 Hz | If governor clamps, highlights delta in amber/red with intervention banner |
| **Dynamic Visibility Bar** | "What is the effective forward visibility in fog?" | `environment.visibility_m` | Metres (0–500m bar) | 1 Hz | Flags `DENSE FOG` (<30m) or `FOG PATCH` (30–100m) with warning colorway |
| **Road & Grade Profile** | "What grade and road segment am I on?" | `road.grade_percent`, `road.segment_id`, `road.surface_condition` | % grade & segment ID | Event / 1 Hz | Defaults to `UNKNOWN ROAD` / 0.0% grade if off-network |
| **Safety Advisory Banner** | "What is my immediate operational instruction?" | `safety.advisoryState` (`NORMAL`, `CAUTION`, `SLOW DOWN`, `STOP`) | Primary Colorway Banner | 10 Hz | Falls back to `CAUTION` on telemetry degradation; `EMERGENCY STOP` on obstacle or v_safe=0 |
| **Headway Radar & Target** | "How far is the lead vehicle and who am I following?" | `safety.headway_m`, `safety.lead_vehicle_id`, `safety.safe_headway_m` | Metres | 10 Hz | Renders `NO TARGET` when clear; turns red with buzzer alert if headway < safe_headway |
| **RF & Transport Status** | "Are my LoRa V2V and Wi-Fi V2I links operational?" | `vehicle.v2vState`, `vehicle.v2iState`, `vehicle.transport` | Badges (`CONNECTED`, `STALE`, `LOST`) | 2 Hz | Shows fallback indicator if V2I drops and V2V takes over |
| **Safe Beacon Indicator** | "Is my autonomous emergency beacon broadcasting?" | `safeBeaconActive` (Firmware safe beacon state) | Status: `STANDBY` / `ACTIVE` | 1 Hz | Labels: `SOFTWARE READY · FIELD GATE PENDING` |
| **Vehicle Diagnostics** | "Are chassis sensors healthy and what is my firmware boot counter?" | `boot_id`, `sequence`, `firmware_version`, encoder ticks, IMU health | Mono telemetry badges | 1 Hz | Alerts if sequence jumps or stalls; indicates sensor signal state |

---

## 3. Strict Absence of Frontend Physics Calculations

In compliance with Rule 6:
- **No Speed Integration:** The frontend does not integrate acceleration ($a_x$) or RPM pulses to invent vehicle speed. Speed is rendered exclusively from authoritative Twin state (`vehicle.speedMps`).
- **No Braking Distance Calculation:** $S_{\text{stop}}$ and $v_{\text{safe}}$ are calculated authoritatively by the backend physics solver (`backend/app/safety/physics_solver.py` via `v_stop`, `v_retarder`, `v_traction`, `v_curve`, `v_mine`). The Operator HMI purely visualizes the resulting $v_{\text{safe}}$ constraint.
- **No Path Extrapolation:** Vehicle position along the haul road is projected by the Digital Twin coordinate transformer, not by client-side dead reckoning.

---

## 4. Degraded Mode & Fault Matrix

| Condition | In-Cab Indicator | Audio Alert | Commanded Action |
| :--- | :--- | :--- | :--- |
| **Normal Operation** | Green advisory `NORMAL`, all telemetry fresh | None | Maintain speed $\le v_{\text{safe}}$ |
| **Entering Fog Patch** | Amber banner `CAUTION — REDUCED VISIBILITY`, $v_{\text{safe}}$ lowers | Single chime | Decelerate to commanded target |
| **Dense Fog ($<30\text{ m}$)** | Amber/Red banner `SLOW DOWN — CRITICAL VISIBILITY` | Double chime | Reduce speed $\le 1.5\text{ m/s}$ ($5.4\text{ km/h}$) |
| **Proximity Intrusion** | Red flashing banner `STOP — PROXIMITY HAZARD`, distance flashing | Continuous 2 kHz buzzer | Stop immediately; apply service brakes |
| **Telemetry Timeout ($>2.0\text{ s}$)** | Grey/Amber `STALE TELEMETRY`, timestamp delta highlighted | Periodic warning tone | Hold current speed or slow to crawl; do not accelerate |
| **Wi-Fi Link Loss** | `V2I DISCONNECTED · V2V ACTIVE (LoRa)` | Advisory chirp | Continue under autonomous V2V governor |
| **Safe Beacon Active** | Red flashing `SAFE BEACON BROADCASTING (1.0 Hz)` | Dual-tone alarm | Motor standby disabled (STBY=LOW); await recovery |

---

## 5. Verification & Test Evidence

- **Unit & Contract Tests:** Verified in `SYNQRA_SIH2026-27-HMI/frontend/src/vehicle/driverScreen.test.tsx` (13 tests) and `src/state/speedContract.test.tsx` (25 tests).
- **Prohibitions Verified:**
  - Zero regex matches for `speed_mps_reported` or `speed_mps_pwm_derived`.
  - Zero regex matches for `/rpm\s*\*|\*\s*Math\.PI|wheel_radius/i`.
  - Zero un-derived `PHYSICAL` string tags that would mislead simulation vs hardware state.
- **Compilation:** Clean build verified under `tsc --noEmit && vite build`.
