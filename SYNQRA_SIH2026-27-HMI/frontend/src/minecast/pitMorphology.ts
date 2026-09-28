/**
 * Synthetic open-pit morphology — footprint, benches, floor and switchback ramp.
 *
 * ==========================================================================
 *  SYNTHETIC MINE GEOMETRY · NOT SURVEYED
 *
 *  This is an invented open-pit shape, chosen to READ as an open-cast excavation rather
 *  than a crater. It is not a reconstruction of Bailadila Deposit-5 and nothing about it
 *  was inferred from imagery, memory or assumptions about the real mine. Every feature
 *  derived from it carries source = SYNTHETIC_FOR_DEMO, verified = false, confidence = LOW.
 * ==========================================================================
 *
 * WHY THE CRATER LOOKED LIKE A CRATER
 *
 * The Pass 2 pit was radial: depth was a function of distance from one centre, so the rim
 * was a circle, every bench was a concentric ring, and the floor sat dead centre. Real
 * open pits are none of those things - they are elongated, one wall is steeper than
 * another, benches run out into working faces, and a ramp cuts through the benches on
 * its way down.
 *
 * THE WARPED-POLAR FRAME
 *
 * Everything here is expressed in (θ, u) about the pit centre:
 *
 *   θ  bearing from the centre
 *   u  "inwardness": 0 on the rim, 1 on the floor edge, negative outside the pit
 *
 * The rim radius rO(θ) and the floor radius rI(θ) are each a sum of a few fixed-phase
 * harmonics, so the rim is irregular and elongated, the floor is irregular AND offset
 * (its first harmonic pushes it to one side), and each bench - a curve of constant u -
 * is a different blend of the two. A ramp is simply a path in (θ, u) whose u climbs while
 * θ sweeps back and forth: a switchback that follows the pit wall.
 *
 * DETERMINISTIC. No `Math.random`. Every number below is a fixed constant or a closed-form
 * function of the terrain config.
 *
 * Pure and framework-free, so it is testable without a DOM or WebGL (M4D-C).
 */

import type { MineCastProvenance } from "./minecastProjection";

// ---------------------------------------------------------------------------
// provenance
// ---------------------------------------------------------------------------

export const MORPHOLOGY_DISCLOSURE = "SYNTHETIC MINE GEOMETRY · NOT SURVEYED";

export const MORPHOLOGY_PROVENANCE = {
  source: "SYNTHETIC_FOR_DEMO" as MineCastProvenance,
  verified: false as const,
  confidence: "LOW" as const,
  disclosure: MORPHOLOGY_DISCLOSURE,
  detail:
    "Invented open-pit morphology - irregular rim, offset floor, terraced benches and a switchback " +
    "ramp - chosen to read as an open-cast excavation for demonstration. It is not a reconstruction " +
    "of Deposit-5 and was not inferred from imagery or assumptions about the real mine.",
};

// ---------------------------------------------------------------------------
// configuration
// ---------------------------------------------------------------------------

export interface PitMorphology {
  /** Pit centre, scene metres. The rim is described about this point. */
  readonly centreX: number;
  readonly centreY: number;
  /** Base rim radius before the harmonics shape it, metres. */
  readonly baseRadiusM: number;
  /** Floor radius as a fraction of the base radius, before its own harmonics. */
  readonly floorRatio: number;
  /** Total depth rim to floor, metres. */
  readonly depthM: number;
  /** Number of benches between rim and floor. */
  readonly benchCount: number;
  /** Ramp corridor width, metres. */
  readonly rampWidthM: number;
  /** Bearing of the surface access, radians. */
  readonly accessBearingRad: number;
}

/**
 * The demonstration pit, sized to the site.
 *
 * The bearing and every harmonic below are hand-chosen constants. They are not derived
 * from any real geometry.
 */
