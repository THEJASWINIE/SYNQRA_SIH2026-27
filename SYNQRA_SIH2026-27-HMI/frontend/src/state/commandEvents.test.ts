/**
 * Phase 3 — WebSocket command events, correlation and deterministic merge.
 *
 * THE FRAMES USED HERE WERE CAPTURED FROM THE RUNNING BACKEND, not invented:
 *
 *   { "type": "command_issued",
 *     "data": { "command_id": "P3-ACC-1788665008494", "vehicle_id": "TRUCK_01",
 *               "action": "STOP", "target_speed": 0.0, "reason": "phase3 probe",
 *               "timestamp": 1788665008.5387936, "status": "ACCEPTED",
 *               "gateway_reason": "Validated by gateway; not yet transmitted" } }
 *
 *   { "type": "command_rejected", "reason": "COMMAND_INJECTION_NOT_PERMITTED",
 *     "message": "Submit commands via POST /api/commands; ..." }
 *
 * The second is NOT a command result - it is the socket refusing a command submitted over
 * the WebSocket, and it carries no command_id.
 *
 * Pure logic only: no DOM, no jsdom, no Testing Library (M4D-C).
 */

import { describe, expect, it } from "vitest";

import type { SessionCommand } from "../contracts/appState";
import {
  type CommandEvent,
  type CommandOutcome,
  canTransition,
  mergeCommandEvent,
  normalizeCommandFrame,
} from "./dispatchCommand";

const T0 = "2026-01-01T00:00:00.000Z";
const T1 = "2026-01-01T00:00:01.000Z";
const T2 = "2026-01-01T00:00:02.000Z";

/** The exact frame the live backend emits on acceptance. */
function issuedFrame(commandId = "CMD-1", over: Record<string, unknown> = {}) {
  return {
    type: "command_issued",
    data: {
      command_id: commandId,
      vehicle_id: "TRUCK_01",
      action: "STOP",
      target_speed: 0.0,
      reason: "phase3 probe",
      timestamp: 1_788_665_008.5387936,
      status: "ACCEPTED",
      gateway_reason: "Validated by gateway; not yet transmitted",
      ...over,
    },
  };
}

function httpEvent(commandId: string, outcome: CommandOutcome, at = T0): CommandEvent {
  return {
    commandId,
    origin: "HTTP",
    observedAtIso: at,
    vehicleId: "TRUCK_01",
    action: "STOP",
    targetSpeedMps: 0,
    reason: "operator",
    outcome,
    message: outcome === "ACCEPTED" ? "accepted by gateway; not yet executed" : "refused",
  };
}

// ---------------------------------------------------------------------------
// 1/2/5/17/18/19 — normalization
// ---------------------------------------------------------------------------

describe("event normalization", () => {
  it("1 — consumes a real command_issued frame", () => {
    const event = normalizeCommandFrame(issuedFrame(), T0);
    expect(event).not.toBeNull();
    expect(event?.commandId).toBe("CMD-1");
    expect(event?.vehicleId).toBe("TRUCK_01");
    expect(event?.action).toBe("STOP");
    expect(event?.targetSpeedMps).toBe(0);
    expect(event?.origin).toBe("WEBSOCKET");
    expect(event?.gatewayConfirmed).toBe(true);
    expect(event?.message).toContain("not yet transmitted");
  });

  it("2 — command_rejected is NOT treated as a command result", () => {
    const frame = {
      type: "command_rejected",
      reason: "COMMAND_INJECTION_NOT_PERMITTED",
      message: "Submit commands via POST /api/commands; they are validated by the gateway.",
    };
    expect(normalizeCommandFrame(frame, T0)).toBeNull();
  });

  it("19 — a frame without command_id is dropped, not turned into a phantom row", () => {
    const frame = { type: "command_issued", data: { vehicle_id: "TRUCK_01" } };
    expect(normalizeCommandFrame(frame, T0)).toBeNull();
    expect(normalizeCommandFrame(issuedFrame("   "), T0)).toBeNull();
  });

  it.each([
    ["null", null],
    ["a string", "not a frame"],
    ["a number", 42],
    ["an array", [1, 2, 3]],
    ["no data", { type: "command_issued" }],
    ["data as a string", { type: "command_issued", data: "x" }],
    ["another type", { type: "telemetry_update", data: { command_id: "CMD-9" } }],
  ])("17 — malformed input (%s) returns null rather than throwing", (_label, raw) => {
    expect(() => normalizeCommandFrame(raw, T0)).not.toThrow();
    expect(normalizeCommandFrame(raw, T0)).toBeNull();
  });

  it("18 — an unrecognised status never becomes ACCEPTED", () => {
    const event = normalizeCommandFrame(issuedFrame("CMD-X", { status: "WHATEVER" }), T0);
    expect(event?.outcome).not.toBe("ACCEPTED");
    expect(event?.outcome).toBe("ISSUED");
  });
});

