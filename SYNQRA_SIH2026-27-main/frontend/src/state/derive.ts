/**
 * Display derivations — M4. PURE FUNCTIONS ONLY.
 *
 * ============================================================================
 *  SCOPE BOUNDARY — READ BEFORE ADDING ANYTHING TO THIS FILE
 *
 *  Task 1 derives exactly two kinds of thing, and both are properties of the
 *  data path or of presentation, never of the mine (contract §12 items 1–2, 6):
 *
 *    1. data age, from a supplied timestamp   — see `state/freshness.ts`
 *    2. display comparison, ordering, projection and unit formatting of
 *       ALREADY-SUPPLIED values                — this file
 *
 *  Nothing here computes v_safe, h_safe, stopping distance, friction, a queue,
 *  a bottleneck score, a dispatch decision, a route or a forecast. Nothing here
 *  interpolates, extrapolates or smooths a supplied series. A function that did
 *  any of those would be Task 2 code in a Task 1 repository.
 * ============================================================================
 */

import type { AppState } from "../contracts/appState";
import type {
  Alert,
  BottleneckState,
  DispatchCommand,
  MineTopology,
  RoadState,
  SafetyState,
  SlotState,
  VehicleState,
} from "../contracts/domain";
import type { AlertSeverity } from "../contracts/enums";

// ---------------------------------------------------------------------------
// Units
// ---------------------------------------------------------------------------

/**
 * Display conversion only. Both members of a compared pair are converted with the same
 * factor, so no comparison can change which side of a threshold it falls on. The
 * violation test itself runs on the supplied m/s values, not on these.
 */
const MPS_TO_KMH = 3.6;

export function kmh(mps: number | null | undefined): number | null {
  return mps === null || mps === undefined ? null : mps * MPS_TO_KMH;
}

/** Formats a number for display, or the explicit unavailable marker. Never renders 0 for absent. */
export function fmt(value: number | null | undefined, digits = 1): string {
  return value === null || value === undefined || !Number.isFinite(value)
    ? "—"
    : value.toFixed(digits);
}

// ---------------------------------------------------------------------------
// Alerts — ordering is a display sort on supplied values (contract §12 item 6)
// ---------------------------------------------------------------------------

const SEVERITY_RANK: Record<AlertSeverity, number> = {
  CRITICAL: 0,
  WARNING: 1,
  INFO: 2,
};

/**
 * Active alerts, most severe first, then most recent first.
 *
 * Severity is supplied. This orders supplied values; it never assigns or promotes one.
 */
export function rankAlerts(alerts: readonly Alert[]): Alert[] {
  return alerts
    .filter((a) => a.active)
    .slice()
    .sort((a, b) => {
      const bySeverity = SEVERITY_RANK[a.severity] - SEVERITY_RANK[b.severity];
      if (bySeverity !== 0) return bySeverity;
      const byRecency = b.timestamp.localeCompare(a.timestamp);
      if (byRecency !== 0) return byRecency;
      // Alert id is the final tiebreak, so equal severity AND equal timestamp still
      // produce one fixed order. FR-014 AC2 requires ordering to be deterministic
      // across shuffled input; without this, two simultaneous alerts of the same
      // severity would render in whatever order they happened to arrive.
      return a.alertId.localeCompare(b.alertId);
    });
}

export function criticalAlerts(alerts: readonly Alert[]): Alert[] {
  return rankAlerts(alerts).filter((a) => a.severity === "CRITICAL");
}

// ---------------------------------------------------------------------------
// Bottlenecks — ranking by a SUPPLIED score
// ---------------------------------------------------------------------------

/**
 * Bottlenecks ordered by supplied `bottleneckScore`, highest first.
 *
 * The score is Task 2's output. Task 1 sorts by it and never derives it — a node with no
 * supplied score sorts last rather than being given one.
 */
export function rankBottlenecks(bottlenecks: Record<string, BottleneckState>): BottleneckState[] {
  return Object.values(bottlenecks)
    .slice()
    .sort(
      (a, b) =>
        (b.bottleneckScore ?? Number.NEGATIVE_INFINITY) -
          (a.bottleneckScore ?? Number.NEGATIVE_INFINITY) || a.nodeId.localeCompare(b.nodeId),
    );
}

