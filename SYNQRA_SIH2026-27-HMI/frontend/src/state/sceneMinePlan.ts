/**
 * The Digital Twin mine plan — ONE shared domain, consumed by the 2D plan and the 3D scene.
 *
 * ==========================================================================
 *  SHARED MINE DOMAIN
 *          │
 *   ┌──────┴──────┐
 *   2D renderer   3D renderer          (GeoSiteMap)            (MineCanvas / Mine-Cast)
 *   engineering   spatial twin
 *   └──── SAME ROUTES, SAME ZONES, SAME BENCHES, SAME ELEVATION FIELD ────┘
 *
 *  Nothing in this file invents geometry. It composes the pure generators the 3D scene
 *  already renders - `haulCorridors`, `mineFeatures`, `mineZones`, `demoRoutes`,
 *  `elevationAt` - into one plan object, and adds two things a top-down plan needs that a
 *  3D scene does not: contour lines of the same elevation field, and a strict orthographic
 *  SCENE_METRES -> SVG projection. There is no second route dataset anywhere.
 * ==========================================================================
 *
 * EVERYTHING HERE IS SYNTHETIC DEMONSTRATION GEOMETRY. Not surveyed. Not NMDC
 * infrastructure. The published coordinate extent (`geoSite.ts`) is the only verified
 * geography and is kept a separate reference layer; it is never merged with this.
 *
 * Framework-free: no React, no DOM, no Three.js. Pure maths and contracts.
 */

import {
  type DemoRoute,
  demoRoutes,
  ROUTE_DISCLOSURE,
  ROUTE_METADATA,
} from "../minecast/demoRoutes";
import {
  CORRIDOR_DISCLOSURE,
  CORRIDOR_PROVENANCE,
  type HaulCorridor,
  haulCorridors,
  ROUTE_CLASSIFICATION,
} from "../minecast/haulRoads";
import {
  type MineFeature,
  mineFeatures,
  SYNTHETIC_GEOMETRY_PROVENANCE,
} from "../minecast/mineFeatures";
import {
  type DrainageLine,
  drainageLines,
  type MineZone,
  mineZones,
  ZONE_DISCLOSURE,
} from "../minecast/mineZones";
import { crestContourAt, inwardnessAt } from "../minecast/pitMorphology";
import { elevationAt, type TerrainConfig, terrainConfig } from "../minecast/terrainField";
import {
  type DecimalExtent,
  extentSizeMetres,
  type LonLat,
  projectToLocalMetres,
  type SiteExtent,
  toDecimalExtent,
} from "./geoSite";

export {
  CORRIDOR_DISCLOSURE,
  ROUTE_CLASSIFICATION,
  ROUTE_DISCLOSURE,
  ROUTE_METADATA,
  ZONE_DISCLOSURE,
};
export type { DemoRoute, DrainageLine, HaulCorridor, MineFeature, MineZone };

// ---------------------------------------------------------------------------
// vocabulary
// ---------------------------------------------------------------------------

/**
 * SYNTHETIC BENCH MODEL. Bench elevations are shown as display levels about an invented
 * datum so the plan reads like a bench schedule (BENCH 1180, BENCH 1128 ...). The datum is
 * a round number chosen for legibility; it is NOT a surveyed reduced level and the levels
 * are NOT Deposit-5's bench elevations. The layer is labelled accordingly.
 */
export const BENCH_MODEL_LABEL = "SYNTHETIC BENCH MODEL";
export const BENCH_DISPLAY_DATUM_M = 1180;

/** Contour interval for the surrounding ground, metres of the synthetic field. */
export const CONTOUR_INTERVAL_M = 5;

/** The plan's compact persistent disclosure. */
export const PLAN_DISCLOSURE = {
  twin: "DIGITAL TWIN · SIMULATION",
  frame: "SCENE_METRES",
  routes: "SYNTHETIC ROUTES · NOT SURVEYED",
  infrastructure: "NOT NMDC INFRASTRUCTURE",
  benches: BENCH_MODEL_LABEL,
} as const;

// ---------------------------------------------------------------------------
// the plan
// ---------------------------------------------------------------------------

export interface ScenePoint {
  readonly x: number;
  readonly y: number;
}

export interface ContourLine {
  /** Field elevation of the line, metres about the synthetic datum. */
  readonly levelM: number;
  /** Display level: `BENCH_DISPLAY_DATUM_M + levelM`. */
  readonly displayM: number;
  readonly polylines: readonly (readonly ScenePoint[])[];
}

