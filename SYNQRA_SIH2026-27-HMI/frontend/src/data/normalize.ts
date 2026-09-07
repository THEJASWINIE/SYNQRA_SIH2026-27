/**
 * Normalization — M2.
 *
 * Converts a validated raw payload (snake_case, MAD-E) into the normalized domain shape
 * (camelCase, MAD-F).
 *
 * This is a PURE TRANSFORM. It performs no arithmetic on operational values, no
 * aggregation, no inference, and it fills no gaps. An absent value stays absent and is
 * represented by quality, not by a substituted number (realtime-data skill §8, PAD-F).
 *
 * Unknown enum values normalize to `UNKNOWN` — never dropped, and never a reason to
 * reject an otherwise valid message (contract E-03).
 */

import type {
  Alert,
  ArrivalPlan,
  BottleneckState,
  CVResult,
  DispatchCommand,
  EventRecord,
  Health,
  KpiSnapshot,
  MineTopology,
  RoadState,
  SafetyState,
  SlotState,
  SystemHealth,
  VehicleState,
  VisibilityForecast,
} from "../contracts/domain";
import {
  ACTIVE_CONSTRAINTS,
  type ActiveConstraint,
  CRITICALITIES,
  type Criticality,
  HEALTH_STATES,
  type HealthState,
  RISK_LEVELS,
  type RiskLevel,
  SLOT_STATUSES,
  type SlotStatus,
  SURFACE_STATES,
  type SurfaceState,
  VEHICLE_MODES,
  type VehicleMode,
} from "../contracts/enums";
import type { Estimate } from "../contracts/primitives";
import type { RawTwinField, RawTwinVehicle } from "../contracts/raw";
import type { TwinFieldProvenance } from "../contracts/domain";
import type {
  RawAlert,
  RawArrivalPlan,
  RawBottleneckState,
  RawCvResult,
  RawDispatchCommand,
  RawEventRecord,
  RawHealth,
  RawKpiSnapshot,
  RawMineTopology,
  RawRoadState,
  RawSafetyState,
  RawSlotState,
  RawSystemHealth,
  RawVehicleState,
  RawVisibilityForecast,
} from "../contracts/raw";

// ---------------------------------------------------------------------------
// Enum tolerance
// ---------------------------------------------------------------------------

/**
 * Map a producer-supplied enum value onto a known member, falling back to `UNKNOWN`.
 *
 * The fallback is the whole point: AMB-007 leaves the real value sets unagreed, so an
 * unrecognised member must survive as `UNKNOWN` rather than being dropped (which loses
 * information) or rejected (which discards an otherwise usable message).
 */
function toEnum<T extends string>(value: unknown, allowed: readonly T[], fallback: T): T {
  return typeof value === "string" && (allowed as readonly string[]).includes(value)
    ? (value as T)
    : fallback;
}

const toVehicleMode = (v: unknown): VehicleMode => toEnum(v, VEHICLE_MODES, "UNKNOWN");
const toActiveConstraint = (v: unknown): ActiveConstraint =>
  toEnum(v, ACTIVE_CONSTRAINTS, "UNKNOWN");
const toRiskLevel = (v: unknown): RiskLevel => toEnum(v, RISK_LEVELS, "UNKNOWN");
const toCriticality = (v: unknown): Criticality => toEnum(v, CRITICALITIES, "UNKNOWN");
const toSlotStatus = (v: unknown): SlotStatus => toEnum(v, SLOT_STATUSES, "UNKNOWN");
const toHealthState = (v: unknown): HealthState => toEnum(v, HEALTH_STATES, "UNKNOWN");

/** Nullable variant: an absent surface state stays null; an unrecognised one becomes UNKNOWN. */
const toSurfaceStateOrNull = (v: unknown): SurfaceState | null =>
  v === null || v === undefined ? null : toEnum(v, SURFACE_STATES, "UNKNOWN");

const toEstimate = (e: { value: number | null; sigma: number | null }): Estimate => ({
  value: e.value,
  sigma: e.sigma,
});

// ---------------------------------------------------------------------------
// Message normalizers — contract §2–§11
// ---------------------------------------------------------------------------


/**
 * P6.1 — normalize one canonical Twin vehicle projection.
 *
 * ONE centralized mapping (no per-screen ad-hoc mapping). Values the Twin reports as
 * unavailable stay `null`; they are never defaulted to 0, false or "". Per-field
 * provenance is carried through verbatim so presentation can show source/freshness
 * without ever recomputing a physical quantity.
 */
