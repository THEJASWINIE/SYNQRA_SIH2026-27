/**
 * S4 Dispatch — command construction, validation and result interpretation.
 *
 * ==========================================================================
 *  THIS MODULE MAKES NO SAFETY DECISION.
 *
 *  It validates OPERATOR INPUT (is this a number? is it negative?) and it CLASSIFIES a
 *  response the backend already produced. It never decides whether a speed is safe -
 *  that is the CommandGateway's judgement, reached from the canonical Twin's v_safe, and
 *  the frontend only reports what came back.
 *
 *  It computes no v_safe, holds no vehicle state, and issues no request. The transport
 *  lives in `api/commandClient.ts`; React only wires the two together.
 * ==========================================================================
 *
 * Pure and framework-free on purpose: the HMI test architecture is `react-dom/server`
 * with no DOM (M4D-C), so logic that must be tested cannot live inside a component.
 * Same split as `state/operatorAction.ts`.
 */

import type { SessionCommand } from "../contracts/appState";

/** Actions the backend accepts. Mirrors `HMICommandRequest.action` validation. */
export const DISPATCH_ACTIONS = ["TARGET_SPEED", "HOLD", "STOP", "RELEASE"] as const;
export type DispatchAction = (typeof DISPATCH_ACTIONS)[number];

/** Actions that are destructive/defensive and require explicit confirmation. */
export const CONFIRM_REQUIRED: readonly DispatchAction[] = ["STOP"];

/** The backend's own default when `reason` is omitted (`HMICommandRequest.reason`). */
export const DEFAULT_REASON = "HMI_OPERATOR_DISPATCH";

/**
 * The wire payload. Field names and units are the backend's, not the HMI's.
 * `target_speed` is METRES PER SECOND - the contract's unit. No conversion happens here.
 */
export interface CommandRequestPayload {
  command_id: string;
  vehicle_id: string;
  action: DispatchAction;
  target_speed: number;
  reason: string;
}

/**
 * Outcomes this screen can render.
 *
 * PENDING and NETWORK_ERROR are CLIENT-side states - the request is in flight, or never
 * reached the backend. Everything else is a status the backend actually returned; none of
 * them is inferred.
 */
export type CommandOutcome =
  | "PENDING"
  /** Phase 3: the gateway confirmed the command over the WebSocket. */
  | "ISSUED"
  | "ACCEPTED"
  | "REJECTED"
  | "UNKNOWN_VEHICLE"
  | "DUPLICATE"
  | "INVALID"
  | "UNSAFE"
  | "TIMEOUT"
  | "NOT_EXECUTED"
  | "NETWORK_ERROR";

/** Operator-facing wording. Never claims execution. */
export const OUTCOME_LABEL: Record<CommandOutcome, string> = {
  PENDING: "SUBMITTING",
  ISSUED: "ISSUED",
  ACCEPTED: "ACCEPTED",
  REJECTED: "REJECTED",
  UNKNOWN_VEHICLE: "UNKNOWN VEHICLE",
  DUPLICATE: "DUPLICATE",
  INVALID: "INVALID",
  UNSAFE: "UNSAFE",
  TIMEOUT: "TIMEOUT",
  NOT_EXECUTED: "NOT EXECUTED",
  NETWORK_ERROR: "NOT DELIVERED",
};

/**
 * What each outcome means for the OPERATOR.
 *
 * ACCEPTED deliberately does NOT say the vehicle did anything. The backend's own message
 * is "not yet executed"; the gateway validated and recorded the command, and nothing more
 * has been observed. Saying "vehicle stopped" here would be a fabricated execution claim.
 */
export const OUTCOME_DETAIL: Record<CommandOutcome, string> = {
  PENDING: "Sending to the Command Gateway…",
  ISSUED: "Issued to the Command Gateway — execution not yet acknowledged.",
  ACCEPTED: "Command accepted by gateway — execution not yet acknowledged.",
  REJECTED: "Refused by the Command Gateway. The vehicle was not commanded.",
  UNKNOWN_VEHICLE: "The gateway does not recognise this vehicle. Nothing was sent.",
  DUPLICATE: "This command_id was already accepted. Nothing new was sent.",
  INVALID: "The gateway rejected the command as invalid. Nothing was sent.",
  UNSAFE: "Refused: the requested speed exceeds the authoritative safe speed.",
  TIMEOUT: "Accepted earlier, but no acknowledgement arrived within the timeout.",
  NOT_EXECUTED: "Recorded by the gateway. No execution has been acknowledged.",
  NETWORK_ERROR: "The command did not reach the backend. It was NOT sent to any vehicle.",
};

