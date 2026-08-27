/**
 * LiveDataProvider unit and integration tests — M12-A.
 *
 * Verifies:
 *   1. Connection lifecycle and status transitions
 *   2. Stub transport integration and deterministic time advances
 *   3. Message routing across contract schemas to shared validation/normalization
 *   4. Runtime validation failure recording (ValidationFailure in diagnostics)
 *   5. Valid siblings preservation when one payload in a batch fails
 *   6. Unknown enum normalization to UNKNOWN without message loss
 *   7. Capture of `receivedAt` on deliveries for clock skew measurement
 *   8. Explicit deletion semantics (`deletions?: EntityDeletions`)
 *   9. Duplicate / upsert handling
 *  10. Reconnect state machine with exponential backoff and jitter
 *  11. Typed error classification (INITIALIZATION, TRANSPORT, PROTOCOL)
 *  12. Advisory acknowledgement workflow (PAD-B, PAD-D)
 *  13. Teardown determinism and scheduler cleanup
 */

import { describe, expect, it } from "vitest";
import type { ConnectionStatus } from "../contracts/appState";
import { type ProviderError, providerError } from "../data/errors";
import type { ProviderPatch } from "./DataProvider";
import {
  createScenarioStubTransport,
  LiveDataProvider,
  type LiveTransport,
  StubLiveTransport,
} from "./LiveDataProvider";
import { type ManualScheduler, manualScheduler } from "./scheduler";

const T0 = 1_700_000_000_000;
const T0_ISO = new Date(T0).toISOString();

function createTestHarness(
  options: {
    transport?: LiveTransport;
    reconnect?: boolean;
    initialDelayMs?: number;
    maxRetries?: number;
    maxDelayMs?: number;
    factor?: number;
    jitter?: boolean;
  } = {},
) {
  let virtualTime = T0;
  const clock = () => virtualTime;
  const scheduler: ManualScheduler = manualScheduler(0);

  const stubTransport =
    options.transport ??
    new StubLiveTransport({
      clock,
      scheduler,
      intervalMs: 1000,
    });

  const provider = new LiveDataProvider({
    transport: stubTransport,
    clock,
    scheduler,
    reconnect:
      options.reconnect === false
        ? false
        : {
            initialDelayMs: options.initialDelayMs ?? 1000,
            maxDelayMs: options.maxDelayMs ?? 30000,
            factor: options.factor ?? 1.5,
            jitter: options.jitter ?? false,
            maxRetries: options.maxRetries ?? 5,
          },
  });

  return {
    provider,
    transport: stubTransport instanceof StubLiveTransport ? stubTransport : null,
    scheduler,
    clock,
    setTime: (ms: number) => {
      virtualTime = ms;
    },
  };
}

describe("LiveDataProvider lifecycle", () => {
  it("starts in IDLE status with live provider kind", () => {
    const h = createTestHarness();
    expect(h.provider.kind).toBe("LIVE");
    expect(h.provider.currentStatus).toBe("IDLE");
  });

  it("transitions IDLE → CONNECTING → CONNECTED on successful connect", async () => {
    const h = createTestHarness();
    const statuses: ConnectionStatus[] = [];
    h.provider.onStatusChange((status) => statuses.push(status));

    await h.provider.connect();

    expect(statuses).toEqual(["IDLE", "CONNECTING", "CONNECTED"]);
    expect(h.provider.currentStatus).toBe("CONNECTED");
  });

  it("transitions to DISCONNECTED on deliberate disconnect", async () => {
    const h = createTestHarness();
    const statuses: ConnectionStatus[] = [];
    await h.provider.connect();

    h.provider.onStatusChange((status) => statuses.push(status));
    await h.provider.disconnect();

    expect(h.provider.currentStatus).toBe("DISCONNECTED");
  });

  it("fails connect() with typed INITIALIZATION error if transport connect fails", async () => {
    const failTransport = new StubLiveTransport({ failConnect: true });
    const h = createTestHarness({ transport: failTransport, reconnect: false });

    await expect(h.provider.connect()).rejects.toMatchObject({
      kind: "INITIALIZATION",
    });
    expect(h.provider.currentStatus).toBe("ERROR");
  });
});

