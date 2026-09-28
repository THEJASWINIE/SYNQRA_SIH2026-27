/**
 * Freshness overview tests — M10. NFR-003, M10D-A.
 *
 * The load-bearing assertions are the ones about NOT classifying: with no configured
 * threshold the overview reports ages and refuses to tally quality, because "not
 * evaluated" and "all current" are different statements (AMB-014, M8D-B).
 */

import { describe, expect, it } from "vitest";
import { freshnessConfig } from "../config/freshness";
import type { AppState } from "../contracts/appState";
import type { Alert, VehicleState } from "../contracts/domain";
import { emptyAppState } from "../data/patch";
import { freshnessOverview, populatedRows } from "./diagnostics";

const T0 = "2026-01-01T00:00:00.000Z";
const NOW = Date.parse("2026-01-01T00:00:10.000Z");
const CONFIG = freshnessConfig(5000);

function vehicle(id: string, timestamp: string): VehicleState {
  return {
    vehicleId: id,
    timestamp,
    position: { x: null, y: null, segmentId: "S-1", offsetM: 5 },
    speedMps: 8,
    accelMps2: 0,
    gradeRad: 0,
    frictionEst: { value: 0.6, sigma: null },
    mode: "NORMAL",
    commConfidence: 1,
    vehicleKind: "TRUCK",
    routeId: null,
  };
}

function alert(id: string, timestamp: string): Alert {
  return {
    alertId: id,
    timestamp,
    severity: "WARNING",
    category: "UNSAFE_SPEED",
    origin: "TASK2",
    subject: { kind: "VEHICLE", id: "V-1" },
    message: "supplied",
    reasonCode: null,
    acknowledgeable: true,
    acknowledged: null,
    active: true,
  };
}

function state(partial: Partial<AppState> = {}): AppState {
  return { ...emptyAppState(T0), ...partial };
}

const row = (overview: ReturnType<typeof freshnessOverview>, type: string) =>
  overview.rows.find((r) => r.messageType === type);

// ---------------------------------------------------------------------------

describe("coverage of message types", () => {
  it("reports a row for every contract message type carried in AppState", () => {
    const overview = freshnessOverview(state(), CONFIG, NOW);
    for (const type of [
      "VehicleState",
      "SafetyState",
      "RoadState",
      "VisibilityForecast",
      "BottleneckState",
      "ArrivalPlan",
      "SlotState",
      "DispatchCommand",
      "Alert",
      "EventRecord",
      "SystemHealth",
      "KpiSnapshot",
      "CVResult",
      "MineTopology",
    ]) {
      expect(row(overview, type), `missing row: ${type}`).toBeDefined();
    }
  });

  it("is deterministically ordered", () => {
    const a = freshnessOverview(state(), CONFIG, NOW).rows.map((r) => r.messageType);
    const b = freshnessOverview(state(), CONFIG, NOW).rows.map((r) => r.messageType);
    expect(a).toEqual(b);
  });

  it("an empty state reports zero held everywhere, not unknown", () => {
    const overview = freshnessOverview(state(), CONFIG, NOW);
    expect(overview.totalEntities).toBe(0);
    expect(overview.rows.every((r) => r.count === 0)).toBe(true);
  });

  it("counts entities held per type", () => {
    const overview = freshnessOverview(
      state({ vehicles: { "V-1": vehicle("V-1", T0), "V-2": vehicle("V-2", T0) } }),
      CONFIG,
      NOW,
    );
    expect(row(overview, "VehicleState")?.count).toBe(2);
    expect(overview.totalEntities).toBe(2);
  });

  it("populatedRows returns only types actually carrying entities", () => {
    const overview = freshnessOverview(
      state({ vehicles: { "V-1": vehicle("V-1", T0) } }),
      CONFIG,
      NOW,
    );
    expect(populatedRows(overview).map((r) => r.messageType)).toEqual(["VehicleState"]);
  });
});