export interface BenchLevel {
  readonly feature: MineFeature;
  /** Display elevation of the bench surface, metres, synthetic datum. */
  readonly displayM: number;
  readonly label: string;
  /**
   * The UNCUT closed ring of this crest (the feature segments are cut where the ramp
   * crosses). A plan fills the ring so each level reads as a flat terrace step - a tone
   * per level, not shading.
   */
  readonly ring: readonly ScenePoint[];
}

export interface MinePlan {
  readonly config: TerrainConfig;
  readonly size: { readonly widthM: number; readonly heightM: number };
  readonly extent: DecimalExtent;
  readonly corridors: readonly HaulCorridor[];
  readonly routes: readonly DemoRoute[];
  readonly features: readonly MineFeature[];
  readonly benches: readonly BenchLevel[];
  readonly zones: readonly MineZone[];
  readonly drainage: readonly DrainageLine[];
  readonly contours: readonly ContourLine[];
  readonly provenance: {
    readonly corridors: typeof CORRIDOR_PROVENANCE;
    readonly geometry: typeof SYNTHETIC_GEOMETRY_PROVENANCE;
    readonly disclosure: typeof PLAN_DISCLOSURE;
  };
}

function resolveExtent(extent: SiteExtent | DecimalExtent): DecimalExtent {
  const d = extent as DecimalExtent;
  return typeof d.north === "number" && typeof d.west === "number"
    ? d
    : toDecimalExtent(extent as SiteExtent);
}

/**
 * The whole plan for a site extent. Deterministic: the same extent yields the same plan.
 * Contours cost ~10k field samples; callers memoise on the extent.
 */
export function sceneMinePlan(extent: SiteExtent | DecimalExtent): MinePlan {
  const decimal = resolveExtent(extent);
  const size = extentSizeMetres(decimal);
  const config = terrainConfig(size.widthM, size.heightM);
  const features = mineFeatures(config);
  // A crest is the top edge of the face below it, so a bench crest is labelled with the
  // level of the shelf BELOW it - the bench a truck on that crest looks down onto.
  const benches = features.map((feature) => {
    const shelfM = feature.kind === "BENCH" ? feature.elevationM - feature.riserM : feature.elevationM;
    const displayM = Math.round(BENCH_DISPLAY_DATUM_M + shelfM);
    const ring = crestContourAt(feature.inwardness, config.pit, 160);
    return {
      feature,
      displayM,
      ring: [...ring, ring[0] as ScenePoint],
      label:
        feature.kind === "PIT"
          ? `RIM ${displayM}`
          : feature.kind === "FLOOR"
            ? `FLOOR ${displayM}`
            : `BENCH ${displayM}`,
    };
  });

  return {
    config,
    size,
    extent: decimal,
    corridors: haulCorridors(config),
    routes: demoRoutes(config),
    features,
    benches,
    zones: mineZones(config),
    drainage: drainageLines(config.widthM, config.heightM, config.pit),
    contours: groundContours(config),
    provenance: {
      corridors: CORRIDOR_PROVENANCE,
      geometry: SYNTHETIC_GEOMETRY_PROVENANCE,
      disclosure: PLAN_DISCLOSURE,
    },
  };
}

/** The corridors a route is composed of, for highlighting the selected truck's route. */
export function routeCorridorIds(
  plan: MinePlan,
  routeId: string | null | undefined,
): readonly string[] {
  if (!routeId) return [];
  return plan.routes.find((r) => r.routeId === routeId)?.corridorIds ?? [];
}

/** The declared route for a vehicle, if the demonstration assigns one. */
export function routeForVehicle(plan: MinePlan, vehicleId: string): DemoRoute | null {
  return plan.routes.find((r) => r.vehicleId === vehicleId) ?? null;
}

// ---------------------------------------------------------------------------
// contours — marching squares over the shared elevation field, outside the pit
// ---------------------------------------------------------------------------

/**
 * Contour polylines of `elevationAt` outside the rim, at `CONTOUR_INTERVAL_M`.
 *
 * Inside the rim the plan draws the bench crests instead (they ARE the contours of a
 * benched pit), so cells that touch the pit are skipped. Segments from marching squares
 * are chained into polylines by matching endpoints, so the SVG draws a few long paths
 * rather than thousands of two-point lines.
 */
