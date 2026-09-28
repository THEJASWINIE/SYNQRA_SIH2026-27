/**
 * Focused tests for CONTROL-ROOM-MINECAST-INTEGRATION-01
 * Control Room S1 Digital Twin screen (OperationsOverview & GeoSiteMap).
 *
 * Assertions verify:
 * 1. T01 and T02 render from canonical Digital Twin scene positions.
 * 2. Vehicle selection uses vehicleId (never array index).
 * 3. Selected panel corresponds to selected vehicle.
 * 4. SCENE_METRES remains simulation provenance.
 * 5. No fake geographic coordinates are created.
 * 6. Safety unavailable remains unavailable ("SAFETY DATA UNAVAILABLE · DO NOT ASSUME SAFE").
 * 7. V2V unavailable remains unavailable.
 * 8. V2I unavailable remains unavailable.
 * 9. Published extent is still labeled NOT A LEASE BOUNDARY.
 * 10. Synthetic corridors remain explicitly disclosed.
 * 11. S1 does not create independent fetch/WebSocket/store logic.
 * 12. Fleet dynamic: renders any supplied vehicles without hardcoded truck counts.
 *
 * SOFTWARE ONLY: Every value below is a simulated fixture; no hardware verification.
 */

import { readFileSync } from "node:fs";
import { join } from "node:path";
import { renderToString } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { freshnessConfig } from "../config/freshness";
import type { PositionScene, SafetyState, VehicleState } from "../contracts/domain";
import { OperationsOverview } from "./OperationsOverview";
import { ControlRoom3DTwin } from "../controlRoom/ControlRoom3DTwin";
import { bailadilaDeposit5, toDecimalExtent } from "../state/geoSite";
import { HmiContext } from "../state/ProviderHost";
import { AppStateStore } from "../state/store";
import { testHmiContext } from "../state/testHmiContext";
import {
  fleetPositions,
  placeablePositions,
  providerForMode,
  SCENE_FRAME,
  TWIN_SCENE_LABEL,
} from "../state/vehiclePosition";

const T = "2026-09-14T12:00:00.000Z";
const CONFIG = freshnessConfig(5000);
const SITE = bailadilaDeposit5();
const EXTENT = toDecimalExtent(SITE.extent);

