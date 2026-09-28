/**
 * Patch assembly and merge tests — M3.
 * Covers required tests 24 (patch merge), 25 (explicit deletion), 26 (missing key).
 */

import { describe, expect, it } from "vitest";
import type { VehicleState } from "../contracts/domain";
import type { ProviderPatch } from "../providers/DataProvider";
import { buildPatch, emptyAppState, mergePatch } from "./patch";

const NOW = "2026-01-01T00:00:00.000Z";

function vehicle(id: string, speed: number): VehicleState {
  return {
    vehicleId: id,
    timestamp: NOW,
    position: { x: null, y: null, segmentId: "S-1", offsetM: null },
    speedMps: speed,
    accelMps2: 0,
    gradeRad: 0,
    frictionEst: { value: 0.6, sigma: 0.04 },
    mode: "NORMAL",
    commConfidence: 1,
    vehicleKind: "TRUCK",
    routeId: null,
  };
}

const base = () => emptyAppState(NOW);

describe("buildPatch", () => {
  it("indexes keyed collections by their id", () => {
    const patch = buildPatch({ vehicles: [vehicle("V-1", 5), vehicle("V-2", 6)] });
    expect(Object.keys(patch.vehicles ?? {})).toEqual(["V-1", "V-2"]);
  });

  it("omits slices that are absent from the batch", () => {
    const patch = buildPatch({ vehicles: [vehicle("V-1", 5)] });
    expect(patch).not.toHaveProperty("safety");
    expect(patch).not.toHaveProperty("alerts");
  });

  it("an empty batch produces an empty patch, not empty collections", () => {
    // An empty collection would read as "everything was removed" — it must not appear.
    expect(buildPatch({})).toEqual({});
  });
});

describe("NO CHANGE — missing key (test 26)", () => {
  it("leaves an untouched slice exactly as it was", () => {
    const start = mergePatch(base(), { changes: { vehicles: { "V-1": vehicle("V-1", 5) } } });
    const next = mergePatch(start, { changes: { kpis: null } });
    expect(next.vehicles["V-1"]).toBeDefined();
    expect(next.vehicles["V-1"]?.speedMps).toBe(5);
  });

  it("an entity absent from a patch is NOT deleted", () => {
    const start = mergePatch(base(), {
      changes: { vehicles: { "V-1": vehicle("V-1", 5), "V-2": vehicle("V-2", 6) } },
    });
    // Patch mentions only V-1. V-2 must survive.
    const next = mergePatch(start, { changes: { vehicles: { "V-1": vehicle("V-1", 9) } } });
    expect(next.vehicles["V-2"]).toBeDefined();
    expect(next.vehicles["V-1"]?.speedMps).toBe(9);
  });

  it("an empty changes object changes nothing", () => {
    const start = mergePatch(base(), { changes: { vehicles: { "V-1": vehicle("V-1", 5) } } });
    expect(mergePatch(start, { changes: {} })).toEqual(start);
  });
});

describe("UPSERT (test 24)", () => {
  it("adds a new entity", () => {
    const next = mergePatch(base(), { changes: { vehicles: { "V-1": vehicle("V-1", 5) } } });
    expect(next.vehicles["V-1"]?.speedMps).toBe(5);
  });

  it("replaces an existing entity", () => {
    const start = mergePatch(base(), { changes: { vehicles: { "V-1": vehicle("V-1", 5) } } });
    const next = mergePatch(start, { changes: { vehicles: { "V-1": vehicle("V-1", 12) } } });
    expect(next.vehicles["V-1"]?.speedMps).toBe(12);
    expect(Object.keys(next.vehicles)).toHaveLength(1);
  });

  it("does not mutate the input state", () => {
    const start = base();
    mergePatch(start, { changes: { vehicles: { "V-1": vehicle("V-1", 5) } } });
    expect(Object.keys(start.vehicles)).toHaveLength(0);
  });

  it("replaces collection-valued slices whole", () => {
    const start = mergePatch(base(), {
      changes: {
        alerts: [
          {
            alertId: "A-1",
            timestamp: NOW,
            severity: "INFO",
            category: "STALE_DATA",
            origin: "HMI",
            subject: { kind: "SYSTEM", id: "SYS" },
            message: "one",
            reasonCode: null,
            acknowledgeable: true,
            acknowledged: null,
            active: true,
          },
        ],
      },
    });
    const next = mergePatch(start, { changes: { alerts: [] } });
    expect(next.alerts).toHaveLength(0);
  });

  it("applies an explicit null to a singleton slice", () => {
    const next = mergePatch(base(), { changes: { kpis: null } });
    expect(next.kpis).toBeNull();
  });
});

