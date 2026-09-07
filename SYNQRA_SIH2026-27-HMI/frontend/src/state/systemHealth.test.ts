/**
 * S7 System Health — derivation tests. Phase 5.
 *
 * Pure logic: no DOM, no jsdom, no Testing Library (M4D-C).
 * The snapshot below is the shape the live backend actually returns.
 */

import { describe, expect, it } from "vitest";

import { normalizeObservability } from "../api/observabilityClient";
import type { ObservabilityState } from "../contracts/appState";
import {
  backendLine,
  commandLine,
  deriveSystemHealth,
  formatAgeSeconds,
  formatCounter,
  hardwareLine,
  modeLine,
  telemetryLine,
  twinLine,
} from "./systemHealth";

const LIVE_PAYLOAD = {
  service: "hmi-backend",
  timestamp: 1_788_665_982.04608,
  twin_attached: true,
  twin_vehicle_count: 2,
  telemetry_ingest: {
    accepted: 56,
    duplicate: 0,
    out_of_order: 0,
    invalid: 0,
    unknown_vehicle: 0,
  },
  command_gateway: {
    accepted: 6,
    rejected: 6,
    duplicate: 1,
    stale: 0,
    unknown_vehicle: 2,
    invalid: 0,
    unsafe: 3,
    timeout: 0,
  },
  backend_cache_vehicles: 2,
  websocket_clients: 1,
  command_history_length: 12,
  hardware: { hardware_seen: false, hardware_connected: false, age_seconds: null },
  mode: "MOCK",
};

const T0 = "2026-01-01T00:00:00.000Z";

function stateFrom(payload: unknown, over: Partial<ObservabilityState> = {}): ObservabilityState {
  const data = normalizeObservability(payload);
  return { status: "CURRENT", data, fetchedAt: T0, error: null, ...over };
}

const IDLE: ObservabilityState = { status: "IDLE", data: null, fetchedAt: null, error: null };

// ---------------------------------------------------------------------------
// 7/8 — counter formatting
// ---------------------------------------------------------------------------

describe("counter formatting", () => {
  it("7 — a real zero stays 0", () => {
    expect(formatCounter(0)).toBe("0");
  });

  it("8 — a missing counter shows unavailable, never 0", () => {
    expect(formatCounter(null)).toBe("--");
    expect(formatCounter(undefined)).toBe("--");
    expect(formatCounter(Number.NaN)).toBe("--");
    expect(formatCounter(null)).not.toBe("0");
  });

  it("formats an age, preserving unavailability", () => {
    expect(formatAgeSeconds(1.25)).toBe("1.3 s");
    expect(formatAgeSeconds(null)).toBe("--");
  });
});

// ---------------------------------------------------------------------------
// 3/9/10/11/12/13 — observability lifecycle
// ---------------------------------------------------------------------------

describe("observability lifecycle", () => {
  it("12 — IDLE before any fetch is not reported as healthy", () => {
    const line = backendLine(IDLE);
    expect(line.state).toBe("UNAVAILABLE");
    expect(line.value).toBe("NOT YET QUERIED");
    expect(line.value).not.toContain("ONLINE");
  });

  it("3 — CURRENT reports the backend online", () => {
    expect(backendLine(stateFrom(LIVE_PAYLOAD)).state).toBe("OK");
    expect(backendLine(stateFrom(LIVE_PAYLOAD)).value).toBe("ONLINE");
  });

  it("9/10 — STALE is degraded and keeps the last known counters", () => {
    const stale = stateFrom(LIVE_PAYLOAD, { status: "STALE", error: "backend unreachable" });
    const line = backendLine(stale);

    expect(line.state).toBe("DEGRADED");
    expect(line.value).toContain("STALE");
    expect(line.detail).toBe("backend unreachable");
    // The counters survive; they are neither blanked nor zeroed.
    expect(telemetryLine(stale).detail).toContain("56");
  });

  it("11 — ERROR before any success reports unreachable, with nothing invented", () => {
    const error: ObservabilityState = {
      status: "ERROR",
      data: null,
      fetchedAt: null,
      error: "connection refused",
    };
    expect(backendLine(error).state).toBe("OFF");
    expect(telemetryLine(error).value).toBe("--");
    expect(commandLine(error).value).toBe("--");
    expect(hardwareLine(error).value).toBe("--");
  });

  it("13 — a later success returns the banner to healthy", () => {
    expect(backendLine(stateFrom(LIVE_PAYLOAD, { status: "CURRENT" })).state).toBe("OK");
  });
});

