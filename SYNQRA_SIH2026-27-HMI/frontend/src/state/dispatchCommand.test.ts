/**
 * S4 dispatch command logic — Phase 2.
 *
 * The HMI test architecture is `react-dom/server` with no DOM (M4D-C), so the command
 * logic lives outside React and is tested here directly. That covers validation, payload
 * construction, id uniqueness, result wording and the history reducer.
 *
 * Nothing here asserts a safety decision: the frontend makes none.
 */

import { describe, expect, it } from "vitest";

import {
  __resetCommandCounter,
  buildCommandPayload,
  type CommandHistoryEntry,
  type CommandOutcome,
  DEFAULT_REASON,
  DISPATCH_ACTIONS,
  HISTORY_LIMIT,
  nextCommandId,
  OUTCOME_DETAIL,
  OUTCOME_LABEL,
  requiresConfirmation,
  requiresTargetSpeed,
  upsertHistory,
  validateTargetSpeed,
} from "./dispatchCommand";

// ---------------------------------------------------------------------------
// C/D/E — target speed validation
// ---------------------------------------------------------------------------

describe("target speed validation", () => {
  it("accepts a positive decimal speed", () => {
    const result = validateTargetSpeed("2.5");
    expect(result.ok).toBe(true);
    expect(result.value).toBe(2.5);
    expect(result.error).toBeNull();
  });

  it("accepts zero as a real requested speed", () => {
    expect(validateTargetSpeed("0").ok).toBe(true);
    expect(validateTargetSpeed("0").value).toBe(0);
  });

  it("D — rejects a negative target speed", () => {
    const result = validateTargetSpeed("-5");
    expect(result.ok).toBe(false);
    expect(result.value).toBeNull();
    expect(result.error).toContain("negative");
  });

  it.each(["abc", "fast", "1.2.3", "NaN", "--", "1e"])(
    "E — rejects non-numeric input %s",
    (raw) => {
      const result = validateTargetSpeed(raw);
      expect(result.ok, `${raw} was accepted`).toBe(false);
      expect(result.value).toBeNull();
    },
  );

  it("rejects an empty field for TARGET_SPEED", () => {
    expect(validateTargetSpeed("").ok).toBe(false);
    expect(validateTargetSpeed("   ").ok).toBe(false);
  });

  it("rejects Infinity, which is numeric but not a speed", () => {
    expect(validateTargetSpeed("Infinity").ok).toBe(false);
    expect(validateTargetSpeed("-Infinity").ok).toBe(false);
  });
});

// ---------------------------------------------------------------------------
// action semantics
// ---------------------------------------------------------------------------

describe("action semantics", () => {
  it("offers exactly the four backend-supported actions", () => {
    expect([...DISPATCH_ACTIONS]).toEqual(["TARGET_SPEED", "HOLD", "STOP", "RELEASE"]);
  });

  it("needs a target speed only for TARGET_SPEED", () => {
    expect(requiresTargetSpeed("TARGET_SPEED")).toBe(true);
    for (const action of ["HOLD", "STOP", "RELEASE"] as const) {
      expect(requiresTargetSpeed(action), action).toBe(false);
    }
  });

  it("F — requires confirmation for STOP and nothing else", () => {
    expect(requiresConfirmation("STOP")).toBe(true);
    for (const action of ["TARGET_SPEED", "HOLD", "RELEASE"] as const) {
      expect(requiresConfirmation(action), action).toBe(false);
    }
  });
});

// ---------------------------------------------------------------------------
// I — payload shape
// ---------------------------------------------------------------------------

