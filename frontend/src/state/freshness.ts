/**
 * Render-time freshness — M4. M4D-E, MID-B.
 *
 * The frozen contract holds `AppState` entities UNWRAPPED — `VehicleState`, not
 * `Sourced<VehicleState>`. So freshness is derived here, at the rendering boundary, from
 * each entity's own supplied timestamp. The contract is not amended to carry provenance
 * it was not specified to carry.
 *
 * AMB-014 governs what happens without a threshold. HMI-NFR-003 requires a *configurable*
 * staleness timeout and the specification states no value. PAD-G forbids inventing one,
 * so when the threshold is absent this module reports the age and REFUSES TO CLASSIFY.
 * It never falls back to a number nobody authorized.
 */

import type { FreshnessConfig } from "../config/freshness";
import type { Quality } from "../contracts/primitives";
import { supplied } from "../data/sourced";
import { ageMsFrom } from "../data/timestamps";

/**
 * What the UI needs to render freshness honestly.
 *
 * `quality` is null when — and only when — no threshold is configured. Null means "not
 * evaluated", which is a different statement from OK and must render differently.
 */
export interface FreshnessView {
  timestamp: string | null;
  /** Null when age is not assessable (no timestamp, or an unparseable one). */
  ageMs: number | null;
  /** Null when the threshold is unconfigured — NOT evaluated, never assumed OK. */
  quality: Quality | null;
  thresholdConfigured: boolean;
}

export const MISSING_FRESHNESS: FreshnessView = {
  timestamp: null,
  ageMs: null,
  quality: "MISSING",
  thresholdConfigured: false,
};

/**
 * Classify one supplied timestamp.
 *
 * With a config, classification is delegated to `data/sourced.ts` — the single site where
 * `Sourced<T>` values are built. Duplicating the OK/STALE rule here would create a second
 * definition of staleness, and the two would eventually disagree.
 */
export function viewFreshness(
  timestamp: string | null | undefined,
  config: FreshnessConfig | null,
  nowMs: number,
): FreshnessView {
  if (timestamp === null || timestamp === undefined || timestamp === "") {
    return MISSING_FRESHNESS;
  }

  const epochMs = Date.parse(timestamp);
  if (!Number.isFinite(epochMs)) {
    // Supplied but unusable. INVALID, never MISSING — collapsing the two would hide an
    // integration fault behind what looks like a quiet link.
    return { timestamp, ageMs: null, quality: "INVALID", thresholdConfigured: config !== null };
  }

  const ageMs = ageMsFrom(epochMs, nowMs);

  if (config === null) {
    return { timestamp, ageMs, quality: null, thresholdConfigured: false };
  }

  const datum = supplied(timestamp, timestamp, epochMs, null, config, () => nowMs);
  return { timestamp, ageMs, quality: datum.quality, thresholdConfigured: true };
}

/** Human-readable age. Returns null when age is not assessable. */
export function formatAge(ageMs: number | null): string | null {
  if (ageMs === null) return null;
  if (ageMs < 1000) return `${ageMs} ms ago`;
  const seconds = ageMs / 1000;
  if (seconds < 60) return `${seconds.toFixed(1)} s ago`;
  const minutes = Math.floor(seconds / 60);
  const rest = Math.floor(seconds % 60);
  return `${minutes} m ${rest} s ago`;
}

/**
 * The text shown alongside a value. Always non-empty, so freshness never depends on a
 * colour to be communicated (NFR-008).
 */
export function freshnessLabel(view: FreshnessView): string {
  switch (view.quality) {
    case "OK":
      return "CURRENT";
    case "STALE":
      return "STALE";
    case "MISSING":
      return "UNAVAILABLE";
    case "INVALID":
      return "INVALID";
    default:
      return "AGE ONLY — NOT CLASSIFIED";
  }
}

export function freshnessGlyph(view: FreshnessView): string {
  switch (view.quality) {
    case "OK":
      return "●";
    case "STALE":
      return "◐";
    case "MISSING":
      return "○";
    case "INVALID":
      return "▲";
    default:
      return "◌";
  }
}
