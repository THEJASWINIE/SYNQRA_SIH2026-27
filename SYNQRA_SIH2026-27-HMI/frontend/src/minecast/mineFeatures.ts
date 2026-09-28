/**
 * Mine geometry — the rim, the bench crests and the floor, as invented features with
 * provenance.
 *
 * ==========================================================================
 *  EVERY FEATURE HERE IS SYNTHETIC, AND EVERY FEATURE SAYS SO.
 *
 *  There is no authoritative pit survey, bench schedule or high-wall model in this
 *  repository. These features exist so the spatial view has a mine to show; they are not
 *  NMDC infrastructure and must never be labelled as such.
 *
 *  Each feature therefore carries its own provenance record - `source`, `verified`,
 *  `confidence` - rather than relying on a single banner somewhere else on the page.
 * ==========================================================================
 *
 * DERIVED FROM THE MORPHOLOGY, NOT DRAWN INDEPENDENTLY
 *
 * Every line here is a contour of constant inwardness in `pitMorphology.ts` - the same
 * description `elevationAt` cuts the terrain from. So the rim line sits on the rim, each
 * bench crest sits on the upper edge of its riser, and the floor outline traces the
 * floor. The bench crests are INTERRUPTED where the ramp cuts through them: a bench that
 * a ramp passes through does not have a crest there, and drawing one would contradict
 * the terrain.
 *
 * FORBIDDEN LABELS
 *
 * `NMDC INFRASTRUCTURE`, `OFFICIAL NMDC PIT`, `LEASE BOUNDARY` and any wording implying a
 * survey. Asserted in the tests, not just intended here.
 *
 * Pure and framework-free - no Three.js import - so it is testable without a DOM or a
 * WebGL context (M4D-C).
 */

import type { MineCastProvenance } from "./minecastProjection";
import {
  benchDepthM,
  contourAt,
  crestContourAt,
  nearestRampPoint,
  type PitMorphology,
  rampCentreline,
} from "./pitMorphology";
import { elevationAt, type TerrainConfig } from "./terrainField";

/** What kind of mine feature this is. */
export type MineFeatureKind = "PIT" | "BENCH" | "FLOOR";

export interface ScenePoint {
  readonly x: number;
  readonly y: number;
}

/**
 * One invented mine feature.
 *
 * The provenance triple is the point of this type. `source` names where the geometry came
 * from, `verified` records that nobody checked it against reality, and `confidence` says
 * how much weight it can bear - which for invented geometry is none.
 */
export interface MineFeature {
  readonly id: string;
  readonly kind: MineFeatureKind;
  readonly source: MineCastProvenance;
  readonly verified: boolean;
  readonly confidence: "LOW" | "MEDIUM" | "HIGH";
  /** Human label for the scene and the provenance panel. */
  readonly label: string;

  /** Inwardness of this feature's contour: 0 rim, 1 floor edge. */
  readonly inwardness: number;
  /** Bench level this crest belongs to. 0 for the rim, `benchCount` for the floor. */
  readonly level: number;
  /** Elevation of this feature's surface, relative metres about the local datum. */
  readonly elevationM: number;
  /** Height of the riser below this feature, metres. Zero for the floor. */
  readonly riserM: number;
  /**
   * The contour as one or more open polylines.
   *
   * The rim and the floor are single closed loops (their last point joins their first).
   * A bench crest is usually several segments, because the ramp interrupts it.
   */
  readonly segments: readonly (readonly ScenePoint[])[];
  /** True when the contour was cut by the ramp and is therefore not a closed ring. */
  readonly interrupted: boolean;
}

/** The single provenance record every feature in this module shares. */
export const SYNTHETIC_GEOMETRY_PROVENANCE = {
  source: "SYNTHETIC_FOR_DEMO" as MineCastProvenance,
  verified: false,
  confidence: "LOW" as const,
  detail:
    "Invented open-pit geometry for demonstration. No authoritative pit survey, bench schedule or wall model exists in this repository. This is not NMDC infrastructure.",
};

