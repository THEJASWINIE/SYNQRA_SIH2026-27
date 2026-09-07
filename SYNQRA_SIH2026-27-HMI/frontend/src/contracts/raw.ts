/**
 * Raw wire schemas — M2.
 *
 * These describe the external payload EXACTLY as the producer sends it, in the
 * contract's snake_case (MAD-E). They are untrusted input. Nothing downstream may
 * consume a raw type without it having passed through `data/validate.ts` first
 * (realtime-data skill §7).
 *
 * zod is the validator (MAD-A): one schema yields both the runtime check and the
 * inferred type, so the two cannot silently diverge.
 *
 * Enum handling: fields the contract requires to tolerate unknown values are typed here
 * as `z.string()`, NOT as an enum. Rejecting an otherwise valid message because one enum
 * member is unrecognised is forbidden (contract E-03) — normalization maps the unknown
 * value to `UNKNOWN` instead. Enums with no `UNKNOWN` member in the contract stay strict.
 */

import { z } from "zod";

// ---------------------------------------------------------------------------
// Primitives
// ---------------------------------------------------------------------------

/**
 * A timestamp string. Deliberately NOT validated for format here — timestamp legality
 * is decided in one place, `data/timestamps.ts`, so the rules (timezone required,
 * parseable, not absurdly future) live together rather than being split between the
 * schema and the normalizer.
 */
const isoString = z.string();

export const estimateSchema = z.object({
  value: z.number().nullable(),
  sigma: z.number().nullable(),
});

/** Enum members the contract does NOT extend with UNKNOWN stay strict. */
const systemModeSchema = z.enum(["NORMAL", "CAUTION", "DEGRADED", "LOCAL_SAFE", "STOP_UNSAFE"]);
const alertSeveritySchema = z.enum(["INFO", "WARNING", "CRITICAL"]);
const alertOriginSchema = z.enum(["TASK2", "HMI"]);
const alertCategorySchema = z.enum([
  "UNSAFE_SPEED",
  "UNSAFE_HEADWAY",
  "BOTTLENECK_RISK",
  "COMM_LOSS",
  "STALE_DATA",
  "SLOT_CONFLICT",
]);
const alertSubjectKindSchema = z.enum(["VEHICLE", "NODE", "SEGMENT", "SLOT", "SYSTEM"]);
const eventCategorySchema = z.enum([
  "FOG_CHANGE",
  "ALERT_RAISED",
  "ALERT_ACKNOWLEDGED",
  "COMMAND_RECEIVED",
  "COMMAND_ISSUED",
  "QUEUE_CHANGE",
  "VIOLATION",
  "RECOVERY",
  "MODE_TRANSITION",
]);
const dispatchStateSchema = z.enum([
  "RECOMMENDED",
  "ISSUED",
  "ACKNOWLEDGED",
  "SUPERSEDED",
  "REJECTED",
]);
const connectivitySchema = z.enum(["CONNECTED", "DEGRADED", "DISCONNECTED"]);
const linkKindSchema = z.enum(["V2V", "V2I", "LORA", "BACKEND", "SENSOR"]);
const cvStatusSchema = z.enum(["OK", "UNAVAILABLE", "STALE"]);
const nodeKindSchema = z.enum(["SHOVEL", "CRUSHER", "INTERSECTION", "SWITCHBACK", "WAYPOINT"]);
const arrivalDecisionSchema = z.enum(["HOLD", "METER", "RELEASE"]);

/** Unknown-tolerant: accepted as a string, mapped to UNKNOWN during normalization. */
const tolerantEnum = z.string();

// ---------------------------------------------------------------------------
// Messages — contract §2–§11
// ---------------------------------------------------------------------------

export const rawVehicleStateSchema = z.object({
  vehicle_id: z.string(),
  timestamp: isoString,
  position: z.object({
    x: z.number().nullable(),
    y: z.number().nullable(),
    segment_id: z.string().nullable(),
    offset_m: z.number().nullable(),
  }),
  // P6.1: nullable where the canonical Twin may legitimately have no value.
  // null means UNAVAILABLE - never 0, never a stand-in.
  speed_mps: z.number().nullable(),
  accel_mps2: z.number().nullable(),
  grade_rad: z.number().nullable(),
  friction_est: estimateSchema.nullable(),
  mode: tolerantEnum,
  comm_confidence: z.number().nullable(),
  vehicle_kind: z.string().nullable(),
  route_id: z.string().nullable(),
});

