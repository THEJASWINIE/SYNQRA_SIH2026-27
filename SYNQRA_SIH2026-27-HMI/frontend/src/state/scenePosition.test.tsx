/**
 * MAP-02 — two trucks on the mine map, as Digital Twin entities.
 *
 * ==========================================================================
 *  SOFTWARE ONLY. Every coordinate in this file is a SIMULATED Digital Twin scene
 *  pose, exactly as the backend's `scene_position_sim` produces it. Nothing here is a
 *  GNSS fix, and no test below is hardware verification.
 * ==========================================================================
 *
 * The numbered items are MAP-02's own test list.
 */

import { readFileSync } from "node:fs";
import { join } from "node:path";
import type { ReactNode } from "react";
import { renderToString } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { freshnessConfig } from "../config/freshness";
import type { PositionScene, VehicleState } from "../contracts/domain";
import { OperationsOverview } from "../screens/OperationsOverview";
import { DriverScreen } from "../vehicle/DriverScreen";
import { vehicleConfig } from "../vehicle/vehicleConfig";
import { projectVehicle } from "../vehicle/vehicleProjection";
import { bailadilaDeposit5, toDecimalExtent } from "./geoSite";
import { HmiContext } from "./ProviderHost";
import { AppStateStore } from "./store";
import { testHmiContext } from "./testHmiContext";
import {
  fleetPositions,
  placeablePositions,
  providerForMode,
  resolveVehiclePosition,
  SCENE_FRAME,
  TWIN_SCENE_LABEL,
  twinScenePosition,
} from "./vehiclePosition";

const T = "2026-09-14T12:00:00.000Z";
const CONFIG = freshnessConfig(5000);
const SITE = bailadilaDeposit5();
const EXTENT = toDecimalExtent(SITE.extent);

/** A scene pose shaped exactly like the Twin's `position_scene` payload. */
function scene(xM: number, yM: number, over: Partial<PositionScene> = {}): PositionScene {
  return {
    xM,
    yM,
    headingRad: 0.5,
    frame: SCENE_FRAME,
    status: "VALID",
    source: "SIMULATION",
    origin: "SIMULATION",
    provenanceLabel: "SIMULATION · DIGITAL TWIN",
    method: "DIGITAL_TWIN_SCENE_SIM",
    reason: "Digital Twin demonstration position in SCENE_METRES.",
    ...over,
  };
}

function vehicle(id: string, positionScene: PositionScene | null = null): VehicleState {
  return {
    vehicleId: id,
    timestamp: T,
    position: { x: null, y: null, segmentId: null, offsetM: null },
    positionScene,
    speedMps: 7.5,
    accelMps2: null,
    gradeRad: null,
    frictionEst: null,
    mode: "NORMAL",
    commConfidence: null,
    vehicleKind: "TRUCK",
    routeId: null,
  } as VehicleState;
}

/** The demo fleet: both trucks carrying well-separated scene poses. */
const T01 = vehicle("TRUCK_01", scene(1150, 2380));
const T02 = vehicle("TRUCK_02", scene(2048, 736));

function storeWithFleet(): AppStateStore {
  const store = new AppStateStore(T, "LIVE");
  store.applyPatch({ changes: { vehicles: { TRUCK_01: T01, TRUCK_02: T02 } } } as never, T);
  store.setStatus("CONNECTED", null);
  return store;
}

const text = (html: string) => html.replace(/<!-- -->/g, "");

function render(store: AppStateStore, node: ReactNode): string {
  const value = testHmiContext({ store, freshness: CONFIG });
  return text(renderToString(<HmiContext.Provider value={value}>{node}</HmiContext.Provider>));
}

function truckHmi(store: AppStateStore, id: "TRUCK_01" | "TRUCK_02"): string {
  return render(
    store,
    <DriverScreen
      projection={projectVehicle(store.getSnapshot(), id)}
      config={vehicleConfig(id)}
    />,
  );
}

const src = (rel: string) => readFileSync(join(__dirname, "..", rel), "utf-8");

// ===========================================================================