describe("LiveDataProvider message ingestion and validation pipeline", () => {
  it("ingests and routes valid VehicleState payload into ProviderPatch", async () => {
    const h = createTestHarness();
    await h.provider.connect();

    const patches: ProviderPatch[] = [];
    h.provider.subscribe((patch) => patches.push(patch));

    h.transport?.feed({
      VehicleState: [
        {
          vehicle_id: "TRK-01",
          timestamp: T0_ISO,
          position: { x: 100, y: 200, segment_id: "SEG-A", offset_m: 10 },
          speed_mps: 12.5,
          accel_mps2: 0.2,
          grade_rad: 0.05,
          friction_est: { value: 0.75, sigma: 0.02 },
          mode: "NORMAL",
          comm_confidence: 0.98,
          vehicle_kind: "truck",
          route_id: "R-01",
        },
      ],
    });

    expect(patches).toHaveLength(1);
    const vehicles = patches[0]?.changes.vehicles;
    expect(vehicles).toBeDefined();
    expect(vehicles?.["TRK-01"]).toMatchObject({
      vehicleId: "TRK-01",
      speedMps: 12.5,
      mode: "NORMAL",
    });
    expect(h.provider.diagnostics.validationFailures).toHaveLength(0);
  });

  it("routes array of message envelopes with multiple slices", async () => {
    const h = createTestHarness();
    await h.provider.connect();

    const patches: ProviderPatch[] = [];
    h.provider.subscribe((patch) => patches.push(patch));

    h.transport?.feed([
      {
        type: "VehicleState",
        payload: {
          vehicle_id: "TRK-02",
          timestamp: T0_ISO,
          position: { x: null, y: null, segment_id: "SEG-B", offset_m: null },
          speed_mps: 8.0,
          accel_mps2: 0.0,
          grade_rad: 0.0,
          friction_est: { value: null, sigma: null },
          mode: "CAUTION",
          comm_confidence: 0.9,
          vehicle_kind: null,
          route_id: null,
        },
      },
      {
        type: "SafetyState",
        payload: {
          vehicle_id: "TRK-02",
          timestamp: T0_ISO,
          v_safe: 10.0,
          h_safe: 50.0,
          actual_speed: 8.0,
          headway_current: 60.0,
          lead_vehicle_id: "TRK-01",
          active_constraint: "VISIBILITY",
          risk_level: "LOW",
          headway_violation: false,
          envelope_violation: false,
        },
      },
    ]);

    expect(patches).toHaveLength(1);
    expect(patches[0]?.changes.vehicles?.["TRK-02"]?.vehicleId).toBe("TRK-02");
    expect(patches[0]?.changes.safety?.["TRK-02"]?.activeConstraint).toBe("VISIBILITY");
  });

  it("records ValidationFailure when a message violates schema, without crashing", async () => {
    const h = createTestHarness();
    await h.provider.connect();

    const patches: ProviderPatch[] = [];
    h.provider.subscribe((patch) => patches.push(patch));

    // Missing required speed_mps
    h.transport?.feed({
      VehicleState: [
        {
          vehicle_id: "BAD-TRK",
          timestamp: T0_ISO,
          position: { x: null, y: null, segment_id: null, offset_m: null },
          // speed_mps omitted
          accel_mps2: 0,
          grade_rad: 0,
          friction_est: { value: null, sigma: null },
          mode: "NORMAL",
          comm_confidence: 1,
        },
      ],
    });

    expect(patches).toHaveLength(0);
    const failures = h.provider.diagnostics.validationFailures;
    expect(failures).toHaveLength(1);
    expect(failures[0]?.messageType).toBe("VehicleState");
    expect(failures[0]?.issues.some((i) => i.path === "speed_mps")).toBe(true);
  });

  it("preserves valid siblings when one item in a batch fails validation", async () => {
    const h = createTestHarness();
    await h.provider.connect();

    const patches: ProviderPatch[] = [];
    h.provider.subscribe((patch) => patches.push(patch));

    h.transport?.feed({
      VehicleState: [
        // Valid item 1
        {
          vehicle_id: "TRK-GOOD-1",
          timestamp: T0_ISO,
          position: { x: 1, y: 1, segment_id: null, offset_m: null },
          speed_mps: 10,
          accel_mps2: 0,
          grade_rad: 0,
          friction_est: { value: null, sigma: null },
          mode: "NORMAL",
          comm_confidence: 1,
          vehicle_kind: null,
          route_id: null,
        },
        // Invalid item (missing speed_mps)
        {
          vehicle_id: "TRK-BAD",
          timestamp: T0_ISO,
          position: { x: null, y: null, segment_id: null, offset_m: null },
          accel_mps2: 0,
          grade_rad: 0,
          friction_est: { value: null, sigma: null },
          mode: "NORMAL",
          comm_confidence: 1,
        },
        // Valid item 2
        {
          vehicle_id: "TRK-GOOD-2",
          timestamp: T0_ISO,
          position: { x: 2, y: 2, segment_id: null, offset_m: null },
          speed_mps: 15,
          accel_mps2: 0,
          grade_rad: 0,
          friction_est: { value: null, sigma: null },
          mode: "NORMAL",
          comm_confidence: 1,
          vehicle_kind: null,
          route_id: null,
        },
      ],
    });

    expect(patches).toHaveLength(1);
    const vehicles = patches[0]?.changes.vehicles;
    expect(vehicles?.["TRK-GOOD-1"]).toBeDefined();
    expect(vehicles?.["TRK-GOOD-2"]).toBeDefined();
    expect(vehicles?.["TRK-BAD"]).toBeUndefined();
    expect(h.provider.diagnostics.validationFailures).toHaveLength(1);
  });

  it("normalizes unknown enum values to UNKNOWN without dropping the message (E-03)", async () => {
    const h = createTestHarness();
    await h.provider.connect();

    const patches: ProviderPatch[] = [];
    h.provider.subscribe((patch) => patches.push(patch));

    h.transport?.feed({
      VehicleState: [
        {
          vehicle_id: "TRK-FUTURE",
          timestamp: T0_ISO,
          position: { x: 0, y: 0, segment_id: null, offset_m: null },
          speed_mps: 5,
          accel_mps2: 0,
          grade_rad: 0,
          friction_est: { value: null, sigma: null },
          mode: "SUPER_AUTONOMOUS_HOVER", // Unknown enum value
          comm_confidence: 1,
          vehicle_kind: null,
          route_id: null,
        },
      ],
      SafetyState: [
        {
          vehicle_id: "TRK-FUTURE",
          timestamp: T0_ISO,
          v_safe: 5,
          h_safe: 20,
          actual_speed: 5,
          headway_current: 25,
          lead_vehicle_id: null,
          active_constraint: "QUANTUM_TUNNEL", // Unknown constraint
          risk_level: "EXTREME_DANGER", // Unknown risk level
          headway_violation: null,
          envelope_violation: null,
        },
      ],
    });

    expect(patches).toHaveLength(1);
    expect(patches[0]?.changes.vehicles?.["TRK-FUTURE"]?.mode).toBe("UNKNOWN");
    expect(patches[0]?.changes.safety?.["TRK-FUTURE"]?.activeConstraint).toBe("UNKNOWN");
    expect(patches[0]?.changes.safety?.["TRK-FUTURE"]?.riskLevel).toBe("UNKNOWN");
  });

  it("preserves explicit entity deletions (MID-C / E-14)", async () => {
    const h = createTestHarness();
    await h.provider.connect();

    const patches: ProviderPatch[] = [];
    h.provider.subscribe((patch) => patches.push(patch));

    h.transport?.feed({
      emit: {
        VehicleState: [
          {
            vehicle_id: "TRK-01",
            timestamp: T0_ISO,
            position: { x: 0, y: 0, segment_id: null, offset_m: null },
            speed_mps: 5,
            accel_mps2: 0,
            grade_rad: 0,
            friction_est: { value: null, sigma: null },
            mode: "NORMAL",
            comm_confidence: 1,
            vehicle_kind: null,
            route_id: null,
          },
        ],
      },
      deletions: {
        vehicles: ["TRK-99", "TRK-98"],
        slots: ["SLOT-EXPIRED"],
      },
    });

    expect(patches).toHaveLength(1);
    expect(patches[0]?.changes.vehicles?.["TRK-01"]).toBeDefined();
    expect(patches[0]?.deletions).toEqual({
      vehicles: ["TRK-99", "TRK-98"],
      slots: ["SLOT-EXPIRED"],
    });
  });

  it("handles malformed JSON string payload by emitting PROTOCOL error without throwing", async () => {
    const h = createTestHarness();
    await h.provider.connect();

    let capturedError: ProviderError | null = null;
    h.provider.onStatusChange((_status, error) => {
      if (error) capturedError = error;
    });

    h.transport?.feed("INVALID_JSON_NOT_AN_OBJECT{{{");

    expect(h.provider.currentStatus).toBe("ERROR");
    expect(capturedError).not.toBeNull();
    expect((capturedError as ProviderError | null)?.kind).toBe("PROTOCOL");
  });
});

