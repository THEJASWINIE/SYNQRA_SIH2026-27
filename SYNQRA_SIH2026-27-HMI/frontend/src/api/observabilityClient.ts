/**
 * Observability client — Phase 4.
 *
 * Transport + normalization for `GET /api/observability`, the backend's control-plane
 * counters. Transport lives here rather than in a component, matching `healthClient.ts`
 * and `commandClient.ts`; no screen calls `fetch` for this.
 *
 * THE EXACT LIVE RESPONSE (captured from the running backend, not assumed):
 *
 *   {
 *     "service": "hmi-backend",
 *     "timestamp": 1788665982.04608,
 *     "twin_attached": true,
 *     "twin_vehicle_count": 0,
 *     "telemetry_ingest": { "accepted": 0, "duplicate": 0, "out_of_order": 0,
 *                           "invalid": 0, "unknown_vehicle": 0 },
 *     "command_gateway": { "accepted": 5, "rejected": 6, "duplicate": 1, "stale": 0,
 *                          "unknown_vehicle": 2, "invalid": 0, "unsafe": 3, "timeout": 0 },
 *     "backend_cache_vehicles": 0,
 *     "websocket_clients": 0,
 *     "command_history_length": 11,
 *     "hardware": { "hardware_seen": false, "hardware_connected": false,
 *                   "age_seconds": null },
 *     "mode": "MOCK"
 *   }
 *
 * The backend documents that an unwired component reports `null`, never `0`. This module
 * preserves that: a MISSING counter stays null and renders UNAVAILABLE, because
 * "not measured" and "measured zero" are different answers.
 *
 * THIS IS METRICS, NOT STATE.
 *   * `twin_vehicle_count` is a count, not vehicle state - the Twin projection remains the
 *     only source of vehicle data.
 *   * `command_gateway.*` are counters, not command records - `AppState.commands` (Phase 3)
 *     remains the authoritative command history.
 */

import { API_BASE_URL } from "./healthClient";

/** Telemetry ingestion counters. Every field may be absent; absent is not zero. */
export interface TelemetryCounters {
  accepted: number | null;
  duplicate: number | null;
  outOfOrder: number | null;
  invalid: number | null;
  unknownVehicle: number | null;
}

/** Command gateway counters. METRICS ONLY - never command history. */
export interface CommandGatewayCounters {
  accepted: number | null;
  rejected: number | null;
  duplicate: number | null;
  stale: number | null;
  unknownVehicle: number | null;
  invalid: number | null;
  unsafe: number | null;
  timeout: number | null;
}

/**
 * Physical-link status, as the BACKEND reports it.
 *
 * `hardwareSeen` (it happened once) is deliberately separate from `hardwareConnected`
 * (it is happening now). Neither may be inferred from `mode`, and a reachable backend is
 * not evidence of hardware.
 */
export interface HardwareStatus {
  hardwareSeen: boolean | null;
  hardwareConnected: boolean | null;
  ageSeconds: number | null;
}

export interface ObservabilitySnapshot {
  service: string | null;
  /** Backend epoch seconds, as supplied. */
  timestamp: number | null;
  twinAttached: boolean | null;
  twinVehicleCount: number | null;
  telemetryIngest: TelemetryCounters | null;
  commandGateway: CommandGatewayCounters | null;
  backendCacheVehicles: number | null;
  websocketClients: number | null;
  commandHistoryLength: number | null;
  hardware: HardwareStatus | null;
  /** Backend operating mode ("MOCK" / "LIVE"). NOT a hardware claim. */
  mode: string | null;
}

export type ObservabilityResult =
  | { kind: "ok"; snapshot: ObservabilitySnapshot }
  | { kind: "error"; message: string; httpStatus: number | null };

// ---------------------------------------------------------------------------
// normalization — pure, and never invents a value
// ---------------------------------------------------------------------------

/** A finite number, or null. `undefined`, null, NaN and non-numbers all become null. */
function num(value: unknown): number | null {
  return typeof value === "number" && Number.isFinite(value) ? value : null;
}