export function pitMorphology(
  centreX: number,
  centreY: number,
  baseRadiusM: number,
  depthM: number,
): PitMorphology {
  return {
    centreX,
    centreY,
    baseRadiusM,
    floorRatio: 0.34,
    depthM,
    // Pass 3B-M2: five strong terraces rather than eight thin rings. Each shelf is then
    // wide enough (~130 m) and each face tall enough (52 m true, 130 m drawn) to read
    // as a working level from the overview camera.
    benchCount: 5,
    // Wide enough to draw as a road surface, not a line: two terrain cells across.
    rampWidthM: 40,
    accessBearingRad: 2.75,
  };
}

// ---------------------------------------------------------------------------
// footprints
// ---------------------------------------------------------------------------

/**
 * Rim radius at a bearing, as a multiple of the base radius.
 *
 * A first harmonic elongates the pit toward one side, a second stretches it along an
 * axis, and the odd third and fifth harmonics break rotational symmetry so no two
 * opposite walls match.
 */
export function rimShape(theta: number): number {
  return (
    1 +
    0.22 * Math.cos(theta - 0.35) +
    0.16 * Math.cos(2 * theta + 1.05) +
    0.1 * Math.cos(3 * theta - 2.2) +
    0.05 * Math.cos(5 * theta + 0.6)
  );
}

/**
 * Floor radius at a bearing, as a multiple of the floor's own base.
 *
 * The strong first harmonic, pointed in a DIFFERENT direction from the rim's, is what
 * pushes the floor off-centre: the deepest part of the pit sits under one wall, not in
 * the middle.
 */
export function floorShape(theta: number): number {
  return (
    1 +
    0.6 * Math.cos(theta - 2.6) +
    0.15 * Math.cos(2 * theta - 0.3) +
    0.08 * Math.cos(3 * theta + 1.4)
  );
}

/** Rim radius in metres at a bearing. */
export function rimRadiusAt(theta: number, pit: PitMorphology): number {
  return pit.baseRadiusM * rimShape(theta);
}

/**
 * Floor-edge radius in metres at a bearing.
 *
 * Clamped below the rim so the floor can never poke through a wall on the side where the
 * rim is narrowest and the floor widest.
 */
export function floorRadiusAt(theta: number, pit: PitMorphology): number {
  const wanted = pit.baseRadiusM * pit.floorRatio * floorShape(theta);
  const ceiling = rimRadiusAt(theta, pit) * 0.8;
  return wanted < ceiling ? wanted : ceiling;
}

/** Bearing and distance of a scene point from the pit centre. */
export function polarOf(
  x: number,
  y: number,
  pit: PitMorphology,
): { theta: number; distance: number } {
  const dx = x - pit.centreX;
  const dy = y - pit.centreY;
  return { theta: Math.atan2(dy, dx), distance: Math.sqrt(dx * dx + dy * dy) };
}

/**
 * Inwardness of a point: 0 on the rim, 1 on the floor edge, <0 outside, >1 on the floor.
 *
 * This is the single quantity every other feature is derived from, which is what keeps
 * the terrain, the bench lines and the ramp mutually consistent.
 */
export function inwardnessAt(x: number, y: number, pit: PitMorphology): number {
  const { theta, distance } = polarOf(x, y, pit);
  const rim = rimRadiusAt(theta, pit);
  const floor = floorRadiusAt(theta, pit);
  return (rim - distance) / (rim - floor);
}

/**
 * Bench-width warp: how much the bench steps are pushed inward or outward at a bearing.
 *
 * Applied to inwardness BEFORE it is quantised into levels, so on one side of the pit
 * the upper benches are wide and the lower ones narrow, and on another side the reverse.
 * This is what gives unequal bench lengths and working faces instead of a stack of
 * uniformly spaced rings. Zero at the rim and at the floor, so neither moves.
 */
export function benchWarp(theta: number): number {
  return 0.18 * Math.cos(3 * theta + 0.8) + 0.1 * Math.cos(theta - 1.9);
}

