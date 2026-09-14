/**
 * Mine-Cast architectural boundary guards.
 *
 * These scan the REAL Mine-Cast sources, not a reconstruction of them, because every
 * boundary below is invisible in rendered output. A viewer that quietly opened its own
 * WebSocket, or that could submit a command, would look identical on screen to one that
 * could not.
 *
 * The four properties held here:
 *
 *   1. the projection is framework-free       (pure, testable, no React)
 *   2. there is no command submission path    (Mine-Cast is read-only)
 *   3. there is no telemetry ingestion        (no fetch, no WebSocket, no polling)
 *   4. ProviderHost remains the sole boundary (one provider, one store, one Twin)
 *
 * SOFTWARE ONLY. Reads source text; touches no hardware and no network.
 */

import { readdirSync, readFileSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";

const MINECAST_DIR = "src/minecast";

/** Every Mine-Cast module, discovered rather than listed, so a new one is covered too. */
const MODULES = readdirSync(MINECAST_DIR)
  .filter((name) => (name.endsWith(".ts") || name.endsWith(".tsx")) && !name.includes(".test."))
  .sort();

/**
 * THE SCENE BOUNDARY.
 *
 * Pass 2 introduced a WebGL view, so "no Three.js anywhere" is no longer the right
 * invariant - but "Three.js only here" is a stronger one. These four modules are the only
 * ones permitted to import three / @react-three, and they are permitted nothing else:
 * they draw, and they never read safety, submit a command or fetch telemetry.
 */
const SCENE_MODULES = [
  "MineCanvas.tsx",
  "MineScene.tsx",
  "MineTerrain.tsx",
  "MineGeometry.tsx",
  "HaulRoadsLayer.tsx",
  // MINECAST-01: draws the Twin's trucks. Same rule as the rest of the boundary - it
  // draws what it is handed and reads no safety, submits no command, fetches nothing.
  "VehicleMarkers.tsx",
  // MINE-ROUTES-02: drapes the synthetic zones. Draws what it is handed, nothing more.
  "MineZonesLayer.tsx",
];

/**
 * The pure maths behind the scene: height field, mine geometry, camera framing.
 *
 * Three-free (so they are unit tested in `scene.test.ts`), but they DO legitimately use
 * `Math.sqrt` and `Math.min` - a radial distance and a clamp are geometry, not an
 * operational safety value. They are therefore exempt from the arithmetic guards below
 * while remaining subject to every other boundary.
 */
const SCENE_MATH_MODULES = [
  "terrainField.ts",
  "mineFeatures.ts",
  "mineCamera.ts",
  "haulRoads.ts",
  "pitMorphology.ts",
];

/**
 * Everything else: the projection, the store, and the six overlay panels. These stay
 * completely free of Three.js so they remain renderable and testable without a GPU.
 */
const NON_SCENE_MODULES = MODULES.filter((name) => !SCENE_MODULES.includes(name));

/**
 * The modules that must contain NO physical or safety arithmetic whatsoever: the
 * projection, the store and the panels. This is where an operational value could actually
 * leak in, and it is the set the arithmetic guards scan.
 */
const NO_ARITHMETIC_MODULES = NON_SCENE_MODULES.filter(
  (name) => !SCENE_MATH_MODULES.includes(name),
);

/**
 * Strip comments before scanning.
 *
 * Prose that NAMES a forbidden thing must not count as doing it - these files explain at
 * length why they do not submit commands, and that explanation is not a violation.
 */
function code(name: string): string {
  return readFileSync(join(MINECAST_DIR, name), "utf-8")
    .replace(/\{\/\*[\s\S]*?\*\/\}/g, "")
    .replace(/\/\*[\s\S]*?\*\//g, "")
    .replace(/^\s*\/\/.*$/gm, "");
}

describe("the scan covers the real Mine-Cast sources", () => {
  it("finds the modules", () => {
    expect(MODULES).toContain("MineCastApp.tsx");
    expect(MODULES).toContain("minecastProjection.ts");
    expect(MODULES).toContain("minecastStore.ts");
    expect(MODULES).toContain("FleetPanel.tsx");
    expect(MODULES).toContain("VehiclePanel.tsx");
    expect(MODULES).toContain("LayerPanel.tsx");
    expect(MODULES).toContain("Legend.tsx");
    expect(MODULES).toContain("ProvenancePanel.tsx");
    expect(MODULES).toContain("MiniMap.tsx");
  });

  it("finds the scene boundary modules", () => {
    for (const name of SCENE_MODULES) expect(MODULES, name).toContain(name);
  });

  it("keeps the non-scene set non-empty, so the guards below actually scan something", () => {
    expect(NON_SCENE_MODULES.length).toBeGreaterThan(6);
    expect(NON_SCENE_MODULES).toContain("minecastProjection.ts");
    expect(NON_SCENE_MODULES).toContain("VehiclePanel.tsx");
  });

  it("exempts only the three scene-maths modules from the arithmetic guards", () => {
    // A narrow, named exemption. The projection, the store and every panel remain in the
    // strict set, which is where an operational value could actually leak in.
    expect(SCENE_MATH_MODULES).toEqual([
      "terrainField.ts",
      "mineFeatures.ts",
      "mineCamera.ts",
      "haulRoads.ts",
      "pitMorphology.ts",
    ]);
    expect(NO_ARITHMETIC_MODULES).toContain("minecastProjection.ts");
    expect(NO_ARITHMETIC_MODULES).toContain("minecastStore.ts");
    for (const panel of [
      "FleetPanel.tsx",
      "VehiclePanel.tsx",
      "LayerPanel.tsx",
      "Legend.tsx",
      "ProvenancePanel.tsx",
      "MiniMap.tsx",
    ]) {
      expect(NO_ARITHMETIC_MODULES, panel).toContain(panel);
    }
    for (const exempt of SCENE_MATH_MODULES) {
      expect(NO_ARITHMETIC_MODULES, exempt).not.toContain(exempt);
    }
  });
});

// ---------------------------------------------------------------------------
// 1. the projection is framework-free
// ---------------------------------------------------------------------------

describe("the projection is framework-free", () => {
  const projection = code("minecastProjection.ts");

  it("imports no React", () => {
    expect(projection).not.toMatch(/from\s+["']react["']/);
    expect(projection).not.toMatch(/from\s+["']react-dom/);
  });

  it("uses no hook and no JSX", () => {
    expect(projection).not.toMatch(/\buse[A-Z]\w*\(/);
    expect(projection).not.toMatch(/<[A-Z]\w*[\s/>]/);
  });

  it("is a .ts module, so JSX could not be added without moving it", () => {
    expect(MODULES).toContain("minecastProjection.ts");
    expect(MODULES).not.toContain("minecastProjection.tsx");
  });

  it("touches no browser global", () => {
    for (const global of ["window.", "document.", "localStorage", "sessionStorage", "navigator."]) {
      expect(projection, global).not.toContain(global);
    }
  });
});

// ---------------------------------------------------------------------------
// 2. no command submission path
// ---------------------------------------------------------------------------

describe("Mine-Cast is read-only", () => {
  it("no module imports the command client", () => {
    for (const name of MODULES) {
      expect(code(name), name).not.toContain("commandClient");
      expect(code(name), name).not.toContain("submitCommand");
    }
  });

  it("no module builds a command payload or a command id", () => {
    for (const name of MODULES) {
      const source = code(name);
      expect(source, name).not.toContain("buildCommandPayload");
      expect(source, name).not.toContain("nextCommandId");
    }
  });

  it("no module posts anything", () => {
    for (const name of MODULES) {
      const source = code(name);
      expect(source, name).not.toMatch(/method:\s*["']POST["']/);
      expect(source, name).not.toMatch(/method:\s*["']PUT["']/);
      expect(source, name).not.toMatch(/method:\s*["']DELETE["']/);
    }
  });

  it("the command path stays with the operational consoles", () => {
    // The single command transport is still imported by the screens and the vehicle
    // console, and NOT by Mine-Cast. Asserted positively so this test fails loudly if the
    // command path were ever moved rather than merely copied.
    const dispatch = readFileSync("src/screens/DispatchSlots.tsx", "utf-8");
    const vehiclePanels = readFileSync("src/vehicle/panels.tsx", "utf-8");
    expect(dispatch).toContain("submitCommand");
    expect(vehiclePanels).toContain("submitCommand");
  });
});

// ---------------------------------------------------------------------------
// 3. no telemetry ingestion of its own
// ---------------------------------------------------------------------------

describe("Mine-Cast ingests no telemetry", () => {
  it("calls no fetch", () => {
    for (const name of MODULES) {
      const source = code(name);
      expect(source, name).not.toMatch(/\bfetch\s*\(/);
      expect(source, name).not.toContain("XMLHttpRequest");
    }
  });

  it("constructs no WebSocket", () => {
    for (const name of MODULES) {
      const source = code(name);
      expect(source, name).not.toMatch(/new\s+WebSocket/);
      expect(source, name).not.toContain("EventSource");
    }
  });

  it("starts no polling loop of its own", () => {
    // `ProviderHost` already owns the display ticker and the observability poll. A second
    // timer here would be a second, unsynchronised read of the same backend.
    for (const name of MODULES) {
      const source = code(name);
      expect(source, name).not.toMatch(/setInterval\s*\(/);
      expect(source, name).not.toMatch(/setTimeout\s*\(/);
    }
  });

  it("imports no concrete data provider", () => {
    for (const name of MODULES) {
      const source = code(name);
      expect(source, name).not.toContain("LiveDataProvider");
      expect(source, name).not.toContain("MockDataProvider");
      expect(source, name).not.toContain("ReplayProvider");
    }
  });

  it("imports no API client at all", () => {
    for (const name of MODULES) {
      expect(code(name), name).not.toMatch(/from\s+["']\.\.\/api\//);
    }
  });
});

// ---------------------------------------------------------------------------
// 4. ProviderHost remains the sole telemetry boundary
// ---------------------------------------------------------------------------

describe("ProviderHost is the only telemetry boundary", () => {
  it("Mine-Cast mounts ProviderHost, exactly as the vehicle console does", () => {
    const app = code("MineCastApp.tsx");
    expect(app).toContain("ProviderHost");
    expect(app).toMatch(/<ProviderHost>/);

    const vehicleApp = readFileSync("src/vehicle/VehicleHmiApp.tsx", "utf-8");
    expect(vehicleApp).toMatch(/<ProviderHost>/);
  });

  it("reads state only through useAppState", () => {
    const app = code("MineCastApp.tsx");
    expect(app).toContain("useAppState");
  });

  it("no module constructs its own store", () => {
    for (const name of MODULES) {
      expect(code(name), name).not.toMatch(/new\s+AppStateStore/);
    }
  });

  it("no module writes to the canonical store", () => {
    // A viewer that could applyPatch, setStatus or reset would be able to mutate the Twin
    // projection every other view reads.
    for (const name of MODULES) {
      const source = code(name);
      for (const writer of ["applyPatch", "setStatus(", "setObservability", "store.reset"]) {
        expect(source, `${name} / ${writer}`).not.toContain(writer);
      }
    }
  });

  it("ProviderHost is still the only importer of a concrete provider", () => {
    const host = readFileSync("src/state/ProviderHost.tsx", "utf-8");
    expect(host).toContain("LiveDataProvider");
    expect(host).toContain("MockDataProvider");
  });
});

// ---------------------------------------------------------------------------
// no 3D was introduced in this pass
// ---------------------------------------------------------------------------

describe("Three.js is confined to the scene boundary", () => {
  it("only the scene modules import three or @react-three", () => {
    for (const name of NON_SCENE_MODULES) {
      const source = code(name);
      expect(source, name).not.toMatch(/from\s+["']three["']/);
      expect(source, name).not.toContain("@react-three");
      expect(source, name).not.toContain("useThree");
    }
  });

  it("the projection stays pure — no Three.js, no React, no browser global", () => {
    const projection = code("minecastProjection.ts");
    expect(projection).not.toMatch(/from\s+["']three["']/);
    expect(projection).not.toContain("@react-three");
    expect(projection).not.toMatch(/from\s+["']react["']/);
  });

  it("the pure scene maths modules import no Three.js either", () => {
    // terrainField / mineGeometry / mineCamera are what make the scene testable at all.
    for (const name of SCENE_MATH_MODULES) {
      expect(MODULES, name).toContain(name);
      const source = code(name);
      expect(source, name).not.toMatch(/from\s+["']three["']/);
      expect(source, name).not.toContain("@react-three");
    }
  });

  it("MineCanvas is the single WebGL entry, and it is lazily loaded", () => {
    // Lazy loading is what keeps Three.js out of the server render and out of the Node
    // test environment. A static import here would break the shell tests.
    const canvas = code("MineCanvas.tsx");
    expect(canvas).toContain("@react-three/fiber");
    expect(canvas).toContain("Canvas");

    const app = code("MineCastApp.tsx");
    expect(app).toMatch(/lazy\(\s*\(\)\s*=>\s*import\(["']\.\/MineCanvas["']\)\s*\)/);
    expect(app).not.toMatch(/^import .*MineCanvas.*$/m);
  });

  it("no panel imports the canvas or the scene", () => {
    const panels = [
      "FleetPanel.tsx",
      "VehiclePanel.tsx",
      "LayerPanel.tsx",
      "Legend.tsx",
      "ProvenancePanel.tsx",
      "MiniMap.tsx",
    ];
    for (const name of panels) {
      const source = code(name);
      expect(source, name).not.toContain("MineCanvas");
      expect(source, name).not.toContain("MineScene");
    }
  });

  it("the mini-map is still inline SVG and needs no map engine", () => {
    const miniMap = code("MiniMap.tsx");
    expect(miniMap).toMatch(/<svg/);
    for (const engine of ["leaflet", "mapbox", "maplibre", "openlayers", "cesium"]) {
      expect(miniMap.toLowerCase(), engine).not.toContain(engine);
    }
  });

  it("the scene draws no route or communication link", () => {
    // These still require evidence the Twin does not supply. A placeholder for any of
    // them would be a fabrication, so the scene simply does not contain one.
    const scene =
      code("MineScene.tsx") +
      code("MineCanvas.tsx") +
      code("MineGeometry.tsx") +
      code("HaulRoadsLayer.tsx") +
      code("VehicleMarkers.tsx");
    for (const term of ["v2vlink", "v2ilayer", "routes.tsx"]) {
      expect(scene.toLowerCase(), term).not.toContain(term);
    }
  });

  it("MINECAST-01: the scene invents no vehicle position of its own", () => {
    // Vehicles ARE drawn now, but every coordinate arrives from the canonical Twin
    // through the shared spatial-position contract. The drawing modules must contain no
    // vehicle id and no literal coordinate to place one at.
    for (const name of ["VehicleMarkers.tsx", "MineScene.tsx", "MineCanvas.tsx"]) {
      const source = code(name);
      expect(source, name).not.toMatch(/\bTRUCK_0\d\b/);
      expect(source, name).not.toMatch(/\bxM\s*[:=]\s*-?\d/);
      expect(source, name).not.toMatch(/\byM\s*[:=]\s*-?\d/);
      expect(source, name).not.toMatch(/\blat\s*[:=]\s*\d|\blon\s*[:=]\s*\d/);
      // No second source of telemetry, either.
      expect(source, name).not.toMatch(/new WebSocket|fetch\(/);
    }
  });
});

describe("Mine-Cast authors no operational value", () => {
  it("computes no minimum — v_safe is solved outside this application", () => {
    // Scanned on the projection, store and panels. Terrain and camera maths legitimately
    // need sqrt and min, and neither is an operational safety value.
    for (const name of NO_ARITHMETIC_MODULES) {
      const source = code(name);
      expect(source, name).not.toMatch(/Math\.min\s*\(/);
    }
  });

  it("computes no stopping distance and no square root", () => {
    for (const name of NO_ARITHMETIC_MODULES) {
      const source = code(name);
      expect(source, name).not.toMatch(/Math\.sqrt\s*\(/);
      expect(source, name).not.toMatch(/Math\.pow\s*\(/);
    }
  });

  it("re-implements no provenance or freshness label", () => {
    // Both come from the shared `state/dataStatus` helpers, so Mine-Cast cannot disagree
    // with the control room or the vehicle consoles about the same field.
    for (const name of MODULES) {
      const source = code(name);
      if (source.includes("provenanceLabel") || source.includes("DATA_STATE_TEXT")) {
        expect(source, name).toMatch(/from\s+["']\.\.\/state\/dataStatus["']/);
      }
    }
  });

  it("derives link state only through the shared communication module", () => {
    const projection = code("minecastProjection.ts");
    expect(projection).toMatch(/from\s+["']\.\.\/vehicle\/communication["']/);
    // No module re-decides what CONNECTED means.
    for (const name of NON_SCENE_MODULES) {
      expect(code(name), name).not.toMatch(/=\s*["']CONNECTED["']/);
    }
  });
});