/** The highest-ranked bottleneck, or null when none was supplied. */
export function activeBottleneck(
  bottlenecks: Record<string, BottleneckState>,
): BottleneckState | null {
  return rankBottlenecks(bottlenecks)[0] ?? null;
}

// ---------------------------------------------------------------------------
// Safety presentation
// ---------------------------------------------------------------------------

export interface SpeedView {
  actualKmh: number;
  /** Null when Task 2 supplied no safe speed. NEVER substituted. */
  safeKmh: number | null;
  /**
   * True only when both values were supplied and actual exceeds safe.
   * A display comparison on two supplied values — permitted by contract §12 item 6.
   */
  violation: boolean;
  /** Non-empty text whenever a violation is shown, so colour is never the only signal. */
  violationText: string | null;
  /** True when no safe speed was supplied, so the pair cannot be compared at all. */
  safeSpeedUnavailable: boolean;
}

export const OVER_SAFE_SPEED_TEXT = "OVER SAFE SPEED";

/**
 * Actual speed beside supplied safe speed.
 *
 * `vSafe` is SUPPLIED BY TASK 2 and is never computed, adjusted, buffered, clamped or
 * rounded in a direction that changes meaning. When it is absent the pair is
 * incomparable, and no violation marker may be shown — there is nothing to violate.
 */
export function speedView(safety: SafetyState | undefined): SpeedView | null {
  if (!safety) return null;

  const safeSpeedUnavailable = safety.vSafe === null;
  const violation = safety.vSafe !== null && safety.actualSpeed > safety.vSafe;

  return {
    actualKmh: safety.actualSpeed * MPS_TO_KMH,
    safeKmh: kmh(safety.vSafe),
    violation,
    violationText: violation ? OVER_SAFE_SPEED_TEXT : null,
    safeSpeedUnavailable,
  };
}

export interface HeadwayView {
  current: number | null;
  hSafe: number | null;
  leadVehicleId: string | null;
  /** SUPPLIED by Task 2 when it evaluates headway. Never derived locally. */
  suppliedViolation: boolean | null;
  /** Always true while AMB-001 is open. Rendered so the operator is not misled. */
  unitsUnresolved: true;
}

export const HSAFE_UNIT_NOTE = "unit unresolved — AMB-001";

/**
 * Headway pair.
 *
 * AMB-001 is UNRESOLVED: the specification does not state whether `h_safe` is a distance
 * or a time. So this view carries both numbers and DOES NOT COMPARE THEM. An unlabelled
 * numeric comparison across unknown units looks authoritative and would be worse than no
 * comparison at all. Where Task 2 supplies `headwayViolation`, that flag is what the HMI
 * displays.
 */
export function headwayView(safety: SafetyState | undefined): HeadwayView | null {
  if (!safety) return null;
  return {
    current: safety.headwayCurrent,
    hSafe: safety.hSafe,
    leadVehicleId: safety.leadVehicleId,
    suppliedViolation: safety.headwayViolation,
    unitsUnresolved: true,
  };
}

// ---------------------------------------------------------------------------
// Mine map projection — SUPPLIED COORDINATES ONLY
// ---------------------------------------------------------------------------

export interface Projection {
  minX: number;
  minY: number;
  width: number;
  height: number;
}

export const MAP_PADDING = 40;

/**
 * Viewport bounds from supplied node coordinates.
 *
 * This is a display projection: it scales and offsets coordinates the data layer
 * supplied. It invents no coordinate and infers no position.
 */
export function projectTopology(topology: MineTopology | null): Projection | null {
  if (!topology || topology.nodes.length === 0) return null;

  const xs = topology.nodes.map((n) => n.x);
  const ys = topology.nodes.map((n) => n.y);
  const minX = Math.min(...xs);
  const maxX = Math.max(...xs);
  const minY = Math.min(...ys);
  const maxY = Math.max(...ys);

  return {
    minX: minX - MAP_PADDING,
    minY: minY - MAP_PADDING,
    width: Math.max(maxX - minX, 1) + MAP_PADDING * 2,
    height: Math.max(maxY - minY, 1) + MAP_PADDING * 2,
  };
}

/** How a marker's coordinate was obtained. Shown to the operator, never hidden. */
export type PositionSource = "SUPPLIED" | "SEGMENT_GEOMETRY";