export function groundContours(config: TerrainConfig, cells = 72): readonly ContourLine[] {
  const W = config.widthM;
  const H = config.heightM;
  const nx = cells;
  const ny = Math.max(8, Math.round((cells * H) / W));
  const dx = W / nx;
  const dy = H / ny;

  // Sample once. NaN marks a sample inside (or on) the pit rim.
  const z: number[] = new Array((nx + 1) * (ny + 1));
  let min = Number.POSITIVE_INFINITY;
  let max = Number.NEGATIVE_INFINITY;
  for (let j = 0; j <= ny; j += 1) {
    for (let i = 0; i <= nx; i += 1) {
      const x = i * dx;
      const y = j * dy;
      const inside = inwardnessAt(x, y, config.pit) > -0.04;
      const v = inside ? Number.NaN : elevationAt(x, y, config);
      z[j * (nx + 1) + i] = v;
      if (!inside) {
        if (v < min) min = v;
        if (v > max) max = v;
      }
    }
  }
  if (!Number.isFinite(min) || !Number.isFinite(max)) return [];

  const levels: number[] = [];
  const first = Math.ceil(min / CONTOUR_INTERVAL_M) * CONTOUR_INTERVAL_M;
  for (let level = first; level <= max; level += CONTOUR_INTERVAL_M) levels.push(level);

  const at = (i: number, j: number) => z[j * (nx + 1) + i] as number;
  const lerp = (a: number, b: number, level: number) => (level - a) / (b - a);

  return levels.map((level) => {
    const segments: [ScenePoint, ScenePoint][] = [];
    for (let j = 0; j < ny; j += 1) {
      for (let i = 0; i < nx; i += 1) {
        const a = at(i, j);
        const b = at(i + 1, j);
        const c = at(i + 1, j + 1);
        const d = at(i, j + 1);
        if (Number.isNaN(a) || Number.isNaN(b) || Number.isNaN(c) || Number.isNaN(d)) continue;
        const x0 = i * dx;
        const y0 = j * dy;
        // Crossing points on the four edges, when the level crosses them.
        const crossings: ScenePoint[] = [];
        if (a < level !== b < level) crossings.push({ x: x0 + lerp(a, b, level) * dx, y: y0 });
        if (b < level !== c < level) {
          crossings.push({ x: x0 + dx, y: y0 + lerp(b, c, level) * dy });
        }
        if (c < level !== d < level) {
          crossings.push({ x: x0 + lerp(d, c, level) * dx, y: y0 + dy });
        }
        if (d < level !== a < level) crossings.push({ x: x0, y: y0 + lerp(a, d, level) * dy });
        if (crossings.length === 2) {
          segments.push([crossings[0] as ScenePoint, crossings[1] as ScenePoint]);
        } else if (crossings.length === 4) {
          // Saddle: pair by edge order; the ambiguity is cosmetic at this interval.
          segments.push([crossings[0] as ScenePoint, crossings[1] as ScenePoint]);
          segments.push([crossings[2] as ScenePoint, crossings[3] as ScenePoint]);
        }
      }
    }
    return {
      levelM: level,
      displayM: BENCH_DISPLAY_DATUM_M + level,
      polylines: chain(segments),
    };
  });
}

/** Chain segments into polylines by matching endpoints (rounded to 0.1 m). */
function chain(
  segments: readonly [ScenePoint, ScenePoint][],
): readonly (readonly ScenePoint[])[] {
  const key = (p: ScenePoint) => `${Math.round(p.x * 10)}:${Math.round(p.y * 10)}`;
  const byEnd = new Map<string, number[]>();
  segments.forEach((seg, index) => {
    for (const p of seg) {
      const k = key(p);
      const list = byEnd.get(k);
      if (list) list.push(index);
      else byEnd.set(k, [index]);
    }
  });
  const used = new Array<boolean>(segments.length).fill(false);
  const out: ScenePoint[][] = [];

  const takeFrom = (point: ScenePoint): ScenePoint | null => {
    const list = byEnd.get(key(point));
    if (!list) return null;
    for (const index of list) {
      if (used[index]) continue;
      used[index] = true;
      const seg = segments[index] as [ScenePoint, ScenePoint];
      return key(seg[0]) === key(point) ? seg[1] : seg[0];
    }
    return null;
  };

  for (let s = 0; s < segments.length; s += 1) {
    if (used[s]) continue;
    used[s] = true;
    const seg = segments[s] as [ScenePoint, ScenePoint];
    const line: ScenePoint[] = [seg[0], seg[1]];
    for (;;) {
      const next = takeFrom(line[line.length - 1] as ScenePoint);
      if (!next) break;
      line.push(next);
    }
    for (;;) {
      const prev = takeFrom(line[0] as ScenePoint);
      if (!prev) break;
      line.unshift(prev);
    }
    out.push(line);
  }
  return out;
}

// ---------------------------------------------------------------------------
// projection — strict orthographic top-down, uniform scale
// ---------------------------------------------------------------------------