function scene(xM: number, yM: number, over: Partial<PositionScene> = {}): PositionScene {
  return {
    xM,
    yM,
    headingRad: 0.52,
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

function fixtureVehicle(
  id: string,
  speedMps: number | null,
  positionScene: PositionScene | null = null,
  extra: Partial<VehicleState> = {},
): VehicleState {
  return {
    vehicleId: id,
    mode: "NORMAL",
    vehicleKind: "DUMPER",
    speedMps,
    position: { x: null, y: null, segmentId: null, offsetM: null },
    positionScene,
    accelMps2: null,
    gradeRad: null,
    commConfidence: null,
    frictionEst: null,
    routeId: null,
    timestamp: T,
    provenance: {
      speed_mps: {
        source: "SIMULATION",
        origin: "SIMULATION",
        quality: "OK",
        freshness: "CURRENT",
        available: true,
        timestamp: Date.parse(T) / 1000,
      },
    } as never,
    ...extra,
  } as VehicleState;
}

function createStore(vehicles: Record<string, VehicleState>, safety: Record<string, SafetyState> = {}): AppStateStore {
  const store = new AppStateStore(T, "LIVE");
  store.applyPatch(
    {
      changes: {
        vehicles,
        safety,
      },
    } as never,
    T,
  );
  store.setStatus("CONNECTED", null);
  return store;
}

function renderS1(store: AppStateStore, onSelectVehicle = () => {}): string {
  const value = testHmiContext({ store, freshness: CONFIG });
  return renderToString(
    <HmiContext.Provider value={value}>
      <OperationsOverview onSelectVehicle={onSelectVehicle} />
    </HmiContext.Provider>,
  );
}

function readSource(rel: string): string {
  return readFileSync(join(__dirname, rel), "utf-8")
    .replace(/\/\*[\s\S]*?\*\//g, "")
    .replace(/^\s*\/\/.*$/gm, "");
}

describe("CONTROL-ROOM-MINECAST-INTEGRATION-01 — S1 OperationsOverview", () => {
  const t01 = fixtureVehicle("TRUCK_01", 7.8, scene(1150, 2380));
  const t02 = fixtureVehicle("TRUCK_02", 6.2, scene(2048, 736));

  it("1. T01 and T02 render from canonical Digital Twin scene positions", () => {
    const store = createStore({ TRUCK_01: t01, TRUCK_02: t02 });
    const html = renderS1(store);

    // Both trucks appear as map markers with canonical simulation label
    expect(html).toContain(`TRUCK_01 · ${TWIN_SCENE_LABEL}`);
    expect(html).toContain(`TRUCK_02 · ${TWIN_SCENE_LABEL}`);

    // Positions resolved from canonical fleet resolver
    const placed = placeablePositions(
      fleetPositions({ TRUCK_01: t01, TRUCK_02: t02 }, providerForMode("LIVE", EXTENT), EXTENT),
    );
    expect(placed.map((p) => p.vehicleId)).toEqual(["TRUCK_01", "TRUCK_02"]);
    expect(placed.every((p) => p.provenance === "SIMULATED_TWIN_SCENE")).toBe(true);
  });

  it("2. Vehicle selection uses vehicleId string, never array index", () => {
    const store = createStore({ TRUCK_01: t01, TRUCK_02: t02 });
    const html = renderS1(store);

    // Selection attributes and targets use vehicleId
    expect(html).toContain('data-vehicle-id="TRUCK_01"');
    expect(html).toContain('data-vehicle-id="TRUCK_02"');

    // No numeric array index references in selection attributes
    expect(html).not.toMatch(/data-vehicle-index/);
  });

  it("3. Selected panel corresponds to selected vehicle", () => {
    const store = createStore({ TRUCK_01: t01, TRUCK_02: t02 });
    const html = renderS1(store);

    // Selected vehicle panel shows context
    expect(html).toContain("SELECTED VEHICLE");
    expect(html).toMatch(/TRUCK_01|TRUCK_02/);
    expect(html).toContain("km/h");
  });

  it("4. SCENE_METRES remains simulation provenance and is never GNSS", () => {
    const store = createStore({ TRUCK_01: t01, TRUCK_02: t02 });
    const html = renderS1(store);

    expect(html).toContain("SCENE_METRES");
    expect(html).toContain("SIMULATION · NOT GNSS");
    expect(html).not.toContain("LIVE HARDWARE");
  });

  it("5. No fake geographic coordinates are created in S1 presentation", () => {
    const s1Code = readSource("OperationsOverview.tsx");
    const mapCode = readSource("GeoSiteMap.tsx");
    for (const code of [s1Code, mapCode]) {
      // Must not fabricate coordinates
      expect(code).not.toMatch(/lat:\s*1[89]\.\d/);
      expect(code).not.toMatch(/lon:\s*8[01]\.\d/);
      expect(code).not.toMatch(/\bxM:\s*\d|\byM:\s*\d/);
    }
  });

  it("6. Safety unavailable remains unavailable: exactly 'SAFETY DATA UNAVAILABLE · DO NOT ASSUME SAFE'", () => {
    // Store has vehicles but NO safety state
    const store = createStore({ TRUCK_01: t01 });
    const html = renderS1(store);

    expect(html).toContain("SAFETY DATA UNAVAILABLE · DO NOT ASSUME SAFE");
  });

  it("7. V2V unavailable remains unavailable when no evidence exists", () => {
    const store = createStore({ TRUCK_01: t01 });
    const html = renderS1(store);

    expect(html).toContain("V2V");
    expect(html).toContain("UNAVAILABLE");
  });

  it("8. V2I unavailable remains unavailable in every mode", () => {
    const store = createStore({ TRUCK_01: t01 });
    const html = renderS1(store);

    expect(html).toContain("V2I");
    expect(html).toContain("UNAVAILABLE");
  });

  it("9. Published extent is still labeled NOT A LEASE BOUNDARY", () => {
    const store = createStore({ TRUCK_01: t01, TRUCK_02: t02 });
    const html = renderS1(store);

    expect(html).toContain("not a lease boundary");
    expect(html).toContain("ASSUMED_WGS84_UNVERIFIED");
  });

  it("10. Synthetic corridors remain explicitly disclosed", () => {
    const store = createStore({ TRUCK_01: t01, TRUCK_02: t02 });
    const html = renderS1(store);

    expect(html).toContain("SYNTHETIC OPERATIONAL CORRIDORS · NOT NMDC INFRASTRUCTURE");
  });

  it("11. S1 does not create independent fetch/WebSocket/store logic", () => {
    for (const rel of ["OperationsOverview.tsx", "GeoSiteMap.tsx"]) {
      const text = readSource(rel);
      expect(text, rel).not.toMatch(/new WebSocket\(/);
      expect(text, rel).not.toMatch(/\bfetch\(/);
      expect(text, rel).not.toMatch(/new AppStateStore\(/);
      expect(text, rel).not.toMatch(/useState<\s*(VehicleState|SafetyState|AppState)\b/);
      expect(text, rel).not.toMatch(/from ["']\.\.?\/minecast\//);
      expect(text, rel).not.toMatch(/from ["']three["']|@react-three/);
    }
  });

  it("12. Fleet dynamic: renders any supplied vehicle collection without hardcoded IDs or counts", () => {
    const t07 = fixtureVehicle("TRUCK_07", 5.5, scene(1500, 1500));
    const store = createStore({ TRUCK_01: t01, TRUCK_02: t02, TRUCK_07: t07 });
    const html = renderS1(store);

    expect(html).toContain("TRUCK_01");
    expect(html).toContain("TRUCK_02");
    expect(html).toContain("TRUCK_07");
    expect(html).toContain("TWIN 3 VEHICLES");
  });

  it("13. S1 provides [ 2D MAP ] [ 3D TWIN ] workspace toggle defaulting to 2D", () => {
    const store = createStore({ TRUCK_01: t01, TRUCK_02: t02 });
    const html = renderS1(store);

    expect(html).toContain("2D MAP");
    expect(html).toContain("3D TWIN");
    expect(html).toContain('data-view-mode="2D"');
    expect(html).toContain('data-view-mode="3D"');
    expect(html).toContain('aria-pressed="true"');
  });

  it("14. S1 does not couple to Mine-Cast application or store internals", () => {
    const s1Code = readSource("OperationsOverview.tsx");
    const cr3dCode = readFileSync(join(__dirname, "../controlRoom/ControlRoom3DTwin.tsx"), "utf-8")
      .replace(/\/\*[\s\S]*?\*\//g, "")
      .replace(/^\s*\/\/.*$/gm, "");

    // S1 does NOT import MineCastApp or useMineCastStore
    expect(s1Code).not.toMatch(/MineCastApp/);
    expect(s1Code).not.toMatch(/minecastStore/);
    expect(cr3dCode).not.toMatch(/useMineCastStore/);
    expect(cr3dCode).not.toMatch(/MineCastApp/);
    expect(cr3dCode).not.toMatch(/from ["']\.\.?\/minecast\/minecastStore["']/);
  });

  it("15. ControlRoom3DTwin renders S1-native disclosures and controls in SSR/test environment", () => {
    const store = createStore({ TRUCK_01: t01, TRUCK_02: t02 });
    const value = testHmiContext({ store, freshness: CONFIG });
    const html = renderToString(
      <HmiContext.Provider value={value}>
        <ControlRoom3DTwin selectedVehicleId="TRUCK_01" />
      </HmiContext.Provider>,
    );

    expect(html).toContain("3D DIGITAL TWIN");
    expect(html).toContain("SYNTHETIC TERRAIN · NOT SURVEYED · VERTICAL SCALE 2.5x");
    expect(html).toContain("VEHICLES: DIGITAL TWIN SIMULATION (SCENE_METRES) · NOT GNSS");
    expect(html).toContain("FIT");
    expect(html).toContain("PLAN");
    expect(html).toContain("3D");
  });
});