/** Why no coordinate could be produced. Each value names a specific missing input. */
export type PositionUnavailableReason =
  | "NO_SEGMENT_ID"
  | "UNKNOWN_SEGMENT"
  | "NO_OFFSET"
  | "SEGMENT_ENDPOINT_MISSING"
  | "SEGMENT_LENGTH_MISSING"
  | "NO_TOPOLOGY";

export type PositionResolution =
  | { ok: true; x: number; y: number; source: PositionSource }
  | { ok: false; reason: PositionUnavailableReason };

export interface PlacedVehicle {
  vehicle: VehicleState;
  x: number;
  y: number;
  source: PositionSource;
}

export interface UnplacedVehicle {
  vehicle: VehicleState;
  reason: PositionUnavailableReason;
}

export interface VehiclePlacement {
  placed: PlacedVehicle[];
  /** Vehicles no supplied input could place. Shown, never hidden, never guessed. */
  unplaced: UnplacedVehicle[];
}

/** Readable text for a missing-position reason. Colour is never the only signal. */
export const POSITION_UNAVAILABLE_REASON_TEXT: Readonly<Record<PositionUnavailableReason, string>> =
  {
    NO_TOPOLOGY: "no topology supplied",
    NO_SEGMENT_ID: "no segment supplied",
    UNKNOWN_SEGMENT: "segment not in supplied topology",
    NO_OFFSET: "no offset along segment supplied",
    SEGMENT_ENDPOINT_MISSING: "segment endpoint missing from supplied topology",
    SEGMENT_LENGTH_MISSING: "segment length not supplied",
  };

/**
 * Resolve a vehicle's map coordinate. M4D-F.
 *
 * ==========================================================================
 *  THE ONLY DERIVED COORDINATE IN TASK 1. Closed derivation list, item 9.
 *
 *  Two paths, in order:
 *
 *    1. Supplied `x`/`y`               — used as given, always wins.
 *    2. Supplied `segmentId` + supplied `offsetM` + supplied node geometry
 *       — a deterministic geometric transform, permitted by HMI-FR-002
 *         ("Vehicles drawn at x/y or interpolated along segment_id") and
 *         supplied for by E-01.
 *
 *  The transform is a pure function of supplied data. It reads no clock, no
 *  history and no previous position, so the same inputs always give the same
 *  point. It answers "where is this vehicle now", never "where will it be".
 *
 *  NOT enabled by this, and never to be added here: trajectory prediction,
 *  future position estimation, speed calculation, movement over time,
 *  animation or tweening between updates, dead reckoning, route planning,
 *  path optimization, or any Task 2 computation.
 *
 *  Insufficient geometry is NOT a licence to guess. Every failure path
 *  returns a typed reason and the vehicle renders POSITION UNAVAILABLE. It is
 *  never placed at an endpoint "near enough", never at the segment midpoint,
 *  and never at a previous position.
 * ==========================================================================
 */
export function resolvePosition(
  vehicle: VehicleState,
  topology: MineTopology | null,
): PositionResolution {
  const { x, y, segmentId, offsetM } = vehicle.position;

  // 1. Supplied coordinates always win. Nothing is derived when nothing needs to be.
  if (x !== null && y !== null && Number.isFinite(x) && Number.isFinite(y)) {
    return { ok: true, x, y, source: "SUPPLIED" };
  }

  if (topology === null) return { ok: false, reason: "NO_TOPOLOGY" };
  if (segmentId === null) return { ok: false, reason: "NO_SEGMENT_ID" };

  const segment = topology.segments.find((s) => s.segmentId === segmentId);
  if (!segment) return { ok: false, reason: "UNKNOWN_SEGMENT" };

  if (offsetM === null || !Number.isFinite(offsetM)) {
    return { ok: false, reason: "NO_OFFSET" };
  }

  const from = topology.nodes.find((n) => n.nodeId === segment.fromNode);
  const to = topology.nodes.find((n) => n.nodeId === segment.toNode);
  if (!from || !to) return { ok: false, reason: "SEGMENT_ENDPOINT_MISSING" };
  if (!Number.isFinite(from.x) || !Number.isFinite(from.y)) {
    return { ok: false, reason: "SEGMENT_ENDPOINT_MISSING" };
  }
  if (!Number.isFinite(to.x) || !Number.isFinite(to.y)) {
    return { ok: false, reason: "SEGMENT_ENDPOINT_MISSING" };
  }

  if (!Number.isFinite(segment.lengthM) || segment.lengthM <= 0) {
    return { ok: false, reason: "SEGMENT_LENGTH_MISSING" };
  }

  // Supplied fraction along a supplied straight line between two supplied endpoints.
  // Clamped to the segment because a marker outside its own segment would misinform;
  // clamping bounds the DISPLAY and alters no supplied value.
  const fraction = Math.min(Math.max(offsetM / segment.lengthM, 0), 1);

  return {
    ok: true,
    x: from.x + (to.x - from.x) * fraction,
    y: from.y + (to.y - from.y) * fraction,
    source: "SEGMENT_GEOMETRY",
  };
}

