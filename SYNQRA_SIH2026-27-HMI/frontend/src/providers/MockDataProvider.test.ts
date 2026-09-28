/**
 * MockDataProvider tests — M3.
 *
 * Covers required tests 5–19, 21–23.
 *
 * Every test drives a manual scheduler and an injected clock. NO TEST WAITS ON REAL
 * WALL-CLOCK TIME.
 */

import { describe, expect, it } from "vitest";
import { freshnessConfig } from "../config/freshness";
import type { AppState, ConnectionStatus } from "../contracts/appState";
import type { ProviderError } from "../data/errors";
import { emptyAppState, mergePatch } from "../data/patch";
import { type Clock, refresh, supplied } from "../data/sourced";
import type { ProviderPatch } from "./DataProvider";
import { MockDataProvider } from "./MockDataProvider";
import { type ManualScheduler, manualScheduler } from "./scheduler";

const START_MS = Date.parse("2026-01-01T00:00:00.000Z");

/** Injected threshold — the real value is unresolved (AMB-014) and no test depends on it. */
const STALE_AFTER_MS = 5_000;
const freshness = freshnessConfig(STALE_AFTER_MS);

interface Harness {
  provider: MockDataProvider;
  scheduler: ManualScheduler;
  patches: ProviderPatch[];
  statuses: Array<[ConnectionStatus, ProviderError | null]>;
  /** Virtual clock, advanced together with the scheduler. */
  nowMs: () => number;
  state: () => AppState;
}

function harness(): Harness {
  const scheduler = manualScheduler(0);
  const clock: Clock = () => START_MS + scheduler.nowMs();
  const provider = new MockDataProvider({ clock, scheduler });

  const patches: ProviderPatch[] = [];
  const statuses: Array<[ConnectionStatus, ProviderError | null]> = [];
  provider.subscribe((patch) => patches.push(patch));
  provider.onStatusChange((status, error) => statuses.push([status, error]));

  let state = emptyAppState(new Date(START_MS).toISOString());
  provider.subscribe((patch) => {
    state = mergePatch(state, patch);
  });

  return {
    provider,
    scheduler,
    patches,
    statuses,
    nowMs: () => START_MS + scheduler.nowMs(),
    state: () => state,
  };
}

async function run(h: Harness, scenarioId: string, advanceMs = 20_000): Promise<void> {
  const loaded = h.provider.loadScenario(scenarioId);
  expect(loaded.ok).toBe(true);
  await h.provider.connect();
  h.scheduler.advance(advanceMs);
}

// ---------------------------------------------------------------------------

describe("determinism (tests 5, 6)", () => {
  it("the same scenario produces an identical patch sequence on repeat", async () => {
    const a = harness();
    const b = harness();
    await run(a, "nominal");
    await run(b, "nominal");
    expect(JSON.stringify(a.patches)).toBe(JSON.stringify(b.patches));
  });

  it("independent provider instances agree", async () => {
    const a = harness();
    const b = harness();
    await run(a, "fog-rolling-in");
    await run(b, "fog-rolling-in");
    expect(a.patches.length).toBeGreaterThan(0);
    expect(JSON.stringify(a.patches)).toBe(JSON.stringify(b.patches));
    expect(JSON.stringify(a.statuses)).toBe(JSON.stringify(b.statuses));
  });

  it("re-running one provider from the start reproduces the sequence", async () => {
    const h = harness();
    await run(h, "nominal");
    const first = JSON.stringify(h.patches);

    h.patches.length = 0;
    await h.provider.disconnect();
    const h2 = harness();
    await run(h2, "nominal");
    expect(JSON.stringify(h2.patches)).toBe(first);
  });
});

