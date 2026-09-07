/**
 * Cross-screen consistency — Phase 8 §9.
 *
 * ONE vehicle, ONE store, rendered through EVERY screen that shows it. The same field
 * must read the same way on all of them.
 *
 * This is the test the phase exists for. Each screen already has its own suite, and every
 * one of them passed while the screens disagreed with each other: a hardware-derived speed
 * read "PHYSICAL (derived)" on S3, "PHYSICAL" on S4 and "DERIVED · HARDWARE" on the
 * operator view, and the operator view reported a healthy link while the Twin was
 * supplying COMMUNICATION_DEGRADED. Only a test that renders them together can see that.
 *
 * `react-dom/server`, no jsdom, no Testing Library (M4D-C).
 */

import type { ReactNode } from "react";
import { renderToString } from "react-dom/server";
import { describe, expect, it } from "vitest";
import { freshnessConfig } from "../config/freshness";
import type { TwinFieldProvenance, VehicleState } from "../contracts/domain";
import { HmiContext } from "../state/ProviderHost";
import { AppStateStore } from "../state/store";
import { testHmiContext } from "../state/testHmiContext";
import { DigitalTwin } from "./DigitalTwin";
import { DispatchSlots } from "./DispatchSlots";
import { OperationsOverview } from "./OperationsOverview";
import { OperatorView } from "./OperatorView";
import { SafetyEnvironment } from "./SafetyEnvironment";
import { VehicleDetail } from "./VehicleDetail";

const T = "2026-01-01T00:00:00.000Z";
const CONFIG = freshnessConfig(5000);
const VEHICLE_ID = "TRUCK_01";

function field(partial: Partial<TwinFieldProvenance> = {}): TwinFieldProvenance {
  return {
    value: 0.9797,
    timestamp: 1_788_681_152,
    source: "SIMULATION",
    origin: "SIMULATION",
    quality: "GOOD",
    ageS: 0.2,
    available: true,
    clockDomain: "WALL_CLOCK",
    freshness: "CURRENT",
    ...partial,
  };
}

/**
 * A vehicle chosen to be maximally revealing:
 *   - speed DERIVED from HARDWARE, the case three screens used to disagree about
 *   - communication DEGRADED while telemetry is CURRENT, the pair that must not merge
 */
function vehicle(partial: Partial<VehicleState> = {}): VehicleState {
  return {
    vehicleId: VEHICLE_ID,
    timestamp: T,
    position: { x: null, y: null, segmentId: null, offsetM: null },
    speedMps: 0.9797,
    accelMps2: null,
    gradeRad: null,
    frictionEst: null,
    mode: "NORMAL",
    commConfidence: null,
    vehicleKind: "TRUCK",
    routeId: null,
    provenance: {
      speed_mps: field({ source: "DERIVED", origin: "HARDWARE" }),
      communication_state: field({ value: "COMMUNICATION_DEGRADED" }),
    },
    ...partial,
  };
}

/** Renders every screen against one shared store holding exactly this vehicle. */
function renderAll(v: VehicleState): Record<string, string> {
  const store = new AppStateStore(T);
  store.applyPatch({ changes: { vehicles: { [VEHICLE_ID]: v } } }, T);
  store.setStatus("CONNECTED", null);

  const value = testHmiContext({ store, freshness: CONFIG });
  const wrap = (children: ReactNode) =>
    renderToString(<HmiContext.Provider value={value}>{children}</HmiContext.Provider>);

  return {
    "S1 Operations": wrap(<OperationsOverview onSelectVehicle={() => {}} />),
    "S2 Vehicle Detail": wrap(<VehicleDetail vehicleId={VEHICLE_ID} onBack={() => {}} />),
    "S3 Safety / Environment": wrap(<SafetyEnvironment vehicleId={VEHICLE_ID} />),
    "S4 Dispatch": wrap(<DispatchSlots />),
    "S6 Digital Twin": wrap(<DigitalTwin vehicleId={VEHICLE_ID} />),
    Operator: wrap(<OperatorView vehicleId={VEHICLE_ID} />),
  };
}

