/**
 * Unified data-state semantics — Phase 8.
 *
 * ==========================================================================
 *  ONE INTERPRETATION, NOT A SECOND FRESHNESS SYSTEM.
 *
 *  Nothing here starts a timer, reclassifies a threshold or re-derives an age. The
 *  authoritative freshness machinery is unchanged and stays where it is:
 *
 *    entity timestamps  ->  `state/freshness.ts` (viewFreshness, M4D-E)
 *    Twin per-field     ->  the SUPPLIED `TwinFieldProvenance.freshness`
 *    observability      ->  the Phase 4 lifecycle IDLE / CURRENT / STALE / ERROR
 *    service health     ->  /api/health
 *    command lifecycle  ->  the Phase 2/3 command states
 *
 *  This module only makes those five vocabularies MEAN THE SAME THING when they are
 *  shown next to each other, and gives the screens one place to ask.
 * ==========================================================================
 *
 * FOUR DISTINCT DATA STATES. Collapsing any pair is the failure this module prevents:
 *
 *   CURRENT      authoritative data exists and its own source considers it fresh
 *   STALE        data existed and is now past its freshness, or the source says stale
 *   UNKNOWN      the state cannot be established (unparseable, unclassifiable)
 *   UNAVAILABLE  the current source does not supply this field at all
 *
 * THREE THINGS THAT ARE NOT DATA STATES, and are never converted into one:
 *
 *   SERVICE      ONLINE / OFFLINE / UNKNOWN — a backend fact
 *   PROVENANCE   SIMULATION / PHYSICAL — where a value came from
 *   COMMAND      the command lifecycle — PENDING, ACCEPTED, REJECTED, ...
 *
 * A backend that is ONLINE while its telemetry is STALE is a normal, valid state, and so
 * is an ACCEPTED command beside STALE telemetry. Neither is a contradiction.
 *
 * Pure and framework-free, so it is testable without a DOM (M4D-C).
 */

import type { TwinFieldProvenance, VehicleState } from "../contracts/domain";
import type { FreshnessView } from "./freshness";

// ---------------------------------------------------------------------------
// vocabulary
// ---------------------------------------------------------------------------

export type DataState = "CURRENT" | "STALE" | "UNKNOWN" | "UNAVAILABLE";

/** Backend/service reachability. Never derived from vehicle-data freshness. */
export type ServiceState = "ONLINE" | "OFFLINE" | "UNKNOWN";

/**
 * TWO UNAVAILABLE RENDERINGS, ONE MEANING — the distinction is deliberate (Phase 8 §6).
 *
 *   UNAVAILABLE_VALUE  "--"           in a VALUE slot, where a number or reading would be
 *   UNAVAILABLE_LABEL  "UNAVAILABLE"  in a STATUS slot, where a word would be
 *
 * Both say "the source does not supply this". Neither ever means zero. A supplied 0 is
 * rendered "0" — see `formatAvailability`.
 */
export const UNAVAILABLE_VALUE = "--";
export const UNAVAILABLE_LABEL = "UNAVAILABLE";

/** Text per data state. Always non-empty, so colour is never the only signal (NFR-008). */
export const DATA_STATE_TEXT: Record<DataState, string> = {
  CURRENT: "CURRENT",
  STALE: "STALE",
  UNKNOWN: "UNKNOWN",
  UNAVAILABLE: UNAVAILABLE_LABEL,
};

export const DATA_STATE_GLYPH: Record<DataState, string> = {
  CURRENT: "●",
  STALE: "◐",
  UNKNOWN: "▲",
  UNAVAILABLE: "○",
};

// ---------------------------------------------------------------------------
// freshness — read, never recomputed
// ---------------------------------------------------------------------------

/**
 * Data state from an entity-timestamp `FreshnessView`.
 *
 * Maps the existing `Quality` vocabulary onto the shared one without re-deciding
 * anything. `INVALID` becomes UNKNOWN rather than UNAVAILABLE: a datum that arrived but
 * could not be read is an integration fault, not an absent field, and hiding it as
 * "never supplied" would lose that. A null quality is "not evaluated" (AMB-014, no
 * configured threshold) and is therefore UNKNOWN — never optimistically CURRENT.
 */
export function viewDataState(view: FreshnessView | null | undefined): DataState {
  if (!view) return "UNAVAILABLE";
  switch (view.quality) {
    case "OK":
      return "CURRENT";
    case "STALE":
      return "STALE";
    case "MISSING":
      return "UNAVAILABLE";
    case "INVALID":
      return "UNKNOWN";
    default:
      return "UNKNOWN";
  }
}

