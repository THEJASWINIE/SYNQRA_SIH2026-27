/**
 * Synthetic operational corridors — geometry and honesty, asserted.
 *
 * A road drawn on a mine map looks like a road that exists. These tests hold that every
 * corridor is stamped as invented, is generated deterministically, sits on the SAME
 * synthetic terrain as everything else, and - critically - that adding a road network
 * changed nothing about which vehicles may be drawn: TRUCK_01 is still local-only and
 * TRUCK_02 is still unavailable.
 *
 * Numbering follows the Pass 3B brief.
 *
 * SOFTWARE ONLY. No hardware, no WebGL, no DOM, no network.
 */

import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";

import type { AppState } from "../contracts/appState";
import type { VehicleState } from "../contracts/domain";
import {
  CORRIDOR_DISCLOSURE,
  CORRIDOR_PROVENANCE,
  corridorRibbon,
  corridorsOfKind,
  haulCorridors,
} from "./haulRoads";
import {
  LAYERS,
  MINECAST_SITE,
  projectMineCast,
  projectMineCastVehicle,
} from "./minecastProjection";
import { initialViewState, minecastReducer } from "./minecastStore";
import { drawablePositions, spatialPositions, toSpatialPosition } from "./spatialPosition";
import {
  elevationAt,
  gridElevationAt,
  sampleHeightGrid,
  terrainConfig,
  VERTICAL_EXAGGERATION,
} from "./terrainField";

const CONFIG = terrainConfig(3200, 3400);
const ROADS = haulCorridors(CONFIG);
/** The continuous field, as a sampler. */
const FIELD = (x: number, y: number) => elevationAt(x, y, CONFIG);

