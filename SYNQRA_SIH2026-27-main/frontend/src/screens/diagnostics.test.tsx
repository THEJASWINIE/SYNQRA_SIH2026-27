/**
 * S6 Diagnostics render tests — M10. FR-013, S6-a, NFR-003.
 *
 * `react-dom/server` against a real `AppStateStore` via `HmiContext` (M5D-B). No jsdom,
 * no Testing Library (M4D-C). Colour stripped before every state assertion (NFR-008).
 *
 * FIXTURES ARE TEST-LOCAL. No authored scenario supplies V2V, LoRa, a non-UP health
 * state, an error code or a non-CONNECTED connectivity, so those are fixtured here.
 * NO M3 SCENARIO FILE IS MODIFIED.
 */

import type { ReactNode } from "react";
import { renderToString } from "react-dom/server";
import { describe, expect, it } from "vitest";
import { API_BASE_URL } from "../api/healthClient";
import { type FreshnessConfig, freshnessConfig } from "../config/freshness";
import type { ConnectionStatus } from "../contracts/appState";
import type { Health, VehicleState } from "../contracts/domain";
import type { ConnectivityState, HealthState, LinkKind, SystemMode } from "../contracts/enums";
import { CONNECTIVITY_STATES, HEALTH_STATES, LINK_KINDS, SYSTEM_MODES } from "../contracts/enums";
import type { ValidationFailure } from "../data/errors";
import { HmiContext, type HmiContextValue } from "../state/ProviderHost";
import { AppStateStore } from "../state/store";
import { testHmiContext } from "../state/testHmiContext";
import { Diagnostics } from "./Diagnostics";

const T = "2026-01-01T00:00:00.000Z";
const CONFIG = freshnessConfig(5000);

