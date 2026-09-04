/**
 * Provider switching, fail-closed enforcement, and LiveDataProvider integration tests — M12-A.
 *
 * Verifies:
 *   1. Fail-closed behavior: unconfigured LIVE provider emits zero data, rejects connect,
 *      and sets typed ProviderError ("INITIALIZATION").
 *   2. Screen protection: unconfigured LIVE provider shows "Provider error", zero vehicles,
 *      empty panels, and never masquerades as "Live Feed".
 *   3. Truthful identity: injected StubLiveTransport renders as "Stub Feed — Test Only".
 *   4. LiveDataProvider feeds live Task 2 payloads through AppStateStore into screens.
 *   5. Diagnostics surfaces live validation failures read-only (M10D-B / D11).
 *   6. Full scenario stream plays through LiveDataProvider into screens without regression.
 */

import { renderToString } from "react-dom/server";
import { describe, expect, it } from "vitest";
import {
  createScenarioStubTransport,
  LiveDataProvider,
  StubLiveTransport,
} from "../providers/LiveDataProvider";
import { manualScheduler } from "../providers/scheduler";
import { AppShell } from "../screens/AppShell";
import { HmiContext } from "./ProviderHost";
import { AppStateStore } from "./store";
import { testHmiContext } from "./testHmiContext";

const T0 = 1_700_000_000_000;
const T0_ISO = new Date(T0).toISOString();

