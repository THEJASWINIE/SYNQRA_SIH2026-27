/**
 * Phase 4 — observability normalization, transport and shared-state semantics.
 *
 * THE PAYLOAD BELOW WAS CAPTURED FROM THE RUNNING BACKEND, not invented.
 * Pure logic only: no DOM, no jsdom, no Testing Library (M4D-C).
 */

import { describe, expect, it, vi } from "vitest";

import { AppStateStore } from "../state/store";
import { fetchObservability, normalizeObservability } from "./observabilityClient";

/** Verbatim `GET /api/observability` response from the live backend. */
const LIVE_PAYLOAD = {
  service: "hmi-backend",
  timestamp: 1_788_665_982.04608,
  twin_attached: true,
  twin_vehicle_count: 0,
  telemetry_ingest: {
    accepted: 0,
    duplicate: 0,
    out_of_order: 0,
    invalid: 0,
    unknown_vehicle: 0,
  },
  command_gateway: {
    accepted: 5,
    rejected: 6,
    duplicate: 1,
    stale: 0,
    unknown_vehicle: 2,
    invalid: 0,
    unsafe: 3,
    timeout: 0,
  },
  backend_cache_vehicles: 0,
  websocket_clients: 0,
  command_history_length: 11,
  hardware: { hardware_seen: false, hardware_connected: false, age_seconds: null },
  mode: "MOCK",
};

const T0 = "2026-01-01T00:00:00.000Z";
const T1 = "2026-01-01T00:00:05.000Z";

function jsonResponse(status: number, body: unknown): Response {
  return {
    ok: status >= 200 && status < 300,
    status,
    json: async () => body,
  } as unknown as Response;
}

function stubFetch(response: Response) {
  return vi.fn(async () => response) as unknown as typeof fetch;
}

// ---------------------------------------------------------------------------
// 1/2/3/4/5/15/16 — normalization
// ---------------------------------------------------------------------------

describe("observability normalization", () => {
  it("1/2 — parses the real response and maps every counter", () => {
    const snapshot = normalizeObservability(LIVE_PAYLOAD);
    expect(snapshot).not.toBeNull();
    if (snapshot === null) return;

    expect(snapshot.service).toBe("hmi-backend");
    expect(snapshot.timestamp).toBe(1_788_665_982.04608);
    expect(snapshot.twinAttached).toBe(true);
    expect(snapshot.twinVehicleCount).toBe(0);
    expect(snapshot.backendCacheVehicles).toBe(0);
    expect(snapshot.websocketClients).toBe(0);
    expect(snapshot.commandHistoryLength).toBe(11);
    expect(snapshot.mode).toBe("MOCK");

    expect(snapshot.telemetryIngest).toEqual({
      accepted: 0,
      duplicate: 0,
      outOfOrder: 0,
      invalid: 0,
      unknownVehicle: 0,
    });
    expect(snapshot.commandGateway).toEqual({
      accepted: 5,
      rejected: 6,
      duplicate: 1,
      stale: 0,
      unknownVehicle: 2,
      invalid: 0,
      unsafe: 3,
      timeout: 0,
    });
  });

  it("3 — a zero counter stays zero, and is not confused with unavailable", () => {
    const snapshot = normalizeObservability(LIVE_PAYLOAD);
    expect(snapshot?.telemetryIngest?.accepted).toBe(0);
    expect(snapshot?.telemetryIngest?.accepted).not.toBeNull();
    expect(snapshot?.commandGateway?.timeout).toBe(0);
  });

  it("4 — a MISSING counter stays null, never becomes 0", () => {
    const partial = {
      ...LIVE_PAYLOAD,
      telemetry_ingest: { accepted: 7 }, // the rest are absent
      twin_vehicle_count: undefined,
    };
    const snapshot = normalizeObservability(partial);

    expect(snapshot?.telemetryIngest?.accepted).toBe(7);
    expect(snapshot?.telemetryIngest?.duplicate).toBeNull();
    expect(snapshot?.telemetryIngest?.duplicate).not.toBe(0);
    expect(snapshot?.twinVehicleCount).toBeNull();
  });

  it("4b — an absent block is null, distinct from a block of zeros", () => {
    const snapshot = normalizeObservability({ service: "hmi-backend", mode: "MOCK" });

    expect(snapshot?.telemetryIngest).toBeNull();
    expect(snapshot?.commandGateway).toBeNull();
    expect(snapshot?.hardware).toBeNull();
  });

  it("rejects a non-numeric or non-finite counter rather than coercing it", () => {
    const snapshot = normalizeObservability({
      ...LIVE_PAYLOAD,
      telemetry_ingest: { accepted: "12", duplicate: Number.NaN, invalid: null },
    });
    expect(snapshot?.telemetryIngest?.accepted).toBeNull();
    expect(snapshot?.telemetryIngest?.duplicate).toBeNull();
    expect(snapshot?.telemetryIngest?.invalid).toBeNull();
  });

  it.each([
    ["null", null],
    ["a string", "nope"],
    ["a number", 5],
    ["an array", [1, 2]],
  ])("5 — malformed payload (%s) is rejected safely", (_label, raw) => {
    expect(() => normalizeObservability(raw)).not.toThrow();
    expect(normalizeObservability(raw)).toBeNull();
  });

  it("15/16 — hardware and mode semantics are preserved, never inferred", () => {
    const snapshot = normalizeObservability(LIVE_PAYLOAD);
    // The backend was reachable, yet no hardware is claimed.
    expect(snapshot?.hardware?.hardwareSeen).toBe(false);
    expect(snapshot?.hardware?.hardwareConnected).toBe(false);
    expect(snapshot?.hardware?.ageSeconds).toBeNull();
    // MOCK mode must not be read as physical hardware.
    expect(snapshot?.mode).toBe("MOCK");
    expect(snapshot?.hardware?.hardwareConnected).not.toBe(true);
  });

  it("15b — seen and connected stay independent", () => {
    const snapshot = normalizeObservability({
      ...LIVE_PAYLOAD,
      hardware: { hardware_seen: true, hardware_connected: false, age_seconds: 42.5 },
      mode: "MOCK",
    });
    expect(snapshot?.hardware?.hardwareSeen).toBe(true);
    expect(snapshot?.hardware?.hardwareConnected).toBe(false);
    expect(snapshot?.hardware?.ageSeconds).toBe(42.5);
  });
});

