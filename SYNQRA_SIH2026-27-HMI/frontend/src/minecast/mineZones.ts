/**
 * Synthetic operational zones — active working area, ore stockpile, waste dump, drainage.
 *
 * ==========================================================================
 *  SYNTHETIC DEMONSTRATION GEOMETRY · NOT SURVEYED · NOT NMDC INFRASTRUCTURE
 *
 *  Nothing here is a real Deposit-5 stockpile, dump, working face or drain. The zones
 *  exist so the plan (2D) and the spatial view (3D) both read as an open-pit MINING
 *  OPERATION - benches, haul roads, a place ore goes and a place waste goes - instead of
 *  a landform with a hole in it. Every zone carries the same SYNTHETIC_FOR_DEMO /
 *  verified=false / confidence=LOW triple the pit and the corridors carry.
 * ==========================================================================
 *
 * ONE GEOMETRY, TWO RENDERERS
 *
 * The 2D plan draws these polygons top-down; the 3D scene drapes the same polygons on
 * the terrain. The dump and the stockpile are also LANDFORM: `zoneLiftAt` is added into
 * `elevationAt`, so in 3D the dump is a terraced mound the service road climbs, and the
 * plan's dump terraces are the very tiers the terrain steps up.
 *
 * Positions are stated in the pit's own polar frame (bearing, inwardness) so a zone can
 * never land inside the rim by accident, then converted to scene metres once.
 *
 * Deterministic and pure: no Math.random, no Date, no DOM, no Three.js.
 */

import type { MineCastProvenance } from "./minecastProjection";
import { centroidOf, contourAt, type PitMorphology, pointAt } from "./pitMorphology";

export type MineZoneKind = "ACTIVE_AREA" | "STOCKPILE" | "WASTE_DUMP";

export interface ZonePoint {
  readonly x: number;
  readonly y: number;
}

/** One terrace of a mound: its outline and how far above the surrounding ground it sits. */
export interface ZoneTier {
  readonly liftM: number;
  readonly polygon: readonly ZonePoint[];
}

export interface MineZone {
  readonly id: string;
  readonly kind: MineZoneKind;
  /** Engineering label for the plan, e.g. `ORE STOCKPILE`. */
  readonly planLabel: string;
  /** Long label; always says synthetic. */
  readonly label: string;
  readonly source: MineCastProvenance;
  readonly verified: false;
  readonly confidence: "LOW";
  /** Closed outline (last point equals first), scene metres. */
  readonly polygon: readonly ZonePoint[];
  readonly centre: ZonePoint;
  /** Terraces, outermost first. A flat zone has one tier at lift 0. */
  readonly tiers: readonly ZoneTier[];
}

export interface DrainageLine {
  readonly id: string;
  readonly label: string;
  readonly source: MineCastProvenance;
  readonly points: readonly ZonePoint[];
}

export const ZONE_DISCLOSURE = "SYNTHETIC OPERATIONAL ZONES · NOT SURVEYED · NOT NMDC INFRASTRUCTURE";

export const ZONE_PROVENANCE = {
  source: "SYNTHETIC_FOR_DEMO" as MineCastProvenance,
  verified: false as const,
  confidence: "LOW" as const,
  disclosure: ZONE_DISCLOSURE,
  detail:
    "Invented working area, ore stockpile, waste dump and drainage for demonstration. No " +
    "surveyed Deposit-5 stockpile, dump or drainage geometry exists in this repository and " +
    "none was inferred from the real mine.",
};

// ---------------------------------------------------------------------------
// where the zones are, in the pit's own frame
// ---------------------------------------------------------------------------

/**
 * Zone placements. The stockpile sits in the pit's polar frame (bearing, inwardness) north-
 * east of the rim; negative inwardness is OUTSIDE the rim. The dump sits in the open ground
 * south-west of the pit, stated as fractions of the extent because the rim is narrow on
 * that side and a polar offset there would land it on a bench. Radii are fractions of the
 * pit's base radius. Tests assert every zone point is outside the rim.
 */
const STOCKPILE_PLACEMENT = { theta: 0.72, u: -0.52, radiusRatio: 0.2 };
const DUMP_PLACEMENT = { fx: 0.27, fy: 0.25, radiusRatio: 0.24 };

/** Site extent, so fraction-placed zones can be resolved. */
export interface ZoneSite {
  readonly widthM: number;
  readonly heightM: number;
  readonly pit: PitMorphology;
}

function dumpCentre(site: ZoneSite): ZonePoint {
  return { x: site.widthM * DUMP_PLACEMENT.fx, y: site.heightM * DUMP_PLACEMENT.fy };
}