export const rawSafetyStateSchema = z.object({
  vehicle_id: z.string(),
  timestamp: isoString,
  v_safe: z.number().nullable(),
  h_safe: z.number().nullable(),
  actual_speed: z.number(),
  headway_current: z.number().nullable(),
  lead_vehicle_id: z.string().nullable(),
  active_constraint: tolerantEnum,
  risk_level: tolerantEnum,
  headway_violation: z.boolean().nullable(),
  envelope_violation: z.boolean().nullable(),
});

export const rawRoadStateSchema = z.object({
  segment_id: z.string(),
  timestamp: isoString,
  visibility: estimateSchema,
  friction: estimateSchema,
  grade: z.number(),
  capacity_vph: z.number().nullable(),
  queue: z.number().nullable(),
  utilization: z.number().nullable(),
  surface_state: tolerantEnum.nullable(),
  roughness: z.number().nullable(),
});

export const rawVisibilityForecastSchema = z.object({
  segment_id: z.string(),
  issued_at: isoString,
  horizon: z.array(
    z.object({
      at: isoString,
      visibility: estimateSchema,
    }),
  ),
});

export const rawBottleneckStateSchema = z.object({
  node_id: z.string(),
  timestamp: isoString,
  lambda_vph: z.number().nullable(),
  mu_vph: z.number().nullable(),
  queue: z.number().nullable(),
  queue_max: z.number().nullable(),
  utilization: z.number().nullable(),
  criticality: tolerantEnum,
  bottleneck_score: z.number().nullable(),
  queue_history: z.array(z.object({ at: isoString, queue: z.number() })).nullable(),
  queue_forecast: z
    .array(z.object({ at: isoString, queue: z.number(), sigma: z.number().nullable() }))
    .nullable(),
});

export const rawDispatchCommandSchema = z.object({
  command_id: z.string(),
  vehicle_id: z.string(),
  route_id: z.string().nullable(),
  departure_time: isoString.nullable(),
  target_speed: z.number().nullable(),
  slot_id: z.string().nullable(),
  reason_code: z.string(),
  timestamp: isoString,
  state: dispatchStateSchema,
  limiting_variables: z.array(z.string()).nullable(),
  route_node_ids: z.array(z.string()).nullable(),
});

export const rawSlotStateSchema = z.object({
  slot_id: z.string(),
  resource_id: z.string(),
  vehicle_id: z.string().nullable(),
  start_time: isoString,
  end_time: isoString,
  status: tolerantEnum,
  eta: isoString.nullable(),
  conflict_with: z.array(z.string()).nullable(),
});

export const rawArrivalPlanSchema = z.object({
  node_id: z.string(),
  issued_at: isoString,
  planned: z.array(z.object({ at: isoString, count: z.number() })),
  actual: z.array(z.object({ at: isoString, count: z.number() })),
  active_decisions: z.array(
    z.object({
      vehicle_id: z.string(),
      decision: arrivalDecisionSchema,
      until: isoString.nullable(),
      reason_code: z.string(),
    }),
  ),
});

export const rawAlertSchema = z.object({
  alert_id: z.string(),
  timestamp: isoString,
  severity: alertSeveritySchema,
  category: alertCategorySchema,
  origin: alertOriginSchema,
  subject: z.object({ kind: alertSubjectKindSchema, id: z.string() }),
  message: z.string(),
  reason_code: z.string().nullable(),
  acknowledgeable: z.boolean(),
  acknowledged: z.object({ by: z.string(), at: isoString }).nullable(),
  active: z.boolean(),
});

export const rawEventRecordSchema = z.object({
  event_id: z.string(),
  timestamp: isoString,
  category: eventCategorySchema,
  subject_id: z.string().nullable(),
  payload: z.unknown(),
  actor: z.string().nullable(),
});

export const rawHealthSchema = z.object({
  component_id: z.string(),
  timestamp: isoString,
  state: tolerantEnum,
  latency_ms: z.number().nullable(),
  age_ms: z.number().nullable(),
  error_code: z.string().nullable(),
  link_kind: linkKindSchema.nullable(),
  messages_received: z.number().nullable(),
  messages_dropped: z.number().nullable(),
});

export const rawSystemHealthSchema = z.object({
  timestamp: isoString,
  system_mode: systemModeSchema,
  connectivity: connectivitySchema,
  fleet_count: z.number(),
  components: z.array(rawHealthSchema),
});

export const rawKpiSnapshotSchema = z.object({
  timestamp: isoString,
  window_s: z.number().nullable(),
  throughput_tph: z.number().nullable(),
  cycle_time_s: z.number().nullable(),
  queue_length_avg: z.number().nullable(),
  utilization: z.number().nullable(),
  stops_count: z.number().nullable(),
  safety_envelope_violations: z.number().nullable(),
  recovery_time_s: z.number().nullable(),
});

