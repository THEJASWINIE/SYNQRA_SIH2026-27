/**
 * Provider-to-store lifecycle tests — M4.
 *
 * Exercises the exact sequence `ProviderHost` performs — disconnect → reset → load →
 * connect — without React, so it is deterministic and needs no DOM. Virtual time comes
 * from `manualScheduler`; no test waits for real wall-clock time.
 *
 * These are the evidence for the M4 verification items: scenario switching resets state,
 * disconnect cancels activity, stale-feed stays CONNECTED while data ages,
 * communication-loss becomes DISCONNECTED, and recovery restores fresh presentation.
 */

import { beforeEach, describe, expect, it } from "vitest";
import { freshnessConfig } from "../config/freshness";
import type { ConnectionStatus } from "../contracts/appState";
import { MockDataProvider } from "../providers/MockDataProvider";
import { type ManualScheduler, manualScheduler } from "../providers/scheduler";
import { viewFreshness } from "./freshness";
import { AppStateStore } from "./store";

const BASE_MS = Date.parse("2026-01-01T00:00:00.000Z");
const STALE_AFTER_MS = 5000;
const CONFIG = freshnessConfig(STALE_AFTER_MS);

let scheduler: ManualScheduler;
let provider: MockDataProvider;
let store: AppStateStore;

function nowIso(): string {
  return new Date(BASE_MS + scheduler.nowMs()).toISOString();
}

function wire(): void {
  provider.subscribe((patch) => store.applyPatch(patch, nowIso()));
  provider.onStatusChange((status, error) => store.setStatus(status, error?.message ?? null));
}

/** The exact order `ProviderHost.switchTo` uses. */
async function switchTo(id: string): Promise<void> {
  await provider.disconnect();
  store.reset(nowIso());
  const loaded = provider.loadScenario(id);
  if (!loaded.ok) {
    store.setStatus("ERROR", loaded.error.message);
    return;
  }
  store.setScenarioName(id);
  await provider.connect();
}

beforeEach(() => {
  scheduler = manualScheduler(0);
  provider = new MockDataProvider({
    clock: () => BASE_MS + scheduler.nowMs(),
    scheduler,
  });
  store = new AppStateStore(nowIso());
  wire();
});

// ---------------------------------------------------------------------------

describe("scenario switching resets the previous scenario (verification 1)", () => {
  it("discards vehicles, alerts and bottlenecks from the previous mine", async () => {
    await switchTo("envelope-violation");
    scheduler.advance(3000);

    const populated = store.getSnapshot();
    expect(Object.keys(populated.vehicles).length).toBeGreaterThan(0);
    expect(populated.alerts.length).toBeGreaterThan(0);

    await switchTo("nominal");
    // Immediately after the switch, before the new scenario emits anything.
    const afterReset = store.getSnapshot();
    expect(afterReset.alerts).toHaveLength(0);
    expect(Object.keys(afterReset.vehicles)).toHaveLength(0);
    expect(afterReset.topology).toBeNull();
  });

  it("does not leak a bottleneck into a scenario that supplies none", async () => {
    await switchTo("fleet-density-high");
    scheduler.advance(3000);
    expect(Object.keys(store.getSnapshot().bottlenecks).length).toBeGreaterThan(0);

    await switchTo("nominal");
    scheduler.runAll();
    // Nominal supplies no BottleneckState. The panel must be honestly empty.
    expect(Object.keys(store.getSnapshot().bottlenecks)).toHaveLength(0);
  });

  it("an unknown scenario id becomes an ERROR status, not a silent no-op", async () => {
    await switchTo("no-such-scenario");
    expect(store.getSnapshot().connection.status).toBe("ERROR");
    expect(store.getSnapshot().connection.error).toContain("no-such-scenario");
  });
});

// ---------------------------------------------------------------------------

describe("disconnect cancels activity (verification 2)", () => {
  it("leaves no scheduled work outstanding", async () => {
    await switchTo("nominal");
    expect(scheduler.pendingCount()).toBeGreaterThan(0);
    await provider.disconnect();
    expect(scheduler.pendingCount()).toBe(0);
  });

  it("emits nothing after disconnect, however far time advances", async () => {
    await switchTo("nominal");
    scheduler.advance(1000);
    await provider.disconnect();

    const after = store.getSnapshot();
    scheduler.advance(60_000);
    // Only the clock could have moved, and only if something ticked it — nothing did.
    expect(store.getSnapshot()).toBe(after);
  });

  it("is idempotent", async () => {
    await switchTo("nominal");
    await provider.disconnect();
    await provider.disconnect();
    expect(store.getSnapshot().connection.status).toBe("DISCONNECTED");
  });
});

// ---------------------------------------------------------------------------