/**
 * Label/detail for an outcome string that may not be one we know.
 *
 * An UNRECOGNISED status is shown as itself and explained as unrecognised - it is never
 * silently rendered as ACCEPTED, and never assumed to mean success.
 */
export function outcomeLabel(outcome: string): string {
  return OUTCOME_LABEL[outcome as CommandOutcome] ?? outcome;
}

export function outcomeDetail(outcome: string): string {
  return (
    OUTCOME_DETAIL[outcome as CommandOutcome] ??
    "Unrecognised status reported by the backend. Not treated as success."
  );
}

/** Outcomes meaning the command definitively did not reach a vehicle. */
export const REFUSED_OUTCOMES: readonly CommandOutcome[] = [
  "REJECTED",
  "UNKNOWN_VEHICLE",
  "DUPLICATE",
  "INVALID",
  "UNSAFE",
  "NETWORK_ERROR",
];

// ---------------------------------------------------------------------------
// command_id
// ---------------------------------------------------------------------------

/**
 * A unique command id.
 *
 * Every submission gets a fresh one, so a retry after a failure is a NEW command and can
 * never be mistaken by the gateway for an idempotent replay. A deliberate resubmission of
 * the same id is possible only by passing that id explicitly.
 */
let commandCounter = 0;

export function nextCommandId(
  vehicleId: string,
  action: DispatchAction,
  nowMs: number = Date.now(),
  randomPart: string = Math.random().toString(36).slice(2, 8),
): string {
  commandCounter += 1;
  return `HMI-${vehicleId}-${action}-${nowMs}-${commandCounter}-${randomPart}`;
}

/** Test seam: reset the monotonic part so ids are deterministic in tests. */
export function __resetCommandCounter(): void {
  commandCounter = 0;
}

// ---------------------------------------------------------------------------
// input validation — OPERATOR INPUT ONLY, never a safety judgement
// ---------------------------------------------------------------------------

export interface SpeedValidation {
  ok: boolean;
  /** Parsed m/s, only when ok. */
  value: number | null;
  /** Operator-readable problem, only when not ok. */
  error: string | null;
}

/**
 * Validate the target-speed field.
 *
 * Rejects what cannot be a speed at all. It does NOT decide whether the speed is safe -
 * an in-range value can still be refused by the gateway, and that refusal is the
 * authoritative one.
 */
export function validateTargetSpeed(raw: string): SpeedValidation {
  const trimmed = raw.trim();
  if (trimmed === "") {
    return { ok: false, value: null, error: "Target speed is required for TARGET_SPEED." };
  }
  const parsed = Number(trimmed);
  if (!Number.isFinite(parsed)) {
    return { ok: false, value: null, error: "Target speed must be a number (m/s)." };
  }
  if (parsed < 0) {
    return { ok: false, value: null, error: "Target speed cannot be negative." };
  }
  return { ok: true, value: parsed, error: null };
}

/** Whether the action needs the target-speed field at all. */
export function requiresTargetSpeed(action: DispatchAction): boolean {
  return action === "TARGET_SPEED";
}

/** Whether the action must be confirmed before it is sent. */
export function requiresConfirmation(action: DispatchAction): boolean {
  return CONFIRM_REQUIRED.includes(action);
}

export interface FormInput {
  vehicleId: string | null;
  action: DispatchAction;
  targetSpeedRaw: string;
  reason: string;
}

export type BuildResult =
  | { ok: true; payload: CommandRequestPayload }
  | { ok: false; error: string };

/**
 * Build the wire payload from operator input.
 *
 * `target_speed` is sent in m/s exactly as typed - the backend contract's unit. Nothing is
 * converted here, so a km/h number cannot silently become an m/s command.
 */
