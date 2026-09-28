/**
 * Alert merging and HMI data-path alert tests — M8. FR-014, M8D-A, M8D-B.
 *
 * The load-bearing assertions here are the negative ones: the HMI must never fabricate a
 * producer category, never overwrite a supplied alert, and never raise a STALE_DATA alert
 * while AMB-014 leaves the threshold unconfigured.
 */

import { describe, expect, it } from "vitest";
import { freshnessConfig } from "../config/freshness";
import type { AppState } from "../contracts/appState";
import type { Alert, VehicleState } from "../contracts/domain";
import { emptyAppState } from "../data/patch";
import {
  assessStale,
  COMM_LOSS_ALERT_ID,
  hmiDataPathAlerts,
  isHmiOriginated,
  mergedAlerts,
  STALE_DATA_ALERT_ID,
} from "./alerts";

const T = "2026-01-01T00:00:00.000Z";
const NOW = Date.parse("2026-01-01T00:00:10.000Z");
const CONFIG = freshnessConfig(5000);

function vehicle(id: string, timestamp: string): VehicleState {
  return {
    vehicleId: id,
    timestamp,
    position: { x: null, y: null, segmentId: "S-1", offsetM: 10 },
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

function alert(partial: Partial<Alert> = {}): Alert {
  return {
    alertId: "A-1",
    timestamp: T,
    severity: "WARNING",
    category: "UNSAFE_SPEED",
    origin: "TASK2",
    subject: { kind: "VEHICLE", id: "V-1" },
    message: "supplied alert",
    reasonCode: null,
    acknowledgeable: true,
    acknowledged: null,
    active: true,
    ...partial,
  };
}

function stateWith(partial: Partial<AppState> = {}): AppState {
  return { ...emptyAppState(T), ...partial };
}

function connected(state: AppState, status: AppState["connection"]["status"]): AppState {
  return { ...state, connection: { ...state.connection, status } };
}

// ---------------------------------------------------------------------------

describe("COMM_LOSS — derived from the HMI's own connection status", () => {
  it("is raised when the feed is DISCONNECTED", () => {
    const derived = hmiDataPathAlerts(connected(stateWith(), "DISCONNECTED"), CONFIG, NOW);
    expect(derived).toHaveLength(1);
    expect(derived[0]?.category).toBe("COMM_LOSS");
    expect(derived[0]?.origin).toBe("HMI");
  });

  it("is raised on a provider ERROR", () => {
    const derived = hmiDataPathAlerts(connected(stateWith(), "ERROR"), CONFIG, NOW);
    expect(derived.some((a) => a.category === "COMM_LOSS")).toBe(true);
  });

  it("is NOT raised while the feed is up", () => {
    for (const status of ["IDLE", "CONNECTING", "CONNECTED", "RECONNECTING"] as const) {
      const derived = hmiDataPathAlerts(connected(stateWith(), status), CONFIG, NOW);
      expect(derived.some((a) => a.category === "COMM_LOSS")).toBe(false);
    }
  });

  it("clears when the link comes back", () => {
    const lost = connected(stateWith(), "DISCONNECTED");
    expect(hmiDataPathAlerts(lost, CONFIG, NOW)).toHaveLength(1);
    expect(hmiDataPathAlerts(connected(lost, "CONNECTED"), CONFIG, NOW)).toHaveLength(0);
  });

  it("carries the supplied provider error message when there is one", () => {
    const state = {
      ...connected(stateWith(), "DISCONNECTED"),
      connection: {
        ...stateWith().connection,
        status: "DISCONNECTED" as const,
        error: "V2I link lost",
      },
    };
    expect(hmiDataPathAlerts(state, CONFIG, NOW)[0]?.message).toContain("V2I link lost");
  });

  it("has a fixed severity — nothing computes or escalates it", () => {
    expect(
      hmiDataPathAlerts(connected(stateWith(), "DISCONNECTED"), CONFIG, NOW)[0]?.severity,
    ).toBe("WARNING");
  });

  it("is not acknowledgeable in M8 — no acknowledgement UI exists", () => {
    expect(
      hmiDataPathAlerts(connected(stateWith(), "DISCONNECTED"), CONFIG, NOW)[0]?.acknowledgeable,
    ).toBe(false);
  });
});

// ---------------------------------------------------------------------------

describe("STALE_DATA — gated on the configured threshold (M8D-B)", () => {
  const stale = stateWith({ vehicles: { "V-1": vehicle("V-1", T) } });

  it("is raised when a supplied datum exceeds the configured threshold", () => {
    // Vehicle timestamp is 10 s old; threshold is 5 s.
    const derived = hmiDataPathAlerts(stale, CONFIG, NOW);
    expect(derived.some((a) => a.category === "STALE_DATA")).toBe(true);
  });

  it("is NOT raised when no threshold is configured — AMB-014 unresolved", () => {
    const derived = hmiDataPathAlerts(stale, null, NOW);
    expect(derived.some((a) => a.category === "STALE_DATA")).toBe(false);
  });

  it("is not raised however old the data gets, while the threshold is absent", () => {
    const derived = hmiDataPathAlerts(stale, null, NOW + 86_400_000);
    expect(derived).toHaveLength(0);
  });

  it("is not raised when everything is within the threshold", () => {
    const fresh = stateWith({
      vehicles: { "V-1": vehicle("V-1", "2026-01-01T00:00:09.000Z") },
    });
    expect(hmiDataPathAlerts(fresh, CONFIG, NOW).some((a) => a.category === "STALE_DATA")).toBe(
      false,
    );
  });

  it("names which supplied values aged out", () => {
    const derived = hmiDataPathAlerts(stale, CONFIG, NOW);
    expect(derived.find((a) => a.category === "STALE_DATA")?.message).toContain("vehicle V-1");
  });

  it("has a fixed severity — age does not escalate it", () => {
    const veryOld = stateWith({ vehicles: { "V-1": vehicle("V-1", "2020-01-01T00:00:00.000Z") } });
    expect(
      hmiDataPathAlerts(veryOld, CONFIG, NOW).find((a) => a.category === "STALE_DATA")?.severity,
    ).toBe("WARNING");
  });
});

describe("assessStale", () => {
  it("reports not-evaluated when no threshold is configured", () => {
    const result = assessStale(stateWith(), null, NOW);
    expect(result.staleLabels).toBeNull();
    expect(result.thresholdConfigured).toBe(false);
  });

  it("reports an empty list when a threshold exists and nothing is stale", () => {
    const result = assessStale(stateWith(), CONFIG, NOW);
    expect(result.staleLabels).toEqual([]);
    expect(result.thresholdConfigured).toBe(true);
  });

  it("an unparseable timestamp is INVALID, not stale — it is skipped, not reported", () => {
    const bad = stateWith({ vehicles: { "V-1": vehicle("V-1", "not-a-timestamp") } });
    expect(assessStale(bad, CONFIG, NOW).staleLabels).toEqual([]);
  });

  it("covers vehicles, safety, road and health timestamps", () => {
    const state = stateWith({
      vehicles: { "V-1": vehicle("V-1", T) },
      health: {
        timestamp: T,
        systemMode: "NORMAL",
        connectivity: "CONNECTED",
        fleetCount: 1,
        components: [],
      },
    });
    const labels = assessStale(state, CONFIG, NOW).staleLabels ?? [];
    expect(labels).toContain("vehicle V-1");
    expect(labels).toContain("system health");
  });

  it("is deterministically ordered", () => {
    const state = stateWith({
      vehicles: { "V-2": vehicle("V-2", T), "V-1": vehicle("V-1", T) },
    });
    expect(assessStale(state, CONFIG, NOW).staleLabels).toEqual(["vehicle V-1", "vehicle V-2"]);
  });

  it("never reports a negative age for a future timestamp", () => {
    const future = stateWith({ vehicles: { "V-1": vehicle("V-1", "2027-01-01T00:00:00.000Z") } });
    expect(assessStale(future, CONFIG, NOW).staleLabels).toEqual([]);
  });
});

// ---------------------------------------------------------------------------

describe("merging — supplied alerts are never altered or displaced", () => {
  const supplied = stateWith({ alerts: [alert()] });

  it("passes supplied alerts through unchanged", () => {
    const before = JSON.parse(JSON.stringify(supplied.alerts));
    const merged = mergedAlerts(supplied, CONFIG, NOW);
    expect(merged.supplied).toHaveLength(1);
    expect(JSON.parse(JSON.stringify(supplied.alerts))).toEqual(before);
  });

  it("does not mutate AppState", () => {
    const before = JSON.parse(JSON.stringify(supplied));
    mergedAlerts(supplied, CONFIG, NOW);
    expect(JSON.parse(JSON.stringify(supplied))).toEqual(before);
  });

  it("adds derived alerts alongside supplied ones", () => {
    const merged = mergedAlerts(connected(supplied, "DISCONNECTED"), CONFIG, NOW);
    expect(merged.supplied).toHaveLength(1);
    expect(merged.derived).toHaveLength(1);
    expect(merged.all).toHaveLength(2);
  });

  it("a derived alert never overwrites a supplied alert sharing its id", () => {
    const collision = stateWith({
      alerts: [alert({ alertId: COMM_LOSS_ALERT_ID, message: "supplied wins" })],
    });
    const merged = mergedAlerts(connected(collision, "DISCONNECTED"), CONFIG, NOW);
    expect(merged.all).toHaveLength(1);
    expect(merged.all[0]?.message).toBe("supplied wins");
    expect(merged.derived).toHaveLength(0);
  });

  it("marks derived alerts with origin HMI, and supplied ones with TASK2", () => {
    const merged = mergedAlerts(connected(supplied, "DISCONNECTED"), CONFIG, NOW);
    expect(merged.derived.every(isHmiOriginated)).toBe(true);
    expect(merged.supplied.every((a) => a.origin === "TASK2")).toBe(true);
  });

  it("namespaces derived ids so they cannot be mistaken for supplied ones", () => {
    expect(COMM_LOSS_ALERT_ID.startsWith("HMI:")).toBe(true);
    expect(STALE_DATA_ALERT_ID.startsWith("HMI:")).toBe(true);
  });

  it("reports whether stale alerting could fire at all", () => {
    expect(mergedAlerts(supplied, CONFIG, NOW).staleAlertingActive).toBe(true);
    expect(mergedAlerts(supplied, null, NOW).staleAlertingActive).toBe(false);
  });
});

describe("merged ordering is deterministic (FR-014 AC2)", () => {
  it("orders by severity, then recency, then id", () => {
    const state = stateWith({
      alerts: [
        alert({ alertId: "A-info", severity: "INFO" }),
        alert({ alertId: "A-crit", severity: "CRITICAL" }),
        alert({ alertId: "A-warn", severity: "WARNING" }),
      ],
    });
    expect(mergedAlerts(state, CONFIG, NOW).all.map((a) => a.alertId)).toEqual([
      "A-crit",
      "A-warn",
      "A-info",
    ]);
  });

  it("is stable for equal severity AND equal timestamp", () => {
    const state = stateWith({
      alerts: [
        alert({ alertId: "A-z", severity: "WARNING" }),
        alert({ alertId: "A-a", severity: "WARNING" }),
      ],
    });
    expect(mergedAlerts(state, CONFIG, NOW).all.map((a) => a.alertId)).toEqual(["A-a", "A-z"]);
  });

  it("produces the same order whatever order the input arrived in", () => {
    const alerts = [
      alert({ alertId: "A-1", severity: "WARNING" }),
      alert({ alertId: "A-2", severity: "CRITICAL" }),
      alert({ alertId: "A-3", severity: "INFO" }),
      alert({ alertId: "A-4", severity: "WARNING" }),
    ];
    const forward = mergedAlerts(stateWith({ alerts }), CONFIG, NOW).all.map((a) => a.alertId);
    const reversed = mergedAlerts(
      stateWith({ alerts: [...alerts].reverse() }),
      CONFIG,
      NOW,
    ).all.map((a) => a.alertId);
    expect(reversed).toEqual(forward);
  });

  it("handles every supplied severity, INFO included", () => {
    for (const severity of ["INFO", "WARNING", "CRITICAL"] as const) {
      const merged = mergedAlerts(stateWith({ alerts: [alert({ severity })] }), CONFIG, NOW);
      expect(merged.all[0]?.severity).toBe(severity);
    }
  });

  it("carries every contract category through untouched", () => {
    for (const category of [
      "UNSAFE_SPEED",
      "UNSAFE_HEADWAY",
      "BOTTLENECK_RISK",
      "SLOT_CONFLICT",
      "COMM_LOSS",
      "STALE_DATA",
    ] as const) {
      const merged = mergedAlerts(stateWith({ alerts: [alert({ category })] }), CONFIG, NOW);
      expect(merged.all[0]?.category).toBe(category);
      // Supplied alerts keep their supplied origin, even for the two HMI categories.
      expect(merged.all[0]?.origin).toBe("TASK2");
    }
  });

  it("an empty state yields no alerts at all", () => {
    const merged = mergedAlerts(stateWith(), CONFIG, NOW);
    expect(merged.all).toEqual([]);
    expect(merged.derived).toEqual([]);
  });
});

describe("scope — the HMI fabricates no producer alert", () => {
  it("originates only COMM_LOSS and STALE_DATA, under every condition tested", () => {
    const state = stateWith({
      vehicles: { "V-1": vehicle("V-1", "2020-01-01T00:00:00.000Z") },
      alerts: [alert()],
    });
    for (const status of ["IDLE", "CONNECTED", "DISCONNECTED", "ERROR", "RECONNECTING"] as const) {
      for (const config of [CONFIG, null]) {
        for (const derived of hmiDataPathAlerts(connected(state, status), config, NOW)) {
          expect(["COMM_LOSS", "STALE_DATA"]).toContain(derived.category);
          expect(derived.origin).toBe("HMI");
        }
      }
    }
  });

  it("never originates UNSAFE_SPEED, UNSAFE_HEADWAY, BOTTLENECK_RISK or SLOT_CONFLICT", () => {
    const state = connected(
      stateWith({ vehicles: { "V-1": vehicle("V-1", "2020-01-01T00:00:00.000Z") } }),
      "DISCONNECTED",
    );
    const categories = hmiDataPathAlerts(state, CONFIG, NOW).map((a) => a.category);
    for (const forbidden of [
      "UNSAFE_SPEED",
      "UNSAFE_HEADWAY",
      "BOTTLENECK_RISK",
      "SLOT_CONFLICT",
    ]) {
      expect(categories).not.toContain(forbidden);
    }
  });

  it("is deterministic for identical inputs", () => {
    const state = connected(stateWith(), "DISCONNECTED");
    expect(hmiDataPathAlerts(state, CONFIG, NOW)).toEqual(hmiDataPathAlerts(state, CONFIG, NOW));
  });
});