describe("stale-feed stays CONNECTED while data ages (verification 3)", () => {
  it("the link stays up after emission halts", async () => {
    await switchTo("stale-feed");
    scheduler.runAll();
    // The feed went silent; the pipe did not drop. These are different situations.
    expect(store.getSnapshot().connection.status).toBe("CONNECTED");
  });

  it("supplied data ages to STALE on its own, keeping its value", async () => {
    await switchTo("stale-feed");
    scheduler.advance(1000);

    const vehicleId = Object.keys(store.getSnapshot().vehicles)[0];
    expect(vehicleId).toBeDefined();
    const vehicle = store.getSnapshot().vehicles[vehicleId as string];
    expect(vehicle).toBeDefined();

    const whenFresh = viewFreshness(vehicle?.timestamp, CONFIG, BASE_MS + scheduler.nowMs());
    expect(whenFresh.quality).toBe("OK");

    // No new data arrives. Age advances with the clock — this is how NFR-012 degrades
    // rather than freezes, without any special case when a feed goes quiet.
    const later = viewFreshness(
      vehicle?.timestamp,
      CONFIG,
      BASE_MS + scheduler.nowMs() + STALE_AFTER_MS + 1,
    );
    expect(later.quality).toBe("STALE");
    // The value itself is untouched — stale means old, not absent.
    expect(store.getSnapshot().vehicles[vehicleId as string]).toBe(vehicle);
  });
});

// ---------------------------------------------------------------------------

describe("communication-loss becomes DISCONNECTED (verification 4)", () => {
  it("reports the link down with the supplied error", async () => {
    const seen: ConnectionStatus[] = [];
    provider.onStatusChange((status) => seen.push(status));

    await switchTo("communication-loss");
    scheduler.runAll();

    expect(store.getSnapshot().connection.status).toBe("DISCONNECTED");
    expect(store.getSnapshot().connection.error).toContain("link lost");
    expect(seen).toContain("DISCONNECTED");
  });

  it("retains the last supplied values rather than blanking the display", async () => {
    await switchTo("communication-loss");
    scheduler.runAll();
    expect(Object.keys(store.getSnapshot().vehicles).length).toBeGreaterThan(0);
  });

  it("is distinguishable from a silent feed on a live link", async () => {
    await switchTo("communication-loss");
    scheduler.runAll();
    const lost = store.getSnapshot().connection.status;

    await switchTo("stale-feed");
    scheduler.runAll();
    const silent = store.getSnapshot().connection.status;

    expect(lost).toBe("DISCONNECTED");
    expect(silent).toBe("CONNECTED");
    expect(lost).not.toBe(silent);
  });
});

// ---------------------------------------------------------------------------

describe("recovery restores current data (verification 5)", () => {
  it("returns to CONNECTED and delivers fresh values", async () => {
    await switchTo("disconnect-reconnect");

    scheduler.advance(2500);
    expect(store.getSnapshot().connection.status).toBe("DISCONNECTED");

    scheduler.advance(6500); // through RECONNECTING, CONNECTED and the 9 000 ms emission
    expect(store.getSnapshot().connection.status).toBe("CONNECTED");

    const vehicleId = Object.keys(store.getSnapshot().vehicles)[0] as string;
    const recovered = store.getSnapshot().vehicles[vehicleId];
    const view = viewFreshness(recovered?.timestamp, CONFIG, BASE_MS + scheduler.nowMs());
    expect(view.quality).toBe("OK");
  });

  it("post-recovery data still ages on its own", async () => {
    await switchTo("disconnect-reconnect");
    scheduler.runAll();

    const vehicleId = Object.keys(store.getSnapshot().vehicles)[0] as string;
    const recovered = store.getSnapshot().vehicles[vehicleId];
    const later = viewFreshness(
      recovered?.timestamp,
      CONFIG,
      BASE_MS + scheduler.nowMs() + STALE_AFTER_MS * 4,
    );
    expect(later.quality).toBe("STALE");
  });
});

// ---------------------------------------------------------------------------

describe("empty states are driven by the data, not by the UI (verifications 7, 8)", () => {
  it("nominal supplies no alerts and no bottlenecks", async () => {
    await switchTo("nominal");
    scheduler.runAll();
    const state = store.getSnapshot();
    expect(state.alerts).toHaveLength(0);
    expect(Object.keys(state.bottlenecks)).toHaveLength(0);
    // Yet it is a working scenario, not an empty one.
    expect(Object.keys(state.vehicles).length).toBeGreaterThan(0);
    expect(state.kpis).not.toBeNull();
  });

  it("alerts appear only from scenarios that supply them", async () => {
    await switchTo("envelope-violation");
    scheduler.runAll();
    expect(store.getSnapshot().alerts.length).toBeGreaterThan(0);
  });

  it("bottlenecks appear only from scenarios that supply them", async () => {
    await switchTo("fleet-density-high");
    scheduler.runAll();
    expect(Object.keys(store.getSnapshot().bottlenecks).length).toBeGreaterThan(0);
  });
});

// ---------------------------------------------------------------------------

describe("the provider assigns no quality (M3 rule, still true through the store)", () => {
  it("no patch carries a quality field into application state", async () => {
    await switchTo("stale-feed");
    scheduler.runAll();
    const serialized = JSON.stringify(store.getSnapshot());
    expect(serialized).not.toContain('"quality"');
  });
});