function greyscale(html: string): string {
  return html.replace(/color:[^;"]*;?/g, "").replace(/#[0-9a-fA-F]{3,8}/g, "");
}

describe("provenance agrees across every screen (§9)", () => {
  const screens = renderAll(vehicle());

  it("every screen that names provenance uses the same words for it", () => {
    for (const [name, html] of Object.entries(screens)) {
      if (!html.includes("PHYSICAL")) continue; // this screen does not show provenance
      expect(html, `${name} uses the shared wording`).toContain("PHYSICAL (derived)");
    }
  });

  it("no screen keeps one of the superseded wordings", () => {
    for (const [name, html] of Object.entries(screens)) {
      expect(html, `${name} kept an old provenance wording`).not.toContain("DERIVED · HARDWARE");
    }
  });

  it("a derived physical value never reads as a directly measured one", () => {
    for (const [name, html] of Object.entries(screens)) {
      if (!html.includes("PHYSICAL")) continue;
      // "PHYSICAL" must only ever appear as part of "PHYSICAL (derived)" for this vehicle.
      const bare = html.split("PHYSICAL").length - 1;
      const derived = html.split("PHYSICAL (derived)").length - 1;
      expect(bare, `${name} shows a bare PHYSICAL`).toBe(derived);
    }
  });

  it("S1 and S2 now show provenance at all", () => {
    // Before Phase 8 neither did, so a simulated speed and a measured one looked identical
    // on the two most-used screens in the HMI.
    expect(screens["S1 Operations"]).toContain("PHYSICAL (derived)");
    expect(screens["S2 Vehicle Detail"]).toContain("PHYSICAL (derived)");
  });
});

describe("communication agrees across every screen (§15)", () => {
  const screens = renderAll(vehicle());

  it("every screen that names the link reports the SUPPLIED state", () => {
    for (const [name, html] of Object.entries(screens)) {
      if (!html.includes("COMMUNICATION") && !html.includes("Communication")) continue;
      expect(html, `${name} hides the degraded link`).toContain("COMMUNICATION_DEGRADED");
    }
  });

  it("no screen claims a healthy link the Twin did not report", () => {
    for (const [name, html] of Object.entries(screens)) {
      expect(greyscale(html), `${name} invents CONNECTED`).not.toMatch(
        /COMMUNICATION:\s*<strong>CONNECTED/,
      );
    }
  });

  it("a degraded link does not make the telemetry look stale", () => {
    // Both facts are true at once and both are shown; neither overwrites the other.
    for (const [name, html] of Object.entries(screens)) {
      if (!html.includes("COMMUNICATION_DEGRADED")) continue;
      expect(html, `${name} downgraded fresh telemetry`).not.toContain("TELEMETRY STALE");
    }
  });
});

describe("unavailable behaviour agrees across every screen (§6)", () => {
  const bare = renderAll(
    vehicle({ speedMps: null, provenance: { speed_mps: field({ available: false }) } }),
  );

  it("an unsupplied speed is never rendered as zero anywhere", () => {
    for (const [name, html] of Object.entries(bare)) {
      expect(greyscale(html), `${name} fabricated a zero speed`).not.toContain(">0.0<");
    }
  });

  it("an unsupplied field renders as -- or UNAVAILABLE, never blank", () => {
    for (const [name, html] of Object.entries(bare)) {
      const marked = html.includes("--") || html.includes("UNAVAILABLE");
      expect(marked, `${name} left an unsupplied field unmarked`).toBe(true);
    }
  });
});

describe("stale telemetry is shown, not hidden (§7, §18)", () => {
  const stale = renderAll(vehicle({ provenance: { speed_mps: field({ freshness: "STALE" }) } }));

  it("the last known value stays visible beside the stale marker", () => {
    // 0.9797 m/s -> 3.5 km/h. The value is not blanked, zeroed or replaced.
    expect(stale["S4 Dispatch"]).toContain("3.5");
    expect(stale["S4 Dispatch"]).toContain("STALE");
  });

  it("S4 warns the operator without inventing a rejection", () => {
    const html = stale["S4 Dispatch"] ?? "";
    expect(html).toContain("TELEMETRY STALE");
    expect(html).toContain("CommandGateway decides acceptance");
    // The HMI must not pre-fail a command the gateway has not seen.
    expect(html).not.toContain("COMMAND REJECTED");
  });

  it("stale telemetry never reads as CURRENT on the same screen", () => {
    const html = stale.Operator ?? "";
    expect(html).toContain("STALE");
    expect(html).not.toMatch(/FRESHNESS:\s*<strong>CURRENT/);
  });
});