describe("1-4. both trucks have a drawable, simulated SCENE_METRES position", () => {
  it("1/2. TRUCK_01 and TRUCK_02 each resolve to a drawable position", () => {
    for (const v of [T01, T02]) {
      const resolved = twinScenePosition(v, EXTENT);
      expect(resolved, v.vehicleId).not.toBeNull();
      expect(resolved?.position).not.toBeNull();
      expect(Number.isFinite(resolved?.position?.lat)).toBe(true);
      expect(Number.isFinite(resolved?.position?.lon)).toBe(true);
    }
  });

  it("1/2. both land inside the published extent, and not on top of each other", () => {
    const a = twinScenePosition(T01, EXTENT)?.position;
    const b = twinScenePosition(T02, EXTENT)?.position;
    for (const p of [a, b]) {
      expect(p!.lat).toBeGreaterThan(EXTENT.south);
      expect(p!.lat).toBeLessThan(EXTENT.north);
      expect(p!.lon).toBeGreaterThan(EXTENT.west);
      expect(p!.lon).toBeLessThan(EXTENT.east);
    }
    expect(Math.abs(a!.lat - b!.lat) + Math.abs(a!.lon - b!.lon)).toBeGreaterThan(0.005);
  });

  it("3/12. the classification is simulation, never GNSS or physical", () => {
    const resolved = twinScenePosition(T01, EXTENT);
    expect(resolved?.provenance).toBe("SIMULATED_TWIN_SCENE");
    expect(resolved?.provenance).not.toBe("PHYSICAL");
    expect(TWIN_SCENE_LABEL).toBe("SIMULATION · DIGITAL TWIN");
    for (const word of ["GNSS", "GPS", "PHYSICAL", "SURVEYED", "HARDWARE"]) {
      expect(TWIN_SCENE_LABEL.toUpperCase()).not.toContain(word);
      expect(resolved?.provenance.toUpperCase()).not.toContain(word);
    }
  });

  it("4. only the SCENE_METRES frame is accepted", () => {
    expect(SCENE_FRAME).toBe("SCENE_METRES");
    const wrongFrame = vehicle("TRUCK_01", scene(1150, 2380, { frame: "ODOMETRY_LOCAL_METRES" }));
    expect(twinScenePosition(wrongFrame, EXTENT)).toBeNull();
  });

  it("refuses a pose that claims hardware, or is invalid, or is absent", () => {
    const claims = vehicle("TRUCK_01", scene(1150, 2380, { origin: "HARDWARE" }));
    expect(twinScenePosition(claims, EXTENT)).toBeNull();
    const invalid = vehicle("TRUCK_01", scene(1150, 2380, { status: "UNAVAILABLE" }));
    expect(twinScenePosition(invalid, EXTENT)).toBeNull();
    expect(twinScenePosition(vehicle("TRUCK_01", null), EXTENT)).toBeNull();
  });

  it("a genuine fix would win over the demo pose", () => {
    // No GNSS exists today, so this asserts the PRECEDENCE, not a capability.
    const withFix = {
      ...vehicle("TRUCK_01", scene(1150, 2380)),
      positionGnss: {
        latitude: 18.69,
        longitude: 81.19,
        source: "GNSS",
        status: "VALID",
        timestamp: 1,
        origin: "HARDWARE",
      },
    } as VehicleState;
    const provider = providerForMode("LIVE", EXTENT);
    expect(resolveVehiclePosition(withFix, provider, EXTENT).provenance).toBe("PHYSICAL");
  });

  it("a vehicle with no pose at all keeps the provider's UNAVAILABLE answer", () => {
    const provider = providerForMode("LIVE", EXTENT);
    const resolved = resolveVehiclePosition(vehicle("TRUCK_09"), provider, EXTENT);
    expect(resolved.position).toBeNull();
    expect(resolved.provenance).toBe("UNAVAILABLE");
    expect(resolved.reason).toBeTruthy();
  });
});

describe("5. Control Room renders both trucks from canonical state", () => {
  const html = render(storeWithFleet(), <OperationsOverview onSelectVehicle={() => {}} />);

  it("draws a marker for each truck, labelled as a Digital Twin simulation", () => {
    expect(html).toContain(`TRUCK_01 · ${TWIN_SCENE_LABEL}`);
    expect(html).toContain(`TRUCK_02 · ${TWIN_SCENE_LABEL}`);
  });

  it("both markers come from the one canonical fleet resolver", () => {
    const placed = placeablePositions(
      fleetPositions({ TRUCK_01: T01, TRUCK_02: T02 }, providerForMode("LIVE", EXTENT), EXTENT),
    );
    expect(placed.map((p) => p.vehicleId)).toEqual(["TRUCK_01", "TRUCK_02"]);
    expect(placed.every((p) => p.provenance === "SIMULATED_TWIN_SCENE")).toBe(true);
  });

  it("11. the published extent stays an extent, never a lease polygon", () => {
    expect(html).toContain("PUBLISHED LEASE COORDINATE EXTENT — not a lease boundary");
    const extentFeature = SITE.layers
      .find((l) => l.id === "SITE_EXTENT")
      ?.features.find((f) => f.id === "DEP5-EXTENT");
    expect(extentFeature?.geometryType).toBe("BOUNDING_EXTENT");
    expect(extentFeature?.coordinates).toEqual([]);
  });
});