export function normalizeTwinVehicle(raw: RawTwinVehicle): VehicleState {
  const dynamic = raw.dynamic ?? {};

  const field = (name: string): RawTwinField | undefined => dynamic[name];

  const numberOf = (name: string): number | null => {
    const f = field(name);
    if (!f || !f.available || typeof f.value !== "number" || !Number.isFinite(f.value)) {
      return null;
    }
    return f.value;
  };

  const stringOf = (name: string): string | null => {
    const f = field(name);
    if (!f || !f.available || typeof f.value !== "string") return null;
    return f.value;
  };

  const provenance: Record<string, TwinFieldProvenance> = {};
  for (const [name, f] of Object.entries(dynamic) as [string, RawTwinField][]) {
    provenance[name] = {
      value: f.value,
      timestamp: f.timestamp,
      source: f.source,
      origin: f.origin,
      quality: f.quality,
      ageS: f.age_s,
      available: f.available,
      clockDomain: f.clock_domain,
      freshness: f.freshness,
    };
  }

  // Prefer the timestamp of a genuinely observed field; never invent one.
  const stamped = (Object.values(dynamic) as RawTwinField[]).find(
    (f) => f.available && f.timestamp !== null,
  );
  const timestamp = stamped?.timestamp != null
    ? new Date(stamped.timestamp * 1000).toISOString()
    : new Date(0).toISOString();

  const roadId = stringOf("road_id");

  return {
    vehicleId: raw.vehicle_id,
    timestamp,
    position: {
      // No hardware on this prototype measures map coordinates. They stay null unless a
      // simulation supplies an along-road offset.
      x: null,
      y: null,
      segmentId: roadId,
      offsetM: numberOf("position_s"),
    },
    speedMps: numberOf("speed_mps"),
    accelMps2: numberOf("acceleration_mps2"),
    gradeRad: null,
    frictionEst: null,
    mode: toVehicleMode(stringOf("state") ?? "UNKNOWN"),
    commConfidence: null,
    vehicleKind: "TRUCK",
    routeId: roadId,
    provenance,
    hasHardwareData: raw.has_hardware_data ?? false,
  };
}

export function normalizeVehicleState(raw: RawVehicleState): VehicleState {
  return {
    vehicleId: raw.vehicle_id,
    timestamp: raw.timestamp,
    position: {
      x: raw.position.x,
      y: raw.position.y,
      segmentId: raw.position.segment_id,
      offsetM: raw.position.offset_m,
    },
    speedMps: raw.speed_mps,
    accelMps2: raw.accel_mps2,
    gradeRad: raw.grade_rad,
    frictionEst: raw.friction_est === null ? null : toEstimate(raw.friction_est),
    mode: toVehicleMode(raw.mode),
    commConfidence: raw.comm_confidence,
    vehicleKind: raw.vehicle_kind,
    routeId: raw.route_id,
  };
}

export function normalizeSafetyState(raw: RawSafetyState): SafetyState {
  return {
    vehicleId: raw.vehicle_id,
    timestamp: raw.timestamp,
    // v_safe and h_safe are copied verbatim. Task 1 never computes either (PAD-E).
    vSafe: raw.v_safe,
    hSafe: raw.h_safe,
    actualSpeed: raw.actual_speed,
    headwayCurrent: raw.headway_current,
    leadVehicleId: raw.lead_vehicle_id,
    activeConstraint: toActiveConstraint(raw.active_constraint),
    riskLevel: toRiskLevel(raw.risk_level),
    // Violation flags are copied as supplied. Absent stays null — no local comparison
    // is substituted here; that is a display-time concern (contract §12 item 8).
    headwayViolation: raw.headway_violation,
    envelopeViolation: raw.envelope_violation,
  };
}

export function normalizeRoadState(raw: RawRoadState): RoadState {
  return {
    segmentId: raw.segment_id,
    timestamp: raw.timestamp,
    visibility: toEstimate(raw.visibility),
    friction: toEstimate(raw.friction),
    grade: raw.grade,
    capacityVph: raw.capacity_vph,
    queue: raw.queue,
    utilization: raw.utilization,
    surfaceState: toSurfaceStateOrNull(raw.surface_state),
    roughness: raw.roughness,
  };
}

export function normalizeVisibilityForecast(raw: RawVisibilityForecast): VisibilityForecast {
  // The horizon is copied point for point. Nothing is interpolated, smoothed or
  // extended — fog modelling belongs to Task 2 (PAD-E).
  return {
    segmentId: raw.segment_id,
    issuedAt: raw.issued_at,
    horizon: raw.horizon.map((point) => ({
      at: point.at,
      visibility: toEstimate(point.visibility),
    })),
  };
}

export function normalizeBottleneckState(raw: RawBottleneckState): BottleneckState {
  return {
    nodeId: raw.node_id,
    timestamp: raw.timestamp,
    lambdaVph: raw.lambda_vph,
    muVph: raw.mu_vph,
    queue: raw.queue,
    queueMax: raw.queue_max,
    utilization: raw.utilization,
    criticality: toCriticality(raw.criticality),
    // Copied as supplied. The HMI sorts by this score; it never derives it.
    bottleneckScore: raw.bottleneck_score,
    queueHistory: raw.queue_history,
    // Copied as supplied. Never extrapolated — this is Task 2's queue prediction.
    queueForecast: raw.queue_forecast,
  };
}

