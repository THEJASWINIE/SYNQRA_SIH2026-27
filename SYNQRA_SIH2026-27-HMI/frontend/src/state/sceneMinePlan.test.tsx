/**
 * CONTROL-ROOM-DIGITAL-TWIN-MINE-ROUTES-02 — one mine domain, two renderers.
 *
 * SOFTWARE ONLY. Every coordinate below is synthetic demonstration geometry; nothing is a
 * surveyed NMDC route, bench, stockpile or dump, and nothing is hardware verification.
 *
 * The backend follower (`scene_position_sim.py`) is asserted by
 * `tests/test_scene_position_contract.py`; here the route DOMAIN, the exported contract,
 * the 2D plan and the 3D inputs are proven to share one geometry.
 */

import { readFileSync } from "node:fs";
import { join } from "node:path";
import { renderToString } from "react-dom/server";
import { describe, expect, it } from "vitest";

import type { PositionScene, VehicleState } from "../contracts/domain";
import { demoRoutes, ROUTE_ID, ROUTE_METADATA } from "../minecast/demoRoutes";
import { CORRIDOR_ID, haulCorridors } from "../minecast/haulRoads";
import { projectMineCast } from "../minecast/minecastProjection";
import { mineZones, zoneOfKind } from "../minecast/mineZones";
import { inwardnessAt } from "../minecast/pitMorphology";
import { spatialPositions } from "../minecast/spatialPosition";
import { elevationAt, sampleHeightGrid } from "../minecast/terrainField";
import { terrainSurfaceY, vehicleSurfaceY } from "../minecast/vehiclePlacement";
import { GeoSiteMap } from "../screens/GeoSiteMap";
import { bailadilaDeposit5 } from "./geoSite";
import {
  arrowMarks,
  BENCH_MODEL_LABEL,
  groundContours,
  PLAN_DISCLOSURE,
  planProjection,
  planScaleBar,
  ROUTE_CLASSIFICATION,
  routeCorridorIds,
  sceneMinePlan,
} from "./sceneMinePlan";
import { AppStateStore } from "./store";
import {
  drawableScenePose,
  fleetPositions,
  providerForMode,
  SCENE_FRAME,
  TWIN_SCENE_LABEL,
} from "./vehiclePosition";

const SITE = bailadilaDeposit5();
const PLAN = sceneMinePlan(SITE.extent);
const CONFIG = PLAN.config;
const T = "2026-09-14T12:00:00.000Z";
const CONTRACT = JSON.parse(
  readFileSync(join(__dirname, "..", "..", "..", "contracts", "scene_routes.json"), "utf-8"),
) as {
  _provenance: Record<string, unknown>;
  routes: {
    route_id: string;
    vehicle_id: string;
    waypoints: [number, number][];
    metadata: Record<string, string>;
    classification: string;
    legs: unknown[];
  }[];
};

const REQUIRED_ROUTE_IDS = [
  "SYNTH-HAUL-MAIN",
  "SYNTH-PIT-RAMP-01",
  "SYNTH-LOADING-LOOP-01",
  "SYNTH-ORE-DISPATCH-01",
  "SYNTH-SERVICE-01",
];

type XY = readonly [number, number];

function scene(xM: number, yM: number, routeId: string, headingRad = 0.4): PositionScene {
  return {
    xM,
    yM,
    headingRad,
    frame: SCENE_FRAME,
    status: "VALID",
    source: "SIMULATION",
    origin: "SIMULATION",
    provenanceLabel: TWIN_SCENE_LABEL,
    method: "DIGITAL_TWIN_SCENE_SIM",
    reason: "Digital Twin demonstration position in SCENE_METRES.",
    routeId,
    routeDirection: 1,
    routeClassification: ROUTE_CLASSIFICATION,
  };
}

function vehicle(id: string, positionScene: PositionScene): VehicleState {
  return {
    vehicleId: id,
    mode: "NORMAL",
    vehicleKind: "DUMPER",
    speedMps: 6.1,
    position: { x: null, y: null, segmentId: null, offsetM: null },
    positionScene,
    accelMps2: null,
    gradeRad: null,
    commConfidence: null,
    frictionEst: null,
    routeId: null,
    timestamp: T,
    provenance: {} as never,
  } as VehicleState;
}

