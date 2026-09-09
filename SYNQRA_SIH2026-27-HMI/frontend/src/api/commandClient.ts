/**
 * Dispatch command client — S4.
 *
 * THE ONLY COMMAND PATHWAY OUT OF THE HMI.
 *
 *   HMI -> POST /api/commands -> CommandGateway -> vehicle
 *
 * Commands are never sent over the WebSocket: that socket is a one-way state feed, and a
 * second write path would bypass the gateway's validation. Transport lives here rather
 * than in a component, matching `api/healthClient.ts`.
 *
 * This module makes no safety judgement. It performs one POST and reports, verbatim, what
 * the backend said. A refusal is a RESULT, not an error to be smoothed over.
 */

import type { CommandOutcome, CommandRequestPayload } from "../state/dispatchCommand";
import { API_BASE_URL } from "./healthClient";
import { authHeader } from "./operatorClient";

/** Mirrors `backend/app/main.py::HMICommandResponse`. */
export interface CommandResponseBody {
  command_id: string;
  vehicle_id: string;
  action: string;
  status: string;
  timestamp: number;
  message: string;
}

export interface CommandResult {
  outcome: CommandOutcome;
  /** The backend's message, verbatim when it supplied one. */
  message: string;
  /** Raw status string the backend returned, when it returned one. */
  backendStatus: string | null;
  /** HTTP status, or null when the request never completed. */
  httpStatus: number | null;
}

/** Default guard so a hung backend cannot leave the operator waiting indefinitely. */
export const COMMAND_TIMEOUT_MS = 10_000;

/**
 * Map a backend status string onto an outcome this screen renders.
 *
 * Anything unrecognised becomes REJECTED, never ACCEPTED: an unknown status must not be
 * optimistically read as success. The backend's own message is always carried through, so
 * the operator sees the real words even when the mapping is coarse.
 */
export function classifyStatus(status: string | null | undefined): CommandOutcome {
  const normalized = (status ?? "").trim().toUpperCase();
  switch (normalized) {
    case "ACCEPTED":
      return "ACCEPTED";
    case "REJECTED":
      return "REJECTED";
    case "UNKNOWN_VEHICLE":
      return "UNKNOWN_VEHICLE";
    case "DUPLICATE":
      return "DUPLICATE";
    case "INVALID":
      return "INVALID";
    case "UNSAFE":
      return "UNSAFE";
    case "TIMEOUT":
      return "TIMEOUT";
    case "NOT_EXECUTED":
    case "SUPERSEDED":
      return "NOT_EXECUTED";
    case "STALE":
      return "REJECTED";
    default:
      return "REJECTED";
  }
}

/** Pull an operator-readable message out of a FastAPI error body. */
function describeErrorBody(payload: unknown, httpStatus: number): string {
  if (typeof payload === "object" && payload !== null && "detail" in payload) {
    const detail = (payload as { detail: unknown }).detail;
    if (typeof detail === "string") return detail;
    // 422 validation errors arrive as a list of {loc, msg, type}.
    if (Array.isArray(detail)) {
      const parts = detail
        .map((item) => {
          if (typeof item !== "object" || item === null) return null;
          const entry = item as { loc?: unknown; msg?: unknown };
          const field = Array.isArray(entry.loc) ? entry.loc.join(".") : null;
          const msg = typeof entry.msg === "string" ? entry.msg : null;
          return field && msg ? `${field}: ${msg}` : msg;
        })
        .filter((part): part is string => Boolean(part));
      if (parts.length > 0) return parts.join("; ");
    }
  }
  return `Backend returned HTTP ${httpStatus}`;
}

export interface SubmitOptions {
  /** Injected in tests. Defaults to the global fetch. */
  fetchImpl?: typeof fetch;
  timeoutMs?: number;
  signal?: AbortSignal;
  /**
   * Bearer token to authenticate as. Defaults to the session token held by
   * `api/operatorClient`. Passing `null` sends the request unauthenticated, which the
   * backend refuses - useful only for proving that it does.
   */
  token?: string | null;
}

/**
 * Submit one command.
 *
 * Never throws: a transport failure is returned as NETWORK_ERROR so the caller renders an
 * honest "not delivered" rather than an unhandled rejection. NETWORK_ERROR explicitly
 * means the command reached no vehicle.
 */
export async function submitCommand(
  payload: CommandRequestPayload,
  options: SubmitOptions = {},
): Promise<CommandResult> {
  const doFetch = options.fetchImpl ?? fetch;
  const timeoutMs = options.timeoutMs ?? COMMAND_TIMEOUT_MS;

  const controller = typeof AbortController !== "undefined" ? new AbortController() : null;
  const timer =
    controller !== null
      ? setTimeout(() => {
          controller.abort();
        }, timeoutMs)
      : null;

  try {
    const signal = options.signal ?? controller?.signal;
    /**
     * IDENTITY TRAVELS IN THE HEADER, NEVER IN THE BODY.
     *
     * The backend reads the operator only from `Authorization` (`_bearer_token`), so a
     * body field claiming an operator id would be ignored. Sending no header is a valid
     * state and produces an honest 401 rather than a silently unauthenticated command.
     */
    const response = await doFetch(`${API_BASE_URL}/api/commands`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...authHeader(options.token === undefined ? undefined : options.token),
      },
      body: JSON.stringify(payload),
      ...(signal ? { signal } : {}),
    });

    let body: unknown = null;
    try {
      body = await response.json();
    } catch {
      body = null;
    }

    if (!response.ok) {
      /**
       * An authorization refusal is a REJECTION, not a malformed request.
       *
       * 401 (no authenticated operator), 403 (not assigned to this vehicle) and 503
       * (authorization registry unavailable - fail closed) all mean the same operational
       * thing: no command was issued and no vehicle was reached. They are reported as
       * REJECTED with the backend's own words, and NOT as INVALID, which would tell the
       * operator to go and fix a payload that was fine.
       *
       * No new lifecycle state is introduced for this (root CLAUDE.md - the command
       * lifecycle is fixed).
       */
      const refusedByAuthorization =
        response.status === 401 || response.status === 403 || response.status === 503;

      // 400 (invalid action) and 422 (schema violation) are real gateway refusals.
      return {
        outcome: refusedByAuthorization ? "REJECTED" : "INVALID",
        message: describeErrorBody(body, response.status),
        backendStatus: null,
        httpStatus: response.status,
      };
    }

    if (typeof body !== "object" || body === null || !("status" in body)) {
      return {
        outcome: "REJECTED",
        message: "Backend response did not match the expected command shape.",
        backendStatus: null,
        httpStatus: response.status,
      };
    }

    const parsed = body as Partial<CommandResponseBody>;
    const backendStatus = typeof parsed.status === "string" ? parsed.status : null;
    return {
      outcome: classifyStatus(backendStatus),
      message:
        typeof parsed.message === "string" && parsed.message.trim() !== ""
          ? parsed.message
          : "No message supplied by the backend.",
      backendStatus,
      httpStatus: response.status,
    };
  } catch (error) {
    const aborted = error instanceof Error && error.name === "AbortError";
    return {
      outcome: aborted ? "TIMEOUT" : "NETWORK_ERROR",
      message: aborted
        ? `No response within ${timeoutMs} ms. Delivery is unconfirmed.`
        : error instanceof Error
          ? error.message
          : "Unknown network error",
      backendStatus: null,
      httpStatus: null,
    };
  } finally {
    if (timer !== null) clearTimeout(timer);
  }
}