/** Points along the contour that lie within reach of the ramp corridor are dropped. */
function cutByRamp(
  contour: readonly ScenePoint[],
  pit: PitMorphology,
  clearanceM: number,
): { segments: ScenePoint[][]; interrupted: boolean } {
  const ramp = rampCentreline(pit);
  const segments: ScenePoint[][] = [];
  let current: ScenePoint[] = [];
  let interrupted = false;

  for (const point of contour) {
    const { distance } = nearestRampPoint(point.x, point.y, ramp);
    if (distance < clearanceM) {
      interrupted = true;
      if (current.length > 1) segments.push(current);
      current = [];
    } else {
      current.push(point);
    }
  }
  if (current.length > 1) segments.push(current);

  // A contour with no cut is one closed loop: join its end back to its start.
  if (!interrupted && segments.length === 1) {
    const only = segments[0] as ScenePoint[];
    const first = only[0];
    if (first) only.push(first);
  }

  return { segments, interrupted };
}

function feature(
  id: string,
  kind: MineFeatureKind,
  label: string,
  inwardness: number,
  level: number,
  pit: PitMorphology,
  cut: boolean,
): MineFeature {
  // Crests follow the warped steps, so each one sits on its own bench edge.
  const contour = crestContourAt(inwardness, pit, 160);
  const riserM = pit.depthM / pit.benchCount;
  const clearance = pit.rampWidthM / 2 + 18;
  const { segments, interrupted } = cut
    ? cutByRamp(contour, pit, clearance)
    : { segments: [[...contour, contour[0] as ScenePoint]], interrupted: false };

  return {
    id,
    kind,
    source: SYNTHETIC_GEOMETRY_PROVENANCE.source,
    verified: SYNTHETIC_GEOMETRY_PROVENANCE.verified,
    confidence: SYNTHETIC_GEOMETRY_PROVENANCE.confidence,
    label,
    inwardness,
    level,
    // `0 - 0` rather than `-0`, so the rim compares equal to zero.
    elevationM: 0 - benchDepthM(level, pit),
    riserM: kind === "FLOOR" ? 0 : riserM,
    segments,
    interrupted,
  };
}

/**
 * The rim, one crest per bench, and the floor outline.
 *
 * Bench crest k sits just outside the riser between level k-1 and level k, so its
 * elevation is level k-1's - the top of the step. The rim is level 0 and is not cut by
 * the ramp (the ramp enters across it, which is the access); every bench crest is.
 */
export function mineFeatures(config: TerrainConfig): readonly MineFeature[] {
  const pit = config.pit;
  const features: MineFeature[] = [
    feature("PIT-01", "PIT", "Pit rim (synthetic)", 0, 0, pit, false),
  ];

  for (let k = 1; k < pit.benchCount; k += 1) {
    features.push(
      feature(
        `BENCH-${String(k).padStart(2, "0")}`,
        "BENCH",
        `Bench ${k} crest (synthetic)`,
        // A hair outside the step so the crest samples the upper bench, not the riser.
        k / pit.benchCount - 0.004,
        k - 1,
        pit,
        true,
      ),
    );
  }

  features.push(
    feature("FLOOR-01", "FLOOR", "Pit floor outline (synthetic)", 1, pit.benchCount, pit, true),
  );

  return features;
}

/** Only the bench crests, outermost first. */
export function benchFeatures(config: TerrainConfig): readonly MineFeature[] {
  return mineFeatures(config).filter((f) => f.kind === "BENCH");
}

/** The rim outline feature. */
export function pitFeature(config: TerrainConfig): MineFeature {
  const pit = mineFeatures(config).find((f) => f.kind === "PIT");
  if (!pit) throw new Error("mineFeatures must always include a pit rim");
  return pit;
}

/** The floor outline feature. */
export function floorFeature(config: TerrainConfig): MineFeature {
  const floor = mineFeatures(config).find((f) => f.kind === "FLOOR");
  if (!floor) throw new Error("mineFeatures must always include a floor outline");
  return floor;
}

/** Every polyline of a feature, for a renderer or a test. */
export function featureSegments(feature: MineFeature): readonly (readonly ScenePoint[])[] {
  return feature.segments;
}

// ---------------------------------------------------------------------------
// bench SURFACES — shelves, faces and the floor, as areas rather than lines
// ---------------------------------------------------------------------------

