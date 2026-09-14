/**
 * Synthetic operational corridors — the demonstration haul-road network.
 *
 * ==========================================================================
 *  SYNTHETIC OPERATIONAL CORRIDORS · NOT NMDC INFRASTRUCTURE
 *
 *  No surveyed Deposit-5 haul-road geometry exists in this repository, and none has been
 *  reverse-engineered from guesses about how the real mine is laid out. These corridors
 *  exist so the spatial view has an operational road network to hang later passes on -
 *  route visualisation, corridor state - and for no other reason.
 *
 *  Every corridor therefore carries:
 *
 *    source          SYNTHETIC_FOR_DEMO
 *    verified        false
 *    confidence      LOW
 *    classification  OPERATIONAL_CORRIDOR
 *
 *  and is never labelled as an NMDC road, an official road, a surveyed road, a real haul
 *  road, or Deposit-5 road geometry. That is asserted by tests, not merely intended.
 * ==========================================================================
 *
 * ONE TERRAIN, ONE VERTICAL CONVENTION
 *
 * Corridor elevations are sampled from `elevationAt` - the same function that builds the
 * terrain - so a road sits on the landform it crosses and a ramp steps down the pit
 * bench by bench. There is no second elevation model. Elevations are TRUE metres about the
 * local synthetic datum; the renderer applies the same draw-time vertical exaggeration it
 * applies to the terrain, and the ribbon builder below takes that multiplier as an
 * argument rather than assuming it.
 *
 * DETERMINISTIC
 *
 * Every coordinate is a closed-form function of the terrain config. No `Math.random`.
 * The same config yields byte-identical corridors on every run and every machine.
 *
 * Pure and framework-free - no Three.js, no React - so the geometry is testable in the
 * Node test environment (M4D-C). The ribbon vertices are computed here too, so the
 * renderer is a thin bridge and the maths that could go wrong is under test.
 */

import type { MineCastProvenance } from "./minecastProjection";
import { mineZones, nearestOutlinePoint, zoneOfKind } from "./mineZones";
import { pointAt, rampCentreline } from "./pitMorphology";
import { elevationAt, type TerrainConfig } from "./terrainField";

// ---------------------------------------------------------------------------
// vocabulary and provenance
// ---------------------------------------------------------------------------

/** The only classification a synthetic corridor may have. */
export type CorridorClassification = "OPERATIONAL_CORRIDOR";

/**
 * What kind of corridor this is, for width, styling and route logic.
 *
 *   MAIN_HAUL      the dominant haul road: site entry, up the west side, around the rim
 *   RAMP           the switchback pit ramp, cut through the benches
 *   LOADING_LOOP   the small loop on the pit floor around the active working area
 *   DISPATCH       the road from the rim to the ore stockpile / dispatch point
 *   SERVICE        the narrow service road to the waste dump
 */
export type CorridorKind = "MAIN_HAUL" | "RAMP" | "LOADING_LOOP" | "DISPATCH" | "SERVICE";

/** The concise on-screen disclosure. Shown wherever corridors are shown. */
export const CORRIDOR_DISCLOSURE = "SYNTHETIC OPERATIONAL CORRIDORS · NOT NMDC INFRASTRUCTURE";

/** MINE-ROUTES-02: the route-level classification every corridor and every route carries. */
export const ROUTE_CLASSIFICATION = "SYNTHETIC_DIGITAL_TWIN_ROUTE" as const;

export const CORRIDOR_PROVENANCE = {
  source: "SYNTHETIC_FOR_DEMO" as MineCastProvenance,
  verified: false as const,
  confidence: "LOW" as const,
  classification: "OPERATIONAL_CORRIDOR" as CorridorClassification,
  routeClassification: ROUTE_CLASSIFICATION,
  disclosure: CORRIDOR_DISCLOSURE,
  detail:
    "Invented haul road, pit ramp, loading loop, dispatch and service corridors for demonstration. " +
    "No surveyed Deposit-5 road geometry exists in this repository and none was inferred from " +
    "assumptions about the real mine. Elevations are draped on the synthetic terrain and are not " +
    "real mine elevations.",
};

// ---------------------------------------------------------------------------
// the contract
// ---------------------------------------------------------------------------

/** One point on a corridor centreline. Scene metres, TRUE (un-exaggerated) elevation. */
export interface CorridorPoint {
  readonly x: number;
  readonly y: number;
  readonly elevationM: number;
}

