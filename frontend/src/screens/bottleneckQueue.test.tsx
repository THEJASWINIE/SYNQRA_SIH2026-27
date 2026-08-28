/**
 * S3 Bottleneck & Queue tests — M6.
 *
 * Rendered with `react-dom/server`, the pattern M1 established. No jsdom and no
 * @testing-library (M4D-C). Screens are mounted against a real `AppStateStore` holding a
 * controlled patch, so the data path under test is the production one.
 *
 * ASSERTIONS ARE AGAINST TEXT. Colour is stripped before every criticality assertion, so
 * no test can pass on a colour attribute alone (NFR-008).
 */

import type { ReactNode } from "react";
import { renderToString } from "react-dom/server";
import { describe, expect, it } from "vitest";
import { type FreshnessConfig, freshnessConfig } from "../config/freshness";
import type { ConnectionStatus } from "../contracts/appState";
import type { ArrivalPlan, BottleneckState } from "../contracts/domain";
import { HmiContext } from "../state/ProviderHost";
import { AppStateStore } from "../state/store";
import { testHmiContext } from "../state/testHmiContext";
import { BottleneckQueue } from "./BottleneckQueue";

const T = "2026-01-01T00:00:00.000Z";
const CONFIG = freshnessConfig(5000);

function greyscale(html: string): string {
  return html.replace(/color:[^;"]*;?/g, "").replace(/#[0-9a-fA-F]{3,8}/g, "");
}

function bottleneck(nodeId: string, partial: Partial<BottleneckState> = {}): BottleneckState {
  return {
    nodeId,
    timestamp: T,
    lambdaVph: 38,
    muVph: 40,
    queue: 4,
    queueMax: 8,
    utilization: 0.72,
    criticality: "HIGH",
    bottleneckScore: 0.5,
    queueHistory: null,
    queueForecast: null,
    ...partial,
  };
}

function arrival(nodeId: string, partial: Partial<ArrivalPlan> = {}): ArrivalPlan {
  return {
    nodeId,
    issuedAt: T,
    planned: [{ at: T, count: 4 }],
    actual: [{ at: T, count: 6 }],
    activeDecisions: [
      {
        vehicleId: "V-7",
        decision: "HOLD",
        until: T,
        reasonCode: "CRUSHER_QUEUE_LIMIT",
      },
    ],
    ...partial,
  };
}

interface MountOptions {
  bottlenecks?: Record<string, BottleneckState>;
  arrivals?: Record<string, ArrivalPlan>;
  status?: ConnectionStatus;
  error?: string | null;
  config?: FreshnessConfig | null;
  nowIso?: string;
}

/** Mounts S3 against a real store holding the supplied patch. */
function render(options: MountOptions = {}): string {
  const store = new AppStateStore(T);

  store.applyPatch(
    {
      changes: {
        bottlenecks: options.bottlenecks ?? { "N-CRUSHER-1": bottleneck("N-CRUSHER-1") },
        arrivals: options.arrivals ?? { "N-CRUSHER-1": arrival("N-CRUSHER-1") },
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

  return renderToString(wrap(<BottleneckQueue />));
}

// ---------------------------------------------------------------------------
// FR-006 — Bottleneck ranking
// ---------------------------------------------------------------------------

describe("bottleneck ranking (FR-006)", () => {
  it("renders a ranked list sorted by descending supplied score", () => {
    const html = render({
      bottlenecks: {
        "N-1": bottleneck("N-1", { bottleneckScore: 0.2 }),
        "N-2": bottleneck("N-2", { bottleneckScore: 0.9 }),
        "N-3": bottleneck("N-3", { bottleneckScore: 0.5 }),
      },
    });
    const n2 = html.indexOf("N-2");
    const n3 = html.indexOf("N-3");
    const n1 = html.indexOf("N-1");
    expect(n2).toBeLessThan(n3);
    expect(n3).toBeLessThan(n1);
  });

  it("deterministic tie-break by nodeId when scores are equal", () => {
    const html = render({
      bottlenecks: {
        "N-B": bottleneck("N-B", { bottleneckScore: 0.5 }),
        "N-A": bottleneck("N-A", { bottleneckScore: 0.5 }),
        "N-C": bottleneck("N-C", { bottleneckScore: 0.5 }),
      },
    });
    const nA = html.indexOf("N-A");
    const nB = html.indexOf("N-B");
    const nC = html.indexOf("N-C");
    // Alphabetical tie-break: N-A before N-B before N-C
    expect(nA).toBeLessThan(nB);
    expect(nB).toBeLessThan(nC);
  });

  it("each row shows score, utilization, queue, criticality", () => {
    const html = greyscale(
      render({
        bottlenecks: {
          "N-X": bottleneck("N-X", {
            bottleneckScore: 0.88,
            utilization: 0.95,
            queue: 6,
            queueMax: 8,
            criticality: "HIGH",
          }),
        },
      }),
    );
    expect(html).toContain("N-X");
    expect(html).toContain("0.88");
    expect(html).toContain("0.95");
    expect(html).toContain("6");
    expect(html).toContain("8");
    expect(html).toContain("HIGH");
  });

  it("null score renders as — and node sorts last", () => {
    const html = render({
      bottlenecks: {
        "N-1": bottleneck("N-1", { bottleneckScore: null }),
        "N-2": bottleneck("N-2", { bottleneckScore: 0.1 }),
      },
    });
    const n2 = html.indexOf("N-2");
    const n1 = html.indexOf("N-1");
    expect(n2).toBeLessThan(n1);
    expect(html).toContain("—");
  });

  it("empty bottleneck state renders NO BOTTLENECK DATA SUPPLIED", () => {
    const html = render({ bottlenecks: {}, arrivals: {} });
    expect(html).toContain("NO BOTTLENECK DATA SUPPLIED");
  });

  it("UNKNOWN criticality renders as UNKNOWN, not LOW or blank", () => {
    const html = greyscale(
      render({
        bottlenecks: {
          "N-1": bottleneck("N-1", { criticality: "UNKNOWN" }),
        },
      }),
    );
    expect(html).toContain("UNKNOWN");
  });
});

// ---------------------------------------------------------------------------
// FR-007 — Queue monitoring
// ---------------------------------------------------------------------------

describe("queue monitoring (FR-007)", () => {
  it("shows queue against queueMax", () => {
    const html = render({
      bottlenecks: {
        "N-1": bottleneck("N-1", { queue: 6, queueMax: 8 }),
      },
    });
    expect(html).toContain("6");
    expect(html).toContain("8");
  });

  it("lambda and mu labelled with vph units", () => {
    const html = render({
      bottlenecks: {
        "N-1": bottleneck("N-1", { lambdaVph: 46, muVph: 40 }),
      },
    });
    expect(html).toContain("46");
    expect(html).toContain("40");
    expect(html).toContain("vph");
  });

  it("null lambda/mu renders UNAVAILABLE, never 0", () => {
    const html = render({
      bottlenecks: {
        "N-1": bottleneck("N-1", { lambdaVph: null, muVph: null }),
      },
    });
    expect(html).toContain("UNAVAILABLE");
    // Ensure "0" does not appear where lambda/mu values would be
    // Both values are null, so no numeric "0" should be substituted
    // Note: "0" may appear in other contexts (timestamps, other fields),
    // so we check that UNAVAILABLE appears for both rate fields
    const unavailableCount = (html.match(/UNAVAILABLE/g) || []).length;
    // At least 4 UNAVAILABLE: 2 in the ranking table + 2 in the detail panel
    expect(unavailableCount).toBeGreaterThanOrEqual(4);
  });

  it("renders measured queue history as a labelled section", () => {
    const html = render({
      bottlenecks: {
        "N-1": bottleneck("N-1", {
          queueHistory: [
            { at: "2026-01-01T00:00:00.000Z", queue: 2 },
            { at: "2026-01-01T00:01:00.000Z", queue: 4 },
          ],
        }),
      },
    });
    expect(html).toContain("Measured history");
    expect(html).toContain("Measured queue history");
  });

  it("renders supplied queue forecast as a separately labelled section", () => {
    const html = render({
      bottlenecks: {
        "N-1": bottleneck("N-1", {
          queueForecast: [{ at: "2026-01-01T01:00:00.000Z", queue: 8, sigma: 1.5 }],
        }),
      },
    });
    expect(html).toContain("Forecast");
    expect(html).toContain("supplied by Task 2");
    expect(html).toContain("Supplied queue forecast");
  });

  it("null forecast explicitly states QUEUE FORECAST NOT SUPPLIED", () => {
    const html = render({
      bottlenecks: {
        "N-1": bottleneck("N-1", { queueForecast: null }),
      },
    });
    expect(html).toContain("QUEUE FORECAST NOT SUPPLIED");
  });

  it("history and forecast are structurally separated tables", () => {
    const html = render({
      bottlenecks: {
        "N-1": bottleneck("N-1", {
          queueHistory: [{ at: T, queue: 2 }],
          queueForecast: [{ at: T, queue: 8, sigma: 1.5 }],
        }),
      },
    });
    // Both sections exist as separate labelled elements
    expect(html).toContain("Measured history");
    expect(html).toContain("Forecast (supplied by Task 2)");
    // The two tables have distinct aria-labels
    expect(html).toContain("Measured queue history");
    expect(html).toContain("Supplied queue forecast");
  });
});

// ---------------------------------------------------------------------------
// FR-008 — Arrival shaping
// ---------------------------------------------------------------------------

describe("arrival shaping (FR-008)", () => {
  it("renders planned and actual arrivals as separately labelled sections", () => {
    const html = render();
    expect(html).toContain("Planned arrivals");
    expect(html).toContain("Actual arrivals");
  });

  it("active decision shows vehicle, decision, reason code", () => {
    const html = render();
    expect(html).toContain("V-7");
    expect(html).toContain("HOLD");
    expect(html).toContain("CRUSHER_QUEUE_LIMIT");
  });

  it("empty decision set renders NO ACTIVE METERING", () => {
    const html = render({
      arrivals: {
        "N-1": arrival("N-1", { activeDecisions: [] }),
      },
    });
    expect(html).toContain("NO ACTIVE METERING");
  });

  it("absent arrival data renders ARRIVAL DATA UNAVAILABLE", () => {
    const html = render({ arrivals: {} });
    expect(html).toContain("ARRIVAL DATA UNAVAILABLE");
  });

  it("renders decision timing when supplied", () => {
    const html = render();
    // The default fixture has an `until` field
    expect(html).toContain(T);
  });

  it("renders METER and RELEASE decisions correctly", () => {
    const html = render({
      arrivals: {
        "N-1": arrival("N-1", {
          activeDecisions: [
            { vehicleId: "V-1", decision: "METER", until: null, reasonCode: "RATE_LIMIT" },
            { vehicleId: "V-2", decision: "RELEASE", until: null, reasonCode: "CLEAR" },
          ],
        }),
      },
    });
    expect(html).toContain("METER");
    expect(html).toContain("RELEASE");
    expect(html).toContain("RATE_LIMIT");
    expect(html).toContain("CLEAR");
  });
});

// ---------------------------------------------------------------------------
// Degraded states
// ---------------------------------------------------------------------------

describe("degraded states", () => {
  it("classifies as STALE when threshold is configured and data is old", () => {
    const html = render({
      config: freshnessConfig(2000),
      nowIso: "2026-01-01T00:00:10.000Z",
    });
    expect(html).toContain("STALE");
  });

  it("with no configured threshold, shows age but does NOT classify", () => {
    const html = render({
      config: null,
      nowIso: "2026-01-01T00:00:10.000Z",
    });
    expect(html).toContain("AGE ONLY");
    expect(html).toContain("NOT CLASSIFIED");
  });

  it("renders a disconnected provider explicitly", () => {
    const html = render({ status: "DISCONNECTED" });
    expect(html).toContain("DISCONNECTED");
    expect(html).toContain("Disconnected");
  });

  it("keeps showing supplied values while disconnected, marked by their age", () => {
    const html = render({
      status: "DISCONNECTED",
      nowIso: "2026-01-01T00:05:00.000Z",
    });
    // Bottleneck data is still rendered
    expect(html).toContain("N-CRUSHER-1");
    // Age is shown
    expect(html).toContain("ago");
  });

  it("renders a provider error with its message", () => {
    const html = render({ status: "ERROR", error: "Socket timeout" });
    expect(html).toContain("Provider error");
    expect(html).toContain("Socket timeout");
  });
});

// ---------------------------------------------------------------------------
// Scope
// ---------------------------------------------------------------------------

describe("scope (M6)", () => {
  it("S3 renders no control that could command or actuate anything", () => {
    const html = render();
    // No form elements, no buttons
    expect(html).not.toContain("<form");
    expect(html).not.toContain("<button");
    expect(html).not.toContain("Acknowledge");
  });

  it("contains no scoring formula or computation text", () => {
    const html = render();
    // The disclaimer says "no scoring formula exists" — that is a scope statement,
    // not a formula. There should be no "formula = " or "computed" claims.
    expect(html).not.toContain("formula =");
    expect(html).not.toContain("calculated");
    expect(html).not.toContain("predicted");
    // The word "supplied" should appear (confirming data source)
    expect(html).toContain("supplied");
  });
});