function greyscale(html: string): string {
  return html.replace(/color:[^;"]*;?/g, "").replace(/#[0-9a-fA-F]{3,8}/g, "");
}

function link(partial: Partial<Health> = {}): Health {
  return {
    componentId: "LINK-V2I",
    timestamp: T,
    state: "UP",
    latencyMs: 12,
    ageMs: 40,
    errorCode: null,
    linkKind: "V2I",
    messagesReceived: 100,
    messagesDropped: 0,
    ...partial,
  };
}

function vehicle(timestamp: string): VehicleState {
  return {
    vehicleId: "V-1",
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

const failure: ValidationFailure = {
  kind: "VALIDATION",
  messageType: "VehicleState",
  receivedAt: "2026-01-01T00:00:03.000Z",
  issues: [
    {
      path: "position.segment_id",
      expected: "string",
      received: "number",
      message: "Expected string, received number",
    },
  ],
};

interface MountOptions {
  links?: Health[];
  mode?: SystemMode | null;
  connectivity?: ConnectivityState;
  status?: ConnectionStatus;
  error?: string | null;
  config?: FreshnessConfig | null;
  vehicleTimestamp?: string;
  nowIso?: string;
  failures?: readonly ValidationFailure[];
}

function render(options: MountOptions = {}): string {
  const store = new AppStateStore(T);

  store.applyPatch(
    {
      changes: {
        ...(options.vehicleTimestamp
          ? { vehicles: { "V-1": vehicle(options.vehicleTimestamp) } }
          : {}),
        ...(options.mode === null
          ? {}
          : {
              health: {
                timestamp: T,
                systemMode: options.mode ?? "NORMAL",
                connectivity: options.connectivity ?? "CONNECTED",
                fleetCount: 2,
                components: options.links ?? [link()],
              },
            }),
      },
    },
    T,
  );

  store.setStatus(options.status ?? "CONNECTED", options.error ?? null);
  if (options.nowIso) store.tick(options.nowIso);

  const overrides: Partial<HmiContextValue> = { validationFailures: options.failures ?? [] };
  const value = testHmiContext({
    store,
    freshness: options.config === undefined ? CONFIG : options.config,
    overrides,
  });

  const wrap = (children: ReactNode) => (
    <HmiContext.Provider value={value}>{children}</HmiContext.Provider>
  );
  return renderToString(wrap(<Diagnostics />));
}

// ---------------------------------------------------------------------------

describe("communication health (FR-013)", () => {
  it.each(LINK_KINDS)("renders supplied link kind %s", (linkKind: LinkKind) => {
    // No authored scenario supplies V2V or LoRa — fixtured here (FR-013 AC1).
    const html = render({ links: [link({ linkKind, componentId: `LINK-${linkKind}` })] });
    expect(html).toContain(linkKind);
  });

  it("represents all three link kinds on one screen", () => {
    const html = render({
      links: [
        link({ linkKind: "V2V", componentId: "LINK-V2V" }),
        link({ linkKind: "V2I", componentId: "LINK-V2I" }),
        link({ linkKind: "LORA", componentId: "LINK-LORA" }),
      ],
    });
    for (const kind of ["V2V", "V2I", "LORA"]) expect(html).toContain(kind);
  });

  it.each(HEALTH_STATES)("renders supplied health state %s as text", (state: HealthState) => {
    const html = greyscale(render({ links: [link({ state })] }));
    expect(html).toContain(state.replace(/_/g, " "));
  });

  it("renders UNKNOWN as unknown, never normalised to UP", () => {
    const html = greyscale(render({ links: [link({ state: "UNKNOWN" })] }));
    expect(html).toContain("UNKNOWN");
    expect(html).not.toMatch(/>UP</);
  });

  it("renders a supplied error code, and says so when none was supplied", () => {
    expect(render({ links: [link({ errorCode: "V2I-TIMEOUT" })] })).toContain("V2I-TIMEOUT");
    expect(render()).toContain("none supplied");
  });

  it("renders supplied latency and supplied age, labelled as supplied", () => {
    const html = render({ links: [link({ latencyMs: 140, ageMs: 800 })] });
    expect(html).toContain("140");
    expect(html).toContain("800");
    expect(html).toContain("Latency (supplied)");
    expect(html).toContain("Age (supplied)");
  });

  it("never conflates the supplied Health.ageMs with the derived datum age", () => {
    const html = render();
    expect(html).toContain("Age (supplied)");
    expect(html).toContain("Oldest age (derived)");
    expect(html).toContain("are SUPPLIED by the producer");
  });

  it("states which link kinds this scenario actually supplies", () => {
    const html = render({ links: [link({ linkKind: "V2I" })] });
    // React splits interpolations with comment markers: `V2I<!-- --> · SUPPLIED`.
    expect(html).toContain("V2I<!-- --> · SUPPLIED");
    expect(html).toContain("V2V<!-- --> · not in this scenario");
  });

  it("renders an empty state when no component was supplied", () => {
    const html = render({ links: [] });
    expect(html).toContain("NO LINK HEALTH SUPPLIED");
    expect(html).toContain("does not synthesise link health");
  });
});

describe("message counters (S6-a, M10D-A)", () => {
  it("renders supplied received and dropped counts", () => {
    const html = render({ links: [link({ messagesReceived: 1200, messagesDropped: 3 })] });
    expect(html).toContain("1200");
    expect(html).toContain("3");
  });

  it("renders a supplied zero as zero — a zero is a value", () => {
    const html = render({ links: [link({ messagesDropped: 0 })] });
    expect(html).toContain("Msgs dropped");
    expect(html).toContain("0");
  });

  it("renders an absent counter as UNAVAILABLE, never as 0", () => {
    const html = render({
      links: [link({ messagesReceived: null, messagesDropped: null })],
    });
    expect(html).toContain("UNAVAILABLE");
  });

  it("renders absent latency and age as UNAVAILABLE", () => {
    const html = render({ links: [link({ latencyMs: null, ageMs: null })] });
    expect(html).toContain("UNAVAILABLE");
  });
});

describe("freshness overview (NFR-003)", () => {
  it("lists every message type", () => {
    const html = render();
    for (const type of ["VehicleState", "SafetyState", "SystemHealth", "KpiSnapshot"]) {
      expect(html).toContain(type);
    }
  });

  it("classifies a recent datum as current when a threshold is configured", () => {
    const html = greyscale(render({ vehicleTimestamp: T }));
    expect(html).toContain("CURRENT");
  });

  it("classifies an aged datum as stale", () => {
    const html = greyscale(render({ vehicleTimestamp: T, nowIso: "2026-01-01T00:01:00.000Z" }));
    expect(html).toContain("STALE");
  });

  it("classifies a malformed timestamp as INVALID, never stale", () => {
    const html = greyscale(render({ vehicleTimestamp: "not-a-timestamp" }));
    expect(html).toContain("INVALID");
  });

  it("with no configured threshold, shows ages and refuses to classify", () => {
    const html = render({ config: null, vehicleTimestamp: T });
    expect(html).toContain("FRESHNESS THRESHOLD NOT CONFIGURED");
    expect(html).toContain("n/e");
    expect(html).toContain("not evaluated");
  });

  it("never invents a default threshold", () => {
    expect(render({ config: null })).toContain("No default is assumed");
  });

  it("states the INVALID / MISSING distinction", () => {
    const html = render();
    expect(html).toContain("INVALID, never STALE");
    expect(html).toContain("MISSING, never INVALID");
  });
});

describe("backend health — a separate failure domain", () => {
  it("renders the backend panel distinctly from the operational feed", () => {
    const html = render();
    expect(html).toContain("HMI backend health");
    expect(html).toContain("separate failure domain");
    expect(html).toContain("Data connection — operational telemetry");
  });

  it("states that the backend panel is not the data feed", () => {
    expect(render()).toContain("never merged into one indicator");
  });

  it("shows the configured backend address", () => {
    expect(render()).toContain(API_BASE_URL);
  });

  it("renders service, version, milestone and latency slots", () => {
    const html = render();
    for (const label of ["Service", "Version", "Milestone", "Round-trip latency"]) {
      expect(html).toContain(label);
    }
  });

  it("keeps operational values visible regardless of backend state", () => {
    // Effects do not run under renderToString, so this is the pre-check state: the
    // operational panels must already be populated from AppState alone.
    const html = render({ vehicleTimestamp: T });
    expect(html).toContain("VehicleState");
    expect(html).toContain("Communication health");
  });
});

describe("provider status", () => {
  it.each(["IDLE", "CONNECTING", "CONNECTED", "RECONNECTING", "DISCONNECTED", "ERROR"] as const)(
    "renders provider status %s",
    (status) => {
      const html = greyscale(render({ status }));
      const expected = {
        IDLE: "Idle",
        CONNECTING: "Connecting",
        CONNECTED: "Connected",
        RECONNECTING: "Reconnecting",
        DISCONNECTED: "Disconnected",
        ERROR: "Provider error",
      }[status];
      expect(html).toContain(expected);
    },
  );

  it("shows the provider error message when one is reported", () => {
    expect(render({ status: "ERROR", error: "feed lost" })).toContain("feed lost");
  });
});

describe("global operational state", () => {
  it.each(SYSTEM_MODES)("renders supplied system mode %s", (mode: SystemMode) => {
    const html = greyscale(render({ mode }));
    const expected =
      mode === "LOCAL_SAFE" ? "LOCAL-SAFE" : mode === "STOP_UNSAFE" ? "STOP / UNSAFE" : mode;
    expect(html).toContain(expected);
  });

  it("never defaults to NORMAL when no mode was supplied", () => {
    const html = greyscale(render({ mode: null }));
    expect(html).toContain("NOT SUPPLIED");
  });

  it("applies the M8 DEGRADED floor when the feed is lost", () => {
    const html = greyscale(render({ mode: "NORMAL", status: "DISCONNECTED" }));
    expect(html).toContain("DEGRADED");
    expect(html).toContain("data feed lost");
  });

  it.each(CONNECTIVITY_STATES)("renders supplied connectivity %s", (connectivity) => {
    expect(render({ connectivity })).toContain(connectivity);
  });
});

describe("validation diagnostics (M10D-B)", () => {
  it("renders an explicit empty state when nothing failed", () => {
    const html = render({ failures: [] });
    expect(html).toContain("NO VALIDATION FAILURES RECORDED");
    expect(html).toContain("passed the contract schema");
  });

  it("renders a recorded failure with type, field, expectation and detail", () => {
    const html = render({ failures: [failure] });
    expect(html).toContain("VehicleState");
    expect(html).toContain("position.segment_id");
    expect(html).toContain("Expected string, received number");
  });

  it("renders every issue of a multi-issue failure", () => {
    const html = render({
      failures: [
        {
          ...failure,
          issues: [
            ...failure.issues,
            { path: "speed_mps", expected: "number", received: "string", message: "second issue" },
          ],
        },
      ],
    });
    expect(html).toContain("position.segment_id");
    expect(html).toContain("speed_mps");
  });

  it("is read-only — the panel renders no control at all", () => {
    // The panel's own prose explains that there is no retry or reset, so a word scan
    // would match the explanation. Assert on interactive ELEMENTS instead.
    const html = render({ failures: [failure] });
    expect(html).not.toContain("<button");
    expect(html).not.toContain("<input");
    expect(html).not.toContain("<form");
    expect(html).not.toContain("onclick");
  });

  it("states the INVALID-not-MISSING rule", () => {
    expect(render()).toContain("INVALID, never MISSING");
  });
});

describe("scope — no operational control, no computation", () => {
  it("renders no form, no input and no button", () => {
    const html = render({ failures: [failure] });
    expect(html).not.toContain("<form");
    expect(html).not.toContain("<input");
    expect(html).not.toContain("<button");
  });

  it("renders no acknowledge, command, override or actuation control", () => {
    const html = render({ failures: [failure] }).toLowerCase();
    for (const forbidden of [
      "acknowledge",
      "send command",
      "override",
      "actuate",
      "dispatch now",
      "release vehicle",
    ]) {
      expect(html, `forbidden control: ${forbidden}`).not.toContain(forbidden);
    }
  });

  it("does not mutate the supplied health it renders", () => {
    const supplied = link();
    const before = JSON.parse(JSON.stringify(supplied));
    render({ links: [supplied] });
    expect(supplied).toEqual(before);
  });

  it("states that nothing operational is computed", () => {
    // The claim lives in the no-link empty state.
    expect(render({ links: [] })).toContain("Task 1 does not synthesise link health");
  });
});
