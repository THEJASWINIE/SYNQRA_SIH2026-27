/**
 * Open-pit morphology — the anti-crater assertions.
 *
 * Pass 2's pit was radial and read as a crater: circular rim, concentric rings, central
 * floor. These tests are written so that a regression back toward that shape FAILS -
 * they measure asymmetry, offset and interruption numerically rather than checking that
 * objects merely exist.
 *
 * Numbering follows the Pass 3B-M brief where it applies.
 *
 * SOFTWARE ONLY. No hardware, no WebGL, no DOM, no network. The geometry is synthetic
 * and is asserted to say so.
 */

import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";

import type { AppState } from "../contracts/appState";
import type { VehicleState } from "../contracts/domain";
import { corridorRibbon, corridorsOfKind, haulCorridors } from "./haulRoads";
import { MINECAST_SITE, projectMineCast, projectMineCastVehicle } from "./minecastProjection";
import {
  benchFeatures,
  benchSurfaces,
  floorFeature,
  mineFeatures,
  pitFeature,
  surfaceAreaM2,
  surfacesOfKind,
} from "./mineFeatures";
import {
  benchDepthM,
  benchInwardnessAt,
  benchLevelAt,
  benchWarp,
  centroidOf,
  contourAt,
  crestContourAt,
  floorRadiusAt,
  floorShape,
  inwardnessAt,
  MORPHOLOGY_DISCLOSURE,
  MORPHOLOGY_PROVENANCE,
  pointAt,
  rampCentreline,
  rampInfluence,
  rimRadiusAt,
  rimShape,
} from "./pitMorphology";
import { drawablePositions, spatialPositions, toSpatialPosition } from "./spatialPosition";
import {
  elevationAt,
  FACE_SLOPE_THRESHOLD,
  sampleHeightGrid,
  slopeAt,
  terrainConfig,
  terrainShade,
} from "./terrainField";

const CONFIG = terrainConfig(3200, 3400);
const PIT = CONFIG.pit;
const TAU = Math.PI * 2;