export interface HaulCorridor {
  /** Stable id, e.g. `SYNTH-HAUL-MAIN`, `SYNTH-PIT-RAMP-01`. */
  readonly id: string;
  readonly kind: CorridorKind;
  readonly classification: CorridorClassification;
  readonly routeClassification: typeof ROUTE_CLASSIFICATION;
  readonly source: MineCastProvenance;
  readonly verified: false;
  readonly confidence: "LOW";
  /** Human label. Always says "synthetic". */
  readonly label: string;
  /** Short engineering label for the plan and the scene, e.g. `MAIN HAUL`. */
  readonly planLabel: string;
  /** Corridor width in metres. Invented; not a real road width. */
  readonly widthM: number;
  /** Ordered centreline, at least two points. */
  readonly centreline: readonly CorridorPoint[];
  /**
   * Named indices into the centreline where another corridor joins. Routes are composed
   * from these, so a junction is a SHARED point rather than two nearly-equal ones.
   */
  readonly junctions: Readonly<Record<string, number>>;
  /** Elevation at the first and last centreline point, for a quick sense of climb. */
  readonly startElevationM: number;
  readonly endElevationM: number;
}

// ---------------------------------------------------------------------------
// geometry helpers (pure)
// ---------------------------------------------------------------------------

type XY = readonly [number, number];

/** A point draped on the synthetic terrain at (x, y). */
function draped(x: number, y: number, config: TerrainConfig): CorridorPoint {
  return { x, y, elevationM: elevationAt(x, y, config) };
}

/**
 * Uniform Catmull-Rom spline through every control point, `steps` samples per span.
 * Passing THROUGH the controls is the point: a junction is a control, so the road really
 * does go through it. Ends are clamped by repeating the end controls.
 */
function catmullRom(controls: readonly XY[], steps: number): XY[] {
  if (controls.length < 2) throw new Error("a spline needs at least two controls");
  const pts: XY[] = [controls[0] as XY, ...controls, controls[controls.length - 1] as XY];
  const out: XY[] = [];
  for (let i = 1; i < pts.length - 2; i += 1) {
    const p0 = pts[i - 1] as XY;
    const p1 = pts[i] as XY;
    const p2 = pts[i + 1] as XY;
    const p3 = pts[i + 2] as XY;
    for (let k = i === 1 ? 0 : 1; k <= steps; k += 1) {
      const t = k / steps;
      const t2 = t * t;
      const t3 = t2 * t;
      const x =
        0.5 *
        (2 * p1[0] +
          (-p0[0] + p2[0]) * t +
          (2 * p0[0] - 5 * p1[0] + 4 * p2[0] - p3[0]) * t2 +
          (-p0[0] + 3 * p1[0] - 3 * p2[0] + p3[0]) * t3);
      const y =
        0.5 *
        (2 * p1[1] +
          (-p0[1] + p2[1]) * t +
          (2 * p0[1] - 5 * p1[1] + 4 * p2[1] - p3[1]) * t2 +
          (-p0[1] + 3 * p1[1] - 3 * p2[1] + p3[1]) * t3);
      out.push([x, y]);
    }
  }
  return out;
}

function corridor(
  id: string,
  kind: CorridorKind,
  label: string,
  planLabel: string,
  widthM: number,
  centreline: readonly CorridorPoint[],
  junctions: Readonly<Record<string, number>> = {},
): HaulCorridor {
  const first = centreline[0];
  const last = centreline[centreline.length - 1];
  if (!first || !last) throw new Error(`corridor ${id} needs at least two points`);
  return {
    id,
    kind,
    classification: CORRIDOR_PROVENANCE.classification,
    routeClassification: ROUTE_CLASSIFICATION,
    source: CORRIDOR_PROVENANCE.source,
    verified: false,
    confidence: "LOW",
    label,
    planLabel,
    widthM,
    centreline,
    junctions,
    startElevationM: first.elevationM,
    endElevationM: last.elevationM,
  };
}

// ---------------------------------------------------------------------------
// the network
// ---------------------------------------------------------------------------

/** Corridor ids. Exported so routes and tests name them once. */
export const CORRIDOR_ID = {
  MAIN: "SYNTH-HAUL-MAIN",
  RAMP: "SYNTH-PIT-RAMP-01",
  LOOP: "SYNTH-LOADING-LOOP-01",
  DISPATCH: "SYNTH-ORE-DISPATCH-01",
  SERVICE: "SYNTH-SERVICE-01",
} as const;

/** Samples per spline span. Enough that a 30 m ribbon has no visible facets. */
const SPAN_STEPS = 10;