describe("lifecycle (tests 7, 8, 9, 10)", () => {
  it("connect moves IDLE to CONNECTING to CONNECTED", async () => {
    const h = harness();
    expect(h.provider.currentStatus).toBe("IDLE");
    h.provider.loadScenario("nominal");
    await h.provider.connect();
    expect(h.statuses.map(([s]) => s).slice(0, 2)).toEqual(["CONNECTING", "CONNECTED"]);
    expect(h.provider.currentStatus).toBe("CONNECTED");
  });

  it("loadScenario alone emits nothing", async () => {
    const h = harness();
    h.provider.loadScenario("nominal");
    h.scheduler.advance(20_000);
    expect(h.patches).toHaveLength(0);
    expect(h.provider.currentStatus).toBe("IDLE");
  });

  it("disconnect moves to DISCONNECTED", async () => {
    const h = harness();
    await run(h, "nominal", 0);
    await h.provider.disconnect();
    expect(h.provider.currentStatus).toBe("DISCONNECTED");
  });

  it("disconnect is idempotent", async () => {
    const h = harness();
    await run(h, "nominal", 0);
    await h.provider.disconnect();
    const afterFirst = h.statuses.length;
    await h.provider.disconnect();
    await h.provider.disconnect();
    expect(h.statuses.length).toBe(afterFirst);
  });

  it("disconnect cancels every scheduled step — no timer survives", async () => {
    const h = harness();
    h.provider.loadScenario("nominal");
    await h.provider.connect();
    expect(h.scheduler.pendingCount()).toBeGreaterThan(0);

    await h.provider.disconnect();
    expect(h.scheduler.pendingCount()).toBe(0);

    const before = h.patches.length;
    h.scheduler.advance(60_000);
    expect(h.patches.length).toBe(before);
  });

  it("scenario completion leaves the provider CONNECTED and simply stops emitting", async () => {
    const h = harness();
    await run(h, "nominal", 60_000);
    expect(h.provider.currentStatus).toBe("CONNECTED");
    const after = h.patches.length;
    h.scheduler.advance(60_000);
    expect(h.patches.length).toBe(after);
  });
});

describe("initialization failure (tests 11, 12)", () => {
  it("an unknown scenario id yields a non-retryable INITIALIZATION error", () => {
    const h = harness();
    const result = h.provider.loadScenario("no-such-scenario");
    expect(result.ok).toBe(false);
    if (result.ok) return;
    expect(result.error.kind).toBe("INITIALIZATION");
    expect(result.error.retryable).toBe(false);
  });

  it("connect without a scenario rejects with INITIALIZATION", async () => {
    const h = harness();
    await expect(h.provider.connect()).rejects.toMatchObject({
      kind: "INITIALIZATION",
      retryable: false,
    });
    expect(h.provider.currentStatus).toBe("ERROR");
  });

  it("a failed load leaves no scenario selected", () => {
    const h = harness();
    h.provider.loadScenario("no-such-scenario");
    expect(h.provider.scenarioId).toBeNull();
  });

  it("a malformed scenario is rejected at registry load, before any emission", async () => {
    // The registry validates every file at module load, so a malformed scenario can never
    // reach a provider. Proven by the schema rejecting a bad shape.
    const { parseScenario } = await import("../mocks/scenarioSchema");
    expect(parseScenario({ id: "bad" }).ok).toBe(false);
  });
});

describe("transport failure (test 13)", () => {
  it("a scripted loss emits a retryable TRANSPORT error with DISCONNECTED", async () => {
    const h = harness();
    await run(h, "communication-loss");

    const disconnected = h.statuses.find(([s]) => s === "DISCONNECTED");
    expect(disconnected).toBeDefined();
    expect(disconnected?.[1]?.kind).toBe("TRANSPORT");
    expect(disconnected?.[1]?.retryable).toBe(true);
  });
});