export const rawCvResultSchema = z.object({
  timestamp: isoString,
  source_id: z.string(),
  visibility_proxy: z.number().nullable(),
  confidence: z.number().nullable(),
  detections: z.array(
    z.object({
      class_name: z.string(),
      confidence: z.number(),
      bbox: z.tuple([z.number(), z.number(), z.number(), z.number()]).nullable(),
    }),
  ),
  road_state: tolerantEnum.nullable(),
  status: cvStatusSchema,
  frame_ref: z.string().nullable(),
});

export const rawMineTopologySchema = z.object({
  version: z.string(),
  nodes: z.array(
    z.object({
      node_id: z.string(),
      kind: nodeKindSchema,
      label: z.string(),
      x: z.number(),
      y: z.number(),
    }),
  ),
  segments: z.array(
    z.object({
      segment_id: z.string(),
      from_node: z.string(),
      to_node: z.string(),
      length_m: z.number(),
      grade_rad: z.number(),
      bidirectional: z.boolean(),
    }),
  ),
});

// ---------------------------------------------------------------------------
// Registry
// ---------------------------------------------------------------------------

/** The fifteen contract messages, addressable by name. */
/**
 * P6.1 — canonical Twin field envelope.
 *
 * Every dynamic field the backend projects carries its own provenance. `source` and
 * `origin` are deliberately separate: source=DERIVED + origin=HARDWARE (a speed computed
 * from a measured RPM) must never collapse into source=HARDWARE.
 */
export const twinFieldSchema = z.object({
  value: z.unknown(),
  timestamp: z.number().nullable(),
  source: tolerantEnum,
  origin: tolerantEnum,
  quality: tolerantEnum,
  age_s: z.number().nullable(),
  available: z.boolean(),
  clock_domain: tolerantEnum,
  freshness: tolerantEnum,
});

export const rawTwinVehicleSchema = z.object({
  vehicle_id: z.string(),
  static: z.record(z.string(), z.unknown()).optional(),
  dynamic: z.record(z.string(), twinFieldSchema),
  has_hardware_data: z.boolean().optional(),
});

export const RAW_SCHEMAS = {
  TwinVehicle: rawTwinVehicleSchema,
  VehicleState: rawVehicleStateSchema,
  SafetyState: rawSafetyStateSchema,
  RoadState: rawRoadStateSchema,
  VisibilityForecast: rawVisibilityForecastSchema,
  BottleneckState: rawBottleneckStateSchema,
  DispatchCommand: rawDispatchCommandSchema,
  SlotState: rawSlotStateSchema,
  ArrivalPlan: rawArrivalPlanSchema,
  Alert: rawAlertSchema,
  EventRecord: rawEventRecordSchema,
  Health: rawHealthSchema,
  SystemHealth: rawSystemHealthSchema,
  KpiSnapshot: rawKpiSnapshotSchema,
  CVResult: rawCvResultSchema,
  MineTopology: rawMineTopologySchema,
} as const;

export type MessageType = keyof typeof RAW_SCHEMAS;

export const MESSAGE_TYPES = Object.keys(RAW_SCHEMAS) as MessageType[];

export type RawTwinField = z.infer<typeof twinFieldSchema>;
export type RawTwinVehicle = z.infer<typeof rawTwinVehicleSchema>;
export type RawVehicleState = z.infer<typeof rawVehicleStateSchema>;
export type RawSafetyState = z.infer<typeof rawSafetyStateSchema>;
export type RawRoadState = z.infer<typeof rawRoadStateSchema>;
export type RawVisibilityForecast = z.infer<typeof rawVisibilityForecastSchema>;
export type RawBottleneckState = z.infer<typeof rawBottleneckStateSchema>;
export type RawDispatchCommand = z.infer<typeof rawDispatchCommandSchema>;
export type RawSlotState = z.infer<typeof rawSlotStateSchema>;
export type RawArrivalPlan = z.infer<typeof rawArrivalPlanSchema>;
export type RawAlert = z.infer<typeof rawAlertSchema>;
export type RawEventRecord = z.infer<typeof rawEventRecordSchema>;
export type RawHealth = z.infer<typeof rawHealthSchema>;
export type RawSystemHealth = z.infer<typeof rawSystemHealthSchema>;
export type RawKpiSnapshot = z.infer<typeof rawKpiSnapshotSchema>;
export type RawCvResult = z.infer<typeof rawCvResultSchema>;
export type RawMineTopology = z.infer<typeof rawMineTopologySchema>;