/** A boolean, or null when the field was not supplied. */
function bool(value: unknown): boolean | null {
  return typeof value === "boolean" ? value : null;
}

function str(value: unknown): string | null {
  return typeof value === "string" ? value : null;
}

function asRecord(value: unknown): Record<string, unknown> | null {
  return typeof value === "object" && value !== null && !Array.isArray(value)
    ? (value as Record<string, unknown>)
    : null;
}

/**
 * Normalize a raw payload into the HMI model.
 *
 * Returns null only when the payload is not an object at all - a partially-populated
 * response is still useful, and the fields it omits stay null rather than becoming zero.
 * Never throws.
 */
export function normalizeObservability(raw: unknown): ObservabilitySnapshot | null {
  const body = asRecord(raw);
  if (body === null) return null;

  const ingest = asRecord(body.telemetry_ingest);
  const gateway = asRecord(body.command_gateway);
  const hardware = asRecord(body.hardware);

  return {
    service: str(body.service),
    timestamp: num(body.timestamp),
    twinAttached: bool(body.twin_attached),
    twinVehicleCount: num(body.twin_vehicle_count),
    // A null block means the component is not wired at all - distinct from zeroed counters.
    telemetryIngest:
      ingest === null
        ? null
        : {
            accepted: num(ingest.accepted),
            duplicate: num(ingest.duplicate),
            outOfOrder: num(ingest.out_of_order),
            invalid: num(ingest.invalid),
            unknownVehicle: num(ingest.unknown_vehicle),
          },
    commandGateway:
      gateway === null
        ? null
        : {
            accepted: num(gateway.accepted),
            rejected: num(gateway.rejected),
            duplicate: num(gateway.duplicate),
            stale: num(gateway.stale),
            unknownVehicle: num(gateway.unknown_vehicle),
            invalid: num(gateway.invalid),
            unsafe: num(gateway.unsafe),
            timeout: num(gateway.timeout),
          },
    backendCacheVehicles: num(body.backend_cache_vehicles),
    websocketClients: num(body.websocket_clients),
    commandHistoryLength: num(body.command_history_length),
    hardware:
      hardware === null
        ? null
        : {
            hardwareSeen: bool(hardware.hardware_seen),
            hardwareConnected: bool(hardware.hardware_connected),
            ageSeconds: num(hardware.age_seconds),
          },
    mode: str(body.mode),
  };
}

// ---------------------------------------------------------------------------
// transport
// ---------------------------------------------------------------------------

export interface FetchObservabilityOptions {
  /** Injected in tests. Defaults to the global fetch. */
  fetchImpl?: typeof fetch;
  signal?: AbortSignal;
}

/**
 * Fetch one observability snapshot.
 *
 * Never throws: a transport or shape problem is returned as `kind: "error"` so the caller
 * can keep the last known good snapshot and mark it stale rather than blanking the panel.
 */
export async function fetchObservability(
  options: FetchObservabilityOptions = {},
): Promise<ObservabilityResult> {
  const doFetch = options.fetchImpl ?? fetch;
  try {
    const response = await doFetch(`${API_BASE_URL}/api/observability`, {
      ...(options.signal ? { signal: options.signal } : {}),
    });

    if (!response.ok) {
      return {
        kind: "error",
        message: `Observability endpoint returned HTTP ${response.status}`,
        httpStatus: response.status,
      };
    }

    let payload: unknown = null;
    try {
      payload = await response.json();
    } catch {
      return {
        kind: "error",
        message: "Observability response was not valid JSON",
        httpStatus: response.status,
      };
    }

    const snapshot = normalizeObservability(payload);
    if (snapshot === null) {
      return {
        kind: "error",
        message: "Observability response did not match the expected shape",
        httpStatus: response.status,
      };
    }

    return { kind: "ok", snapshot };
  } catch (error) {
    return {
      kind: "error",
      message: error instanceof Error ? error.message : "Unknown network error",
      httpStatus: null,
    };
  }
}
