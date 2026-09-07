/**
 * S7 System Health — derivation. Phase 5.
 *
 * ==========================================================================
 *  EVERY LINE HERE IS DERIVED FROM A VALUE THE BACKEND ACTUALLY REPORTED.
 *
 *  No aggregate is invented. If the data cannot support a verdict, the verdict is
 *  UNAVAILABLE and the underlying facts are shown instead - a reassuring "HEALTHY"
 *  computed from nothing is the most dangerous thing this screen could display.
 *
 *  The forbidden inferences, spelled out because each is tempting:
 *    * backend reachable          !=  hardware connected
 *    * Twin attached              !=  a vehicle is physically present
 *    * WebSocket clients          !=  vehicles
 *    * mode MOCK                  !=  malfunction, and != hardware disconnected
 *    * gateway rejections         !=  a fault (fail-closed refusal is CORRECT behaviour)
 * ==========================================================================
 *
 * Pure and framework-free, so it is testable without a DOM (M4D-C).
 */

import type { ObservabilityState } from "../contracts/appState";

/**
 * A status a health line can carry.
 *
 * UNAVAILABLE is a first-class answer, not a failure to compute: it means the backend
 * supplied nothing to judge, which is different from judging the thing unhealthy.
 */
export type HealthState = "OK" | "DEGRADED" | "OFF" | "UNAVAILABLE";

export interface HealthLine {
  label: string;
  state: HealthState;
  /** What is actually shown next to the label. Never a guess. */
  value: string;
  /** Optional supporting fact, shown small. */
  detail?: string | undefined;
}

/** Glyph per state. Text always accompanies it, so colour is never the only signal. */
export const HEALTH_GLYPH: Record<HealthState, string> = {
  OK: "●",
  DEGRADED: "▲",
  OFF: "○",
  UNAVAILABLE: "–",
};

/**
 * PHASE 8 — a re-export, not a second definition. `dataStatus.UNAVAILABLE_VALUE` is the
 * one "--" in the HMI; S7 keeps importing it under its established name.
 */
export { UNAVAILABLE_VALUE as UNAVAILABLE_TEXT } from "./dataStatus";
import { UNAVAILABLE_VALUE as UNAVAILABLE_TEXT } from "./dataStatus";

/**
 * Format a counter for display.
 *
 * A real 0 renders as "0". A MISSING value renders as "--". Collapsing the two would
 * claim a measurement that was never taken.
 */
export function formatCounter(value: number | null | undefined): string {
  return typeof value === "number" && Number.isFinite(value) ? String(value) : UNAVAILABLE_TEXT;
}

/** Format an age in seconds, preserving unavailability. */
export function formatAgeSeconds(value: number | null | undefined): string {
  return typeof value === "number" && Number.isFinite(value)
    ? `${value.toFixed(1)} s`
    : UNAVAILABLE_TEXT;
}

// ---------------------------------------------------------------------------
// individual derivations
// ---------------------------------------------------------------------------

/**
 * Backend line, from the observability fetch outcome.
 *
 * This describes the OBSERVABILITY endpoint specifically. Service liveness is a separate
 * question answered by `/api/health`, and the two are shown separately on S7.
 */
export function backendLine(observability: ObservabilityState): HealthLine {
  switch (observability.status) {
    case "CURRENT":
      return { label: "Backend", state: "OK", value: "ONLINE" };
    case "STALE":
      return {
        label: "Backend",
        state: "DEGRADED",
        value: "LAST SNAPSHOT STALE",
        detail: observability.error ?? undefined,
      };
    case "ERROR":
      return {
        label: "Backend",
        state: "OFF",
        value: "UNREACHABLE",
        detail: observability.error ?? undefined,
      };
    default:
      return { label: "Backend", state: "UNAVAILABLE", value: "NOT YET QUERIED" };
  }
}

/** Twin line. Attachment is a software fact and says nothing about any vehicle. */
export function twinLine(observability: ObservabilityState): HealthLine {
  const attached = observability.data?.twinAttached;
  if (attached === true) {
    return {
      label: "Digital Twin",
      state: "OK",
      value: "ATTACHED",
      detail: `${formatCounter(observability.data?.twinVehicleCount)} vehicle(s) in Twin`,
    };
  }
  if (attached === false) {
    return { label: "Digital Twin", state: "OFF", value: "NOT ATTACHED" };
  }
  return { label: "Digital Twin", state: "UNAVAILABLE", value: UNAVAILABLE_TEXT };
}

/**
 * Telemetry line.
 *
 * DEGRADED when the backend reports rejected packets - that is a real, measured signal.
 * "No data yet" is reported as such rather than as healthy, because zero accepted packets
 * is not a working pipeline.
 */
