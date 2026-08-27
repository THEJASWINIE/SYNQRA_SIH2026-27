/**
 * Backend health client — M1 foundation.
 *
 * Architecture rule (`.claude/skills/task1-architecture`): transport logic must not live
 * inside visual components. This module owns the fetch and hands back a normalized,
 * typed result. `App.tsx` never calls `fetch`.
 *
 * Scope note: this is a foundation-level placeholder for the shape the real provider
 * layer takes. The `DataProvider` interface, the contract schemas and the normalization
 * layer are M2 work and are deliberately NOT built here.
 */

/** Mirrors `backend/app/schemas/health.py::HealthResponse`. */
export interface BackendHealth {
  readonly status: "ok";
  readonly service: string;
  readonly version: string;
  readonly milestone: string;
  /** ISO-8601, timezone-aware, produced by the backend. */
  readonly timestamp: string;
}

export type HealthResult =
  | { readonly kind: "ok"; readonly health: BackendHealth; readonly latencyMs: number }
  | { readonly kind: "error"; readonly message: string };

/** Base URL comes from configuration, never a hard-coded literal in a component. */
export const API_BASE_URL: string = import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000";

/** Narrow an unknown payload to `BackendHealth` without trusting the server blindly. */
function isBackendHealth(value: unknown): value is BackendHealth {
  if (typeof value !== "object" || value === null) return false;
  const candidate = value as Record<string, unknown>;
  return (
    candidate.status === "ok" &&
    typeof candidate.service === "string" &&
    typeof candidate.version === "string" &&
    typeof candidate.milestone === "string" &&
    typeof candidate.timestamp === "string"
  );
}

export async function fetchHealth(signal?: AbortSignal): Promise<HealthResult> {
  const startedAt = performance.now();
  try {
    const response = await fetch(`${API_BASE_URL}/api/health`, {
      ...(signal ? { signal } : {}),
    });
    if (!response.ok) {
      return { kind: "error", message: `Backend returned HTTP ${response.status}` };
    }
    const payload: unknown = await response.json();
    if (!isBackendHealth(payload)) {
      return { kind: "error", message: "Backend response did not match the expected shape" };
    }
    return {
      kind: "ok",
      health: payload,
      latencyMs: Math.round(performance.now() - startedAt),
    };
  } catch (error) {
    const message = error instanceof Error ? error.message : "Unknown network error";
    return { kind: "error", message };
  }
}
