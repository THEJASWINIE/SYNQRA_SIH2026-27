/**
 * Event log and session recorder tests — M9. M9D-A, M9D-B, M9D-C.
 *
 * The load-bearing assertions are the negative ones: the log never loses or rewrites an
 * entry, and the recorder never fabricates an operational event category.
 */

import { describe, expect, it } from "vitest";
import type { AppState } from "../contracts/appState";
import type { Alert, DispatchCommand, EventRecord } from "../contracts/domain";
import type { SystemMode } from "../contracts/enums";
import { emptyAppState } from "../data/patch";
import { EventLog, frameAt } from "./eventLog";
import { SessionRecorder } from "./recorder";

const T0 = "2026-01-01T00:00:00.000Z";
const MS = (iso: string) => Date.parse(iso);

function event(id: string, timestamp: string, category: EventRecord["category"]): EventRecord {
  return { eventId: id, timestamp, category, subjectId: null, payload: null, actor: null };
}

function alert(id: string, partial: Partial<Alert> = {}): Alert {
  return {
    alertId: id,
    timestamp: T0,
    severity: "WARNING",
    category: "UNSAFE_SPEED",
    origin: "TASK2",
    subject: { kind: "VEHICLE", id: "V-1" },
    message: `alert ${id}`,
    reasonCode: null,
    acknowledgeable: true,
    acknowledged: null,
    active: true,
    ...partial,
  };
}

function command(id: string): DispatchCommand {
  return {
    commandId: id,
    vehicleId: "V-1",
    routeId: "R-1",
    departureTime: T0,
    targetSpeed: 6,
    slotId: null,
    reasonCode: "REASON",
    timestamp: T0,
    state: "RECOMMENDED",
    limitingVariables: null,
    routeNodeIds: null,
  };
}

function state(partial: Partial<AppState> = {}): AppState {
  return { ...emptyAppState(T0), ...partial };
}

function withStatus(base: AppState, status: AppState["connection"]["status"]): AppState {
  return { ...base, connection: { ...base.connection, status } };
}

function withMode(base: AppState, systemMode: SystemMode): AppState {
  return {
    ...base,
    health: {
      timestamp: T0,
      systemMode,
      connectivity: "CONNECTED",
      fleetCount: 0,
      components: [],
    },
  };
}

// ---------------------------------------------------------------------------

