/**
 * MINECAST-02 — the trucks drive on the mine, deterministically, on the drawn roads.
 *
 * SOFTWARE ONLY. Every coordinate here is a synthetic demonstration route composed from
 * the scene's invented corridors. Nothing is a real NMDC haul road and nothing is
 * hardware verification.
 *
 * The route follower itself is Python (`scene_position_sim.py`) and is asserted by
 * `tests/test_scene_position_contract.py`. What this file owns is the geometry contract
 * (the routes, and the exported JSON the follower reads), the terrain conformance the
 * renderer applies, and the source-level guarantee that no presentation component animates
 * a truck on its own.
 */

import { readdirSync, readFileSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";

import { bailadilaDeposit5, extentSizeMetres, toDecimalExtent } from "../state/geoSite";
import { demoRoutes, ROUTE_DISCLOSURE, toSceneRoutesDocument, type Waypoint } from "./demoRoutes";
import { haulCorridors } from "./haulRoads";
import { sampleHeightGrid, terrainConfig } from "./terrainField";
import { terrainSurfaceY, VEHICLE_CLEARANCE_M, vehicleSurfaceY } from "./vehiclePlacement";

const size = extentSizeMetres(toDecimalExtent(bailadilaDeposit5().extent));
const CONFIG = terrainConfig(size.widthM, size.heightM);
const ROUTES = demoRoutes(CONFIG);
const GRID = sampleHeightGrid(CONFIG);

const CONTRACT_PATH = join(__dirname, "..", "..", "..", "contracts", "scene_routes.json");
const MINECAST_DIR = join(__dirname);

const byVehicle = (id: string) => ROUTES.find((r) => r.vehicleId === id);

/** Distance from a point to the nearest point on a polyline. */
function distanceToPolyline(point: Waypoint, line: readonly Waypoint[]): number {
  let best = Number.POSITIVE_INFINITY;
  for (let i = 1; i < line.length; i += 1) {
    const [ax, ay] = line[i - 1] as Waypoint;
    const [bx, by] = line[i] as Waypoint;
    const dx = bx - ax;
    const dy = by - ay;
    const len2 = dx * dx + dy * dy;
    const t =
      len2 === 0
        ? 0
        : Math.max(0, Math.min(1, ((point[0] - ax) * dx + (point[1] - ay) * dy) / len2));
    const px = ax + dx * t;
    const py = ay + dy * t;
    best = Math.min(best, Math.hypot(point[0] - px, point[1] - py));
  }
  return best;
}

// ===========================================================================

describe("1-3. each truck has its own deterministic route", () => {
  it("1. TRUCK_01 has a deterministic route with explicit waypoints", () => {
    const route = byVehicle("TRUCK_01");
    expect(route).toBeDefined();
    expect(route?.waypoints.length).toBeGreaterThan(10);
    expect(route?.lengthM).toBeGreaterThan(1000);
    // Deterministic: the same config yields byte-identical waypoints.
    expect(demoRoutes(CONFIG).find((r) => r.vehicleId === "TRUCK_01")?.waypoints).toEqual(
      route?.waypoints,
    );
  });

  it("2. TRUCK_02 has a deterministic route with explicit waypoints", () => {
    const route = byVehicle("TRUCK_02");
    expect(route).toBeDefined();
    expect(route?.waypoints.length).toBeGreaterThan(10);
    expect(demoRoutes(CONFIG).find((r) => r.vehicleId === "TRUCK_02")?.waypoints).toEqual(
      route?.waypoints,
    );
  });

  it("3. the two routes are different, and start in different places", () => {
    const a = byVehicle("TRUCK_01");
    const b = byVehicle("TRUCK_02");
    expect(a?.routeId).not.toBe(b?.routeId);
    expect(a?.corridorIds).not.toEqual(b?.corridorIds);
    expect(a?.waypoints).not.toEqual(b?.waypoints);
    expect(a?.speedMps).not.toBe(b?.speedMps);
  });

  it("5. no route uses randomness", () => {
    // Comments stripped: the module's own header says "no Math.random", which is the point.
    const source = readFileSync(join(MINECAST_DIR, "demoRoutes.ts"), "utf-8")
      .replace(/\/\*[\s\S]*?\*\//g, "")
      .replace(/^\s*\/\/.*$/gm, "");
    expect(source).not.toContain("Math.random");
    expect(source).not.toContain("Date.now");
  });
});

describe("6. routes stay on the declared demonstration area and on the drawn roads", () => {
  it("every waypoint lies inside the scene extent", () => {
    for (const route of ROUTES) {
      for (const [x, y] of route.waypoints) {
        expect(x, route.routeId).toBeGreaterThanOrEqual(0);
        expect(x, route.routeId).toBeLessThanOrEqual(CONFIG.widthM);
        expect(y, route.routeId).toBeGreaterThanOrEqual(0);
        expect(y, route.routeId).toBeLessThanOrEqual(CONFIG.heightM);
      }
    }
  });

  it("every waypoint sits ON a synthetic corridor centreline - nothing was drawn anew", () => {
    const corridors = haulCorridors(CONFIG);
    for (const route of ROUTES) {
      const lines = route.corridorIds.map(
        (id) =>
          corridors.find((c) => c.id === id)?.centreline.map((p) => [p.x, p.y] as const) ?? [],
      );
      for (const waypoint of route.waypoints) {
        const nearest = Math.min(...lines.map((line) => distanceToPolyline(waypoint, line)));
        expect(nearest, `${route.routeId} ${waypoint}`).toBeLessThan(0.001);
      }
    }
  });

  it("the routes carry the corridors' own disclosure, never an NMDC claim", () => {
    expect(ROUTE_DISCLOSURE).toContain("NOT NMDC INFRASTRUCTURE");
    expect(ROUTE_DISCLOSURE).toContain("SYNTHETIC");
    const doc = toSceneRoutesDocument(CONFIG);
    expect(doc._provenance.source).toBe("SYNTHETIC_FOR_DEMO");
    expect(doc._provenance.frame).toBe("SCENE_METRES");
    for (const word of ["GNSS", "GPS", "SURVEYED", "HARDWARE"]) {
      expect(doc._provenance.disclosure.toUpperCase()).not.toContain(word);
    }
  });
});

describe("the exported contract the backend follows is not stale", () => {
  it("contracts/scene_routes.json equals what demoRoutes() generates now", () => {
    const committed = JSON.parse(readFileSync(CONTRACT_PATH, "utf-8"));
    const generated = JSON.parse(JSON.stringify(toSceneRoutesDocument(CONFIG)));
    // If this fails: npx vite-node scripts/exportSceneRoutes.ts
    expect(committed).toEqual(generated);
  });
});

describe("8-10. terrain conformance", () => {
  const samples = ROUTES.flatMap((r) =>
    r.waypoints.filter((_, i) => i % 5 === 0).map((w) => ({ id: r.routeId, w })),
  );

  it("8. a truck's vertical is derived from the sampled terrain surface", () => {
    for (const { w } of samples) {
      const ground = terrainSurfaceY(GRID, w[0], w[1]);
      expect(Number.isFinite(ground)).toBe(true);
      expect(vehicleSurfaceY(GRID, w[0], w[1])).toBeCloseTo(
        ground + VEHICLE_CLEARANCE_M * GRID.verticalExaggeration,
        6,
      );
    }
  });

  it("9. it does not float: clearance is small relative to the truck", () => {
    expect(VEHICLE_CLEARANCE_M).toBeGreaterThan(0);
    expect(VEHICLE_CLEARANCE_M).toBeLessThan(2);
  });

  it("10. it does not sink: the underside is never below the drawn ground", () => {
    for (const { id, w } of samples) {
      expect(vehicleSurfaceY(GRID, w[0], w[1]), id).toBeGreaterThan(
        terrainSurfaceY(GRID, w[0], w[1]),
      );
    }
  });

  it("the vertical is not a constant - the ground actually varies along the route", () => {
    const heights = samples.map(({ w }) => terrainSurfaceY(GRID, w[0], w[1]));
    expect(Math.max(...heights) - Math.min(...heights)).toBeGreaterThan(10);
  });
});

describe("14. no presentation component animates a truck on its own", () => {
  const presentation = readdirSync(MINECAST_DIR).filter((n) => n.endsWith(".tsx"));

  it("no .tsx holds waypoints, a route speed, or a time-driven position", () => {
    for (const name of presentation) {
      const source = readFileSync(join(MINECAST_DIR, name), "utf-8")
        .replace(/\/\*[\s\S]*?\*\//g, "")
        .replace(/^\s*\/\/.*$/gm, "");
      expect(source, name).not.toMatch(/waypoints?\s*[:=]/i);
      expect(source, name).not.toMatch(/speedMps\s*\*|\*\s*speedMps/);
      expect(source, name).not.toMatch(/Date\.now\(\)|performance\.now\(\)|useFrame\(/);
      expect(source, name).not.toContain("Math.random");
      expect(source, name).not.toMatch(/\bxM\s*[:=]\s*-?\d|\byM\s*[:=]\s*-?\d/);
    }
  });

  it("the renderer takes the vertical from the placement helper, not a constant", () => {
    const markers = readFileSync(join(MINECAST_DIR, "VehicleMarkers.tsx"), "utf-8");
    expect(markers).toContain("vehicleSurfaceY(grid, x, y)");
    expect(markers).not.toMatch(/position=\{\[x,\s*\d+(\.\d+)?,\s*y\]\}/);
  });
});