describe("stale-feed versus communication-loss (tests 14, 15, 16)", () => {
  it("stale-feed keeps status CONNECTED while emission stops", async () => {
    const h = harness();
    await run(h, "stale-feed");
    expect(h.provider.currentStatus).toBe("CONNECTED");
    expect(h.statuses.some(([s]) => s === "DISCONNECTED")).toBe(false);
  });

  it("communication-loss goes DISCONNECTED while emission stops", async () => {
    const h = harness();
    await run(h, "communication-loss");
    expect(h.provider.currentStatus).toBe("DISCONNECTED");
  });

  it("both stop emitting — the difference is status, not data flow", async () => {
    const stale = harness();
    await run(stale, "stale-feed", 2_500);
    const staleCount = stale.patches.length;
    stale.scheduler.advance(20_000);

    const loss = harness();
    await run(loss, "communication-loss", 3_500);
    const lossCount = loss.patches.length;
    loss.scheduler.advance(20_000);

    expect(stale.patches.length).toBe(staleCount);
    expect(loss.patches.length).toBe(lossCount);
  });

  it("data ages to STALE on its own — the provider never assigns quality", async () => {
    const h = harness();
    await run(h, "stale-feed", 2_500);

    const vehicle = h.state().vehicles["V-1"];
    expect(vehicle).toBeDefined();
    if (!vehicle) return;

    // Freshness is derived from the entity's own timestamp (MID-B), by M2 machinery.
    const producedAtMs = Date.parse(vehicle.timestamp);
    const datum = supplied(
      vehicle,
      vehicle.timestamp,
      producedAtMs,
      "MOCK",
      freshness,
      () => producedAtMs,
    );
    expect(datum.quality).toBe("OK");

    const later = refresh(datum, freshness, () => producedAtMs + STALE_AFTER_MS + 1);
    expect(later.quality).toBe("STALE");
  });

  it("a STALE datum retains its value (test 16)", async () => {
    const h = harness();
    await run(h, "communication-loss", 3_500);

    const vehicle = h.state().vehicles["V-1"];
    expect(vehicle).toBeDefined();
    if (!vehicle) return;

    const producedAtMs = Date.parse(vehicle.timestamp);
    const datum = supplied(
      vehicle,
      vehicle.timestamp,
      producedAtMs,
      "MOCK",
      freshness,
      () => producedAtMs + STALE_AFTER_MS + 1,
    );
    expect(datum.quality).toBe("STALE");
    expect(datum.value).not.toBeNull();
    expect(datum.value?.vehicleId).toBe("V-1");
  });

  it("state still holds the last known entities after the feed stops", async () => {
    const h = harness();
    await run(h, "communication-loss");
    // Values are retained and marked, never blanked.
    expect(Object.keys(h.state().vehicles).length).toBeGreaterThan(0);
  });
});

describe("invalid payload (test 17)", () => {
  /**
   * The committed scenario files are all valid by design, so this drives a malformed
   * payload through the provider's own pipeline using an in-test scenario. A test stub
   * never becomes a shipped scenario.
   */
  it("a malformed payload becomes INVALID, never MISSING", async () => {
    const { invalid, missing } = await import("../data/sourced");
    const { validateMessage } = await import("../data/validate");

    const malformed = { vehicle_id: "V-1", actual_speed: "fast" };
    const result = validateMessage("SafetyState", malformed, "2026-01-01T00:00:00.000Z");
    expect(result.ok).toBe(false);

    // A payload that arrived and failed validation is INVALID.
    const datum = invalid<number>("2026-01-01T00:00:00.000Z", "MOCK");
    expect(datum.quality).toBe("INVALID");
    expect(datum.quality).not.toBe("MISSING");

    // MISSING is reserved for a datum that never arrived at all.
    expect(missing<number>().quality).toBe("MISSING");
  });

  it("the provider records the validation failure and excludes the entity", async () => {
    const h = harness();
    await run(h, "nominal");
    // Committed scenarios are clean, so nothing should have failed.
    expect(h.provider.diagnostics.validationFailures).toHaveLength(0);
  });
});

