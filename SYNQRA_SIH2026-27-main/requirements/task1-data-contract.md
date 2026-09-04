# Task 1 — Conceptual Data Contract

**Specification:** `docs/FOG_ORCHESTRATOR_Task1_HMI_Requirements.pdf` (canonical path; sole Task 1 specification). "PDF §n" below refers to this document.
**Baseline:** Planning Baseline v1.3 (frozen). Changes governed by `requirements/DECISIONS.md`.

**Source:** PDF §9 "Data Interfaces" (minimum fields), extended only where a mandatory
requirement needs a field the PDF did not enumerate. Every extension is marked
**[EXT]** and listed in §12 for Task 2 agreement.

**Status:** conceptual contract. No code. Types are expressed in TypeScript-like notation
for precision; the implementing repository will centralize them (architecture skill:
"centralize schemas and types") and mirror them as Pydantic models on the backend.

**Boundary rule (scope-control skill):** every field below is an **input to the HMI**.
Task 1 computes none of them. The only values Task 1 derives are presentation-layer
properties of the data path itself: `age_ms` (now minus timestamp), staleness, and the
alerts and DEGRADED mode that follow from staleness. Those are explicitly listed in §10.

---

## 1. Shared Primitives

```ts
type Iso8601 = string;          // UTC, millisecond precision
type VehicleId = string;
type SegmentId = string;
type NodeId = string;
type SlotId = string;
type CommandId = string;
type RouteId = string;
type ComponentId = string;

/** Wrapper for every externally supplied datum. Carries provenance so NFR-003 and
 *  NFR-012 can be satisfied uniformly instead of per-field. */
interface Sourced<T> {
  value: T | null;              // null = not supplied. Never coerce to 0.
  timestamp: Iso8601;           // when the source produced it
  source_id: ComponentId;
  age_ms: number;               // derived by HMI at render time
  quality: "OK" | "STALE" | "MISSING" | "INVALID";  // derived by HMI
}

/** Value with supplied uncertainty. */
interface Estimate {
  value: number | null;
  sigma: number | null;         // null = uncertainty not supplied
}
```

`Sourced<T>` is the single mechanism by which NFR-003 (freshness), NFR-012 (stale rather
than frozen) and the testing skill's stale/disconnected state checks are met. A component
that renders a raw number instead of a `Sourced` value is a defect.

---

## 2. VehicleState

PDF §9 minimum fields: `vehicle_id, timestamp, x/y or segment_id, speed_mps, accel_mps2,
grade_rad, friction_est, friction_sigma, mode, comm_confidence`.

```ts
interface VehicleState {
  vehicle_id: VehicleId;
  timestamp: Iso8601;

  // position: either coordinates, or a segment plus optional offset
  position: {
    x: number | null;
    y: number | null;
    segment_id: SegmentId | null;
    offset_m: number | null;    // [EXT] distance along segment, for map interpolation
  };

  speed_mps: number;
  accel_mps2: number;
  grade_rad: number;            // road grade at the vehicle (FR-003, S2-a)
  friction_est: Estimate;       // friction_est + friction_sigma from PDF
  mode: VehicleMode;
  comm_confidence: number;      // 0..1

  vehicle_kind: string | null;  // [EXT] truck / shovel / other, for map glyphs (FR-002)
  route_id: RouteId | null;     // [EXT] currently assigned route, for FR-010 cross-ref
}

type VehicleMode =
  | "NORMAL" | "CAUTION" | "DEGRADED" | "LOCAL_SAFE" | "STOP_UNSAFE"
  | "UNKNOWN";                  // [EXT] required so an unrecognised value is never dropped
```

Note: PDF §5 FR-016 defines the five mode names for the *system*; `VehicleMode` reuses
the same enum for a vehicle. Whether the vehicle-level and system-level enums are the same
set is **AMB-005**.

---

## 3. SafetyState

PDF §9: `vehicle_id, v_safe, h_safe, actual_speed, active_constraint, risk_level`.

