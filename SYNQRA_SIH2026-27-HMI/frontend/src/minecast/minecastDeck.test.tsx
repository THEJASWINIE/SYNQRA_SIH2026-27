/**
 * MINECAST-03 — the operational deck: dense, but every figure still canonical.
 *
 * SOFTWARE ONLY. The trucks are Digital Twin demonstration positions on synthetic
 * corridors; nothing here is hardware verification and nothing is a real NMDC road.
 *
 * The scene itself is WebGL and cannot run here (M4D-C). What this file asserts is the
 * shell (rendered through the real `MineCastContent`), the view store the rails drive, the
 * layer catalogue, and source-level guarantees on the drawing modules.
 */

import { readdirSync, readFileSync } from "node:fs";
import { join } from "node:path";
import type { ReactNode } from "react";
import { renderToString } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { freshnessConfig } from "../config/freshness";
import type { PositionScene, VehicleState } from "../contracts/domain";
import { HmiContext } from "../state/ProviderHost";
import { AppStateStore } from "../state/store";
import { testHmiContext } from "../state/testHmiContext";
import { CORRIDOR_PROVENANCE, haulCorridors } from "./haulRoads";
import { MineCastContent } from "./MineCastApp";
import { LAYERS, projectMineCast } from "./minecastProjection";
import { initialViewState, minecastReducer } from "./minecastStore";
import { terrainConfig } from "./terrainField";

const T = "2026-09-14T12:00:00.000Z";
const MINECAST_DIR = join(__dirname);

function scene(xM: number, yM: number): PositionScene {
  return {
    xM,
    yM,
    headingRad: 0.4,
    frame: "SCENE_METRES",
    status: "VALID",
    source: "SIMULATION",
    origin: "SIMULATION",
    provenanceLabel: "SIMULATION · DIGITAL TWIN",
    method: "DIGITAL_TWIN_SCENE_SIM",
    reason: "Digital Twin demonstration position in SCENE_METRES.",
  };
}

