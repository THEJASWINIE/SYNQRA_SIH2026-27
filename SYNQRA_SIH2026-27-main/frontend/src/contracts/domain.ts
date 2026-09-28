/**
 * Normalized domain types — M2.
 *
 * Source of truth: `requirements/task1-data-contract.md` §2–§11.
 * Naming: camelCase (MAD-F). The raw wire equivalents keep the contract's snake_case
 * (MAD-E) and live in `raw.ts`. The difference between the two families is deliberate —
 * it makes "has this been normalized yet?" visible in the type name.
 *
 * SCOPE BOUNDARY (PAD-E, scope-control skill):
 * every operational field below is INBOUND ONLY. Task 1 receives and displays these
 * values. Task 1 computes none of them. Fields marked SUPPLIED are the ones most likely
 * to tempt a local calculation; they are called out so the audit has something to check.
 *
 * `[EXT] E-nn` marks a field that is not in PDF §9 and requires Task 2 agreement —
 * the marker is preserved so the negotiation surface stays visible in code.
 */

import type {
  ActiveConstraint,
  AlertCategory,
  AlertOrigin,
  AlertSeverity,
  AlertSubjectKind,
  ArrivalDecision,
  ConnectivityState,
  Criticality,
  CvStatus,
  DispatchState,
  EventCategory,
  HealthState,
  LinkKind,
  NodeKind,
  RiskLevel,
  SlotStatus,
  SurfaceState,
  SystemMode,
  VehicleMode,
} from "./enums";
import type {
  CommandId,
  ComponentId,
  Estimate,
  Iso8601,
  NodeId,
  RouteId,
  SegmentId,
  SlotId,
  VehicleId,
} from "./primitives";

// ---------------------------------------------------------------------------
// 1. VehicleState — contract §2
// ---------------------------------------------------------------------------

export interface VehiclePosition {
  x: number | null;
  y: number | null;
  segmentId: SegmentId | null;
  /** [EXT] E-01 distance along the segment, for map interpolation. */
  offsetM: number | null;
}

export interface VehicleState {
  vehicleId: VehicleId;
  timestamp: Iso8601;
  position: VehiclePosition;
  speedMps: number;
  accelMps2: number;
  /** Road grade at the vehicle (FR-003, S2-a). SUPPLIED. */
  gradeRad: number;
  /** SUPPLIED — friction estimation is Task 2's. */
  frictionEst: Estimate;
  mode: VehicleMode;
  /** 0..1 */
  commConfidence: number;
  /** [EXT] E-02 truck / shovel / other, for map glyphs (FR-002). */
  vehicleKind: string | null;
  /** [EXT] E-02 currently assigned route, for FR-010 cross-reference. */
  routeId: RouteId | null;
}

// ---------------------------------------------------------------------------
// 2. SafetyState — contract §3
// ---------------------------------------------------------------------------

export interface SafetyState {
  vehicleId: VehicleId;
  /** [EXT] E-06 required for freshness (NFR-003). */
  timestamp: Iso8601;
  /** m/s — SUPPLIED BY TASK 2. Never computed here (PAD-E). */
  vSafe: number | null;
  /** SUPPLIED BY TASK 2. Units unresolved — AMB-001 / E-19. Never computed here. */
  hSafe: number | null;
  actualSpeed: number;
  /** [EXT] E-04 FR-005 requires current headway; PDF §9 omits it. SUPPLIED. */
  headwayCurrent: number | null;
  /** [EXT] E-04 the pair partner FR-005 needs. */
  leadVehicleId: VehicleId | null;
  activeConstraint: ActiveConstraint;
  riskLevel: RiskLevel;
  /** [EXT] E-05 supplied if Task 2 evaluates it. Task 1 never models headway. */
  headwayViolation: boolean | null;
  /** [EXT] E-05 supplied. Task 1 never computes the envelope. */
  envelopeViolation: boolean | null;
}

// ---------------------------------------------------------------------------
// 3. RoadState + VisibilityForecast — contract §4
// ---------------------------------------------------------------------------

export interface RoadState {
  segmentId: SegmentId;
  /** [EXT] E-06 freshness. */
  timestamp: Iso8601;
  /** visibility_m + visibility_sigma. SUPPLIED. */
  visibility: Estimate;
  /** [EXT] E-07 friction + sigma. SUPPLIED — no friction computation here. */
  friction: Estimate;
  /** rad */
  grade: number;
  capacityVph: number | null;
  queue: number | null;
  /** 0..1 */
  utilization: number | null;
  /** [EXT] E-07 FR-012 wetness/surface state. */
  surfaceState: SurfaceState | null;
  /** [EXT] E-07 FR-012 optional roughness. */
  roughness: number | null;
}

export interface VisibilityHorizonPoint {
  at: Iso8601;
  visibility: Estimate;
}