```ts
interface SafetyState {
  vehicle_id: VehicleId;
  timestamp: Iso8601;           // [EXT] required for freshness (NFR-003)

  v_safe: number | null;        // m/s — SUPPLIED BY TASK 2, never computed here
  h_safe: number | null;        // m or s (units must be agreed — AMB-001)
  actual_speed: number;
  headway_current: number | null;  // [EXT] FR-005 requires "current headway"; PDF §9 omits it
  lead_vehicle_id: VehicleId | null; // [EXT] FR-005 "vehicle pairs" needs the pair partner

  active_constraint: ActiveConstraint;
  risk_level: RiskLevel;

  headway_violation: boolean | null;  // [EXT] supplied if Task 2 evaluates it; otherwise
                                      // the HMI shows a direct comparison of the two numbers
  envelope_violation: boolean | null; // [EXT] actual_speed above v_safe, per FR-004 / KPI
}

type ActiveConstraint =
  | "VISIBILITY" | "FRICTION" | "GRADE" | "BRAKING_RETARDER"
  | "CURVE" | "SITE_LIMIT" | "NONE" | "UNKNOWN";

type RiskLevel = "LOW" | "MODERATE" | "HIGH" | "CRITICAL" | "UNKNOWN";
```

`ActiveConstraint` values come verbatim from PDF §5 FR-004. `RiskLevel` band names are
**not specified in the PDF** — see AMB-007.

---

## 4. RoadState

PDF §9: `segment_id, visibility_m, visibility_sigma, friction, grade, capacity_vph, queue,
utilization`.

```ts
interface RoadState {
  segment_id: SegmentId;
  timestamp: Iso8601;           // [EXT] freshness

  visibility: Estimate;         // visibility_m + visibility_sigma
  friction: Estimate;           // friction + [EXT] friction_sigma, for FR-012 consistency
  grade: number;                // rad
  capacity_vph: number | null;
  queue: number | null;
  utilization: number | null;   // 0..1

  surface_state: SurfaceState | null;  // [EXT] FR-012 requires wetness/surface state
  roughness: number | null;            // [EXT] FR-012 optional roughness
}

type SurfaceState = "DRY" | "WET" | "MUDDY" | "ICY" | "UNKNOWN";  // [EXT] set to be agreed
```

### VisibilityForecast [EXT — whole message]

FR-011 requires forecast visibility with an uncertainty band "when available". PDF §9
defines no forecast message.

```ts
interface VisibilityForecast {
  segment_id: SegmentId;
  issued_at: Iso8601;
  horizon: Array<{
    at: Iso8601;
    visibility: Estimate;       // value + sigma gives the confidence band
  }>;
}
```

Computed entirely by Task 2. Task 1 draws the band and labels it as forecast.

---

## 5. BottleneckState

PDF §9: `node_id, lambda_vph, mu_vph, queue, queue_max, criticality, bottleneck_score`.

```ts
interface BottleneckState {
  node_id: NodeId;
  timestamp: Iso8601;           // [EXT] freshness

  lambda_vph: number | null;    // arrival rate — SUPPLIED
  mu_vph: number | null;        // service rate — SUPPLIED
  queue: number | null;
  queue_max: number | null;
  utilization: number | null;   // [EXT] FR-006/FR-007 name utilization explicitly
  criticality: Criticality;
  bottleneck_score: number | null;  // SUPPLIED — the HMI sorts by it, never derives it

  queue_history: Array<{ at: Iso8601; queue: number }> | null;    // [EXT] measured
  queue_forecast: Array<{ at: Iso8601; queue: number; sigma: number | null }> | null;
                                 // [EXT] S3 "predicted queue trend" — SUPPLIED BY TASK 2
}

type Criticality = "LOW" | "MEDIUM" | "HIGH" | "CRITICAL" | "UNKNOWN";
```

`queue_forecast` is the single most scope-sensitive field in this contract: it is exactly
the queue-prediction output the scope-control skill forbids Task 1 from producing. It is
consumed and drawn, distinguished from `queue_history`, and never extrapolated.

---

## 6. DispatchCommand

PDF §9: `vehicle_id, route_id, departure_time, target_speed, slot_id, reason_code,
timestamp, command_id`.

```ts
interface DispatchCommand {
  command_id: CommandId;
  vehicle_id: VehicleId;
  route_id: RouteId | null;
  departure_time: Iso8601 | null;
  target_speed: number | null;  // m/s
  slot_id: SlotId | null;
  reason_code: string;          // mandatory per NFR-006; empty is a data defect
  timestamp: Iso8601;

  state: "RECOMMENDED" | "ISSUED" | "ACKNOWLEDGED" | "SUPERSEDED" | "REJECTED"; // [EXT]
  limiting_variables: string[] | null;  // [EXT] NFR-006 "key limiting variables"
  route_node_ids: NodeId[] | null;      // [EXT] to draw the route on the map (FR-010)
}
```

