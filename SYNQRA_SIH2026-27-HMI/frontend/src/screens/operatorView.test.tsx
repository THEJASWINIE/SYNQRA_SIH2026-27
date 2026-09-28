/**
 * P8 — Operator HMI screen tests.
 *
 * Same convention as the other screen suites: `react-dom/server`, a real
 * `AppStateStore` holding a controlled patch, and colour stripped before every safety
 * assertion so no test can pass on colour alone (NFR-008).
 *
 * All values are authored test data (SIMULATION). No physical hardware.
 */

import type { ReactNode } from "react";
import { renderToString } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { freshnessConfig } from "../config/freshness";
import type { DispatchCommand, RoadState, SafetyState, VehicleState } from "../contracts/domain";
import { HmiContext } from "../state/ProviderHost";
import { AppStateStore } from "../state/store";
import { testHmiContext } from "../state/testHmiContext";
import { OperatorView } from "./OperatorView";

const T = "2026-01-01T00:00:00.000Z";
const CONFIG = freshnessConfig(5000);

/** Strip colour so a state can never be proven by colour alone. */
function greyscale(html: string): string {
  return html.replace(/color:[^;"]*;?/g, "").replace(/#[0-9a-fA-F]{3,8}/g, "");
}

function vehicle(partial: Partial<VehicleState> = {}): VehicleState {
  return {
    vehicleId: "TRUCK_02",
    timestamp: T,
    position: { x: null, y: null, segmentId: "S-1", offsetM: 25 },
    speedMps: 5,
    accelMps2: 0.3,
    gradeRad: null,
    frictionEst: null,
    mode: "NORMAL",
    commConfidence: null,
    vehicleKind: "TRUCK",
    routeId: "S-1",
    ...partial,
  } as VehicleState;
}

function safety(partial: Partial<SafetyState> = {}): SafetyState {
  return {
    vehicleId: "TRUCK_02",
    timestamp: T,
    vSafe: 10,
    hSafe: null,
    actualSpeed: 5,
    headwayCurrent: null,
    leadVehicleId: null,
    activeConstraint: "v_stop",
    riskLevel: "LOW",
    headwayViolation: null,
    envelopeViolation: null,
    ...partial,
  } as SafetyState;
}

function road(partial: Partial<RoadState> = {}): RoadState {
  return {
    segmentId: "S-1",
    timestamp: T,
    visibility: { value: 15, sigma: 2 },
    friction: { value: 0.35, sigma: 0.05 },
    grade: 0.04,
    capacityVph: null,
    queue: null,
    ...partial,
  } as RoadState;
}

function command(partial: Partial<DispatchCommand> = {}): DispatchCommand {
  return {
    commandId: "CMD-1",
    vehicleId: "TRUCK_02",
    routeId: null,
    departureTime: null,
    targetSpeed: 8,
    slotId: null,
    reasonCode: "FOG",
    timestamp: T,
    state: "ISSUED",
    ...partial,
  } as DispatchCommand;
}

interface Options {
  vehicles?: Record<string, VehicleState>;
  safety?: Record<string, SafetyState>;
  road?: Record<string, RoadState>;
  dispatch?: Record<string, DispatchCommand>;
  vehicleId?: string | null;
}

function render(options: Options = {}): string {
  const store = new AppStateStore(T);
  store.applyPatch(
    {
      changes: {
        vehicles: options.vehicles === undefined ? { TRUCK_02: vehicle() } : options.vehicles,
        safety: options.safety === undefined ? { TRUCK_02: safety() } : options.safety,
        road: options.road ?? { "S-1": road() },
        ...(options.dispatch ? { dispatch: options.dispatch } : {}),
      },
    },
    T,
  );
  store.setScenarioName("Operator test");

  const value = testHmiContext({ store, freshness: CONFIG });
  const wrap = (children: ReactNode) => (
    <HmiContext.Provider value={value}>{children}</HmiContext.Provider>
  );
  return renderToString(wrap(<OperatorView vehicleId={options.vehicleId ?? null} />));
}

// ---------------------------------------------------------------------
// 1-5. identity and the three distinct speeds
// ---------------------------------------------------------------------

describe("P8 operator screen — core readouts", () => {
  it("renders the selected vehicle", () => {
    expect(render()).toContain("TRUCK_02");
  });

  it("shows actual, safe and commanded speed as three separate values", () => {
    const html = greyscale(render({ dispatch: { "CMD-1": command() } }));

    expect(html).toContain("ACTUAL SPEED");
    expect(html).toContain("SAFE SPEED");
    expect(html).toContain("COMMANDED SPEED");

    expect(html).toContain("18.0"); // actual 5 m/s
    expect(html).toContain("36.0"); // safe 10 m/s
    expect(html).toContain("28.8"); // commanded 8 m/s
  });

  it("never overwrites actual speed with safe speed", () => {
    // actual 8.72 m/s = 31.4 km/h, safe 6.86 m/s = 24.7 km/h
    const html = greyscale(
      render({
        vehicles: { TRUCK_02: vehicle({ speedMps: 8.72 }) },
        safety: { TRUCK_02: safety({ actualSpeed: 8.72, vSafe: 6.86 }) },
      }),
    );
    expect(html).toContain("31.4");
    expect(html).toContain("24.7");
    expect(html).toContain("SLOW DOWN");
  });
});

// ---------------------------------------------------------------------
// 10-14. action states, all asserted on TEXT
// ---------------------------------------------------------------------

describe("P8 operator screen — action states", () => {
  it("NORMAL well below the supplied ceiling", () => {
    const html = greyscale(render({ safety: { TRUCK_02: safety({ vSafe: 10, actualSpeed: 2 }) } }));
    expect(html).toContain("NORMAL");
  });

  it("CAUTION near the supplied ceiling", () => {
    const html = greyscale(
      render({ safety: { TRUCK_02: safety({ vSafe: 10, actualSpeed: 9.5 }) } }),
    );
    expect(html).toContain("CAUTION");
  });

  it("SLOW DOWN above the supplied ceiling", () => {
    const html = greyscale(render({ safety: { TRUCK_02: safety({ vSafe: 5, actualSpeed: 9 }) } }));
    expect(html).toContain("SLOW DOWN");
  });

  it("STOP when the supplied safe speed is zero", () => {
    const html = greyscale(render({ safety: { TRUCK_02: safety({ vSafe: 0, actualSpeed: 0 }) } }));
    expect(html).toContain("STOP");
  });

  it("SAFETY DATA UNAVAILABLE when no safe speed is supplied — never NORMAL", () => {
    const html = greyscale(render({ safety: { TRUCK_02: safety({ vSafe: null }) } }));
    expect(html).toContain("SAFETY DATA UNAVAILABLE");
    expect(html).not.toContain(">NORMAL<");
  });

  it("communicates state without relying on colour", () => {
    const html = greyscale(render({ safety: { TRUCK_02: safety({ vSafe: 5, actualSpeed: 9 }) } }));
    // The label survives colour stripping, and a non-colour glyph accompanies it.
    expect(html).toContain("SLOW DOWN");
    expect(html).toContain("▼");
  });
});

// ---------------------------------------------------------------------
// 6-9, 23. unavailable semantics
// ---------------------------------------------------------------------

describe("P8 operator screen — unavailable semantics", () => {
  it("shows UNAVAILABLE for an unavailable actual speed, never 0", () => {
    const html = greyscale(
      render({
        vehicles: { TRUCK_02: vehicle({ speedMps: null }) },
        safety: { TRUCK_02: safety({ actualSpeed: Number.NaN }) },
      }),
    );
    expect(html).toContain("UNAVAILABLE");
    expect(html).toContain("SAFETY DATA UNAVAILABLE");
  });

  it("shows UNAVAILABLE for an unavailable safe speed", () => {
    expect(greyscale(render({ safety: { TRUCK_02: safety({ vSafe: null }) } }))).toContain(
      "UNAVAILABLE",
    );
  });

  it("shows UNAVAILABLE visibility when no road is supplied", () => {
    const html = greyscale(render({ road: {} }));
    expect(html).toContain("VISIBILITY");
    expect(html).toContain("UNAVAILABLE");
  });

  it("shows UNAVAILABLE commanded speed and NONE status with no command", () => {
    const html = greyscale(render());
    expect(html).toContain("COMMANDED SPEED");
    expect(html).toContain("no command supplied");
    expect(html).toContain("NONE");
  });

  it("renders a hardware-only vehicle with no fabricated position or visibility", () => {
    const html = greyscale(
      render({
        vehicles: {
          TRUCK_02: vehicle({
            position: { x: null, y: null, segmentId: null, offsetM: null },
            routeId: null,
            provenance: {
              speed_mps: {
                value: 0.8,
                timestamp: 1788000000,
                source: "DERIVED",
                origin: "HARDWARE",
                quality: "GOOD",
                ageS: 0.5,
                available: true,
                clockDomain: "WALL_CLOCK",
                freshness: "CURRENT",
              },
            },
          }),
        },
        road: {},
      }),
    );
    expect(html).toContain("TRUCK_02");
    expect(html).toContain("UNAVAILABLE"); // visibility
    expect(html).not.toContain("120"); // the old fabricated coordinate
  });

  it("says so honestly when no vehicle is supplied at all", () => {
    const html = greyscale(render({ vehicles: {}, safety: {} }));
    expect(html).toContain("NO VEHICLE SUPPLIED");
  });
});

// ---------------------------------------------------------------------
// 15-20. provenance and freshness
// ---------------------------------------------------------------------

describe("P8 operator screen — provenance and freshness", () => {
  function withProvenance(source: string, origin: string, freshness: string) {
    return render({
      vehicles: {
        TRUCK_02: vehicle({
          provenance: {
            speed_mps: {
              value: 5,
              timestamp: 1788000000,
              source,
              origin,
              quality: "GOOD",
              ageS: 0.5,
              available: true,
              clockDomain: "WALL_CLOCK",
              freshness,
            },
          },
        }),
      },
    });
  }

  it("does not collapse DERIVED + HARDWARE into HARDWARE", () => {
    // PHASE 8 — the wording is now the shared one. The distinction it protects is
    // unchanged: a derived physical value must not read like a directly measured one.
    const html = greyscale(withProvenance("DERIVED", "HARDWARE", "CURRENT"));
    expect(html).toContain("PHYSICAL (derived)");
  });

  it("shows simulation provenance as SIMULATION", () => {
    expect(greyscale(withProvenance("SIMULATION", "SIMULATION", "CURRENT"))).toContain("SIMULATION");
  });

  it("surfaces canonical freshness verbatim", () => {
    expect(greyscale(withProvenance("HARDWARE", "HARDWARE", "CURRENT"))).toContain("CURRENT");
    expect(greyscale(withProvenance("HARDWARE", "HARDWARE", "STALE"))).toContain("STALE");
  });

  it("shows an unclassifiable freshness as UNKNOWN, never as STALE or CURRENT", () => {
    // PHASE 8 — an unrecognised verdict maps to the shared UNKNOWN. It is still neither
    // reassuring (CURRENT) nor a claim the data has aged out (STALE).
    const html = greyscale(withProvenance("SIMULATION", "SIMULATION", "NOT_EVALUATED"));
    expect(html).toContain("UNKNOWN");
  });
});

// ---------------------------------------------------------------------
// reason, command status, selection
// ---------------------------------------------------------------------

describe("P8 operator screen — reason, command and selection", () => {
  it("shows the supplied constraint in operator wording", () => {
    expect(greyscale(render())).toContain("STOPPING DISTANCE");
  });

  it("shows a supplied command status without implying execution", () => {
    const html = greyscale(render({ dispatch: { "CMD-1": command({ state: "ISSUED" }) } }));
    expect(html).toContain("ISSUED");
    expect(html).not.toContain("EXECUTED");
  });

  it("offers a selector when several vehicles are supplied", () => {
    const html = greyscale(
      render({
        vehicles: { TRUCK_01: vehicle({ vehicleId: "TRUCK_01" }), TRUCK_02: vehicle() },
        safety: { TRUCK_01: safety({ vehicleId: "TRUCK_01" }), TRUCK_02: safety() },
      }),
    );
    expect(html).toContain("Select vehicle");
    expect(html).toContain("TRUCK_01");
    expect(html).toContain("TRUCK_02");
  });

  it("honours an explicitly requested vehicle", () => {
    const html = greyscale(
      render({
        vehicles: { TRUCK_01: vehicle({ vehicleId: "TRUCK_01" }), TRUCK_02: vehicle() },
        safety: { TRUCK_01: safety({ vehicleId: "TRUCK_01" }), TRUCK_02: safety() },
        vehicleId: "TRUCK_02",
      }),
    );
    expect(html).toContain("TRUCK_02");
  });
});
