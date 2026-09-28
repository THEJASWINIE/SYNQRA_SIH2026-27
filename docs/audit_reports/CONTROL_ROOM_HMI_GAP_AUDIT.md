# CONTROL ROOM HMI GAP AUDIT
**FOG-ORCHESTRATOR 2.0 — Pre-Final Integration Closure**
**Document ID:** HMI-AUD-CR-01  
**Target Screen:** Control Room Master Overview (Screen S1)  
**Component:** `SYNQRA_SIH2026-27-HMI/frontend/src/screens/OperationsOverview.tsx`  
**Status:** COMPLETE / CLOSED

---

## 1. Executive Summary & Supervisory Role

The Control Room HMI (`OperationsOverview.tsx`) serves as the central operational overview for mine dispatchers and safety supervisors.

Under Section 11 of `AGENTS.md`:
> *"The existing Technician HMI must continue working. Do not redesign it unnecessarily... It should consume Twin state for: fleet, vehicle position, vehicle speed, safe speed, visibility, warnings, communication state, bottlenecks, road state, system health. It must not reconstruct conflicting authoritative state."*

The Control Room HMI maintains a fleet-wide supervisory posture. It aggregates real-time Digital Twin state across all active vehicles, tracks mine-wide bottleneck queues, visualizes environmental fog progression, and monitors critical RF/V2V communication links.

---

## 2. Panel Architecture & Data Lineage

| Panel / Component | Supervisory Purpose | Authoritative Data Source | SI Units & Format | Update Rate | Degraded / Timeout State |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Fleet Metric KPI Bar** | Instant fleet-level health: total vehicles, active haulers, bottleneck count, safety violations | `useHmiStore.getState().vehicles`, `activeAlerts`, `bottlenecks` | Numeric Counts & Status Badges | 2 Hz | Shows `DISCONNECTED` banner if backend WebSocket drops; retains last known counts with `STALE` badge |
| **Fleet Vehicle Cards Grid** | Per-vehicle summary cards: speed, safe limit, battery, current road segment, safety state | `TwinVehicle` array via `useHmiStore` | Speed ($m/s$), Distance ($m$), State Enum | 10 Hz | Individual cards turn Amber/Grey if `freshness > 2.0s`; red hazard stripe on safety violation |
| **Mine Topology / Haul Map** | Geospatial visualization of mine roads, pit benches, crushers, switchbacks, and vehicle vectors | `useHmiStore.getState().roads`, `spatialPositions` | Scene Coordinates ($m$) | 10 Hz | Vehicles remain visible at last verified position with dashed vector if telemetry goes stale |
| **Context Vehicle Inspector (Sidebar)** | Deep diagnostic inspection of operator-selected vehicle | `selectedVehicle` (`TwinVehicle`), `selectedSafety` | Structured Telemetry & Diagnostics Tables | 10 Hz | Clears or displays `DESELECTED / OFFLINE` if vehicle expires from Twin state store |
| **Command & Governor Panel** | Compares Requested Dispatch Speed vs Safe Limit ($v_{\text{safe}}$) vs Commanded Speed | `provenance.dispatch_target_mps`, `selectedSafety.vSafe`, `UNKNOWN / NOT TELEMETRIED` | Speed ($m/s$ & $km/h$) | 10 Hz | Highlights `ACTIVE INTERVENTION (CLAMPING)` if actual speed exceeds $v_{\text{safe}}$ |
| **RF Failover & Redundancy** | Live visibility into V2I (Wi-Fi), V2V (LoRa), and autonomous failover state | `v2vLink`, `v2iLink`, `safeBeaconActive` | Connection Enum (`CONNECTED`, `STALE`, `LOST`) | 2 Hz | Flags `NOT VERIFIED (PROTOCOL OPEN)` and `SOFTWARE READY · FIELD GATE PENDING` |
| **Chassis Health & Diagnostics** | Telemetry sequence counter, boot session ID, encoder signal, IMU 3-axis health | `boot_id`, `sequence`, `rpm`, `ax_mps2` | Integer ID, Counter, $RPM$, $m/s^2$ | 1 Hz | Flags `NO SIGNAL` on zero pulses, flags missing IMU or sequence skips |
| **Safety Event Stream & Alerts** | Chronological feed of safety violations, proximity warnings, fog entries | `alerts` array (`useHmiStore`) | ISO 8601 UTC timestamp, Severity, Message | Event-driven (push) | Persists unacknowledged alerts; logs ack events |
| **Bottleneck & Switchback Queue** | Manages switchback traffic flow and crusher queue density | `bottleneckQueue` model | Vehicle IDs, Wait Times ($s$) | 1 Hz | Re-ranks queue automatically based on priority and haul cycle time |

---

## 3. Strict Compliance with Architectural Rules

- **Rule 5 (One Authoritative Digital Twin):** The Control Room does not maintain a private vehicle state store. All vehicle states originate from `store.ts` which receives updates via the backend WebSocket streaming `/ws/state`.
- **Rule 6 (Frontend Must Not Invent State):** The screen does not compute safe speeds or simulate braking distances. Speed limits and headway warnings are streamed directly from the backend physics solver.
- **Rule 4 & Rule 3 (No Fabricated Telemetry):** All values display explicit provenance tags (`SIMULATION`, `HARDWARE`, `HYBRID`). When applied speed is not telemetried from a physical chassis actuator sensor, it is explicitly displayed as `UNKNOWN / NOT TELEMETRIED` rather than assumed or synthesized.
- **Derived Provenance Contract:** Ensures exact parity between `PHYSICAL` and `PHYSICAL (derived)` tags to avoid confusing raw sensor readings with calculated metrics.

---

## 4. Operational Transition & Intervention Flow

```
[Vehicle Approaches Fog Zone]
              ↓
[Fog Sensor / Sim Ingests Low Visibility (e.g. 25m)]
              ↓
[Digital Twin Updates Environment State]
              ↓
[Backend Physics Solver: v_safe clamped to 2.1 m/s]
              ↓
[WebSocket Broadcasts Update to Control Room HMI]
              ↓
[Fleet Grid: Vehicle Card turns AMBER, v_safe displays 2.1 m/s]
              ↓
[Inspector Sidebar: Governor Status = ACTIVE INTERVENTION]
              ↓
[Safety Event Log: Emits "SPEED_GOVERNED: TRUCK_01 reduced for FOG"]
```

---

## 5. Verification & Test Evidence

- **Unit & Contract Tests:** Passed 100% of tests in `src/screens/operationsOverview.test.tsx` (15 tests), `src/controlRoom/controlRoomWorkspace.test.tsx` (18 tests), and `src/screens/screenConsistency.test.tsx` (12 tests).
- **Zero Regex Violations:** No occurrences of raw internal keys (`speed_mps_reported`, `speed_mps_pwm_derived`) or forbidden calculation patterns.
- **Production Build:** Verified clean bundle generation via `npm run build`.