// ---------------------------------------------------------------------------
// 14 — Twin
// ---------------------------------------------------------------------------

describe("twin line", () => {
  it("14 — reports attachment and the reported count", () => {
    const line = twinLine(stateFrom(LIVE_PAYLOAD));
    expect(line.state).toBe("OK");
    expect(line.value).toBe("ATTACHED");
    expect(line.detail).toContain("2 vehicle(s)");
  });

  it("says NOT ATTACHED when the backend says so", () => {
    const line = twinLine(stateFrom({ ...LIVE_PAYLOAD, twin_attached: false }));
    expect(line.state).toBe("OFF");
    expect(line.value).toBe("NOT ATTACHED");
  });

  it("does not claim attachment when the field is missing", () => {
    const line = twinLine(stateFrom({ ...LIVE_PAYLOAD, twin_attached: undefined }));
    expect(line.state).toBe("UNAVAILABLE");
  });

  it("attachment is never read as a vehicle being physically present", () => {
    const line = twinLine(stateFrom(LIVE_PAYLOAD));
    expect(`${line.value} ${line.detail}`.toLowerCase()).not.toContain("physical");
  });
});

// ---------------------------------------------------------------------------
// 4 — telemetry verdicts
// ---------------------------------------------------------------------------

describe("telemetry line", () => {
  it("4 — HEALTHY only when packets were accepted and none rejected", () => {
    const line = telemetryLine(stateFrom(LIVE_PAYLOAD));
    expect(line.state).toBe("OK");
    expect(line.value).toBe("HEALTHY");
  });

  it("DEGRADED when the backend reports invalid packets", () => {
    const line = telemetryLine(
      stateFrom({
        ...LIVE_PAYLOAD,
        telemetry_ingest: { ...LIVE_PAYLOAD.telemetry_ingest, invalid: 4 },
      }),
    );
    expect(line.state).toBe("DEGRADED");
    expect(line.detail).toContain("4 rejected");
  });

  it.each(["duplicate", "out_of_order", "unknown_vehicle"])(
    "DEGRADED when %s packets are reported",
    (field) => {
      const line = telemetryLine(
        stateFrom({
          ...LIVE_PAYLOAD,
          telemetry_ingest: { ...LIVE_PAYLOAD.telemetry_ingest, [field]: 2 },
        }),
      );
      expect(line.state).toBe("DEGRADED");
    },
  );

  it("NO DATA rather than HEALTHY when nothing has been accepted", () => {
    const line = telemetryLine(
      stateFrom({
        ...LIVE_PAYLOAD,
        telemetry_ingest: {
          accepted: 0,
          duplicate: 0,
          out_of_order: 0,
          invalid: 0,
          unknown_vehicle: 0,
        },
      }),
    );
    expect(line.state).toBe("OFF");
    expect(line.value).toBe("NO DATA");
    expect(line.value).not.toBe("HEALTHY");
  });

  it("UNAVAILABLE, not HEALTHY, when no counter was supplied", () => {
    const line = telemetryLine(stateFrom({ ...LIVE_PAYLOAD, telemetry_ingest: undefined }));
    expect(line.state).toBe("UNAVAILABLE");
  });
});

// ---------------------------------------------------------------------------
// 5/19 — command gateway
// ---------------------------------------------------------------------------

describe("command gateway line", () => {
  it("5 — READY with the real counters", () => {
    const line = commandLine(stateFrom(LIVE_PAYLOAD));
    expect(line.state).toBe("OK");
    expect(line.value).toBe("READY");
    expect(line.detail).toContain("6 accepted");
    expect(line.detail).toContain("6 refused");
  });

  it("19 — refusals are counters, not a fault verdict", () => {
    // 6 refusals out of 12 is the gateway failing closed, which is correct behaviour.
    const line = commandLine(stateFrom(LIVE_PAYLOAD));
    expect(line.state).not.toBe("DEGRADED");
    expect(line.state).toBe("OK");
  });

  it("UNAVAILABLE when the gateway reports nothing", () => {
    expect(commandLine(stateFrom({ ...LIVE_PAYLOAD, command_gateway: undefined })).state).toBe(
      "UNAVAILABLE",
    );
  });
});