export function telemetryLine(observability: ObservabilityState): HealthLine {
  const counters = observability.data?.telemetryIngest;
  if (!counters) {
    return { label: "Telemetry", state: "UNAVAILABLE", value: UNAVAILABLE_TEXT };
  }

  const { accepted, invalid, unknownVehicle, duplicate, outOfOrder } = counters;

  // Every judged counter missing: nothing has been measured, so no verdict is defensible.
  if (accepted === null && invalid === null && unknownVehicle === null) {
    return { label: "Telemetry", state: "UNAVAILABLE", value: UNAVAILABLE_TEXT };
  }

  const problems = (invalid ?? 0) + (unknownVehicle ?? 0) + (duplicate ?? 0) + (outOfOrder ?? 0);

  if (problems > 0) {
    return {
      label: "Telemetry",
      state: "DEGRADED",
      value: "DEGRADED",
      detail: `${problems} rejected packet(s) reported`,
    };
  }
  if ((accepted ?? 0) > 0) {
    return {
      label: "Telemetry",
      state: "OK",
      value: "HEALTHY",
      detail: `${formatCounter(accepted)} accepted, none rejected`,
    };
  }
  return {
    label: "Telemetry",
    state: "OFF",
    value: "NO DATA",
    detail: "No telemetry has been accepted yet",
  };
}

/**
 * Command gateway line.
 *
 * READY means the gateway is reporting. A high rejection count is NOT a fault: refusing an
 * unsafe or unvalidated command is the gateway doing its job, so rejections are shown as
 * counters rather than folded into a health verdict.
 */
export function commandLine(observability: ObservabilityState): HealthLine {
  const gateway = observability.data?.commandGateway;
  if (!gateway) {
    return { label: "Commands", state: "UNAVAILABLE", value: UNAVAILABLE_TEXT };
  }
  return {
    label: "Commands",
    state: "OK",
    value: "READY",
    detail: `${formatCounter(gateway.accepted)} accepted · ${formatCounter(
      gateway.rejected,
    )} refused`,
  };
}

/**
 * Hardware line — the one most easily faked, so the rules are explicit.
 *
 * Derived ONLY from `hardware_seen` / `hardware_connected`. Never from backend
 * reachability, Twin attachment, WebSocket clients, or mode.
 */
export function hardwareLine(observability: ObservabilityState): HealthLine {
  const hardware = observability.data?.hardware;
  if (!hardware || (hardware.hardwareSeen === null && hardware.hardwareConnected === null)) {
    return { label: "Hardware", state: "UNAVAILABLE", value: UNAVAILABLE_TEXT };
  }

  if (hardware.hardwareConnected === true) {
    return {
      label: "Hardware",
      state: "OK",
      value: "CONNECTED",
      detail: `last packet ${formatAgeSeconds(hardware.ageSeconds)} ago`,
    };
  }
  if (hardware.hardwareSeen === true) {
    return {
      label: "Hardware",
      state: "DEGRADED",
      value: "SEEN, NOT CONNECTED",
      detail: `last packet ${formatAgeSeconds(hardware.ageSeconds)} ago`,
    };
  }
  return {
    label: "Hardware",
    state: "OFF",
    value: "NOT CONNECTED",
    detail: "No physical packet has been received by this backend",
  };
}

/**
 * Mode line.
 *
 * The backend's own mode string, plus what it means for provenance. MOCK means the
 * telemetry ingress is SIMULATED - not that anything is broken.
 */
export function modeLine(observability: ObservabilityState): HealthLine {
  const mode = observability.data?.mode;
  if (typeof mode !== "string" || mode.trim() === "") {
    return { label: "Mode", state: "UNAVAILABLE", value: UNAVAILABLE_TEXT };
  }
  const upper = mode.toUpperCase();
  if (upper === "MOCK") {
    return {
      label: "Mode",
      state: "OK",
      value: "MOCK",
      detail: "SIMULATION — telemetry is simulated, not physically measured",
    };
  }
  if (upper === "LIVE") {
    return {
      label: "Mode",
      state: "OK",
      value: "LIVE",
      detail: "Backend reports a recent packet on the physical ingress",
    };
  }
  return { label: "Mode", state: "UNAVAILABLE", value: upper };
}

/** The full banner, in display order. */
export function deriveSystemHealth(observability: ObservabilityState): HealthLine[] {
  return [
    backendLine(observability),
    twinLine(observability),
    telemetryLine(observability),
    commandLine(observability),
    hardwareLine(observability),
    modeLine(observability),
  ];
}

/** Human wording for the observability lifecycle, shown verbatim on S7. */
export const OBSERVABILITY_STATUS_TEXT: Record<ObservabilityState["status"], string> = {
  IDLE: "NOT YET QUERIED",
  CURRENT: "CURRENT",
  STALE: "STALE",
  /**
   * PHASE 8 §11 — ERROR is its own word, not "UNAVAILABLE".
   *
   * UNAVAILABLE means the source does not supply the field. ERROR means the fetch itself
   * failed and nothing has ever arrived. Rendering the second as the first hid a broken
   * observability endpoint behind the same wording as a field that simply is not offered,
   * and neither implies the backend is down — only /api/health can say that.
   */
  ERROR: "ERROR",
};

export const OBSERVABILITY_STATUS_DETAIL: Record<ObservabilityState["status"], string> = {
  IDLE: "No observability snapshot has been requested yet.",
  CURRENT: "The most recent observability fetch succeeded.",
  STALE: "The most recent fetch failed. The last known good counters are shown below.",
  ERROR: "Unable to obtain an observability snapshot. No counters have ever been received.",
};