`state` is an extension because FR-010 requires "recommended/issued" to be distinguishable
and NFR-007 requires issue and receipt to be logged; PDF §9 provides no state field.
Whether Task 1 may *issue* commands or only display them is **AMB-008**.

---

## 7. SlotState

PDF §9: `slot_id, resource_id, vehicle_id, start_time, end_time, status`.

```ts
interface SlotState {
  slot_id: SlotId;
  resource_id: NodeId;          // switchback / intersection / crusher / shovel
  vehicle_id: VehicleId | null; // current holder; null = unheld
  start_time: Iso8601;
  end_time: Iso8601;
  status: SlotStatus;

  eta: Iso8601 | null;          // [EXT] FR-009 requires ETA; PDF §9 omits it
  conflict_with: SlotId[] | null;  // [EXT] FR-009 requires conflict status to be visible;
                                   // the conflicting party is needed to render it usefully
}

type SlotStatus =
  | "RESERVED" | "ACTIVE" | "RELEASED" | "EXPIRED" | "CONFLICT" | "UNKNOWN";
```

Conflicts are **determined by Task 2**. Task 1 renders `status === "CONFLICT"` and the
`conflict_with` links; it runs no slot solver.

### ArrivalPlan [EXT — whole message]

FR-008 requires planned vs actual arrivals and active metering/hold decisions. PDF §9
defines no such message (AMB-002).

```ts
interface ArrivalPlan {
  node_id: NodeId;
  issued_at: Iso8601;
  planned: Array<{ at: Iso8601; count: number }>;
  actual:  Array<{ at: Iso8601; count: number }>;
  active_decisions: Array<{
    vehicle_id: VehicleId;
    decision: "HOLD" | "METER" | "RELEASE";
    until: Iso8601 | null;
    reason_code: string;
  }>;
}
```

---

## 8. Alert / Event

PDF §9 defines no Alert message; FR-014, FR-015, NFR-007, S5-a require one.
**[EXT — whole message]**

```ts
interface Alert {
  alert_id: string;
  timestamp: Iso8601;
  severity: "INFO" | "WARNING" | "CRITICAL";
  category: AlertCategory;
  origin: "TASK2" | "HMI";      // HMI may originate only STALE_DATA and COMM_LOSS
  subject: { kind: "VEHICLE" | "NODE" | "SEGMENT" | "SLOT" | "SYSTEM"; id: string };
  message: string;
  reason_code: string | null;
  acknowledgeable: boolean;     // false for safety-critical (FR-015)
  acknowledged: {
    by: string;                 // operator identity
    at: Iso8601;
  } | null;
  active: boolean;
}

type AlertCategory =
  | "UNSAFE_SPEED" | "UNSAFE_HEADWAY" | "BOTTLENECK_RISK"
  | "COMM_LOSS" | "STALE_DATA" | "SLOT_CONFLICT";   // the six named in FR-014

/** Append-only audit record backing S5 and NFR-007. */
interface EventRecord {
  event_id: string;
  timestamp: Iso8601;
  category: EventCategory;
  subject_id: string | null;
  payload: unknown;             // the alert, command or mode transition, as received
  actor: string | null;         // operator identity for operator-initiated events
}

type EventCategory =
  | "FOG_CHANGE" | "ALERT_RAISED" | "ALERT_ACKNOWLEDGED"
  | "COMMAND_RECEIVED" | "COMMAND_ISSUED"
  | "QUEUE_CHANGE" | "VIOLATION" | "RECOVERY" | "MODE_TRANSITION";  // per S5-a, NFR-007
```

---

## 9. Health / System State

PDF §9 Health: `component_id, timestamp, state, latency_ms, age_ms, error_code`.

```ts
interface Health {
  component_id: ComponentId;
  timestamp: Iso8601;
  state: "UP" | "DEGRADED" | "DOWN" | "UNKNOWN";
  latency_ms: number | null;
  age_ms: number | null;
  error_code: string | null;

  link_kind: "V2V" | "V2I" | "LORA" | "BACKEND" | "SENSOR" | null;  // [EXT] FR-013
  messages_received: number | null;   // [EXT] S6-a message counts
  messages_dropped: number | null;    // [EXT] S6-a
}

/** Global roll-up rendered in the status bar. */
interface SystemHealth {                                 // [EXT — whole message]
  timestamp: Iso8601;
  system_mode: SystemMode;      // supplied; HMI may force at least DEGRADED (FR-016)
  connectivity: "CONNECTED" | "DEGRADED" | "DISCONNECTED";
  fleet_count: number;
  components: Health[];
}

type SystemMode =
  | "NORMAL" | "CAUTION" | "DEGRADED" | "LOCAL_SAFE" | "STOP_UNSAFE";  // PDF §5 FR-016
```