/** A point on a route, taken from the route itself. */
function onRoute(routeId: string, index: number): XY {
  const route = PLAN.routes.find((r) => r.routeId === routeId);
  return route?.waypoints[index] as XY;
}

const T01_XY = onRoute(ROUTE_ID.T01, 40);
const T02_XY = onRoute(ROUTE_ID.T02, 12);
const T01 = vehicle("TRUCK_01", scene(T01_XY[0], T01_XY[1], ROUTE_ID.T01));
const T02 = vehicle("TRUCK_02", scene(T02_XY[0], T02_XY[1], ROUTE_ID.T02));

function distanceToPolyline(p: XY, line: readonly XY[]): number {
  let best = Number.POSITIVE_INFINITY;
  for (let i = 1; i < line.length; i += 1) {
    const [ax, ay] = line[i - 1] as XY;
    const [bx, by] = line[i] as XY;
    const dx = bx - ax;
    const dy = by - ay;
    const len2 = dx * dx + dy * dy;
    const t =
      len2 === 0 ? 0 : Math.max(0, Math.min(1, ((p[0] - ax) * dx + (p[1] - ay) * dy) / len2));
    best = Math.min(best, Math.hypot(p[0] - (ax + dx * t), p[1] - (ay + dy * t)));
  }
  return best;
}

