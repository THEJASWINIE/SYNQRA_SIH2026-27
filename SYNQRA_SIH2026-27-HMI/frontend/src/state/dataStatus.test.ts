/**
 * Unified data-state semantics tests — Phase 8.
 *
 * Pure logic. No DOM, no jsdom, no Testing Library (M4D-C).
 *
 * THE CENTRAL ASSERTION OF THIS FILE: four data states that never collapse into each
 * other, and three neighbouring vocabularies — service health, provenance and the command
 * lifecycle — that are never converted into a data state. Most of the danger in this HMI
 * lives in the pairs that LOOK interchangeable: UNAVAILABLE and 0, STALE and UNAVAILABLE,
 * CONNECTED and PHYSICAL, ERROR and UNAVAILABLE.
 */

import { describe, expect, it } from "vitest";
import type { TwinFieldProvenance, VehicleState } from "../contracts/domain";
import {
  communicationState,
  communicationText,
  DATA_STATE_TEXT,
  fieldDataState,
  formatAvailability,
  isPhysical,
  isStale,
  provenanceLabel,
  serviceState,
  UNAVAILABLE_LABEL,
  UNAVAILABLE_VALUE,
  vehicleProvenanceLabel,
  viewDataState,
} from "./dataStatus";
import type { FreshnessView } from "./freshness";
import { OBSERVABILITY_STATUS_TEXT } from "./systemHealth";

const T = "2026-01-01T00:00:00.000Z";

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

function vehicle(provenance?: Record<string, TwinFieldProvenance>): VehicleState {
  const base: VehicleState = {
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
  };
  return provenance ? { ...base, provenance } : base;
}

function view(partial: Partial<FreshnessView> = {}): FreshnessView {
  return { timestamp: T, ageMs: 100, quality: "OK", thresholdConfigured: true, ...partial };
}

// ---------------------------------------------------------------------------
// 1, 2, 3, 4 — the four states stay distinct
// ---------------------------------------------------------------------------

describe("the four data states (1, 2, 3, 4)", () => {
  it("1 — CURRENT remains CURRENT, from either freshness source", () => {
    expect(viewDataState(view({ quality: "OK" }))).toBe("CURRENT");
    expect(fieldDataState(field({ freshness: "CURRENT" }))).toBe("CURRENT");
    expect(DATA_STATE_TEXT.CURRENT).toBe("CURRENT");
  });

  it("2 — STALE remains STALE, and is never softened to CURRENT", () => {
    expect(viewDataState(view({ quality: "STALE" }))).toBe("STALE");
    expect(fieldDataState(field({ freshness: "STALE" }))).toBe("STALE");
    expect(isStale("STALE")).toBe(true);
    expect(isStale("CURRENT")).toBe(false);
  });

  it("3 — UNKNOWN remains UNKNOWN, and is never reported as fresh", () => {
    // An unparseable timestamp arrived: an integration fault, not an absent field.
    expect(viewDataState(view({ quality: "INVALID" }))).toBe("UNKNOWN");
    // No configured threshold (AMB-014): not evaluated, so not classifiable.
    expect(viewDataState(view({ quality: null, thresholdConfigured: false }))).toBe("UNKNOWN");
    // A verdict the HMI does not recognise is never assumed good.
    expect(fieldDataState(field({ freshness: "NOT_EVALUATED" }))).toBe("UNKNOWN");
  });

  it("4 — UNAVAILABLE remains UNAVAILABLE and is distinct from every other state", () => {
    expect(viewDataState(view({ quality: "MISSING" }))).toBe("UNAVAILABLE");
    expect(fieldDataState(undefined)).toBe("UNAVAILABLE");
    expect(fieldDataState(field({ available: false }))).toBe("UNAVAILABLE");
  });

  it("4b — no two states share a rendering", () => {
    const texts = Object.values(DATA_STATE_TEXT);
    expect(new Set(texts).size).toBe(texts.length);
    expect(texts.length).toBe(4);
  });
});

// ---------------------------------------------------------------------------
// 5, 6, 7 — zero versus absent
// ---------------------------------------------------------------------------

describe("zero is a measurement (5, 6, 7)", () => {
  it("5 — a supplied 0 renders as 0, never as unavailable", () => {
    expect(formatAvailability(0)).toBe("0.0");
    expect(formatAvailability(0, 0)).toBe("0");
    expect(formatAvailability(0)).not.toBe(UNAVAILABLE_VALUE);
  });

  it("6 — null renders as unavailable, never as 0", () => {
    expect(formatAvailability(null)).toBe(UNAVAILABLE_VALUE);
    expect(formatAvailability(null)).not.toBe("0.0");
  });

  it("7 — a missing or unusable field renders as unavailable", () => {
    expect(formatAvailability(undefined)).toBe(UNAVAILABLE_VALUE);
    expect(formatAvailability(Number.NaN)).toBe(UNAVAILABLE_VALUE);
    expect(formatAvailability(Number.POSITIVE_INFINITY)).toBe(UNAVAILABLE_VALUE);
  });

  it("7b — the two unavailable renderings differ only by slot, never by meaning", () => {
    expect(UNAVAILABLE_VALUE).toBe("--");
    expect(UNAVAILABLE_LABEL).toBe("UNAVAILABLE");
    expect(DATA_STATE_TEXT.UNAVAILABLE).toBe(UNAVAILABLE_LABEL);
  });
});