/**
 * Pass 3B-M2. A bench is not a line: it is a horizontal SHELF with area, separated from
 * the next level by a steep FACE with area. The crest polylines above are kept as subtle
 * edges; the surfaces below are what the Benches layer draws.
 *
 * Every surface is a set of STRIPS - an outer polyline and an inner polyline of equal
 * length, joined into quads - and each strip stops where the ramp cuts through, so a
 * shelf the ramp crosses is genuinely interrupted rather than painted over the road.
 * The floor is one strip whose inner edge collapses to the pit centre (a fan).
 *
 * Elevations are TRUE metres from the SAME `elevationAt` the terrain is built from, so
 * a shelf sits on its own bench and a face spans exactly one riser. The renderer
 * re-drapes on the mesh's own triangulation and applies the disclosed exaggeration.
 */
export type BenchSurfaceKind = "SHELF" | "FACE" | "FLOOR_SURFACE";

export interface SurfacePoint {
  readonly x: number;
  readonly y: number;
  /** TRUE metres about the local synthetic datum. */
  readonly elevationM: number;
}

export interface SurfaceStrip {
  readonly outer: readonly SurfacePoint[];
  readonly inner: readonly SurfacePoint[];
}

export interface BenchSurface {
  readonly id: string;
  readonly kind: BenchSurfaceKind;
  readonly source: MineCastProvenance;
  readonly verified: boolean;
  readonly confidence: "LOW" | "MEDIUM" | "HIGH";
  readonly label: string;
  /** Bench level this surface belongs to; a face is numbered by the level BELOW it. */
  readonly level: number;
  /** Nominal elevation at the top and bottom of the surface, TRUE metres. Equal for a shelf. */
  readonly topElevationM: number;
  readonly bottomElevationM: number;
  readonly strips: readonly SurfaceStrip[];
  /** True when the ramp cuts this surface into more than one strip. */
  readonly interrupted: boolean;
}

/** Half-width, in warped inwardness, of the band a face occupies about its step. */
const FACE_HALF_BAND = 0.018;

function surfacePoint(x: number, y: number, config: TerrainConfig): SurfacePoint {
  return { x, y, elevationM: elevationAt(x, y, config) };
}

/**
 * Pair two contours of equal sample count into strips, dropping every pair within
 * `clearanceM` of the ramp centreline. Closed when the ramp never touches it.
 */
function stripsBetween(
  outer: readonly ScenePoint[],
  inner: readonly ScenePoint[],
  config: TerrainConfig,
  clearanceM: number,
): { strips: SurfaceStrip[]; interrupted: boolean } {
  const ramp = rampCentreline(config.pit);
  const strips: SurfaceStrip[] = [];
  let o: SurfacePoint[] = [];
  let n: SurfacePoint[] = [];
  let interrupted = false;

  const flush = () => {
    if (o.length > 1) strips.push({ outer: o, inner: n });
    o = [];
    n = [];
  };

  for (let i = 0; i < outer.length; i += 1) {
    const a = outer[i] as ScenePoint;
    const b = inner[i] as ScenePoint;
    const cut =
      nearestRampPoint(a.x, a.y, ramp).distance < clearanceM ||
      nearestRampPoint(b.x, b.y, ramp).distance < clearanceM;
    if (cut) {
      interrupted = true;
      flush();
    } else {
      o.push(surfacePoint(a.x, a.y, config));
      n.push(surfacePoint(b.x, b.y, config));
    }
  }
  flush();

  // Uncut: close the ring by repeating the first pair.
  if (!interrupted && strips.length === 1) {
    const only = strips[0] as SurfaceStrip;
    const firstO = only.outer[0];
    const firstN = only.inner[0];
    if (firstO && firstN) {
      strips[0] = { outer: [...only.outer, firstO], inner: [...only.inner, firstN] };
    }
  }

  return { strips, interrupted };
}

function surface(
  id: string,
  kind: BenchSurfaceKind,
  label: string,
  level: number,
  topElevationM: number,
  bottomElevationM: number,
  built: { strips: SurfaceStrip[]; interrupted: boolean },
): BenchSurface {
  return {
    id,
    kind,
    source: SYNTHETIC_GEOMETRY_PROVENANCE.source,
    verified: SYNTHETIC_GEOMETRY_PROVENANCE.verified,
    confidence: SYNTHETIC_GEOMETRY_PROVENANCE.confidence,
    label,
    level,
    topElevationM,
    bottomElevationM,
    strips: built.strips,
    interrupted: built.interrupted,
  };
}

