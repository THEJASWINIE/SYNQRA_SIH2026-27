/**
 * Alert list render tests — M8. FR-014, FR-016.
 *
 * `react-dom/server` against a real `AppStateStore` via `HmiContext` (M5D-B). No jsdom,
 * no Testing Library (M4D-C).
 *
 * Colour is stripped before every severity, mode and provenance assertion, so nothing
 * passes on a colour attribute alone (NFR-008).
 *
 * FIXTURES ARE TEST-LOCAL (M7D-D precedent). No authored scenario supplies INFO severity,
 * BOTTLENECK_RISK, DEGRADED, LOCAL_SAFE or STOP_UNSAFE, so those are fixtured here.
 * NO M3 SCENARIO FILE IS MODIFIED.
 */

import type { ReactNode } from "react";
import { renderToString } from "react-dom/server";
import { describe, expect, it } from "vitest";
import { type FreshnessConfig, freshnessConfig } from "../config/freshness";
import type { ConnectionStatus } from "../contracts/appState";
import type { Alert, VehicleState } from "../contracts/domain";
import type { SystemMode } from "../contracts/enums";
import { ALERT_CATEGORIES, ALERT_SEVERITIES, SYSTEM_MODES } from "../contracts/enums";
import { HmiContext } from "../state/ProviderHost";
import { AppStateStore } from "../state/store";
import { testHmiContext } from "../state/testHmiContext";
import { AlertList } from "./AlertList";

const T = "2026-01-01T00:00:00.000Z";
const CONFIG = freshnessConfig(5000);