/** Warped inwardness: the value the bench levels are cut from. */
export function warpInwardness(theta: number, u: number): number {
  return u + benchWarp(theta) * u * (1 - u);
}

/**
 * Invert `warpInwardness` for a bearing: the geometric u at which the warped value
 * equals `warped`. Closed form of the quadratic c·u² − (1 + c)·u + warped = 0.
 */
export function unwarpInwardness(theta: number, warped: number): number {
  const c = benchWarp(theta);
  if (Math.abs(c) < 1e-9) return warped;
  const b = 1 + c;
  const disc = b * b - 4 * c * warped;
  const root = disc > 0 ? Math.sqrt(disc) : 0;
  return (b - root) / (2 * c);
}

/** Warped inwardness of a scene point - what `benchLevelAt` should be fed. */
export function benchInwardnessAt(x: number, y: number, pit: PitMorphology): number {
  const { theta } = polarOf(x, y, pit);
  const u = inwardnessAt(x, y, pit);
  if (u <= 0 || u >= 1) return u;
  return warpInwardness(theta, u);
}

/**
 * The crest contour for a warped inwardness value: at each bearing, the geometric u that
 * lands on that bench step. This is what makes a drawn crest sit on the terrain's own
 * step even though the steps are warped.
 */
export function crestContourAt(
  warped: number,
  pit: PitMorphology,
  segments = 144,
): readonly { readonly x: number; readonly y: number }[] {
  const points: { x: number; y: number }[] = [];
  for (let i = 0; i < segments; i += 1) {
    const theta = (i / segments) * Math.PI * 2;
    const u = warped <= 0 || warped >= 1 ? warped : unwarpInwardness(theta, warped);
    points.push(pointAt(theta, u, pit));
  }
  return points;
}

/** Scene point for a (θ, u) pair. Inverse of `inwardnessAt` along a bearing. */
export function pointAt(theta: number, u: number, pit: PitMorphology): { x: number; y: number } {
  const rim = rimRadiusAt(theta, pit);
  const floor = floorRadiusAt(theta, pit);
  const radius = rim - u * (rim - floor);
  return {
    x: pit.centreX + Math.cos(theta) * radius,
    y: pit.centreY + Math.sin(theta) * radius,
  };
}

/** The closed curve at constant inwardness, sampled at `segments` bearings. */
export function contourAt(
  u: number,
  pit: PitMorphology,
  segments = 144,
): readonly { readonly x: number; readonly y: number }[] {
  const points: { x: number; y: number }[] = [];
  for (let i = 0; i < segments; i += 1) {
    points.push(pointAt((i / segments) * Math.PI * 2, u, pit));
  }
  return points;
}

/** Centroid of a closed polygon given as points. */
export function centroidOf(points: readonly { readonly x: number; readonly y: number }[]): {
  x: number;
  y: number;
} {
  let sx = 0;
  let sy = 0;
  for (const point of points) {
    sx += point.x;
    sy += point.y;
  }
  return { x: sx / points.length, y: sy / points.length };
}

// ---------------------------------------------------------------------------
// benches
// ---------------------------------------------------------------------------

/**
 * Bench level for an inwardness value: 0 on the rim bench, `benchCount` on the floor.
 * Quantised, so the wall descends in steps. Anything outside the pit is level 0.
 */
export function benchLevelAt(u: number, pit: PitMorphology): number {
  if (u <= 0) return 0;
  if (u >= 1) return pit.benchCount;
  return Math.floor(u * pit.benchCount);
}

/** Depth below the rim for a bench level, metres. */
export function benchDepthM(level: number, pit: PitMorphology): number {
  return (level / pit.benchCount) * pit.depthM;
}

// ---------------------------------------------------------------------------
// the switchback ramp
// ---------------------------------------------------------------------------

/** One point on the ramp centreline. */
export interface RampPoint {
  readonly x: number;
  readonly y: number;
  /** Inwardness along the descent. Negative on the surface approach. */
  readonly u: number;
  /** Target depth below the rim, metres. 0 on the surface approach. */
  readonly depthM: number;
}

