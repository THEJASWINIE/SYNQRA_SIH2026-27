/**
 * Driver screen — renders supplied values, marks absence, isolates the two trucks.
 *
 * Rendered with `react-dom/server`'s `renderToString` in the Node test environment (no
 * DOM, no WebGL). SOFTWARE ONLY: every value is a synthetic fixture.
 */

import type { ReactNode } from "react";
import { renderToString } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { type FreshnessConfig, freshnessConfig } from "../config/freshness";
import type { RoadState, SafetyState, VehicleState } from "../contracts/domain";
import { HmiContext } from "../state/ProviderHost";
import { AppStateStore } from "../state/store";
import { testHmiContext } from "../state/testHmiContext";
import { DriverScreen } from "./DriverScreen";
import { vehicleConfig } from "./vehicleConfig";
import { projectVehicle } from "./vehicleProjection";

const T = "2026-09-10T12:00:00.000Z";
const CONFIG = freshnessConfig(5000);

function vehicle(id: string, speedMps: number | null, timestamp = T): VehicleState {
  return {
    vehicleId: id,
    mode: "NORMAL",
    vehicleKind: "DUMPER",
    speedMps,
    position: { x: 0, y: 0, segmentId: "ROAD_1", offsetM: 0 },
    accelMps2: null,
    gradeRad: Math.atan(0.04),
    commConfidence: 1,
    frictionEst: null,
    routeId: null,
    timestamp,
  } as VehicleState;
}

function safety(id: string, overrides: Partial<SafetyState> = {}): SafetyState {
  return {
    vehicleId: id,
    timestamp: T,
    vSafe: 18 / 3.6,
    hSafe: 20,
    actualSpeed: 24 / 3.6,
    headwayCurrent: 12,
    leadVehicleId: "TRUCK_01",
    activeConstraint: "VISIBILITY",
    riskLevel: "HIGH",
    headwayViolation: false,
    envelopeViolation: false,
    ...overrides,
  };
}

const ROAD: RoadState = {
  segmentId: "ROAD_1",
  timestamp: T,
  visibility: { value: 15, sigma: 2 },
  friction: { value: 0.35, sigma: 0.05 },
  grade: Math.atan(0.04),
  capacityVph: null,
  queue: null,
  utilization: null,
  surfaceState: "WET",
  roughness: null,
};

function render(
  store: AppStateStore,
  id: "TRUCK_01" | "TRUCK_02",
  freshness: FreshnessConfig | null = CONFIG,
): string {
  const value = testHmiContext({ store, freshness });
  const wrap = (children: ReactNode) => (
    <HmiContext.Provider value={value}>{children}</HmiContext.Provider>
  );
  const projection = projectVehicle(store.getSnapshot(), id);
  return renderToString(wrap(<DriverScreen projection={projection} config={vehicleConfig(id)} />));
}

function storeWith(changes: Record<string, unknown>, now = T): AppStateStore {
  const store = new AppStateStore(now);
  store.applyPatch({ changes } as never, now);
  return store;
}

describe("driver screen — the spec's example", () => {
  const store = storeWith({
    vehicles: { TRUCK_01: vehicle("TRUCK_01", 28 / 3.6), TRUCK_02: vehicle("TRUCK_02", 24 / 3.6) },
    safety: { TRUCK_02: safety("TRUCK_02") },
    road: { ROAD_1: ROAD },
  });
  const html = render(store, "TRUCK_02");

  it("makes SLOW DOWN dominant and names the vehicle", () => {
    expect(html).toContain('data-driver-state="SLOW_DOWN"');
    expect(html).toContain("SLOW DOWN");
    expect(html).toContain("TRUCK_02");
  });

  it("keeps actual speed and safe speed as separate values", () => {
    expect(html).toContain("24 km/h");
    expect(html).toContain("18 km/h");
    expect(html).toContain("SPEED");
    expect(html).toContain("SAFE SPEED");
  });

  it("shows visibility with its fog wording, and gap vs required gap", () => {
    expect(html).toContain("15 m");
    expect(html).toContain("DENSE FOG");
    expect(html).toContain("12 m");
    expect(html).toContain("20 m");
    expect(html).toContain("FOLLOWING: FOLLOWING");
    expect(html).toContain("TRUCK_01");
  });

  it("always shows the active constraint and the risk", () => {
    expect(html).toContain("ACTIVE CONSTRAINT: FOG VISIBILITY");
    expect(html).toContain("RISK: HIGH");
  });

  it("shows road, condition and grade", () => {
    expect(html).toContain("ROAD_1");
    expect(html).toContain("WET");
    expect(html).toContain("+4%");
  });

  it("shows V2V and V2I states without inventing a link", () => {
    expect(html).toContain("V2V");
    expect(html).toContain("V2I");
    // No LoRa evidence in the fixture, and no physical RSU exists: UNAVAILABLE, not CONNECTED.
    expect(html).not.toContain("= CONNECTED");
  });

  it("marks the stopping margin UNAVAILABLE because the Twin does not supply it", () => {
    expect(html).toContain("STOPPING MARGIN");
    // The envelope flag IS supplied (false), so only the margin distance is missing.
    expect(html).toContain("envelope OK");
    const noFlag = render(
      storeWith({
        vehicles: { TRUCK_02: vehicle("TRUCK_02", 3) },
        safety: { TRUCK_02: safety("TRUCK_02", { envelopeViolation: null }) },
      }),
      "TRUCK_02",
    );
    expect(noFlag).toContain("not supplied by the Twin");
  });
});

