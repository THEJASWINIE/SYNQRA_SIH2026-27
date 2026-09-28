/**
 * NFR-009 scale verification — M11.
 *
 * ==========================================================================
 *  THIS FILE RENDERS THE SCALE SCENARIO. IT DOES NOT ASSERT A TIME BUDGET.
 *
 *  NFR-009 requires that 50 vehicles and a 20-node topology "render correctly
 *  and remain interactive". Until M11 the scale scenario was only checked for
 *  its SHAPE (`mocks/scenarios.test.ts` test 20) — nothing had ever put it
 *  through the real screens. This closes that gap.
 *
 *  What is asserted here is CORRECTNESS AT SCALE: every entity present, every
 *  entity present exactly once, nothing silently dropped, and the screens still
 *  legible with colour stripped (NFR-008).
 *
 *  What is NOT asserted here is elapsed time. The NFR-001 threshold is an
 *  unfilled placeholder (AMB-004), so a timing assertion would have to invent
 *  the number the specification withholds. Measurement is reported instead, in
 *  `docs/verification/perf.md`.
 *
 *  The freshness threshold is left UNCONFIGURED (null) throughout, because
 *  AMB-014 leaves it unresolved and no scale claim should depend on a value
 *  this project is forbidden to choose.
 * ==========================================================================
 */

import type { ReactNode } from "react";
import { renderToString } from "react-dom/server";
import { describe, expect, it } from "vitest";
import type { AppState } from "../contracts/appState";
import { emptyAppState, mergePatch } from "../data/patch";
import type { Clock } from "../data/sourced";
import { MockDataProvider } from "../providers/MockDataProvider";
import { manualScheduler } from "../providers/scheduler";
import { Diagnostics } from "../screens/Diagnostics";
import { OperationsOverview } from "../screens/OperationsOverview";
import { freshnessOverview } from "./diagnostics";
import { HmiContext } from "./ProviderHost";
import { AppStateStore } from "./store";
import { testHmiContext } from "./testHmiContext";

const START_MS = Date.parse("2026-01-01T00:00:00.000Z");
const START_ISO = new Date(START_MS).toISOString();