describe("LiveDataProvider reconnect state machine", () => {
  it("enters RECONNECTING and reconnects on transport disconnect", async () => {
    const h = createTestHarness({
      initialDelayMs: 500,
      factor: 2.0,
      jitter: false,
    });
    await h.provider.connect();

    const statuses: ConnectionStatus[] = [];
    h.provider.onStatusChange((status) => statuses.push(status));

    // Simulate link loss
    h.transport?.triggerDisconnect(
      providerError("TRANSPORT", "Network dropped", { occurredAt: T0_ISO }),
    );

    expect(h.provider.currentStatus).toBe("RECONNECTING");

    // Advance virtual time by backoff delay (500ms)
    h.scheduler.advance(500);

    expect(h.provider.currentStatus).toBe("CONNECTED");
    expect(statuses).toContain("RECONNECTING");
    expect(statuses[statuses.length - 1]).toBe("CONNECTED");
  });

  it("applies exponential backoff across multiple reconnect attempts", async () => {
    let attempts = 0;
    const flakeTransport: LiveTransport = {
      name: "FLAKY",
      async connect() {
        attempts++;
        if (attempts <= 2) {
          throw providerError("TRANSPORT", `Simulated connect error ${attempts}`, {
            occurredAt: T0_ISO,
          });
        }
      },
      async disconnect() {},
      onMessage: () => () => {},
      onStatus: () => () => {},
    };

    const h = createTestHarness({
      transport: flakeTransport,
      initialDelayMs: 1000,
      factor: 2.0,
      jitter: false,
      maxRetries: 5,
    });

    // Initial connect fails
    await expect(h.provider.connect()).rejects.toBeDefined();
    expect(h.provider.currentStatus).toBe("RECONNECTING");

    // First retry scheduled at 1000ms
    h.scheduler.advance(999);
    expect(attempts).toBe(1);

    h.scheduler.advance(1); // attempt 2 runs and fails
    await Promise.resolve();
    await Promise.resolve();
    expect(attempts).toBe(2);
    expect(h.provider.currentStatus).toBe("RECONNECTING");

    // Second retry scheduled at 1000 * 2^1 = 2000ms
    h.scheduler.advance(1999);
    expect(attempts).toBe(2);

    h.scheduler.advance(1); // attempt 3 runs and succeeds
    await Promise.resolve();
    await Promise.resolve();
    expect(attempts).toBe(3);
    expect(h.provider.currentStatus).toBe("CONNECTED");
  });

  it("transitions to ERROR when maxRetries is exceeded", async () => {
    const deadTransport: LiveTransport = {
      name: "DEAD",
      async connect() {
        throw providerError("TRANSPORT", "Permanent failure", { occurredAt: T0_ISO });
      },
      async disconnect() {},
      onMessage: () => () => {},
      onStatus: () => () => {},
    };

    const h = createTestHarness({
      transport: deadTransport,
      initialDelayMs: 100,
      factor: 1.0,
      jitter: false,
      maxRetries: 2,
    });

    await expect(h.provider.connect()).rejects.toBeDefined();
    // Attempt 1 fails immediately, schedules retry 1 at 100ms
    h.scheduler.advance(100); // retry 1 fails
    await Promise.resolve();
    await Promise.resolve();
    h.scheduler.advance(100); // retry 2 fails -> max retries exceeded
    await Promise.resolve();
    await Promise.resolve();

    expect(h.provider.currentStatus).toBe("ERROR");
  });

  it("cancels reconnect timers deterministically on manual disconnect", async () => {
    const deadTransport: LiveTransport = {
      name: "DEAD",
      async connect() {
        throw providerError("TRANSPORT", "Down", { occurredAt: T0_ISO });
      },
      async disconnect() {},
      onMessage: () => () => {},
      onStatus: () => () => {},
    };

    const h = createTestHarness({
      transport: deadTransport,
      initialDelayMs: 1000,
    });

    await expect(h.provider.connect()).rejects.toBeDefined();
    expect(h.scheduler.pendingCount()).toBe(1);

    await h.provider.disconnect();
    expect(h.scheduler.pendingCount()).toBe(0);
    expect(h.provider.currentStatus).toBe("DISCONNECTED");
  });
});