// ---------------------------------------------------------------------------
// 8, 9, 10 — provenance
// ---------------------------------------------------------------------------

describe("provenance (8, 9, 10)", () => {
  it("8 — SIMULATION remains SIMULATION and is never relabelled LIVE or REAL", () => {
    const label = provenanceLabel(field({ source: "SIMULATION", origin: "SIMULATION" }));
    expect(label).toBe("SIMULATION");
    expect(label).not.toContain("LIVE");
    expect(label).not.toContain("REAL");
    expect(label).not.toContain("PHYSICAL");
  });

  it("9 — PHYSICAL is shown only for hardware origin", () => {
    expect(provenanceLabel(field({ source: "MEASURED", origin: "HARDWARE" }))).toBe("PHYSICAL");
    expect(isPhysical(vehicle({ speed_mps: field({ origin: "HARDWARE" }) }))).toBe(true);
    expect(isPhysical(vehicle({ speed_mps: field({ origin: "SIMULATION" }) }))).toBe(false);
    expect(isPhysical(vehicle())).toBe(false);
    expect(isPhysical(undefined)).toBe(false);
  });

  it("10 — DERIVED from hardware is physical, and says it was derived", () => {
    expect(provenanceLabel(field({ source: "DERIVED", origin: "HARDWARE" }))).toBe(
      "PHYSICAL (derived)",
    );
    // Distinct from a directly measured value — the distinction is the point.
    expect(provenanceLabel(field({ source: "DERIVED", origin: "HARDWARE" }))).not.toBe("PHYSICAL");
  });

  it("10b — an unsupplied provenance is unavailable, never assumed to be either", () => {
    expect(provenanceLabel(undefined)).toBe(UNAVAILABLE_VALUE);
    expect(vehicleProvenanceLabel(vehicle())).toBe(UNAVAILABLE_VALUE);
    expect(vehicleProvenanceLabel(undefined)).toBe(UNAVAILABLE_VALUE);
  });

  it("10c — an unrecognised origin is reported verbatim, not forced into a bucket", () => {
    expect(provenanceLabel(field({ source: "CONFIGURED", origin: "UNKNOWN" }))).toBe(
      "CONFIGURED · UNKNOWN",
    );
  });
});

// ---------------------------------------------------------------------------
// 11, 12 — service health is a separate domain
// ---------------------------------------------------------------------------

describe("service health versus data state (11, 12)", () => {
  it("11 — ONLINE service with STALE data is a valid, representable pair", () => {
    expect(serviceState(true)).toBe("ONLINE");
    expect(fieldDataState(field({ freshness: "STALE" }))).toBe("STALE");
  });

  it("12 — ONLINE service with an UNAVAILABLE field is also valid", () => {
    expect(serviceState(true)).toBe("ONLINE");
    expect(fieldDataState(undefined)).toBe("UNAVAILABLE");
  });

  it("11b — service state comes from the probe, never from data freshness", () => {
    expect(serviceState(false)).toBe("OFFLINE");
    expect(serviceState(null)).toBe("UNKNOWN");
    expect(serviceState(undefined)).toBe("UNKNOWN");
  });

  it("11c — stale data does not make the service OFFLINE", () => {
    // The only input to `serviceState` is the probe; there is deliberately no data path in.
    expect(serviceState(true)).toBe("ONLINE");
    expect(isStale(fieldDataState(field({ freshness: "STALE" })))).toBe(true);
  });
});

// ---------------------------------------------------------------------------
// 13, 14 — the command lifecycle is a separate domain
// ---------------------------------------------------------------------------

describe("command lifecycle versus data state (13, 14)", () => {
  const COMMAND_STATES = [
    "PENDING",
    "ISSUED",
    "ACCEPTED",
    "REJECTED",
    "UNKNOWN_VEHICLE",
    "DUPLICATE",
    "INVALID",
    "UNSAFE",
    "TIMEOUT",
    "NOT_EXECUTED",
    "NETWORK_ERROR",
  ];

  it("13 — ACCEPTED is not a data state and is never treated as CURRENT", () => {
    expect(Object.keys(DATA_STATE_TEXT)).not.toContain("ACCEPTED");
    expect(DATA_STATE_TEXT.CURRENT).not.toBe("ACCEPTED");
  });

  it("14 — REJECTED is not a data state and is never treated as STALE", () => {
    expect(Object.keys(DATA_STATE_TEXT)).not.toContain("REJECTED");
    expect(DATA_STATE_TEXT.STALE).not.toBe("REJECTED");
  });

  it("13b — no command state collides with a data state", () => {
    for (const command of COMMAND_STATES) {
      expect(Object.keys(DATA_STATE_TEXT), command).not.toContain(command);
    }
  });

  it("13c — an ACCEPTED command beside STALE telemetry is not a contradiction", () => {
    // Both facts hold at once; nothing in this module reconciles or overrides either.
    expect(fieldDataState(field({ freshness: "STALE" }))).toBe("STALE");
    expect(COMMAND_STATES).toContain("ACCEPTED");
  });
});