### KpiSnapshot [EXT — whole message]

FR-018 names seven KPIs; PDF §9 defines no KPI message (AMB-003).

```ts
interface KpiSnapshot {
  timestamp: Iso8601;
  window_s: number | null;                    // averaging window, if any
  throughput_tph: number | null;
  cycle_time_s: number | null;
  queue_length_avg: number | null;
  utilization: number | null;                 // 0..1
  stops_count: number | null;
  safety_envelope_violations: number | null;
  recovery_time_s: number | null;
}
```

All seven are **supplied**. Deriving them from a telemetry history inside Task 1 would be
computing operational metrics over a simulation Task 1 does not own.

---

## 10. CVResult (optional)

PDF §9: `timestamp, source_id, visibility_proxy, confidence, detections[], road_state`.

```ts
interface CVResult {
  timestamp: Iso8601;
  source_id: ComponentId;
  visibility_proxy: number | null;
  confidence: number | null;    // 0..1
  detections: Array<{
    class_name: string;
    confidence: number;
    bbox: [number, number, number, number] | null;
  }>;
  road_state: SurfaceState | null;
  status: "OK" | "UNAVAILABLE" | "STALE";     // [EXT] CV-005 graceful failure
  frame_ref: string | null;                   // [EXT] FR-020 requires the frame be shown
}
```

CV output is advisory (OPS-004) and must be labelled as non-authoritative next to
physics-derived values.

---

## 11. MineTopology [EXT — whole message]

FR-002 requires a graph-based map. PDF §9 defines no topology message; without one the map
cannot be data-driven, which the architecture skill requires.

```ts
interface MineTopology {
  version: string;
  nodes: Array<{
    node_id: NodeId;
    kind: "SHOVEL" | "CRUSHER" | "INTERSECTION" | "SWITCHBACK" | "WAYPOINT";
    label: string;
    x: number;
    y: number;
  }>;
  segments: Array<{
    segment_id: SegmentId;
    from_node: NodeId;
    to_node: NodeId;
    length_m: number;
    grade_rad: number;
    bidirectional: boolean;
  }>;
}
```

Topology is quasi-static: fetched once and refreshed on `version` change.

---

## 12. Normalized Application State

The single shape every screen reads (architecture skill: providers to normalization to
typed state to React). No component reads a provider or raw JSON.

```ts
interface AppState {
  connection: {
    status: "IDLE" | "CONNECTING" | "CONNECTED" | "RECONNECTING" | "DISCONNECTED" | "ERROR";
    provider: "MOCK" | "LIVE" | "REPLAY";
    scenario_name: string | null;   // FR-019
    last_message_at: Iso8601 | null;
    error: string | null;
  };
  clock: { now: Iso8601; replay_position: Iso8601 | null };

  topology: MineTopology | null;
  vehicles: Record<VehicleId, VehicleState>;
  safety:   Record<VehicleId, SafetyState>;
  road:     Record<SegmentId, RoadState>;
  forecasts: Record<SegmentId, VisibilityForecast>;
  bottlenecks: Record<NodeId, BottleneckState>;
  arrivals: Record<NodeId, ArrivalPlan>;
  slots:    Record<SlotId, SlotState>;
  dispatch: Record<CommandId, DispatchCommand>;
  alerts:   Alert[];
  events:   EventRecord[];
  health:   SystemHealth | null;
  kpis:     KpiSnapshot | null;
  cv:       CVResult | null;
}
```

### Values the HMI itself derives — the complete list

The scope-control skill requires this list to be closed and auditable. Task 1 derives
**only** these, and every one is a property of the data path or of presentation, not of
the mine:

1. `age_ms` for any datum — `now` minus `timestamp`.
2. `quality` — `OK` / `STALE` / `MISSING` from `age_ms` against the configured timeout.
3. `connection.status`.
4. Alerts of category `STALE_DATA` and `COMM_LOSS`.
5. Forcing displayed `system_mode` to at least `DEGRADED` when the feed is lost (NFR-012).
6. Sort order of the bottleneck list from the supplied `bottleneck_score`.
7. Alert ordering from supplied severity and timestamp.
8. Boolean comparisons of two supplied numbers for display only (for example
   `actual_speed > v_safe`), used solely when Task 2 has not supplied the flag.