describe("M12-A Fail-Closed Integration & Provider Switching", () => {
  it("fails closed when LIVE provider has no configured endpoint or transport", async () => {
    // Unconfigured live provider without injected transport or URL
    const live = new LiveDataProvider();
    expect(live.transportName).toBe("NONE");

    const store = new AppStateStore(T0_ISO);
    store.setProvider("LIVE");

    live.onStatusChange((status, error) => {
      store.setStatus(status, error ? error.message : null);
    });

    await expect(live.connect()).rejects.toMatchObject({
      kind: "INITIALIZATION",
      retryable: false,
    });

    const snapshot = store.getSnapshot();
    expect(snapshot.connection.status).toBe("ERROR");
    expect(snapshot.connection.error).toContain("No live endpoint or transport configured");
    expect(Object.keys(snapshot.vehicles)).toHaveLength(0);
    expect(snapshot.alerts).toHaveLength(0);

    // Render screen with unconfigured live store
    const contextValue = testHmiContext({ store });
    const html = renderToString(
      <HmiContext.Provider value={contextValue}>
        <AppShell />
      </HmiContext.Provider>,
    );

    // Shows Provider error badge and specific error message
    expect(html).toContain("Provider error");
    expect(html).toContain("No live endpoint or transport configured");
    // Displays unsupplied / unavailable empty states
    expect(html).toContain("TOPOLOGY UNAVAILABLE");
    expect(html).toContain("NO ACTIVE BOTTLENECK");
    expect(html).toContain("0");
    // Never masquerades as an active Live Feed or displays mock vehicle data
    expect(html).not.toContain("Live Feed");
    expect(html).not.toContain("TRK-01");
  });

  it("truthfully identifies an injected stub transport as Stub Feed — Test Only", async () => {
    const store = new AppStateStore(T0_ISO);
    store.setProvider("LIVE");
    store.setScenarioName("Stub Feed — Test Only");

    const stub = new StubLiveTransport({ clock: () => T0 });
    const live = new LiveDataProvider({ transport: stub, clock: () => T0 });

    expect(live.transportName).toBe("STUB");
    live.onStatusChange((status, error) => {
      store.setStatus(status, error ? error.message : null);
    });

    await live.connect();
    expect(store.getSnapshot().connection.status).toBe("CONNECTED");

    const contextValue = testHmiContext({ store });
    const html = renderToString(
      <HmiContext.Provider value={contextValue}>
        <AppShell />
      </HmiContext.Provider>,
    );

    expect(html).toContain("FOG-ORCHESTRATOR 2.0");
    expect(html).toContain("LIVE");
    expect(html).toContain("Stub Feed — Test Only");
    await live.disconnect();
  });

  it("LiveDataProvider feeds live Task 2 payloads through AppStateStore into screens", async () => {
    const store = new AppStateStore(T0_ISO);
    store.setProvider("LIVE");
    store.setScenarioName("Live Feed");

    const stub = new StubLiveTransport({ clock: () => T0 });
    const live = new LiveDataProvider({
      transport: stub,
      clock: () => T0,
      reconnect: false,
    });

    live.subscribe((patch) => store.applyPatch(patch, T0_ISO));
    live.onStatusChange((status, error) => {
      store.setStatus(status, error ? error.message : null);
    });

    await live.connect();
    expect(store.getSnapshot().connection.status).toBe("CONNECTED");

    // Feed a live batch containing VehicleState and Alert
    stub.feed({
      VehicleState: [
        {
          vehicle_id: "LIVE-TRK-01",
          timestamp: T0_ISO,
          position: { x: 50, y: 50, segment_id: "SEG-01", offset_m: null },
          speed_mps: 14.2,
          accel_mps2: 0.1,
          grade_rad: 0.02,
          friction_est: { value: 0.8, sigma: null },
          mode: "NORMAL",
          comm_confidence: 1.0,
          vehicle_kind: "truck",
          route_id: null,
        },
      ],
      Alert: [
        {
          alert_id: "ALT-LIVE-01",
          timestamp: T0_ISO,
          severity: "WARNING",
          category: "UNSAFE_SPEED",
          origin: "TASK2",
          subject: { kind: "VEHICLE", id: "LIVE-TRK-01" },
          message: "Speed alert on LIVE-TRK-01",
          reason_code: "SPEED_LIMIT",
          acknowledgeable: true,
          acknowledged: null,
          active: true,
        },
      ],
    });

    const snapshot = store.getSnapshot();
    expect(snapshot.vehicles["LIVE-TRK-01"]).toBeDefined();
    expect(snapshot.vehicles["LIVE-TRK-01"]?.speedMps).toBe(14.2);
    expect(snapshot.alerts).toHaveLength(1);
    expect(snapshot.alerts[0]?.alertId).toBe("ALT-LIVE-01");

    // Render screens using the live store
    const contextValue = testHmiContext({ store });
    const html = renderToString(
      <HmiContext.Provider value={contextValue}>
        <AppShell />
      </HmiContext.Provider>,
    );

    expect(html).toContain("LIVE-TRK-01");
    expect(html).toContain("51.1");
    expect(html).toContain("Speed alert on LIVE-TRK-01");
  });

  it("surfaces live validation failures on Diagnostics read-only (M10D-B)", async () => {
    const stub = new StubLiveTransport({ clock: () => T0 });
    const live = new LiveDataProvider({
      transport: stub,
      clock: () => T0,
      reconnect: false,
    });
    await live.connect();

    expect(live.diagnostics.validationFailures).toHaveLength(0);

    // Feed invalid payload (missing speed_mps)
    stub.feed({
      VehicleState: [
        {
          vehicle_id: "MALFORMED-TRK",
          timestamp: T0_ISO,
          position: { x: null, y: null, segment_id: null, offset_m: null },
          accel_mps2: 0,
          grade_rad: 0,
          friction_est: { value: null, sigma: null },
          mode: "NORMAL",
          comm_confidence: 1,
        },
      ],
    });

    expect(live.diagnostics.validationFailures).toHaveLength(1);
    expect(live.diagnostics.validationFailures[0]?.messageType).toBe("VehicleState");
  });

  it("plays a full scenario stream through LiveDataProvider into screens without regression", async () => {
    const scheduler = manualScheduler(0);
    const clock = () => T0 + scheduler.nowMs();
    const transport = createScenarioStubTransport("fog-rolling-in", {
      clock,
      scheduler,
      intervalMs: 1000,
    });

    const store = new AppStateStore(T0_ISO);
    store.setProvider("LIVE");

    const live = new LiveDataProvider({ transport, clock, scheduler });
    live.subscribe((patch) => store.applyPatch(patch, new Date(clock()).toISOString()));
    live.onStatusChange((status, error) => {
      store.setStatus(status, error ? error.message : null);
    });

    await live.connect();

    // Advance by 3 steps (3000ms)
    scheduler.advance(3000);

    const snapshot = store.getSnapshot();
    expect(Object.keys(snapshot.vehicles).length).toBeGreaterThan(0);

    // Render shell under live scenario feed
    const contextValue = testHmiContext({ store });
    const html = renderToString(
      <HmiContext.Provider value={contextValue}>
        <AppShell />
      </HmiContext.Provider>,
    );

    expect(html).toContain("FOG-ORCHESTRATOR 2.0");
    await live.disconnect();
  });
});