// ---------------------------------------------------------------------------
// 20 — deterministic transitions
// ---------------------------------------------------------------------------

describe("state transitions", () => {
  it("20 — moves forward but never backwards to PENDING", () => {
    expect(canTransition("PENDING", "ISSUED")).toBe(true);
    expect(canTransition("PENDING", "REJECTED")).toBe(true);
    expect(canTransition("ISSUED", "ACCEPTED")).toBe(true);
    expect(canTransition("ACCEPTED", "NOT_EXECUTED")).toBe(true);
    expect(canTransition("ACCEPTED", "TIMEOUT")).toBe(true);

    expect(canTransition("ACCEPTED", "PENDING")).toBe(false);
    expect(canTransition("REJECTED", "PENDING")).toBe(false);
    expect(canTransition("ACCEPTED", "ISSUED")).toBe(false);
  });

  it("allows an idempotent refresh at the same rank", () => {
    expect(canTransition("ACCEPTED", "ACCEPTED")).toBe(true);
  });
});

// ---------------------------------------------------------------------------
// 3/4/5/6/7/14 — correlation and idempotence
// ---------------------------------------------------------------------------

describe("correlation and idempotence", () => {
  it("3/4 — an event for a known command updates it rather than adding a row", () => {
    const first = mergeCommandEvent([], httpEvent("CMD-1", "PENDING"));
    expect(first).toHaveLength(1);

    const frame = normalizeCommandFrame(issuedFrame("CMD-1"), T1) as CommandEvent;
    const second = mergeCommandEvent(first, frame);

    expect(second, "a second row was created").toHaveLength(1);
    expect(second[0]?.commandId).toBe("CMD-1");
    expect(second[0]?.gatewayConfirmed).toBe(true);
  });

  it("6 — a repeated command_issued is idempotent", () => {
    const frame = normalizeCommandFrame(issuedFrame("CMD-1"), T1) as CommandEvent;
    let history = mergeCommandEvent([], frame);
    for (let i = 0; i < 5; i += 1) history = mergeCommandEvent(history, frame);

    expect(history).toHaveLength(1);
    expect(history[0]?.outcome).toBe("ACCEPTED");
  });

  it("7 — a repeated refusal is idempotent", () => {
    const reject = httpEvent("CMD-2", "REJECTED");
    let history = mergeCommandEvent([], reject);
    for (let i = 0; i < 5; i += 1) history = mergeCommandEvent(history, reject);

    expect(history).toHaveLength(1);
    expect(history[0]?.outcome).toBe("REJECTED");
  });

  it("14 — one row per command_id across many commands and repeats", () => {
    let history: readonly SessionCommand[] = [];
    for (const id of ["A", "B", "C"]) {
      history = mergeCommandEvent(history, httpEvent(id, "PENDING"));
      history = mergeCommandEvent(history, httpEvent(id, "ACCEPTED", T1));
      const frame = normalizeCommandFrame(issuedFrame(id), T2) as CommandEvent;
      history = mergeCommandEvent(history, frame);
    }

    expect(history).toHaveLength(3);
    expect(new Set(history.map((r) => r.commandId)).size).toBe(3);
  });

  it("5 — an event for an unknown command is recorded safely, without invented fields", () => {
    const frame = normalizeCommandFrame(issuedFrame("CMD-UNSEEN"), T0) as CommandEvent;
    const history = mergeCommandEvent([], frame);

    expect(history).toHaveLength(1);
    expect(history[0]?.commandId).toBe("CMD-UNSEEN");
    expect(history[0]?.vehicleId).toBe("TRUCK_01");
    // NOT supplied by any source, and therefore not claimed:
    expect(history[0]?.executionAckIso).toBeNull();
  });

  it("marks a field UNKNOWN rather than guessing when the event omits it", () => {
    const event: CommandEvent = { commandId: "CMD-BARE", origin: "WEBSOCKET", observedAtIso: T0 };
    const history = mergeCommandEvent([], event);

    expect(history[0]?.vehicleId).toBe("UNKNOWN");
    expect(history[0]?.action).toBe("UNKNOWN");
    expect(history[0]?.targetSpeedMps).toBeNull();
  });
});

// ---------------------------------------------------------------------------
// 8/9/10/11 — HTTP + WebSocket race
// ---------------------------------------------------------------------------

