/**
 * S1 [ 2D MAP ] [ 3D TWIN ] workspace toggle — one operational workspace, two renderers.
 *
 * SOFTWARE ONLY. Fixtures are simulated; nothing here is hardware verification.
 *
 * The Node test environment has no DOM, so clicks are proven through the pure reducer
 * the buttons dispatch to (`workspaceState.ts`), and each resulting mode is rendered
 * with `renderToString` via the `initialWorkspace` prop. Source-level guards keep S1
 * off Mine-Cast's application and store.
 */

import { readdirSync, readFileSync } from "node:fs";
import { join } from "node:path";
import { renderToString } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { freshnessConfig } from "../config/freshness";
import type { PositionScene, VehicleState } from "../contracts/domain";
import { projectMineCast } from "../minecast/minecastProjection";
import { spatialPositions } from "../minecast/spatialPosition";
import { OperationsOverview } from "../screens/OperationsOverview";
import { HmiContext } from "../state/ProviderHost";
import { AppStateStore } from "../state/store";
import { testHmiContext } from "../state/testHmiContext";
import { drawableScenePose, SCENE_FRAME, TWIN_SCENE_LABEL } from "../state/vehiclePosition";
import { ControlRoom3DTwin, TWIN_3D_DISCLOSURES } from "./ControlRoom3DTwin";
import { INITIAL_WORKSPACE, type S1Workspace, workspaceReducer } from "./workspaceState";

const T = "2026-09-14T12:00:00.000Z";
const CONFIG = freshnessConfig(5000);
const HERE = __dirname;
const SCREENS = join(HERE, "..", "screens");