// ---------------------------------------------------------------------------
// 15, 16 — observability keeps its own lifecycle
// ---------------------------------------------------------------------------

describe("observability lifecycle (15, 16)", () => {
  it("15 — ERROR remains ERROR, no longer collapsed into UNAVAILABLE", () => {
    expect(OBSERVABILITY_STATUS_TEXT.ERROR).toBe("ERROR");
    expect(OBSERVABILITY_STATUS_TEXT.ERROR).not.toBe(UNAVAILABLE_LABEL);
  });

  it("16 — STALE observability is distinct from ERROR and from IDLE", () => {
    expect(OBSERVABILITY_STATUS_TEXT.STALE).toBe("STALE");
    expect(OBSERVABILITY_STATUS_TEXT.IDLE).toBe("NOT YET QUERIED");
    const values = Object.values(OBSERVABILITY_STATUS_TEXT);
    expect(new Set(values).size).toBe(values.length);
  });

  it("16b — the observability lifecycle keeps all four of its own states", () => {
    expect(Object.keys(OBSERVABILITY_STATUS_TEXT).sort()).toEqual([
      "CURRENT",
      "ERROR",
      "IDLE",
      "STALE",
    ]);
  });
});

// ---------------------------------------------------------------------------
// 17, 18, 19, 20 — independence of the vocabularies
// ---------------------------------------------------------------------------

describe("the vocabularies stay independent (17, 18, 19, 20)", () => {
  it("17 — provenance does not change with freshness", () => {
    const fresh = field({ origin: "SIMULATION", freshness: "CURRENT" });
    const stale = field({ origin: "SIMULATION", freshness: "STALE" });
    expect(provenanceLabel(fresh)).toBe(provenanceLabel(stale));
    expect(fieldDataState(fresh)).not.toBe(fieldDataState(stale));
  });

  it("17b — freshness does not change with provenance", () => {
    const simulated = field({ origin: "SIMULATION", freshness: "CURRENT" });
    const physical = field({ origin: "HARDWARE", freshness: "CURRENT" });
    expect(fieldDataState(simulated)).toBe(fieldDataState(physical));
    expect(provenanceLabel(simulated)).not.toBe(provenanceLabel(physical));
  });

  it("18 — communication health is independent of telemetry freshness", () => {
    const degraded = vehicle({
      speed_mps: field({ freshness: "CURRENT" }),
      communication_state: field({ value: "COMMUNICATION_DEGRADED" }),
    });
    // Fresh telemetry, degraded link — both true at once, and both reported.
    expect(fieldDataState(degraded.provenance?.speed_mps)).toBe("CURRENT");
    expect(communicationState(degraded)).toBe("COMMUNICATION_DEGRADED");
  });

  it("18b — communication is never inferred from the existence of a vehicle", () => {
    // The pre-Phase-8 operator view printed CONNECTED whenever a vehicle object existed.
    expect(communicationState(vehicle())).toBeNull();
    expect(communicationText(vehicle())).toBe("UNKNOWN");
    expect(communicationText(vehicle())).not.toBe("CONNECTED");
    expect(communicationText(undefined)).toBe("UNKNOWN");
  });

  it("19 — Twin attachment is not a hardware connection", () => {
    // Attachment is a software fact on the observability snapshot; provenance is the only
    // thing that can say a value is physical, and it is read per field.
    const attachedButSimulated = vehicle({ speed_mps: field({ origin: "SIMULATION" }) });
    expect(isPhysical(attachedButSimulated)).toBe(false);
    expect(vehicleProvenanceLabel(attachedButSimulated)).toBe("SIMULATION");
  });

  it("20 — simulated data is not a hardware failure", () => {
    const simulated = field({ origin: "SIMULATION", freshness: "CURRENT" });
    expect(fieldDataState(simulated)).toBe("CURRENT");
    expect(provenanceLabel(simulated)).toBe("SIMULATION");
    // Being simulated changes neither the data state nor the service state.
    expect(serviceState(true)).toBe("ONLINE");
  });

  it("20b — a connected backend never implies PHYSICAL", () => {
    expect(serviceState(true)).toBe("ONLINE");
    expect(vehicleProvenanceLabel(vehicle({ speed_mps: field() }))).toBe("SIMULATION");
  });
});