/** Colour stripped before any state assertion — nothing may pass on colour alone. */
function greyscale(html: string): string {
  return html.replace(/color:[^;"]*;?/g, "").replace(/#[0-9a-fA-F]{3,8}/g, "");
}

/**
 * Play the authored `scale` scenario through the real provider into a real store.
 *
 * No fixture is hand-built here: the point of the exercise is that the SHIPPED scenario
 * reaches the SHIPPED screens through the SHIPPED merge path.
 */
async function playScale(advanceMs = 20_000): Promise<{ store: AppStateStore; state: AppState }> {
  const scheduler = manualScheduler(0);
  const clock: Clock = () => START_MS + scheduler.nowMs();
  const provider = new MockDataProvider({ clock, scheduler });

  const store = new AppStateStore(START_ISO);
  let state = emptyAppState(START_ISO);

  provider.subscribe((patch) => {
    state = mergePatch(state, patch);
    store.applyPatch(patch, new Date(START_MS + scheduler.nowMs()).toISOString());
  });

  const loaded = provider.loadScenario("scale");
  expect(loaded.ok, "the scale scenario must be registered").toBe(true);
  await provider.connect();
  scheduler.advance(advanceMs);
  provider.disconnect();

  return { store, state };
}

function mount(store: AppStateStore, node: ReactNode): string {
  const value = testHmiContext({ store, freshness: null });
  return renderToString(<HmiContext.Provider value={value}>{node}</HmiContext.Provider>);
}

/** Every `aria-label="Vehicle X"` in the markup, in document order. */
function vehicleLabels(html: string): string[] {
  return [...html.matchAll(/aria-label="Vehicle ([^"]+)"/g)].map((m) => m[1] as string);
}

const s1 = (store: AppStateStore) =>
  mount(store, <OperationsOverview onSelectVehicle={() => {}} />);

// ---------------------------------------------------------------------------

describe("NFR-009 — the store holds the full scale load", () => {
  it("carries 50 vehicles and a 20-node topology after playback", async () => {
    const { state } = await playScale();
    expect(Object.keys(state.vehicles)).toHaveLength(50);
    expect(state.topology, "no topology was supplied").not.toBeNull();
    expect(state.topology?.nodes).toHaveLength(20);
  });

  it("carries a safety state for every vehicle", async () => {
    const { state } = await playScale();
    expect(Object.keys(state.safety)).toHaveLength(50);
    for (const vehicleId of Object.keys(state.vehicles)) {
      expect(state.safety[vehicleId], `no SafetyState for ${vehicleId}`).toBeDefined();
    }
  });

  it("carries road state for every segment", async () => {
    const { state } = await playScale();
    expect(state.topology?.segments).toHaveLength(20);
    expect(Object.keys(state.road)).toHaveLength(20);
  });

  it("keys entities by id, so a repeated emission cannot duplicate one", async () => {
    const { state } = await playScale();
    const ids = Object.keys(state.vehicles);
    expect(new Set(ids).size).toBe(ids.length);
    for (const [key, vehicle] of Object.entries(state.vehicles)) {
      expect(vehicle.vehicleId, "store key must match the entity id").toBe(key);
    }
  });
});

describe("NFR-009 — S1 renders the full load", () => {
  it("renders one card per vehicle: 50 cards, no duplicate, no omission", async () => {
    const { store, state } = await playScale();
    const labels = vehicleLabels(greyscale(s1(store)));

    expect(labels).toHaveLength(50);
    expect(new Set(labels).size, "a vehicle was rendered twice").toBe(50);
    expect([...labels].sort()).toEqual(Object.keys(state.vehicles).sort());
  });

  it("renders cards in deterministic id order", async () => {
    const a = await playScale();
    const b = await playScale();
    const first = vehicleLabels(s1(a.store));
    const second = vehicleLabels(s1(b.store));
    expect(first).toEqual(second);
    expect(first).toEqual([...first].sort((x, y) => x.localeCompare(y)));
  });

  it("the map accounts for all 20 nodes and all 50 vehicles", async () => {
    const { store } = await playScale();
    const label =
      /aria-label="Mine map: (\d+) nodes, (\d+) vehicles placed, (\d+) position unavailable"/.exec(
        s1(store),
      );
    expect(label, "the map did not render its summary label").not.toBeNull();
    if (!label) return;

    const [, nodes, placed, unplaced] = label;
    expect(Number(nodes)).toBe(20);
    // Every vehicle is accounted for as either placed or explicitly unavailable —
    // silently dropping one at scale is the failure this asserts against.
    expect(Number(placed) + Number(unplaced)).toBe(50);
  });

  it("stays legible with colour stripped at scale (NFR-008)", async () => {
    const { store } = await playScale();
    const html = greyscale(s1(store));
    expect(html).toContain("Active alerts");
    expect(html).toContain("Mine map");
  });

  it("renders every vehicle id as readable text, not only as a label", async () => {
    const { store, state } = await playScale();
    const html = greyscale(s1(store));
    for (const vehicleId of Object.keys(state.vehicles)) {
      expect(html, `${vehicleId} missing from the rendered text`).toContain(vehicleId);
    }
  });
});

describe("NFR-009 — S6 accounts for the full load", () => {
  it("counts every held entity by message type", async () => {
    const { state } = await playScale();
    const overview = freshnessOverview(state, null, START_MS + 20_000);
    const row = (type: string) => overview.rows.find((r) => r.messageType === type);

    expect(row("VehicleState")?.count).toBe(50);
    expect(row("SafetyState")?.count).toBe(50);
    expect(row("RoadState")?.count).toBe(20);
  });

  it("reports no quality tally while the threshold is unconfigured, even at scale", async () => {
    const { state } = await playScale();
    const overview = freshnessOverview(state, null, START_MS + 20_000);
    expect(overview.thresholdConfigured).toBe(false);
    expect(overview.rows.every((r) => r.qualities === null)).toBe(true);
  });

  it("renders S6 against the scale load", async () => {
    const { store } = await playScale();
    const html = greyscale(mount(store, <Diagnostics />));
    expect(html).toContain("Data freshness by message type");
    expect(html).toContain("VehicleState");
  });
});