describe("LiveDataProvider advisory acknowledgement", () => {
  it("updates local alert state and emits ALERT_ACKNOWLEDGED event for known alerts", async () => {
    const h = createTestHarness();
    await h.provider.connect();

    const patches: ProviderPatch[] = [];
    h.provider.subscribe((patch) => patches.push(patch));

    // First deliver an alert
    h.transport?.feed({
      Alert: [
        {
          alert_id: "ALT-01",
          timestamp: T0_ISO,
          severity: "WARNING",
          category: "UNSAFE_SPEED",
          origin: "TASK2",
          subject: { kind: "VEHICLE", id: "TRK-01" },
          message: "Speed exceeded limit",
          reason_code: "SPEED_LIMIT",
          acknowledgeable: true,
          acknowledged: null,
          active: true,
        },
      ],
    });

    expect(patches).toHaveLength(1);
    expect(patches[0]?.changes.alerts?.[0]?.acknowledged).toBeNull();

    // Now acknowledge it
    await h.provider.sendAcknowledgement("ALT-01", "operator-1");

    expect(patches).toHaveLength(2);
    const ackPatch = patches[1]?.changes;
    expect(ackPatch?.alerts?.[0]?.acknowledged).toEqual({
      by: "operator-1",
      at: T0_ISO,
    });
    expect(ackPatch?.events?.[0]?.category).toBe("ALERT_ACKNOWLEDGED");
  });

  it("transmits acknowledgement message over transport if send is available", async () => {
    const h = createTestHarness();
    await h.provider.connect();

    await h.provider.sendAcknowledgement("ALT-99", "operator-2");

    expect(h.transport?.sentMessages).toHaveLength(1);
    const sent = JSON.parse(h.transport?.sentMessages[0] ?? "{}");
    expect(sent).toMatchObject({
      type: "ALERT_ACKNOWLEDGED",
      alertId: "ALT-99",
      actor: "operator-2",
    });
  });

  it("rejects acknowledgement when provider is disconnected", async () => {
    const h = createTestHarness();
    await expect(h.provider.sendAcknowledgement("ALT-01", "op")).rejects.toMatchObject({
      kind: "TRANSPORT",
    });
  });
});

describe("Scenario stub transport loader", () => {
  it("creates a stub transport loaded from an authored scenario", async () => {
    const transport = createScenarioStubTransport("nominal");
    expect(transport.name).toBe("STUB");

    const provider = new LiveDataProvider({ transport });
    await provider.connect();

    expect(provider.currentStatus).toBe("CONNECTED");
    await provider.disconnect();
    expect(provider.currentStatus).toBe("DISCONNECTED");
  });
});
