/**
 * Synthetic terrain height field.
 *
 * ==========================================================================
 *  THIS TERRAIN IS INVENTED. IT IS NOT A SURVEY OF BAILADILA DEPOSIT-5.
 *
 *  No DEM, no LiDAR, no photogrammetry and no mine survey is bundled with this
 *  repository, so there is nothing to sample real elevations from. Rather than ship an
 *  empty viewport, Pass 2 generates a plausible open-pit landform and labels it
 *  SYNTHETIC_FOR_DEMO everywhere it appears - in the layer drawer, in the provenance
 *  panel, and on the scene itself.
 *
 *  Consequences that are deliberately preserved:
 *    * elevations are RELATIVE metres about a local datum, never metres above sea level,
 *      because an absolute height would imply a vertical reference nobody established;
 *    * no distance, gradient or volume read off this surface means anything about the
 *      real mine;
 *    * a vehicle is never placed by sampling this surface - a marker is drawn only where
 *      the Twin supplies a real position.
 *
 *  When a real DEM is obtained it replaces `elevationAt` behind the same interface, and
 *  the provenance below changes with it. Nothing else in the scene needs to know.
 * ==========================================================================
 *
 * DETERMINISTIC BY CONSTRUCTION
 *
 * Seeded integer hashing, no `Math.random`. The same seed yields the same landform on
 * every run and on every machine, so a screenshot is reproducible and a test can assert
 * exact values. A terrain that shifted between runs would also defeat the requirement
 * that terrain is built once and never rebuilt on a telemetry update.
 *
 * Pure and framework-free - no Three.js import - so it is testable without a DOM or a
 * WebGL context (M4D-C).
 */

import type { MineCastProvenance } from "./minecastProjection";
import { zoneLiftAt } from "./mineZones";
import {
  benchDepthM,
  benchInwardnessAt,
  benchLevelAt,
  inwardnessAt,
  nearestRampPoint,
  type PitMorphology,
  pitMorphology,
  type RampPoint,
  rampCentreline,
  rampInfluence,
} from "./pitMorphology";

// ---------------------------------------------------------------------------
// provenance
// ---------------------------------------------------------------------------

export interface TerrainProvenance {
  readonly source: MineCastProvenance;
  /** False, and it stays false until a real elevation source is bundled. */
  readonly verified: boolean;
  readonly confidence: "LOW" | "MEDIUM" | "HIGH";
  /** Shown wherever the terrain is shown. Not a tooltip. */
  readonly label: string;
  readonly detail: string;
  /** The vertical reference. NOT mean sea level - there isn't one. */
  readonly verticalDatum: string;
  /**
   * Vertical scale multiplier applied when drawing.
   *
   * Exaggerating relief is standard practice in mine visualisation - at true 1:1 a 260 m
   * pit across a 3 km site reads as a dimple - but it MUST be disclosed, because it makes
   * every slope on screen steeper than the ground it depicts. No gradient read off this
   * view is a real gradient.
   */
  readonly verticalExaggeration: number;
}

/**
 * Vertical scale multiplier for drawing. Disclosed on the viewport caption and in the
 * provenance panel; never applied silently.
 */
export const VERTICAL_EXAGGERATION = 2.5;

export const TERRAIN_PROVENANCE: TerrainProvenance = {
  source: "SYNTHETIC_FOR_DEMO",
  verified: false,
  confidence: "LOW",
  label: "SYNTHETIC TERRAIN — NOT SURVEYED",
  detail:
    "Procedurally generated open-pit landform. No DEM, LiDAR or mine survey is bundled with this repository, so no elevation here is a measurement of Bailadila Deposit-5. Vertical scale is exaggerated 2.5x for legibility, so no slope shown is a real gradient.",
  verticalDatum: "LOCAL_RELATIVE_METRES_UNSURVEYED",
  verticalExaggeration: VERTICAL_EXAGGERATION,
};

// ---------------------------------------------------------------------------
// configuration
// ---------------------------------------------------------------------------