/**
 * [EXT] E-08 whole message. FR-011 forecast visibility with uncertainty band.
 * COMPUTED ENTIRELY BY TASK 2. Task 1 draws the band and labels it as forecast.
 * Task 1 never extrapolates or models fog (PAD-E).
 */
export interface VisibilityForecast {
  segmentId: SegmentId;
  issuedAt: Iso8601;
  horizon: VisibilityHorizonPoint[];
}

// ---------------------------------------------------------------------------
// 4. BottleneckState — contract §5
// ---------------------------------------------------------------------------

export interface QueueHistoryPoint {
  at: Iso8601;
  queue: number;
}

export interface QueueForecastPoint {
  at: Iso8601;
  queue: number;
  sigma: number | null;
}

export interface BottleneckState {
  nodeId: NodeId;
  /** [EXT] E-06 freshness. */
  timestamp: Iso8601;
  /** Arrival rate — SUPPLIED. */
  lambdaVph: number | null;
  /** Service rate — SUPPLIED. */
  muVph: number | null;
  queue: number | null;
  queueMax: number | null;
  /** [EXT] E-09 FR-006/FR-007 name utilization explicitly. */
  utilization: number | null;
  criticality: Criticality;
  /** SUPPLIED — the HMI sorts by it (contract §12 item 6) and never derives it. */
  bottleneckScore: number | null;
  /** [EXT] E-09 measured history. */
  queueHistory: QueueHistoryPoint[] | null;
  /**
   * [EXT] E-09 S3 "predicted queue trend" — SUPPLIED BY TASK 2.
   *
   * The most scope-sensitive field in the contract: this is exactly the queue-prediction
   * output the scope-control skill forbids Task 1 from producing. It is consumed, drawn
   * distinctly from `queueHistory`, and never extrapolated.
   */
  queueForecast: QueueForecastPoint[] | null;
}

// ---------------------------------------------------------------------------
// 5. DispatchCommand — contract §6
// ---------------------------------------------------------------------------

/**
 * SUPPLIED BY TASK 2. Task 1 never selects, optimizes or issues an assignment
 * (PAD-B, PAD-C). Whether Task 1 may issue commands at all is AMB-008 — unresolved.
 */
export interface DispatchCommand {
  commandId: CommandId;
  vehicleId: VehicleId;
  routeId: RouteId | null;
  departureTime: Iso8601 | null;
  /** m/s */
  targetSpeed: number | null;
  slotId: SlotId | null;
  /** Mandatory per NFR-006. An empty string is a data defect, not a valid value. */
  reasonCode: string;
  timestamp: Iso8601;
  /** [EXT] E-11 recommended vs issued, for display (FR-010). */
  state: DispatchState;
  /** [EXT] E-11 NFR-006 "key limiting variables". */
  limitingVariables: string[] | null;
  /** [EXT] E-11 to draw the route on the map (FR-010). */
  routeNodeIds: NodeId[] | null;
}

// ---------------------------------------------------------------------------
// 6. SlotState + ArrivalPlan — contract §7
// ---------------------------------------------------------------------------

/** Conflicts are determined by TASK 2. Task 1 runs no slot solver. */
export interface SlotState {
  slotId: SlotId;
  /** switchback / intersection / crusher / shovel */
  resourceId: NodeId;
  /** Current holder; null = unheld. */
  vehicleId: VehicleId | null;
  startTime: Iso8601;
  endTime: Iso8601;
  status: SlotStatus;
  /** [EXT] E-12 FR-009 requires ETA; PDF §9 omits it. */
  eta: Iso8601 | null;
  /** [EXT] E-12 the conflicting party, needed to render conflict usefully. */
  conflictWith: SlotId[] | null;
}

export interface ArrivalCount {
  at: Iso8601;
  count: number;
}

export interface ArrivalDecisionRecord {
  vehicleId: VehicleId;
  decision: ArrivalDecision;
  until: Iso8601 | null;
  reasonCode: string;
}

/**
 * [EXT] E-10 whole message (AMB-002). SUPPLIED BY TASK 2.
 * Task 1 never generates an arrival plan and never decides metering (PAD-F).
 */
export interface ArrivalPlan {
  nodeId: NodeId;
  issuedAt: Iso8601;
  planned: ArrivalCount[];
  actual: ArrivalCount[];
  activeDecisions: ArrivalDecisionRecord[];
}

// ---------------------------------------------------------------------------
// 7. Alert + EventRecord — contract §8
// ---------------------------------------------------------------------------

export interface AlertSubject {
  kind: AlertSubjectKind;
  id: string;
}

export interface AlertAcknowledgement {
  /** Operator identity. */
  by: string;
  at: Iso8601;
}

/**
 * [EXT] E-13 whole message.
 *
 * The HMI may originate only STALE_DATA and COMM_LOSS — both properties of the data path
 * it owns. The other four categories are supplied by Task 2 and are never raised from a
 * local safety or bottleneck calculation (FR-014, contract §12 item 4).
 */
