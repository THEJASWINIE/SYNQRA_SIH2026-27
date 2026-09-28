/**
 * S6 Digital Twin — presentation derivation. Phase 7.
 *
 * ==========================================================================
 *  NO COORDINATE IS INVENTED HERE.
 *
 *  This module reports what the Twin actually contains. It does not synthesize
 *  topology, does not place a vehicle, does not estimate a heading and does not
 *  turn an abstract graph into a geographic map. Placement stays where it already
 *  lives - `derive.placeVehicles` / `derive.resolvePosition` (M4D-F) - and is reused,
 *  not reimplemented.
 * ==========================================================================
 *
 * AUDITED AVAILABILITY (Phase 7, measured against the running backend):
 *
 *   LIVE       topology UNAVAILABLE (`mine: {nodes:{}, adjacency:{}}`; the backend emits
 *              no MineTopology frame at all), position UNAVAILABLE, road_id UNAVAILABLE,
 *              heading UNAVAILABLE, environment UNAVAILABLE.
 *              Vehicle telemetry IS available: speed, rpm, communication state,
 *              sequence, with per-field provenance and freshness.
 *   MOCK       topology SUPPLIED by all 11 scenario files; environment and positions
 *              supplied by the scenario.
 *   REPLAY     whatever the recording captured, carried verbatim.
 *
 * Nothing below branches on the provider. It reports the slices, so LIVE gaining a
 * topology source later needs no change here.
 *
 * HEADING IS A SEPARATE CASE. It is not merely absent from the live feed - `VehicleState`
 * carries no heading field, so no provider can supply one. It is reported as unavailable
 * with that reason stated, rather than implied to be a temporary gap.
 *
 * Pure and framework-free, so it is testable without a DOM (M4D-C).
 */

import type { AppState, ObservabilityState } from "../contracts/appState";
import type { MineTopology, VehicleState } from "../contracts/domain";
import {
  DATA_STATE_TEXT,
  fieldDataState,
  provenanceLabel,
  vehicleProvenanceLabel,
} from "./dataStatus";
import { POSITION_UNAVAILABLE_REASON_TEXT, placeVehicles } from "./derive";
import { type Readout, UNAVAILABLE } from "./safetyEnvironment";
import { formatCounter, type HealthLine } from "./systemHealth";

/** Heading has no field in the contract, so no provider can ever supply it. */
export const HEADING_ABSENT_TEXT =
  "not carried by the HMI vehicle contract — no provider supplies it";

// ---------------------------------------------------------------------------
// Twin data status
// ---------------------------------------------------------------------------

/**
 * Topology availability.
 *
 * "Twin attached but topology empty" is a DIFFERENT state from "no Twin", and both are
 * different from "topology drawn". Collapsing them into a generic "no data" would hide
 * that the Twin is running and simply models no roads.
 */
export function topologyLine(topology: MineTopology | null): HealthLine {
  if (topology === null) {
    return {
      label: "Topology",
      state: "UNAVAILABLE",
      value: "NOT SUPPLIED",
      detail: "No provider has sent a mine topology. None is synthesized.",
    };
  }
  const nodes = topology.nodes.length;
  const segments = topology.segments.length;
  if (nodes === 0 && segments === 0) {
    return {
      label: "Topology",
      state: "OFF",
      value: "SUPPLIED BUT EMPTY",
      detail: "A topology arrived carrying no nodes and no roads. Nothing is drawn.",
    };
  }
  return {
    label: "Topology",
    state: "OK",
    value: "AVAILABLE",
    detail: `${nodes} node(s), ${segments} road(s) · version ${topology.version}`,
  };
}

/** Environment availability, from the supplied RoadState slice. */
export function environmentLine(road: AppState["road"]): HealthLine {
  const count = Object.keys(road).length;
  if (count === 0) {
    return {
      label: "Environment",
      state: "UNAVAILABLE",
      value: UNAVAILABLE,
      detail: "No RoadState supplied. Visibility, friction and surface are not shown.",
    };
  }
  return {
    label: "Environment",
    state: "OK",
    value: "AVAILABLE",
    detail: `${count} road segment(s) carry supplied environment`,
  };
}