function scene(xM: number, yM: number): PositionScene {
  return {
    xM,
    yM,
    headingRad: 0.52,
    frame: SCENE_FRAME,
    status: "VALID",
    source: "SIMULATION",
    origin: "SIMULATION",
    provenanceLabel: TWIN_SCENE_LABEL,
    method: "DIGITAL_TWIN_SCENE_SIM",
    reason: "Digital Twin demonstration position in SCENE_METRES.",
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

const T01 = vehicle("TRUCK_01", scene(1150, 2380));
const T02 = vehicle("TRUCK_02", scene(2048, 736));

function store(): AppStateStore {
  const s = new AppStateStore(T, "LIVE");
  s.applyPatch({ changes: { vehicles: { TRUCK_01: T01, TRUCK_02: T02 } } } as never, T);
  s.setStatus("CONNECTED", null);
  return s;
}

function renderS1(initialWorkspace?: Partial<S1Workspace>): string {
  const value = testHmiContext({ store: store(), freshness: CONFIG });
  return renderToString(
    <HmiContext.Provider value={value}>
      <OperationsOverview onSelectVehicle={() => {}} initialWorkspace={initialWorkspace} />
    </HmiContext.Provider>,
  );
}

/** The `aria-pressed` value of the toggle button for `mode`. */
function pressed(html: string, mode: "2D" | "3D"): string | undefined {
  return html.match(new RegExp(`data-view-mode="${mode}"[^>]*aria-pressed="([a-z]+)"`))?.[1];
}

function source(path: string): string {
  return readFileSync(path, "utf-8")
    .replace(/\/\*[\s\S]*?\*\//g, "")
    .replace(/^\s*\/\/.*$/gm, "");
}

const S1_SOURCES = [
  join(SCREENS, "OperationsOverview.tsx"),
  join(HERE, "ControlRoom3DTwin.tsx"),
  join(HERE, "workspaceState.ts"),
];

// ===========================================================================

describe("1-4. the toggle", () => {
  it("1. S1 defaults to 2D MAP", () => {
    expect(INITIAL_WORKSPACE.mode).toBe("2D");
    const html = renderS1();
    expect(pressed(html, "2D")).toBe("true");
    expect(pressed(html, "3D")).toBe("false");
    expect(html).toContain("cr-map-workspace");
    expect(html).not.toContain('data-testid="cr-3d-twin"');
  });

  it("2. both buttons render, in one control, directly above the workspace", () => {
    const html = renderS1();
    const toggle = html.match(/<div class="cr-view-toggle"[\s\S]*?<\/div>/)?.[0] ?? "";
    expect(toggle).toContain(">2D MAP<");
    expect(toggle).toContain(">3D TWIN<");
    // Header (with the toggle) precedes the workspace body inside the same centre column.
    expect(html.indexOf("cr-view-toggle")).toBeLessThan(html.indexOf("cr-map-workspace"));
    expect(html.indexOf('aria-label="Digital Twin Workspace"')).toBeLessThan(
      html.indexOf("cr-view-toggle"),
    );
  });

  it("3. clicking 3D TWIN changes only the workspace mode", () => {
    const before: S1Workspace = { mode: "2D", selectedVehicleId: "TRUCK_02", routeEmphasis: false };
    const after = workspaceReducer(before, { type: "SET_MODE", mode: "3D" });
    expect(after).toEqual({ ...before, mode: "3D" });
    // And the rendered 3D mode shows the 3D twin in the same centre column, not a route/page.
    const html = renderS1({ mode: "3D" });
    expect(pressed(html, "3D")).toBe("true");
    expect(html).toContain('data-testid="cr-3d-twin"');
    expect(html).not.toContain("cr-map-workspace");
    expect(html).toContain('aria-label="Digital Twin Workspace"');
    expect(html).not.toMatch(/href="[^"]*mine-cast/);
  });

  it("4. clicking 2D MAP returns to 2D", () => {
    const in3d: S1Workspace = { mode: "3D", selectedVehicleId: "TRUCK_02", routeEmphasis: false };
    expect(workspaceReducer(in3d, { type: "SET_MODE", mode: "2D" })).toEqual({
      ...in3d,
      mode: "2D",
    });
    const html = renderS1({ mode: "2D", selectedVehicleId: "TRUCK_02" });
    expect(html).toContain("cr-map-workspace");
    expect(html).not.toContain('data-testid="cr-3d-twin"');
  });

  it("the buttons dispatch to the reducer and nothing else", () => {
    const s1 = source(join(SCREENS, "OperationsOverview.tsx"));
    expect(s1).toContain('dispatch({ type: "SET_MODE", mode })');
    expect(s1).toContain('dispatch({ type: "SELECT_VEHICLE", vehicleId })');
    expect(s1).not.toMatch(/useState<\s*["']2D["']/);
    expect(s1).not.toMatch(/window\.(open|location)/);
    expect(s1).not.toMatch(/navigate\(/);
  });
});

describe("5-7. architectural boundary", () => {
  it("5. S1 and its 3D view do not import MineCastApp", () => {
    for (const path of S1_SOURCES) {
      expect(source(path), path).not.toMatch(/MineCastApp/);
    }
  });

  it("6. S1 and its 3D view do not import minecastStore / useMineCastStore", () => {
    for (const path of S1_SOURCES) {
      const text = source(path);
      expect(text, path).not.toMatch(/minecastStore/);
      expect(text, path).not.toMatch(/useMineCastStore/);
    }
  });

  it("6b. the only Mine-Cast modules S1 reaches are pure projections / primitives", () => {
    const allowed = new Set([
      "minecastProjection",
      "spatialPosition",
      "terrainField",
      "MineCanvas",
    ]);
    for (const path of S1_SOURCES) {
      const imports = [...source(path).matchAll(/from ["']\.\.\/minecast\/([A-Za-z0-9_]+)["']/g)];
      for (const [, name] of imports) {
        expect(allowed.has(name as string), `${path} imports minecast/${name}`).toBe(true);
      }
    }
  });

  it("6c. Mine-Cast stays independent: nothing in src/minecast imports src/controlRoom", () => {
    const dir = join(HERE, "..", "minecast");
    for (const name of readdirSync(dir).filter((n) => /\.tsx?$/.test(n))) {
      expect(readFileSync(join(dir, name), "utf-8"), name).not.toMatch(/controlRoom\//);
    }
  });

  it("7. no second WebSocket, fetch, store or simulation is created", () => {
    for (const path of S1_SOURCES) {
      const text = source(path);
      expect(text, path).not.toMatch(/new WebSocket\(/);
      expect(text, path).not.toMatch(/\bfetch\(/);
      expect(text, path).not.toMatch(/EventSource\(/);
      expect(text, path).not.toMatch(/new AppStateStore\(/);
      expect(text, path).not.toMatch(/setInterval\(|requestAnimationFrame\(|useFrame\(/);
      expect(text, path).not.toMatch(/Math\.random|Date\.now\(\)/);
      expect(text, path).not.toMatch(/from ["']three["']|@react-three/);
    }
  });
});

describe("8, 11, 12. one canonical state, both renderers", () => {
  it("8. both views read the same AppStateStore through useAppState", () => {
    const s1 = source(join(SCREENS, "OperationsOverview.tsx"));
    const twin3d = source(join(HERE, "ControlRoom3DTwin.tsx"));
    expect(s1).toContain("useAppState()");
    expect(twin3d).toContain("useAppState()");
    expect(twin3d).toContain("projectMineCast(state)");
    // Rendered: the same store yields the same fleet in both modes.
    for (const mode of ["2D", "3D"] as const) {
      const html = renderS1({ mode });
      expect(html, mode).toContain('data-vehicle-id="TRUCK_01"');
      expect(html, mode).toContain('data-vehicle-id="TRUCK_02"');
      expect(html, mode).toContain("TWIN 2 VEHICLES");
    }
  });

  it("11. T01/T02 3D positions are the canonical position_scene, unchanged", () => {
    const value = testHmiContext({ store: store(), freshness: CONFIG });
    const projected = projectMineCast(value.store.getSnapshot());
    const positions = spatialPositions(projected.vehicles, projected.site);
    for (const v of [T01, T02]) {
      const pose = drawableScenePose(v);
      const drawn = positions.find((p) => p.canonicalVehicleId === v.vehicleId);
      expect(pose).not.toBeNull();
      expect(drawn?.drawableInScene).toBe(true);
      expect(drawn?.x).toBe(pose?.xM);
      expect(drawn?.y).toBe(pose?.yM);
      expect(drawn?.x).toBe(v.positionScene?.xM);
      expect(drawn?.y).toBe(v.positionScene?.yM);
      expect(drawn?.lonLat).toBeNull();
    }
    // The 3D component itself carries no coordinates.
    const twin3d = source(join(HERE, "ControlRoom3DTwin.tsx"));
    expect(twin3d).not.toMatch(/\bxM\s*[:=]\s*\d|\byM\s*[:=]\s*\d/);
    expect(twin3d).not.toMatch(/(latitude|longitude|lat|lon|lng)\s*[:=]/i);
    expect(twin3d).not.toMatch(/GPS/);
    // GNSS may appear only as a negation.
    expect(twin3d.replace(/NOT GNSS/g, "")).not.toMatch(/GNSS/);
    expect(twin3d).toContain("spatialPositions(minecast.vehicles, minecast.site)");
  });

  it("12. SCENE_METRES is preserved end to end", () => {
    const value = testHmiContext({ store: store(), freshness: CONFIG });
    const projected = projectMineCast(value.store.getSnapshot());
    for (const p of spatialPositions(projected.vehicles, projected.site)) {
      expect(p.frame).toBe("SCENE_METRES");
    }
    expect(TWIN_3D_DISCLOSURES.frame).toBe("SCENE_METRES");
    const html = renderS1({ mode: "3D" });
    expect(html).toContain("DIGITAL TWIN · SIMULATION · SCENE_METRES");
    expect(html).toContain("SYNTHETIC DEMONSTRATION GEOMETRY");
    expect(html).toContain("VEHICLES: DIGITAL TWIN SIMULATION (SCENE_METRES) · NOT GNSS");
    expect(html).toContain("NOT NMDC INFRASTRUCTURE");
    expect(html).toContain("NOT A LEASE BOUNDARY");
    expect(html).toContain(TWIN_SCENE_LABEL);
  });
});

describe("9-10. selection survives the toggle", () => {
  it("9. selected vehicle survives 2D → 3D", () => {
    let s = workspaceReducer(INITIAL_WORKSPACE, { type: "SELECT_VEHICLE", vehicleId: "TRUCK_02" });
    s = workspaceReducer(s, { type: "SET_MODE", mode: "3D" });
    expect(s).toEqual({ mode: "3D", selectedVehicleId: "TRUCK_02", routeEmphasis: false });
    const html = renderS1(s);
    expect(html).toMatch(/cr-fleet-card-wrapper cr-selected"[^>]*data-vehicle-id="TRUCK_02"/);
    expect(html).toMatch(/<div class="cr-selected-body" data-vehicle-id="TRUCK_02"/);
    expect(html).toContain('data-testid="cr-3d-twin"');
  });

  it("10. selected vehicle survives 3D → 2D", () => {
    let s: S1Workspace = { mode: "3D", selectedVehicleId: null, routeEmphasis: false };
    s = workspaceReducer(s, { type: "SELECT_VEHICLE", vehicleId: "TRUCK_02" });
    s = workspaceReducer(s, { type: "SET_MODE", mode: "2D" });
    expect(s).toEqual({ mode: "2D", selectedVehicleId: "TRUCK_02", routeEmphasis: false });
    const html = renderS1(s);
    expect(html).toMatch(/cr-fleet-card-wrapper cr-selected"[^>]*data-vehicle-id="TRUCK_02"/);
    expect(html).toMatch(/<div class="cr-selected-body" data-vehicle-id="TRUCK_02"/);
    expect(html).toContain("cr-map-workspace");
  });

  it("selection is passed to the 3D renderer as the canonical vehicleId", () => {
    const s1 = source(join(SCREENS, "OperationsOverview.tsx"));
    const block = s1.match(/<ControlRoom3DTwin[\s\S]*?\/>/)?.[0] ?? "";
    expect(block).toContain("selectedVehicleId={activeSelectedId}");
    expect(block).toContain("onSelectVehicle={(vid) => setSelectedId(vid)}");
  });
});

describe("13-14. resilience and the 2D map", () => {
  it("13. WebGL unavailable does not break S1: the notice is drawn, everything else stays", () => {
    // Node has no `document`, so detection reports no WebGL — the same path a browser
    // without WebGL takes.
    const html = renderS1({ mode: "3D", selectedVehicleId: "TRUCK_01" });
    expect(html).toContain("WEBGL UNAVAILABLE");
    expect(html).not.toContain("<canvas");
    expect(html).toContain("TWIN 2 VEHICLES");
    expect(html).toContain("SELECTED VEHICLE");
    expect(html).toContain(">2D MAP<");
    expect(html).toContain("FIT");
    expect(html).toContain("PLAN");
    // The component alone renders too, with the S1-owned camera rail.
    const value = testHmiContext({ store: store(), freshness: CONFIG });
    const alone = renderToString(
      <HmiContext.Provider value={value}>
        <ControlRoom3DTwin selectedVehicleId={null} />
      </HmiContext.Provider>,
    );
    expect(alone).toContain('aria-label="3D Camera Controls"');
    for (const label of ["FIT", "+", "−", "PLAN", "3D"]) expect(alone).toContain(`>${label}<`);
  });

  it("14. the existing GeoSiteMap behaviour is intact in 2D mode", () => {
    const html = renderS1();
    expect(html).toContain(`TRUCK_01 · ${TWIN_SCENE_LABEL}`);
    expect(html).toContain(`TRUCK_02 · ${TWIN_SCENE_LABEL}`);
    expect(html).toContain("not a lease boundary");
    expect(html).toContain("ASSUMED_WGS84_UNVERIFIED");
    expect(html).toContain("SYNTHETIC OPERATIONAL CORRIDORS · NOT NMDC INFRASTRUCTURE");
    // The map is not re-designed for the toggle: the render still uses the same component.
    const s1 = source(join(SCREENS, "OperationsOverview.tsx"));
    expect(s1).toMatch(/<GeoSiteMap\s[\s\S]*?site=\{geoSite\}[\s\S]*?positions=\{geoPositions\}/);
  });
});