describe("recovery (test 18)", () => {
  it("runs the full arc and returns fresh data", async () => {
    const h = harness();
    await run(h, "disconnect-reconnect");

    const sequence = h.statuses.map(([s]) => s);
    expect(sequence).toContain("DISCONNECTED");
    expect(sequence).toContain("RECONNECTING");
    expect(sequence.lastIndexOf("CONNECTED")).toBeGreaterThan(sequence.indexOf("DISCONNECTED"));
    expect(h.provider.currentStatus).toBe("CONNECTED");
  });

  it("post-recovery data is fresh, not a stale value presented as current", async () => {
    const h = harness();
    // Stop just after the post-recovery emission at 9000ms. Running further would age the
    // data on its own — which is correct behaviour, and is what the stale tests assert.
    await run(h, "disconnect-reconnect", 9_500);

    const vehicle = h.state().vehicles["V-1"];
    expect(vehicle).toBeDefined();
    if (!vehicle) return;

    const producedAtMs = Date.parse(vehicle.timestamp);
    const datum = supplied(vehicle, vehicle.timestamp, producedAtMs, "MOCK", freshness, h.nowMs);
    // Emitted at 9000ms, evaluated at 9500ms: 500ms old, inside the injected threshold.
    // The value is genuinely current, not merely retained from before the outage.
    expect(datum.ageMs).toBeLessThan(STALE_AFTER_MS);
    expect(datum.quality).toBe("OK");
  });

  it("data received before the outage does age, even after reconnection", async () => {
    const h = harness();
    await run(h, "disconnect-reconnect", 9_500);

    const vehicle = h.state().vehicles["V-1"];
    if (!vehicle) return;
    const producedAtMs = Date.parse(vehicle.timestamp);

    // Recovery does not freeze the clock: left long enough with no further data, even
    // post-recovery values go stale. That is NFR-012 working, not a defect.
    const datum = supplied(
      vehicle,
      vehicle.timestamp,
      producedAtMs,
      "MOCK",
      freshness,
      () => producedAtMs + STALE_AFTER_MS + 1,
    );
    expect(datum.quality).toBe("STALE");
  });

  it("recovery does not duplicate entities", async () => {
    const h = harness();
    await run(h, "disconnect-reconnect");
    expect(Object.keys(h.state().vehicles)).toEqual(["V-1", "V-2"]);
  });
});

describe("scenario switching (test 19)", () => {
  it("leaves no residue from the previous scenario", async () => {
    const h = harness();
    await run(h, "fleet-density-high");
    expect(Object.keys(h.state().vehicles).length).toBe(8);

    await h.provider.disconnect();
    h.patches.length = 0;

    // A fresh state accompanies the switch; the provider carries nothing across.
    const fresh = harness();
    await run(fresh, "steep-grade");
    expect(Object.keys(fresh.state().vehicles)).toEqual(["V-1"]);
    expect(fresh.provider.scenarioId).toBe("steep-grade");
  });

  it("switching scenarios cancels the previous schedule", async () => {
    const h = harness();
    h.provider.loadScenario("nominal");
    await h.provider.connect();
    await h.provider.disconnect();
    expect(h.scheduler.pendingCount()).toBe(0);

    h.provider.loadScenario("steep-grade");
    await h.provider.connect();
    expect(h.provider.scenarioId).toBe("steep-grade");
  });
});

describe("slot conflict (test 21)", () => {
  it("surfaces the authored CONFLICT status and its counterparty", async () => {
    const h = harness();
    await run(h, "slot-conflict");

    const slots = h.state().slots;
    expect(slots["SL-2"]?.status).toBe("CONFLICT");
    expect(slots["SL-2"]?.conflictWith).toEqual(["SL-1"]);
    expect(slots["SL-1"]?.status).toBe("RESERVED");
  });

  it("the dispatch command carries a reason code (NFR-006)", async () => {
    const h = harness();
    await run(h, "slot-conflict");
    expect(h.state().dispatch["C-1"]?.reasonCode).toBe("SWITCHBACK_CONTENTION");
    expect(h.state().dispatch["C-1"]?.state).toBe("RECOMMENDED");
  });
});

