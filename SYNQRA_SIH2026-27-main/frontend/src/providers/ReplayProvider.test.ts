/**
 * ReplayProvider tests — M9. FR-017.
 *
 * The central test is AC1: record a session, scrub to every recorded timestamp in several
 * orders, and assert the reconstructed store state EQUALS the state recorded there. Not
 * "close to". Equal.
 *
 * Virtual time only — `manualScheduler`, as M3 established. No test waits on the clock.
 */

import { beforeEach, describe, expect, it } from "vitest";
import { freshnessConfig } from "../config/freshness";
import type { AppState } from "../contracts/appState";
import type { Alert, VehicleState } from "../contracts/domain";
import { emptyAppState } from "../data/patch";
import { EventLog, type Recording } from "../state/eventLog";
import { viewFreshness } from "../state/freshness";
import { AppStateStore } from "../state/store";
import { REPLAY_COMMAND_REJECTED, REPLAY_TICK_MS, ReplayProvider } from "./ReplayProvider";
import { type ManualScheduler, manualScheduler } from "./scheduler";

const BASE = Date.parse("2026-01-01T00:00:00.000Z");
const CONFIG = freshnessConfig(5000);

function vehicle(id: string, iso: string): VehicleState {
  return {
    vehicleId: id,
    timestamp: iso,
    position: { x: 1, y: 2, segmentId: "S-1", offsetM: 5 },
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

function alert(id: string): Alert {
  return {
    alertId: id,
    timestamp: "2026-01-01T00:00:00.000Z",
    severity: "WARNING",
    category: "UNSAFE_SPEED",
    origin: "TASK2",
    subject: { kind: "VEHICLE", id: "V-1" },
    message: `alert ${id}`,
    reasonCode: null,
    acknowledgeable: true,
    acknowledged: null,
    active: true,
  };
}

/**
 * A three-frame session. Frame 2 ADDS a vehicle, frame 3 REMOVES it and adds an alert —
 * so a backward scrub must delete an entity, which is the case a naive merge gets wrong.
 */
function buildRecording(): { recording: Recording; frames: AppState[]; times: number[] } {
  const log = new EventLog();
  const times = [BASE, BASE + 1000, BASE + 2000];

  const f1: AppState = {
    ...emptyAppState(new Date(times[0] as number).toISOString()),
    vehicles: { "V-1": vehicle("V-1", "2026-01-01T00:00:00.000Z") },
  };
  const f2: AppState = {
    ...f1,
    vehicles: {
      "V-1": vehicle("V-1", "2026-01-01T00:00:00.000Z"),
      "V-2": vehicle("V-2", "2026-01-01T00:00:01.000Z"),
    },
  };
  const f3: AppState = {
    ...f1,
    vehicles: { "V-1": vehicle("V-1", "2026-01-01T00:00:02.000Z") },
    alerts: [alert("A-1")],
  };

  const frames = [f1, f2, f3];
  frames.forEach((state, i) => {
    const at = times[i] as number;
    log.appendFrame(state, at, new Date(at).toISOString());
  });

  return { recording: log.recording(), frames, times };
}

let scheduler: ManualScheduler;
let provider: ReplayProvider;
let store: AppStateStore;
let built: ReturnType<typeof buildRecording>;

function wire(): void {
  provider.subscribe((patch) => store.applyPatch(patch, new Date().toISOString()));
  provider.onStatusChange((status, error) => store.setStatus(status, error?.message ?? null));
}

beforeEach(() => {
  built = buildRecording();
  scheduler = manualScheduler(0);
  provider = new ReplayProvider(built.recording, { scheduler });
  store = new AppStateStore(new Date(BASE).toISOString(), "REPLAY");
  wire();
});

// ---------------------------------------------------------------------------

describe("the third provider behind the same interface (FR-017 AC4)", () => {
  it("reports kind REPLAY", () => {
    expect(provider.kind).toBe("REPLAY");
  });

  it("implements the DataProvider surface", () => {
    for (const method of [
      "connect",
      "disconnect",
      "subscribe",
      "onStatusChange",
      "sendAcknowledgement",
    ]) {
      expect(typeof (provider as unknown as Record<string, unknown>)[method]).toBe("function");
    }
  });

  it("connects and reports CONNECTED", async () => {
    await provider.connect();
    expect(store.getSnapshot().connection.status).toBe("CONNECTED");
  });

  it("refuses to connect with nothing recorded, rather than replaying an empty session", async () => {
    const empty = new ReplayProvider(new EventLog().recording(), { scheduler });
    empty.onStatusChange((status) => store.setStatus(status, null));
    await expect(empty.connect()).rejects.toMatchObject({ kind: "INITIALIZATION" });
    expect(store.getSnapshot().connection.status).toBe("ERROR");
  });

  it("disconnect cancels playback and is idempotent", async () => {
    await provider.connect();
    provider.play();
    expect(scheduler.pendingCount()).toBeGreaterThan(0);
    await provider.disconnect();
    expect(scheduler.pendingCount()).toBe(0);
    await provider.disconnect();
    expect(store.getSnapshot().connection.status).toBe("DISCONNECTED");
  });
});

describe("FR-017 AC1 — scrubbing to t reproduces the state recorded at t", () => {
  /** Everything a frame recorded, ignoring the replay clock the provider sets. */
  const operational = (s: AppState) => ({
    topology: s.topology,
    vehicles: s.vehicles,
    safety: s.safety,
    road: s.road,
    forecasts: s.forecasts,
    bottlenecks: s.bottlenecks,
    arrivals: s.arrivals,
    slots: s.slots,
    dispatch: s.dispatch,
    alerts: s.alerts,
    events: s.events,
    health: s.health,
    kpis: s.kpis,
    cv: s.cv,
  });

  it("reproduces each recorded frame exactly, forwards", async () => {
    await provider.connect();
    built.times.forEach((t, i) => {
      provider.scrubTo(t);
      expect(operational(store.getSnapshot())).toEqual(operational(built.frames[i] as AppState));
    });
  });

  it("reproduces each recorded frame exactly, BACKWARDS", async () => {
    // The hard direction: going back must DELETE entities that did not exist at t.
    await provider.connect();
    for (let i = built.times.length - 1; i >= 0; i -= 1) {
      provider.scrubTo(built.times[i] as number);
      expect(operational(store.getSnapshot())).toEqual(operational(built.frames[i] as AppState));
    }
  });

  it("reproduces each frame exactly in a shuffled order", async () => {
    await provider.connect();
    for (const i of [2, 0, 1, 2, 1, 0]) {
      provider.scrubTo(built.times[i] as number);
      expect(operational(store.getSnapshot())).toEqual(operational(built.frames[i] as AppState));
    }
  });

  it("removes an entity that did not exist at the scrubbed moment", async () => {
    await provider.connect();
    provider.scrubTo(built.times[1] as number);
    expect(Object.keys(store.getSnapshot().vehicles).sort()).toEqual(["V-1", "V-2"]);
    provider.scrubTo(built.times[0] as number);
    // V-2 did not exist at the first frame and must be gone, not lingering.
    expect(Object.keys(store.getSnapshot().vehicles)).toEqual(["V-1"]);
  });

  it("does not interpolate between frames", async () => {
    await provider.connect();
    // Halfway between frame 1 and frame 2: the state is frame 1's, unchanged.
    provider.scrubTo((built.times[0] as number) + 500);
    expect(operational(store.getSnapshot())).toEqual(operational(built.frames[0] as AppState));
  });

  it("clamps a position outside the recorded window", async () => {
    await provider.connect();
    provider.scrubTo(BASE - 999_999);
    expect(provider.position.positionMs).toBe(built.recording.startMs);
    provider.scrubTo(BASE + 999_999);
    expect(provider.position.positionMs).toBe(built.recording.endMs);
  });

  it("is deterministic — replaying the same position twice gives the same state", async () => {
    await provider.connect();
    provider.scrubTo(built.times[2] as number);
    const first = JSON.stringify(operational(store.getSnapshot()));
    provider.scrubTo(built.times[0] as number);
    provider.scrubTo(built.times[2] as number);
    expect(JSON.stringify(operational(store.getSnapshot()))).toBe(first);
  });
});

describe("M9D-E — the replay clock", () => {
  it("sets clock.now and clock.replayPosition to the replayed moment", async () => {
    await provider.connect();
    provider.scrubTo(built.times[1] as number);
    const clock = store.getSnapshot().clock;
    const expected = new Date(built.times[1] as number).toISOString();
    expect(clock.replayPosition).toBe(expected);
    expect(clock.now).toBe(expected);
  });

  it("replayed data is NOT stale merely because the wall clock has moved on", async () => {
    await provider.connect();
    provider.scrubTo(built.times[0] as number);

    const state = store.getSnapshot();
    const nowMs = Date.parse(state.clock.now);
    const view = viewFreshness(state.vehicles["V-1"]?.timestamp, CONFIG, nowMs);

    // Against the replay clock the datum was current, and replay must reproduce that.
    expect(view.quality).toBe("OK");

    // Against the real wall clock — years later — it would read stale. That is the bug
    // M9D-E exists to prevent.
    const wallClockView = viewFreshness(state.vehicles["V-1"]?.timestamp, CONFIG, Date.now());
    expect(wallClockView.quality).toBe("STALE");
  });

  it("the live ticker cannot advance the clock while a replay position is set", async () => {
    await provider.connect();
    provider.scrubTo(built.times[1] as number);
    const before = store.getSnapshot().clock.now;
    store.tick(new Date().toISOString());
    expect(store.getSnapshot().clock.now).toBe(before);
  });
});

describe("replay transport", () => {
  it("play advances the position and pause stops it", async () => {
    await provider.connect();
    provider.play();
    expect(provider.position.playing).toBe(true);

    const startPosition = provider.position.positionMs;
    scheduler.advance(REPLAY_TICK_MS);
    expect(provider.position.positionMs).toBeGreaterThan(startPosition);

    provider.pause();
    const paused = provider.position.positionMs;
    scheduler.advance(REPLAY_TICK_MS * 10);
    expect(provider.position.positionMs).toBe(paused);
    expect(scheduler.pendingCount()).toBe(0);
  });

  it("speed multiplies how far each tick advances", async () => {
    await provider.connect();
    provider.setSpeed(4);
    provider.play();
    const start = provider.position.positionMs;
    scheduler.advance(REPLAY_TICK_MS);
    expect(provider.position.positionMs - start).toBe(REPLAY_TICK_MS * 4);
  });

  it("stops at the end of the recording rather than running past it", async () => {
    await provider.connect();
    provider.play();
    scheduler.advance(REPLAY_TICK_MS * 100);
    expect(provider.position.positionMs).toBe(built.recording.endMs);
    expect(provider.position.playing).toBe(false);
  });

  it("reports position, window, speed and frame count", async () => {
    await provider.connect();
    expect(provider.position).toMatchObject({
      startMs: built.recording.startMs,
      endMs: built.recording.endMs,
      speed: 1,
      frameCount: 3,
    });
  });

  it("notifies position listeners", async () => {
    const seen: number[] = [];
    provider.onPositionChange((p) => seen.push(p.positionMs));
    await provider.connect();
    provider.scrubTo(built.times[2] as number);
    expect(seen).toContain(built.times[2] as number);
  });
});

describe("FR-017 AC3 — no command may be issued while replaying", () => {
  it("sendAcknowledgement rejects with a typed provider error", async () => {
    await provider.connect();
    await expect(provider.sendAcknowledgement("A-1", "operator")).rejects.toMatchObject({
      kind: "ABORTED",
      retryable: false,
    });
  });

  it("the rejection names the reason", async () => {
    await provider.connect();
    await expect(provider.sendAcknowledgement("A-1", "operator")).rejects.toMatchObject({
      message: REPLAY_COMMAND_REJECTED,
    });
  });

  it("rejects even before connecting, and even while disconnected", async () => {
    await expect(provider.sendAcknowledgement("A-1", "op")).rejects.toBeDefined();
    await provider.connect();
    await provider.disconnect();
    await expect(provider.sendAcknowledgement("A-1", "op")).rejects.toBeDefined();
  });

  it("a rejected acknowledgement changes no state", async () => {
    await provider.connect();
    provider.scrubTo(built.times[2] as number);
    const before = JSON.stringify(store.getSnapshot());
    await provider.sendAcknowledgement("A-1", "operator").catch(() => {});
    expect(JSON.stringify(store.getSnapshot())).toBe(before);
  });

  it("exposes NO other method that could act on the mine", () => {
    // The whole command surface of the interface is one method, and it always rejects.
    for (const forbidden of [
      "sendCommand",
      "issueCommand",
      "dispatch",
      "override",
      "actuate",
      "setTargetSpeed",
      "releaseVehicle",
      "holdVehicle",
    ]) {
      expect(provider, `ReplayProvider must not expose ${forbidden}`).not.toHaveProperty(forbidden);
    }
  });
});
