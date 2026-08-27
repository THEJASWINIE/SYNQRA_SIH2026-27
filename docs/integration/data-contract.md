# Task 1 / Task 2 Integration Data Contract — Extension Inventory (E-01..E-20)

**Specification:** `docs/FOG_ORCHESTRATOR_Task1_HMI_Requirements.pdf` (sole Task 1 functional specification)  
**Baseline:** Planning Baseline v1.9 (frozen). Governed by `requirements/DECISIONS.md`.  
**Source Contract:** `requirements/task1-data-contract.md` §14  
**Status:** **INTEGRATION NEGOTIATION BASELINE**

---

## 1. Executive Summary

PDF §9 defines the minimum fields for core telemetry messages. To satisfy mandatory functional requirements without locally generating operational physics, queue forecasts, or arrival plans (which belong strictly to Task 2 per `CLAUDE.md`), Task 1 defines twenty contract extensions marked **[EXT]** (E-01 through E-20).

Every extension has:
1. A runtime Zod schema (`frontend/src/contracts/raw.ts`)
2. A TypeScript domain type (`frontend/src/contracts/domain.ts`)
3. A mirrored backend Pydantic model (`backend/app/schemas/contracts/messages.py`)
4. A pure normalization function (`frontend/src/data/normalize.ts`)

---

## 2. E-01..E-20 Extension Readiness and Specification Dependency Matrix