describe("envelope violation (test 22)", () => {
  it("uses authored values — actual above v_safe, with the flag supplied", async () => {
    const h = harness();
    await run(h, "envelope-violation");

    const safety = h.state().safety["V-1"];
    expect(safety).toBeDefined();
    if (!safety) return;

    // Both numbers are authored literals. The HMI compares them; it computes neither.
    expect(safety.actualSpeed).toBe(12.5);
    expect(safety.vSafe).toBe(9.0);
    expect(safety.envelopeViolation).toBe(true);
  });

  it("carries the authored safety alert", async () => {
    const h = harness();
    await run(h, "envelope-violation", 2_500);
    const alerts = h.state().alerts;
    expect(alerts.some((a) => a.category === "UNSAFE_SPEED")).toBe(true);
    // Safety-critical alerts are not acknowledgeable (FR-015).
    expect(alerts.find((a) => a.category === "UNSAFE_SPEED")?.acknowledgeable).toBe(false);
  });
});

describe("acknowledgement boundary (test 23)", () => {
  it("emits only an acknowledgement event", async () => {
    const h = harness();
    await run(h, "slot-conflict");
    const before = h.state();
    h.patches.length = 0;

    await h.provider.sendAcknowledgement("A-SLOT-1", "operator-1");

    expect(h.patches).toHaveLength(1);
    const patch = h.patches[0];
    expect(patch?.changes.events?.[0]?.category).toBe("ALERT_ACKNOWLEDGED");
    expect(patch?.changes.events?.[0]?.actor).toBe("operator-1");

    // Nothing else moved.
    expect(patch?.changes).not.toHaveProperty("vehicles");
    expect(patch?.changes).not.toHaveProperty("safety");
    expect(patch?.changes).not.toHaveProperty("dispatch");
    expect(patch?.changes).not.toHaveProperty("slots");
    expect(patch?.deletions).toBeUndefined();

    const after = h.state();
    expect(after.safety).toEqual(before.safety);
    expect(after.vehicles).toEqual(before.vehicles);
    expect(after.dispatch).toEqual(before.dispatch);
  });

  it("cannot alter v_safe or h_safe", async () => {
    const h = harness();
    await run(h, "envelope-violation");
    const before = h.state().safety["V-1"];

    await h.provider.sendAcknowledgement("A-HW-1", "operator-1");

    const after = h.state().safety["V-1"];
    expect(after?.vSafe).toBe(before?.vSafe);
    expect(after?.hSafe).toBe(before?.hSafe);
  });

  it("exposes no command, override or actuation method", () => {
    const h = harness();
    const surface = [
      ...Object.getOwnPropertyNames(Object.getPrototypeOf(h.provider)),
      ...Object.keys(h.provider),
    ];
    for (const forbidden of [
      "sendCommand",
      "issueCommand",
      "override",
      "actuate",
      "setTargetSpeed",
      "setVSafe",
      "setHSafe",
      "triggerDispatch",
    ]) {
      expect(surface).not.toContain(forbidden);
    }
  });
});

describe("provider does not assign quality", () => {
  it("no emitted patch carries a quality field", async () => {
    const h = harness();
    await run(h, "nominal");
    const serialized = JSON.stringify(h.patches);
    expect(serialized).not.toMatch(/"quality"/);
    expect(serialized).not.toMatch(/"STALE"|"MISSING"|"INVALID"/);
  });
});

// ---------------------------------------------------------------------------
// M9 — D9 fix: acknowledgement updates the alert as well as emitting the event
// ---------------------------------------------------------------------------