describe("EventLog — append-only", () => {
  it("appends and returns entries", () => {
    const log = new EventLog();
    expect(log.append(event("E-1", T0, "RECOVERY"), "SUPPLIED")).toBe(true);
    expect(log.eventCount).toBe(1);
  });

  it("never overwrites an earlier entry with a later duplicate id", () => {
    const log = new EventLog();
    log.append(event("E-1", T0, "RECOVERY"), "SUPPLIED");
    const accepted = log.append(event("E-1", "2026-01-01T00:00:09.000Z", "VIOLATION"), "SUPPLIED");
    expect(accepted).toBe(false);
    expect(log.eventCount).toBe(1);
    // The FIRST occurrence survives. History is not rewritten by a later copy.
    expect(log.entries()[0]?.event.category).toBe("RECOVERY");
    expect(log.entries()[0]?.event.timestamp).toBe(T0);
  });

  it("exposes no way to remove, truncate or mutate an entry", () => {
    const log = new EventLog();
    for (const forbidden of ["remove", "delete", "truncate", "clear", "update", "splice"]) {
      expect(log, `EventLog must not expose ${forbidden}`).not.toHaveProperty(forbidden);
    }
  });

  it("a returned entry list is a copy — mutating it cannot corrupt the log", () => {
    const log = new EventLog();
    log.append(event("E-1", T0, "RECOVERY"), "SUPPLIED");
    log.entries().length = 0;
    expect(log.eventCount).toBe(1);
  });

  it("orders by timestamp, then by arrival", () => {
    const log = new EventLog();
    log.append(event("late", "2026-01-01T00:00:09.000Z", "RECOVERY"), "SUPPLIED");
    log.append(event("early", T0, "RECOVERY"), "SUPPLIED");
    expect(log.entries().map((e) => e.event.eventId)).toEqual(["early", "late"]);
  });

  it("breaks equal timestamps by arrival, never by reordering history", () => {
    const log = new EventLog();
    log.append(event("first", T0, "RECOVERY"), "SUPPLIED");
    log.append(event("second", T0, "RECOVERY"), "SUPPLIED");
    expect(log.entries().map((e) => e.event.eventId)).toEqual(["first", "second"]);
  });

  it("sorts an unparseable timestamp last rather than to the epoch", () => {
    const log = new EventLog();
    log.append(event("bad", "not-a-timestamp", "RECOVERY"), "SUPPLIED");
    log.append(event("good", T0, "RECOVERY"), "SUPPLIED");
    expect(log.entries().map((e) => e.event.eventId)).toEqual(["good", "bad"]);
  });

  it("is deterministic across repeated reads", () => {
    const log = new EventLog();
    log.append(event("E-1", T0, "RECOVERY"), "SUPPLIED");
    log.append(event("E-2", T0, "MODE_TRANSITION"), "HMI_OBSERVED");
    expect(log.entries()).toEqual(log.entries());
  });

  it("entriesUpTo excludes later events and unparseable ones", () => {
    const log = new EventLog();
    log.append(event("early", T0, "RECOVERY"), "SUPPLIED");
    log.append(event("late", "2026-01-01T00:00:09.000Z", "RECOVERY"), "SUPPLIED");
    log.append(event("bad", "nope", "RECOVERY"), "SUPPLIED");
    expect(log.entriesUpTo(MS("2026-01-01T00:00:05.000Z")).map((e) => e.event.eventId)).toEqual([
      "early",
    ]);
  });

  it("records provenance for every entry", () => {
    const log = new EventLog();
    log.append(event("s", T0, "RECOVERY"), "SUPPLIED");
    log.append(event("h", T0, "MODE_TRANSITION"), "HMI_OBSERVED");
    expect(
      log
        .entries()
        .map((e) => e.origin)
        .sort(),
    ).toEqual(["HMI_OBSERVED", "SUPPLIED"]);
  });
});

describe("EventLog — frames and recording", () => {
  it("records frames and reports the window", () => {
    const log = new EventLog();
    log.appendFrame(state(), MS(T0), T0);
    log.appendFrame(state(), MS("2026-01-01T00:00:09.000Z"), "2026-01-01T00:00:09.000Z");
    const recording = log.recording();
    expect(recording.frames).toHaveLength(2);
    expect(recording.startMs).toBe(MS(T0));
    expect(recording.endMs).toBe(MS("2026-01-01T00:00:09.000Z"));
  });

  it("an empty log yields an empty recording, not a fabricated one", () => {
    const recording = new EventLog().recording();
    expect(recording.frames).toHaveLength(0);
    expect(recording.events).toHaveLength(0);
  });
});

describe("frameAt — exact, never approximate", () => {
  const log = new EventLog();
  const a = state({ alerts: [alert("A-1")] });
  const b = state({ alerts: [alert("A-2")] });
  log.appendFrame(a, 1000, "t1");
  log.appendFrame(b, 2000, "t2");
  const recording = log.recording();

  it("returns the frame recorded at that exact moment", () => {
    expect(frameAt(recording, 1000)?.state).toBe(a);
    expect(frameAt(recording, 2000)?.state).toBe(b);
  });

  it("returns the latest frame at or before the moment — no interpolation", () => {
    // 1500 lies between two frames; the state at 1500 is the one recorded at 1000.
    expect(frameAt(recording, 1500)?.state).toBe(a);
  });

  it("returns null before the first frame rather than inventing a starting state", () => {
    expect(frameAt(recording, 500)).toBeNull();
  });

  it("returns the last frame beyond the end, never a predicted one", () => {
    expect(frameAt(recording, 999_999)?.state).toBe(b);
  });
});