/**
 * MINE-ROUTES-02: the demonstration haul-road network, five corridors from one config.
 *
 *   SYNTH-HAUL-MAIN        site entry (south-west) -> north along the west side, past the
 *                          service junction -> the pit access, then the rim road around the
 *                          north side to the east. The junctions are named indices.
 *   SYNTH-PIT-RAMP-01      the morphology's own switchback, from the access to the floor
 *   SYNTH-LOADING-LOOP-01  from the ramp foot, a closed loop around the active working
 *                          area on the pit floor, back to the ramp foot
 *   SYNTH-ORE-DISPATCH-01  from the rim road's east end to the ore stockpile
 *   SYNTH-SERVICE-01       from the service junction on the approach to the waste dump
 *
 * Every point is a closed-form function of the config. Widths are round demonstration
 * numbers, not measurements.
 */
export function haulCorridors(config: TerrainConfig): readonly HaulCorridor[] {
  const W = config.widthM;
  const H = config.heightM;
  const pit = config.pit;
  const zones = mineZones(config);
  const stockpile = zoneOfKind(zones, "STOCKPILE");
  const dump = zoneOfKind(zones, "WASTE_DUMP");
  const active = zoneOfKind(zones, "ACTIVE_AREA");

  // -- ramp: the morphology's switchback, draped ------------------------------
  const rampLine = rampCentreline(pit).map((p) => draped(p.x, p.y, config));
  const access = rampLine[0] as CorridorPoint;
  const rampFoot = rampLine[rampLine.length - 1] as CorridorPoint;
  const ramp = corridor(
    CORRIDOR_ID.RAMP,
    "RAMP",
    "Pit switchback ramp (synthetic)",
    "PIT RAMP 01",
    pit.rampWidthM,
    rampLine,
    { ACCESS: 0, FOOT: rampLine.length - 1 },
  );

  // -- main haul: entry -> service junction -> access -> rim road --------------
  const polar = (theta: number, u: number): XY => {
    const p = pointAt(theta, u, pit);
    return [p.x, p.y];
  };
  const entry: XY = [W * 0.06, H * 0.05];
  const serviceJunction: XY = [W * 0.09, H * 0.25];
  const approachControls: readonly XY[] = [
    entry,
    serviceJunction,
    [W * 0.1, H * 0.45],
    [W * 0.13, H * 0.6],
    [access.x, access.y],
  ];
  const rimControls: readonly XY[] = [
    [access.x, access.y],
    polar(2.2, -0.11),
    polar(1.8, -0.12),
    polar(1.4, -0.11),
    polar(1.0, -0.12),
    polar(0.65, -0.11),
    polar(0.35, -0.11),
  ];
  const approach = catmullRom(approachControls, SPAN_STEPS);
  const rim = catmullRom(rimControls, SPAN_STEPS).slice(1);
  const mainLine = [...approach, ...rim].map(([x, y]) => draped(x, y, config));
  const accessIndex = approach.length - 1;
  const main = corridor(
    CORRIDOR_ID.MAIN,
    "MAIN_HAUL",
    "Main haul route (synthetic)",
    "MAIN HAUL",
    30,
    mainLine,
    { ENTRY: 0, SERVICE: SPAN_STEPS, ACCESS: accessIndex, RIM_END: mainLine.length - 1 },
  );

  // -- loading loop: ramp foot -> around the active area -> ramp foot ----------
  const ring = active.polygon.slice(0, -1);
  let nearest = 0;
  let nearestSq = Number.POSITIVE_INFINITY;
  ring.forEach((p, i) => {
    const sq = (p.x - rampFoot.x) ** 2 + (p.y - rampFoot.y) ** 2;
    if (sq < nearestSq) {
      nearestSq = sq;
      nearest = i;
    }
  });
  const loopXY: XY[] = [[rampFoot.x, rampFoot.y]];
  for (let k = 0; k <= ring.length; k += 1) {
    const p = ring[(nearest + k) % ring.length] as { x: number; y: number };
    loopXY.push([p.x, p.y]);
  }
  loopXY.push([rampFoot.x, rampFoot.y]);
  const loop = corridor(
    CORRIDOR_ID.LOOP,
    "LOADING_LOOP",
    "Loading loop around the active working area (synthetic)",
    "LOADING LOOP",
    20,
    loopXY.map(([x, y]) => draped(x, y, config)),
    { FOOT: 0 },
  );

  // -- ore dispatch: rim road east end -> stockpile ---------------------------
  // Roads end at a zone's EDGE: a truck tips at the toe of a stockpile or a dump, it
  // does not drive up the mound.
  const rimEnd = mainLine[mainLine.length - 1] as CorridorPoint;
  const stockToe = nearestOutlinePoint(stockpile, rimEnd.x, rimEnd.y);
  const dispatchLine = catmullRom(
    [
      [rimEnd.x, rimEnd.y],
      polar(0.45, -0.3),
      [stockToe.x, stockToe.y],
    ],
    SPAN_STEPS,
  ).map(([x, y]) => draped(x, y, config));
  const dispatch = corridor(
    CORRIDOR_ID.DISPATCH,
    "DISPATCH",
    "Ore dispatch road to the stockpile (synthetic)",
    "ORE DISPATCH",
    24,
    dispatchLine,
    { RIM: 0, STOCKPILE: dispatchLine.length - 1 },
  );

  // -- service road: approach junction -> waste dump ---------------------------
  const junction = mainLine[SPAN_STEPS] as CorridorPoint;
  const dumpToe = nearestOutlinePoint(dump, junction.x, junction.y);
  const serviceLine = catmullRom(
    [
      [junction.x, junction.y],
      [(junction.x + dumpToe.x) / 2, junction.y - (dumpToe.x - junction.x) * 0.12],
      [dumpToe.x, dumpToe.y],
    ],
    SPAN_STEPS,
  ).map(([x, y]) => draped(x, y, config));
  const service = corridor(
    CORRIDOR_ID.SERVICE,
    "SERVICE",
    "Service road to the waste dump (synthetic)",
    "SERVICE ROAD",
    14,
    serviceLine,
    { MAIN: 0, DUMP: serviceLine.length - 1 },
  );

  return [main, ramp, loop, dispatch, service];
}