export interface Alert {
  alertId: string;
  timestamp: Iso8601;
  severity: AlertSeverity;
  category: AlertCategory;
  origin: AlertOrigin;
  subject: AlertSubject;
  message: string;
  reasonCode: string | null;
  /** false for safety-critical (FR-015). */
  acknowledgeable: boolean;
  /** Acknowledgement changes display and audit state only — never the condition (PAD-D). */
  acknowledged: AlertAcknowledgement | null;
  active: boolean;
}

/** [EXT] E-14 append-only audit record backing S5 and NFR-007. */
export interface EventRecord {
  eventId: string;
  timestamp: Iso8601;
  category: EventCategory;
  subjectId: string | null;
  /** The alert, command or mode transition, as received. Opaque by design. */
  payload: unknown;
  /** Operator identity for operator-initiated events. */
  actor: string | null;
}

// ---------------------------------------------------------------------------
// 8. Health + SystemHealth + KpiSnapshot — contract §9
// ---------------------------------------------------------------------------

/**
 * Component and link health SUPPLIED by the wider system.
 *
 * Distinct from M1's `BackendHealth` in `api/healthClient.ts`, which is the liveness of
 * the HMI's own backend process. The two answer different questions and are deliberately
 * not merged; they meet as separate rows on S6 Diagnostics in M10.
 */
export interface Health {
  componentId: ComponentId;
  timestamp: Iso8601;
  state: HealthState;
  latencyMs: number | null;
  /** Supplied by the producer. Distinct from `Sourced.ageMs`, which Task 1 derives. */
  ageMs: number | null;
  errorCode: string | null;
  /** [EXT] E-15 FR-013 link kinds. */
  linkKind: LinkKind | null;
  /** [EXT] E-15 S6-a message counts. */
  messagesReceived: number | null;
  /** [EXT] E-15 S6-a. */
  messagesDropped: number | null;
}

/**
 * [EXT] E-15 whole message. Global roll-up for the status bar.
 * `systemMode` is SUPPLIED; the HMI may force the *displayed* mode to at least DEGRADED
 * on data-path loss (FR-016, NFR-012, contract §12 item 5) but never aggregates it.
 */
export interface SystemHealth {
  timestamp: Iso8601;
  systemMode: SystemMode;
  connectivity: ConnectivityState;
  fleetCount: number;
  components: Health[];
}

/**
 * [EXT] E-16 whole message (AMB-003). All seven KPIs are SUPPLIED.
 *
 * Deriving these from telemetry history inside Task 1 would be computing operational
 * metrics over a simulation Task 1 does not own (PAD-F). Absent values stay null and are
 * rendered as unavailable — never as 0.
 */
export interface KpiSnapshot {
  timestamp: Iso8601;
  /** Averaging window, if any. */
  windowS: number | null;
  throughputTph: number | null;
  cycleTimeS: number | null;
  queueLengthAvg: number | null;
  /** 0..1 */
  utilization: number | null;
  stopsCount: number | null;
  safetyEnvelopeViolations: number | null;
  recoveryTimeS: number | null;
}

// ---------------------------------------------------------------------------
// 9. CVResult — contract §10 (optional feature, M13)
// ---------------------------------------------------------------------------

export interface CvDetection {
  className: string;
  confidence: number;
  bbox: [number, number, number, number] | null;
}

/**
 * Optional. CV output is advisory (OPS-004) and must be labelled non-authoritative next
 * to physics-derived values. Typed in M2 so the contract is complete; no CV code exists.
 */
export interface CVResult {
  timestamp: Iso8601;
  sourceId: ComponentId;
  visibilityProxy: number | null;
  /** 0..1 */
  confidence: number | null;
  detections: CvDetection[];
  roadState: SurfaceState | null;
  /** [EXT] E-18 CV-005 graceful failure. */
  status: CvStatus;
  /** [EXT] E-18 FR-020 requires the frame be shown. */
  frameRef: string | null;
}

// ---------------------------------------------------------------------------
// 10. MineTopology — contract §11
// ---------------------------------------------------------------------------

export interface TopologyNode {
  nodeId: NodeId;
  kind: NodeKind;
  label: string;
  x: number;
  y: number;
}

export interface TopologySegment {
  segmentId: SegmentId;
  fromNode: NodeId;
  toNode: NodeId;
  lengthM: number;
  gradeRad: number;
  bidirectional: boolean;
}

/**
 * [EXT] E-17 whole message (AMB-011). Quasi-static: fetched once, refreshed on version
 * change. Without it the map cannot be data-driven, which the architecture skill requires.
 */
export interface MineTopology {
  version: string;
  nodes: TopologyNode[];
  segments: TopologySegment[];
}