/**
 * Split the fleet into vehicles with supplied coordinates and vehicles without.
 *
 * A vehicle is drawn at the coordinates the data layer supplied, or it is not drawn at
 * all. There is deliberately NO fallback path: no interpolation along a segment from
 * `offsetM`, no dead reckoning from speed and elapsed time, no reuse of a previous point,
 * no placement at a node "near enough". A guessed truck on an operator's map is worse
 * than an absent one, because the operator cannot tell it is guessed.
 */
export function placeVehicles(
  vehicles: Record<string, VehicleState>,
  topology: MineTopology | null,
): VehiclePlacement {
  const placed: PlacedVehicle[] = [];
  const unplaced: UnplacedVehicle[] = [];

  for (const vehicle of Object.values(vehicles)) {
    const resolved = resolvePosition(vehicle, topology);
    if (resolved.ok) {
      placed.push({ vehicle, x: resolved.x, y: resolved.y, source: resolved.source });
    } else {
      unplaced.push({ vehicle, reason: resolved.reason });
    }
  }

  placed.sort((a, b) => a.vehicle.vehicleId.localeCompare(b.vehicle.vehicleId));
  unplaced.sort((a, b) => a.vehicle.vehicleId.localeCompare(b.vehicle.vehicleId));
  return { placed, unplaced };
}

// ---------------------------------------------------------------------------
// Visibility — supplied readings only
// ---------------------------------------------------------------------------

export interface VisibilityView {
  segmentId: string;
  visibilityM: number | null;
  sigma: number | null;
  timestamp: string;
}

/**
 * The lowest supplied visibility reading across segments — the worst current condition.
 *
 * A selection among supplied values, not an aggregate: no averaging, no smoothing, no
 * modelling of fog. Segments with no supplied visibility are skipped rather than
 * defaulted.
 */
export function worstVisibility(road: Record<string, RoadState>): VisibilityView | null {
  let worst: VisibilityView | null = null;

  for (const segment of Object.values(road)) {
    const value = segment.visibility.value;
    if (value === null) continue;
    if (worst === null || value < (worst.visibilityM ?? Number.POSITIVE_INFINITY)) {
      worst = {
        segmentId: segment.segmentId,
        visibilityM: value,
        sigma: segment.visibility.sigma,
        timestamp: segment.timestamp,
      };
    }
  }

  return worst;
}

// ---------------------------------------------------------------------------
// Fleet summary — counts of supplied records
// ---------------------------------------------------------------------------

export interface FleetSummary {
  total: number;
  withPosition: number;
  withoutPosition: number;
  /** Count of vehicles whose SUPPLIED actual speed exceeds their SUPPLIED safe speed. */
  overSafeSpeed: number;
  /** Count of vehicles for which no safe speed was supplied. */
  safeSpeedUnavailable: number;
}

export function fleetSummary(state: AppState): FleetSummary {
  const { placed, unplaced } = placeVehicles(state.vehicles, state.topology);
  let overSafeSpeed = 0;
  let safeSpeedUnavailable = 0;

  for (const vehicleId of Object.keys(state.vehicles)) {
    const view = speedView(state.safety[vehicleId]);
    if (!view) continue;
    if (view.violation) overSafeSpeed += 1;
    if (view.safeSpeedUnavailable) safeSpeedUnavailable += 1;
  }

  return {
    total: Object.keys(state.vehicles).length,
    withPosition: placed.length,
    withoutPosition: unplaced.length,
    overSafeSpeed,
    safeSpeedUnavailable,
  };
}

