/**
 * GeoSiteMap — own-vehicle emphasis and CONTROL-ROOM-MINECAST-MAP-SYNC-01 tests.
 *
 * `renderToString` in the Node environment (no DOM).
 *
 * SOFTWARE ONLY: The positions and geometry here are demonstration fixtures;
 * no hardware verification is claimed.
 */

import { execSync } from "node:child_process";
import { readFileSync } from "node:fs";
import { join } from "node:path";
import { renderToString } from "react-dom/server";
import { describe, expect, it } from "vitest";

import type { PositionScene, VehicleState } from "../contracts/domain";
import { bailadilaDeposit5, toDecimalExtent } from "../state/geoSite";
import {
  CORRIDOR_DISCLOSURE,
  getSceneCorridors,
} from "../state/sceneCorridors";
import {
  SCENE_FRAME,
  twinScenePosition,
  type VehiclePosition,
} from "../state/vehiclePosition";
import { GeoSiteMap } from "./GeoSiteMap";

const SITE = bailadilaDeposit5();
const EXTENT = toDecimalExtent(SITE.extent);
const INSIDE = {
  lon: (EXTENT.west + EXTENT.east) / 2,
  lat: (EXTENT.north + EXTENT.south) / 2,
};

function synthetic(vehicleId: string): VehiclePosition {
  return { vehicleId, position: INSIDE, provenance: "SOFTWARE_ONLY_SYNTHETIC" };
}

function scenePose(xM: number, yM: number, headingRad: number | null = 0.52): PositionScene {
  return {
    xM,
    yM,
    headingRad,
    frame: SCENE_FRAME,
    status: "VALID",
    source: "SIMULATION",
    origin: "SIMULATION",
    provenanceLabel: "SIMULATION · DIGITAL TWIN",
    method: "DIGITAL_TWIN_SCENE_SIM",
    reason: "Digital Twin demonstration position in SCENE_METRES.",
  };
}

function vehicleWithScene(id: string, pose: PositionScene): VehicleState {
  return {
    vehicleId: id,
    mode: "NORMAL",
    vehicleKind: "DUMPER",
    speedMps: 6.5,
    position: { x: null, y: null, segmentId: null, offsetM: null },
    positionScene: pose,
    accelMps2: null,
    gradeRad: null,
    commConfidence: null,
    frictionEst: null,
    routeId: null,
    timestamp: "2026-09-14T12:00:00.000Z",
    provenance: {} as never,
  } as VehicleState;
}