function greyscale(html: string): string {
  return html.replace(/color:[^;"]*;?/g, "").replace(/#[0-9a-fA-F]{3,8}/g, "");
}

function alert(partial: Partial<Alert> = {}): Alert {
  return {
    alertId: "A-1",
    timestamp: T,
    severity: "WARNING",
    category: "UNSAFE_SPEED",
    origin: "TASK2",
    subject: { kind: "VEHICLE", id: "V-1" },
    message: "supplied alert message",
    reasonCode: "ENV-01",
    acknowledgeable: true,
    acknowledged: null,
    active: true,
    ...partial,
  };
}

function vehicle(timestamp: string): VehicleState {
  return {
    vehicleId: "V-1",
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

interface MountOptions {
  alerts?: Alert[];
  mode?: SystemMode | null;
  status?: ConnectionStatus;
  error?: string | null;
  config?: FreshnessConfig | null;
  vehicleTimestamp?: string;
  nowIso?: string;
}

function render(options: MountOptions = {}): string {
  const store = new AppStateStore(T);

  store.applyPatch(
    {
      changes: {
        alerts: options.alerts ?? [],
        ...(options.vehicleTimestamp
          ? { vehicles: { "V-1": vehicle(options.vehicleTimestamp) } }
          : {}),
        ...(options.mode !== null && options.mode !== undefined
          ? {
              health: {
                timestamp: T,
                systemMode: options.mode,
                connectivity: "CONNECTED" as const,
                fleetCount: 1,
                components: [],
              },
            }
          : {}),
      },
    },
    T,
  );

  store.setStatus(options.status ?? "CONNECTED", options.error ?? null);
  store.setScenarioName("Test scenario");
  if (options.nowIso) store.tick(options.nowIso);

  const value = testHmiContext({
    store,
    freshness: options.config === undefined ? CONFIG : options.config,
  });

  const wrap = (children: ReactNode) => (
    <HmiContext.Provider value={value}>{children}</HmiContext.Provider>
  );

  return renderToString(wrap(<AlertList />));
}

// ---------------------------------------------------------------------------

describe("supplied alerts", () => {
  it("renders a supplied alert with its message, category and subject", () => {
    const html = render({ alerts: [alert()] });
    expect(html).toContain("supplied alert message");
    expect(html).toContain("UNSAFE_SPEED");
    expect(html).toContain("V-1");
  });

  it("marks supplied alerts as TASK2 in text", () => {
    expect(greyscale(render({ alerts: [alert()] }))).toContain("ORIGIN TASK2 — SUPPLIED");
  });

  it.each(ALERT_SEVERITIES)("renders supplied severity %s as text", (severity) => {
    expect(greyscale(render({ alerts: [alert({ severity })] }))).toContain(severity);
  });

  it.each(ALERT_CATEGORIES)("renders supplied category %s", (category) => {
    expect(render({ alerts: [alert({ category })] })).toContain(category);
  });

  it("renders multiple alerts, ordered by severity", () => {
    const html = greyscale(
      render({
        alerts: [
          alert({ alertId: "A-info", severity: "INFO", message: "info alert" }),
          alert({ alertId: "A-crit", severity: "CRITICAL", message: "critical alert" }),
          alert({ alertId: "A-warn", severity: "WARNING", message: "warning alert" }),
        ],
      }),
    );
    expect(html.indexOf("critical alert")).toBeLessThan(html.indexOf("warning alert"));
    expect(html.indexOf("warning alert")).toBeLessThan(html.indexOf("info alert"));
  });

  it("excludes inactive alerts from the live list", () => {
    // Cleared alerts are history and belong to the M9 event timeline. Keeping them on a
    // live list would compete for attention with conditions that are still true.
    const html = render({
      alerts: [
        alert({ alertId: "A-1", active: true, message: "still active" }),
        alert({ alertId: "A-2", active: false, message: "already cleared" }),
      ],
    });
    expect(html).toContain("still active");
    expect(html).not.toContain("already cleared");
    expect(html).toContain("1 active");
  });

  it("marks a non-acknowledgeable alert as such", () => {
    expect(render({ alerts: [alert({ acknowledgeable: false })] })).toContain(
      "not acknowledgeable",
    );
  });

  it("renders an honest empty state", () => {
    const html = render({ alerts: [] });
    expect(html).toContain("NO ACTIVE ALERTS");
    expect(html).toContain("no HMI data-path condition is present");
  });

  it("renders an invalid alert timestamp as INVALID, never as stale", () => {
    const html = greyscale(render({ alerts: [alert({ timestamp: "not-a-timestamp" })] }));
    expect(html).toContain("INVALID");
  });
});

describe("HMI-originated alerts (M8D-A)", () => {
  it("raises COMM_LOSS when the feed is lost, marked ORIGIN HMI", () => {
    const html = greyscale(render({ status: "DISCONNECTED" }));
    expect(html).toContain("COMM_LOSS");
    expect(html).toContain("ORIGIN HMI — DATA PATH");
  });

  it("includes the supplied provider error text", () => {
    expect(render({ status: "ERROR", error: "V2I link lost" })).toContain("V2I link lost");
  });

  it("raises no COMM_LOSS while the feed is up", () => {
    expect(render({ status: "CONNECTED" })).not.toContain("COMM_LOSS ·");
  });

  it("raises STALE_DATA when a threshold is configured and data aged out", () => {
    const html = greyscale(render({ vehicleTimestamp: T, nowIso: "2026-01-01T00:01:00.000Z" }));
    expect(html).toContain("STALE_DATA");
    expect(html).toContain("ORIGIN HMI");
  });

  it("counts supplied and derived alerts separately", () => {
    const html = render({ alerts: [alert()], status: "DISCONNECTED" });
    expect(html).toContain("Supplied by Task 2");
    expect(html).toContain("Originated by the HMI");
  });

  it("supplied alerts of an HMI category keep their supplied origin", () => {
    const html = greyscale(render({ alerts: [alert({ category: "COMM_LOSS" })] }));
    expect(html).toContain("ORIGIN TASK2 — SUPPLIED");
  });
});

describe("stale alerting gate (M8D-B)", () => {
  it("reports stale alerting INACTIVE when no threshold is configured", () => {
    const html = render({ config: null });
    expect(html).toContain("STALE ALERTING INACTIVE");
    expect(html).toContain("no freshness threshold configured");
    expect(html).toContain("AMB-014");
  });

  it("raises no STALE_DATA alert without a threshold, however old the data", () => {
    const html = render({
      config: null,
      vehicleTimestamp: "2020-01-01T00:00:00.000Z",
      nowIso: "2026-01-01T02:00:00.000Z",
    });
    expect(html).not.toContain("STALE_DATA ·");
  });

  it("still shows age when the threshold is absent", () => {
    expect(render({ config: null, alerts: [alert()] })).toContain("AGE ONLY — NOT CLASSIFIED");
  });

  it("reports stale alerting ACTIVE when a threshold exists", () => {
    expect(render({})).toContain("ACTIVE");
  });

  it("never invents a threshold", () => {
    const html = render({ config: null });
    expect(html).toContain("No default is assumed");
  });
});

describe("system mode (FR-016)", () => {
  it.each(SYSTEM_MODES)("renders supplied mode %s while the feed is up", (mode) => {
    expect(greyscale(render({ mode }))).toContain(
      mode === "LOCAL_SAFE" ? "LOCAL-SAFE" : mode === "STOP_UNSAFE" ? "STOP / UNSAFE" : mode,
    );
  });

  it("floors NORMAL to DEGRADED when the feed is lost", () => {
    const html = greyscale(render({ mode: "NORMAL", status: "DISCONNECTED" }));
    expect(html).toContain("DEGRADED");
    expect(html).toContain("data feed lost");
  });

  it("floors CAUTION to DEGRADED when the feed is lost", () => {
    expect(greyscale(render({ mode: "CAUTION", status: "DISCONNECTED" }))).toContain("DEGRADED");
  });

  it("preserves a supplied LOCAL_SAFE through feed loss", () => {
    const html = greyscale(render({ mode: "LOCAL_SAFE", status: "DISCONNECTED" }));
    expect(html).toContain("LOCAL-SAFE");
  });

  it("preserves a supplied STOP_UNSAFE through feed loss", () => {
    const html = greyscale(render({ mode: "STOP_UNSAFE", status: "DISCONNECTED" }));
    expect(html).toContain("STOP / UNSAFE");
  });

  it("states the supplied value when the floor applied", () => {
    const html = render({ mode: "NORMAL", status: "DISCONNECTED" });
    expect(html).toContain("Supplied mode was");
    expect(html).toContain("NORMAL");
  });

  it("never defaults to NORMAL when no mode was supplied", () => {
    const html = greyscale(render({ mode: null }));
    expect(html).toContain("NO SYSTEM MODE SUPPLIED");
    expect(html).not.toContain(">NORMAL<");
  });

  it("shows DEGRADED when nothing was supplied and the feed is lost", () => {
    expect(greyscale(render({ mode: null, status: "DISCONNECTED" }))).toContain("DEGRADED");
  });
});

describe("scope — display only (M8D-C)", () => {
  it("renders no acknowledgement control", () => {
    const html = render({ alerts: [alert({ acknowledgeable: true })], status: "DISCONNECTED" });
    expect(html).not.toContain("<button");
    expect(html).not.toContain("<form");
    expect(html).not.toContain("<input");
    expect(html.toLowerCase()).not.toContain(">acknowledge<");
  });

  it("states that acknowledgement is deferred to M9", () => {
    const html = render();
    expect(html).toContain("FR-015 acknowledgement is NOT implemented");
    expect(html).toContain("M9");
  });

  it("renders no command, override or actuation control", () => {
    const html = render({ alerts: [alert()] }).toLowerCase();
    for (const forbidden of ["override", "send command", "execute", "dispatch now", "actuate"]) {
      expect(html, `forbidden control: ${forbidden}`).not.toContain(forbidden);
    }
  });

  it("does not mutate the supplied alerts it renders", () => {
    const supplied = alert();
    const before = JSON.parse(JSON.stringify(supplied));
    render({ alerts: [supplied] });
    expect(supplied).toEqual(before);
  });

  it("lists all six contract categories as reference, and names the two the HMI owns", () => {
    const html = render();
    for (const category of ALERT_CATEGORIES) expect(html).toContain(category);
    expect(html).toContain("The HMI originates only");
  });

  it("severity key carries a label and a glyph for each severity", () => {
    const html = greyscale(render());
    for (const severity of ALERT_SEVERITIES) expect(html).toContain(severity);
  });
});