function source(rel: string): string {
  return readFileSync(join(__dirname, rel), "utf-8")
    .replace(/\/\*[\s\S]*?\*\//g, "")
    .replace(/^\s*\/\/.*$/gm, "");
}

// ===========================================================================

describe("ROUTE DOMAIN", () => {
  it("all required route ids exist, once, with engineering labels", () => {
    expect(PLAN.corridors.map((c) => c.id)).toEqual(REQUIRED_ROUTE_IDS);
    expect(new Set(PLAN.corridors.map((c) => c.id)).size).toBe(REQUIRED_ROUTE_IDS.length);
    expect(PLAN.corridors.map((c) => c.planLabel)).toEqual([
      "MAIN HAUL",
      "PIT RAMP 01",
      "LOADING LOOP",
      "ORE DISPATCH",
      "SERVICE ROAD",
    ]);
  });

  it("route waypoints are finite and inside the scene", () => {
    for (const road of PLAN.corridors) {
      for (const p of road.centreline) {
        expect(
          Number.isFinite(p.x) && Number.isFinite(p.y) && Number.isFinite(p.elevationM),
          road.id,
        ).toBe(true);
        expect(p.x, road.id).toBeGreaterThanOrEqual(0);
        expect(p.x, road.id).toBeLessThanOrEqual(CONFIG.widthM);
        expect(p.y, road.id).toBeGreaterThanOrEqual(0);
        expect(p.y, road.id).toBeLessThanOrEqual(CONFIG.heightM);
      }
    }
    for (const route of PLAN.routes) {
      for (const [x, y] of route.waypoints) {
        expect(Number.isFinite(x) && Number.isFinite(y)).toBe(true);
      }
    }
  });

  it("route segments have valid lengths: no zero-length, no teleport", () => {
    for (const route of PLAN.routes) {
      for (let i = 1; i < route.waypoints.length; i += 1) {
        const [ax, ay] = route.waypoints[i - 1] as XY;
        const [bx, by] = route.waypoints[i] as XY;
        const len = Math.hypot(bx - ax, by - ay);
        expect(len, `${route.routeId} segment ${i}`).toBeGreaterThan(0);
        expect(len, `${route.routeId} segment ${i}`).toBeLessThan(220);
      }
      expect(route.lengthM).toBeGreaterThan(1000);
    }
  });

  it("routes are deterministic", () => {
    expect(JSON.stringify(sceneMinePlan(SITE.extent).routes)).toBe(JSON.stringify(PLAN.routes));
    expect(JSON.stringify(haulCorridors(CONFIG))).toBe(JSON.stringify(haulCorridors(CONFIG)));
    const shared =
      source("../minecast/mineZones.ts") +
      source("../minecast/haulRoads.ts") +
      source("../minecast/demoRoutes.ts") +
      source("sceneMinePlan.ts");
    expect(shared).not.toMatch(/Math\.random|Date\.now|performance\.now/);
  });

  it("topology is connected where intended: legs meet at shared junction points", () => {
    const byId = new Map(PLAN.corridors.map((c) => [c.id, c]));
    const main = byId.get(CORRIDOR_ID.MAIN)!;
    const ramp = byId.get(CORRIDOR_ID.RAMP)!;
    const loop = byId.get(CORRIDOR_ID.LOOP)!;
    const dispatch = byId.get(CORRIDOR_ID.DISPATCH)!;
    const service = byId.get(CORRIDOR_ID.SERVICE)!;
    const at = (c: typeof main, j: string) => c.centreline[c.junctions[j] as number]!;
    const same = (a: { x: number; y: number }, b: { x: number; y: number }) =>
      expect(Math.hypot(a.x - b.x, a.y - b.y)).toBeLessThan(1e-6);
    same(at(main, "ACCESS"), at(ramp, "ACCESS"));
    same(at(ramp, "FOOT"), at(loop, "FOOT"));
    same(at(main, "RIM_END"), at(dispatch, "RIM"));
    same(at(main, "SERVICE"), at(service, "MAIN"));
    // The loop closes on itself, so a truck circles the working area and leaves as it came.
    same(loop.centreline[0]!, loop.centreline[loop.centreline.length - 1]!);
    // The loop is ON the pit floor; the surface roads are OUTSIDE the rim.
    for (const p of loop.centreline) {
      expect(inwardnessAt(p.x, p.y, CONFIG.pit)).toBeGreaterThanOrEqual(0.97);
    }
    for (const road of [main, dispatch, service]) {
      for (const p of road.centreline) {
        expect(inwardnessAt(p.x, p.y, CONFIG.pit), road.id).toBeLessThan(-0.03);
      }
    }
  });

  it("the ramp connects bench elevations and the roads end at zone toes", () => {
    const ramp = PLAN.corridors.find((c) => c.kind === "RAMP")!;
    expect(ramp.startElevationM - ramp.endElevationM).toBeGreaterThan(CONFIG.pitDepthM * 0.6);
    const zones = mineZones(CONFIG);
    const stock = zoneOfKind(zones, "STOCKPILE");
    const dump = zoneOfKind(zones, "WASTE_DUMP");
    const dispatch = PLAN.corridors.find((c) => c.kind === "DISPATCH")!;
    const service = PLAN.corridors.find((c) => c.kind === "SERVICE")!;
    const endOf = (c: typeof dispatch) => c.centreline[c.centreline.length - 1]!;
    const touches = (poly: readonly { x: number; y: number }[], p: { x: number; y: number }) =>
      poly.some((q) => Math.hypot(q.x - p.x, q.y - p.y) < 1e-6);
    expect(touches(stock.polygon, endOf(dispatch))).toBe(true);
    expect(touches(dump.polygon, endOf(service))).toBe(true);
    // Zones never intrude into the pit; the active area is on the floor.
    for (const z of [stock, dump]) {
      for (const p of z.polygon)
        expect(inwardnessAt(p.x, p.y, CONFIG.pit), z.id).toBeLessThan(-0.1);
    }
    for (const p of zoneOfKind(zones, "ACTIVE_AREA").polygon) {
      expect(inwardnessAt(p.x, p.y, CONFIG.pit)).toBeGreaterThan(1);
    }
  });
});

describe("VEHICLE ROUTING", () => {
  it("T01 follows its declared route through ramp, loop, rim road and dispatch", () => {
    const t01 = PLAN.routes.find((r) => r.vehicleId === "TRUCK_01")!;
    expect(t01.routeId).toBe(ROUTE_ID.T01);
    expect(t01.behaviour).toBe("LOOP");
    expect(t01.legs.map((l) => l.corridorId)).toEqual([
      CORRIDOR_ID.RAMP,
      CORRIDOR_ID.LOOP,
      CORRIDOR_ID.RAMP,
      CORRIDOR_ID.MAIN,
      CORRIDOR_ID.DISPATCH,
      CORRIDOR_ID.DISPATCH,
      CORRIDOR_ID.MAIN,
    ]);
  });

  it("T02 follows a different, coherent route: dump -> service -> main -> dispatch", () => {
    const t02 = PLAN.routes.find((r) => r.vehicleId === "TRUCK_02")!;
    expect(t02.routeId).toBe(ROUTE_ID.T02);
    expect(t02.behaviour).toBe("PING_PONG");
    expect(t02.legs.map((l) => l.corridorId)).toEqual([
      CORRIDOR_ID.SERVICE,
      CORRIDOR_ID.MAIN,
      CORRIDOR_ID.DISPATCH,
    ]);
    expect(t02.routeId).not.toBe(ROUTE_ID.T01);
  });

  it("every route waypoint sits on a corridor centreline the route declares", () => {
    for (const route of PLAN.routes) {
      const lines = route.corridorIds.map((id) =>
        PLAN.corridors.find((c) => c.id === id)!.centreline.map((p) => [p.x, p.y] as const),
      );
      for (const wp of route.waypoints) {
        expect(
          Math.min(...lines.map((line) => distanceToPolyline(wp, line))),
          route.routeId,
        ).toBeLessThan(1e-6);
      }
    }
  });

  it("the exported contract the backend follows equals the domain", () => {
    expect(CONTRACT.routes.map((r) => r.route_id)).toEqual(PLAN.routes.map((r) => r.routeId));
    for (const exported of CONTRACT.routes) {
      const route = PLAN.routes.find((r) => r.routeId === exported.route_id)!;
      expect(exported.waypoints.length).toBe(route.waypoints.length);
      exported.waypoints.forEach(([x, y], i) => {
        expect(Math.abs(x - (route.waypoints[i] as XY)[0])).toBeLessThan(0.001);
        expect(Math.abs(y - (route.waypoints[i] as XY)[1])).toBeLessThan(0.001);
      });
    }
  });

  it("heading follows the route tangent: the follower has no other heading source", () => {
    const follower = readFileSync(
      join(__dirname, "..", "..", "..", "..", "scene_position_sim.py"),
      "utf-8",
    );
    expect(follower).toContain("math.atan2(");
    expect(follower).not.toMatch(/random\.|time\.time\(\)/);
  });

  it("vehicle elevation follows the route terrain: on the ground, never floating or buried", () => {
    const grid = sampleHeightGrid(CONFIG);
    for (const route of PLAN.routes) {
      for (const [x, y] of route.waypoints.filter((_, i) => i % 7 === 0)) {
        const ground = terrainSurfaceY(grid, x, y);
        const truck = vehicleSurfaceY(grid, x, y);
        expect(Number.isFinite(ground)).toBe(true);
        expect(truck).toBeGreaterThan(ground);
        expect(truck - ground).toBeLessThan(2 * grid.verticalExaggeration);
        expect(Number.isFinite(elevationAt(x, y, CONFIG))).toBe(true);
      }
    }
  });
});

describe("2D", () => {
  const positions = fleetPositions(
    { TRUCK_01: T01, TRUCK_02: T02 },
    providerForMode("LIVE", PLAN.extent),
    PLAN.extent,
  );
  const html = renderToString(
    <GeoSiteMap
      site={SITE}
      positions={positions}
      mode="LIVE"
      selectedVehicleId="TRUCK_01"
      routeEmphasis
    />,
  );

  it("uses the shared route geometry, every route id drawn as a band", () => {
    for (const id of REQUIRED_ROUTE_IDS) expect(html).toContain(`data-corridor-id="${id}"`);
    expect(source("../screens/GeoSiteMap.tsx")).toContain('from "../state/sceneMinePlan"');
  });

  it("is a strict top-down projection with uniform scale and north up", () => {
    const proj = planProjection(PLAN.size, PLAN.extent, 900, 940);
    const a = proj.toSvg({ x: 0, y: 0 });
    const b = proj.toSvg({ x: 1000, y: 0 });
    const c = proj.toSvg({ x: 0, y: 1000 });
    expect(b.x - a.x).toBeCloseTo(a.y - c.y, 9); // 1000 m east == 1000 m north on the page
    expect(c.y).toBeLessThan(a.y); // north is up
    expect(html).toContain('data-projection="TOP_DOWN_ORTHOGRAPHIC"');
    expect(html).toContain('data-frame="SCENE_METRES"');
    expect(html).toContain('aria-label="North"');
    expect(html).toMatch(/data-scale-metres="\d+"/);
    expect(planScaleBar(proj).metres).toBeGreaterThan(0);
  });

  it("has no 3D/perspective transformation, shading or Three.js", () => {
    const code = source("../screens/GeoSiteMap.tsx");
    expect(code).not.toMatch(
      /perspective|matrix3d|rotateX|rotateY|skew|feDropShadow|linearGradient|radialGradient/,
    );
    expect(code).not.toMatch(
      /from ["']three["']|@react-three|MineCanvas|MineScene|terrainShade|slopeAt/,
    );
    expect(html).not.toMatch(/<feDropShadow|<linearGradient|<radialGradient/);
  });

  it("routes render distinctly: band + casing + dashed centreline; labels and arrows on emphasis", () => {
    for (const road of PLAN.corridors) {
      const block =
        new RegExp(`<g data-corridor-id="${road.id}"[\\s\\S]*?</g>`).exec(html)?.[0] ?? "";
      expect((block.match(/<polyline/g) ?? []).length, road.id).toBeGreaterThanOrEqual(3);
      expect(block, road.id).toContain('stroke-dasharray="6 4"');
      expect(html).toContain(`data-route-label="${road.id}"`);
      expect(html).toContain(`${road.planLabel} · SYN`);
    }
    expect(html).toContain('data-route-emphasis="true"');
    expect((html.match(/<polygon points="0,-3.2 6,0 0,3.2"/g) ?? []).length).toBeGreaterThan(10);
    const off = renderToString(<GeoSiteMap site={SITE} positions={positions} mode="LIVE" />);
    expect(off).toContain('data-route-emphasis="false"');
    expect(off).not.toContain("data-route-label=");
  });

  it("benches render distinctly as stepped rings with synthetic display levels", () => {
    expect(html).toContain(`data-bench-model="${BENCH_MODEL_LABEL}"`);
    const crests = PLAN.benches.filter((b) => b.feature.kind === "BENCH");
    expect(crests.length).toBeGreaterThanOrEqual(4);
    for (const bench of crests) {
      expect(html).toContain(`data-bench-level="${bench.displayM}"`);
      expect(html).toContain(bench.label);
    }
    expect(html).toContain('data-feature-id="PIT-01"');
    expect(html).toContain('data-feature-id="FLOOR-01"');
    expect(groundContours(CONFIG).length).toBeGreaterThan(2);
    expect(html).toContain('data-layer="CONTOURS"');
    for (const id of ["ZONE-ACTIVE-01", "ZONE-STOCKPILE-01", "ZONE-DUMP-01"]) {
      expect(html).toContain(`data-zone-id="${id}"`);
    }
    expect(html).toContain("WASTE DUMP");
    expect(html).toContain("ORE STOCKPILE");
    expect(html).toContain("DRAINAGE · SYN");
  });

  it("truck positions match the canonical Twin scene positions, symbol oriented by heading", () => {
    const proj = planProjection(PLAN.size, PLAN.extent, 900, 940);
    for (const v of [T01, T02]) {
      const pose = drawableScenePose(v)!;
      const s = proj.toSvg({ x: pose.xM, y: pose.yM });
      const group =
        new RegExp(`<g data-vehicle-id="${v.vehicleId}"[\\s\\S]*?<text`).exec(html)?.[0] ?? "";
      expect(group).toContain(`translate(${s.x.toFixed(1)} ${s.y.toFixed(1)}) rotate(`);
      expect(html).toContain(`${v.vehicleId} · ${TWIN_SCENE_LABEL}`);
    }
    // Selected truck: ring, route id and direction from the Twin, its route lit.
    expect(html).toMatch(/<g data-vehicle-id="TRUCK_01"[^>]*data-selected="true"/);
    expect(html).toContain(`${ROUTE_ID.T01} · OUTBOUND`);
    for (const id of routeCorridorIds(PLAN, ROUTE_ID.T01)) {
      expect(html).toMatch(new RegExp(`data-corridor-id="${id}"[^>]*data-highlighted="true"`));
    }
    expect(html).not.toMatch(/data-corridor-id="SYNTH-SERVICE-01"[^>]*data-highlighted="true"/);
  });
});

describe("3D", () => {
  const store = new AppStateStore(T, "LIVE");
  store.applyPatch({ changes: { vehicles: { TRUCK_01: T01, TRUCK_02: T02 } } } as never, T);
  const projected = projectMineCast(store.getSnapshot());
  const spatial = spatialPositions(projected.vehicles, projected.site);

  it("uses the shared route geometry: the scene draws haulCorridors(config) and demoRoutes(config)", () => {
    const canvas = source("../minecast/MineCanvas.tsx");
    expect(canvas).toContain("haulCorridors(config)");
    expect(canvas).toContain("demoRoutes(config)");
    expect(canvas).toContain("mineZones(config)");
    expect(source("../minecast/MineScene.tsx")).toContain("<MineZonesLayer");
  });

  it("routes render in SCENE_METRES and vehicles use canonical position_scene", () => {
    for (const p of spatial) {
      expect(p.frame).toBe("SCENE_METRES");
      expect(p.drawableInScene).toBe(true);
      expect(p.lonLat).toBeNull();
    }
    const t01 = spatial.find((p) => p.canonicalVehicleId === "TRUCK_01")!;
    expect(t01.x).toBe(T01.positionScene!.xM);
    expect(t01.y).toBe(T01.positionScene!.yM);
    expect(
      projected.vehicles.find((v) => v.canonicalVehicleId === "TRUCK_01")!.scenePose!.routeId,
    ).toBe(ROUTE_ID.T01);
  });

  it("vehicle elevation is valid and no vehicle floats", () => {
    const grid = sampleHeightGrid(CONFIG);
    for (const p of spatial) {
      const ground = terrainSurfaceY(grid, p.x!, p.y!);
      const y = vehicleSurfaceY(grid, p.x!, p.y!);
      expect(Number.isFinite(y)).toBe(true);
      expect(y - ground).toBeGreaterThan(0);
      expect(y - ground).toBeLessThan(2 * grid.verticalExaggeration);
    }
    expect(source("../minecast/VehicleMarkers.tsx")).toContain("vehicleSurfaceY(grid, x, y)");
  });
});

describe("CROSS-VIEW", () => {
  it("the same route coordinates feed 2D and 3D", () => {
    expect(JSON.stringify(PLAN.corridors)).toBe(JSON.stringify(haulCorridors(CONFIG)));
    expect(JSON.stringify(PLAN.routes)).toBe(JSON.stringify(demoRoutes(CONFIG)));
    expect(JSON.stringify(PLAN.zones)).toBe(JSON.stringify(mineZones(CONFIG)));
  });

  it("the same vehicle scene position feeds 2D and 3D", () => {
    const pose = drawableScenePose(T01)!;
    const twoD = fleetPositions(
      { TRUCK_01: T01 },
      providerForMode("LIVE", PLAN.extent),
      PLAN.extent,
    )[0]!;
    const proj = planProjection(PLAN.size, PLAN.extent, 900, 940);
    const via2d = proj.lonLatToSvg(twoD.position!);
    const direct = proj.toSvg({ x: pose.xM, y: pose.yM });
    expect(Math.hypot(via2d.x - direct.x, via2d.y - direct.y)).toBeLessThan(0.01);
    expect(twoD.routeId).toBe(pose.routeId);
    const store = new AppStateStore(T, "LIVE");
    store.applyPatch({ changes: { vehicles: { TRUCK_01: T01 } } } as never, T);
    const p = projectMineCast(store.getSnapshot());
    const threeD = spatialPositions(p.vehicles, p.site)[0]!;
    expect(threeD.x).toBe(pose.xM);
    expect(threeD.y).toBe(pose.yM);
  });

  it("no duplicated route dataset exists", () => {
    for (const rel of [
      "../screens/GeoSiteMap.tsx",
      "../controlRoom/ControlRoom3DTwin.tsx",
      "../screens/OperationsOverview.tsx",
    ]) {
      expect(source(rel), rel).not.toMatch(/waypoints\s*[:=]\s*\[/);
      expect(source(rel), rel).not.toMatch(/\bxM\s*[:=]\s*\d|\byM\s*[:=]\s*\d/);
    }
  });
});

describe("PROVENANCE", () => {
  it("routes carry SIMULATION / SIMULATED_TWIN_SCENE / SCENE_METRES / DIGITAL_TWIN_SCENE_SIM / SYNTHETIC_DIGITAL_TWIN_ROUTE", () => {
    expect(ROUTE_METADATA).toEqual({
      source: "SIMULATION",
      provenance: "SIMULATED_TWIN_SCENE",
      frame: "SCENE_METRES",
      method: "DIGITAL_TWIN_SCENE_SIM",
      classification: "SYNTHETIC_DIGITAL_TWIN_ROUTE",
    });
    for (const route of PLAN.routes) expect(route.metadata).toEqual(ROUTE_METADATA);
    for (const exported of CONTRACT.routes) {
      expect(exported.metadata).toEqual(ROUTE_METADATA);
      expect(exported.classification).toBe("SYNTHETIC_DIGITAL_TWIN_ROUTE");
    }
    expect(CONTRACT._provenance.route_classification).toBe("SYNTHETIC_DIGITAL_TWIN_ROUTE");
  });

  it("routes and zones are synthetic and unverified", () => {
    for (const c of PLAN.corridors) {
      expect(c.source).toBe("SYNTHETIC_FOR_DEMO");
      expect(c.verified).toBe(false);
      expect(c.confidence).toBe("LOW");
      expect(c.routeClassification).toBe("SYNTHETIC_DIGITAL_TWIN_ROUTE");
      expect(c.label.toLowerCase()).toContain("synthetic");
    }
    for (const z of PLAN.zones) {
      expect(z.source).toBe("SYNTHETIC_FOR_DEMO");
      expect(z.verified).toBe(false);
      expect(z.label.toLowerCase()).toContain("synthetic");
    }
    expect(PLAN_DISCLOSURE).toEqual({
      twin: "DIGITAL TWIN · SIMULATION",
      frame: "SCENE_METRES",
      routes: "SYNTHETIC ROUTES · NOT SURVEYED",
      infrastructure: "NOT NMDC INFRASTRUCTURE",
      benches: "SYNTHETIC BENCH MODEL",
    });
  });

  it("no route is labelled as verified NMDC infrastructure, in code or on screen", () => {
    const FORBIDDEN = [
      "NMDC ROAD",
      "NMDC HAUL",
      "OFFICIAL",
      "SURVEYED ROAD",
      "REAL HAUL",
      "GPS",
      "AUTHORITATIVE",
      "VERIFIED ROUTE",
      "ACTUAL NMDC",
    ];
    for (const c of PLAN.corridors) {
      const words = `${c.id} ${c.label} ${c.planLabel}`.toUpperCase();
      for (const f of FORBIDDEN) expect(words, `${c.id} / ${f}`).not.toContain(f);
    }
    for (const r of PLAN.routes) {
      const words = `${r.routeId} ${r.label}`.toUpperCase();
      for (const f of FORBIDDEN) expect(words, `${r.routeId} / ${f}`).not.toContain(f);
    }
    const html = renderToString(
      <GeoSiteMap site={SITE} positions={[]} mode="LIVE" routeEmphasis />,
    );
    expect(html).toContain("SYNTHETIC ROUTES · NOT SURVEYED");
    expect(html).toContain("NOT NMDC INFRASTRUCTURE");
    expect(html).toContain("DIGITAL TWIN · SIMULATION");
    expect(html).toContain("PUBLISHED LEASE COORDINATE EXTENT — not a lease boundary");
    for (const f of ["NMDC ROAD", "NMDC HAUL ROAD", "SURVEYED ROUTE", "VERIFIED ROUTE"]) {
      expect(html.toUpperCase()).not.toContain(f);
    }
  });

  it("direction arrows follow the route and are placed along it", () => {
    const route = PLAN.routes[0]!;
    const marks = arrowMarks(
      route.waypoints.map(([x, y]) => ({ x, y })),
      240,
    );
    expect(marks.length).toBeGreaterThan(20);
    for (const m of marks) {
      expect(distanceToPolyline([m.x, m.y], route.waypoints)).toBeLessThan(1e-6);
      expect(Number.isFinite(m.angleRad)).toBe(true);
    }
  });
});

describe("SPEED SYNCHRONIZATION (DIGITAL-TWIN-OPERATIONAL-FLOW-01)", () => {
  it("no renderer independently calculates vehicle speed - it is displayed from the Twin only", () => {
    for (const rel of [
      "../screens/GeoSiteMap.tsx",
      "../screens/OperationsOverview.tsx",
      "../controlRoom/ControlRoom3DTwin.tsx",
      "../minecast/VehicleMarkers.tsx",
      "../minecast/VehicleCallout.tsx",
      "../vehicle/DriverScreen.tsx",
    ]) {
      const code = source(rel);
      // No delta-position-over-time speed, no unit conversion invented from RPM, no clock.
      expect(code, rel).not.toMatch(/\/\s*(deltaT|deltaS|elapsedS|dtS)\b/);
      expect(code, rel).not.toMatch(/speedMps\s*=\s*[^=]/);
      expect(code, rel).not.toMatch(/rpm\s*\*|\*\s*rpm|wheelRadius|WHEEL_RADIUS/);
      expect(code, rel).not.toMatch(/Date\.now\(\)|performance\.now\(\)/);
    }
  });

  it("the route contract declares the constant speed the backend advances the pose at", () => {
    for (const exported of CONTRACT.routes) {
      const route = PLAN.routes.find((r) => r.routeId === exported.route_id)!;
      expect((exported as unknown as { speed_mps: number }).speed_mps).toBe(route.speedMps);
      expect(route.speedMps).toBeGreaterThan(0);
    }
  });
});

// ===========================================================================

describe("PLAN SHEET IS THE PUBLISHED EXTENT (nothing beyond it is drawn)", () => {
  const positions = fleetPositions(
    { TRUCK_01: T01, TRUCK_02: T02 },
    providerForMode("LIVE", PLAN.extent),
    PLAN.extent,
  );
  const html = renderToString(<GeoSiteMap site={SITE} positions={positions} mode="LIVE" />);
  const viewBox = /viewBox="0 0 (\d+) (\d+)"/.exec(html);

  it("the viewBox has the extent's own aspect, so the extent fills the sheet", () => {
    expect(viewBox).not.toBeNull();
    const [, w, h] = viewBox as RegExpExecArray;
    const sheetAspect = Number(w) / Number(h);
    const extentAspect = PLAN.size.widthM / PLAN.size.heightM;
    expect(Math.abs(sheetAspect - extentAspect)).toBeLessThan(0.01);
    const proj = planProjection(PLAN.size, PLAN.extent, Number(w), Number(h));
    // The extent box sits within a few units of the margin on every side: no blank band.
    expect(proj.box.x).toBeLessThan(32);
    expect(proj.box.y).toBeLessThan(32);
    expect(proj.box.x + proj.box.width).toBeGreaterThan(Number(w) - 32);
    expect(proj.box.y + proj.box.height).toBeGreaterThan(Number(h) - 32);
  });

  it("the sheet is fitted, never cropped, and everything is clipped to it", () => {
    expect(html).toContain('preserveAspectRatio="xMidYMid meet"');
    expect(html).toContain('<clipPath id="cr-sheet-clip">');
    expect(html).toContain('clip-path="url(#cr-sheet-clip)"');
    // Nothing is sampled beyond the scene: the grid and contours stay inside the extent.
    for (const c of PLAN.contours) {
      for (const line of c.polylines) {
        for (const p of line) {
          expect(p.x).toBeGreaterThanOrEqual(0);
          expect(p.x).toBeLessThanOrEqual(PLAN.size.widthM);
          expect(p.y).toBeGreaterThanOrEqual(0);
          expect(p.y).toBeLessThanOrEqual(PLAN.size.heightM);
        }
      }
    }
  });

  it("the sheet sets its own width from its height, so the map column can fit it", () => {
    // Server render: no frame yet, no width forced (the CSS aspect fit still applies).
    expect(html).not.toContain("data-sheet-width=");
    const src = source("../screens/GeoSiteMap.tsx");
    expect(src).toMatch(/ResizeObserver/);
    expect(src).toMatch(/Math\.floor\(\(h \* VIEW_W\) \/ VIEW_H\)/);
    // Never stretched: the aspect fit stays, the width only ever matches it.
    expect(html).not.toContain('preserveAspectRatio="none"');
  });
});