// ---------------------------------------------------------------------------

describe("SessionRecorder — a passive observer", () => {
  it("records a frame per observation", () => {
    const recorder = new SessionRecorder();
    recorder.observe(state(), 1000, T0);
    recorder.observe(state(), 2000, T0);
    expect(recorder.log.frameCount).toBe(2);
  });

  it("never mutates the state it observes", () => {
    const recorder = new SessionRecorder();
    const observed = state({ alerts: [alert("A-1")] });
    const before = JSON.parse(JSON.stringify(observed));
    recorder.observe(observed, 1000, T0);
    expect(JSON.parse(JSON.stringify(observed))).toEqual(before);
  });

  it("emits nothing — it exposes no subscribe or emit surface", () => {
    const recorder = new SessionRecorder();
    for (const forbidden of ["emit", "subscribe", "connect", "sendAcknowledgement"]) {
      expect(recorder, `recorder must not expose ${forbidden}`).not.toHaveProperty(forbidden);
    }
  });

  it("logs no transition on the very first observation", () => {
    const recorder = new SessionRecorder();
    recorder.observe(withMode(state(), "NORMAL"), 1000, T0);
    expect(recorder.log.eventCount).toBe(0);
  });

  it("is deterministic — the same observations give the same recording", () => {
    const build = () => {
      const r = new SessionRecorder();
      r.observe(state(), 1000, T0);
      r.observe(state({ alerts: [alert("A-1")] }), 2000, T0);
      return r.log.entries().map((e) => e.event.eventId);
    };
    expect(build()).toEqual(build());
  });
});