export function normalizeDispatchCommand(raw: RawDispatchCommand): DispatchCommand {
  return {
    commandId: raw.command_id,
    vehicleId: raw.vehicle_id,
    routeId: raw.route_id,
    departureTime: raw.departure_time,
    targetSpeed: raw.target_speed,
    slotId: raw.slot_id,
    reasonCode: raw.reason_code,
    timestamp: raw.timestamp,
    state: raw.state,
    limitingVariables: raw.limiting_variables,
    routeNodeIds: raw.route_node_ids,
  };
}

export function normalizeSlotState(raw: RawSlotState): SlotState {
  return {
    slotId: raw.slot_id,
    resourceId: raw.resource_id,
    vehicleId: raw.vehicle_id,
    startTime: raw.start_time,
    endTime: raw.end_time,
    // Conflict status is reported by Task 2. No slot solver runs here.
    status: toSlotStatus(raw.status),
    eta: raw.eta,
    conflictWith: raw.conflict_with,
  };
}

export function normalizeArrivalPlan(raw: RawArrivalPlan): ArrivalPlan {
  return {
    nodeId: raw.node_id,
    issuedAt: raw.issued_at,
    planned: raw.planned.map((p) => ({ at: p.at, count: p.count })),
    actual: raw.actual.map((a) => ({ at: a.at, count: a.count })),
    activeDecisions: raw.active_decisions.map((d) => ({
      vehicleId: d.vehicle_id,
      decision: d.decision,
      until: d.until,
      reasonCode: d.reason_code,
    })),
  };
}

export function normalizeAlert(raw: RawAlert): Alert {
  return {
    alertId: raw.alert_id,
    timestamp: raw.timestamp,
    severity: raw.severity,
    category: raw.category,
    origin: raw.origin,
    subject: { kind: raw.subject.kind, id: raw.subject.id },
    message: raw.message,
    reasonCode: raw.reason_code,
    acknowledgeable: raw.acknowledgeable,
    acknowledged:
      raw.acknowledged === null ? null : { by: raw.acknowledged.by, at: raw.acknowledged.at },
    active: raw.active,
  };
}

export function normalizeEventRecord(raw: RawEventRecord): EventRecord {
  return {
    eventId: raw.event_id,
    timestamp: raw.timestamp,
    category: raw.category,
    subjectId: raw.subject_id,
    payload: raw.payload,
    actor: raw.actor,
  };
}

export function normalizeHealth(raw: RawHealth): Health {
  return {
    componentId: raw.component_id,
    timestamp: raw.timestamp,
    state: toHealthState(raw.state),
    latencyMs: raw.latency_ms,
    ageMs: raw.age_ms,
    errorCode: raw.error_code,
    linkKind: raw.link_kind,
    messagesReceived: raw.messages_received,
    messagesDropped: raw.messages_dropped,
  };
}

export function normalizeSystemHealth(raw: RawSystemHealth): SystemHealth {
  return {
    timestamp: raw.timestamp,
    // Copied as supplied. The HMI never aggregates system mode from vehicle modes.
    systemMode: raw.system_mode,
    connectivity: raw.connectivity,
    fleetCount: raw.fleet_count,
    components: raw.components.map(normalizeHealth),
  };
}

export function normalizeKpiSnapshot(raw: RawKpiSnapshot): KpiSnapshot {
  // Every KPI is copied as supplied. None is computed from telemetry history (PAD-F).
  // Absent stays null and renders as unavailable — never as 0.
  return {
    timestamp: raw.timestamp,
    windowS: raw.window_s,
    throughputTph: raw.throughput_tph,
    cycleTimeS: raw.cycle_time_s,
    queueLengthAvg: raw.queue_length_avg,
    utilization: raw.utilization,
    stopsCount: raw.stops_count,
    safetyEnvelopeViolations: raw.safety_envelope_violations,
    recoveryTimeS: raw.recovery_time_s,
  };
}

export function normalizeCvResult(raw: RawCvResult): CVResult {
  return {
    timestamp: raw.timestamp,
    sourceId: raw.source_id,
    visibilityProxy: raw.visibility_proxy,
    confidence: raw.confidence,
    detections: raw.detections.map((d) => ({
      className: d.class_name,
      confidence: d.confidence,
      bbox: d.bbox,
    })),
    roadState: toSurfaceStateOrNull(raw.road_state),
    status: raw.status,
    frameRef: raw.frame_ref,
  };
}

export function normalizeMineTopology(raw: RawMineTopology): MineTopology {
  return {
    version: raw.version,
    nodes: raw.nodes.map((n) => ({
      nodeId: n.node_id,
      kind: n.kind,
      label: n.label,
      x: n.x,
      y: n.y,
    })),
    segments: raw.segments.map((s) => ({
      segmentId: s.segment_id,
      fromNode: s.from_node,
      toNode: s.to_node,
      lengthM: s.length_m,
      gradeRad: s.grade_rad,
      bidirectional: s.bidirectional,
    })),
  };
}
