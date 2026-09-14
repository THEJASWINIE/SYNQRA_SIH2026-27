/**
 * MINECAST-01 — the Twin's trucks reach the 3D scene, and nothing else invents them.
 *
 * ==========================================================================
 *  SOFTWARE ONLY. Every coordinate here is the canonical Digital Twin DEMONSTRATION
 *  pose (`position_scene`, SCENE_METRES, SIMULATION). No GNSS exists on this prototype,
 *  nothing physical was executed, and no test below is hardware verification.
 * ==========================================================================
 *
 * The numbered items are MINECAST-01's own test list. The scene renderer itself is WebGL
 * and cannot run in this Node environment (M4D-C), so what is asserted here is everything
 * that DECIDES what the renderer draws: the projection, the shared validator, the spatial
 * contract, and the source-level guarantee that no drawing module holds a coordinate.
 */

import { readdirSync, readFileSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";

import type { PositionScene, VehicleState } from "../contracts/domain";
import { bailadilaDeposit5, toDecimalExtent } from "../state/geoSite";
import { AppStateStore } from "../state/store";
import { drawableScenePose, twinScenePosition } from "../state/vehiclePosition";
import { type MineCastVehicle, projectMineCast } from "./minecastProjection";
import { drawablePositions, spatialPositions, toSpatialPosition } from "./spatialPosition";

const T = "2026-09-14T12:00:00.000Z";
const MINECAST_DIR = join(__dirname);

function scene(xM: number, yM: number, over: Partial<PositionScene> = {}): PositionScene {
  return {
    xM,
    yM,
    headingRad: 0.75,
    frame: "SCENE_METRES",
    status: "VALID",
    source: "SIMULATION",
    origin: "SIMULATION",
    provenanceLabel: "SIMULATION · DIGITAL TWIN",
    method: "DIGITAL_TWIN_SCENE_SIM",
    reason: "Digital Twin demonstration position in SCENE_METRES.",
    ...over,
  };
}

function vehicle(id: string, positionScene: PositionScene | null): VehicleState {
  return {
    vehicleId: id,
    timestamp: T,
    position: { x: null, y: null, segmentId: null, offsetM: null },
    positionScene,
    speedMps: 6.5,
    accelMps2: null,
    gradeRad: null,
    frictionEst: null,
    mode: "NORMAL",
    commConfidence: null,
    vehicleKind: "TRUCK",
    routeId: null,
    provenance: {
      received_at: {
        value: 1,
        timestamp: 1,
        source: "SIMULATION",
        origin: "SIMULATION",
        quality: "GOOD",
        ageS: 0,
        available: true,
        clockDomain: "WALL_CLOCK",
        freshness: "CURRENT",
      },
    },
  } as unknown as VehicleState;
}

/** Both trucks, placed by the Twin at well-separated scene poses. */
const T01_SCENE = scene(1150, 2380);
const T02_SCENE = scene(2048, 736);

function storeWithFleet(
  t01: PositionScene | null = T01_SCENE,
  t02: PositionScene | null = T02_SCENE,
): AppStateStore {
  const store = new AppStateStore(T, "LIVE");
  store.applyPatch(
    {
      changes: {
        vehicles: { TRUCK_01: vehicle("TRUCK_01", t01), TRUCK_02: vehicle("TRUCK_02", t02) },
      },
    } as never,
    T,
  );
  store.setStatus("CONNECTED", null);
  return store;
}

function minecastFor(store: AppStateStore) {
  return projectMineCast(store.getSnapshot());
}

const code = (name: string) => readFileSync(join(MINECAST_DIR, name), "utf-8");
const sourceFiles = readdirSync(MINECAST_DIR).filter(
  (name) => (name.endsWith(".ts") || name.endsWith(".tsx")) && !name.includes(".test."),
);

// ===========================================================================

describe("1-5. both trucks arrive from canonical Twin state, drawable and simulated", () => {
  const minecast = minecastFor(storeWithFleet());
  const positions = spatialPositions(minecast.vehicles, minecast.site);
  const byId = (id: string) => positions.find((p) => p.canonicalVehicleId === id);

  it("1/2. TRUCK_01 and TRUCK_02 both reach Mine-Cast with a scene pose", () => {
    for (const id of ["TRUCK_01", "TRUCK_02"]) {
      const projected = minecast.vehicles.find((v) => v.canonicalVehicleId === id);
      expect(projected, id).toBeDefined();
      expect(projected?.scenePose, id).not.toBeNull();
      expect(byId(id), id).toBeDefined();
    }
  });

  it("3. both positions are expressed in SCENE_METRES", () => {
    expect(byId("TRUCK_01")?.frame).toBe("SCENE_METRES");
    expect(byId("TRUCK_02")?.frame).toBe("SCENE_METRES");
  });

  it("4. both positions are drawable in the scene", () => {
    expect(byId("TRUCK_01")?.drawableInScene).toBe(true);
    expect(byId("TRUCK_02")?.drawableInScene).toBe(true);
    expect(drawablePositions(positions)).toHaveLength(2);
  });

  it("5/6. provenance is synthetic-for-demo, and no GNSS is involved", () => {
    for (const id of ["TRUCK_01", "TRUCK_02"]) {
      const position = byId(id);
      expect(position?.provenance, id).toBe("SYNTHETIC_FOR_DEMO");
      expect(position?.synthetic, id).toBe(true);
      // Not a coordinate on the earth, and never labelled as a fix.
      expect(position?.lonLat, id).toBeNull();
      expect(position?.method, id).toBe("DIGITAL_TWIN_SCENE_SIM");
      expect(position?.method.toUpperCase(), id).not.toContain("GNSS");
      expect(position?.provenance.toUpperCase(), id).not.toContain("HARDWARE");
    }
  });

  it("6. no vehicle carries a GNSS fix, and the scene still draws both", () => {
    for (const projected of minecast.vehicles) {
      expect(projected.position.kind).not.toBe("GEOGRAPHIC");
    }
    expect(drawablePositions(positions)).toHaveLength(2);
  });

  it("8. the two trucks stay distinct — separate ids and separate coordinates", () => {
    const a = byId("TRUCK_01");
    const b = byId("TRUCK_02");
    expect(a?.canonicalVehicleId).not.toBe(b?.canonicalVehicleId);
    expect(a?.displayId).not.toBe(b?.displayId);
    expect(a?.x).not.toBe(b?.x);
    expect(a?.y).not.toBe(b?.y);
  });

  it("9. heading comes from the canonical scene pose when supplied, and only then", () => {
    expect(byId("TRUCK_01")?.headingRad).toBe(T01_SCENE.headingRad);

    const noHeading = minecastFor(storeWithFleet(scene(1150, 2380, { headingRad: null })));
    const without = spatialPositions(noHeading.vehicles, noHeading.site).find(
      (p) => p.canonicalVehicleId === "TRUCK_01",
    );
    // Absent rather than invented: no default bearing is substituted.
    expect(without?.headingRad).toBeNull();
    expect(without?.drawableInScene).toBe(true);
  });
});

describe("7. Mine-Cast creates no vehicle coordinate of its own", () => {
  it("the scene coordinates are IDENTICAL to the canonical Twin values", () => {
    const minecast = minecastFor(storeWithFleet());
    const positions = spatialPositions(minecast.vehicles, minecast.site);
    const t01 = positions.find((p) => p.canonicalVehicleId === "TRUCK_01");
    // Passed through untouched: no scaling, no offset, no rounding.
    expect(t01?.x).toBe(T01_SCENE.xM);
    expect(t01?.y).toBe(T01_SCENE.yM);
  });

  it("Mine-Cast and the Control Room agree, because they share one validator", () => {
    const minecast = minecastFor(storeWithFleet());
    const projected = minecast.vehicles.find(
      (v) => v.canonicalVehicleId === "TRUCK_01",
    ) as MineCastVehicle;

    // The 2D map's lon/lat and Mine-Cast's scene metres are two renderings of ONE value.
    const shared = drawableScenePose(vehicle("TRUCK_01", T01_SCENE));
    const map2d = twinScenePosition(
      vehicle("TRUCK_01", T01_SCENE),
      toDecimalExtent(bailadilaDeposit5().extent),
    );
    const scene3d = toSpatialPosition(projected, minecast.site);

    expect(shared?.xM).toBe(T01_SCENE.xM);
    expect(scene3d.x).toBe(shared?.xM);
    expect(scene3d.y).toBe(shared?.yM);
    expect(map2d?.provenance).toBe("SIMULATED_TWIN_SCENE");
    expect(map2d?.position).not.toBeNull();
  });

  it("a truck the Twin has not placed is not drawn at all", () => {
    const minecast = minecastFor(storeWithFleet(T01_SCENE, null));
    const positions = spatialPositions(minecast.vehicles, minecast.site);
    const t02 = positions.find((p) => p.canonicalVehicleId === "TRUCK_02");
    expect(t02?.drawableInScene).toBe(false);
    expect(t02?.x).toBeNull();
    expect(t02?.y).toBeNull();
    expect(drawablePositions(positions)).toHaveLength(1);
  });

  it("a pose claiming hardware, or a foreign frame, is refused", () => {
    for (const bad of [
      scene(1150, 2380, { origin: "HARDWARE" }),
      scene(1150, 2380, { source: "HARDWARE" }),
      scene(1150, 2380, { frame: "ODOMETRY_LOCAL_METRES" }),
      scene(1150, 2380, { status: "UNAVAILABLE" }),
    ]) {
      const minecast = minecastFor(storeWithFleet(bad, null));
      const t01 = spatialPositions(minecast.vehicles, minecast.site).find(
        (p) => p.canonicalVehicleId === "TRUCK_01",
      );
      expect(t01?.drawableInScene).toBe(false);
    }
  });
});

describe("10. TRUCK_01's local odometry is still not a scene position", () => {
  const odom = {
    xM: 12.5,
    yM: -3.25,
    headingRad: 0.1,
    distanceM: 42,
    timestamp: 1,
    source: "DERIVED",
    origin: "HARDWARE",
    provenanceLabel: "PHYSICAL_DERIVED",
    method: "WHEEL_IMU_ODOMETRY",
    status: "VALID",
    originType: "LOCAL ODOMETRY ORIGIN",
  };

  function storeWith(positionScene: PositionScene | null): AppStateStore {
    const withOdom = { ...vehicle("TRUCK_01", positionScene), positionOdom: odom };
    const store = new AppStateStore(T, "LIVE");
    store.applyPatch({ changes: { vehicles: { TRUCK_01: withOdom } } } as never, T);
    return store;
  }

  it("odometry alone remains undrawable, in its own frame", () => {
    const minecast = minecastFor(storeWith(null));
    const projected = minecast.vehicles.find(
      (v) => v.canonicalVehicleId === "TRUCK_01",
    ) as MineCastVehicle;

    expect(projected.position.kind).toBe("LOCAL_ODOMETRY");
    expect(projected.scenePose).toBeNull();

    const spatial = toSpatialPosition(projected, minecast.site);
    expect(spatial.frame).toBe("ODOMETRY_LOCAL_METRES");
    expect(spatial.drawableInScene).toBe(false);
    expect(spatial.lonLat).toBeNull();
  });

  it("a scene pose does not erase the instrument truth beside it", () => {
    const minecast = minecastFor(storeWith(T01_SCENE));
    const projected = minecast.vehicles.find(
      (v) => v.canonicalVehicleId === "TRUCK_01",
    ) as MineCastVehicle;

    // The marker is placed by the scene pose, and the odometry is still reported as
    // odometry on its own field for the vehicle panel to show.
    expect(projected.position.kind).toBe("LOCAL_ODOMETRY");
    expect(projected.position.xM).toBe(12.5);
    expect(projected.scenePose?.xM).toBe(T01_SCENE.xM);

    const spatial = toSpatialPosition(projected, minecast.site);
    expect(spatial.drawableInScene).toBe(true);
    // Still not geographic, and still stamped as a demonstration placement.
    expect(spatial.lonLat).toBeNull();
    expect(spatial.provenance).toBe("SYNTHETIC_FOR_DEMO");
  });
});

describe("12. no Mine-Cast source holds a truck coordinate or a truck id", () => {
  it("no module contains a literal vehicle coordinate", () => {
    for (const name of sourceFiles) {
      const source = code(name)
        .replace(/\/\*[\s\S]*?\*\//g, "")
        .replace(/^\s*\/\/.*$/gm, "");
      expect(source, name).not.toMatch(/\bxM\s*[:=]\s*-?\d/);
      expect(source, name).not.toMatch(/\byM\s*[:=]\s*-?\d/);
      expect(source, name).not.toMatch(/\blatitude\s*[:=]\s*-?\d/);
      expect(source, name).not.toMatch(/\blongitude\s*[:=]\s*-?\d/);
    }
  });

  it("the drawing modules name no vehicle and open no connection", () => {
    for (const name of ["VehicleMarkers.tsx", "MineScene.tsx", "MineCanvas.tsx"]) {
      const source = code(name);
      expect(source, name).not.toMatch(/\bTRUCK_0\d\b/);
      expect(source, name).not.toMatch(/new WebSocket|fetch\(/);
    }
  });

  it("the vehicle renderer takes its positions as a prop and nothing else", () => {
    const markers = code("VehicleMarkers.tsx");
    // No store, no context, no projection: it is handed what to draw.
    expect(markers).not.toContain("useAppState");
    expect(markers).not.toContain("useMineCastStore");
    expect(markers).not.toContain("projectMineCast");
    expect(markers).toContain("positions");
  });
});