// ---------------------------------------------------------------------------
// 6/7 — transport
// ---------------------------------------------------------------------------

describe("observability transport", () => {
  it("returns a snapshot on success", async () => {
    const result = await fetchObservability({
      fetchImpl: stubFetch(jsonResponse(200, LIVE_PAYLOAD)),
    });
    expect(result.kind).toBe("ok");
    expect(result.kind === "ok" && result.snapshot.commandHistoryLength).toBe(11);
  });

  it("requests the observability endpoint exactly once per call", async () => {
    const fetchImpl = stubFetch(jsonResponse(200, LIVE_PAYLOAD));
    await fetchObservability({ fetchImpl });
    const mock = fetchImpl as unknown as ReturnType<typeof vi.fn>;
    expect(mock.mock.calls).toHaveLength(1);
    expect(String(mock.mock.calls[0]?.[0])).toContain("/api/observability");
  });

  it("6 — an HTTP error is reported, not thrown", async () => {
    const result = await fetchObservability({ fetchImpl: stubFetch(jsonResponse(503, {})) });
    expect(result.kind).toBe("error");
    expect(result.kind === "error" && result.httpStatus).toBe(503);
  });

  it("7 — a network failure is reported, not thrown", async () => {
    const fetchImpl = vi.fn(async () => {
      throw new Error("Failed to fetch");
    }) as unknown as typeof fetch;

    const result = await fetchObservability({ fetchImpl });
    expect(result.kind).toBe("error");
    expect(result.kind === "error" && result.message).toContain("Failed to fetch");
    expect(result.kind === "error" && result.httpStatus).toBeNull();
  });

  it("5b — a malformed success body is an error, not a blank snapshot", async () => {
    const result = await fetchObservability({ fetchImpl: stubFetch(jsonResponse(200, "nope")) });
    expect(result.kind).toBe("error");
  });

  it("handles a body that is not JSON", async () => {
    const fetchImpl = stubFetch({
      ok: true,
      status: 200,
      json: async () => {
        throw new Error("not json");
      },
    } as unknown as Response);

    const result = await fetchObservability({ fetchImpl });
    expect(result.kind).toBe("error");
    expect(result.kind === "error" && result.message).toContain("not valid JSON");
  });
});

