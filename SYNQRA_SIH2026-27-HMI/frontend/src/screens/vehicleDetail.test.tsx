/**
 * S2 Vehicle Detail tests — M5.
 *
 * Rendered with `react-dom/server`, the pattern M1 established. No jsdom and no
 * @testing-library (M4D-C). Screens are mounted against a real `AppStateStore` holding a
 * controlled patch, so the data path under test is the production one.
 *
 * ASSERTIONS ARE AGAINST TEXT. Colour is stripped before every safety assertion, so no
 * test can pass on a colour attribute alone (NFR-008).
 */

import type { ReactNode } from "react";
import { renderToString } from "react-dom/server";
import { describe, expect, it } from "vitest";
import { type FreshnessConfig, freshnessConfig } from "../config/freshness";
import type { ConnectionStatus } from "../contracts/appState";
import type {
  Health,
  MineTopology,
  RoadState,
  SafetyState,
  VehicleState,
} from "../contracts/domain";
import { HmiContext } from "../state/ProviderHost";
import { AppStateStore } from "../state/store";
import { testHmiContext } from "../state/testHmiContext";
import { VehicleDetail } from "./VehicleDetail";

const T = "2026-01-01T00:00:00.000Z";
const CONFIG = freshnessConfig(5000);

function greyscale(html: string): string {
  return html.replace(/color:[^;"]*;?/g, "").replace(/#[0-9a-fA-F]{3,8}/g, "");
}

function topology(): MineTopology {
  return {
    version: "1",
    nodes: [
      { nodeId: "N-1", kind: "SHOVEL", label: "Shovel", x: 0, y: 0 },
      { nodeId: "N-2", kind: "CRUSHER", label: "Crusher", x: 100, y: 200 },
    ],
    segments: [
      {
        segmentId: "S-1",
        fromNode: "N-1",
        toNode: "N-2",
        lengthM: 100,
        gradeRad: 0.04,
        bidirectional: true,
      },
    ],
  };
}

function vehicle(partial: Partial<VehicleState> = {}): VehicleState {
  return {
    vehicleId: "TRUCK-07",
    timestamp: T,
    position: { x: null, y: null, segmentId: "S-1", offsetM: 25 },
    speedMps: 12.5,
    accelMps2: 0.3,
    gradeRad: 0.04,
    frictionEst: { value: 0.55, sigma: 0.03 },
    mode: "NORMAL",
    commConfidence: 0.92,
    vehicleKind: "TRUCK",
    routeId: "R-1",
    ...partial,
  };
}

function safety(partial: Partial<SafetyState> = {}): SafetyState {
  return {
    vehicleId: "TRUCK-07",
    timestamp: T,
    vSafe: 15,
    hSafe: 60,
    actualSpeed: 12.5,
    headwayCurrent: 41,
    leadVehicleId: "TRUCK-03",
    activeConstraint: "VISIBILITY",
    riskLevel: "MODERATE",
    headwayViolation: null,
    envelopeViolation: null,
    ...partial,
  };
}

function road(partial: Partial<RoadState> = {}): RoadState {
  return {
    segmentId: "S-1",
    timestamp: T,
    visibility: { value: 180, sigma: 12 },
    friction: { value: 0.58, sigma: 0.04 },
    grade: 0.04,
    capacityVph: 40,
    queue: 2,
    utilization: 0.6,
    surfaceState: "WET",
    roughness: null,
    ...partial,
  };
}

const link: Health = {
  componentId: "V2I-GW-1",
  timestamp: T,
  state: "DEGRADED",
  latencyMs: 140,
  ageMs: 800,
  errorCode: null,
  linkKind: "V2I",
  messagesReceived: 1200,
  messagesDropped: 3,
};

interface MountOptions {
  vehicles?: Record<string, VehicleState>;
  safety?: Record<string, SafetyState>;
  road?: Record<string, RoadState>;
  topology?: MineTopology | null;
  health?: boolean;
  status?: ConnectionStatus;
  error?: string | null;
  config?: FreshnessConfig | null;
  nowIso?: string;
}

/** Mounts S2 against a real store holding the supplied patch. */
function render(vehicleId: string | null, options: MountOptions = {}): string {
  const store = new AppStateStore(T);

  store.applyPatch(
    {
      changes: {
        vehicles: options.vehicles ?? { "TRUCK-07": vehicle() },
        safety: options.safety ?? { "TRUCK-07": safety() },
        road: options.road ?? { "S-1": road() },
        topology: options.topology === undefined ? topology() : options.topology,
        ...(options.health
          ? {
              health: {
                timestamp: T,
                systemMode: "NORMAL" as const,
                connectivity: "DEGRADED" as const,
                fleetCount: 1,
                components: [link],
              },
            }
          : {}),
      },
    },
    T,
  );

  if (options.status) store.setStatus(options.status, options.error ?? null);
  store.setScenarioName("Test scenario");
  if (options.nowIso) store.tick(options.nowIso);

  const value = testHmiContext({
    store,
    freshness: options.config === undefined ? CONFIG : options.config,
  });

  const wrap = (children: ReactNode) => (
    <HmiContext.Provider value={value}>{children}</HmiContext.Provider>
  );

  return renderToString(wrap(<VehicleDetail vehicleId={vehicleId} onBack={() => {}} />));
}

// ---------------------------------------------------------------------------

describe("selection and navigation (tests 1, 2, 3)", () => {
  it("renders the selected vehicle's identity", () => {
    const html = render("TRUCK-07");
    expect(html).toContain("TRUCK-07");
    expect(html).toContain("Vehicle state");
  });

  it("always offers a return path to Operations Overview", () => {
    for (const id of ["TRUCK-07", "NOPE", null]) {
      expect(render(id)).toContain("Back to Operations Overview");
    }
  });

  it("renders NO VEHICLE SELECTED when nothing is selected", () => {
    const html = render(null);
    expect(html).toContain("NO VEHICLE SELECTED");
    expect(html).not.toContain("Vehicle state");
  });
});

describe("unknown and removed vehicles (tests 4, 5)", () => {
  it("an unknown id reports that it is not in current state", () => {
    const html = render("NO-SUCH-TRUCK");
    expect(html).toContain("VEHICLE NOT IN CURRENT STATE");
    expect(html).toContain("NO-SUCH-TRUCK");
  });

  it("a vehicle removed after selection is reported, not rendered from a stale copy", () => {
    // The selected id is still TRUCK-07, but supplied state no longer contains it.
    const html = render("TRUCK-07", { vehicles: {}, safety: {} });
    expect(html).toContain("VEHICLE NOT IN CURRENT STATE");
    expect(html).toContain("No remembered values are shown");
    // No speed, no risk, nothing survives from the previous selection.
    expect(html).not.toContain("Actual speed");
  });
});

describe("actual versus safe speed (tests 6, 7, 8, 9)", () => {
  it("actualSpeed > vSafe renders an explicit TEXTUAL violation marker", () => {
    const html = greyscale(
      render("TRUCK-07", { safety: { "TRUCK-07": safety({ actualSpeed: 20, vSafe: 10 }) } }),
    );
    expect(html).toContain("OVER SAFE SPEED");
  });

  it("actualSpeed <= vSafe produces no false violation", () => {
    const html = greyscale(
      render("TRUCK-07", { safety: { "TRUCK-07": safety({ actualSpeed: 8, vSafe: 15 }) } }),
    );
    expect(html).not.toContain("OVER SAFE SPEED");
    expect(html).toContain("WITHIN SAFE SPEED");
  });

  it("labels actual and safe speed separately and readably", () => {
    const html = render("TRUCK-07");
    expect(html).toContain("Actual speed");
    expect(html).toContain("Safe speed (supplied)");
    expect(html).toContain("km/h");
  });

  it("a missing safe speed renders UNAVAILABLE and NOT COMPARABLE, never a comparison", () => {
    const html = greyscale(
      render("TRUCK-07", { safety: { "TRUCK-07": safety({ actualSpeed: 99, vSafe: null }) } }),
    );
    expect(html).toContain("UNAVAILABLE");
    expect(html).toContain("NOT COMPARABLE");
    expect(html).not.toContain("OVER SAFE SPEED");
    expect(html).not.toContain("WITHIN SAFE SPEED");
  });

  it("no supplied safety data at all is stated, and nothing is derived", () => {
    const html = render("TRUCK-07", { safety: {} });
    expect(html).toContain("NO SUPPLIED SAFETY DATA");
    expect(html).toContain("none is derived locally");
  });

  it("the active constraint is rendered from the supplied enum", () => {
    const html = render("TRUCK-07", {
      safety: { "TRUCK-07": safety({ activeConstraint: "BRAKING_RETARDER" }) },
    });
    expect(html).toContain("BRAKING RETARDER");
  });

  it("an UNKNOWN risk renders as unknown, never as low or blank", () => {
    const html = greyscale(
      render("TRUCK-07", { safety: { "TRUCK-07": safety({ riskLevel: "UNKNOWN" }) } }),
    );
    expect(html).toContain("UNKNOWN");
    expect(html).not.toContain("RISK LOW");
  });
});

describe("headway — AMB-001 (tests 10, 11, 12)", () => {
  it("attaches no invented unit to H_safe", () => {
    const html = render("TRUCK-07");
    expect(html).toContain("Required H_safe");
    expect(html).toContain("unit unresolved — AMB-001");
    // The two units a guess would reach for must not appear against the headway values.
    const headwayBlock = html.slice(
      html.indexOf("Required H_safe"),
      html.indexOf("Required H_safe") + 400,
    );
    expect(headwayBlock).not.toMatch(/H_safe[\s\S]{0,120}>m</);
    expect(headwayBlock).not.toMatch(/H_safe[\s\S]{0,120}>s</);
  });

  it("does not compare headwayCurrent with hSafe numerically", () => {
    // 41 against 60 would be "within" under one unit and meaningless under another.
    const html = greyscale(
      render("TRUCK-07", {
        safety: { "TRUCK-07": safety({ headwayCurrent: 41, hSafe: 60, headwayViolation: null }) },
      }),
    );
    expect(html).toContain("HEADWAY VIOLATION NOT SUPPLIED");
    expect(html).not.toContain("▲ HEADWAY VIOLATION (supplied)");
    expect(html).toContain("are NOT compared numerically");
  });

  it("renders a SUPPLIED headway violation when Task 2 sends one", () => {
    const html = greyscale(
      render("TRUCK-07", { safety: { "TRUCK-07": safety({ headwayViolation: true }) } }),
    );
    expect(html).toContain("HEADWAY VIOLATION (supplied)");
  });

  it("renders a supplied false flag as no violation", () => {
    const html = greyscale(
      render("TRUCK-07", { safety: { "TRUCK-07": safety({ headwayViolation: false }) } }),
    );
    expect(html).toContain("NO HEADWAY VIOLATION (supplied)");
  });

  it("shows the lead vehicle when supplied, and states its absence when not", () => {
    expect(render("TRUCK-07")).toContain("TRUCK-03");
    const html = render("TRUCK-07", {
      safety: { "TRUCK-07": safety({ leadVehicleId: null }) },
    });
    expect(html).toContain("Lead vehicle");
    expect(html).toContain("UNAVAILABLE");
  });
});

describe("position (tests 16, 17, 18)", () => {
  it("derives the map coordinate from supplied segment geometry", () => {
    // offsetM 25 of lengthM 100 = 0.25 along (0,0) -> (100,200) = (25, 50).
    const html = render("TRUCK-07");
    expect(html).toContain("25.0, 50.0");
    expect(html).toContain("derived from supplied segment geometry");
  });

  it("prefers supplied coordinates when they exist", () => {
    const html = render("TRUCK-07", {
      vehicles: {
        "TRUCK-07": vehicle({ position: { x: 7, y: 9, segmentId: "S-1", offsetM: 25 } }),
      },
    });
    expect(html).toContain("7.0, 9.0");
    expect(html).toContain("supplied coordinates");
  });

  it("insufficient geometry renders POSITION UNAVAILABLE with the missing input named", () => {
    const html = render("TRUCK-07", {
      vehicles: {
        "TRUCK-07": vehicle({ position: { x: null, y: null, segmentId: "S-1", offsetM: null } }),
      },
    });
    expect(html).toContain("POSITION UNAVAILABLE");
    expect(html).toContain("no offset along segment supplied");
  });

  it("no topology renders POSITION UNAVAILABLE, not a guessed point", () => {
    const html = render("TRUCK-07", { topology: null });
    expect(html).toContain("POSITION UNAVAILABLE");
    expect(html).toContain("no topology supplied");
  });

  it("an unknown segment is never placed at a nearby node", () => {
    const html = render("TRUCK-07", {
      vehicles: {
        "TRUCK-07": vehicle({ position: { x: null, y: null, segmentId: "S-X", offsetM: 25 } }),
      },
    });
    expect(html).toContain("POSITION UNAVAILABLE");
    expect(html).toContain("segment not in supplied topology");
  });
});

describe("supplied vehicle fields (FR-003)", () => {
  it("renders friction with its uncertainty, never bare (FR-003 AC2)", () => {
    const html = render("TRUCK-07");
    expect(html).toContain("Friction estimate");
    expect(html).toContain("0.55");
    expect(html).toContain("0.03");
  });

  it("states when sigma was not supplied rather than omitting it", () => {
    const html = render("TRUCK-07", {
      vehicles: { "TRUCK-07": vehicle({ frictionEst: { value: 0.5, sigma: null } }) },
    });
    expect(html).toContain("σ not supplied");
  });

  it("renders grade for the vehicle (S2-a)", () => {
    expect(render("TRUCK-07")).toContain("Grade (vehicle)");
  });

  it("renders the occupied segment's road condition (FR-011, FR-012)", () => {
    const html = render("TRUCK-07");
    expect(html).toContain("Visibility");
    expect(html).toContain("Friction");
    expect(html).toContain("Surface");
    expect(html).toContain("WET");
  });

  it("omits roughness when it was not supplied, and shows it when it was", () => {
    expect(render("TRUCK-07")).not.toContain("Roughness");
    expect(render("TRUCK-07", { road: { "S-1": road({ roughness: 1.4 }) } })).toContain(
      "Roughness",
    );
  });

  it("states when no road state was supplied for the segment", () => {
    const html = render("TRUCK-07", { road: {} });
    expect(html).toContain("NO ROAD STATE SUPPLIED");
  });

  it("never replaces an unavailable value with zero", () => {
    const html = render("TRUCK-07", {
      vehicles: {
        "TRUCK-07": vehicle({
          routeId: null,
          frictionEst: { value: null, sigma: null },
          position: { x: null, y: null, segmentId: null, offsetM: null },
        }),
      },
      road: {},
    });
    expect(html).toContain("UNAVAILABLE");
    expect(html).toContain("SEGMENT UNAVAILABLE");
  });
});

describe("communication (FR-013)", () => {
  it("renders supplied link rows with kind, state and supplied age", () => {
    const html = render("TRUCK-07", { health: true });
    expect(html).toContain("V2I");
    expect(html).toContain("DEGRADED");
    expect(html).toContain("140 ms");
  });

  it("states when no link health was supplied", () => {
    expect(render("TRUCK-07")).toContain("NO LINK HEALTH SUPPLIED");
  });

  it("does not classify comm confidence into a band — no threshold is specified", () => {
    const html = render("TRUCK-07");
    expect(html).toContain("0.92");
    expect(html).toContain("PAD-G forbids inventing one");
  });
});

describe("connection states (tests 13, 14)", () => {
  it("renders a disconnected provider explicitly", () => {
    const html = greyscale(render("TRUCK-07", { status: "DISCONNECTED" }));
    expect(html).toContain("Disconnected");
  });

  it("renders a reconnecting provider explicitly", () => {
    expect(greyscale(render("TRUCK-07", { status: "RECONNECTING" }))).toContain("Reconnecting");
  });

  it("renders a provider error with its message", () => {
    const html = greyscale(render("TRUCK-07", { status: "ERROR", error: "V2I link lost" }));
    expect(html).toContain("Provider error");
    expect(html).toContain("V2I link lost");
  });

  it("keeps showing supplied values while disconnected, marked by their age", () => {
    const html = render("TRUCK-07", { status: "DISCONNECTED" });
    expect(html).toContain("Actual speed");
    expect(html).toContain("Vehicle timestamp (source)");
  });
});

describe("freshness (test 15)", () => {
  it("classifies as CURRENT when a threshold is configured and data is recent", () => {
    expect(render("TRUCK-07")).toContain("CURRENT");
  });

  it("classifies as STALE past the configured threshold, keeping the value", () => {
    const html = render("TRUCK-07", { nowIso: "2026-01-01T00:01:00.000Z" });
    expect(html).toContain("STALE");
    expect(html).toContain("Actual speed");
  });

  it("with no configured threshold, shows age but does NOT classify", () => {
    const html = render("TRUCK-07", { config: null });
    expect(html).toContain("AGE ONLY — NOT CLASSIFIED");
    expect(html).not.toContain(">CURRENT<");
  });

  it("never invents OK or STALE from an unconfigured threshold", () => {
    const html = render("TRUCK-07", { config: null, nowIso: "2026-01-01T01:00:00.000Z" });
    expect(html).toContain("AGE ONLY — NOT CLASSIFIED");
    expect(html).not.toContain(">STALE<");
  });

  it("shows source timestamps and provenance", () => {
    const html = render("TRUCK-07");
    expect(html).toContain("Vehicle timestamp (source)");
    expect(html).toContain("Provider");
    expect(html).toContain("Test scenario");
  });
});

describe("scope (test 19)", () => {
  it("S2 renders no control that could command or actuate anything", () => {
    const html = render("TRUCK-07", { health: true });
    // The only interactive element is the back link.
    const buttons = html.match(/<button/g) ?? [];
    expect(buttons).toHaveLength(1);
    expect(html).not.toContain("<form");
    expect(html).not.toContain("Acknowledge");
  });

  it("records the unsupplied trend honestly instead of fabricating one (S2-b)", () => {
    const html = render("TRUCK-07");
    expect(html).toContain("TREND DATA NOT SUPPLIED");
    expect(html).toContain("not accumulated locally");
  });
});
