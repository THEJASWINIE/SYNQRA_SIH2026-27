/**
 * AppStateStore tests — M4.
 * Covers store merge/reset, provider status, and the display ticker's scope boundary.
 */

import { describe, expect, it, vi } from "vitest";
import type { VehicleState } from "../contracts/domain";
import { AppStateStore } from "./store";

const T0 = "2026-01-01T00:00:00.000Z";
const T1 = "2026-01-01T00:00:05.000Z";

function vehicle(id: string, speedMps: number): VehicleState {
  return {
    vehicleId: id,
    timestamp: T0,
    position: { x: 10, y: 20, segmentId: "S-1", offsetM: null },
    speedMps,
    accelMps2: 0,
    gradeRad: 0,
    frictionEst: { value: 0.6, sigma: 0.04 },
    mode: "NORMAL",
    commConfidence: 1,
    vehicleKind: "TRUCK",
    routeId: null,
  };
}

describe("snapshot identity", () => {
  it("returns the same object until something changes", () => {
    const store = new AppStateStore(T0);
    expect(store.getSnapshot()).toBe(store.getSnapshot());
  });

  it("returns a new object after a patch, so useSyncExternalStore re-renders", () => {
    const store = new AppStateStore(T0);
    const before = store.getSnapshot();
    store.applyPatch({ changes: { vehicles: { "V-1": vehicle("V-1", 5) } } }, T0);
    expect(store.getSnapshot()).not.toBe(before);
  });

  it("notifies subscribers, and stops after unsubscribe", () => {
    const store = new AppStateStore(T0);
    const listener = vi.fn();
    const off = store.subscribe(listener);

    store.setStatus("CONNECTED", null);
    expect(listener).toHaveBeenCalledTimes(1);

    off();
    store.setStatus("DISCONNECTED", null);
    expect(listener).toHaveBeenCalledTimes(1);
  });
});

describe("patch application", () => {
  it("merges through the shared patch semantics", () => {
    const store = new AppStateStore(T0);
    store.applyPatch({ changes: { vehicles: { "V-1": vehicle("V-1", 5) } } }, T0);
    store.applyPatch({ changes: { vehicles: { "V-2": vehicle("V-2", 7) } } }, T1);

    // V-1 absent from the second patch means NO CHANGE, never "removed".
    expect(Object.keys(store.getSnapshot().vehicles).sort()).toEqual(["V-1", "V-2"]);
  });

  it("honours explicit deletions", () => {
    const store = new AppStateStore(T0);
    store.applyPatch(
      { changes: { vehicles: { "V-1": vehicle("V-1", 5), "V-2": vehicle("V-2", 7) } } },
      T0,
    );
    store.applyPatch({ changes: {}, deletions: { vehicles: ["V-1"] } }, T1);
    expect(Object.keys(store.getSnapshot().vehicles)).toEqual(["V-2"]);
  });

  it("records receipt time on the connection, not on any datum", () => {
    const store = new AppStateStore(T0);
    store.applyPatch({ changes: { vehicles: { "V-1": vehicle("V-1", 5) } } }, T1);
    const state = store.getSnapshot();
    expect(state.connection.lastMessageAt).toBe(T1);
    // The vehicle keeps the timestamp the SOURCE supplied.
    expect(state.vehicles["V-1"]?.timestamp).toBe(T0);
  });
});

describe("status and scenario", () => {
  it("records status and error text", () => {
    const store = new AppStateStore(T0);
    store.setStatus("ERROR", "no scenario loaded");
    expect(store.getSnapshot().connection.status).toBe("ERROR");
    expect(store.getSnapshot().connection.error).toBe("no scenario loaded");
  });

  it("records the active scenario name", () => {
    const store = new AppStateStore(T0);
    store.setScenarioName("Nominal operations");
    expect(store.getSnapshot().connection.scenarioName).toBe("Nominal operations");
  });
});

describe("reset — scenario switching must not leak the previous mine", () => {
  it("discards vehicles, alerts and bottlenecks", () => {
    const store = new AppStateStore(T0);
    store.applyPatch(
      {
        changes: {
          vehicles: { "V-1": vehicle("V-1", 5) },
          alerts: [
            {
              alertId: "A-1",
              timestamp: T0,
              severity: "CRITICAL",
              category: "UNSAFE_SPEED",
              origin: "TASK2",
              subject: { kind: "VEHICLE", id: "V-1" },
              message: "old scenario alert",
              reasonCode: null,
              acknowledgeable: true,
              acknowledged: null,
              active: true,
            },
          ],
        },
      },
      T0,
    );

    store.reset(T1);
    const state = store.getSnapshot();
    expect(Object.keys(state.vehicles)).toHaveLength(0);
    expect(state.alerts).toHaveLength(0);
    expect(state.topology).toBeNull();
    expect(state.kpis).toBeNull();
  });

  it("preserves provider identity — the provider did not change, the data did", () => {
    const store = new AppStateStore(T0);
    store.setStatus("CONNECTED", null);
    store.reset(T1);
    expect(store.getSnapshot().connection.provider).toBe("MOCK");
    expect(store.getSnapshot().connection.status).toBe("IDLE");
  });
});

describe("display ticker — presentation only", () => {
  it("advances the render clock", () => {
    const store = new AppStateStore(T0);
    store.tick(T1);
    expect(store.getSnapshot().clock.now).toBe(T1);
  });

  it("touches NO operational value", () => {
    const store = new AppStateStore(T0);
    store.applyPatch({ changes: { vehicles: { "V-1": vehicle("V-1", 5) } } }, T0);
    const before = store.getSnapshot();

    store.tick(T1);
    const after = store.getSnapshot();

    // The vehicle object is unchanged by reference: nothing moved, nothing decayed,
    // nothing was interpolated. A ticker that altered a datum would be a simulation.
    expect(after.vehicles["V-1"]).toBe(before.vehicles["V-1"]);
    expect(after.vehicles["V-1"]?.speedMps).toBe(5);
    expect(after.vehicles["V-1"]?.position).toEqual(before.vehicles["V-1"]?.position);
  });

  it("is a no-op when the clock has not moved", () => {
    const store = new AppStateStore(T0);
    const before = store.getSnapshot();
    store.tick(T0);
    expect(store.getSnapshot()).toBe(before);
  });
});