| # | Extension | Wire Type & Field | Backend Pydantic Mirror | Source Expectation | Frontend Handling | Unresolved Dependency | Conformance Status |
|---|---|---|---|---|---|---|---|
| **E-01** | Segment offset for vehicle interpolation | `VehicleState.position.offset_m: number \| null` | `VehiclePosition.offset_m: float \| None` | **Task 2** (supplied) | Mapped to closed derivation item 9 (display marker interpolation only; no dead reckoning) | None | **READY** — Nullable in schema |
| **E-02** | Vehicle glyph classification and route ID | `VehicleState.vehicle_kind: string \| null`, `route_id: string \| null` | `VehicleStateMsg.vehicle_kind`, `.route_id` | **Task 2** (supplied) | Normalized to camelCase `vehicleKind` and `routeId`; rendered on S1/S2 | None | **READY** — Nullable in schema |
| **E-03** | `UNKNOWN` enum fallback member | `VehicleMode.UNKNOWN`, `ActiveConstraint.UNKNOWN`, `RiskLevel.UNKNOWN`, etc. | `VehicleModeEnum.UNKNOWN`, `ActiveConstraintEnum.UNKNOWN`, etc. | **Task 2 / HMI** | Normalizer maps any unrecognised wire string to `UNKNOWN`; never drops message | AMB-007 (enum sets) | **READY** — Tested and enforced |
| **E-04** | Current headway and lead vehicle reference | `SafetyState.headway_current: number \| null`, `lead_vehicle_id: string \| null` | `SafetyStateMsg.headway_current`, `.lead_vehicle_id` | **Task 2** (supplied) | Normalized to `headwayCurrent` and `leadVehicleId` on S2; compared against `h_safe` | **AMB-001** (`h_safe` units: metres vs seconds) | **PARTIAL** — Units pending confirmation |
| **E-05** | Headway & safe envelope violation flags | `SafetyState.headway_violation: boolean \| null`, `envelope_violation: boolean \| null` | `SafetyStateMsg.headway_violation`, `.envelope_violation` | **Task 2** (preferred supplied) | If supplied, renders directly; if null, falls back to direct display comparison of supplied numbers | None | **READY** — Fallback comparison active |
| **E-06** | Timestamps on Safety, Road, Bottleneck | `SafetyState.timestamp`, `RoadState.timestamp`, `BottleneckState.timestamp` | `.timestamp: Iso8601` on all message models | **Task 2** (supplied) | Used by `Sourced<T>` to derive data age (`ageMs = now - timestamp`) for NFR-003/012 | **AMB-014** (timeout value missing from PDF) | **READY** — Mechanism active, timeout injected |
| **E-07** | Road surface state, roughness, friction sigma | `RoadState.surface_state: SurfaceState \| null`, `roughness: number \| null`, `friction.sigma` | `RoadStateMsg.surface_state`, `.roughness`, `Estimate.sigma` | **Task 2** (supplied) | Normalized to camelCase on S1/S2 road condition panels | AMB-007 (surface state enum) | **READY** — Nullable in schema |
| **E-08** | `VisibilityForecast` message group | `VisibilityForecast: { segment_id, issued_at, horizon: [{ at, visibility }] }` | `VisibilityForecastMsg` | **Task 2** (supplied) | Renders forecast visibility with uncertainty band on S1/S2; Task 1 runs no fog model | None | **READY** — Type & normalizer implemented |
| **E-09** | Bottleneck utilization, queue history & forecast | `BottleneckState.utilization`, `queue_history`, `queue_forecast` | `BottleneckStateMsg.utilization`, `.queue_history`, `.queue_forecast` | **Task 2** (supplied) | Renders historical & predicted queue trend on S3; Task 1 runs no queue prediction | None | **READY** — S3 renders supplied trend |
| **E-10** | `ArrivalPlan` message group | `ArrivalPlan: { node_id, issued_at, planned[], actual[], active_decisions[] }` | `ArrivalPlanMsg` | **Task 2** (supplied) | Renders planned vs actual arrival chart and HOLD/METER decisions on S3/S4 | AMB-002 (arrival plan source) | **READY** — S3/S4 renders supplied plan |
| **E-11** | Dispatch command state, limiting variables, route | `DispatchCommand.state: DispatchState`, `limiting_variables: string[] \| null`, `route_node_ids` | `DispatchCommandMsg.state`, `.limiting_variables`, `.route_node_ids` | **Task 2** (supplied) | Distinguishes RECOMMENDED vs ISSUED on S4; draws route line on S1 mine map | **AMB-008** (HMI command issuance scope) | **READY** (display-only per PAD-B) |
| **E-12** | Slot ETA and conflict counterparties | `SlotState.eta: Iso8601 \| null`, `conflict_with: string[] \| null` | `SlotStateMsg.eta`, `.conflict_with` | **Task 2** (supplied) | Renders conflict highlights and counterparty links on S4 timeline; Task 1 runs no solver | None | **READY** — S4 highlights conflicts |
| **E-13** | `Alert` message schema and category enum | `Alert: { alert_id, severity, category, origin, subject, message, reason_code, acknowledgeable, active }` | `AlertMsg` | **Task 2** (for 4 mine categories) + **HMI** (STALE_DATA, COMM_LOSS) | Renders alerts in TopAlerts and AlertList; filters by origin and severity | None | **READY** — Dual-origin routing active |
| **E-14** | `EventRecord` audit log message | `EventRecord: { event_id, timestamp, category, subject_id, payload, actor }` | `EventRecordMsg` | **Task 2** (mine events) + **HMI recorder** (session observations) | Populates S5 Event & Replay log; backs NFR-007 | **AMB-010** (persistence ownership/retention) | **READY** (in-memory per M9D-A) |
| **E-15** | SystemHealth roll-up, link kinds, message counters | `SystemHealth: { system_mode, connectivity, fleet_count, components: Health[] }` | `SystemHealthMsg`, `HealthMsg` | **Task 2** (supplied) | Renders status bar roll-up and S6 link table (`V2V`, `V2I`, `LORA`, etc.); message counts | None | **READY** — S6 displays counters as supplied |
| **E-16** | `KpiSnapshot` operational metrics message | `KpiSnapshot: { throughput_tph, cycle_time_s, queue_length_avg, utilization, stops_count, ... }` | `KpiSnapshotMsg` | **Task 2** (supplied) | Renders 7 operational KPIs on S1/S6; Task 1 runs no simulation/accumulation (PAD-E) | AMB-003 (KPI provenance) | **READY** — S1 renders supplied snapshot |
| **E-17** | `MineTopology` graph definition message | `MineTopology: { version, nodes[], segments[] }` | `MineTopologyMsg` | **Task 2 / Static Configuration** | Drives SVG MineMap on S1 with nodes, switchbacks, grades and segments | AMB-011 (topology format/source) | **READY** — Map is 100% data-driven |
| **E-18** | `CVResult` perception advisory message | `CVResult: { visibility_proxy, confidence, detections[], road_state, status, frame_ref }` | `CVResultMsg` | **Laptop CV Pipeline** (optional M13) | Renders non-authoritative CV perception overlay on S1 (OPS-004) | M13 optional scope | **READY** (M13 dependency) |
| **E-19** | Units for required headway `h_safe` | `h_safe: number \| null` (metres vs seconds) | `SafetyStateMsg.h_safe: float \| None` | **Specification Owner / Task 2** | S2 displays value with explicit unit note; awaiting confirmation of metres vs time gap (s) | **AMB-001** (unresolved) | **BLOCKED ON SPEC DECISION** |
| **E-20** | Enum value sets for Risk, Criticality, Surface | `RiskLevel`, `Criticality`, `SurfaceState`, reason codes | Mirrored enums in `backend/app/schemas/contracts/messages.py` | **Task 2 Agreement** | Four-level bands mapped to visual tokens; unknown values normalize to `UNKNOWN` | AMB-007 (unresolved) | **READY** (provisional four-level bands) |

---

## 3. Wire Format & Protocol Guidelines

1. **Naming Convention:** Wire payloads use `snake_case` (e.g. `vehicle_id`, `speed_mps`, `reason_code`). Normalization transforms them to `camelCase` domain properties.
2. **Timestamps:** ISO 8601 UTC with millisecond precision (e.g. `2026-08-27T12:00:00.000Z`). Timestamps lacking timezone information or invalid dates are rejected as `ValidationFailure`.
3. **Absence vs Zero:** Omitted or `null` fields must never be coerced to `0` or empty strings. `null` represents `MISSING` data.
4. **Resilience:** Unrecognised fields must be tolerated (stripped or ignored) to ensure backward/forward schema compatibility.