/**
 * A switchback leg: θ sweeps from `fromTheta` to `toTheta` while u climbs from `fromU`
 * to `toU`. Eased at both ends so the reversal at each switchback is a rounded turn
 * rather than a cusp.
 */
function leg(
  fromTheta: number,
  toTheta: number,
  fromU: number,
  toU: number,
  steps: number,
  pit: PitMorphology,
): RampPoint[] {
  const points: RampPoint[] = [];
  for (let i = 0; i <= steps; i += 1) {
    const t = i / steps;
    const eased = t * t * (3 - 2 * t);
    const theta = fromTheta + (toTheta - fromTheta) * eased;
    const u = fromU + (toU - fromU) * t;
    const { x, y } = pointAt(theta, u, pit);
    points.push({ x, y, u, depthM: u <= 0 ? 0 : u * pit.depthM });
  }
  return points;
}

/**
 * The ramp centreline: a surface approach, then three legs of a switchback that reverses
 * direction twice on its way to the floor.
 *
 * Because it is defined in (θ, u), each leg runs along the pit wall at a steadily
 * increasing depth, and the reversals put the turns where a real switchback would be -
 * at the end of a bench, not in the middle of the pit.
 *
 * DIGITAL-TWIN-OPERATIONAL-FLOW-01: each leg's u now starts exactly where the previous
 * leg's u ended (0 -> U1 -> U2 -> 1), so depth is continuous across every switchback
 * reversal. Previously leg 1 ended at u=0.36 while leg 2 started at u=0.4 (and the same
 * 0.04 gap recurred at the second reversal); theta was already continuous there, so only
 * u jumped, producing a real vertical step at the turn. U1 and U2 are the midpoints of
 * the old (end, start) pairs, so the switchback keeps its original shape and depth
 * schedule; only the discontinuity is removed.
 */
export function rampCentreline(pit: PitMorphology): readonly RampPoint[] {
  const entry = pit.accessBearingRad;
  const U1 = (0.36 + 0.4) / 2;
  const U2 = (0.72 + 0.76) / 2;
  const approach = leg(entry - 0.22, entry, -0.12, 0, 10, pit);
  const first = leg(entry, entry + 1.55, 0, U1, 40, pit);
  const second = leg(entry + 1.55, entry + 0.15, U1, U2, 40, pit);
  const third = leg(entry + 0.15, entry + 1.05, U2, 1.0, 30, pit);
  return [...approach, ...first.slice(1), ...second.slice(1), ...third.slice(1)];
}

/**
 * Nearest ramp centreline point to a scene position, with its distance.
 *
 * Linear scan; the centreline is ~120 points and this runs per terrain vertex once.
 */
export function nearestRampPoint(
  x: number,
  y: number,
  ramp: readonly RampPoint[],
): { point: RampPoint; distance: number } {
  let best = ramp[0] as RampPoint;
  let bestSq = Number.POSITIVE_INFINITY;
  for (const point of ramp) {
    const dx = point.x - x;
    const dy = point.y - y;
    const sq = dx * dx + dy * dy;
    if (sq < bestSq) {
      bestSq = sq;
      best = point;
    }
  }
  return { point: best, distance: Math.sqrt(bestSq) };
}

/**
 * How much the ramp overrides the bench steps at a point: 1 on the ramp surface, fading
 * to 0 across a shoulder beyond the corridor edge. This is what CUTS the ramp through
 * the benches in the terrain itself, instead of drawing a road over a staircase.
 */
export function rampInfluence(distance: number, pit: PitMorphology): number {
  const half = pit.rampWidthM / 2;
  const shoulder = 14;
  if (distance <= half) return 1;
  if (distance >= half + shoulder) return 0;
  const t = (distance - half) / shoulder;
  return 1 - t * t * (3 - 2 * t);
}