/** The module's own source, comments stripped. */
function roadSource(): string {
  return readFileSync("src/minecast/haulRoads.ts", "utf-8")
    .replace(/\/\*[\s\S]*?\*\//g, "")
    .replace(/^\s*\/\/.*$/gm, "");
}

// ---------------------------------------------------------------------------
// 1 + 2. deterministic, stable ids
// ---------------------------------------------------------------------------

describe("1 — road generation is deterministic", () => {
  it("produces byte-identical output on repeated calls", () => {
    expect(JSON.stringify(haulCorridors(CONFIG))).toBe(JSON.stringify(haulCorridors(CONFIG)));
  });

  it("produces byte-identical output for an equal but separately built config", () => {
    expect(JSON.stringify(haulCorridors(terrainConfig(3200, 3400)))).toBe(JSON.stringify(ROADS));
  });

  it("changes with the site dimensions, so it is a function of the config not a constant", () => {
    const other = haulCorridors(terrainConfig(1600, 1700));
    expect(JSON.stringify(other)).not.toBe(JSON.stringify(ROADS));
  });
});

describe("2 — road ids are stable", () => {
  it("uses the documented ids", () => {
    expect(ROADS.map((r) => r.id)).toEqual([
      "SYNTH-HAUL-MAIN",
      "SYNTH-PIT-RAMP-01",
      "SYNTH-LOADING-LOOP-01",
      "SYNTH-ORE-DISPATCH-01",
      "SYNTH-SERVICE-01",
    ]);
  });

  it("keeps the same ids for a different site size", () => {
    const other = haulCorridors(terrainConfig(1600, 1700));
    expect(other.map((r) => r.id)).toEqual(ROADS.map((r) => r.id));
  });

  it("has no duplicate ids", () => {
    expect(new Set(ROADS.map((r) => r.id)).size).toBe(ROADS.length);
  });
});

// ---------------------------------------------------------------------------
// 3 + 4 + 5. finite coordinates, positive widths, finite elevations
// ---------------------------------------------------------------------------

describe("3 — every coordinate is finite", () => {
  it("has no NaN or infinity in any centreline", () => {
    for (const road of ROADS) {
      expect(road.centreline.length, road.id).toBeGreaterThanOrEqual(2);
      for (const point of road.centreline) {
        expect(Number.isFinite(point.x), `${road.id} x`).toBe(true);
        expect(Number.isFinite(point.y), `${road.id} y`).toBe(true);
      }
    }
  });

  it("stays inside the site extent", () => {
    for (const road of ROADS) {
      for (const point of road.centreline) {
        expect(point.x, road.id).toBeGreaterThanOrEqual(0);
        expect(point.x, road.id).toBeLessThanOrEqual(CONFIG.widthM);
        expect(point.y, road.id).toBeGreaterThanOrEqual(0);
        expect(point.y, road.id).toBeLessThanOrEqual(CONFIG.heightM);
      }
    }
  });
});

describe("4 — every width is positive", () => {
  it("has a positive finite width on every corridor", () => {
    for (const road of ROADS) {
      expect(Number.isFinite(road.widthM), road.id).toBe(true);
      expect(road.widthM, road.id).toBeGreaterThan(0);
    }
  });

  it("makes the main haul wider than a branch", () => {
    const main = corridorsOfKind(ROADS, "MAIN_HAUL")[0];
    const branch = corridorsOfKind(ROADS, "DISPATCH")[0];
    expect(main?.widthM ?? 0).toBeGreaterThan(branch?.widthM ?? Number.POSITIVE_INFINITY);
  });
});

describe("5 — every elevation is finite", () => {
  it("has finite elevations at every point and at both ends", () => {
    for (const road of ROADS) {
      for (const point of road.centreline) {
        expect(Number.isFinite(point.elevationM), road.id).toBe(true);
      }
      expect(Number.isFinite(road.startElevationM), road.id).toBe(true);
      expect(Number.isFinite(road.endElevationM), road.id).toBe(true);
    }
  });

  it("drapes every point on the SAME terrain function the mesh is built from", () => {
    // No second elevation model: a road point's elevation IS elevationAt(x, y).
    for (const road of ROADS) {
      for (const point of road.centreline) {
        expect(point.elevationM, road.id).toBe(elevationAt(point.x, point.y, CONFIG));
      }
    }
  });

  it("the ramp descends into the pit", () => {
    const ramp = corridorsOfKind(ROADS, "RAMP")[0];
    expect(ramp).toBeDefined();
    expect(ramp?.endElevationM ?? 0).toBeLessThan(
      ramp?.startElevationM ?? Number.NEGATIVE_INFINITY,
    );
    // Most of the configured pit depth is realised along the ramp.
    expect((ramp?.startElevationM ?? 0) - (ramp?.endElevationM ?? 0)).toBeGreaterThan(
      CONFIG.pitDepthM * 0.6,
    );
  });

  it("the ramp is a graded descent cut THROUGH the benches, not a staircase on top", () => {
    /*
      Pass 3B-M: the terrain is cut along the ramp, so its centreline elevation descends
      smoothly through every bench level instead of stepping. No consecutive pair of
      points may drop by anything like a full riser, and the descent must span at least
      three bench levels.
    */
    const ramp = corridorsOfKind(ROADS, "RAMP")[0];
    const points = ramp?.centreline ?? [];
    const riser = CONFIG.pitDepthM / CONFIG.benchCount;
    let worstDrop = 0;
    for (let i = 1; i < points.length; i += 1) {
      const drop = (points[i - 1]?.elevationM ?? 0) - (points[i]?.elevationM ?? 0);
      if (drop > worstDrop) worstDrop = drop;
    }
    expect(worstDrop).toBeLessThan(riser * 0.6);
    const levelsSpanned = ((ramp?.startElevationM ?? 0) - (ramp?.endElevationM ?? 0)) / riser;
    expect(levelsSpanned).toBeGreaterThanOrEqual(3);
  });

  it("stores TRUE metres, with exaggeration applied only by the ribbon builder", () => {
    const ramp = corridorsOfKind(ROADS, "RAMP")[0] as (typeof ROADS)[number];
    const ribbon = corridorRibbon(ramp, VERTICAL_EXAGGERATION, 0, FIELD);
    // The right-edge y of the last point is the field at that edge, exaggerated.
    const rx = ribbon.rightEdge[ribbon.rightEdge.length - 3] as number;
    const rz = ribbon.rightEdge[ribbon.rightEdge.length - 1] as number;
    const lastY = ribbon.positions[ribbon.positions.length - 2] as number;
    expect(lastY).toBeCloseTo(FIELD(rx, rz) * VERTICAL_EXAGGERATION, 6);
  });
});

// ---------------------------------------------------------------------------
// 6 + 7 + 8 + 9. provenance and labelling
// ---------------------------------------------------------------------------

describe("6 — every road has synthetic provenance", () => {
  it("is SYNTHETIC_FOR_DEMO on every corridor", () => {
    for (const road of ROADS) expect(road.source, road.id).toBe("SYNTHETIC_FOR_DEMO");
    expect(CORRIDOR_PROVENANCE.source).toBe("SYNTHETIC_FOR_DEMO");
  });

  it("labels each corridor as synthetic in its own words", () => {
    for (const road of ROADS) expect(road.label.toLowerCase(), road.id).toContain("synthetic");
  });
});

describe("7 — every road is explicitly unverified", () => {
  it("is verified === false with LOW confidence, everywhere", () => {
    for (const road of ROADS) {
      expect(road.verified, road.id).toBe(false);
      expect(road.confidence, road.id).toBe("LOW");
    }
    expect(CORRIDOR_PROVENANCE.verified).toBe(false);
    expect(CORRIDOR_PROVENANCE.confidence).toBe("LOW");
  });
});

describe("8 — every road is an operational corridor", () => {
  it("is classified OPERATIONAL_CORRIDOR", () => {
    for (const road of ROADS) {
      expect(road.classification, road.id).toBe("OPERATIONAL_CORRIDOR");
    }
    expect(CORRIDOR_PROVENANCE.classification).toBe("OPERATIONAL_CORRIDOR");
  });

  it("covers the required kinds: main haul, ramp, and at least one branch", () => {
    expect(corridorsOfKind(ROADS, "MAIN_HAUL").length).toBeGreaterThanOrEqual(1);
    expect(corridorsOfKind(ROADS, "RAMP").length).toBeGreaterThanOrEqual(1);
    expect(corridorsOfKind(ROADS, "DISPATCH").length).toBeGreaterThanOrEqual(1);
  });
});

describe("9 — no road is labelled official, NMDC or surveyed", () => {
  const FORBIDDEN = [
    "NMDC ROAD",
    "OFFICIAL",
    "SURVEYED ROAD",
    "REAL HAUL",
    "GPS",
    "AUTHORITATIVE",
    "DEPOSIT-5 ROAD",
  ];

  it("uses none of the forbidden words in any id or label", () => {
    for (const road of ROADS) {
      const words = `${road.id} ${road.label}`.toUpperCase();
      for (const forbidden of FORBIDDEN) {
        expect(words, `${road.id} / ${forbidden}`).not.toContain(forbidden);
      }
    }
  });

  it("carries the concise disclosure", () => {
    expect(CORRIDOR_DISCLOSURE).toBe("SYNTHETIC OPERATIONAL CORRIDORS · NOT NMDC INFRASTRUCTURE");
    expect(CORRIDOR_PROVENANCE.disclosure).toBe(CORRIDOR_DISCLOSURE);
    expect(CORRIDOR_PROVENANCE.detail).toContain("No surveyed Deposit-5 road geometry");
    expect(CORRIDOR_PROVENANCE.detail).toContain("not real mine elevations");
  });
});

// ---------------------------------------------------------------------------
// 10. no Math.random
// ---------------------------------------------------------------------------

describe("10 — no Math.random is used", () => {
  it("the module source contains no call to Math.random", () => {
    expect(roadSource()).not.toContain("Math.random");
  });

  it("the terrain it drapes on contains none either", () => {
    const terrain = readFileSync("src/minecast/terrainField.ts", "utf-8")
      .replace(/\/\*[\s\S]*?\*\//g, "")
      .replace(/^\s*\/\/.*$/gm, "");
    expect(terrain).not.toContain("Math.random");
  });
});

// ---------------------------------------------------------------------------
// 11 + 12. roads are separate from vehicle state, and create no positions
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

describe("11 — road geometry is separate from canonical vehicle state", () => {
  it("haulCorridors takes only terrain config, never AppState or a vehicle", () => {
    // The signature is the proof: there is no parameter through which a vehicle could
    // reach the generator, and no import of the Twin contracts.
    const source = roadSource();
    expect(source).not.toContain("AppState");
    expect(source).not.toContain("VehicleState");
    expect(source).not.toContain("projectVehicle");
    expect(source).not.toContain("vehicleProjection");
  });

  it("the corridor type carries no vehicle field", () => {
    for (const road of ROADS) {
      const keys = Object.keys(road);
      for (const forbidden of ["vehicleId", "vehicle", "assignedVehicle", "position", "speed"]) {
        expect(keys, `${road.id} / ${forbidden}`).not.toContain(forbidden);
      }
    }
  });
});

describe("12 — road generation creates no vehicle positions", () => {
  it("both trucks are exactly as drawable after roads exist as before: not at all", () => {
    const state = appState({ TRUCK_01: withOdometry(), TRUCK_02: vehicle("TRUCK_02") });
    const positions = spatialPositions(projectMineCast(state).vehicles, MINECAST_SITE);

    // Roads were generated above; they have no effect on this.
    expect(ROADS.length).toBeGreaterThan(0);
    expect(drawablePositions(positions).length).toBe(0);
  });

  it("no road point is ever mistaken for a vehicle coordinate", () => {
    // A road carries x/y/elevation; a vehicle position carries a provenance and a frame.
    // They are different types and the corridor has no such fields.
    const road = ROADS[0] as (typeof ROADS)[number];
    expect("provenance" in road).toBe(false);
    expect("frame" in road).toBe(false);
    expect("drawableInScene" in road).toBe(false);
  });
});

// ---------------------------------------------------------------------------
// 13 + 14 + 15 + 16. Pass 3A semantics unchanged
// ---------------------------------------------------------------------------

describe("13/14/15 — TRUCK_01 stays LOCAL_ODOMETRY and non-drawable", () => {
  it("is LOCAL_ODOMETRY in its own frame, not drawable, with no lonLat", () => {
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
    expect(position.method).toBe("WHEEL_IMU_ODOMETRY");
  });

  it("is not placed onto a road by existing near one", () => {
    // Pass 3B added roads. A local pose still has no scene anchor, road or not.
    const projected = projectMineCastVehicle(
      appState({ TRUCK_01: withOdometry() }),
      "TRUCK_01",
      "LIVE",
    );
    expect(toSpatialPosition(projected, MINECAST_SITE).drawableInScene).toBe(false);
  });
});

describe("16 — TRUCK_02 remains UNAVAILABLE", () => {
  it("has no spatial position, road network or not", () => {
    const projected = projectMineCastVehicle(
      appState({ TRUCK_02: vehicle("TRUCK_02") }),
      "TRUCK_02",
      "LIVE",
    );
    const position = toSpatialPosition(projected, MINECAST_SITE);
    expect(position.provenance).toBe("UNAVAILABLE");
    expect(position.x).toBeNull();
    expect(position.y).toBeNull();
  });
});

// ---------------------------------------------------------------------------
// 17 + 18. read-only, no ingestion
// ---------------------------------------------------------------------------

describe("17/18 — Mine-Cast remains read-only with no ingestion", () => {
  it("the corridor module submits nothing, fetches nothing, opens nothing", () => {
    const source = roadSource();
    for (const forbidden of [
      "submitCommand",
      "commandClient",
      "fetch(",
      "WebSocket",
      "applyPatch",
    ]) {
      expect(source, forbidden).not.toContain(forbidden);
    }
  });
});

// ---------------------------------------------------------------------------
// ribbon geometry
// ---------------------------------------------------------------------------

describe("ribbon geometry", () => {
  const main = ROADS[0] as (typeof ROADS)[number];
  const ribbon = corridorRibbon(main, VERTICAL_EXAGGERATION, 3, FIELD);

  it("emits two vertices per centreline point", () => {
    expect(ribbon.positions.length).toBe(main.centreline.length * 2 * 3);
  });

  it("emits two triangles per segment", () => {
    expect(ribbon.indices.length).toBe((main.centreline.length - 1) * 6);
  });

  it("references only valid vertex indices", () => {
    const vertexCount = ribbon.positions.length / 3;
    for (const index of ribbon.indices) {
      expect(index).toBeGreaterThanOrEqual(0);
      expect(index).toBeLessThan(vertexCount);
    }
  });

  it("separates the two edges by exactly the corridor width", () => {
    for (let i = 0; i < main.centreline.length; i += 1) {
      const lx = ribbon.leftEdge[i * 3] as number;
      const lz = ribbon.leftEdge[i * 3 + 2] as number;
      const rx = ribbon.rightEdge[i * 3] as number;
      const rz = ribbon.rightEdge[i * 3 + 2] as number;
      const dx = lx - rx;
      const dz = lz - rz;
      expect(Math.sqrt(dx * dx + dz * dz)).toBeCloseTo(main.widthM, 6);
    }
  });

  it("is finite throughout", () => {
    for (const value of [...ribbon.positions, ...ribbon.leftEdge, ...ribbon.rightEdge]) {
      expect(Number.isFinite(value)).toBe(true);
    }
  });

  it("applies the lift on top of the exaggerated elevation, at each edge", () => {
    const lx = ribbon.leftEdge[0] as number;
    const lz = ribbon.leftEdge[2] as number;
    expect(ribbon.positions[1]).toBeCloseTo(FIELD(lx, lz) * VERTICAL_EXAGGERATION + 3, 6);
  });

  it("drapes on the rendered mesh when given the grid sampler", () => {
    // What the renderer actually does: follow the mesh's bilinear interpolation, so the
    // ribbon cannot dip under the drawn surface at a bench riser.
    const grid = sampleHeightGrid(CONFIG);
    const onMesh = corridorRibbon(main, VERTICAL_EXAGGERATION, 4, (x, y) =>
      gridElevationAt(grid, x, y),
    );
    for (let i = 0; i < main.centreline.length; i += 1) {
      const lx = onMesh.leftEdge[i * 3] as number;
      const ly = onMesh.leftEdge[i * 3 + 1] as number;
      const lz = onMesh.leftEdge[i * 3 + 2] as number;
      expect(ly).toBeCloseTo(gridElevationAt(grid, lx, lz) * VERTICAL_EXAGGERATION + 4, 6);
    }
  });
});

// ---------------------------------------------------------------------------
// layer integration
// ---------------------------------------------------------------------------

describe("layer toggle", () => {
  it("HAUL_ROADS and RAMPS are now implemented, synthetic, and default on", () => {
    for (const id of ["HAUL_ROADS", "RAMPS"]) {
      const layer = LAYERS.find((l) => l.id === id);
      expect(layer?.implemented, id).toBe(true);
      expect(layer?.defaultVisible, id).toBe(true);
      expect(layer?.provenance, id).toBe("SYNTHETIC_FOR_DEMO");
      expect(layer?.note.toUpperCase(), id).toContain("NOT NMDC INFRASTRUCTURE");
    }
  });

  it("the corridor layers start visible and toggle off and on again", () => {
    let view = initialViewState();
    expect(view.layerVisibility.HAUL_ROADS).toBe(true);
    expect(view.layerVisibility.RAMPS).toBe(true);

    view = minecastReducer(view, { type: "TOGGLE_LAYER", layerId: "HAUL_ROADS" });
    expect(view.layerVisibility.HAUL_ROADS).toBe(false);
    // Toggling roads leaves terrain, pit and benches alone.
    expect(view.layerVisibility.TERRAIN).toBe(true);
    expect(view.layerVisibility.PIT).toBe(true);
    expect(view.layerVisibility.BENCHES).toBe(true);
    expect(view.layerVisibility.RAMPS).toBe(true);

    view = minecastReducer(view, { type: "TOGGLE_LAYER", layerId: "HAUL_ROADS" });
    expect(view.layerVisibility.HAUL_ROADS).toBe(true);
  });

  it("RAMPS toggles independently of HAUL_ROADS", () => {
    let view = initialViewState();
    view = minecastReducer(view, { type: "SET_LAYER", layerId: "RAMPS", visible: false });
    expect(view.layerVisibility.RAMPS).toBe(false);
    expect(view.layerVisibility.HAUL_ROADS).toBe(true);
  });

  it("the still-unbuilt layers stay unbuilt", () => {
    // VEHICLES left this list in MINECAST-01: it has a renderer now, fed by the canonical
    // Twin scene position. The rest still draw nothing and must still say so.
    // MINE-ROUTES-02 built MINE_ZONES (zones layer) and ROUTES (route labels).
    for (const id of ["SAFETY", "V2V", "V2I_RSU", "ORTHOPHOTO"]) {
      expect(LAYERS.find((l) => l.id === id)?.implemented, id).toBe(false);
    }
  });
});