describe("command payload", () => {
  it("I — builds the exact backend request shape", () => {
    const built = buildCommandPayload(
      { vehicleId: "TRUCK_01", action: "TARGET_SPEED", targetSpeedRaw: "2.5", reason: "fog" },
      "CMD-1",
    );
    expect(built.ok).toBe(true);
    if (!built.ok) return;

    expect(built.payload).toEqual({
      command_id: "CMD-1",
      vehicle_id: "TRUCK_01",
      action: "TARGET_SPEED",
      target_speed: 2.5,
      reason: "fog",
    });
    // Exactly the five contract fields - nothing extra is sent.
    expect(Object.keys(built.payload).sort()).toEqual([
      "action",
      "command_id",
      "reason",
      "target_speed",
      "vehicle_id",
    ]);
  });

  it("sends the typed value in m/s without converting it", () => {
    const built = buildCommandPayload(
      { vehicleId: "TRUCK_01", action: "TARGET_SPEED", targetSpeedRaw: "3", reason: "" },
      "CMD-2",
    );
    expect(built.ok && built.payload.target_speed).toBe(3);
    // 3 m/s must NOT become 10.8 (km/h) or 0.83 (a km/h->m/s conversion).
    expect(built.ok && built.payload.target_speed).not.toBe(10.8);
  });

  it("uses the backend's own default reason when none is typed", () => {
    const built = buildCommandPayload(
      { vehicleId: "TRUCK_01", action: "HOLD", targetSpeedRaw: "", reason: "  " },
      "CMD-3",
    );
    expect(built.ok && built.payload.reason).toBe(DEFAULT_REASON);
  });

  it("sends target_speed 0 for actions that carry no speed", () => {
    for (const action of ["HOLD", "STOP", "RELEASE"] as const) {
      const built = buildCommandPayload(
        { vehicleId: "TRUCK_01", action, targetSpeedRaw: "", reason: "" },
        `CMD-${action}`,
      );
      expect(built.ok, action).toBe(true);
      expect(built.ok && built.payload.target_speed, action).toBe(0);
    }
  });

  it("refuses to build without a vehicle", () => {
    const built = buildCommandPayload(
      { vehicleId: null, action: "STOP", targetSpeedRaw: "", reason: "" },
      "CMD-4",
    );
    expect(built.ok).toBe(false);
    expect(!built.ok && built.error).toContain("Select a vehicle");
  });

  it("refuses to build an invalid TARGET_SPEED", () => {
    for (const raw of ["-1", "abc", ""]) {
      const built = buildCommandPayload(
        { vehicleId: "TRUCK_01", action: "TARGET_SPEED", targetSpeedRaw: raw, reason: "" },
        "CMD-5",
      );
      expect(built.ok, raw).toBe(false);
    }
  });
});

// ---------------------------------------------------------------------------
// J — command_id uniqueness
// ---------------------------------------------------------------------------

describe("command_id", () => {
  it("J — never repeats, even within the same millisecond", () => {
    __resetCommandCounter();
    const ids = new Set<string>();
    for (let i = 0; i < 500; i += 1) {
      ids.add(nextCommandId("TRUCK_01", "STOP", 1_788_000_000_000, "fixed"));
    }
    expect(ids.size).toBe(500);
  });

  it("carries the vehicle and action so a log line is readable", () => {
    __resetCommandCounter();
    const id = nextCommandId("TRUCK_02", "TARGET_SPEED", 1_788_000_000_000, "abc123");
    expect(id).toContain("TRUCK_02");
    expect(id).toContain("TARGET_SPEED");
  });

  it("differs between two vehicles", () => {
    __resetCommandCounter();
    const a = nextCommandId("TRUCK_01", "STOP", 1_788_000_000_000, "x");
    const b = nextCommandId("TRUCK_02", "STOP", 1_788_000_000_000, "x");
    expect(a).not.toBe(b);
  });
});

// ---------------------------------------------------------------------------
// K/L/M/N/T — outcome wording
// ---------------------------------------------------------------------------

const ALL_OUTCOMES: CommandOutcome[] = [
  "PENDING",
  "ACCEPTED",
  "REJECTED",
  "UNKNOWN_VEHICLE",
  "DUPLICATE",
  "INVALID",
  "UNSAFE",
  "TIMEOUT",
  "NOT_EXECUTED",
  "NETWORK_ERROR",
];