export interface PlanPoint {
  readonly x: number;
  readonly y: number;
}

export interface PlanProjection {
  readonly viewW: number;
  readonly viewH: number;
  /** SVG units per scene metre. The SAME in x and y: a plan is never stretched. */
  readonly scale: number;
  /** SVG box of the scene extent. */
  readonly box: {
    readonly x: number;
    readonly y: number;
    readonly width: number;
    readonly height: number;
  };
  /** SCENE_METRES -> SVG. North is up: scene +y maps to SVG -y. No tilt, no depth. */
  readonly toSvg: (p: ScenePoint) => PlanPoint;
  /** A lon/lat -> SVG, THROUGH scene metres, so both chains share one projection. */
  readonly lonLatToSvg: (p: LonLat) => PlanPoint;
  /** SVG length of `metres` on the ground. */
  readonly lengthPx: (metres: number) => number;
}

/**
 * Fit the scene extent into a viewport with a margin, preserving aspect. Equal distances
 * on the ground are equal distances on the page in every direction.
 */
export function planProjection(
  size: { readonly widthM: number; readonly heightM: number },
  extent: DecimalExtent,
  viewW: number,
  viewH: number,
  marginPx = 28,
): PlanProjection {
  const scale = Math.min(
    (viewW - 2 * marginPx) / size.widthM,
    (viewH - 2 * marginPx) / size.heightM,
  );
  const width = size.widthM * scale;
  const height = size.heightM * scale;
  const box = { x: (viewW - width) / 2, y: (viewH - height) / 2, width, height };
  const southWest: LonLat = { lon: extent.west, lat: extent.south };
  const toSvg = (p: ScenePoint): PlanPoint => ({
    x: box.x + p.x * scale,
    y: box.y + height - p.y * scale,
  });
  return {
    viewW,
    viewH,
    scale,
    box,
    toSvg,
    lonLatToSvg: (p) => toSvg(projectToLocalMetres(p, southWest)),
    lengthPx: (metres) => metres * scale,
  };
}

/** A round scale-bar length (1/2/5 sequence) that is about `targetPx` wide. */
export function planScaleBar(
  projection: PlanProjection,
  targetPx = 90,
): { metres: number; px: number } {
  const raw = targetPx / projection.scale;
  const magnitude = 10 ** Math.floor(Math.log10(raw > 0 ? raw : 1));
  const n = raw / magnitude;
  const step = n >= 5 ? 5 : n >= 2 ? 2 : 1;
  const metres = step * magnitude;
  return { metres, px: metres * projection.scale };
}

// ---------------------------------------------------------------------------
// route decoration helpers (pure)
// ---------------------------------------------------------------------------

export interface ArrowMark {
  readonly x: number;
  readonly y: number;
  /** Direction of travel, radians, scene frame (counter-clockwise from +x east). */
  readonly angleRad: number;
}

/**
 * Points every `spacingM` along a polyline with the local direction of travel, for
 * direction arrows. Starts half a spacing in so the first arrow is not on the end.
 */
export function arrowMarks(points: readonly ScenePoint[], spacingM: number): readonly ArrowMark[] {
  const marks: ArrowMark[] = [];
  let next = spacingM / 2;
  let travelled = 0;
  for (let i = 1; i < points.length; i += 1) {
    const a = points[i - 1] as ScenePoint;
    const b = points[i] as ScenePoint;
    const len = Math.hypot(b.x - a.x, b.y - a.y);
    if (len === 0) continue;
    while (next <= travelled + len) {
      const t = (next - travelled) / len;
      marks.push({
        x: a.x + (b.x - a.x) * t,
        y: a.y + (b.y - a.y) * t,
        angleRad: Math.atan2(b.y - a.y, b.x - a.x),
      });
      next += spacingM;
    }
    travelled += len;
  }
  return marks;
}

/** Polyline length in metres. */
export function polylineLengthM(points: readonly ScenePoint[]): number {
  let total = 0;
  for (let i = 1; i < points.length; i += 1) {
    const a = points[i - 1] as ScenePoint;
    const b = points[i] as ScenePoint;
    total += Math.hypot(b.x - a.x, b.y - a.y);
  }
  return total;
}

/** The point and travel direction at the middle of a polyline, for a label. */
export function polylineMidpoint(points: readonly ScenePoint[]): ArrowMark {
  const total = polylineLengthM(points);
  const first = points[0] ?? { x: 0, y: 0 };
  return arrowMarks(points, total)[0] ?? { x: first.x, y: first.y, angleRad: 0 };
}