describe("quality tallies with a configured threshold", () => {
  it("counts a recent datum as OK", () => {
    const overview = freshnessOverview(
      state({ vehicles: { "V-1": vehicle("V-1", "2026-01-01T00:00:08.000Z") } }),
      CONFIG,
      NOW,
    );
    expect(row(overview, "VehicleState")?.qualities).toMatchObject({ OK: 1, STALE: 0 });
  });

  it("counts an aged datum as STALE", () => {
    const overview = freshnessOverview(
      state({ vehicles: { "V-1": vehicle("V-1", T0) } }),
      CONFIG,
      NOW,
    );
    expect(row(overview, "VehicleState")?.qualities).toMatchObject({ OK: 0, STALE: 1 });
  });

  it("counts a malformed timestamp as INVALID, never STALE", () => {
    const overview = freshnessOverview(
      state({ vehicles: { "V-1": vehicle("V-1", "not-a-timestamp") } }),
      CONFIG,
      NOW,
    );
    const qualities = row(overview, "VehicleState")?.qualities;
    expect(qualities).toMatchObject({ INVALID: 1, STALE: 0 });
  });

  it("counts an empty timestamp as MISSING, never INVALID", () => {
    const overview = freshnessOverview(
      state({ vehicles: { "V-1": vehicle("V-1", "") } }),
      CONFIG,
      NOW,
    );
    expect(row(overview, "VehicleState")?.qualities).toMatchObject({ MISSING: 1, INVALID: 0 });
  });

  it("mixes qualities within one type", () => {
    const overview = freshnessOverview(
      state({
        vehicles: {
          "V-1": vehicle("V-1", T0),
          "V-2": vehicle("V-2", "2026-01-01T00:00:09.000Z"),
          "V-3": vehicle("V-3", "bad"),
        },
      }),
      CONFIG,
      NOW,
    );
    expect(row(overview, "VehicleState")?.qualities).toMatchObject({
      OK: 1,
      STALE: 1,
      INVALID: 1,
    });
  });

  it("reports the oldest age across the type", () => {
    const overview = freshnessOverview(
      state({
        vehicles: {
          "V-1": vehicle("V-1", "2026-01-01T00:00:09.000Z"),
          "V-2": vehicle("V-2", T0),
        },
      }),
      CONFIG,
      NOW,
    );
    expect(row(overview, "VehicleState")?.oldestAgeMs).toBe(10_000);
  });

  it("age increases as the clock advances, with no new data", () => {
    const held = state({ vehicles: { "V-1": vehicle("V-1", T0) } });
    const early = freshnessOverview(held, CONFIG, NOW).rows;
    const later = freshnessOverview(held, CONFIG, NOW + 30_000).rows;
    const earlyAge = early.find((r) => r.messageType === "VehicleState")?.oldestAgeMs ?? 0;
    const laterAge = later.find((r) => r.messageType === "VehicleState")?.oldestAgeMs ?? 0;
    expect(laterAge).toBeGreaterThan(earlyAge);
  });

  it("covers alerts and system health as their own types", () => {
    const overview = freshnessOverview(
      state({
        alerts: [alert("A-1", T0)],
        health: {
          timestamp: T0,
          systemMode: "NORMAL",
          connectivity: "CONNECTED",
          fleetCount: 1,
          components: [],
        },
      }),
      CONFIG,
      NOW,
    );
    expect(row(overview, "Alert")?.count).toBe(1);
    expect(row(overview, "SystemHealth")?.count).toBe(1);
  });
});

describe("AMB-014 — no configured threshold means NOT EVALUATED", () => {
  const held = state({ vehicles: { "V-1": vehicle("V-1", T0) } });

  it("reports qualities as null rather than tallying", () => {
    const overview = freshnessOverview(held, null, NOW);
    expect(row(overview, "VehicleState")?.qualities).toBeNull();
    expect(overview.thresholdConfigured).toBe(false);
  });

  it("still reports the age", () => {
    expect(row(freshnessOverview(held, null, NOW), "VehicleState")?.oldestAgeMs).toBe(10_000);
  });

  it("does not silently count an aged datum as OK", () => {
    const overview = freshnessOverview(held, null, NOW + 86_400_000);
    expect(row(overview, "VehicleState")?.qualities).toBeNull();
  });

  it("empty rows are also unevaluated, not reported as clean", () => {
    const overview = freshnessOverview(state(), null, NOW);
    expect(overview.rows.every((r) => r.qualities === null)).toBe(true);
  });

  it("reports thresholdConfigured true when one is supplied", () => {
    expect(freshnessOverview(held, CONFIG, NOW).thresholdConfigured).toBe(true);
  });
});

describe("scope — the overview computes nothing operational", () => {
  it("does not mutate the state it reads", () => {
    const held = state({ vehicles: { "V-1": vehicle("V-1", T0) } });
    const before = JSON.parse(JSON.stringify(held));
    freshnessOverview(held, CONFIG, NOW);
    expect(JSON.parse(JSON.stringify(held))).toEqual(before);
  });

  it("is deterministic for identical inputs", () => {
    const held = state({ vehicles: { "V-1": vehicle("V-1", T0) } });
    expect(freshnessOverview(held, CONFIG, NOW)).toEqual(freshnessOverview(held, CONFIG, NOW));
  });

  it("reports only counts, ages and qualities — no operational field", () => {
    const overview = freshnessOverview(
      state({ vehicles: { "V-1": vehicle("V-1", T0) } }),
      CONFIG,
      NOW,
    );
    const keys = Object.keys(row(overview, "VehicleState") ?? {}).sort();
    expect(keys).toEqual(["count", "messageType", "oldest", "oldestAgeMs", "qualities"]);
  });
});