export function buildCommandPayload(input: FormInput, commandId: string): BuildResult {
  if (!input.vehicleId) {
    return { ok: false, error: "Select a vehicle before dispatching a command." };
  }

  let targetSpeed = 0;
  if (requiresTargetSpeed(input.action)) {
    const validated = validateTargetSpeed(input.targetSpeedRaw);
    if (!validated.ok || validated.value === null) {
      return { ok: false, error: validated.error ?? "Invalid target speed." };
    }
    targetSpeed = validated.value;
  }

  const reason = input.reason.trim();
  return {
    ok: true,
    payload: {
      command_id: commandId,
      vehicle_id: input.vehicleId,
      action: input.action,
      target_speed: targetSpeed,
      reason: reason === "" ? DEFAULT_REASON : reason,
    },
  };
}

// ---------------------------------------------------------------------------
// history — bounded session log
// ---------------------------------------------------------------------------

/**
 * Phase 3: the history entry IS the shared session record. Phase 2 kept its own local
 * shape; converging on one type is what makes a single shared command source possible.
 */
export type CommandHistoryEntry = SessionCommand;

/** Bounded so a long shift cannot grow session state without limit. */
export const HISTORY_LIMIT = 50;

/**
 * Add or update one entry, newest first.
 *
 * A submission appears immediately as PENDING and is then UPDATED IN PLACE by command_id
 * when the response lands - so one command is one row, never two.
 */
export function upsertHistory(
  history: readonly SessionCommand[],
  entry: SessionCommand,
): SessionCommand[] {
  const existing = history.findIndex((row) => row.commandId === entry.commandId);
  if (existing >= 0) {
    const next = [...history];
    next[existing] = entry;
    return next;
  }
  return [entry, ...history].slice(0, HISTORY_LIMIT);
}

// ===========================================================================
// PHASE 3 — WebSocket command events, correlation and deterministic merge
// ===========================================================================

/**
 * WHAT THE BACKEND ACTUALLY EMITS (verified against the running service).
 *
 *   command_issued   broadcast to every client, ONLY when the gateway ACCEPTED a command:
 *     { type: "command_issued", data: { command_id, vehicle_id, action, target_speed,
 *                                       reason, timestamp, status, gateway_reason } }
 *
 *   command_rejected NOT a command result. It is the socket's refusal to accept a command
 *     submitted over the WebSocket, and carries NO command_id:
 *     { type: "command_rejected", reason: "COMMAND_INJECTION_NOT_PERMITTED", message }
 *
 * A REFUSED command therefore emits NO WebSocket event at all - the HTTP response is the
 * only record of it. This module treats `command_rejected` as the injection refusal it
 * really is and never lets it touch command history.
 */

/** Where a piece of information about a command came from. */
export type CommandEventOrigin = "HTTP" | "WEBSOCKET";

export interface CommandEvent {
  commandId: string;
  origin: CommandEventOrigin;
  observedAtIso: string;
  vehicleId?: string | null;
  action?: string | null;
  targetSpeedMps?: number | null;
  reason?: string | null;
  outcome?: CommandOutcome | null;
  message?: string | null;
  /** True when the gateway itself confirmed the command over the socket. */
  gatewayConfirmed?: boolean;
}

/**
 * How far along a command is. A merge never moves BACKWARDS.
 *
 * Without this, a `command_issued` frame arriving after an HTTP ACCEPTED could downgrade a
 * settled record, and a duplicated frame could resurrect a finished one.
 */
const OUTCOME_RANK: Record<CommandOutcome, number> = {
  PENDING: 0,
  ISSUED: 1,
  ACCEPTED: 2,
  // Terminal: nothing further is expected without new authoritative information.
  NOT_EXECUTED: 3,
  TIMEOUT: 3,
  REJECTED: 3,
  UNKNOWN_VEHICLE: 3,
  DUPLICATE: 3,
  INVALID: 3,
  UNSAFE: 3,
  NETWORK_ERROR: 3,
};