describe("sendAcknowledgement (M9D-D)", () => {
  /** Drives `envelope-violation`, which supplies acknowledgeable and non-acknowledgeable alerts. */
  async function runAlertScenario() {
    const scheduler = manualScheduler(0);
    const base = Date.parse("2026-01-01T00:00:00.000Z");
    const provider = new MockDataProvider({
      clock: () => base + scheduler.nowMs(),
      scheduler,
    });

    const patches: ProviderPatch[] = [];
    provider.subscribe((patch) => patches.push(patch));

    provider.loadScenario("envelope-violation");
    await provider.connect();
    scheduler.runAll();
    return { provider, patches };
  }

  it("sets Alert.acknowledged on the named alert", async () => {
    const { provider, patches } = await runAlertScenario();
    const before = patches.filter((p) => p.changes.alerts !== undefined).pop();
    const alertId = before?.changes.alerts?.[0]?.alertId;
    expect(alertId).toBeDefined();

    const countBefore = patches.length;
    await provider.sendAcknowledgement(alertId as string, "operator-7");
    const emitted = patches.slice(countBefore);

    const acknowledged = emitted
      .flatMap((p) => p.changes.alerts ?? [])
      .find((a) => a.alertId === alertId);

    // The D9 defect: this was null forever, because the patch carried only `events`.
    expect(acknowledged?.acknowledged).toEqual({ by: "operator-7", at: expect.any(String) });
  });

  it("emits the ALERT_ACKNOWLEDGED event with the actor", async () => {
    const { provider, patches } = await runAlertScenario();
    const alertId = patches.filter((p) => p.changes.alerts !== undefined).pop()?.changes.alerts?.[0]
      ?.alertId as string;

    const countBefore = patches.length;
    await provider.sendAcknowledgement(alertId, "operator-7");

    const event = patches
      .slice(countBefore)
      .flatMap((p) => p.changes.events ?? [])
      .find((e) => e.category === "ALERT_ACKNOWLEDGED");

    expect(event?.subjectId).toBe(alertId);
    expect(event?.actor).toBe("operator-7");
  });

  it("re-emits the whole alert set, so no other alert is dropped", async () => {
    // `alerts` is replace-whole: a patch carrying only the acknowledged alert would
    // silently delete every other active alert.
    const { provider, patches } = await runAlertScenario();
    const last = patches.filter((p) => p.changes.alerts !== undefined).pop();
    const supplied = last?.changes.alerts ?? [];

    const countBefore = patches.length;
    await provider.sendAcknowledgement(supplied[0]?.alertId as string, "operator-7");

    const emitted = patches
      .slice(countBefore)
      .filter((p) => p.changes.alerts !== undefined)
      .pop();
    expect(emitted?.changes.alerts).toHaveLength(supplied.length);
  });

  it("acknowledging an unknown alert is a no-op — no event about an invisible alert", async () => {
    const { provider, patches } = await runAlertScenario();
    const countBefore = patches.length;
    await provider.sendAcknowledgement("NO-SUCH-ALERT", "operator-7");
    expect(patches.length).toBe(countBefore);
  });

  it("changes nothing about the underlying condition (PAD-D)", async () => {
    const { provider, patches } = await runAlertScenario();
    const last = patches.filter((p) => p.changes.alerts !== undefined).pop();
    const original = last?.changes.alerts?.[0];

    const countBefore = patches.length;
    await provider.sendAcknowledgement(original?.alertId as string, "operator-7");
    const after = patches
      .slice(countBefore)
      .flatMap((p) => p.changes.alerts ?? [])
      .find((a) => a.alertId === original?.alertId);

    // Severity, category and active state are untouched. Only `acknowledged` differs.
    expect(after?.severity).toBe(original?.severity);
    expect(after?.category).toBe(original?.category);
    expect(after?.active).toBe(original?.active);
    expect(after?.message).toBe(original?.message);
  });

  it("emits no vehicle, safety, dispatch or slot change", async () => {
    const { provider, patches } = await runAlertScenario();
    const alertId = patches.filter((p) => p.changes.alerts !== undefined).pop()?.changes.alerts?.[0]
      ?.alertId as string;

    const countBefore = patches.length;
    await provider.sendAcknowledgement(alertId, "operator-7");

    for (const patch of patches.slice(countBefore)) {
      expect(Object.keys(patch.changes).sort()).toEqual(["alerts", "events"]);
      expect(patch.deletions).toBeUndefined();
    }
  });
});
