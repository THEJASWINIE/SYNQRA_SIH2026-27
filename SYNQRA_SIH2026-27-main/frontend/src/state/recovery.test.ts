/**
 * NFR-004 availability / recovery coherence — M11.
 *
 * ==========================================================================
 *  `state/lifecycle.test.ts` (M4) already proves the RECOVERY ARC: the link
 *  drops, data ages, the link returns and fresh values arrive. What it never
 *  asserted is the other half of NFR-004's acceptance criterion — that after
 *  reconnection "no duplicated or incoherent entities" remain.
 *
 *  That is what this file adds, and only that. Nothing here re-tests the arc.
 *
 *  SCOPE LIMIT, STATED PLAINLY: this exercises the MOCK provider's authored
 *  disconnect/reconnect scenario. It is NOT evidence about a real transport,
 *  which does not exist yet (TECH-001, M12). What it does establish is that
 *  the store's merge semantics survive a reconnection without duplicating or
 *  corrupting state — a property of the HMI, independent of transport.
 * ==========================================================================
 */

import { beforeEach, describe, expect, it } from "vitest";
import { freshnessConfig } from "../config/freshness";
import type { AppState } from "../contracts/appState";
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

const nowIso = () => new Date(BASE_MS + scheduler.nowMs()).toISOString();
const nowMs = () => BASE_MS + scheduler.nowMs();

/** The exact order `ProviderHost.switchTo` uses. */
async function switchTo(id: string): Promise<void> {
  await provider.disconnect();
  store.reset(nowIso());
  const loaded = provider.loadScenario(id);
  expect(loaded.ok, `scenario ${id} must load`).toBe(true);
  store.setScenarioName(id);
  await provider.connect();
}

beforeEach(() => {
  scheduler = manualScheduler(0);
  provider = new MockDataProvider({ clock: nowMs, scheduler });
  store = new AppStateStore(nowIso());
  provider.subscribe((patch) => store.applyPatch(patch, nowIso()));
  provider.onStatusChange((status, error) => store.setStatus(status, error?.message ?? null));
});

/** Every keyed slice must key each entity by its own id, or the store has drifted. */
function assertKeysMatchIds(state: AppState): void {
  for (const [key, entity] of Object.entries(state.vehicles)) {
    expect(entity.vehicleId, `vehicles["${key}"] holds ${entity.vehicleId}`).toBe(key);
  }
  for (const [key, entity] of Object.entries(state.safety)) {
    expect(entity.vehicleId, `safety["${key}"] holds ${entity.vehicleId}`).toBe(key);
  }
  for (const [key, entity] of Object.entries(state.road)) {
    expect(entity.segmentId, `road["${key}"] holds ${entity.segmentId}`).toBe(key);
  }
}

// ---------------------------------------------------------------------------

describe("NFR-004 — no duplicated entities across a reconnection", () => {
  it("the fleet count is unchanged before and after recovery", async () => {
    await switchTo("disconnect-reconnect");

    scheduler.advance(1500); // first emission delivered, link still up
    const before = Object.keys(store.getSnapshot().vehicles).length;
    expect(before).toBeGreaterThan(0);

    scheduler.runAll(); // through the loss, the silence and the reconnection
    expect(store.getSnapshot().connection.status).toBe("CONNECTED");
    expect(Object.keys(store.getSnapshot().vehicles)).toHaveLength(before);
  });

  it("re-emitting a vehicle after reconnection updates it rather than adding a second", async () => {
    await switchTo("disconnect-reconnect");
    scheduler.advance(1500);
    const idsBefore = Object.keys(store.getSnapshot().vehicles).sort();

    scheduler.runAll();
    expect(Object.keys(store.getSnapshot().vehicles).sort()).toEqual(idsBefore);
  });

  it("every slice is still keyed by entity id after recovery", async () => {
    await switchTo("disconnect-reconnect");
    scheduler.runAll();
    assertKeysMatchIds(store.getSnapshot());
  });

  it("holds no duplicate alert id after recovery", async () => {
    await switchTo("disconnect-reconnect");
    scheduler.runAll();
    const ids = store.getSnapshot().alerts.map((a) => a.alertId);
    expect(new Set(ids).size).toBe(ids.length);
  });

  it("holds no duplicate event id after recovery", async () => {
    await switchTo("disconnect-reconnect");
    scheduler.runAll();
    const ids = store.getSnapshot().events.map((e) => e.eventId);
    expect(new Set(ids).size).toBe(ids.length);
  });
});

describe("NFR-004 — state is coherent after recovery", () => {
  it("every vehicle still has its matching safety state", async () => {
    await switchTo("disconnect-reconnect");
    scheduler.runAll();
    const state = store.getSnapshot();
    for (const vehicleId of Object.keys(state.vehicles)) {
      expect(state.safety[vehicleId], `safety missing for ${vehicleId}`).toBeDefined();
    }
  });

  it("the recovered timestamp is the post-reconnection one, not the pre-loss one", async () => {
    await switchTo("disconnect-reconnect");
    scheduler.advance(1500);
    const state = store.getSnapshot();
    const vehicleId = Object.keys(state.vehicles)[0] as string;
    const preLoss = state.vehicles[vehicleId]?.timestamp;

    scheduler.runAll();
    const recovered = store.getSnapshot().vehicles[vehicleId]?.timestamp;

    expect(recovered).toBeDefined();
    expect(Date.parse(recovered as string)).toBeGreaterThan(Date.parse(preLoss as string));
  });

  it("no value from before the loss is still presented as current after recovery", async () => {
    await switchTo("disconnect-reconnect");
    scheduler.advance(1500);
    const vehicleId = Object.keys(store.getSnapshot().vehicles)[0] as string;
    const preLoss = store.getSnapshot().vehicles[vehicleId]?.timestamp;

    scheduler.runAll();
    // The pre-loss datum, judged at the post-recovery clock, would read STALE. The value
    // actually held must not be that one — otherwise a stale reading is being shown as live.
    expect(viewFreshness(preLoss, CONFIG, nowMs()).quality).toBe("STALE");
    const held = store.getSnapshot().vehicles[vehicleId]?.timestamp;
    expect(viewFreshness(held, CONFIG, nowMs()).quality).toBe("OK");
  });

  it("recovery does not resurrect entities the reset removed", async () => {
    await switchTo("scale");
    scheduler.advance(2000);
    expect(Object.keys(store.getSnapshot().vehicles).length).toBeGreaterThan(20);

    await switchTo("disconnect-reconnect");
    scheduler.runAll();
    // The 50-vehicle mine must not bleed through the reconnection of a different scenario.
    expect(Object.keys(store.getSnapshot().vehicles).length).toBeLessThan(20);
  });
});