function source(name: string): string {
  return readFileSync(`src/minecast/${name}`, "utf-8")
    .replace(/\/\*[\s\S]*?\*\//g, "")
    .replace(/^\s*\/\/.*$/gm, "");
}

/**
 * Geometric bench width for bench k at each of 36 bearings: the distance between crest
 * k and crest k+1 along the bearing.
 */
function crestWidths(k: number): number[] {
  const benches = benchFeatures(CONFIG);
  const a = benches[k - 1];
  const b = benches[k];
  if (!a || !b) throw new Error("bench missing");
  const widths: number[] = [];
  const outer = crestContourAt(a.inwardness, PIT, 36);
  const inner = crestContourAt(b.inwardness, PIT, 36);
  for (let i = 0; i < 36; i += 1) {
    const o = outer[i] as { x: number; y: number };
    const n = inner[i] as { x: number; y: number };
    widths.push(Math.hypot(o.x - n.x, o.y - n.y));
  }
  return widths;
}

/** Standard deviation of a list. */
function spread(values: readonly number[]): number {
  const mean = values.reduce((a, b) => a + b, 0) / values.length;
  const variance = values.reduce((a, b) => a + (b - mean) ** 2, 0) / values.length;
  return Math.sqrt(variance);
}

// ---------------------------------------------------------------------------
// 1 + 2. deterministic, no Math.random
// ---------------------------------------------------------------------------

describe("1 — geometry generation is deterministic", () => {
  it("produces identical contours, ramp and features on repeated calls", () => {
    expect(JSON.stringify(contourAt(0.5, PIT))).toBe(JSON.stringify(contourAt(0.5, PIT)));
    expect(JSON.stringify(rampCentreline(PIT))).toBe(JSON.stringify(rampCentreline(PIT)));
    expect(JSON.stringify(mineFeatures(CONFIG))).toBe(JSON.stringify(mineFeatures(CONFIG)));
  });
});

describe("2 — no Math.random is used", () => {
  it("in the morphology, the terrain, the features or the roads", () => {
    for (const name of ["pitMorphology.ts", "terrainField.ts", "mineFeatures.ts", "haulRoads.ts"]) {
      expect(source(name), name).not.toContain("Math.random");
    }
  });
});

// ---------------------------------------------------------------------------
// 3 + 4. the pit is not a circle, and is asymmetric
// ---------------------------------------------------------------------------

describe("3 — the pit is not a perfect circle", () => {
  it("has a rim radius that varies substantially with bearing", () => {
    const radii: number[] = [];
    for (let i = 0; i < 72; i += 1) radii.push(rimRadiusAt((i / 72) * TAU, PIT));
    const min = Math.min(...radii);
    const max = Math.max(...radii);
    // A circle has max/min = 1. This rim is elongated well beyond that.
    expect(max / min).toBeGreaterThan(1.6);
    // And not merely an ellipse: the radius spread is not explained by one harmonic.
    expect(spread(radii) / ((max + min) / 2)).toBeGreaterThan(0.1);
  });

  it("is not an ellipse — opposite bearings do not have equal radii", () => {
    // An ellipse (or any even-harmonic shape) has r(θ) = r(θ + π). Odd harmonics break that.
    let asymmetric = 0;
    for (let i = 0; i < 36; i += 1) {
      const theta = (i / 36) * Math.PI;
      const a = rimShape(theta);
      const b = rimShape(theta + Math.PI);
      if (Math.abs(a - b) > 0.05) asymmetric += 1;
    }
    expect(asymmetric).toBeGreaterThan(24);
  });
});

describe("4 — the pit footprint is asymmetric", () => {
  it("has no bearing about which the rim is mirror-symmetric", () => {
    // For a mirror axis at φ, r(φ + t) = r(φ - t). Search all φ; none should fit.
    let bestError = Number.POSITIVE_INFINITY;
    for (let k = 0; k < 180; k += 1) {
      const phi = (k / 180) * Math.PI;
      let error = 0;
      for (let j = 1; j <= 18; j += 1) {
        const t = (j / 18) * Math.PI;
        error += Math.abs(rimShape(phi + t) - rimShape(phi - t));
      }
      if (error < bestError) bestError = error;
    }
    expect(bestError).toBeGreaterThan(0.3);
  });

  it("outer and inner footprints are not rotationally identical", () => {
    // Normalise each to its mean radius and compare shape functions across all bearings.
    const outer: number[] = [];
    const inner: number[] = [];
    for (let i = 0; i < 72; i += 1) {
      const theta = (i / 72) * TAU;
      outer.push(rimShape(theta));
      inner.push(floorShape(theta));
    }
    const meanOuter = outer.reduce((a, b) => a + b, 0) / outer.length;
    const meanInner = inner.reduce((a, b) => a + b, 0) / inner.length;
    let difference = 0;
    for (let i = 0; i < 72; i += 1) {
      difference += Math.abs((outer[i] ?? 0) / meanOuter - (inner[i] ?? 0) / meanInner);
    }
    expect(difference / 72).toBeGreaterThan(0.15);
  });
});

// ---------------------------------------------------------------------------
// 5. the floor is offset from the rim
// ---------------------------------------------------------------------------

describe("5 — the pit floor is not concentric with the outer footprint", () => {
  it("has a floor centroid a deterministic, non-trivial distance from the rim centroid", () => {
    const rimCentroid = centroidOf(contourAt(0, PIT, 360));
    const floorCentroid = centroidOf(contourAt(1, PIT, 360));
    const dx = floorCentroid.x - rimCentroid.x;
    const dy = floorCentroid.y - rimCentroid.y;
    const offset = Math.sqrt(dx * dx + dy * dy);

    // More than a tenth of the base radius: clearly off-centre, not a rounding artefact.
    expect(offset).toBeGreaterThan(PIT.baseRadiusM * 0.1);
    // And the same every time.
    const again = centroidOf(contourAt(1, PIT, 360));
    expect(again.x).toBe(floorCentroid.x);
    expect(again.y).toBe(floorCentroid.y);
  });

  it("puts the floor edge nearer one wall than the other", () => {
    const radii: number[] = [];
    for (let i = 0; i < 72; i += 1) radii.push(floorRadiusAt((i / 72) * TAU, PIT));
    expect(Math.max(...radii) / Math.min(...radii)).toBeGreaterThan(2);
  });

  it("keeps the floor strictly inside the rim at every bearing", () => {
    for (let i = 0; i < 360; i += 1) {
      const theta = (i / 360) * TAU;
      expect(floorRadiusAt(theta, PIT), String(theta)).toBeLessThan(rimRadiusAt(theta, PIT));
    }
  });
});

// ---------------------------------------------------------------------------
// 6 + 7. benches have distinct elevations and are not identical rings
// ---------------------------------------------------------------------------

describe("6 — bench levels have distinct elevations", () => {
  it("assigns a strictly deeper elevation to each successive level", () => {
    for (let level = 1; level <= PIT.benchCount; level += 1) {
      expect(benchDepthM(level, PIT)).toBeGreaterThan(benchDepthM(level - 1, PIT));
    }
  });

  it("quantises inwardness into exactly benchCount steps", () => {
    const seen = new Set<number>();
    for (let u = 0; u < 1; u += 0.005) seen.add(benchLevelAt(u, PIT));
    expect(seen.size).toBe(PIT.benchCount);
    expect(benchLevelAt(1, PIT)).toBe(PIT.benchCount);
    expect(benchLevelAt(-0.3, PIT)).toBe(0);
  });
});

describe("7 — benches are not all identical closed rings", () => {
  it("bench crests have different total lengths and longest-run lengths", () => {
    const benches = benchFeatures(CONFIG);
    const totalPoints = benches.map((b) => b.segments.reduce((n, s) => n + s.length, 0));
    const longestRun = benches.map((b) => Math.max(...b.segments.map((s) => s.length)));
    // If every bench were one uninterrupted, uniformly cut ring these would all match.
    expect(new Set(totalPoints).size).toBeGreaterThan(1);
    expect(new Set(longestRun).size).toBeGreaterThan(1);
  });

  it("bench widths vary with bearing — wide on one side, narrow on another", () => {
    // The warp pushes steps inward on some bearings and outward on others, so the
    // geometric distance between two adjacent crests is not constant around the pit.
    const upper = crestWidths(2);
    const min = Math.min(...upper);
    const max = Math.max(...upper);
    expect(max / min).toBeGreaterThan(1.5);
    // And the warp itself is a real function of bearing, not a constant offset.
    const warps: number[] = [];
    for (let i = 0; i < 36; i += 1) warps.push(benchWarp((i / 36) * TAU));
    expect(spread(warps)).toBeGreaterThan(0.08);
  });

  it("bench segment endpoints vary across benches", () => {
    const benches = benchFeatures(CONFIG);
    const firstEndpoints = benches.map((b) => {
      const first = b.segments[0]?.[0];
      return first ? `${first.x.toFixed(1)},${first.y.toFixed(1)}` : "";
    });
    expect(new Set(firstEndpoints).size).toBe(benches.length);
  });

  it("no bench crest is a scaled copy of the rim", () => {
    // A concentric ring would have every point at a fixed fraction of the rim radius.
    const rim = contourAt(0, PIT, 72);
    const mid = contourAt(0.5, PIT, 72);
    const ratios = mid.map((p, i) => {
      const r = rim[i] as { x: number; y: number };
      const dm = Math.hypot(p.x - PIT.centreX, p.y - PIT.centreY);
      const dr = Math.hypot(r.x - PIT.centreX, r.y - PIT.centreY);
      return dm / dr;
    });
    expect(spread(ratios)).toBeGreaterThan(0.03);
  });
});

// ---------------------------------------------------------------------------
// 8. benches are interrupted by the ramp
// ---------------------------------------------------------------------------

describe("8 — at least one bench is interrupted for the ramp", () => {
  it("cuts several bench crests into multiple segments", () => {
    const cut = benchFeatures(CONFIG).filter((b) => b.interrupted);
    expect(cut.length).toBeGreaterThanOrEqual(3);
    for (const bench of cut) {
      expect(bench.segments.length, bench.id).toBeGreaterThanOrEqual(2);
    }
  });

  it("the ramp genuinely passes through the crests it interrupts", () => {
    // For an interrupted bench, some ramp point lies within that crest's inwardness band.
    const ramp = rampCentreline(PIT);
    for (const bench of benchFeatures(CONFIG).filter((b) => b.interrupted)) {
      const crossing = ramp.some(
        (p) => Math.abs(benchInwardnessAt(p.x, p.y, PIT) - bench.inwardness) < 0.04,
      );
      expect(crossing, bench.id).toBe(true);
    }
  });

  it("the rim itself is not interrupted — the ramp enters across it", () => {
    expect(pitFeature(CONFIG).interrupted).toBe(false);
  });
});

// ---------------------------------------------------------------------------
// 9 + 10 + 11. the ramp
// ---------------------------------------------------------------------------

describe("9 — ramp has finite valid geometry", () => {
  it("is a long, finite, in-extent centreline", () => {
    const ramp = rampCentreline(PIT);
    expect(ramp.length).toBeGreaterThan(60);
    for (const p of ramp) {
      expect(Number.isFinite(p.x)).toBe(true);
      expect(Number.isFinite(p.y)).toBe(true);
      expect(Number.isFinite(p.depthM)).toBe(true);
      expect(p.x).toBeGreaterThanOrEqual(0);
      expect(p.x).toBeLessThanOrEqual(CONFIG.widthM);
      expect(p.y).toBeGreaterThanOrEqual(0);
      expect(p.y).toBeLessThanOrEqual(CONFIG.heightM);
    }
  });

  it("is a switchback — the bearing reverses direction at least twice", () => {
    const ramp = rampCentreline(PIT);
    const bearings = ramp.map((p) => Math.atan2(p.y - PIT.centreY, p.x - PIT.centreX));
    let reversals = 0;
    let previousSign = 0;
    for (let i = 1; i < bearings.length; i += 1) {
      let delta = (bearings[i] ?? 0) - (bearings[i - 1] ?? 0);
      if (delta > Math.PI) delta -= TAU;
      if (delta < -Math.PI) delta += TAU;
      const sign = delta > 1e-4 ? 1 : delta < -1e-4 ? -1 : 0;
      if (sign !== 0 && previousSign !== 0 && sign !== previousSign) reversals += 1;
      if (sign !== 0) previousSign = sign;
    }
    expect(reversals).toBeGreaterThanOrEqual(2);
  });

  it("is not circular — its distance from the centre is not a monotonic spiral", () => {
    // A radial spiral shrinks its radius steadily. A switchback on an irregular wall
    // does not: it follows the rim shape and reverses.
    const ramp = rampCentreline(PIT);
    const radii = ramp.map((p) => Math.hypot(p.x - PIT.centreX, p.y - PIT.centreY));
    let increases = 0;
    for (let i = 1; i < radii.length; i += 1) {
      if ((radii[i] ?? 0) > (radii[i - 1] ?? 0)) increases += 1;
    }
    expect(increases).toBeGreaterThan(5);
  });
});

describe("10 — ramp has positive width", () => {
  it("has a positive, finite corridor width and a matching cut influence", () => {
    expect(PIT.rampWidthM).toBeGreaterThan(0);
    expect(rampInfluence(0, PIT)).toBe(1);
    expect(rampInfluence(PIT.rampWidthM / 2, PIT)).toBe(1);
    expect(rampInfluence(PIT.rampWidthM / 2 + 100, PIT)).toBe(0);
    const road = haulCorridors(CONFIG).find((r) => r.kind === "RAMP");
    expect(road?.widthM).toBe(PIT.rampWidthM);
  });
});

describe("11 — ramp connects multiple elevation levels", () => {
  it("descends from the surface to the floor through every bench level", () => {
    const ramp = rampCentreline(PIT);
    const first = ramp[0] as { depthM: number; u: number };
    const last = ramp[ramp.length - 1] as { depthM: number; u: number };
    expect(first.u).toBeLessThan(0);
    expect(first.depthM).toBe(0);
    expect(last.u).toBeCloseTo(1, 6);
    expect(last.depthM).toBeCloseTo(PIT.depthM, 6);

    const levels = new Set(ramp.map((p) => benchLevelAt(p.u, PIT)));
    expect(levels.size).toBe(PIT.benchCount + 1);
  });

  it("the terrain along the ramp is cut to a graded descent", () => {
    // Along the centreline, elevationAt follows the ramp profile: no riser-sized steps.
    const ramp = rampCentreline(PIT);
    const riser = PIT.depthM / PIT.benchCount;
    let worst = 0;
    for (let i = 1; i < ramp.length; i += 1) {
      const a = ramp[i - 1] as { x: number; y: number };
      const b = ramp[i] as { x: number; y: number };
      const drop = elevationAt(a.x, a.y, CONFIG) - elevationAt(b.x, b.y, CONFIG);
      if (drop > worst) worst = drop;
    }
    expect(worst).toBeLessThan(riser * 0.6);
  });

  it("off the ramp, the wall still steps", () => {
    // Pick a bearing far from the ramp and walk inward: risers are intact there.
    const riser = PIT.depthM / PIT.benchCount;
    const bearing = -1.9;
    let drops = 0;
    let previous = Number.NaN;
    for (let u = -0.05; u <= 1.05; u += 0.005) {
      const { x, y } = pointAt(bearing, u, PIT);
      const here = elevationAt(x, y, CONFIG);
      if (!Number.isNaN(previous) && previous - here >= riser * 0.5) drops += 1;
      previous = here;
    }
    expect(drops).toBeGreaterThanOrEqual(PIT.benchCount - 1);
  });
});

// ---------------------------------------------------------------------------
// 12–17. provenance and honesty
// ---------------------------------------------------------------------------

describe("12/13/14 — synthetic provenance, unverified, low confidence", () => {
  it("on the morphology record", () => {
    expect(MORPHOLOGY_PROVENANCE.source).toBe("SYNTHETIC_FOR_DEMO");
    expect(MORPHOLOGY_PROVENANCE.verified).toBe(false);
    expect(MORPHOLOGY_PROVENANCE.confidence).toBe("LOW");
  });

  it("on every derived feature and corridor", () => {
    for (const f of mineFeatures(CONFIG)) {
      expect(f.source, f.id).toBe("SYNTHETIC_FOR_DEMO");
      expect(f.verified, f.id).toBe(false);
      expect(f.confidence, f.id).toBe("LOW");
    }
    for (const r of haulCorridors(CONFIG)) {
      expect(r.source, r.id).toBe("SYNTHETIC_FOR_DEMO");
      expect(r.verified, r.id).toBe(false);
      expect(r.confidence, r.id).toBe("LOW");
    }
  });

  it("carries the disclosure", () => {
    expect(MORPHOLOGY_DISCLOSURE).toBe("SYNTHETIC MINE GEOMETRY · NOT SURVEYED");
    expect(MORPHOLOGY_PROVENANCE.disclosure).toBe(MORPHOLOGY_DISCLOSURE);
    expect(MORPHOLOGY_PROVENANCE.detail).toContain("not a reconstruction");
  });
});

describe("15/16/17 — nothing claims to be real", () => {
  it("no feature or corridor is labelled official, NMDC, surveyed or real", () => {
    const words = [
      ...mineFeatures(CONFIG).map((f) => `${f.id} ${f.label}`),
      ...haulCorridors(CONFIG).map((r) => `${r.id} ${r.label}`),
    ]
      .join(" ")
      .toUpperCase();
    for (const forbidden of ["OFFICIAL", "NMDC", "SURVEYED", "REAL ", "ACTUAL", "GPS"]) {
      expect(words, forbidden).not.toContain(forbidden);
    }
  });

  it("morphology elevations are relative synthetic metres, not real mine elevations", () => {
    // The floor is `depthM` BELOW a local datum of zero. No absolute altitude exists.
    expect(floorFeature(CONFIG).elevationM).toBe(-PIT.depthM);
    expect(pitFeature(CONFIG).elevationM).toBe(0);
    expect(MORPHOLOGY_PROVENANCE.detail.toUpperCase()).not.toContain("SEA LEVEL");
  });

  it("the morphology module never presents the real deposit as its source", () => {
    const text = source("pitMorphology.ts").toUpperCase();
    expect(text).not.toContain("SURVEYED PIT");
    expect(text).not.toContain("ACTUAL PIT");
    expect(text).not.toContain("REAL HAUL");
  });
});

// ---------------------------------------------------------------------------
// 18. published extent unchanged
// ---------------------------------------------------------------------------

describe("18 — published extent semantics are unchanged", () => {
  it("still says extent, not boundary, and is not the pit's source", () => {
    expect(MINECAST_SITE.extentLabel).toBe("PUBLISHED COORDINATE EXTENT");
    expect(MINECAST_SITE.extentCaveat).toBe("NOT A LEASE BOUNDARY");
    expect(MINECAST_SITE.coordinateReference).toBe("ASSUMED_WGS84_UNVERIFIED");
    // The pit shape is a function of the terrain config, not of any coordinate.
    expect(source("pitMorphology.ts")).not.toContain("DEPOSIT5_EXTENT");
    expect(source("pitMorphology.ts")).not.toContain("geoSite");
  });
});

// ---------------------------------------------------------------------------
// 19–23. Pass 3A untouched, no vehicle positions
// ---------------------------------------------------------------------------

const ISO = "2026-09-10T12:00:00Z";

function vehicle(id: string, overrides: Partial<VehicleState> = {}): VehicleState {
  return {
    vehicleId: id,
    mode: "NORMAL",
    vehicleKind: "DUMPER",
    speedMps: 4.2,
    position: { x: 0, y: 0, segmentId: null, offsetM: 0 },
    accelMps2: 0,
    gradeRad: 0,
    commConfidence: 1,
    frictionEst: null,
    routeId: null,
    timestamp: ISO,
    ...overrides,
  } as VehicleState;
}

function withOdometry(): VehicleState {
  return vehicle("TRUCK_01", {
    positionOdom: {
      xM: 42.5,
      yM: -18.25,
      headingRad: 0.62,
      distanceM: 137.5,
      timestamp: 1,
      source: "DERIVED",
      origin: "HARDWARE",
      provenanceLabel: "PHYSICAL_DERIVED",
      method: "WHEEL_IMU_ODOMETRY",
      status: "VALID",
      originType: "LOCAL_ODOMETRY",
    },
  } as Partial<VehicleState>);
}

function appState(vehicles: Record<string, VehicleState>): AppState {
  return {
    connection: {
      status: "CONNECTED",
      provider: "LIVE",
      scenarioName: null,
      lastMessageAt: ISO,
      error: null,
    },
    clock: { now: ISO, replayPosition: null },
    vehicles,
    safety: {},
    road: {},
    forecasts: {},
    bottlenecks: {},
    arrivals: {},
    slots: {},
    dispatch: {},
    alerts: [],
    events: [],
    health: null,
    kpis: null,
    cv: null,
    commands: [],
    observability: { status: "CURRENT", data: null, fetchedAt: ISO, error: null },
    topology: null,
  } as AppState;
}

describe("19/20/21 — T01 remains LOCAL_ODOMETRY and is not mapped onto the mine", () => {
  it("is still local, still not drawable, still without lonLat", () => {
    const projected = projectMineCastVehicle(
      appState({ TRUCK_01: withOdometry() }),
      "TRUCK_01",
      "LIVE",
    );
    const position = toSpatialPosition(projected, MINECAST_SITE);
    expect(position.provenance).toBe("LOCAL_ODOMETRY");
    expect(position.frame).toBe("ODOMETRY_LOCAL_METRES");
    expect(position.drawableInScene).toBe(false);
    expect(position.lonLat).toBeNull();
  });

  it("the morphology has no path that reads a vehicle", () => {
    const text = source("pitMorphology.ts");
    for (const forbidden of ["VehicleState", "AppState", "positionOdom", "TRUCK_01", "TRUCK_02"]) {
      expect(text, forbidden).not.toContain(forbidden);
    }
  });
});

describe("22 — T02 remains UNAVAILABLE", () => {
  it("has no spatial position", () => {
    const projected = projectMineCastVehicle(
      appState({ TRUCK_02: vehicle("TRUCK_02") }),
      "TRUCK_02",
      "LIVE",
    );
    const position = toSpatialPosition(projected, MINECAST_SITE);
    expect(position.provenance).toBe("UNAVAILABLE");
    expect(position.x).toBeNull();
  });
});

describe("23/24/25 — no vehicle positions, route state or safety state are generated", () => {
  it("the fleet is exactly as undrawable with the morphology as without", () => {
    const state = appState({ TRUCK_01: withOdometry(), TRUCK_02: vehicle("TRUCK_02") });
    const positions = spatialPositions(projectMineCast(state).vehicles, MINECAST_SITE);
    expect(drawablePositions(positions).length).toBe(0);
  });

  it("the morphology and feature modules mention no route or safety concept", () => {
    for (const name of ["pitMorphology.ts", "mineFeatures.ts"]) {
      const text = source(name);
      for (const forbidden of [
        "vSafe",
        "hSafe",
        "riskLevel",
        "routeId",
        "RouteState",
        "V2V",
        "V2I",
      ]) {
        expect(text, `${name} / ${forbidden}`).not.toContain(forbidden);
      }
    }
  });
});

// ---------------------------------------------------------------------------
// 26 + 27. read-only, no ingestion
// ---------------------------------------------------------------------------

describe("26/27 — read-only, no fetch or WebSocket", () => {
  it("the morphology module submits nothing and opens nothing", () => {
    const text = source("pitMorphology.ts");
    for (const forbidden of [
      "submitCommand",
      "commandClient",
      "fetch(",
      "WebSocket",
      "applyPatch",
    ]) {
      expect(text, forbidden).not.toContain(forbidden);
    }
  });
});

// ===========================================================================
// PASS 3B-M2 — benches as terraces, ramp as a road
// ===========================================================================

const SURFACES = benchSurfaces(CONFIG);
const SHELVES = surfacesOfKind(SURFACES, "SHELF");
const FACES = surfacesOfKind(SURFACES, "FACE");
const FLOOR_SURFACE = surfacesOfKind(SURFACES, "FLOOR_SURFACE")[0];
const RIBBON_RAMP = corridorsOfKind(haulCorridors(CONFIG), "RAMP")[0];

describe("3B-M2 benches — fewer, stronger terraces with real area", () => {
  it("uses 4-6 major benches, not a stack of thin rings", () => {
    expect(PIT.benchCount).toBeGreaterThanOrEqual(4);
    expect(PIT.benchCount).toBeLessThanOrEqual(6);
  });

  it("1. has multiple distinct bench elevations, each below the last", () => {
    const elevations = SHELVES.map((s) => s.topElevationM);
    expect(new Set(elevations).size).toBe(SHELVES.length);
    for (let i = 1; i < elevations.length; i += 1) {
      expect(elevations[i] ?? 0).toBeLessThan(elevations[i - 1] ?? 0);
    }
  });

  it("2. every bench shelf has nonzero surface area", () => {
    expect(SHELVES.length).toBe(PIT.benchCount - 1);
    for (const shelf of SHELVES) {
      // A shelf ~130 m wide around a ~1 km pit is well over 100 000 m2.
      expect(surfaceAreaM2(shelf), shelf.id).toBeGreaterThan(100_000);
      // And it is flat: top and bottom elevation are the same level.
      expect(shelf.topElevationM).toBe(shelf.bottomElevationM);
    }
  });

  it("3. every bench face has nonzero area and spans exactly one riser", () => {
    const riser = PIT.depthM / PIT.benchCount;
    expect(FACES.length).toBe(PIT.benchCount);
    for (const face of FACES) {
      expect(surfaceAreaM2(face), face.id).toBeGreaterThan(10_000);
      expect(face.topElevationM - face.bottomElevationM).toBeCloseTo(riser, 6);
      // The strip's own draped points actually step down across the riser.
      const strip = face.strips[0];
      const o = strip?.outer[0];
      const n = strip?.inner[0];
      expect((o?.elevationM ?? 0) - (n?.elevationM ?? 0)).toBeGreaterThan(riser * 0.5);
    }
  });

  it("4. shelves are not concentric copies — width varies around each bench", () => {
    // crestWidths(k) spans crest k to crest k+1; there are benchCount-1 crests.
    for (let k = 1; k < PIT.benchCount - 1; k += 1) {
      const widths = crestWidths(k);
      expect(Math.max(...widths) / Math.min(...widths), `bench ${k}`).toBeGreaterThan(1.4);
    }
  });

  it("5. bench segments vary deterministically across benches", () => {
    const signature = (surfaces: readonly { strips: readonly { outer: readonly unknown[] }[] }[]) =>
      surfaces.map((s) => s.strips.map((st) => st.outer.length).join(":"));
    const once = signature(SHELVES);
    const again = signature(surfacesOfKind(benchSurfaces(CONFIG), "SHELF"));
    expect(once).toEqual(again);
    // Not every shelf is cut into the same pieces.
    expect(new Set(once).size).toBeGreaterThan(1);
  });

  it("6. some bench shelves and faces are interrupted by the primary ramp", () => {
    const cutShelves = SHELVES.filter((s) => s.interrupted);
    const cutFaces = FACES.filter((f) => f.interrupted);
    expect(cutShelves.length).toBeGreaterThanOrEqual(2);
    expect(cutFaces.length).toBeGreaterThanOrEqual(3);
    for (const s of [...cutShelves, ...cutFaces]) {
      expect(s.strips.length, s.id).toBeGreaterThanOrEqual(2);
    }
  });

  it("the terrain shading separates a shelf from a face", () => {
    const grid = sampleHeightGrid(CONFIG);
    // Walk inward on a ramp-free bearing and collect slopes.
    let steepest = 0;
    let flattest = Number.POSITIVE_INFINITY;
    for (let u = 0.1; u <= 0.95; u += 0.01) {
      const { x, y } = pointAt(-1.9, u, PIT);
      const col = Math.round((x / CONFIG.widthM) * CONFIG.segments);
      const row = Math.round((y / CONFIG.heightM) * CONFIG.segments);
      const slope = slopeAt(grid, col, row);
      if (slope > steepest) steepest = slope;
      if (slope < flattest) flattest = slope;
    }
    expect(steepest).toBeGreaterThan(FACE_SLOPE_THRESHOLD);
    expect(flattest).toBeLessThan(FACE_SLOPE_THRESHOLD * 0.5);
    const shelf = terrainShade(0.5, 0);
    const face = terrainShade(0.5, steepest);
    expect(shelf[1] - face[1]).toBeGreaterThan(0.1);
    // Neutral: no channel dominates. Safety colours belong to a later pass.
    for (const shade of [shelf, face]) {
      expect(Math.abs(shade[0] - shade[2])).toBeLessThan(0.03);
    }
  });
});

describe("3B-M2 ramp — one primary haul ramp with width and surface", () => {
  it("7. the primary ramp exists, once", () => {
    expect(corridorsOfKind(haulCorridors(CONFIG), "RAMP").length).toBe(1);
    expect(RIBBON_RAMP?.id).toBe("SYNTH-PIT-RAMP-01");
  });

  it("8. has positive width - wide enough to draw as a road", () => {
    expect(RIBBON_RAMP?.widthM ?? 0).toBeGreaterThanOrEqual(30);
    expect(PIT.rampWidthM).toBe(RIBBON_RAMP?.widthM);
  });

  it("9. has nonzero surface area", () => {
    const ramp = RIBBON_RAMP;
    if (!ramp) throw new Error("ramp missing");
    const ribbon = corridorRibbon(ramp, 1, 0, (x, y) => elevationAt(x, y, CONFIG));
    let area = 0;
    const v = (i: number) => [
      ribbon.positions[i * 3] ?? 0,
      ribbon.positions[i * 3 + 1] ?? 0,
      ribbon.positions[i * 3 + 2] ?? 0,
    ];
    for (let i = 0; i < ribbon.indices.length; i += 3) {
      const a = v(ribbon.indices[i] ?? 0);
      const b = v(ribbon.indices[i + 1] ?? 0);
      const c = v(ribbon.indices[i + 2] ?? 0);
      const ux = (b[0] ?? 0) - (a[0] ?? 0);
      const uy = (b[1] ?? 0) - (a[1] ?? 0);
      const uz = (b[2] ?? 0) - (a[2] ?? 0);
      const vx = (c[0] ?? 0) - (a[0] ?? 0);
      const vy = (c[1] ?? 0) - (a[1] ?? 0);
      const vz = (c[2] ?? 0) - (a[2] ?? 0);
      area +=
        Math.hypot(uy * vz - uz * vy, uz * vx - ux * vz, ux * vy - uy * vx) / 2;
    }
    // ~3 km of 40 m road.
    expect(area).toBeGreaterThan(50_000);
  });

  it("10. contains multiple elevation levels", () => {
    const levels = new Set(
      (RIBBON_RAMP?.centreline ?? []).map((p) => benchLevelAt(inwardnessAt(p.x, p.y, PIT), PIT)),
    );
    expect(levels.size).toBe(PIT.benchCount + 1);
  });

  it("11. connects the surface, every bench level and the floor", () => {
    const ramp = rampCentreline(PIT);
    const first = ramp[0];
    const last = ramp[ramp.length - 1];
    expect(first?.u ?? 0).toBeLessThan(0);
    expect(last?.u ?? 0).toBeCloseTo(1, 6);
    // Its terrain elevation descends the whole pit depth.
    const drop = (RIBBON_RAMP?.startElevationM ?? 0) - (RIBBON_RAMP?.endElevationM ?? 0);
    expect(drop).toBeGreaterThan(PIT.depthM * 0.8);
  });

  it("12. is deterministic", () => {
    const a = JSON.stringify(corridorsOfKind(haulCorridors(CONFIG), "RAMP"));
    const b = JSON.stringify(corridorsOfKind(haulCorridors(CONFIG), "RAMP"));
    expect(a).toBe(b);
  });

  it("13. has finite coordinates everywhere, including the ribbon", () => {
    const ramp = RIBBON_RAMP;
    if (!ramp) throw new Error("ramp missing");
    const ribbon = corridorRibbon(ramp, 2.5, 4, (x, y) => elevationAt(x, y, CONFIG));
    for (const value of ribbon.positions) expect(Number.isFinite(value)).toBe(true);
    for (const p of ramp.centreline) {
      expect(Number.isFinite(p.x) && Number.isFinite(p.y) && Number.isFinite(p.elevationM)).toBe(
        true,
      );
    }
  });

  it("14. is not represented only by a line - the ribbon has triangles", () => {
    const ramp = RIBBON_RAMP;
    if (!ramp) throw new Error("ramp missing");
    const ribbon = corridorRibbon(ramp, 2.5, 4, (x, y) => elevationAt(x, y, CONFIG));
    expect(ribbon.indices.length).toBeGreaterThan(0);
    expect(ribbon.indices.length % 3).toBe(0);
    expect(ribbon.positions.length / 3).toBe(ramp.centreline.length * 2);
    // Left and right edges are genuinely apart by the road width.
    const lx = ribbon.leftEdge[0] ?? 0;
    const lz = ribbon.leftEdge[2] ?? 0;
    const rx = ribbon.rightEdge[0] ?? 0;
    const rz = ribbon.rightEdge[2] ?? 0;
    expect(Math.hypot(lx - rx, lz - rz)).toBeCloseTo(ramp.widthM, 6);
  });

  it("the ramp is cut into the bench faces, not floating above them", () => {
    // Where a face is interrupted, the terrain across the gap follows the ramp grade.
    const riser = PIT.depthM / PIT.benchCount;
    const ramp = RIBBON_RAMP?.centreline ?? [];
    for (let i = 1; i < ramp.length; i += 1) {
      const drop = (ramp[i - 1]?.elevationM ?? 0) - (ramp[i]?.elevationM ?? 0);
      expect(drop).toBeLessThan(riser * 0.6);
    }
  });
});

describe("3B-M2 pit floor", () => {
  it("17. is below the lowest bench and has real area", () => {
    const lowest = SHELVES[SHELVES.length - 1];
    expect(FLOOR_SURFACE?.topElevationM ?? 0).toBeLessThan(lowest?.topElevationM ?? 0);
    expect(surfaceAreaM2(FLOOR_SURFACE as (typeof SURFACES)[number])).toBeGreaterThan(150_000);
  });

  it("18. is not a small circular hole", () => {
    const radii: number[] = [];
    for (let i = 0; i < 72; i += 1) radii.push(floorRadiusAt((i / 72) * TAU, PIT));
    expect(Math.max(...radii) / Math.min(...radii)).toBeGreaterThan(2);
    expect(Math.min(...radii)).toBeGreaterThan(80);
  });
});

describe("3B-M2 provenance on every surface", () => {
  it("19-21. every shelf, face and floor surface is SYNTHETIC_FOR_DEMO, unverified, LOW", () => {
    expect(SURFACES.length).toBe(PIT.benchCount * 2);
    for (const s of SURFACES) {
      expect(s.source, s.id).toBe("SYNTHETIC_FOR_DEMO");
      expect(s.verified, s.id).toBe(false);
      expect(s.confidence, s.id).toBe("LOW");
      expect(s.label.toLowerCase()).toContain("synthetic");
    }
  });

  it("22-23. no surface claims official, surveyed or engineering status", () => {
    const text = JSON.stringify(SURFACES.map((s) => [s.id, s.label]))
      .toUpperCase();
    for (const banned of ["NMDC", "OFFICIAL", "SURVEYED", "ENGINEERING", "REAL", "GPS", "DEPOSIT"]) {
      expect(text, banned).not.toContain(banned);
    }
  });
});