/** Irregular outline radius about a zone centre, as a multiple of its base radius. */
function outlineShape(phi: number, kind: MineZoneKind): number {
  if (kind === "STOCKPILE") {
    return 1 + 0.12 * Math.cos(2 * phi + 0.4) + 0.06 * Math.cos(3 * phi - 1.1);
  }
  return 1 + 0.16 * Math.cos(2 * phi - 0.6) + 0.08 * Math.cos(3 * phi + 0.9) + 0.04 * Math.cos(5 * phi);
}

function outline(centre: ZonePoint, radiusM: number, kind: MineZoneKind, segments = 40): ZonePoint[] {
  const points: ZonePoint[] = [];
  for (let i = 0; i < segments; i += 1) {
    const phi = (i / segments) * Math.PI * 2;
    const r = radiusM * outlineShape(phi, kind);
    points.push({ x: centre.x + Math.cos(phi) * r, y: centre.y + Math.sin(phi) * r });
  }
  points.push(points[0] as ZonePoint);
  return points;
}

function scaledAbout(polygon: readonly ZonePoint[], centre: ZonePoint, scale: number): ZonePoint[] {
  return polygon.map((p) => ({
    x: centre.x + (p.x - centre.x) * scale,
    y: centre.y + (p.y - centre.y) * scale,
  }));
}

function zone(
  id: string,
  kind: MineZoneKind,
  planLabel: string,
  label: string,
  centre: ZonePoint,
  polygon: readonly ZonePoint[],
  tiers: readonly ZoneTier[],
): MineZone {
  return {
    id,
    kind,
    planLabel,
    label,
    source: ZONE_PROVENANCE.source,
    verified: false,
    confidence: "LOW",
    polygon,
    centre,
    tiers,
  };
}

/** Terrace scales and lifts for the waste dump: three tiers, outermost first. */
export const DUMP_TIERS: readonly { readonly scale: number; readonly liftM: number }[] = [
  { scale: 1, liftM: 10 },
  { scale: 0.72, liftM: 22 },
  { scale: 0.46, liftM: 34 },
];

/** Crown height of the ore stockpile mound, metres above the surrounding ground. */
export const STOCKPILE_CROWN_M = 16;

// ---------------------------------------------------------------------------
// the zones
// ---------------------------------------------------------------------------

/**
 * The three operational zones for a pit, in scene metres.
 *
 *   ZONE-ACTIVE-01     the working area: the pit floor's inner part, where the loading
 *                      loop runs
 *   ZONE-STOCKPILE-01  the ore stockpile / dispatch point the ore-dispatch road ends at
 *   ZONE-DUMP-01       the terraced waste dump the service road ends at
 */
export function mineZones(site: ZoneSite): readonly MineZone[] {
  const pit = site.pit;
  // Active area: the floor outline shrunk about its own centroid, so it is on the floor.
  const floor = contourAt(1, pit, 96);
  const floorCentre = centroidOf(floor);
  const active = scaledAbout(floor, floorCentre, 0.62);
  active.push(active[0] as ZonePoint);

  const stock = pointAt(STOCKPILE_PLACEMENT.theta, STOCKPILE_PLACEMENT.u, pit);
  const stockRadius = pit.baseRadiusM * STOCKPILE_PLACEMENT.radiusRatio;
  const stockOutline = outline(stock, stockRadius, "STOCKPILE");

  const dump = dumpCentre(site);
  const dumpRadius = pit.baseRadiusM * DUMP_PLACEMENT.radiusRatio;
  const dumpOutline = outline(dump, dumpRadius, "WASTE_DUMP");

  return [
    zone(
      "ZONE-ACTIVE-01",
      "ACTIVE_AREA",
      "ACTIVE WORKING AREA",
      "Active working area (synthetic)",
      floorCentre,
      active,
      [{ liftM: 0, polygon: active }],
    ),
    zone(
      "ZONE-STOCKPILE-01",
      "STOCKPILE",
      "ORE STOCKPILE · DISPATCH",
      "Ore stockpile and dispatch point (synthetic)",
      stock,
      stockOutline,
      [{ liftM: 0, polygon: stockOutline }],
    ),
    zone(
      "ZONE-DUMP-01",
      "WASTE_DUMP",
      "WASTE DUMP",
      "Terraced waste dump (synthetic)",
      dump,
      dumpOutline,
      DUMP_TIERS.map((tier) => ({
        liftM: tier.liftM,
        polygon: scaledAbout(dumpOutline, dump, tier.scale),
      })),
    ),
  ];
}

/** The outline vertex of a zone nearest to a point: where a road meets the zone's edge. */
export function nearestOutlinePoint(zone: MineZone, x: number, y: number): ZonePoint {
  let best = zone.polygon[0] as ZonePoint;
  let bestSq = Number.POSITIVE_INFINITY;
  for (const p of zone.polygon) {
    const sq = (p.x - x) ** 2 + (p.y - y) ** 2;
    if (sq < bestSq) {
      bestSq = sq;
      best = p;
    }
  }
  return best;
}