function readCleanSource(rel: string): string {
  return readFileSync(join(__dirname, rel), "utf-8")
    .replace(/\/\*[\s\S]*?\*\//g, "")
    .replace(/^\s*\/\/.*$/gm, "");
}

describe("GeoSiteMap own-vehicle emphasis", () => {
  const fleet = [synthetic("TRUCK_02"), synthetic("TRUCK_01")];

  it("rings and labels only the console's own vehicle", () => {
    const html = renderToString(
      <GeoSiteMap site={SITE} positions={fleet} mode="MOCK" ownVehicleId="TRUCK_02" />,
    );
    expect(html).toContain("THIS VEHICLE · TRUCK_02");
    expect(html).not.toContain("THIS VEHICLE · TRUCK_01");
    expect((html.match(/data-own-vehicle="true"/g) ?? []).length).toBe(1);
    // The peer is still drawn, as the fleet, with its own provenance.
    expect(html).toContain("TRUCK_01 · SOFTWARE TEST · SYNTHETIC GNSS");
  });

  it("draws no ring when no own vehicle is named (control room)", () => {
    const html = renderToString(<GeoSiteMap site={SITE} positions={fleet} mode="MOCK" />);
    expect(html).not.toContain("THIS VEHICLE");
    expect(html).not.toContain("data-own-vehicle");
  });

  it("lists an own vehicle without a position rather than placing it", () => {
    const html = renderToString(
      <GeoSiteMap
        site={SITE}
        positions={[
          { vehicleId: "TRUCK_01", position: null, provenance: "UNAVAILABLE", reason: "no fix" },
        ]}
        mode="LIVE"
        ownVehicleId="TRUCK_01"
      />,
    );
    expect(html).toContain("POSITION UNAVAILABLE (1)");
    expect(html).not.toContain("THIS VEHICLE");
  });
});

describe("TASK: CONTROL-ROOM-MINECAST-MAP-SYNC-01 — 12 Acceptance Criteria", () => {
  const sceneCorridors = getSceneCorridors(SITE.extent);

  it("1. GeoSiteMap consumes the same canonical/shared corridor geometry source used by Mine-Cast", () => {
    const html = renderToString(<GeoSiteMap site={SITE} positions={[]} mode="LIVE" />);

    // All 4 canonical corridors are present in the DOM
    expect(html).toContain('data-corridor-id="SYNTH-HAUL-MAIN"');
    expect(html).toContain('data-corridor-id="SYNTH-PIT-RAMP-01"');
    expect(html).toContain('data-corridor-id="SYNTH-LOADING-LOOP-01"');
    expect(html).toContain('data-corridor-id="SYNTH-ORE-DISPATCH-01"');
    expect(html).toContain('data-corridor-id="SYNTH-SERVICE-01"');

    // Canonical pit features are present
    expect(html).toContain('data-feature-id="PIT-01"');
    expect(html).toContain('data-feature-id="FLOOR-01"');

    // Corridor count matches canonical calculation
    expect(sceneCorridors.corridors.length).toBe(5);
    expect(sceneCorridors.corridors.map((c) => c.id)).toEqual([
      "SYNTH-HAUL-MAIN",
      "SYNTH-PIT-RAMP-01",
      "SYNTH-LOADING-LOOP-01",
      "SYNTH-ORE-DISPATCH-01",
      "SYNTH-SERVICE-01",
    ]);
  });

  it("2. S1 does not contain duplicated Mine-Cast corridor geometry", () => {
    const s1Code = readCleanSource("GeoSiteMap.tsx");
    // No hardcoded coordinate arrays or Beziers in S1 GeoSiteMap
    expect(s1Code).not.toMatch(/bezierPath|rampCentreline|crestContourAt/);
    expect(s1Code).not.toMatch(/\[193\.439,\s*271\.72\]/);
    expect(s1Code).toContain('from "../state/sceneCorridors"');
  });

  it("3. Scene coordinates remain SCENE_METRES", () => {
    for (const c of sceneCorridors.corridors) {
      for (const pt of c.centreline) {
        expect(pt.x).toBeGreaterThanOrEqual(0);
        expect(pt.x).toBeLessThanOrEqual(sceneCorridors.size.widthM + 1);
        expect(pt.y).toBeGreaterThanOrEqual(0);
        expect(pt.y).toBeLessThanOrEqual(sceneCorridors.size.heightM + 1);
        expect(Number.isFinite(pt.elevationM)).toBe(true);
      }
    }
  });

  it("4. No fake geographic coordinates are generated in S1", () => {
    const mapCode = readCleanSource("GeoSiteMap.tsx");
    expect(mapCode).not.toMatch(/lat:\s*1[89]\.\d/);
    expect(mapCode).not.toMatch(/lon:\s*8[01]\.\d/);
    expect(mapCode).not.toMatch(/\bxM:\s*\d|\byM:\s*\d/);
  });

  it("5. Vehicle positions still come from canonical position_scene", () => {
    const v1 = vehicleWithScene("TRUCK_01", scenePose(1150, 2380));
    const pos = twinScenePosition(v1, EXTENT);
    expect(pos).not.toBeNull();
    expect(pos?.provenance).toBe("SIMULATED_TWIN_SCENE");

    const html = renderToString(
      <GeoSiteMap site={SITE} positions={[pos as VehiclePosition]} mode="LIVE" />,
    );
    expect(html).toContain("TRUCK_01 · SIMULATION · DIGITAL TWIN");
  });

  it("6. T01/T02 identity remains vehicleId-based (no array index)", () => {
    const pos1 = twinScenePosition(vehicleWithScene("TRUCK_01", scenePose(1150, 2380)), EXTENT)!;
    const pos2 = twinScenePosition(vehicleWithScene("TRUCK_02", scenePose(2048, 736)), EXTENT)!;
    const html = renderToString(
      <GeoSiteMap site={SITE} positions={[pos1, pos2]} mode="LIVE" />,
    );
    expect(html).toContain('data-vehicle-id="TRUCK_01"');
    expect(html).toContain('data-vehicle-id="TRUCK_02"');
    expect(html).not.toMatch(/data-vehicle-index/);
  });

  it("7. Heading is rendered only when canonical heading is finite", () => {
    const withHeading = twinScenePosition(
      vehicleWithScene("TRUCK_01", scenePose(1150, 2380, 0.78)),
      EXTENT,
    )!;
    const withoutHeading = twinScenePosition(
      vehicleWithScene("TRUCK_02", scenePose(2048, 736, null)),
      EXTENT,
    )!;

    const htmlWith = renderToString(
      <GeoSiteMap site={SITE} positions={[withHeading]} mode="LIVE" />,
    );
    const htmlWithout = renderToString(
      <GeoSiteMap site={SITE} positions={[withoutHeading]} mode="LIVE" />,
    );

    // Truck with heading has a line element inside its vehicle group
    expect(htmlWith).toMatch(/<g[^>]*data-vehicle-id="TRUCK_01"[^>]*>[\s\S]*?<line/);
    // Truck without heading has NO line element inside its vehicle group
    expect(htmlWithout).not.toMatch(/<g[^>]*data-vehicle-id="TRUCK_02"[^>]*>[\s\S]*?<line/);
  });

  it("8. Synthetic corridor disclosure remains present", () => {
    const html = renderToString(<GeoSiteMap site={SITE} positions={[]} mode="LIVE" />);
    expect(html).toContain("SYNTHETIC OPERATIONAL CORRIDORS · NOT NMDC INFRASTRUCTURE · DEMONSTRATION");
    expect(CORRIDOR_DISCLOSURE).toBe("SYNTHETIC OPERATIONAL CORRIDORS · NOT NMDC INFRASTRUCTURE");
  });

  it("9. Published extent remains explicitly NOT A LEASE BOUNDARY", () => {
    const html = renderToString(<GeoSiteMap site={SITE} positions={[]} mode="LIVE" />);
    expect(html).toContain("PUBLISHED LEASE COORDINATE EXTENT — not a lease boundary");
    expect(html).toContain("ASSUMED_WGS84_UNVERIFIED");
  });

  it("10. S1 contains no Three.js/@react-three/MineScene/MineCanvas dependency", () => {
    for (const rel of ["GeoSiteMap.tsx", "OperationsOverview.tsx"]) {
      const code = readCleanSource(rel);
      expect(code, rel).not.toMatch(/from ["']three["']|@react-three/);
      expect(code, rel).not.toMatch(/MineCanvas|MineScene/);
      expect(code, rel).not.toMatch(/from ["']\.\.?\/minecast\//);
    }
  });

  it("11. No independent fetch/WebSocket/store was introduced", () => {
    for (const rel of ["GeoSiteMap.tsx", "OperationsOverview.tsx"]) {
      const code = readCleanSource(rel);
      expect(code, rel).not.toMatch(/new WebSocket\(/);
      expect(code, rel).not.toMatch(/\bfetch\(/);
      expect(code, rel).not.toMatch(/new AppStateStore\(/);
      expect(code, rel).not.toMatch(/useState<\s*(VehicleState|SafetyState|AppState)\b/);
    }
  });

  it("12. the shared generators under src/minecast/ stay the ONE geometry owner", () => {
    // MINE-ROUTES-02 changed the shared network itself (new route ids, zones, gentler
    // relief), so a git-status freeze on those files no longer describes the invariant.
    // The invariant is: S1 owns no geometry. The plan module imports every generator from
    // src/minecast and the 2D renderer imports only the plan.
    const planCode = readFileSync(join(__dirname, "../state/sceneMinePlan.ts"), "utf-8");
    for (const generator of ["haulRoads", "mineFeatures", "mineZones", "terrainField", "demoRoutes"]) {
      expect(planCode).toContain(`from "../minecast/${generator}"`);
    }
    const mapCode = readCleanSource("GeoSiteMap.tsx");
    expect(mapCode).toContain('from "../state/sceneMinePlan"');
    expect(mapCode).not.toMatch(/catmullRom|rampCentreline|crestContourAt|mineZones\(|haulCorridors\(/);
    expect(execSync("git ls-files src/state/sceneRoutes2D.ts src/minecast/sceneRoutes3D.ts", {
      cwd: join(__dirname, "../.."),
      encoding: "utf-8",
    }).trim()).toBe("");
  });
});