// ---------------------------------------------------------------------------
// Dispatch and slots — M7. FR-009, FR-010. M7D-A, M7D-B.
//
// Ordering, grouping, lane packing and time-axis positioning ONLY. Nothing here
// selects an assignment, optimizes dispatch, computes an ETA, calculates or
// optimizes a route, generates or resolves a slot, or runs any solver. Every
// value that reaches the screen was supplied.
// ---------------------------------------------------------------------------

/** Rendered when a supplied reason code is absent or empty. NFR-006, FR-010 AC1. */
export const REASON_CODE_MISSING_TEXT = "REASON CODE MISSING (DATA DEFECT)";

/**
 * True when the supplied reason code is unusable.
 *
 * The contract calls an empty string "a data defect, not a valid value", so the HMI says
 * so rather than rendering a blank cell that reads as "nothing to report".
 */
export function isReasonCodeMissing(reasonCode: string | null | undefined): boolean {
  return reasonCode === null || reasonCode === undefined || reasonCode.trim() === "";
}

/**
 * Dispatch commands in a deterministic display order: newest supplied timestamp first,
 * then by command id so equal timestamps never reorder between renders.
 *
 * A display sort over supplied values. It expresses no preference between commands and
 * never selects one — FR-010 AC4.
 */
export function rankDispatch(dispatch: Record<string, DispatchCommand>): DispatchCommand[] {
  return Object.values(dispatch)
    .slice()
    .sort((a, b) => {
      const byTime = b.timestamp.localeCompare(a.timestamp);
      if (byTime !== 0) return byTime;
      return a.commandId.localeCompare(b.commandId);
    });
}

/** Why a resource's slot bands cannot be positioned. Each names a specific missing input. */
export type TimeAxisUnavailableReason = "NO_SLOTS" | "UNPARSEABLE_TIME" | "ZERO_WINDOW";

export const TIME_AXIS_UNAVAILABLE_REASON_TEXT: Readonly<
  Record<TimeAxisUnavailableReason, string>
> = {
  NO_SLOTS: "no slots supplied for this resource",
  UNPARSEABLE_TIME: "a supplied slot time could not be read",
  ZERO_WINDOW: "supplied slot times span no duration",
};

export interface TimeAxis {
  startMs: number;
  endMs: number;
  /** Evenly spaced epoch-ms marks for the axis labels. */
  ticks: number[];
}

export type TimeAxisResolution =
  | { ok: true; axis: TimeAxis }
  | { ok: false; reason: TimeAxisUnavailableReason };

export const TIME_AXIS_TICKS = 5;

/**
 * The window a resource's slot bands are drawn against — FR-009 AC1, "slots positioned on
 * a real time axis".
 *
 * Bounds come from the supplied `startTime` and `endTime` values themselves. No window is
 * assumed, padded to a round number, or extended to "now": every edge traces to a
 * supplied timestamp. Unusable input yields a typed reason, never a guessed window.
 */
export function slotTimeAxis(slots: readonly SlotState[]): TimeAxisResolution {
  if (slots.length === 0) return { ok: false, reason: "NO_SLOTS" };

  let startMs = Number.POSITIVE_INFINITY;
  let endMs = Number.NEGATIVE_INFINITY;

  for (const slot of slots) {
    const from = Date.parse(slot.startTime);
    const to = Date.parse(slot.endTime);
    if (!Number.isFinite(from) || !Number.isFinite(to)) {
      return { ok: false, reason: "UNPARSEABLE_TIME" };
    }
    startMs = Math.min(startMs, from, to);
    endMs = Math.max(endMs, from, to);
  }

  if (endMs <= startMs) return { ok: false, reason: "ZERO_WINDOW" };

  const ticks: number[] = [];
  for (let i = 0; i < TIME_AXIS_TICKS; i += 1) {
    ticks.push(startMs + ((endMs - startMs) * i) / (TIME_AXIS_TICKS - 1));
  }

  return { ok: true, axis: { startMs, endMs, ticks } };
}