/** The zone of a kind, which always exists. */
export function zoneOfKind(zones: readonly MineZone[], kind: MineZoneKind): MineZone {
  const found = zones.find((z) => z.kind === kind);
  if (!found) throw new Error(`mineZones must always include ${kind}`);
  return found;
}

// ---------------------------------------------------------------------------
// the mounds, as landform
// ---------------------------------------------------------------------------

function smoothstep(t: number): number {
  const c = t < 0 ? 0 : t > 1 ? 1 : t;
  return c * c * (3 - 2 * c);
}

/** Normalised radial distance of a point from a zone centre: 1 on the outline. */
function normalisedDistance(
  x: number,
  y: number,
  centre: ZonePoint,
  radiusM: number,
  kind: MineZoneKind,
): number {
  const dx = x - centre.x;
  const dy = y - centre.y;
  const d = Math.hypot(dx, dy);
  if (d > radiusM * 1.3) return 2;
  return d / (radiusM * outlineShape(Math.atan2(dy, dx), kind));
}

/**
 * Metres the dump and the stockpile raise the ground at (x, y). Zero everywhere else.
 *
 * The dump is a stepped mound: each tier is a plateau at its lift, joined by a short
 * slope (`0.06` of the radius) so the terrain mesh gets a clean riser rather than a
 * cliff one cell wide. The stockpile is a single rounded crown.
 */
export function zoneLiftAt(x: number, y: number, site: ZoneSite): number {
  const pit = site.pit;
  const dump = dumpCentre(site);
  const dumpRadius = pit.baseRadiusM * DUMP_PLACEMENT.radiusRatio;
  const dd = normalisedDistance(x, y, dump, dumpRadius, "WASTE_DUMP");
  if (dd < 1) {
    // The outline is the toe (lift 0). Each riser climbs over 0.14 of the radius (~30 m)
    // inward of its outline, so the mesh gets a slope, not a wall, and a road ending at
    // the toe ends on level ground.
    let lift = (DUMP_TIERS[0]?.liftM ?? 0) * smoothstep((1 - dd) / 0.14);
    for (let i = 1; i < DUMP_TIERS.length; i += 1) {
      const below = DUMP_TIERS[i - 1] as { scale: number; liftM: number };
      const tier = DUMP_TIERS[i] as { scale: number; liftM: number };
      lift += (tier.liftM - below.liftM) * smoothstep((tier.scale - dd) / 0.14);
    }
    return lift;
  }

  const stock = pointAt(STOCKPILE_PLACEMENT.theta, STOCKPILE_PLACEMENT.u, pit);
  const stockRadius = pit.baseRadiusM * STOCKPILE_PLACEMENT.radiusRatio;
  const sd = normalisedDistance(x, y, stock, stockRadius, "STOCKPILE");
  if (sd < 1) {
    return STOCKPILE_CROWN_M * smoothstep((1 - sd) * 1.6);
  }
  return 0;
}

// ---------------------------------------------------------------------------
// drainage
// ---------------------------------------------------------------------------

/**
 * Two synthetic drainage lines in the low ground outside the pit, for plan context only.
 * Gentle meanders from closed-form sines; nothing is derived from a hydrology model.
 */
export function drainageLines(
  widthM: number,
  heightM: number,
  pit: PitMorphology,
): readonly DrainageLine[] {
  const line = (
    id: string,
    from: readonly [number, number],
    to: readonly [number, number],
    amplitude: number,
  ): DrainageLine => {
    const points: ZonePoint[] = [];
    const steps = 28;
    const dx = to[0] - from[0];
    const dy = to[1] - from[1];
    const len = Math.hypot(dx, dy) || 1;
    const nx = -dy / len;
    const ny = dx / len;
    for (let i = 0; i <= steps; i += 1) {
      const t = i / steps;
      const wobble =
        amplitude * (Math.sin(t * Math.PI * 3.1) * 0.7 + Math.sin(t * Math.PI * 7.3) * 0.3);
      points.push({ x: from[0] + dx * t + nx * wobble, y: from[1] + dy * t + ny * wobble });
    }
    return { id, label: "Drainage line (synthetic)", source: ZONE_PROVENANCE.source, points };
  };

  // Southern drain along the low ground below the pit; eastern drain toward the corner.
  const south = Math.max(60, pit.centreY - pit.baseRadiusM * 1.5);
  return [
    line("DRAIN-01", [widthM * 0.04, south + 60], [widthM * 0.96, south - 30], 46),
    line("DRAIN-02", [widthM * 0.97, heightM * 0.36], [widthM * 0.8, heightM * 0.03], 30),
  ];
}