function vehicle(
  id: string,
  positionScene: PositionScene | null,
  speedMps: number | null,
): VehicleState {
  return {
    vehicleId: id,
    timestamp: T,
    position: { x: null, y: null, segmentId: null, offsetM: null },
    positionScene,
    speedMps,
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

function storeWith(vehicles: Record<string, VehicleState>): AppStateStore {
  const store = new AppStateStore(T, "LIVE");
  store.applyPatch({ changes: { vehicles } } as never, T);
  store.setStatus("CONNECTED", null);
  return store;
}

const text = (html: string) => html.replace(/<!-- -->/g, "");
function renderShell(store: AppStateStore, node: ReactNode = <MineCastContent />): string {
  const value = testHmiContext({ store, freshness: freshnessConfig(5000) });
  return text(renderToString(<HmiContext.Provider value={value}>{node}</HmiContext.Provider>));
}

const FLEET = storeWith({
  TRUCK_01: vehicle("TRUCK_01", scene(1150, 2380), 6.5),
  TRUCK_02: vehicle("TRUCK_02", scene(2048, 736), 3.1),
});

const code = (name: string) => readFileSync(join(MINECAST_DIR, name), "utf-8");
const stripped = (name: string) =>
  code(name)
    .replace(/\/\*[\s\S]*?\*\//g, "")
    .replace(/^\s*\/\/.*$/gm, "");

// ===========================================================================

describe("identity and disclosures", () => {
  const html = renderShell(FLEET);

  it("says what this deck is, as identity, not as a data claim", () => {
    expect(html).toContain("MINE-CAST");
    expect(html).toContain("DIGITAL TWIN · SIMULATION VIEW");
  });

  it("keeps every truth label over the viewport", () => {
    expect(html).toContain("SYNTHETIC TERRAIN");
    expect(html).toContain("NOT SURVEYED");
    expect(html).toContain("SYNTHETIC OPERATIONAL CORRIDORS");
    expect(html).toContain("NOT NMDC INFRASTRUCTURE");
    expect(html).toContain("DIGITAL TWIN SIMULATION (SCENE_METRES)");
    expect(html).toContain("not GNSS, not a measured position");
    expect(html).toContain("PUBLISHED COORDINATE EXTENT");
  });

  it("renders the rails and every required panel", () => {
    expect(html).toContain('aria-label="Map controls"');
    for (const label of ["FIT", "PLAN", "3D"]) expect(html).toContain(`>${label}</button>`);
    expect(html).toContain("LAYERS");
    for (const title of [
      "Fleet operations",
      "Selected vehicle",
      "Layers",
      "Legend",
      "Provenance",
      "Site context",
    ]) {
      expect(html).toContain(title);
    }
  });
});

describe("1-2, 8. both trucks, and only those two, from canonical state", () => {
  it("the fleet panel lists exactly TRUCK_01 and TRUCK_02", () => {
    const minecast = projectMineCast(FLEET.getSnapshot());
    expect(minecast.vehicles.map((v) => v.canonicalVehicleId).sort()).toEqual([
      "TRUCK_01",
      "TRUCK_02",
    ]);
    const html = renderShell(FLEET);
    expect(html).toContain("T01");
    expect(html).toContain("T02");
    expect(html).not.toMatch(/\bT0[3-9]\b|\bTRUCK_0[3-9]\b/);
  });

  it("the caption counts two drawn trucks from the Twin's scene poses", () => {
    expect(renderShell(FLEET)).toContain(
      "VEHICLES: 2 DRAWN FROM DIGITAL TWIN SIMULATION (SCENE_METRES)",
    );
  });

  it("fleet speed is the canonical value, never a placeholder", () => {
    const html = renderShell(FLEET);
    expect(html).toContain("6.5");
    expect(html).toContain("3.1");
    const bare = storeWith({ TRUCK_01: vehicle("TRUCK_01", scene(1150, 2380), null) });
    expect(renderShell(bare)).not.toMatch(/>0\.0 m\/s</);
  });
});

describe("9. the selected-vehicle panel cannot invent unavailable data", () => {
  it("with TRUCK_01 selected it shows canonical fields and UNAVAILABLE for the rest", () => {
    const view = { ...initialViewState(), selectedVehicleId: "TRUCK_01" };
    const minecast = projectMineCast(FLEET.getSnapshot());
    const selected = minecast.vehicles.find(
      (v) => v.canonicalVehicleId === view.selectedVehicleId,
    );
    expect(selected).toBeDefined();
    expect(selected?.speedMps).toBe(6.5);
    // Nothing supplied safety: the panel's source must say so, never LOW / 0.
    expect(selected?.safety.unavailable).toBe(true);
    expect(selected?.safety.riskLevel).toBeNull();
    expect(selected?.safety.vSafeMps).toBeNull();
    expect(selected?.v2v.state).toBe("UNAVAILABLE");
    expect(selected?.scenePose?.frame).toBe("SCENE_METRES");
  });

  it("selection is view state in the shell's one store", () => {
    let view = initialViewState();
    expect(view.selectedVehicleId).toBeNull();
    view = minecastReducer(view, { type: "SELECT_VEHICLE", canonicalVehicleId: "TRUCK_02" });
    expect(view.selectedVehicleId).toBe("TRUCK_02");
    view = minecastReducer(view, { type: "SELECT_VEHICLE", canonicalVehicleId: null });
    expect(view.selectedVehicleId).toBeNull();
  });
});

describe("map controls are view state, applied once per request", () => {
  it("each request gets a new sequence number, so a repeated command is applied again", () => {
    let view = initialViewState();
    expect(view.cameraRequest).toBeNull();
    view = minecastReducer(view, { type: "REQUEST_CAMERA", command: "FIT" });
    expect(view.cameraRequest).toEqual({ command: "FIT", seq: 1 });
    view = minecastReducer(view, { type: "REQUEST_CAMERA", command: "ZOOM_IN" });
    view = minecastReducer(view, { type: "REQUEST_CAMERA", command: "ZOOM_IN" });
    expect(view.cameraRequest).toEqual({ command: "ZOOM_IN", seq: 3 });
    // A camera request changes nothing about selection or layers.
    expect(view.selectedVehicleId).toBeNull();
    expect(view.layerVisibility).toEqual(initialViewState().layerVisibility);
  });

  it("RESET_VIEW clears the request along with everything else", () => {
    const view = minecastReducer(
      minecastReducer(initialViewState(), { type: "REQUEST_CAMERA", command: "PLAN_VIEW" }),
      { type: "RESET_VIEW" },
    );
    expect(view.cameraRequest).toBeNull();
  });
});

describe("10-11. layers and corridors invent nothing", () => {
  it("every implemented layer is synthetic, a Twin simulation, or the published extent", () => {
    for (const layer of LAYERS.filter((l) => l.implemented)) {
      expect(["SYNTHETIC_FOR_DEMO", "SIMULATION", "HARDWARE"], layer.id).toContain(
        layer.provenance,
      );
      // The only non-synthetic drawn thing is the published coordinate extent.
      if (layer.provenance === "HARDWARE") expect(layer.id).toBe("PUBLISHED_EXTENT");
    }
  });

  it("no layer describes itself as an NMDC road or survey-grade, and no orthophoto exists", () => {
    for (const layer of LAYERS) {
      const note = `${layer.label} ${layer.note}`.toUpperCase();
      expect(note, layer.id).not.toMatch(/\bNMDC (HAUL )?ROAD\b/);
      expect(note, layer.id).not.toContain("SURVEY-GRADE");
      if (layer.id === "ORTHOPHOTO") expect(layer.implemented).toBe(false);
    }
  });

  it("every corridor is labelled synthetic and never verified", () => {
    const config = terrainConfig(3224, 3396);
    for (const corridor of haulCorridors(config)) {
      expect(corridor.source).toBe("SYNTHETIC_FOR_DEMO");
      expect(corridor.verified).toBe(false);
      expect(corridor.confidence).toBe("LOW");
      expect(corridor.label.toLowerCase()).toContain("synthetic");
    }
    expect(CORRIDOR_PROVENANCE.disclosure).toBe(
      "SYNTHETIC OPERATIONAL CORRIDORS · NOT NMDC INFRASTRUCTURE",
    );
  });

  it("the corridor renderer colours by kind only - never by any speed or status", () => {
    const source = stripped("HaulRoadsLayer.tsx");
    expect(source).not.toMatch(/speed|risk|safety|v2v/i);
    // Direction is a dash rhythm on the real centreline, not an invented flow.
    expect(source).toContain("LineDashedMaterial");
    expect(source).toContain("computeLineDistances");
  });
});

describe("7, 12. callouts stay bound; nothing in presentation holds a coordinate", () => {
  it("the callout is keyed and stamped by the same canonical id as its marker", () => {
    const markers = code("VehicleMarkers.tsx");
    expect(markers).toContain("key={position.canonicalVehicleId}");
    expect(markers).toContain(
      "vehicles.find((v) => v.canonicalVehicleId === position.canonicalVehicleId)",
    );
    expect(code("VehicleCallout.tsx")).toContain("data-vehicle-id={vehicle.canonicalVehicleId}");
  });

  it("selection and click flow through the store, never a local vehicle state", () => {
    const markers = stripped("VehicleMarkers.tsx");
    expect(markers).toContain("onSelect?.(position.canonicalVehicleId)");
    expect(markers).not.toContain("useState");
    expect(markers).not.toContain("useAppState");
  });

  it("no presentation module contains a truck id or a literal coordinate", () => {
    const presentation = readdirSync(MINECAST_DIR).filter(
      (n) => n.endsWith(".tsx") && !n.includes(".test."),
    );
    for (const name of presentation) {
      const source = stripped(name);
      expect(source, name).not.toMatch(/\bTRUCK_0\d\b/);
      expect(source, name).not.toMatch(/\bxM\s*[:=]\s*-?\d|\byM\s*[:=]\s*-?\d/);
      expect(source, name).not.toMatch(/\blat(itude)?\s*[:=]\s*\d|\blon(gitude)?\s*[:=]\s*\d/);
      expect(source, name).not.toMatch(/new WebSocket|fetch\(/);
    }
  });
});