export interface SlotBand {
  slot: SlotState;
  /** 0..1 across the axis window. Layout, not an operational value. */
  left: number;
  width: number;
  /** Which stacked row this band occupies, so overlaps stay readable (FR-009 AC4). */
  lane: number;
}

export interface ResourceSlots {
  resourceId: string;
  slots: SlotState[];
  axis: TimeAxisResolution;
  bands: SlotBand[];
  laneCount: number;
  /** True when any supplied slot on this resource reports CONFLICT or names a conflict. */
  hasConflict: boolean;
}

/**
 * Lay a resource's supplied slots into stacked lanes.
 *
 * Greedy first-fit over slots ordered by supplied start time: a slot joins the first lane
 * whose previous band has already ended, otherwise it opens a new lane. This is pure
 * layout — it decides where a band is DRAWN, never which vehicle holds a slot, when a
 * slot occurs, or whether a slot may proceed. FR-009 AC5's "no slot solver" is untouched:
 * nothing here reorders, merges, moves or resolves a slot.
 */
function packLanes(
  slots: readonly SlotState[],
  axis: TimeAxis,
): {
  bands: SlotBand[];
  laneCount: number;
} {
  const span = axis.endMs - axis.startMs;
  const ordered = slots
    .slice()
    .sort(
      (a, b) =>
        Date.parse(a.startTime) - Date.parse(b.startTime) || a.slotId.localeCompare(b.slotId),
    );

  const laneEnds: number[] = [];
  const bands: SlotBand[] = [];

  for (const slot of ordered) {
    const from = Date.parse(slot.startTime);
    const to = Date.parse(slot.endTime);

    let lane = laneEnds.findIndex((end) => end <= from);
    if (lane === -1) {
      lane = laneEnds.length;
      laneEnds.push(to);
    } else {
      laneEnds[lane] = to;
    }

    bands.push({
      slot,
      left: (from - axis.startMs) / span,
      width: Math.max((to - from) / span, 0),
      lane,
    });
  }

  return { bands, laneCount: Math.max(laneEnds.length, 1) };
}

/**
 * Group supplied slots by their supplied `resourceId`, ordered for stable display.
 *
 * Grouping reads `resourceId` as supplied. No slot is assigned to a resource, moved
 * between resources, or created.
 */
export function groupSlotsByResource(slots: Record<string, SlotState>): ResourceSlots[] {
  const byResource = new Map<string, SlotState[]>();

  for (const slot of Object.values(slots)) {
    const existing = byResource.get(slot.resourceId);
    if (existing) existing.push(slot);
    else byResource.set(slot.resourceId, [slot]);
  }

  const groups: ResourceSlots[] = [];

  for (const [resourceId, resourceSlots] of byResource) {
    const ordered = resourceSlots
      .slice()
      .sort(
        (a, b) =>
          (Date.parse(a.startTime) || 0) - (Date.parse(b.startTime) || 0) ||
          a.slotId.localeCompare(b.slotId),
      );

    const axis = slotTimeAxis(ordered);
    const packed = axis.ok ? packLanes(ordered, axis.axis) : { bands: [], laneCount: 1 };

    groups.push({
      resourceId,
      slots: ordered,
      axis,
      bands: packed.bands,
      laneCount: packed.laneCount,
      hasConflict: ordered.some(
        (s) => s.status === "CONFLICT" || (s.conflictWith !== null && s.conflictWith.length > 0),
      ),
    });
  }

  groups.sort((a, b) => a.resourceId.localeCompare(b.resourceId));
  return groups;
}

/**
 * Every supplied slot reporting a conflict, ordered deterministically.
 *
 * A filter over supplied `status` and supplied `conflictWith`. The HMI runs no conflict
 * detection: if Task 2 reports no conflict, the HMI reports no conflict.
 */
export function conflictingSlots(slots: Record<string, SlotState>): SlotState[] {
  return Object.values(slots)
    .filter(
      (s) => s.status === "CONFLICT" || (s.conflictWith !== null && s.conflictWith.length > 0),
    )
    .sort((a, b) => a.slotId.localeCompare(b.slotId));
}

// ---------------------------------------------------------------------------
// Connection presentation
// ---------------------------------------------------------------------------

/** True when the pipe is up. Says nothing about whether any datum is current. */
export function isLinkUp(state: AppState): boolean {
  return state.connection.status === "CONNECTED";
}