9. The **display-only map coordinate** for a vehicle marker, from supplied `segment_id`,
   supplied `offset_m` and supplied topology node geometry — mandated by HMI-FR-002 and
   supplied for by E-01. A deterministic geometric transform for rendering the *current*
   marker only. It must not be extended to trajectory prediction, future position
   estimation, movement over time, animation between updates, dead reckoning, or route
   planning. Where the supplied geometry is insufficient, the vehicle renders as position
   unavailable; no coordinate is guessed. Recorded as M4D-F; added by revision v1.4 after
   D5 found this list in conflict with HMI-FR-002.

Anything not on this list must arrive from a provider. Adding to this list requires
re-checking the scope-control decision rule.

---

## 13. Provider Interface

```ts
interface DataProvider {
  connect(): Promise<void>;
  disconnect(): Promise<void>;
  /** Emits normalized partial updates; never raw transport frames. */
  subscribe(onUpdate: (patch: Partial<AppState>) => void): () => void;
  /** Advisory only (NFR-005). Rejected while provider is REPLAY (FR-017). */
  sendAcknowledgement(alertId: string, actor: string): Promise<void>;
}
```

Three implementations: `MockDataProvider` (M3), `LiveDataProvider` (M12),
`ReplayProvider` (M9). Screens are identical across all three.

---

## 14. Extensions Requiring Task 2 Agreement

Every **[EXT]** above, consolidated. These are the integration-contract negotiation items.

| # | Extension | Needed by | Note |
|---|---|---|---|
| E-01 | `VehicleState.position.offset_m` | FR-002 | map interpolation along a segment |
| E-02 | `VehicleState.vehicle_kind`, `route_id` | FR-002, FR-010 | glyphs and route cross-reference |
| E-03 | `VehicleMode.UNKNOWN`, `ActiveConstraint.UNKNOWN`, `RiskLevel.UNKNOWN` | FR-003, FR-004 | unrecognised values must not be dropped |
| E-04 | `SafetyState.headway_current`, `.lead_vehicle_id` | FR-005 | PDF §9 omits current headway entirely |
| E-05 | `SafetyState.headway_violation`, `.envelope_violation` | FR-005, FR-018 | preferred supplied, not derived |
| E-06 | `timestamp` on SafetyState, RoadState, BottleneckState | NFR-003 | freshness per message |
| E-07 | `RoadState.surface_state`, `.roughness`, `.friction_sigma` | FR-012 | wetness/surface explicitly required |
| E-08 | `VisibilityForecast` message | FR-011 | forecast plus uncertainty band |
| E-09 | `BottleneckState.utilization`, `queue_history`, `queue_forecast` | FR-006, FR-007, S3 | predicted queue trend is Task 2 output |
| E-10 | `ArrivalPlan` message | FR-008 | planned vs actual plus metering decisions |
| E-11 | `DispatchCommand.state`, `.limiting_variables`, `.route_node_ids` | FR-010, NFR-006 | recommended vs issued distinction |
| E-12 | `SlotState.eta`, `.conflict_with` | FR-009 | ETA and conflict counterparty |
| E-13 | `Alert` message and category enum | FR-014, FR-015 | not in PDF §9 at all |
| E-14 | `EventRecord` and category enum | FR-017, NFR-007, S5-a | audit and replay backbone |
| E-15 | `SystemHealth` roll-up, `Health.link_kind`, message counts | FR-001, FR-013, S6-a | link kinds and counters |
| E-16 | `KpiSnapshot` message | FR-018 | seven named KPIs |
| E-17 | `MineTopology` message | FR-002 | without it the map cannot be data-driven |
| E-18 | `CVResult.status`, `.frame_ref` | CV-005, FR-020 | optional |
| E-19 | Units for `h_safe` (metres or seconds) | FR-005 | see AMB-001 |
| E-20 | Enum value sets for `RiskLevel`, `Criticality`, `SurfaceState`, reason codes | FR-004, FR-006, FR-012, NFR-006 | see AMB-007, AMB-009 |

Until agreed, all twenty are represented in mock data with the shapes above, so that
integration is a provider swap and not a rewrite.