/**
 * Data state from a SUPPLIED Twin per-field provenance.
 *
 * The Twin already classified this field. Its verdict is used as-is; the HMI does not
 * second-guess it with a timer of its own. An unrecognised verdict is UNKNOWN, never
 * assumed fresh.
 */
export function fieldDataState(field: TwinFieldProvenance | null | undefined): DataState {
  if (!field) return "UNAVAILABLE";
  if (field.available === false) return "UNAVAILABLE";
  switch (field.freshness) {
    case "CURRENT":
      return "CURRENT";
    case "STALE":
      return "STALE";
    case "MISSING":
      return "UNAVAILABLE";
    default:
      return "UNKNOWN";
  }
}

/** True only for a state that means the value shown is behind reality. */
export function isStale(state: DataState): boolean {
  return state === "STALE";
}

// ---------------------------------------------------------------------------
// provenance — independent of freshness
// ---------------------------------------------------------------------------

/**
 * SIMULATION vs PHYSICAL, from the SUPPLIED per-field provenance and nothing else.
 *
 * THE SINGLE IMPLEMENTATION. Before Phase 8 three screens each had their own, and a
 * hardware-derived speed read "PHYSICAL (derived)" on S3, "PHYSICAL" on S4 and
 * "DERIVED · HARDWARE" on the operator view — three labels for one fact.
 *
 * `origin` is what the value ultimately rests on; `source` is how it was obtained. A
 * speed DERIVED from a measured RPM has origin HARDWARE and is physical, and says so.
 *
 * NEVER inferred from backend connectivity, WebSocket state, Twin attachment or the mere
 * existence of a vehicle. Those are different facts (Phase 8 §4).
 */
export function provenanceLabel(field: TwinFieldProvenance | null | undefined): string {
  if (!field) return UNAVAILABLE_VALUE;
  if (field.origin === "HARDWARE") {
    return field.source === "DERIVED" ? "PHYSICAL (derived)" : "PHYSICAL";
  }
  if (field.origin === "SIMULATION") return "SIMULATION";
  return `${field.source} · ${field.origin}`;
}

/** Provenance of a vehicle, taken from its speed field — the one every screen shows. */
export function vehicleProvenanceLabel(vehicle: VehicleState | null | undefined): string {
  return provenanceLabel(vehicle?.provenance?.speed_mps);
}

/** True only when the supplier said the value ultimately rests on hardware. */
export function isPhysical(vehicle: VehicleState | null | undefined): boolean {
  return vehicle?.provenance?.speed_mps?.origin === "HARDWARE";
}

// ---------------------------------------------------------------------------
// communication — independent of freshness AND of provenance
// ---------------------------------------------------------------------------

/**
 * The vehicle's SUPPLIED communication state.
 *
 * Returns null when nothing was supplied, so the caller renders UNKNOWN rather than a
 * reassuring word. It is NOT derived from the existence of a vehicle object, from
 * telemetry freshness, or from the HMI's own connection — a vehicle can be present and
 * fresh while its link is degraded, and the Twin says so.
 */
export function communicationState(vehicle: VehicleState | null | undefined): string | null {
  const value = vehicle?.provenance?.communication_state?.value;
  if (value === undefined || value === null || value === "") return null;
  return String(value);
}

/** Communication for display. UNKNOWN when unsupplied — never CONNECTED by assumption. */
export function communicationText(vehicle: VehicleState | null | undefined): string {
  return communicationState(vehicle) ?? "UNKNOWN";
}

// ---------------------------------------------------------------------------
// service health — separate domain
// ---------------------------------------------------------------------------

/**
 * Service reachability from a health probe result.
 *
 * Deliberately takes the probe, not the data. Stale telemetry must never be reported as
 * "backend offline", and an unreachable backend must never be softened because the last
 * telemetry still looks recent.
 */
export function serviceState(healthOk: boolean | null | undefined): ServiceState {
  if (healthOk === true) return "ONLINE";
  if (healthOk === false) return "OFFLINE";
  return "UNKNOWN";
}

// ---------------------------------------------------------------------------
// availability formatting
// ---------------------------------------------------------------------------

/**
 * Format a value that may not have been supplied.
 *
 * A supplied 0 renders "0.0" — it is a measurement. Only null, undefined and non-finite
 * render as unavailable. Collapsing the two is the single most dangerous substitution in
 * this HMI: a fabricated zero speed reads as a stopped truck.
 */
export function formatAvailability(
  value: number | null | undefined,
  digits = 1,
  unavailable: string = UNAVAILABLE_VALUE,
): string {
  if (typeof value !== "number" || !Number.isFinite(value)) return unavailable;
  return value.toFixed(digits);
}