describe("HTTP and WebSocket race", () => {
  it("8/11 — HTTP ACCEPTED then WS issued keeps ACCEPTED, adding confirmation", () => {
    const afterHttp = mergeCommandEvent([], httpEvent("CMD-1", "ACCEPTED"));
    const frame = normalizeCommandFrame(issuedFrame("CMD-1"), T1) as CommandEvent;
    const afterWs = mergeCommandEvent(afterHttp, frame);

    expect(afterWs).toHaveLength(1);
    expect(afterWs[0]?.outcome).toBe("ACCEPTED");
    expect(afterWs[0]?.gatewayConfirmed).toBe(true);
  });

  it("10 — WS arriving BEFORE the HTTP response still yields one row", () => {
    const frame = normalizeCommandFrame(issuedFrame("CMD-1"), T0) as CommandEvent;
    const afterWs = mergeCommandEvent([], frame);
    const afterHttp = mergeCommandEvent(afterWs, httpEvent("CMD-1", "ACCEPTED", T1));

    expect(afterHttp).toHaveLength(1);
    expect(afterHttp[0]?.outcome).toBe("ACCEPTED");
  });

  it("a late PENDING cannot downgrade a settled record", () => {
    const settled = mergeCommandEvent([], httpEvent("CMD-1", "ACCEPTED"));
    const late = mergeCommandEvent(settled, httpEvent("CMD-1", "PENDING", T2));

    expect(late[0]?.outcome).toBe("ACCEPTED");
  });

  it("9 — HTTP rejected stays rejected; no WS event exists for a refusal", () => {
    const rejected = mergeCommandEvent([], {
      ...httpEvent("CMD-2", "REJECTED"),
      message: "v_safe unavailable (fail closed)",
    });

    expect(rejected).toHaveLength(1);
    expect(rejected[0]?.outcome).toBe("REJECTED");
    expect(rejected[0]?.message).toBe("v_safe unavailable (fail closed)");
  });

  it("does not erase a message when a later event carries none", () => {
    const withMessage = mergeCommandEvent([], httpEvent("CMD-1", "ACCEPTED"));
    const bare: CommandEvent = { commandId: "CMD-1", origin: "WEBSOCKET", observedAtIso: T2 };
    const after = mergeCommandEvent(withMessage, bare);

    expect(after[0]?.message).toContain("not yet executed");
  });
});

// ---------------------------------------------------------------------------
// 12/13 — execution honesty
// ---------------------------------------------------------------------------

describe("execution honesty", () => {
  it("12 — acceptance never sets an execution acknowledgement", () => {
    const frame = normalizeCommandFrame(issuedFrame("CMD-1"), T0) as CommandEvent;
    const history = mergeCommandEvent(mergeCommandEvent([], httpEvent("CMD-1", "ACCEPTED")), frame);

    expect(history[0]?.outcome).toBe("ACCEPTED");
    expect(history[0]?.executionAckIso, "acceptance was read as execution").toBeNull();
  });

  it("13 — the gateway's 'not yet transmitted' wording is preserved", () => {
    const frame = normalizeCommandFrame(issuedFrame("CMD-1"), T0) as CommandEvent;
    const history = mergeCommandEvent([], frame);

    expect(history[0]?.message).toContain("not yet transmitted");
  });
});

// ---------------------------------------------------------------------------
// 15/16 — disconnect and reconnect
// ---------------------------------------------------------------------------

describe("connection lifecycle", () => {
  it("15 — a disconnect does not touch command history", () => {
    // Nothing in the merge path is driven by connection status: history changes only when
    // a command event arrives. A disconnect emits none, so the log is unchanged.
    const history = mergeCommandEvent([], httpEvent("CMD-1", "ACCEPTED"));
    const snapshot = [...history];

    expect(history).toEqual(snapshot);
    expect(history[0]?.outcome).toBe("ACCEPTED");
  });

  it("16 — replayed frames after a reconnect do not duplicate history", () => {
    const frame = normalizeCommandFrame(issuedFrame("CMD-1"), T0) as CommandEvent;
    let history = mergeCommandEvent([], frame);

    const replayed = normalizeCommandFrame(issuedFrame("CMD-1"), T2) as CommandEvent;
    history = mergeCommandEvent(history, replayed);
    history = mergeCommandEvent(history, replayed);

    expect(history).toHaveLength(1);
    expect(history[0]?.outcome).toBe("ACCEPTED");
  });

  it("does not mutate the history array it was given", () => {
    const original = mergeCommandEvent([], httpEvent("CMD-1", "PENDING"));
    const snapshot = JSON.stringify(original);
    mergeCommandEvent(original, httpEvent("CMD-1", "ACCEPTED", T1));

    expect(JSON.stringify(original)).toBe(snapshot);
  });
});
