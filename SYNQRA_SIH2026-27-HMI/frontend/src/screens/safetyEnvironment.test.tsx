/**
 * S3 Safety / Environment tests — Phase 6.
 *
 * `react-dom/server`, mounted against a real `AppStateStore` via `HmiContext` (M5D-B).
 * No jsdom, no Testing Library (M4D-C).
 *
 * THE CENTRAL ASSERTION OF THIS FILE: nothing that was not supplied ever appears as a
 * number. A fabricated safe speed is the most dangerous output this screen could produce,
 * so most of these tests are about what must be ABSENT.
 *
 * Colour is stripped before every safety-relevant assertion (NFR-008).
 */

import type { ReactNode } from "react";
import { renderToString } from "react-dom/server";
import { describe, expect, it } from "vitest";
import { freshnessConfig } from "../config/freshness";
import type { RoadState, SafetyState, VehicleState } from "../contracts/domain";
import { HmiContext } from "../state/ProviderHost";
import {
  activeConstraintText,
  envelopeView,
  environmentReadouts,
  isPhysical,
  operatingReadouts,
  provenanceLabel,
  safetyStateText,
  stoppingDistanceText,
} from "../state/safetyEnvironment";
import { AppStateStore } from "../state/store";
import { testHmiContext } from "../state/testHmiContext";
import { SafetyEnvironment } from "./SafetyEnvironment";

const T = "2026-01-01T00:00:00.000Z";
const CONFIG = freshnessConfig(5000);
const SCREEN_SOURCE = "src/screens/SafetyEnvironment.tsx";

