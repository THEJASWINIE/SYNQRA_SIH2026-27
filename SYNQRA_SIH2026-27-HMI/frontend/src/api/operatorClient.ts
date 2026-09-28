/**
 * Operator session client.
 *
 * ==========================================================================
 *  THE SERVER DECIDES WHO IS ASKING. THIS MODULE ONLY CARRIES THE ANSWER.
 *
 *  Nothing here establishes identity. `openSession` exchanges a secret for a token the
 *  BACKEND issued, and `fetchOperatorContext` asks the backend who that token belongs to.
 *  The operator id, the role, the assigned vehicle and the shift are all read back off
 *  the wire - none of them is chosen, defaulted or remembered by the frontend.
 *
 *  A component that wants to know who the operator is must ask the backend through here.
 *  A component that decides for itself is a defect: a frontend-asserted identity is a
 *  claim, and the backend rejects claims (operator_registry.py).
 * ==========================================================================
 *
 * WHERE THE TOKEN LIVES
 *
 * In memory, for the lifetime of the page. Deliberately NOT localStorage or a cookie:
 * this is a prototype bearer token over plain HTTP, and persisting it would widen its
 * blast radius past the tab that obtained it for no operational gain. A reload means a
 * new session, which is the honest behaviour for a session that was never durable.
 *
 * Transport only. This module makes no authorization decision - the backend does that,
 * fail-closed, before the command gateway is reached.
 */

import { API_BASE_URL } from "./healthClient";

/** Who the backend says the caller is. Mirrors `GET /api/operator/context`. */
export interface OperatorIdentity {
  readonly operatorId: string;
  readonly name: string;
  readonly role: string;
  /** "DEMO" for the seeded development operators. Rendered, never hidden. */
  readonly provenance: string;
}

export interface OperatorContext {
  readonly operator: OperatorIdentity;
  /** The vehicle the SERVER has this operator assigned to. Null when unassigned. */
  readonly assignedVehicleId: string | null;
  readonly shiftId: string | null;
  readonly assignedAt: string | null;
}

export type OperatorResult =
  | { readonly kind: "ok"; readonly context: OperatorContext }
  /** No authenticated operator: no token, expired, or revoked. */
  | { readonly kind: "unauthenticated"; readonly message: string }
  /** The registry itself is unavailable. Commands are refused while this holds. */
  | { readonly kind: "unavailable"; readonly message: string }
  | { readonly kind: "error"; readonly message: string };

export const OPERATOR_TIMEOUT_MS = 8_000;

// ---------------------------------------------------------------------------
// the in-memory token
// ---------------------------------------------------------------------------

let sessionToken: string | null = null;

/** The bearer token for this page, or null when no session has been opened. */
export function currentToken(): string | null {
  return sessionToken;
}

export function setToken(token: string | null): void {
  sessionToken = token;
}

export function clearToken(): void {
  sessionToken = null;
}

/**
 * The Authorization header for a token, or an empty object when there is none.
 *
 * Returning `{}` rather than a header with an empty value is deliberate: an
 * unauthenticated request must look unauthenticated, so the backend answers 401 rather
 * than trying to resolve a blank token.
 */
export function authHeader(token: string | null = sessionToken): Record<string, string> {
  return token ? { Authorization: `Bearer ${token}` } : {};
}

// ---------------------------------------------------------------------------
// transport
// ---------------------------------------------------------------------------

export interface OperatorRequestOptions {
  fetchImpl?: typeof fetch;
  timeoutMs?: number;
  signal?: AbortSignal;
}

function contextFrom(body: unknown): OperatorContext | null {
  if (typeof body !== "object" || body === null) return null;
  const raw = body as Record<string, unknown>;
  const operator = raw.operator;
  if (typeof operator !== "object" || operator === null) return null;
  const op = operator as Record<string, unknown>;
  if (typeof op.operator_id !== "string") return null;

  return {
    operator: {
      operatorId: op.operator_id,
      name: typeof op.name === "string" ? op.name : op.operator_id,
      role: typeof op.role === "string" ? op.role : "UNKNOWN",
      provenance: typeof op.provenance === "string" ? op.provenance : "UNKNOWN",
    },
    assignedVehicleId: typeof raw.assigned_vehicle_id === "string" ? raw.assigned_vehicle_id : null,
    shiftId: typeof raw.shift_id === "string" ? raw.shift_id : null,
    assignedAt: typeof raw.assigned_at === "string" ? raw.assigned_at : null,
  };
}

function messageFrom(body: unknown, httpStatus: number): string {
  if (typeof body === "object" && body !== null && "detail" in body) {
    const detail = (body as { detail: unknown }).detail;
    if (typeof detail === "string") return detail;
  }
  return `Backend returned HTTP ${httpStatus}`;
}

/** Never throws. A transport failure is a RESULT, so a caller cannot forget to handle it. */
async function request(
  path: string,
  init: RequestInit,
  options: OperatorRequestOptions,
): Promise<OperatorResult> {
  const doFetch = options.fetchImpl ?? fetch;
  const timeoutMs = options.timeoutMs ?? OPERATOR_TIMEOUT_MS;
  const controller = typeof AbortController !== "undefined" ? new AbortController() : null;
  const timer = controller ? setTimeout(() => controller.abort(), timeoutMs) : null;

  try {
    const signal = options.signal ?? controller?.signal;
    const response = await doFetch(`${API_BASE_URL}${path}`, {
      ...init,
      ...(signal ? { signal } : {}),
    });

    let body: unknown = null;
    try {
      body = await response.json();
    } catch {
      body = null;
    }

    if (response.status === 401) {
      return { kind: "unauthenticated", message: messageFrom(body, 401) };
    }
    if (response.status === 503) {
      return { kind: "unavailable", message: messageFrom(body, 503) };
    }
    if (!response.ok) {
      return { kind: "error", message: messageFrom(body, response.status) };
    }

    const context = contextFrom(body);
    if (!context) {
      return { kind: "error", message: "Backend response did not match the operator shape." };
    }

    // A session response also carries the token. Store it; a context response has none.
    if (typeof body === "object" && body !== null && "token" in body) {
      const token = (body as { token: unknown }).token;
      if (typeof token === "string" && token !== "") setToken(token);
    }

    return { kind: "ok", context };
  } catch (error) {
    const aborted = error instanceof Error && error.name === "AbortError";
    return {
      kind: "error",
      message: aborted
        ? `No response within ${timeoutMs} ms.`
        : error instanceof Error
          ? error.message
          : "Unknown network error",
    };
  } finally {
    if (timer !== null) clearTimeout(timer);
  }
}

/**
 * Exchange the shared development secret for a token.
 *
 * The secret is supplied by whoever calls this - it is never read from a VITE_ variable,
 * because a VITE_ value is compiled into the bundle and shipped to every browser.
 */
export function openSession(
  operatorId: string,
  secret: string,
  options: OperatorRequestOptions = {},
): Promise<OperatorResult> {
  return request(
    "/api/operator/session",
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ operator_id: operatorId, secret }),
    },
    options,
  );
}

/** Ask the backend who the current token belongs to. The only source of operator identity. */
export function fetchOperatorContext(
  token: string | null = sessionToken,
  options: OperatorRequestOptions = {},
): Promise<OperatorResult> {
  return request(
    "/api/operator/context",
    { method: "GET", headers: { ...authHeader(token) } },
    options,
  );
}