describe("outcome wording", () => {
  it("labels and explains every supported outcome", () => {
    for (const outcome of ALL_OUTCOMES) {
      expect(OUTCOME_LABEL[outcome], outcome).toBeTruthy();
      expect(OUTCOME_DETAIL[outcome], outcome).toBeTruthy();
    }
  });

  it("T — ACCEPTED never claims the vehicle executed anything", () => {
    expect(OUTCOME_DETAIL.ACCEPTED).toContain("not yet acknowledged");
    for (const outcome of ALL_OUTCOMES) {
      const text = `${OUTCOME_LABEL[outcome]} ${OUTCOME_DETAIL[outcome]}`.toLowerCase();
      expect(text, outcome).not.toContain("vehicle stopped");
      expect(text, outcome).not.toContain("vehicle is stopped");
      expect(text, outcome).not.toContain("executed successfully");
    }
  });

  it("L/M/N — a refusal says the vehicle was not commanded", () => {
    expect(OUTCOME_DETAIL.REJECTED).toContain("not commanded");
    expect(OUTCOME_DETAIL.UNKNOWN_VEHICLE).toContain("Nothing was sent");
    expect(OUTCOME_DETAIL.DUPLICATE).toContain("Nothing new was sent");
  });

  it("a network failure states the command reached no vehicle", () => {
    expect(OUTCOME_DETAIL.NETWORK_ERROR).toContain("NOT sent to any vehicle");
  });
});

// ---------------------------------------------------------------------------
// S — session history
// ---------------------------------------------------------------------------

function entry(over: Partial<CommandHistoryEntry> = {}): CommandHistoryEntry {
  return {
    commandId: "CMD-1",
    vehicleId: "TRUCK_01",
    action: "STOP",
    targetSpeedMps: null,
    outcome: "PENDING",
    message: null,
    reason: DEFAULT_REASON,
    submittedAtIso: "2026-01-01T00:00:00.000Z",
    updatedAtIso: "2026-01-01T00:00:00.000Z",
    gatewayConfirmed: false,
    executionAckIso: null,
    ...over,
  };
}

describe("session command history", () => {
  it("S — records a submitted command", () => {
    const history = upsertHistory([], entry());
    expect(history).toHaveLength(1);
    expect(history[0]?.commandId).toBe("CMD-1");
    expect(history[0]?.outcome).toBe("PENDING");
  });

  it("updates a command in place rather than duplicating it", () => {
    const pending = upsertHistory([], entry());
    const settled = upsertHistory(pending, entry({ outcome: "ACCEPTED", message: "ok" }));

    expect(settled).toHaveLength(1);
    expect(settled[0]?.outcome).toBe("ACCEPTED");
    expect(settled[0]?.message).toBe("ok");
  });

  it("keeps distinct commands as separate rows, newest first", () => {
    const first = upsertHistory([], entry({ commandId: "CMD-1" }));
    const second = upsertHistory(first, entry({ commandId: "CMD-2" }));

    expect(second.map((r) => r.commandId)).toEqual(["CMD-2", "CMD-1"]);
  });

  it("stays bounded", () => {
    let history: readonly CommandHistoryEntry[] = [];
    for (let i = 0; i < HISTORY_LIMIT + 25; i += 1) {
      history = upsertHistory(history, entry({ commandId: `CMD-${i}` }));
    }
    expect(history).toHaveLength(HISTORY_LIMIT);
    // The newest survives; the oldest is dropped.
    expect(history[0]?.commandId).toBe(`CMD-${HISTORY_LIMIT + 24}`);
  });

  it("does not mutate the array it was given", () => {
    const original = upsertHistory([], entry());
    const snapshot = [...original];
    upsertHistory(original, entry({ commandId: "CMD-2" }));
    expect(original).toEqual(snapshot);
  });
});
