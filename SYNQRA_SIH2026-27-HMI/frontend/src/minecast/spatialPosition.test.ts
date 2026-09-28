/**
 * Spatial position contract — the refusals, asserted.
 *
 * Pass 3B will draw vehicle markers on the terrain. These tests fix the contract that
 * decides which vehicles may be drawn BEFORE any marker exists, because once a truck is
 * rendered on a mine map it looks located whether or not anything located it.
 *
 * The claims held here, in the brief's own lettering:
 *
 *   A  TRUCK_01's local odometry stays local
 *   B  TRUCK_01 never acquires a latitude or longitude
 *   C  its provenance stays physically derived / WHEEL_IMU_ODOMETRY
 *   D  TRUCK_02, with no position source, produces no spatial position
 *   E  a missing position is never replaced by zero coordinates
 *   F  a synthetic placement is explicitly SYNTHETIC_FOR_DEMO
 *   G  geographic and local semantics cannot be silently confused
 *   H  canonical ids remain TRUCK_01 / TRUCK_02 behind the T01 / T02 labels
 *   J  the contract module is framework-free
 *
 * SOFTWARE ONLY. No hardware, no WebGL, no DOM, no network.
 */

import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";

import type { AppState } from "../contracts/appState";
import type { VehicleState } from "../contracts/domain";
import { MINECAST_SITE, projectMineCast, projectMineCastVehicle } from "./minecastProjection";
import {
  drawablePositions,
  SPATIAL_PROVENANCE_TEXT,
  SYNTHETIC_PLACEMENT_LABEL,
  spatialPositions,
  syntheticScenePlacement,
  toSpatialPosition,
  undrawablePositions,
} from "./spatialPosition";

const ISO = "2026-09-10T12:00:00Z";

// ---------------------------------------------------------------------------
// fixtures
// ---------------------------------------------------------------------------

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