describe("SessionRecorder — observable events only (M9D-C)", () => {
  const base = state();

  it("logs feed loss, carrying the supplied COMM_LOSS category in its payload", () => {
    const recorder = new SessionRecorder();
    recorder.observe(base, 1000, T0);
    recorder.observe(withStatus(base, "DISCONNECTED"), 2000, T0);
    const entry = recorder.log.entries()[0];
    expect(entry?.event.category).toBe("ALERT_RAISED");
    expect(entry?.origin).toBe("HMI_OBSERVED");
    expect((entry?.event.payload as { category?: string } | undefined)?.category).toBe("COMM_LOSS");
  });

  it("logs RECOVERY when the feed comes back", () => {
    const recorder = new SessionRecorder();
    recorder.observe(withStatus(base, "DISCONNECTED"), 1000, T0);
    recorder.observe(withStatus(base, "CONNECTED"), 2000, T0);
    expect(recorder.log.entries().map((e) => e.event.category)).toContain("RECOVERY");
  });

  it("logs a supplied MODE_TRANSITION, with both ends", () => {
    const recorder = new SessionRecorder();
    recorder.observe(withMode(base, "NORMAL"), 1000, T0);
    recorder.observe(withMode(base, "CAUTION"), 2000, T0);
    const entry = recorder.log.entries().find((e) => e.event.category === "MODE_TRANSITION");
    expect(entry?.event.payload).toEqual({ from: "NORMAL", to: "CAUTION" });
  });

  it("logs no MODE_TRANSITION when the supplied mode has not changed", () => {
    const recorder = new SessionRecorder();
    recorder.observe(withMode(base, "NORMAL"), 1000, T0);
    recorder.observe(withMode(base, "NORMAL"), 2000, T0);
    expect(recorder.log.entries().some((e) => e.event.category === "MODE_TRANSITION")).toBe(false);
  });

  it("logs ALERT_RAISED once, when an alert first appears", () => {
    const recorder = new SessionRecorder();
    recorder.observe(base, 1000, T0);
    recorder.observe(state({ alerts: [alert("A-1")] }), 2000, T0);
    recorder.observe(state({ alerts: [alert("A-1")] }), 3000, T0);
    const raised = recorder.log
      .entries()
      .filter((e) => e.event.category === "ALERT_RAISED" && e.event.subjectId === "A-1");
    expect(raised).toHaveLength(1);
  });

  it("carries the producer's severity and category on an alert event, unaltered", () => {
    const recorder = new SessionRecorder();
    recorder.observe(base, 1000, T0);
    recorder.observe(
      state({ alerts: [alert("A-1", { severity: "CRITICAL", category: "BOTTLENECK_RISK" })] }),
      2000,
      T0,
    );
    const entry = recorder.log.entries().find((e) => e.event.subjectId === "A-1");
    expect(entry?.event.payload).toMatchObject({
      severity: "CRITICAL",
      category: "BOTTLENECK_RISK",
    });
  });

  it("logs COMMAND_RECEIVED when a supplied command appears (FR-010 AC3)", () => {
    const recorder = new SessionRecorder();
    recorder.observe(base, 1000, T0);
    recorder.observe(state({ dispatch: { "C-1": command("C-1") } }), 2000, T0);
    const entry = recorder.log.entries().find((e) => e.event.category === "COMMAND_RECEIVED");
    expect(entry?.event.subjectId).toBe("C-1");
  });

  it("logs COMMAND_RECEIVED, never COMMAND_ISSUED — the HMI issues nothing", () => {
    const recorder = new SessionRecorder();
    recorder.observe(base, 1000, T0);
    recorder.observe(state({ dispatch: { "C-1": command("C-1") } }), 2000, T0);
    expect(recorder.log.entries().some((e) => e.event.category === "COMMAND_ISSUED")).toBe(false);
  });

  it("passes supplied events through verbatim, marked SUPPLIED", () => {
    const recorder = new SessionRecorder();
    const supplied = event("SUP-1", T0, "FOG_CHANGE");
    recorder.observe(state({ events: [supplied] }), 1000, T0);
    const entry = recorder.log.entries()[0];
    expect(entry?.event).toEqual(supplied);
    expect(entry?.origin).toBe("SUPPLIED");
  });

  it("NEVER fabricates FOG_CHANGE, QUEUE_CHANGE or VIOLATION", () => {
    const recorder = new SessionRecorder();
    // A rich transition: alerts, commands, mode change, feed loss, changing road values.
    recorder.observe(withMode(base, "NORMAL"), 1000, T0);
    recorder.observe(
      withStatus(
        withMode(
          state({
            alerts: [alert("A-1", { category: "BOTTLENECK_RISK" })],
            dispatch: { "C-1": command("C-1") },
          }),
          "STOP_UNSAFE",
        ),
        "DISCONNECTED",
      ),
      2000,
      T0,
    );
    const derived = recorder.log.entries().filter((e) => e.origin === "HMI_OBSERVED");
    for (const entry of derived) {
      expect(["FOG_CHANGE", "QUEUE_CHANGE", "VIOLATION"]).not.toContain(entry.event.category);
    }
    expect(derived.length).toBeGreaterThan(0);
  });

  it("derives only the approved observable categories", () => {
    const recorder = new SessionRecorder();
    recorder.observe(withMode(base, "NORMAL"), 1000, T0);
    recorder.observe(
      withStatus(withMode(state({ alerts: [alert("A-1")] }), "CAUTION"), "DISCONNECTED"),
      2000,
      T0,
    );
    for (const entry of recorder.log.entries().filter((e) => e.origin === "HMI_OBSERVED")) {
      expect(["ALERT_RAISED", "RECOVERY", "MODE_TRANSITION", "COMMAND_RECEIVED"]).toContain(
        entry.event.category,
      );
    }
  });

  it("marks every derived event with a namespaced id and no actor", () => {
    const recorder = new SessionRecorder();
    recorder.observe(base, 1000, T0);
    recorder.observe(withStatus(base, "DISCONNECTED"), 2000, T0);
    const entry = recorder.log.entries()[0];
    expect(entry?.event.eventId.startsWith("HMI-EV:")).toBe(true);
    // No operator is involved in an observation.
    expect(entry?.event.actor).toBeNull();
  });
});
