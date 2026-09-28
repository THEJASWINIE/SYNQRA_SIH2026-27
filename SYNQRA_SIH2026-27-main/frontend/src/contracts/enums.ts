/**
 * Contract enums — M2.
 *
 * Source of truth: `requirements/task1-data-contract.md` §2–§11.
 *
 * Every enum that the HMI must render carries `UNKNOWN` (contract [EXT] E-03). An
 * unrecognised value from the producer normalizes to `UNKNOWN` — it is never dropped and
 * never causes an otherwise valid message to be rejected. AMB-007 leaves the real value
 * sets unagreed; `UNKNOWN` is what absorbs that until Task 2 confirms them.
 *
 * These are value sets, not judgements. Nothing here ranks, scores or thresholds them.
 */

export const VEHICLE_MODES = [
  "NORMAL",
  "CAUTION",
  "DEGRADED",
  "LOCAL_SAFE",
  "STOP_UNSAFE",
  "UNKNOWN",
] as const;
export type VehicleMode = (typeof VEHICLE_MODES)[number];

/**
 * PDF §5 FR-016 defines these five for the *system*. Whether the vehicle-level and
 * system-level sets are identical is AMB-005 — unresolved, so the two are kept separate.
 * `SystemMode` has no `UNKNOWN` in the contract; unrecognised values are handled by
 * marking the containing datum INVALID rather than by inventing a member.
 */
export const SYSTEM_MODES = ["NORMAL", "CAUTION", "DEGRADED", "LOCAL_SAFE", "STOP_UNSAFE"] as const;
export type SystemMode = (typeof SYSTEM_MODES)[number];

/** Verbatim from PDF §5 FR-004. */
export const ACTIVE_CONSTRAINTS = [
  "VISIBILITY",
  "FRICTION",
  "GRADE",
  "BRAKING_RETARDER",
  "CURVE",
  "SITE_LIMIT",
  "NONE",
  "UNKNOWN",
] as const;
export type ActiveConstraint = (typeof ACTIVE_CONSTRAINTS)[number];

/** Band names are not specified in the PDF — AMB-007. */
export const RISK_LEVELS = ["LOW", "MODERATE", "HIGH", "CRITICAL", "UNKNOWN"] as const;
export type RiskLevel = (typeof RISK_LEVELS)[number];

/** Band names are not specified in the PDF — AMB-007. */
export const CRITICALITIES = ["LOW", "MEDIUM", "HIGH", "CRITICAL", "UNKNOWN"] as const;
export type Criticality = (typeof CRITICALITIES)[number];

/** [EXT] Set to be agreed with Task 2 — AMB-007. */
export const SURFACE_STATES = ["DRY", "WET", "MUDDY", "ICY", "UNKNOWN"] as const;
export type SurfaceState = (typeof SURFACE_STATES)[number];

export const SLOT_STATUSES = [
  "RESERVED",
  "ACTIVE",
  "RELEASED",
  "EXPIRED",
  "CONFLICT",
  "UNKNOWN",
] as const;
export type SlotStatus = (typeof SLOT_STATUSES)[number];

/**
 * [EXT] Command lifecycle state. FR-010 requires recommended and issued to be
 * distinguishable *for display*. Whether Task 1 may itself issue a command is AMB-008 —
 * unresolved. This enum describes what the producer reports, nothing the HMI may do.
 */
export const DISPATCH_STATES = [
  "RECOMMENDED",
  "ISSUED",
  "ACKNOWLEDGED",
  "SUPERSEDED",
  "REJECTED",
] as const;
export type DispatchState = (typeof DISPATCH_STATES)[number];

/** The six categories named in FR-014. */
export const ALERT_CATEGORIES = [
  "UNSAFE_SPEED",
  "UNSAFE_HEADWAY",
  "BOTTLENECK_RISK",
  "COMM_LOSS",
  "STALE_DATA",
  "SLOT_CONFLICT",
] as const;
export type AlertCategory = (typeof ALERT_CATEGORIES)[number];

export const ALERT_SEVERITIES = ["INFO", "WARNING", "CRITICAL"] as const;
export type AlertSeverity = (typeof ALERT_SEVERITIES)[number];

/** The HMI may originate only STALE_DATA and COMM_LOSS (contract §8). */
export const ALERT_ORIGINS = ["TASK2", "HMI"] as const;
export type AlertOrigin = (typeof ALERT_ORIGINS)[number];

export const ALERT_SUBJECT_KINDS = ["VEHICLE", "NODE", "SEGMENT", "SLOT", "SYSTEM"] as const;
export type AlertSubjectKind = (typeof ALERT_SUBJECT_KINDS)[number];

/** Per S5-a and NFR-007. */
export const EVENT_CATEGORIES = [
  "FOG_CHANGE",
  "ALERT_RAISED",
  "ALERT_ACKNOWLEDGED",
  "COMMAND_RECEIVED",
  "COMMAND_ISSUED",
  "QUEUE_CHANGE",
  "VIOLATION",
  "RECOVERY",
  "MODE_TRANSITION",
] as const;
export type EventCategory = (typeof EVENT_CATEGORIES)[number];

export const HEALTH_STATES = ["UP", "DEGRADED", "DOWN", "UNKNOWN"] as const;
export type HealthState = (typeof HEALTH_STATES)[number];

/** [EXT] FR-013 link kinds. */
export const LINK_KINDS = ["V2V", "V2I", "LORA", "BACKEND", "SENSOR"] as const;
export type LinkKind = (typeof LINK_KINDS)[number];

export const CONNECTIVITY_STATES = ["CONNECTED", "DEGRADED", "DISCONNECTED"] as const;
export type ConnectivityState = (typeof CONNECTIVITY_STATES)[number];

/** [EXT] CV-005 graceful failure. */
export const CV_STATUSES = ["OK", "UNAVAILABLE", "STALE"] as const;
export type CvStatus = (typeof CV_STATUSES)[number];

export const NODE_KINDS = ["SHOVEL", "CRUSHER", "INTERSECTION", "SWITCHBACK", "WAYPOINT"] as const;
export type NodeKind = (typeof NODE_KINDS)[number];

/** [EXT] FR-008 metering decisions, as reported by Task 2. The HMI decides nothing. */
export const ARRIVAL_DECISIONS = ["HOLD", "METER", "RELEASE"] as const;
export type ArrivalDecision = (typeof ARRIVAL_DECISIONS)[number];

/**
 * Enums for which an unrecognised producer value normalizes to `UNKNOWN`
 * rather than invalidating the message. Contract E-03.
 */
export const UNKNOWN_TOLERANT = {
  vehicleMode: "UNKNOWN",
  activeConstraint: "UNKNOWN",
  riskLevel: "UNKNOWN",
  criticality: "UNKNOWN",
  surfaceState: "UNKNOWN",
  slotStatus: "UNKNOWN",
  healthState: "UNKNOWN",
} as const;