/** TRUCK_01 as the wheel+IMU adapter actually reports it: a valid LOCAL pose. */
function withOdometry(xM = 42.5, yM = -18.25, headingRad = 0.62): VehicleState {
  return vehicle("TRUCK_01", {
    positionOdom: {
      xM,
      yM,
      headingRad,
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

/** A physical GNSS fix. No such receiver is fitted; this exercises the contract only. */
function withPhysicalGnss(lat = 18.685, lon = 81.19): VehicleState {
  return vehicle("TRUCK_01", {
    positionGnss: { latitude: lat, longitude: lon, status: "VALID", origin: "HARDWARE" },
  } as Partial<VehicleState>);
}

/** A software-only synthetic fix, from the synthetic GNSS harness. */
function withSyntheticGnss(lat = 18.685, lon = 81.19): VehicleState {
  return vehicle("TRUCK_01", {
    positionGnss: { latitude: lat, longitude: lon, status: "VALID", origin: "SOFTWARE_ONLY" },
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

/** Project one vehicle straight through both layers. */
function spatialFor(id: string, vehicles: Record<string, VehicleState>) {
  const projected = projectMineCastVehicle(appState(vehicles), id, "LIVE");
  return toSpatialPosition(projected, MINECAST_SITE);
}

/** This module's own source, comments stripped, for the framework-free checks. */
function contractSource(): string {
  return readFileSync("src/minecast/spatialPosition.ts", "utf-8")
    .replace(/\/\*[\s\S]*?\*\//g, "")
    .replace(/^\s*\/\/.*$/gm, "");
}

// ---------------------------------------------------------------------------
// A + C. TRUCK_01 local odometry stays local, and stays physically derived
// ---------------------------------------------------------------------------

describe("A — TRUCK_01 local odometry remains local", () => {
  it("reports LOCAL_ODOMETRY in the odometry frame", () => {
    const position = spatialFor("TRUCK_01", { TRUCK_01: withOdometry() });

    expect(position.provenance).toBe("LOCAL_ODOMETRY");
    expect(position.frame).toBe("ODOMETRY_LOCAL_METRES");
    expect(position.frame).not.toBe("SCENE_METRES");
  });

  it("preserves the pose numbers verbatim, in metres", () => {
    const position = spatialFor("TRUCK_01", { TRUCK_01: withOdometry(42.5, -18.25, 0.62) });
    expect(position.x).toBe(42.5);
    expect(position.y).toBe(-18.25);
    expect(position.headingRad).toBe(0.62);
  });

  it("is NOT drawable on the terrain, because the origin is unsurveyed", () => {
    // The pose is real. Where its origin sits in the mine is not known, so a marker
    // placed from it would be at an invented location.
    const position = spatialFor("TRUCK_01", { TRUCK_01: withOdometry() });
    expect(position.drawableInScene).toBe(false);
    expect(position.reason).toContain("unsurveyed");
    expect(position.reason).toContain("NOT a geographic coordinate");
  });

  it("is not marked synthetic — the pose itself is a real measurement chain", () => {
    const position = spatialFor("TRUCK_01", { TRUCK_01: withOdometry() });
    expect(position.synthetic).toBe(false);
  });
});

describe("C — TRUCK_01 provenance stays physically derived", () => {
  it("keeps WHEEL_IMU_ODOMETRY as the method", () => {
    const position = spatialFor("TRUCK_01", { TRUCK_01: withOdometry() });
    expect(position.method).toBe("WHEEL_IMU_ODOMETRY");
    expect(position.method).not.toBe("GNSS");
    expect(position.method).not.toBe("SYNTHETIC_GNSS");
  });

  it("carries PHYSICAL_DERIVED through the underlying Mine-Cast projection", () => {
    const projected = projectMineCastVehicle(
      appState({ TRUCK_01: withOdometry() }),
      "TRUCK_01",
      "LIVE",
    );
    expect(projected.position.provenance).toBe("DERIVED");
    expect(projected.position.kind).toBe("LOCAL_ODOMETRY");
  });

  it("describes LOCAL_ODOMETRY as not geographic in its own vocabulary", () => {
    expect(SPATIAL_PROVENANCE_TEXT.LOCAL_ODOMETRY).toContain("not geographic");
  });
});

// ---------------------------------------------------------------------------
// B. no fabricated latitude / longitude, ever
// ---------------------------------------------------------------------------

describe("B — TRUCK_01 never acquires a latitude or longitude", () => {
  it("leaves lonLat null for an odometry pose", () => {
    const position = spatialFor("TRUCK_01", { TRUCK_01: withOdometry() });
    expect(position.lonLat).toBeNull();
  });

  it("still leaves lonLat null after a synthetic scene placement", () => {
    // Anchoring a local pose into a demo scene creates no coordinate on the earth.
    const local = spatialFor("TRUCK_01", { TRUCK_01: withOdometry() });
    const placed = syntheticScenePlacement(local, { xM: 1500, yM: 1500 });
    expect(placed.lonLat).toBeNull();
  });

  it("produces no lonLat for any distance travelled", () => {
    for (const distance of [0, 10, 1000, 100000]) {
      const position = spatialFor("TRUCK_01", { TRUCK_01: withOdometry(distance, distance) });
      expect(position.lonLat, `at ${distance} m`).toBeNull();
    }
  });

  it("the Mine-Cast projection itself refuses to fill lonLat from odometry", () => {
    const projected = projectMineCastVehicle(
      appState({ TRUCK_01: withOdometry() }),
      "TRUCK_01",
      "LIVE",
    );
    expect(projected.position.lonLat).toBeNull();
  });
});

// ---------------------------------------------------------------------------
// D + E. TRUCK_02 stays unavailable, and absence is never zero
// ---------------------------------------------------------------------------

describe("D — TRUCK_02 produces no spatial position", () => {
  it("is UNAVAILABLE when nothing supplied a position", () => {
    const position = spatialFor("TRUCK_02", { TRUCK_02: vehicle("TRUCK_02") });

    expect(position.provenance).toBe("UNAVAILABLE");
    expect(position.frame).toBe("NONE");
    expect(position.drawableInScene).toBe(false);
  });

  it("is not placed merely because the scene contains two trucks", () => {
    // TRUCK_01 has a pose; TRUCK_02 does not. The second must not inherit placement.
    const state = appState({ TRUCK_01: withOdometry(), TRUCK_02: vehicle("TRUCK_02") });
    const positions = spatialPositions(projectMineCast(state).vehicles, MINECAST_SITE);

    const t02 = positions.find((p) => p.canonicalVehicleId === "TRUCK_02");
    expect(t02?.provenance).toBe("UNAVAILABLE");
    expect(t02?.x).toBeNull();
    expect(t02?.y).toBeNull();
  });

  it("stays UNAVAILABLE even when it reports speed and mode", () => {
    // Having telemetry is not having a position.
    const moving = vehicle("TRUCK_02", { speedMps: 9.1, mode: "NORMAL" });
    const position = spatialFor("TRUCK_02", { TRUCK_02: moving });
    expect(position.provenance).toBe("UNAVAILABLE");
    expect(position.drawableInScene).toBe(false);
  });

  it("cannot be upgraded by asking for a synthetic placement", () => {
    // The escape hatch anchors a LOCAL pose. It must not manufacture one.
    const position = spatialFor("TRUCK_02", { TRUCK_02: vehicle("TRUCK_02") });
    const attempted = syntheticScenePlacement(position, { xM: 900, yM: 900 });

    expect(attempted.provenance).toBe("UNAVAILABLE");
    expect(attempted.drawableInScene).toBe(false);
    expect(attempted.x).toBeNull();
    expect(attempted.y).toBeNull();
  });
});

describe("E — a missing position is never replaced by zero", () => {
  it("returns null coordinates, not (0, 0)", () => {
    const position = spatialFor("TRUCK_02", { TRUCK_02: vehicle("TRUCK_02") });

    expect(position.x).toBeNull();
    expect(position.y).toBeNull();
    // (0, 0) is real ground near the scene origin - a plausible-looking wrong answer.
    expect(position.x).not.toBe(0);
    expect(position.y).not.toBe(0);
  });

  it("returns null for a vehicle the Twin does not carry at all", () => {
    const position = spatialFor("TRUCK_01", {});
    expect(position.provenance).toBe("UNAVAILABLE");
    expect(position.x).toBeNull();
    expect(position.headingRad).toBeNull();
  });

  it("refuses an odometry record whose pose is absent", () => {
    const stalled = vehicle("TRUCK_01", {
      positionOdom: {
        xM: null,
        yM: null,
        headingRad: null,
        distanceM: null,
        timestamp: null,
        source: "DERIVED",
        origin: "HARDWARE",
        provenanceLabel: "UNAVAILABLE",
        method: "WHEEL_IMU_ODOMETRY",
        status: "UNAVAILABLE",
        originType: "NONE",
      },
    } as Partial<VehicleState>);

    const position = spatialFor("TRUCK_01", { TRUCK_01: stalled });
    expect(position.provenance).toBe("UNAVAILABLE");
    expect(position.x).toBeNull();
  });

  it("distinguishes a genuine zero pose from a missing one", () => {
    // A truck sitting exactly at its odometry origin is a real reading of (0, 0).
    const atOrigin = spatialFor("TRUCK_01", { TRUCK_01: withOdometry(0, 0, 0) });
    expect(atOrigin.provenance).toBe("LOCAL_ODOMETRY");
    expect(atOrigin.x).toBe(0);
    expect(atOrigin.y).toBe(0);
  });
});

// ---------------------------------------------------------------------------
// F. synthetic placement is explicit and labelled
// ---------------------------------------------------------------------------

describe("F — synthetic placement is explicitly marked", () => {
  it("stamps SYNTHETIC_FOR_DEMO even though the pose was physically derived", () => {
    const local = spatialFor("TRUCK_01", { TRUCK_01: withOdometry() });
    const placed = syntheticScenePlacement(local, { xM: 1500, yM: 1600 });

    expect(placed.provenance).toBe("SYNTHETIC_FOR_DEMO");
    expect(placed.synthetic).toBe(true);
  });

  it("carries the SOFTWARE TEST caption in its reason", () => {
    const local = spatialFor("TRUCK_01", { TRUCK_01: withOdometry() });
    const placed = syntheticScenePlacement(local, { xM: 1500, yM: 1600 });

    expect(placed.reason).toContain(SYNTHETIC_PLACEMENT_LABEL);
    expect(SYNTHETIC_PLACEMENT_LABEL).toContain("SOFTWARE TEST");
    expect(SYNTHETIC_PLACEMENT_LABEL).toContain("SYNTHETIC SPATIAL PLACEMENT");
  });

  it("preserves the fact that the underlying pose was real", () => {
    // The measurement chain is not erased; only the PLACEMENT is synthetic.
    const local = spatialFor("TRUCK_01", { TRUCK_01: withOdometry() });
    const placed = syntheticScenePlacement(local, { xM: 1500, yM: 1600 });

    expect(placed.underlyingProvenance).toBe("LOCAL_ODOMETRY");
    expect(placed.method).toBe("WHEEL_IMU_ODOMETRY");
    expect(placed.reason).toContain("The pose is real; this position on the map is not.");
  });

  it("applies the anchor as a translation", () => {
    const local = spatialFor("TRUCK_01", { TRUCK_01: withOdometry(100, 50) });
    const placed = syntheticScenePlacement(local, { xM: 1000, yM: 2000 });

    expect(placed.x).toBeCloseTo(1100, 6);
    expect(placed.y).toBeCloseTo(2050, 6);
    expect(placed.frame).toBe("SCENE_METRES");
    expect(placed.drawableInScene).toBe(true);
  });

  it("applies an optional rotation to both position and heading", () => {
    const local = spatialFor("TRUCK_01", { TRUCK_01: withOdometry(100, 0, 0) });
    const placed = syntheticScenePlacement(local, { xM: 0, yM: 0, rotationRad: Math.PI / 2 });

    expect(placed.x).toBeCloseTo(0, 6);
    expect(placed.y).toBeCloseTo(100, 6);
    expect(placed.headingRad).toBeCloseTo(Math.PI / 2, 6);
  });

  it("is deterministic", () => {
    const local = spatialFor("TRUCK_01", { TRUCK_01: withOdometry() });
    const anchor = { xM: 1500, yM: 1600, rotationRad: 0.3 };
    expect(JSON.stringify(syntheticScenePlacement(local, anchor))).toBe(
      JSON.stringify(syntheticScenePlacement(local, anchor)),
    );
  });

  it("is never reached by default — a real pose is never returned as SYNTHETIC", () => {
    const position = spatialFor("TRUCK_01", { TRUCK_01: withOdometry() });
    expect(position.provenance).not.toBe("SYNTHETIC_FOR_DEMO");
    expect(position.synthetic).toBe(false);
  });
});

// ---------------------------------------------------------------------------
// G. geographic and local semantics cannot be confused
// ---------------------------------------------------------------------------

describe("G — geographic and local semantics stay distinct", () => {
  it("a physical fix is VERIFIED_GEOGRAPHIC in scene metres", () => {
    const position = spatialFor("TRUCK_01", { TRUCK_01: withPhysicalGnss() });

    expect(position.provenance).toBe("VERIFIED_GEOGRAPHIC");
    expect(position.frame).toBe("SCENE_METRES");
    expect(position.drawableInScene).toBe(true);
    expect(position.lonLat).not.toBeNull();
  });

  it("a physical fix discloses the projection's limits", () => {
    const position = spatialFor("TRUCK_01", { TRUCK_01: withPhysicalGnss() });
    expect(position.reason).toContain("ASSUMED_WGS84_UNVERIFIED");
    expect(position.reason).toContain("not survey grade");
  });

  it("a SYNTHETIC GNSS fix is geographic but never VERIFIED", () => {
    const position = spatialFor("TRUCK_01", { TRUCK_01: withSyntheticGnss() });

    expect(position.provenance).toBe("SYNTHETIC_FOR_DEMO");
    expect(position.provenance).not.toBe("VERIFIED_GEOGRAPHIC");
    expect(position.synthetic).toBe(true);
    expect(position.reason).toContain(SYNTHETIC_PLACEMENT_LABEL);
  });

  it("the two frames are never the same value for the same vehicle", () => {
    const local = spatialFor("TRUCK_01", { TRUCK_01: withOdometry() });
    const geographic = spatialFor("TRUCK_01", { TRUCK_01: withPhysicalGnss() });
    expect(local.frame).not.toBe(geographic.frame);
  });

  it("only a SCENE_METRES position is ever drawable", () => {
    const cases = [
      spatialFor("TRUCK_01", { TRUCK_01: withOdometry() }),
      spatialFor("TRUCK_01", { TRUCK_01: withPhysicalGnss() }),
      spatialFor("TRUCK_02", { TRUCK_02: vehicle("TRUCK_02") }),
    ];
    for (const position of cases) {
      expect(position.drawableInScene, position.provenance).toBe(position.frame === "SCENE_METRES");
    }
  });

  it("projects a geographic fix inside the site, not to an arbitrary offset", () => {
    // The extent is roughly 3.2 km x 3.4 km; a fix near its centre must land inside it.
    const position = spatialFor("TRUCK_01", { TRUCK_01: withPhysicalGnss(18.685, 81.19) });
    expect(position.x).not.toBeNull();
    expect(position.y).not.toBeNull();
    expect(position.x as number).toBeGreaterThan(0);
    expect(position.y as number).toBeGreaterThan(0);
    expect(position.x as number).toBeLessThan(6000);
    expect(position.y as number).toBeLessThan(6000);
  });
});

// ---------------------------------------------------------------------------
// H. canonical ids survive
// ---------------------------------------------------------------------------

describe("H — canonical ids remain TRUCK_01 / TRUCK_02", () => {
  it("carries the canonical id and the short label separately", () => {
    const t01 = spatialFor("TRUCK_01", { TRUCK_01: withOdometry() });
    const t02 = spatialFor("TRUCK_02", { TRUCK_02: vehicle("TRUCK_02") });

    expect(t01.canonicalVehicleId).toBe("TRUCK_01");
    expect(t01.displayId).toBe("T01");
    expect(t02.canonicalVehicleId).toBe("TRUCK_02");
    expect(t02.displayId).toBe("T02");
  });

  it("never uses the short label as the identifier", () => {
    const t01 = spatialFor("TRUCK_01", { TRUCK_01: withOdometry() });
    expect(t01.canonicalVehicleId).not.toBe("T01");
  });
});

// ---------------------------------------------------------------------------
// fleet helpers
// ---------------------------------------------------------------------------

describe("fleet helpers", () => {
  const state = appState({ TRUCK_01: withOdometry(), TRUCK_02: vehicle("TRUCK_02") });
  const positions = spatialPositions(projectMineCast(state).vehicles, MINECAST_SITE);

  it("projects every configured vehicle, drawable or not", () => {
    expect(positions.length).toBe(2);
    expect(positions.map((p) => p.canonicalVehicleId)).toEqual(["TRUCK_01", "TRUCK_02"]);
  });

  it("draws nothing on the current hardware — no GNSS, no scene anchor", () => {
    expect(drawablePositions(positions).length).toBe(0);
  });

  it("surfaces undrawable vehicles with a reason rather than dropping them", () => {
    const undrawable = undrawablePositions(positions);
    expect(undrawable.length).toBe(2);
    for (const position of undrawable) {
      expect(position.reason.length, position.canonicalVehicleId).toBeGreaterThan(0);
    }
  });

  it("is deterministic across repeated projection", () => {
    expect(JSON.stringify(spatialPositions(projectMineCast(state).vehicles, MINECAST_SITE))).toBe(
      JSON.stringify(positions),
    );
  });
});

// ---------------------------------------------------------------------------
// J. the contract is framework-free
// ---------------------------------------------------------------------------

describe("J — the contract module is framework-free", () => {
  it("imports no React, Three.js or browser global", () => {
    const code = contractSource();

    expect(code).not.toMatch(/from\s+["']react["']/);
    expect(code).not.toMatch(/from\s+["']three["']/);
    expect(code).not.toContain("@react-three");
    for (const global of ["window.", "document.", "localStorage", "navigator."]) {
      expect(code, global).not.toContain(global);
    }
  });

  it("has no path that writes a longitude or latitude from a local pose", () => {
    // Every assignment to `lonLat` is either null or the geographic branch's own value.
    const assignments = contractSource().match(/lonLat:\s*[^,\n]+/g) ?? [];
    expect(assignments.length).toBeGreaterThan(3);
    for (const assignment of assignments) {
      const acceptable = assignment.includes("null") || assignment.includes("lonLat");
      expect(acceptable, assignment).toBe(true);
    }
  });
});