/**
 * Vehicle-position availability across the fleet.
 *
 * Delegates entirely to the existing placement rules. A vehicle counts as positioned only
 * when `resolvePosition` succeeded on supplied inputs.
 */
export function positionLine(state: AppState): HealthLine {
  const total = Object.keys(state.vehicles).length;
  if (total === 0) {
    return { label: "Vehicle position", state: "UNAVAILABLE", value: "NO VEHICLES SUPPLIED" };
  }
  const { placed, unplaced } = placeVehicles(state.vehicles, state.topology);
  if (placed.length === 0) {
    const reasons = [...new Set(unplaced.map((u) => POSITION_UNAVAILABLE_REASON_TEXT[u.reason]))];
    return {
      label: "Vehicle position",
      state: "UNAVAILABLE",
      value: "UNAVAILABLE",
      detail: `${total} vehicle(s), none positioned — ${reasons.join("; ")}. No position is guessed.`,
    };
  }
  return {
    label: "Vehicle position",
    state: unplaced.length === 0 ? "OK" : "DEGRADED",
    value: `${placed.length} OF ${total} POSITIONED`,
    detail:
      unplaced.length === 0
        ? "every supplied vehicle carries sufficient supplied geometry"
        : `${unplaced.length} listed as position unavailable rather than placed`,
  };
}

/** Vehicle telemetry freshness is a different fact from Twin attachment. Kept separate. */
export function telemetryContextLine(vehicle: VehicleState | undefined): HealthLine {
  const field = vehicle?.provenance?.speed_mps;
  if (!field) {
    return { label: "Vehicle telemetry", state: "UNAVAILABLE", value: UNAVAILABLE };
  }
  /**
   * PHASE 8 — the freshness verdict and the provenance both come from the shared
   * vocabulary. This line previously restated provenance as "DERIVED · HARDWARE", a
   * fourth wording for a fact S3 was already calling "PHYSICAL (derived)".
   */
  const dataState = fieldDataState(field);
  return {
    label: "Vehicle telemetry",
    state:
      dataState === "CURRENT" ? "OK" : dataState === "UNAVAILABLE" ? "UNAVAILABLE" : "DEGRADED",
    value: DATA_STATE_TEXT[dataState],
    detail: `${provenanceLabel(field)} · quality ${field.quality}`,
  };
}

/**
 * Twin data status block.
 *
 * `twinLine` from S7 is deliberately NOT duplicated — the caller passes it in, so
 * attachment is stated once in the codebase.
 */
export function twinDataStatus(state: AppState, vehicle: VehicleState | undefined): HealthLine[] {
  return [
    topologyLine(state.topology),
    environmentLine(state.road),
    positionLine(state),
    telemetryContextLine(vehicle),
  ];
}

/** Vehicle count held in the Twin, per the backend's own counter. Never inferred. */
export function twinVehicleCountText(observability: ObservabilityState): string {
  return formatCounter(observability.data?.twinVehicleCount);
}

// ---------------------------------------------------------------------------
// Selected-vehicle context
// ---------------------------------------------------------------------------

function unavailable(label: string, provenance?: string): Readout {
  return { label, value: UNAVAILABLE, available: false, provenance };
}

/**
 * Context rows for the selected vehicle.
 *
 * Position, road and heading are UNAVAILABLE unless genuinely supplied. None is inferred
 * from the selection, the speed, the node order or anything else.
 */