describe("driver screen — fail closed", () => {
  it("with no safety slice shows SAFETY DATA UNAVAILABLE and no numbers for v_safe", () => {
    const store = storeWith({ vehicles: { TRUCK_01: vehicle("TRUCK_01", 5) } });
    const html = render(store, "TRUCK_01");
    expect(html).toContain('data-driver-state="SAFETY_DATA_UNAVAILABLE"');
    expect(html).toContain("DO NOT ASSUME SAFE");
    expect(html).not.toContain('data-driver-state="SAFE"');
  });

  it("with no vehicle at all renders UNAVAILABLE, never 0", () => {
    const store = storeWith({});
    const html = render(store, "TRUCK_02");
    expect(html).toContain("UNAVAILABLE");
    expect(html).not.toContain("0 km/h");
  });

  it("stale safety data becomes DATA STALE, not the last good state", () => {
    const later = "2026-09-10T12:00:30.000Z";
    const store = storeWith(
      {
        vehicles: { TRUCK_01: vehicle("TRUCK_01", 3, later) },
        safety: { TRUCK_01: safety("TRUCK_01", { actualSpeed: 3, headwayCurrent: 50 }) },
      },
      later,
    );
    const html = render(store, "TRUCK_01");
    expect(html).toContain('data-driver-state="DATA_STALE"');
    expect(html).toContain("DATA AGE");
  });

  it("says when staleness is not evaluated (no threshold configured)", () => {
    const store = storeWith({
      vehicles: { TRUCK_01: vehicle("TRUCK_01", 3) },
      safety: { TRUCK_01: safety("TRUCK_01", { actualSpeed: 3, headwayCurrent: 50 }) },
    });
    const html = render(store, "TRUCK_01", null);
    expect(html).toContain("staleness not evaluated");
  });
});

describe("driver screen — two trucks, two isolated displays", () => {
  const store = storeWith({
    vehicles: { TRUCK_01: vehicle("TRUCK_01", 22 / 3.6), TRUCK_02: vehicle("TRUCK_02", 24 / 3.6) },
    safety: {
      TRUCK_01: safety("TRUCK_01", {
        actualSpeed: 22 / 3.6,
        vSafe: 30 / 3.6,
        headwayCurrent: 42,
        leadVehicleId: null,
      }),
      TRUCK_02: safety("TRUCK_02"),
    },
    road: { ROAD_1: ROAD },
  });

  it("TRUCK_01 is SAFE with its own numbers", () => {
    const html = render(store, "TRUCK_01");
    expect(html).toContain('data-driver-state="SAFE"');
    expect(html).toContain("22 km/h");
    expect(html).toContain("30 km/h");
    expect(html).toContain("NO LEAD VEHICLE");
  });

  it("TRUCK_02 is SLOW DOWN with its own numbers and never TRUCK_01's", () => {
    const html = render(store, "TRUCK_02");
    expect(html).toContain('data-driver-state="SLOW_DOWN"');
    // Own SPEED cell is 24; TRUCK_01's 22 appears only in the cell labelled PEER.
    const own = html.indexOf("SPEED</div>");
    expect(html.slice(own, own + 120)).toContain("24 km/h");
    const peer = html.indexOf("PEER TRUCK_01");
    expect(peer).toBeGreaterThan(-1);
    expect(html.slice(peer, peer + 160)).toContain("22 km/h");
    expect(html.slice(0, peer)).not.toContain("22 km/h");
    expect(html).not.toContain("42 m");
  });
});