function greyscale(html: string): string {
  return html.replace(/color:[^;"]*;?/g, "").replace(/#[0-9a-fA-F]{3,8}/g, "");
}

async function screenSource(): Promise<string> {
  const fs = await import("node:fs");
  return fs.readFileSync(SCREEN_SOURCE, "utf-8");
}

/** Provenance in the exact shape the live backend supplies for the simulated producer. */
const SIMULATED_PROVENANCE = {
  speed_mps: {
    value: 0.9797,
    timestamp: 1_788_681_152,
    source: "SIMULATION",
    origin: "SIMULATION",
    quality: "GOOD",
    ageS: 0.2,
    available: true,
    clockDomain: "WALL_CLOCK",
    freshness: "CURRENT",
  },
  communication_state: {
    value: "HEALTHY",
    timestamp: 1_788_681_152,
    source: "SIMULATION",
    origin: "SIMULATION",
    quality: "GOOD",
    ageS: 0.2,
    available: true,
    clockDomain: "WALL_CLOCK",
    freshness: "CURRENT",
  },
};

function vehicle(partial: Partial<VehicleState> = {}): VehicleState {
  return {
    vehicleId: "TRUCK_01",
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
    provenance: SIMULATED_PROVENANCE,
    ...partial,
  };
}

function safetyState(partial: Partial<SafetyState> = {}): SafetyState {
  return {
    vehicleId: "TRUCK_01",
    timestamp: T,
    vSafe: 10,
    hSafe: null,
    actualSpeed: 0.9797,
    headwayCurrent: null,
    leadVehicleId: null,
    activeConstraint: "VISIBILITY",
    riskLevel: "LOW",
    headwayViolation: null,
    envelopeViolation: null,
    ...partial,
  };
}

function roadState(partial: Partial<RoadState> = {}): RoadState {
  return {
    segmentId: "S-1",
    timestamp: T,
    visibility: { value: 15, sigma: 2 },
    friction: { value: 0.3, sigma: 0.05 },
    grade: 0.04,
    capacityVph: null,
    queue: null,
    utilization: null,
    surfaceState: "WET",
    roughness: null,
    ...partial,
  };
}

interface MountOptions {
  vehicles?: Record<string, VehicleState>;
  safety?: Record<string, SafetyState>;
  road?: Record<string, RoadState>;
  nowIso?: string;
  vehicleId?: string | null;
}

function render(options: MountOptions = {}): string {
  const store = new AppStateStore(T);

  store.applyPatch(
    {
      changes: {
        vehicles: options.vehicles ?? { TRUCK_01: vehicle() },
        ...(options.safety ? { safety: options.safety } : {}),
        ...(options.road ? { road: options.road } : {}),
      },
    },
    T,
  );
  if (options.nowIso) store.tick(options.nowIso);

  const value = testHmiContext({ store, freshness: CONFIG });
  const wrap = (children: ReactNode) => (
    <HmiContext.Provider value={value}>{children}</HmiContext.Provider>
  );

  return renderToString(wrap(<SafetyEnvironment vehicleId={options.vehicleId ?? null} />));
}

// ---------------------------------------------------------------------------
// 1, 2, 3, 4 — render, selection, speeds
// ---------------------------------------------------------------------------

describe("S3 renders (1, 2, 3, 4)", () => {
  it("1 — renders the safety/environment screen", () => {
    const html = render();
    expect(html).toContain("Safety / Environment");
    expect(html).toContain("Current operating state");
    expect(html).toContain("Environment");
    expect(html).toContain("Safety envelope");
  });

  it("2 — shows the selected vehicle", () => {
    expect(render()).toContain("TRUCK_01");
  });

  it("3 — shows the current speed when it was supplied", () => {
    // 0.9797 m/s -> 3.5 km/h. A unit conversion, not a derivation.
    expect(render()).toContain("3.5");
  });

  it("4 — an unsupplied speed shows -- and never 0", () => {
    const html = greyscale(render({ vehicles: { TRUCK_01: vehicle({ speedMps: null }) } }));
    expect(html).toContain("--");
    expect(html).not.toContain(">0.0<");
    expect(html).not.toContain(">3.5<");
  });

  it("says so plainly when no vehicle was supplied at all", () => {
    expect(render({ vehicles: {} })).toContain("NO VEHICLE SUPPLIED");
  });
});

// ---------------------------------------------------------------------------
// 5, 6 — environment
// ---------------------------------------------------------------------------

describe("environment (5, 6)", () => {
  it("5 — displays supplied environment fields", () => {
    const html = render({
      vehicles: { TRUCK_01: vehicle({ routeId: "S-1" }) },
      road: { "S-1": roadState() },
    });
    expect(html).toContain("15.0"); // visibility, m
    expect(html).toContain("0.3"); // friction
    expect(html).toContain("WET");
    expect(html).toContain("S-1");
  });

  it("6 — absent environment stays unavailable, not borrowed from a simulator scenario", () => {
    const html = greyscale(render()); // no RoadState — the current live condition
    expect(html).toContain("Visibility");
    expect(html).toContain("--");
    expect(html).toContain("No RoadState has been supplied");
    expect(html).not.toContain("DENSE_FOG");
  });

  it("6b — every environment field reports unavailable without a road", () => {
    for (const row of environmentReadouts(undefined)) {
      expect(row.available, row.label).toBe(false);
      expect(row.value, row.label).toBe("--");
    }
  });
});

// ---------------------------------------------------------------------------
// 7, 8, 9 — provenance
// ---------------------------------------------------------------------------

describe("provenance (7, 8, 9)", () => {
  it("7 — displays the telemetry provenance", () => {
    const html = render();
    expect(html).toContain("Telemetry source");
    expect(html).toContain("SIMULATION");
  });

  it("8 — simulated telemetry is labelled SIMULATION, from the supplied origin", () => {
    expect(provenanceLabel(vehicle())).toBe("SIMULATION");
  });

  it("9 — simulated data makes no physical claim anywhere on the screen", () => {
    const html = greyscale(render());
    expect(html).not.toContain("PHYSICAL");
    expect(html).not.toContain("HARDWARE");
    expect(isPhysical(vehicle())).toBe(false);
  });

  it("9b — a hardware-origin speed is physical, and says when it was derived", () => {
    const hardware = vehicle({
      provenance: {
        speed_mps: { ...SIMULATED_PROVENANCE.speed_mps, source: "DERIVED", origin: "HARDWARE" },
      },
    });
    expect(provenanceLabel(hardware)).toBe("PHYSICAL (derived)");
    expect(isPhysical(hardware)).toBe(true);
  });

  it("9c — missing provenance is unavailable, never assumed to be simulation", () => {
    // Omitted, not set to undefined — `exactOptionalPropertyTypes` distinguishes them,
    // and a Twin projection without provenance omits the key.
    const { provenance: _omitted, ...withoutProvenance } = vehicle();
    expect(provenanceLabel(withoutProvenance)).toBe("--");
    expect(isPhysical(withoutProvenance)).toBe(false);
    expect(isPhysical(undefined)).toBe(false);
  });
});

// ---------------------------------------------------------------------------
// 10, 11 — freshness
// ---------------------------------------------------------------------------

describe("freshness (10, 11)", () => {
  it("10 — displays telemetry freshness", () => {
    const html = render();
    expect(html).toContain("Telemetry freshness");
    expect(html).toContain("CURRENT");
  });

  it("11 — stale telemetry is represented as STALE, and the value is not blanked", () => {
    const html = greyscale(render({ nowIso: "2026-01-01T00:00:30.000Z" }));
    expect(html).toContain("STALE");
    expect(html).toContain("3.5"); // last known speed still shown, honestly aged
  });
});

// ---------------------------------------------------------------------------
// 12-17 — the honesty rules
// ---------------------------------------------------------------------------

describe("safety values appear only when supplied (12, 13)", () => {
  it("12 — v_safe appears when the safety layer supplied it", () => {
    const html = render({ safety: { TRUCK_01: safetyState({ vSafe: 10 }) } });
    expect(html).toContain("v_safe");
    expect(html).toContain("36.0"); // 10 m/s -> 36 km/h
    expect(html).toContain("Safe speed");
  });

  it("13 — a missing v_safe is unavailable, never zero", () => {
    const html = greyscale(render()); // no SafetyState — the current live condition
    expect(html).toContain("DETAILED LIMITS UNAVAILABLE");
    expect(html).toContain("does not expose safety solver output");
    expect(html).not.toContain(">0.0<");
    expect(html).not.toContain(">36.0<");
  });
});

describe("nothing is computed in the HMI (14, 15, 16, 17)", () => {
  it("14 — no v_safe is derived from the current speed", () => {
    // Speed is supplied; v_safe is not. Nothing may manufacture one.
    const view = envelopeView(undefined);
    expect(view.anyAvailable).toBe(false);
    for (const row of view.readouts) expect(row.value).toBe("--");

    const safe = operatingReadouts(vehicle(), undefined, null).find(
      (r) => r.label === "Safe speed",
    );
    expect(safe?.available).toBe(false);
    expect(safe?.value).toBe("--");
  });

  it("14b — the screen contains no safety arithmetic", async () => {
    const source = await screenSource();
    expect(source).not.toContain("Math.min");
    expect(source).not.toContain("Math.sqrt");
  });

  it("15 — stopping distance is never computed here", () => {
    expect(stoppingDistanceText()).toBe("--");
    const html = render();
    expect(html).toContain("Stopping distance");
    expect(html).toContain("never recomputed in the HMI");
  });

  it("16 — no limiter is inferred, and absent limiters are not listed as empty rows", () => {
    const html = render();
    for (const limiter of ["v_stop", "v_retarder", "v_traction", "v_curve", "v_mine"]) {
      expect(html, limiter + " was rendered").not.toContain(limiter);
    }
  });

  it("17 — no safety state or constraint is inferred from a threshold", () => {
    expect(safetyStateText(undefined)).toBe("--");
    expect(activeConstraintText(undefined)).toBe("--");
    const html = render();
    expect(html).toContain("SAFETY REASON UNAVAILABLE");
    expect(html).toContain("never inferred");
  });

  it("17b — a supplied constraint and risk level are shown verbatim", () => {
    const html = render({
      safety: { TRUCK_01: safetyState({ activeConstraint: "VISIBILITY", riskLevel: "HIGH" }) },
    });
    expect(html).toContain("VISIBILITY");
    expect(html).toContain("HIGH");
  });

  it("17c — an UNKNOWN constraint is unavailable, not presented as a cause", () => {
    expect(activeConstraintText(safetyState({ activeConstraint: "UNKNOWN" }))).toBe("--");
  });
});

// ---------------------------------------------------------------------------
// 18, 19, 20 — architecture
// ---------------------------------------------------------------------------

describe("architecture (18, 19, 20)", () => {
  it("18 — the vehicle selector is driven by the shared vehicle state", () => {
    const html = render({
      vehicles: { TRUCK_01: vehicle(), TRUCK_02: vehicle({ vehicleId: "TRUCK_02" }) },
    });
    expect(html).toContain("Select vehicle");
    expect(html).toContain("TRUCK_01");
    expect(html).toContain("TRUCK_02");
  });

  it("18b — honours the vehicle the shell already selected", () => {
    const html = render({
      vehicles: { TRUCK_01: vehicle(), TRUCK_02: vehicle({ vehicleId: "TRUCK_02" }) },
      vehicleId: "TRUCK_02",
    });
    expect(html).toContain("TRUCK_02");
  });

  it("19 — S3 adds no API transport of its own", async () => {
    const source = await screenSource();
    expect(source).not.toContain("fetch(");
    expect(source).not.toContain("WebSocket");
    expect(source).not.toContain("setInterval");
  });

  it("20 — the shared store is read, never duplicated", async () => {
    const source = await screenSource();
    expect(source).toContain("useAppState");
    // The only local state is the selected-vehicle id: one import, one call.
    expect((source.match(/useState/g) ?? []).length).toBe(2);
  });
});