/**
 * The bench surfaces: one SHELF per intermediate level, one FACE per riser (including
 * the riser down to the floor), and the FLOOR_SURFACE.
 *
 * Level 0 - the ground just inside the rim - is not a shelf; it is the surface. The
 * rim crest from `mineFeatures` marks it.
 */
export function benchSurfaces(config: TerrainConfig): readonly BenchSurface[] {
  const pit = config.pit;
  const N = pit.benchCount;
  const samples = 160;
  const clearance = pit.rampWidthM / 2 + 18;
  const surfaces: BenchSurface[] = [];
  const pad = (k: number) => String(k).padStart(2, "0");

  // Faces: the riser at warped inwardness k/N, from just above it to just below it.
  for (let k = 1; k <= N; k += 1) {
    const step = k / N;
    const upper = crestContourAt(step - FACE_HALF_BAND, pit, samples);
    const lower = crestContourAt(step < 1 ? step + FACE_HALF_BAND : 1, pit, samples);
    surfaces.push(
      surface(
        `FACE-${pad(k)}`,
        "FACE",
        `Bench face ${k} (synthetic)`,
        k,
        0 - benchDepthM(k - 1, pit),
        0 - benchDepthM(k, pit),
        stripsBetween(upper, lower, config, clearance),
      ),
    );
  }

  // Shelves: the level ground between riser k and riser k+1.
  for (let k = 1; k < N; k += 1) {
    const outer = crestContourAt(k / N + FACE_HALF_BAND, pit, samples);
    const inner = crestContourAt((k + 1) / N - FACE_HALF_BAND, pit, samples);
    const elevation = 0 - benchDepthM(k, pit);
    surfaces.push(
      surface(
        `SHELF-${pad(k)}`,
        "SHELF",
        `Bench ${k} shelf (synthetic)`,
        k,
        elevation,
        elevation,
        stripsBetween(outer, inner, config, clearance),
      ),
    );
  }

  // Floor: a fan from the pit centre to the floor edge. The centre is inside the floor
  // because the floor radius is strictly positive at every bearing.
  const edge = contourAt(1, pit, samples);
  const centre: ScenePoint[] = edge.map(() => ({ x: pit.centreX, y: pit.centreY }));
  const floorElevation = 0 - benchDepthM(N, pit);
  surfaces.push(
    surface(
      "FLOOR-SURFACE-01",
      "FLOOR_SURFACE",
      "Pit floor (synthetic)",
      N,
      floorElevation,
      floorElevation,
      stripsBetween(edge, centre, config, clearance),
    ),
  );

  return surfaces;
}

/** Surfaces of one kind. */
export function surfacesOfKind(
  surfaces: readonly BenchSurface[],
  kind: BenchSurfaceKind,
): readonly BenchSurface[] {
  return surfaces.filter((s) => s.kind === kind);
}

/** Area of one triangle in 3D, using TRUE elevation as the third axis. */
function triangleArea(a: SurfacePoint, b: SurfacePoint, c: SurfacePoint): number {
  const ux = b.x - a.x;
  const uy = b.y - a.y;
  const uz = b.elevationM - a.elevationM;
  const vx = c.x - a.x;
  const vy = c.y - a.y;
  const vz = c.elevationM - a.elevationM;
  const cx = uy * vz - uz * vy;
  const cy = uz * vx - ux * vz;
  const cz = ux * vy - uy * vx;
  return Math.sqrt(cx * cx + cy * cy + cz * cz) / 2;
}

/**
 * Surface area of a strip in square metres, on the TRUE (un-exaggerated) surface.
 * For a face this is essentially riser height x crest length; for a shelf it is the
 * planimetric shelf area. A line has zero area, which is the point of the test.
 */
export function stripAreaM2(strip: SurfaceStrip): number {
  let area = 0;
  for (let i = 0; i < strip.outer.length - 1; i += 1) {
    const o0 = strip.outer[i] as SurfacePoint;
    const o1 = strip.outer[i + 1] as SurfacePoint;
    const n0 = strip.inner[i] as SurfacePoint;
    const n1 = strip.inner[i + 1] as SurfacePoint;
    area += triangleArea(o0, n0, o1) + triangleArea(o1, n0, n1);
  }
  return area;
}

/** Total area of every strip of a surface, square metres. */
export function surfaceAreaM2(surface: BenchSurface): number {
  return surface.strips.reduce((sum, strip) => sum + stripAreaM2(strip), 0);
}