/** Whether `next` may replace `current`. Equal ranks are allowed (idempotent refresh). */
export function canTransition(current: CommandOutcome, next: CommandOutcome): boolean {
  return OUTCOME_RANK[next] >= OUTCOME_RANK[current];
}

/**
 * Normalize one raw WebSocket frame into a CommandEvent.
 *
 * Returns null for anything that is not a usable command event - including
 * `command_rejected`, which carries no command_id and is not a command result. Never
 * throws: a malformed frame must not take down the provider.
 */
export function normalizeCommandFrame(raw: unknown, observedAtIso: string): CommandEvent | null {
  if (typeof raw !== "object" || raw === null) return null;
  const frame = raw as Record<string, unknown>;
  if (frame.type !== "command_issued") return null;

  const data = frame.data;
  if (typeof data !== "object" || data === null) return null;
  const body = data as Record<string, unknown>;

  const commandId = body.command_id;
  // Without a command_id there is nothing to correlate; dropping it is safer than
  // inventing an identity and creating a phantom row.
  if (typeof commandId !== "string" || commandId.trim() === "") return null;

  const rawStatus = typeof body.status === "string" ? body.status.toUpperCase() : null;
  const outcome: CommandOutcome =
    rawStatus === "ACCEPTED" ? "ACCEPTED" : rawStatus === "ISSUED" ? "ISSUED" : "ISSUED";

  return {
    commandId,
    origin: "WEBSOCKET",
    observedAtIso,
    vehicleId: typeof body.vehicle_id === "string" ? body.vehicle_id : null,
    action: typeof body.action === "string" ? body.action : null,
    targetSpeedMps: typeof body.target_speed === "number" ? body.target_speed : null,
    reason: typeof body.reason === "string" ? body.reason : null,
    outcome,
    message: typeof body.gateway_reason === "string" ? body.gateway_reason : null,
    gatewayConfirmed: true,
  };
}

/**
 * Merge one event into the session log. ONE command_id -> ONE record, always.
 *
 * Rules:
 *   * an unseen command_id creates a record, but only from the fields the event supplied
 *   * a known command_id UPDATES that record in place - never appends a second row
 *   * the outcome only moves forward (see `canTransition`), so a late or repeated frame
 *     cannot downgrade a settled result
 *   * a field the event did not supply is left alone; nothing is overwritten with null
 */
export function mergeCommandEvent(
  history: readonly SessionCommand[],
  event: CommandEvent,
): SessionCommand[] {
  const index = history.findIndex((row) => row.commandId === event.commandId);

  if (index < 0) {
    const record: SessionCommand = {
      commandId: event.commandId,
      vehicleId: event.vehicleId ?? "UNKNOWN",
      action: event.action ?? "UNKNOWN",
      targetSpeedMps: event.targetSpeedMps ?? null,
      outcome: event.outcome ?? "PENDING",
      message: event.message ?? null,
      reason: event.reason ?? DEFAULT_REASON,
      submittedAtIso: event.observedAtIso,
      updatedAtIso: event.observedAtIso,
      gatewayConfirmed: event.gatewayConfirmed ?? false,
      executionAckIso: null,
    };
    return [record, ...history].slice(0, HISTORY_LIMIT);
  }

  const current = history[index] as SessionCommand;
  const currentOutcome = current.outcome as CommandOutcome;
  const proposed = event.outcome ?? null;
  const nextOutcome =
    proposed !== null && canTransition(currentOutcome, proposed) ? proposed : currentOutcome;

  const merged: SessionCommand = {
    ...current,
    // Only fill in what the event actually carried; never blank an existing value.
    vehicleId: event.vehicleId ?? current.vehicleId,
    action: event.action ?? current.action,
    targetSpeedMps: event.targetSpeedMps ?? current.targetSpeedMps,
    reason: event.reason ?? current.reason,
    outcome: nextOutcome,
    // Keep the more authoritative message rather than erasing one with null.
    message: event.message ?? current.message,
    updatedAtIso: event.observedAtIso,
    gatewayConfirmed: current.gatewayConfirmed || (event.gatewayConfirmed ?? false),
  };

  const next = [...history];
  next[index] = merged;
  return next;
}