// ---------------------------------------------------------------------------
// 8/9/10/13/14 — shared state semantics
// ---------------------------------------------------------------------------

describe("observability in shared state", () => {
  function storeWithSnapshot() {
    const store = new AppStateStore(T0);
    const snapshot = normalizeObservability(LIVE_PAYLOAD);
    if (snapshot === null) throw new Error("fixture did not normalize");
    store.setObservability({ kind: "ok", snapshot }, T0);
    return store;
  }

  it("starts IDLE with no data — not zeroed", () => {
    const state = new AppStateStore(T0).getSnapshot().observability;
    expect(state.status).toBe("IDLE");
    expect(state.data).toBeNull();
    expect(state.fetchedAt).toBeNull();
    expect(state.error).toBeNull();
  });

  it("10 — a successful fetch becomes CURRENT with a timestamp", () => {
    const state = storeWithSnapshot().getSnapshot().observability;
    expect(state.status).toBe("CURRENT");
    expect(state.data?.commandHistoryLength).toBe(11);
    expect(state.fetchedAt).toBe(T0);
    expect(state.error).toBeNull();
  });

  it("8/9 — a failure keeps the last good snapshot and marks it STALE", () => {
    const store = storeWithSnapshot();
    store.setObservability({ kind: "error", message: "backend unreachable", httpStatus: null }, T1);

    const state = store.getSnapshot().observability;
    expect(state.status).toBe("STALE");
    // The counters are NOT blanked to zero.
    expect(state.data?.commandGateway?.accepted).toBe(5);
    expect(state.error).toBe("backend unreachable");
    // `fetchedAt` still refers to the last SUCCESS, so age stays honest.
    expect(state.fetchedAt).toBe(T0);
  });

  it("9b — a failure before any success is ERROR, with no invented data", () => {
    const store = new AppStateStore(T0);
    store.setObservability({ kind: "error", message: "connection refused", httpStatus: null }, T0);

    const state = store.getSnapshot().observability;
    expect(state.status).toBe("ERROR");
    expect(state.data).toBeNull();
  });

  it("10b — a later success restores CURRENT and clears the error", () => {
    const store = storeWithSnapshot();
    store.setObservability({ kind: "error", message: "blip", httpStatus: null }, T1);
    expect(store.getSnapshot().observability.status).toBe("STALE");

    const snapshot = normalizeObservability({ ...LIVE_PAYLOAD, command_history_length: 12 });
    if (snapshot === null) throw new Error("fixture did not normalize");
    store.setObservability({ kind: "ok", snapshot }, T1);

    const state = store.getSnapshot().observability;
    expect(state.status).toBe("CURRENT");
    expect(state.error).toBeNull();
    expect(state.data?.commandHistoryLength).toBe(12);
  });

  it("13 — observability counters do not become command history", () => {
    const state = storeWithSnapshot().getSnapshot();

    // The gateway reports 5 accepted and an 11-long backend history...
    expect(state.observability.data?.commandGateway?.accepted).toBe(5);
    expect(state.observability.data?.commandHistoryLength).toBe(11);
    // ...yet the HMI's own command log is untouched by metrics.
    expect(state.commands).toEqual([]);
  });

  it("14 — observability does not become vehicle state", () => {
    const store = new AppStateStore(T0);
    const snapshot = normalizeObservability({ ...LIVE_PAYLOAD, twin_vehicle_count: 2 });
    if (snapshot === null) throw new Error("fixture did not normalize");
    store.setObservability({ kind: "ok", snapshot }, T0);

    const state = store.getSnapshot();
    // A count of 2 is a metric; it creates no vehicles.
    expect(state.observability.data?.twinVehicleCount).toBe(2);
    expect(Object.keys(state.vehicles)).toEqual([]);
  });

  it("does not disturb any other slice", () => {
    const store = new AppStateStore(T0);
    const before = store.getSnapshot();
    const snapshot = normalizeObservability(LIVE_PAYLOAD);
    if (snapshot === null) throw new Error("fixture did not normalize");
    store.setObservability({ kind: "ok", snapshot }, T0);
    const after = store.getSnapshot();

    expect(after.vehicles).toBe(before.vehicles);
    expect(after.commands).toBe(before.commands);
    expect(after.alerts).toBe(before.alerts);
  });
});