// ---------------------------------------------------------------------------
// ribbon geometry (pure, for the renderer)
// ---------------------------------------------------------------------------

export interface CorridorRibbon {
  /** Flat xyz triples, two vertices per centreline point (left edge, right edge). */
  readonly positions: readonly number[];
  /** Triangle indices, two triangles per centreline segment. */
  readonly indices: readonly number[];
  /** Flat xyz triples for the left edge polyline, then the right. */
  readonly leftEdge: readonly number[];
  readonly rightEdge: readonly number[];
}

/**
 * Build a ribbon the width of the corridor along its centreline.
 *
 * Scene convention: x east, z north, y up. `verticalScale` is the SAME draw-time
 * exaggeration the terrain uses, passed in rather than assumed so the two cannot drift.
 * `liftM` raises the ribbon a little so it sits on the surface rather than fighting it.
 *
 * The perpendicular at each point is taken from the direction between its neighbours,
 * which is enough for a smooth centreline.
 */
/**
 * Elevation lookup used to drape a ribbon. The renderer passes the terrain MESH's own
 * bilinear interpolation (`gridElevationAt`) so the road sits on the surface that is
 * actually drawn; tests may pass the continuous field.
 */
export type ElevationSampler = (x: number, y: number) => number;

export function corridorRibbon(
  road: HaulCorridor,
  verticalScale: number,
  liftM: number,
  sampleElevation: ElevationSampler,
): CorridorRibbon {
  const points = road.centreline;
  const half = road.widthM / 2;
  const positions: number[] = [];
  const leftEdge: number[] = [];
  const rightEdge: number[] = [];

  for (let i = 0; i < points.length; i += 1) {
    const here = points[i] as CorridorPoint;
    const ahead = points[i + 1] ?? here;
    const behind = points[i - 1] ?? here;

    // Tangent from the neighbours; falls back to +x on a degenerate segment.
    let tx = ahead.x - behind.x;
    let ty = ahead.y - behind.y;
    const length = Math.sqrt(tx * tx + ty * ty);
    if (length > 0) {
      tx /= length;
      ty /= length;
    } else {
      tx = 1;
      ty = 0;
    }

    // Perpendicular in the ground plane.
    const nx = -ty;
    const ny = tx;

    const lx = here.x + nx * half;
    const lz = here.y + ny * half;
    const rx = here.x - nx * half;
    const rz = here.y - ny * half;

    // Each edge is draped separately, so the ribbon tilts with the cross-slope instead
    // of one edge sinking into a bench wall.
    const ly = sampleElevation(lx, lz) * verticalScale + liftM;
    const ry = sampleElevation(rx, rz) * verticalScale + liftM;

    positions.push(lx, ly, lz, rx, ry, rz);
    leftEdge.push(lx, ly, lz);
    rightEdge.push(rx, ry, rz);
  }

  const indices: number[] = [];
  for (let i = 0; i < points.length - 1; i += 1) {
    const l0 = i * 2;
    const r0 = l0 + 1;
    const l1 = l0 + 2;
    const r1 = l0 + 3;
    indices.push(l0, l1, r0, r0, l1, r1);
  }

  return { positions, indices, leftEdge, rightEdge };
}

/** Corridors of one kind. */
export function corridorsOfKind(
  corridors: readonly HaulCorridor[],
  kind: CorridorKind,
): readonly HaulCorridor[] {
  return corridors.filter((road) => road.kind === kind);
}