// ---------------------------------------------------------------------------
// 6/15/16 — hardware and mode, the honesty-critical lines
// ---------------------------------------------------------------------------

describe("hardware and mode", () => {
  it("6/15 — NOT CONNECTED while the backend is perfectly reachable", () => {
    const line = hardwareLine(stateFrom(LIVE_PAYLOAD));
    expect(line.state).toBe("OFF");
    expect(line.value).toBe("NOT CONNECTED");
  });

  it("15 — reachability, Twin attachment and WS clients never imply hardware", () => {
    // This payload has twin_attached true, 1 websocket client, and 56 accepted packets.
    const line = hardwareLine(stateFrom(LIVE_PAYLOAD));
    expect(line.value).not.toBe("CONNECTED");
  });

  it("distinguishes SEEN from CONNECTED", () => {
    const line = hardwareLine(
      stateFrom({
        ...LIVE_PAYLOAD,
        hardware: { hardware_seen: true, hardware_connected: false, age_seconds: 42.5 },
      }),
    );
    expect(line.state).toBe("DEGRADED");
    expect(line.value).toBe("SEEN, NOT CONNECTED");
    expect(line.detail).toContain("42.5 s");
  });

  it("reports CONNECTED only when the backend says connected", () => {
    const line = hardwareLine(
      stateFrom({
        ...LIVE_PAYLOAD,
        hardware: { hardware_seen: true, hardware_connected: true, age_seconds: 0.4 },
      }),
    );
    expect(line.state).toBe("OK");
    expect(line.value).toBe("CONNECTED");
  });

  it("UNAVAILABLE when hardware status is absent — never NOT CONNECTED by default", () => {
    const line = hardwareLine(stateFrom({ ...LIVE_PAYLOAD, hardware: undefined }));
    expect(line.state).toBe("UNAVAILABLE");
    expect(line.value).toBe("--");
  });

  it("16 — MOCK is labelled SIMULATION, never PHYSICAL", () => {
    const line = modeLine(stateFrom(LIVE_PAYLOAD));
    expect(line.value).toBe("MOCK");
    expect(line.detail).toContain("SIMULATION");
    expect(line.detail).not.toContain("PHYSICAL");
    // And MOCK is not presented as a malfunction.
    expect(line.state).toBe("OK");
  });

  it("16b — LIVE is reported as the backend's own claim", () => {
    const line = modeLine(stateFrom({ ...LIVE_PAYLOAD, mode: "LIVE" }));
    expect(line.value).toBe("LIVE");
  });

  it("UNAVAILABLE when no mode was supplied", () => {
    expect(modeLine(stateFrom({ ...LIVE_PAYLOAD, mode: undefined })).state).toBe("UNAVAILABLE");
  });
});

// ---------------------------------------------------------------------------
// banner composition
// ---------------------------------------------------------------------------

describe("system health banner", () => {
  it("produces one line per system aspect, in order", () => {
    const lines = deriveSystemHealth(stateFrom(LIVE_PAYLOAD));
    expect(lines.map((l) => l.label)).toEqual([
      "Backend",
      "Digital Twin",
      "Telemetry",
      "Commands",
      "Hardware",
      "Mode",
    ]);
  });

  it("never reports a healthy aggregate when nothing has been measured", () => {
    const lines = deriveSystemHealth(IDLE);
    for (const line of lines) {
      expect(line.state, `${line.label} claimed a verdict with no data`).not.toBe("OK");
    }
  });

  it("shows the honest simulated picture: operational HMI, no hardware", () => {
    const lines = deriveSystemHealth(stateFrom(LIVE_PAYLOAD));
    const by = (label: string) => lines.find((l) => l.label === label);

    expect(by("Backend")?.value).toBe("ONLINE");
    expect(by("Digital Twin")?.value).toBe("ATTACHED");
    expect(by("Telemetry")?.value).toBe("HEALTHY");
    expect(by("Commands")?.value).toBe("READY");
    expect(by("Hardware")?.value).toBe("NOT CONNECTED");
    expect(by("Mode")?.value).toBe("MOCK");
  });
});