describe("DELETE — explicit deletions (test 25)", () => {
  it("removes only the ids listed", () => {
    const start = mergePatch(base(), {
      changes: {
        vehicles: {
          "V-1": vehicle("V-1", 5),
          "V-2": vehicle("V-2", 6),
          "V-3": vehicle("V-3", 7),
        },
      },
    });
    const next = mergePatch(start, { changes: {}, deletions: { vehicles: ["V-2"] } });
    expect(Object.keys(next.vehicles).sort()).toEqual(["V-1", "V-3"]);
  });

  it("deleting an unknown id is a no-op, not an error", () => {
    const start = mergePatch(base(), { changes: { vehicles: { "V-1": vehicle("V-1", 5) } } });
    const next = mergePatch(start, { changes: {}, deletions: { vehicles: ["V-99"] } });
    expect(Object.keys(next.vehicles)).toEqual(["V-1"]);
  });

  it("an empty deletions list removes nothing", () => {
    const start = mergePatch(base(), { changes: { vehicles: { "V-1": vehicle("V-1", 5) } } });
    const next = mergePatch(start, { changes: {}, deletions: { vehicles: [] } });
    expect(Object.keys(next.vehicles)).toEqual(["V-1"]);
  });

  it("deletes across several slices independently", () => {
    const start = mergePatch(base(), {
      changes: {
        vehicles: { "V-1": vehicle("V-1", 5) },
        safety: {
          "V-1": {
            vehicleId: "V-1",
            timestamp: NOW,
            vSafe: 10,
            hSafe: 40,
            actualSpeed: 5,
            headwayCurrent: null,
            leadVehicleId: null,
            activeConstraint: "NONE",
            riskLevel: "LOW",
            headwayViolation: null,
            envelopeViolation: null,
          },
        },
      },
    });
    const next = mergePatch(start, { changes: {}, deletions: { safety: ["V-1"] } });
    expect(next.vehicles["V-1"]).toBeDefined();
    expect(next.safety["V-1"]).toBeUndefined();
  });
});

describe("merge order — deletions first, then changes", () => {
  it("an entity both deleted and changed survives (re-add, not a race)", () => {
    const start = mergePatch(base(), { changes: { vehicles: { "V-1": vehicle("V-1", 5) } } });
    const patch: ProviderPatch = {
      changes: { vehicles: { "V-1": vehicle("V-1", 42) } },
      deletions: { vehicles: ["V-1"] },
    };
    const next = mergePatch(start, patch);
    expect(next.vehicles["V-1"]).toBeDefined();
    expect(next.vehicles["V-1"]?.speedMps).toBe(42);
  });

  it("the outcome does not depend on key order in the patch object", () => {
    const start = mergePatch(base(), {
      changes: { vehicles: { "V-1": vehicle("V-1", 1), "V-2": vehicle("V-2", 2) } },
    });
    const a = mergePatch(start, {
      changes: { vehicles: { "V-2": vehicle("V-2", 20) } },
      deletions: { vehicles: ["V-1"] },
    });
    const b = mergePatch(start, {
      deletions: { vehicles: ["V-1"] },
      changes: { vehicles: { "V-2": vehicle("V-2", 20) } },
    });
    expect(a).toEqual(b);
  });
});