export interface TerrainConfig {
  /** Scene extent in metres, east-west. */
  readonly widthM: number;
  /** Scene extent in metres, north-south. */
  readonly heightM: number;
  /** Grid resolution. Vertices per side is `segments + 1`. */
  readonly segments: number;
  /** Deterministic seed. Same seed, same landform. */
  readonly seed: number;
  /** Pit centre, as a fraction of the extent (0..1) from the south-west corner. */
  readonly pitCentre: { readonly fx: number; readonly fy: number };
  /** Pit rim radius in metres. */
  readonly pitRadiusM: number;
  /** Total pit depth in metres, rim to floor. */
  readonly pitDepthM: number;
  /** Number of benches cut into the pit wall. */
  readonly benchCount: number;
  /** Amplitude of the surrounding hill relief, in metres. */
  readonly reliefM: number;
  /**
   * The irregular open-pit shape. Everything below the rim - bench steps, the offset
   * floor, the switchback ramp cut - is derived from this one description, so the
   * terrain, the bench lines and the roads cannot disagree about the pit.
   */
  readonly pit: PitMorphology;
}

/**
 * The demonstration landform.
 *
 * Dimensions are driven by the published coordinate extent's own measured size, so the
 * pit sits inside the area the extent describes rather than at an arbitrary scale. The
 * SHAPE is still invented.
 */
export function terrainConfig(widthM: number, heightM: number): TerrainConfig {
  const pitCentre = { fx: 0.47, fy: 0.52 };
  const pitRadiusM = Math.max(320, widthM * 0.3);
  const pitDepthM = 260;
  const pit = pitMorphology(pitCentre.fx * widthM, pitCentre.fy * heightM, pitRadiusM, pitDepthM);
  return {
    widthM,
    heightM,
    // 200 segments is ~40k vertices, a 16 m cell on this extent: a 40 m ramp is two
    // cells wide and a bench face rasterises as one crisp cell. Built once.
    segments: 200,
    seed: 20260910,
    pitCentre,
    pitRadiusM,
    pitDepthM,
    benchCount: pit.benchCount,
    // MINE-ROUTES-02: gentle undulation only. The pit, its benches and the dump terraces
    // are the landform; hills would make the site read as mountains with a hole in them.
    reliefM: 28,
    pit,
  };
}

/**
 * The ramp centreline for a config, generated once per config object.
 *
 * `elevationAt` runs per terrain vertex and per road point; rebuilding ~120 ramp points
 * each time would dominate the cost of building the landform for no reason.
 */
const rampCache = new WeakMap<PitMorphology, readonly RampPoint[]>();

function rampFor(pit: PitMorphology): readonly RampPoint[] {
  let ramp = rampCache.get(pit);
  if (!ramp) {
    ramp = rampCentreline(pit);
    rampCache.set(pit, ramp);
  }
  return ramp;
}

// ---------------------------------------------------------------------------
// deterministic value noise
// ---------------------------------------------------------------------------

/** Integer hash. Deterministic, cheap, and free of `Math.random`. */
function hash2(ix: number, iy: number, seed: number): number {
  let h = (ix | 0) * 374761393 + (iy | 0) * 668265263 + (seed | 0) * 1274126177;
  h = (h ^ (h >>> 13)) * 1274126177;
  h = h ^ (h >>> 16);
  // Map to 0..1 without bias toward either end.
  return (h >>> 0) / 4294967295;
}

/** Smoothstep, so adjacent noise cells meet without a visible crease. */
function smooth(t: number): number {
  return t * t * (3 - 2 * t);
}

/** Bilinear value noise at a point, in noise-cell units. */
function valueNoise(x: number, y: number, seed: number): number {
  const x0 = Math.floor(x);
  const y0 = Math.floor(y);
  const fx = smooth(x - x0);
  const fy = smooth(y - y0);

  const n00 = hash2(x0, y0, seed);
  const n10 = hash2(x0 + 1, y0, seed);
  const n01 = hash2(x0, y0 + 1, seed);
  const n11 = hash2(x0 + 1, y0 + 1, seed);

  const top = n00 + (n10 - n00) * fx;
  const bottom = n01 + (n11 - n01) * fx;
  return top + (bottom - top) * fy;
}

/** Several octaves of value noise, for relief that reads as ground rather than ripples. */
function fractalNoise(x: number, y: number, seed: number, octaves = 4): number {
  let sum = 0;
  let amplitude = 1;
  let frequency = 1;
  let total = 0;
  for (let octave = 0; octave < octaves; octave += 1) {
    sum += valueNoise(x * frequency, y * frequency, seed + octave * 1013) * amplitude;
    total += amplitude;
    amplitude *= 0.5;
    frequency *= 2;
  }
  return sum / total;
}

// ---------------------------------------------------------------------------
// the surface
// ---------------------------------------------------------------------------