describe("6/7. fixed identity on each truck console, both trucks on the map", () => {
  const store = storeWithFleet();

  it("6. TRUCK_01 console: own is TRUCK_01, peer is TRUCK_02", () => {
    const html = truckHmi(store, "TRUCK_01");
    expect(html).toContain('aria-label="TRUCK_01 driver display"');
    expect(html).toContain("PEER TRUCK_02");
    expect(html).not.toContain("PEER TRUCK_01");
    // Own vehicle ringed on the map, and the peer drawn alongside it.
    expect(html).toContain(`THIS VEHICLE · TRUCK_01 · ${TWIN_SCENE_LABEL}`);
    expect(html).toContain(`TRUCK_02 · ${TWIN_SCENE_LABEL}`);
  });

  it("7. TRUCK_02 console: own is TRUCK_02, peer is TRUCK_01", () => {
    const html = truckHmi(store, "TRUCK_02");
    expect(html).toContain('aria-label="TRUCK_02 driver display"');
    expect(html).toContain("PEER TRUCK_01");
    expect(html).not.toContain("PEER TRUCK_02");
    expect(html).toContain(`THIS VEHICLE · TRUCK_02 · ${TWIN_SCENE_LABEL}`);
    expect(html).toContain(`TRUCK_01 · ${TWIN_SCENE_LABEL}`);
  });

  it("the identities are never reversed between the two consoles", () => {
    const one = truckHmi(store, "TRUCK_01");
    const two = truckHmi(store, "TRUCK_02");
    expect(one).toContain("THIS VEHICLE · TRUCK_01");
    expect(one).not.toContain("THIS VEHICLE · TRUCK_02");
    expect(two).toContain("THIS VEHICLE · TRUCK_02");
    expect(two).not.toContain("THIS VEHICLE · TRUCK_01");
  });
});

describe("8-10. architecture", () => {
  it("8. no truck position is hardcoded in a presentation or map component", () => {
    const presentation = [
      "screens/GeoSiteMap.tsx",
      "screens/OperationsOverview.tsx",
      "vehicle/panels.tsx",
      "vehicle/DriverScreen.tsx",
    ];
    for (const rel of presentation) {
      const code = src(rel)
        .replace(/\/\*[\s\S]*?\*\//g, "")
        .replace(/^\s*\/\/.*$/gm, "");
      expect(code, rel).not.toMatch(/\bTRUCK_0[12]\b/);
      expect(code, rel).not.toMatch(/lat:\s*\d|lon:\s*\d/);
      expect(code, rel).not.toMatch(/\bxM:\s*\d|\byM:\s*\d/);
    }
  });

  it("9. GeoSiteMap remains the single shared map implementation", () => {
    expect(src("screens/OperationsOverview.tsx")).toContain('from "./GeoSiteMap"');
    expect(src("vehicle/panels.tsx")).toContain('from "../screens/GeoSiteMap"');
    // No second map component, and no second site-geometry source.
    expect(src("vehicle/panels.tsx")).toContain("bailadilaDeposit5()");
    expect(src("screens/OperationsOverview.tsx")).toContain("bailadilaDeposit5()");
  });

  it("9. map components open no socket and run no fetch of their own", () => {
    for (const rel of ["screens/GeoSiteMap.tsx", "vehicle/panels.tsx"]) {
      const code = src(rel);
      expect(code, rel).not.toMatch(/new WebSocket|fetch\(/);
    }
  });

  it("10. a LOCAL ODOMETRY pose is still never drawn as a geographic position", () => {
    const odometryOnly = {
      ...vehicle("TRUCK_01", null),
      positionOdom: {
        xM: 12.5,
        yM: -3.25,
        headingRad: 0.1,
        distanceM: 42,
        timestamp: 1,
        source: "DERIVED",
        origin: "HARDWARE",
        provenanceLabel: "PHYSICAL (derived)",
        method: "WHEEL_IMU_ODOMETRY",
        status: "VALID",
        originType: "LOCAL ODOMETRY ORIGIN",
      },
    } as VehicleState;
    const provider = providerForMode("LIVE", EXTENT);
    const resolved = resolveVehiclePosition(odometryOnly, provider, EXTENT);
    // Odometry produces no map coordinate on any path in this module.
    expect(resolved.position).toBeNull();
    expect(resolved.provenance).toBe("UNAVAILABLE");
  });
});
