/**
 * Sourced<T> construction and freshness classification — M2.
 *
 * THIS IS THE ONLY PLACE `Sourced<T>` VALUES ARE BUILT. A second provenance wrapper, or
 * a second site that assembles one, is a defect (realtime-data skill §4).
 *
 * Task 1 derives exactly two fields here — `ageMs` and `quality` — and both are
 * properties of the data path, not of the mine (contract §12 items 1–2). Nothing in this
 * module touches an operational value.
 */

import type { FreshnessConfig } from "../config/freshness";
import type { ComponentId, Quality, Sourced } from "../contracts/primitives";
import { ageMsFrom } from "./timestamps";

/** Injected clock. Freshness logic never calls `Date.now()` directly, so tests stay deterministic. */
export type Clock = () => number;

export const systemClock: Clock = () => Date.now();

/**
 * The complete datum was NOT supplied.
 *
 * Never use this for a payload that arrived and failed validation — that is `invalid()`.
 * Collapsing the two hides an integration fault behind what looks like a quiet link.
 */
export function missing<T>(sourceId: ComponentId | null = null): Sourced<T> {
  return { value: null, timestamp: null, sourceId, ageMs: 0, quality: "MISSING" };
}

/**
 * The datum WAS supplied but failed validation.
 *
 * The timestamp is retained when it was itself valid, so diagnostics can show when the
 * bad payload was produced. Age is 0 and quality stays INVALID regardless: age is
 * meaningless for something that failed validation, and an INVALID datum is never also
 * reported as STALE.
 */
export function invalid<T>(
  timestamp: string | null = null,
  sourceId: ComponentId | null = null,
): Sourced<T> {
  return { value: null, timestamp, sourceId, ageMs: 0, quality: "INVALID" };
}

/**
 * A validated datum with a valid timestamp. Quality is OK or STALE depending on age
 * against the configured threshold.
 *
 * A STALE datum KEEPS ITS VALUE. Stale means "this is a real reading, too old to trust as
 * current" — it is still rendered, marked. That is distinct from MISSING, which has
 * nothing to render.
 */
export function supplied<T>(
  value: T,
  timestampIso: string,
  epochMs: number,
  sourceId: ComponentId | null,
  config: FreshnessConfig,
  clock: Clock,
): Sourced<T> {
  const ageMs = ageMsFrom(epochMs, clock());
  const quality: Quality = ageMs > config.staleTimeoutMs ? "STALE" : "OK";
  return { value, timestamp: timestampIso, sourceId, ageMs, quality };
}

/**
 * Recompute age and quality for an already-built `Sourced<T>`.
 *
 * Age advances with the wall clock, so a value that was OK when received becomes STALE
 * on its own as time passes with no new data. That is how NFR-012's "degraded rather than
 * frozen" behaviour emerges from the age rule instead of being special-cased when a
 * provider disconnects.
 *
 * MISSING and INVALID are terminal — re-evaluating cannot make an absent or malformed
 * datum fresh.
 */
export function refresh<T>(datum: Sourced<T>, config: FreshnessConfig, clock: Clock): Sourced<T> {
  if (datum.quality === "MISSING" || datum.quality === "INVALID") return datum;
  if (datum.timestamp === null) return datum;

  const epochMs = Date.parse(datum.timestamp);
  if (!Number.isFinite(epochMs)) return invalid<T>(datum.timestamp, datum.sourceId);

  const ageMs = ageMsFrom(epochMs, clock());
  return {
    ...datum,
    ageMs,
    quality: ageMs > config.staleTimeoutMs ? "STALE" : "OK",
  };
}

/** True when the datum has a value that may be rendered. STALE values are renderable. */
export function hasValue<T>(datum: Sourced<T>): boolean {
  return datum.value !== null;
}