/**
 * Relative elevation in metres at a scene position.
 *
 * `x` and `y` are metres from the south-west corner of the extent. The return value is
 * metres about a LOCAL datum: positive is up, zero is the nominal surrounding grade. It
 * is not an altitude.
 *
 * Shape: rolling hill relief, with an irregular open pit cut into it. Inside the rim the
 * depth is quantised into benches; along the ramp corridor the steps are overridden by
 * the ramp's own graded descent, so the ramp is a cut through the benches rather than a
 * line drawn over a staircase.
 */
export function elevationAt(x: number, y: number, config: TerrainConfig): number {
  // Surrounding relief. Noise is sampled in units of ~650 m so undulations are broad.
  const nx = x / 650;
  const ny = y / 650;
  const pit = config.pit;
  // The waste dump and the ore stockpile are mounds ON the ground, outside the rim.
  const relief = (fractalNoise(nx, ny, config.seed) - 0.5) * 2 * config.reliefM + zoneLiftAt(x, y, config);

  const u = inwardnessAt(x, y, pit);

  // Outside the rim, and beyond the ramp's surface approach, the ground is just relief.
  const nearest = nearestRampPoint(x, y, rampFor(pit));
  const onRamp = rampInfluence(nearest.distance, pit);

  if (u <= 0 && onRamp === 0) return relief;

  /*
    Inside the rim: bench steps. `u` in [0, 1) is quantised into `benchCount` levels;
    beyond 1 is the floor. The relief is attenuated toward the pit so benches read as
    cut surfaces rather than as hills with a hole in them.
  */
  // Levels are cut from the WARPED inwardness, so bench widths vary with bearing.
  const level = benchLevelAt(benchInwardnessAt(x, y, pit), pit);
  const attenuation = u <= 0 ? 1 : 1 - 0.7 * (u < 1 ? u : 1);
  const benched = relief * attenuation - benchDepthM(level, pit);

  if (onRamp === 0) return benched;

  /*
    On or beside the ramp: blend toward the ramp's graded profile. On the surface
    approach the ramp depth is 0, so the cut fades into the relief; inside the pit it
    descends smoothly through the levels the benches step down.
  */
  // The relief is faded out over the first stretch of the descent rather than switched
  // off at the rim, so the ramp surface has no step where it crosses the crest.
  const reliefKeep = nearest.point.u <= 0 ? 1 : 1 - 0.7 * Math.min(1, nearest.point.u / 0.08);
  const rampSurface = relief * reliefKeep - nearest.point.depthM;
  return benched + (rampSurface - benched) * onRamp;
}

// ---------------------------------------------------------------------------
// sampling to a grid
// ---------------------------------------------------------------------------

export interface HeightGrid {
  /** Vertices per side. */
  readonly size: number;
  readonly widthM: number;
  readonly heightM: number;
  /** Row-major elevations, `size * size` entries, metres. */
  readonly heights: readonly number[];
  readonly minM: number;
  readonly maxM: number;
  /** Draw-time vertical multiplier. Elevations above are TRUE metres. */
  readonly verticalExaggeration: number;
  readonly provenance: TerrainProvenance;
}

/**
 * Sample the field onto a regular grid.
 *
 * Called ONCE and memoised by the renderer. Terrain is static: rebuilding it on a
 * telemetry update would burn a frame budget for a surface that never changes.
 */
export function sampleHeightGrid(config: TerrainConfig): HeightGrid {
  const size = config.segments + 1;
  const heights: number[] = new Array(size * size);

  let minM = Number.POSITIVE_INFINITY;
  let maxM = Number.NEGATIVE_INFINITY;

  for (let row = 0; row < size; row += 1) {
    const y = (row / config.segments) * config.heightM;
    for (let col = 0; col < size; col += 1) {
      const x = (col / config.segments) * config.widthM;
      const h = elevationAt(x, y, config);
      heights[row * size + col] = h;
      if (h < minM) minM = h;
      if (h > maxM) maxM = h;
    }
  }

  return {
    size,
    widthM: config.widthM,
    heightM: config.heightM,
    heights,
    minM,
    maxM,
    verticalExaggeration: VERTICAL_EXAGGERATION,
    provenance: TERRAIN_PROVENANCE,
  };
}

/**
 * Elevation of the RENDERED surface at (x, y).
 *
 * `elevationAt` is the continuous field. The terrain mesh is that field sampled on a grid,
 * with each grid cell drawn as TWO FLAT TRIANGLES split on the top-right / bottom-left
 * diagonal (see `MineTerrain`). That is not the same surface as a bilinear patch: at a
 * bench riser the two differ by several metres, which is enough for a ribbon draped on
 * the wrong one to dip under the drawn ground. So this samples the triangulation the GPU
 * actually rasterises, matching `MineTerrain`'s index order exactly.
 *
 * TRUE metres, same datum, same caveats as the field. Clamped to the grid edge.
 */