export function vehicleContextRows(
  vehicle: VehicleState | undefined,
  topology: MineTopology | null,
): Readout[] {
  if (!vehicle) {
    return [
      unavailable("Speed"),
      unavailable("Position"),
      unavailable("Road segment"),
      unavailable("Heading", HEADING_ABSENT_TEXT),
      unavailable("Communication"),
    ];
  }

  const rows: Readout[] = [];

  rows.push(
    typeof vehicle.speedMps === "number" && Number.isFinite(vehicle.speedMps)
      ? {
          label: "Speed",
          value: (vehicle.speedMps * 3.6).toFixed(1),
          unit: "km/h",
          available: true,
          provenance: vehicleProvenanceLabel(vehicle),
        }
      : unavailable("Speed"),
  );

  // Position: only a coordinate the placement rules produced from supplied inputs.
  const placement = placeVehicles({ [vehicle.vehicleId]: vehicle }, topology);
  const here = placement.placed[0];
  rows.push(
    here
      ? {
          label: "Position",
          value: `x ${here.x.toFixed(1)}, y ${here.y.toFixed(1)}`,
          available: true,
          provenance:
            here.source === "SUPPLIED"
              ? "supplied coordinates (topology units, not geographic)"
              : "derived from supplied segment geometry (topology units, not geographic)",
        }
      : unavailable(
          "Position",
          placement.unplaced[0]
            ? POSITION_UNAVAILABLE_REASON_TEXT[placement.unplaced[0].reason]
            : undefined,
        ),
  );

  const segmentId = vehicle.position?.segmentId ?? null;
  rows.push(
    segmentId
      ? { label: "Road segment", value: segmentId, available: true }
      : unavailable("Road segment", "no segment id supplied"),
  );

  // Heading is structurally absent, not merely missing this run.
  rows.push(unavailable("Heading", HEADING_ABSENT_TEXT));

  const comm = vehicle.provenance?.communication_state?.value;
  rows.push(
    comm === undefined || comm === null
      ? unavailable("Communication")
      : { label: "Communication", value: String(comm), available: true },
  );

  return rows;
}

// ---------------------------------------------------------------------------
// Topology tables and legend
// ---------------------------------------------------------------------------

export interface LegendEntry {
  glyph: string;
  label: string;
}

const NODE_KIND_GLYPH: Record<string, string> = {
  SHOVEL: "▣",
  CRUSHER: "▣",
  INTERSECTION: "●",
  SWITCHBACK: "●",
  WAYPOINT: "●",
};

/**
 * Legend entries for the entity kinds the supplied topology ACTUALLY contains.
 *
 * A symbol for an entity kind nobody sent would imply the mine models something it does
 * not, so kinds absent from the data are absent from the legend.
 */
export function legendEntries(topology: MineTopology | null): LegendEntry[] {
  if (!topology) return [];
  const entries: LegendEntry[] = [];
  const kinds = [...new Set(topology.nodes.map((n) => n.kind))].sort();
  for (const kind of kinds) {
    entries.push({ glyph: NODE_KIND_GLYPH[kind] ?? "●", label: kind });
  }
  if (topology.segments.length > 0) entries.push({ glyph: "━━", label: "ROAD" });
  return entries;
}

export interface SegmentRow {
  segmentId: string;
  fromNode: string;
  toNode: string;
  lengthText: string;
  gradeText: string;
  direction: string;
}

/** Roads as a table, so every supplied road id is legible without reading the SVG. */
export function segmentRows(topology: MineTopology | null): SegmentRow[] {
  if (!topology) return [];
  return [...topology.segments]
    .sort((a, b) => a.segmentId.localeCompare(b.segmentId))
    .map((s) => ({
      segmentId: s.segmentId,
      fromNode: s.fromNode,
      toNode: s.toNode,
      lengthText: Number.isFinite(s.lengthM) ? `${s.lengthM.toFixed(0)} m` : UNAVAILABLE,
      gradeText: Number.isFinite(s.gradeRad) ? `${s.gradeRad.toFixed(3)} rad` : UNAVAILABLE,
      direction: s.bidirectional ? "bidirectional" : "one-way",
    }));
}

export interface NodeRow {
  nodeId: string;
  kind: string;
  label: string;
  coordText: string;
}

/** Nodes as a table. Coordinates are labelled as topology units, never as a fix. */
export function nodeRows(topology: MineTopology | null): NodeRow[] {
  if (!topology) return [];
  return [...topology.nodes]
    .sort((a, b) => a.nodeId.localeCompare(b.nodeId))
    .map((n) => ({
      nodeId: n.nodeId,
      kind: n.kind,
      label: n.label,
      coordText: `${n.x.toFixed(0)}, ${n.y.toFixed(0)}`,
    }));
}