export function gridElevationAt(grid: HeightGrid, x: number, y: number): number {
  const cells = grid.size - 1;
  const fx = (x / grid.widthM) * cells;
  const fy = (y / grid.heightM) * cells;

  const clampIndex = (value: number) => (value < 0 ? 0 : value > cells - 1 ? cells - 1 : value);
  const col = clampIndex(Math.floor(fx));
  const row = clampIndex(Math.floor(fy));
  const rawTx = fx - col;
  const rawTy = fy - row;
  const tx = rawTx < 0 ? 0 : rawTx > 1 ? 1 : rawTx;
  const ty = rawTy < 0 ? 0 : rawTy > 1 ? 1 : rawTy;

  const at = (r: number, c: number) => grid.heights[r * grid.size + c] ?? 0;
  const topLeft = at(row, col);
  const topRight = at(row, col + 1);
  const bottomLeft = at(row + 1, col);
  const bottomRight = at(row + 1, col + 1);

  /*
    MineTerrain emits (topLeft, bottomLeft, topRight) and (topRight, bottomLeft, bottomRight),
    so the shared diagonal runs from topRight (1, 0) to bottomLeft (0, 1): the line
    tx + ty = 1. Points on or below it are in the first triangle.
  */
  if (tx + ty <= 1) {
    return topLeft + (topRight - topLeft) * tx + (bottomLeft - topLeft) * ty;
  }
  return bottomRight + (bottomLeft - bottomRight) * (1 - tx) + (topRight - bottomRight) * (1 - ty);
}

// ---------------------------------------------------------------------------
// slope and shading (pure, so the terrace legibility is testable)
// ---------------------------------------------------------------------------

/**
 * Surface gradient at a grid vertex: rise over run in TRUE metres, from a central
 * difference on the neighbouring heights. Zero on a shelf or the floor; several on a
 * bench face, where a riser drops within one cell.
 */
export function slopeAt(grid: HeightGrid, col: number, row: number): number {
  const last = grid.size - 1;
  const cellX = grid.widthM / last;
  const cellY = grid.heightM / last;
  const at = (r: number, c: number) => grid.heights[r * grid.size + c] ?? 0;
  const c0 = col > 0 ? col - 1 : col;
  const c1 = col < last ? col + 1 : col;
  const r0 = row > 0 ? row - 1 : row;
  const r1 = row < last ? row + 1 : row;
  const dx = c1 === c0 ? 0 : (at(row, c1) - at(row, c0)) / ((c1 - c0) * cellX);
  const dy = r1 === r0 ? 0 : (at(r1, col) - at(r0, col)) / ((r1 - r0) * cellY);
  return Math.sqrt(dx * dx + dy * dy);
}

/** Gradient above which ground is shaded as an excavation face rather than a shelf. */
export const FACE_SLOPE_THRESHOLD = 0.9;

/**
 * Ground colour for a vertex: desaturated, with the LEVEL shelves lighter and the STEEP
 * faces darker.
 *
 * This is what makes the terraces read as shelf / face / shelf instead of one
 * continuous bowl: elevation banding alone cannot separate a bench top from the wall
 * below it, but slope can. Everything stays near-grey - saturated colour is reserved for
 * operational state in later passes.
 */
export function terrainShade(
  normalisedElevation: number,
  slope: number,
): readonly [number, number, number] {
  const t = normalisedElevation < 0 ? 0 : normalisedElevation > 1 ? 1 : normalisedElevation;
  // 0 on a level shelf, 1 on a face, eased between.
  const raw = (slope - FACE_SLOPE_THRESHOLD * 0.5) / FACE_SLOPE_THRESHOLD;
  const f = raw < 0 ? 0 : raw > 1 ? 1 : raw * raw * (3 - 2 * raw);

  // MINE-ROUTES-02: a narrower, darker shelf range. With gentle relief the surrounding
  // ground sits near the top of the range and read as chalk; mid-grey keeps the amber
  // corridors and the zone tints legible against it.
  const shelf = 0.12 + t * 0.17;
  const face = 0.06 + t * 0.06;
  const shade = shelf + (face - shelf) * f;
  // A touch warmer on the faces (cut rock), a touch cooler on the shelves.
  const warm = 0.012 * f - 0.006;
  return [shade + warm, shade, shade - warm];
}
