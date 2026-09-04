/**
 * Displayed system mode — M8. M8D-A.
 *
 * ==========================================================================
 *  ONE SANCTIONED DERIVATION: THE DEGRADED FLOOR.
 *
 *  FR-016 AC3 — "Loss of the data feed forces at least DEGRADED display
 *  regardless of the last supplied mode."
 *  OPS-003    — "On loss of central communication the HMI shall indicate
 *  degraded mode."
 *  NFR-012    — the HMI degrades rather than freezing values silently.
 *  Closed derivation list, item 5.
 *
 *  This module does NOT compute an operational system mode. It reports the
 *  supplied mode, and raises the DISPLAYED result to DEGRADED when the HMI's
 *  own feed is lost — a property of the data path, not of the mine.
 *
 *  `AppState.health.systemMode` is NEVER mutated. The floor exists only in
 *  what is rendered, so the supplied value stays inspectable and the next
 *  patch is never contaminated by a derived one.
 *
 *  THE FLOOR ONLY RAISES SEVERITY, NEVER LOWERS IT. A supplied LOCAL_SAFE or
 *  STOP_UNSAFE survives feed loss unchanged — softening a severe supplied mode
 *  to DEGRADED would be the single most dangerous thing this file could do.
 * ==========================================================================
 */

import type { AppState, ConnectionStatus } from "../contracts/appState";
import type { SystemMode } from "../contracts/enums";

/**
 * Severity ordering of the five modes, least to most severe.
 *
 * Used ONLY to decide whether the DEGRADED floor would soften a supplied mode. It ranks
 * modes for that comparison; it never produces one.
 */
const MODE_SEVERITY: Record<SystemMode, number> = {
  NORMAL: 0,
  CAUTION: 1,
  DEGRADED: 2,
  LOCAL_SAFE: 3,
  STOP_UNSAFE: 4,
};

/** Connection states that mean the HMI's feed is lost. */
const FEED_LOST_STATUSES: readonly ConnectionStatus[] = ["DISCONNECTED", "ERROR"];

export function isFeedLost(status: ConnectionStatus): boolean {
  return FEED_LOST_STATUSES.includes(status);
}

/** Why the displayed mode is what it is. Rendered, so the operator is never guessing. */
export type ModeSource =
  | "SUPPLIED"
  /** Supplied mode was less severe than DEGRADED and the feed is lost (FR-016 AC3). */
  | "DEGRADED_FLOOR"
  /** Feed lost and nothing was ever supplied. */
  | "DEGRADED_FLOOR_NO_SUPPLIED_MODE"
  /** Nothing supplied and the feed is up — an honest unknown, never NORMAL. */
  | "NOT_SUPPLIED";

export interface DisplayedMode {
  /** Null only when nothing was supplied and the feed is up. NEVER defaulted to NORMAL. */
  mode: SystemMode | null;
  source: ModeSource;
  /** The supplied value, unaltered, for provenance display. */
  suppliedMode: SystemMode | null;
  /** True when the floor changed what is displayed. */
  flooredByFeedLoss: boolean;
}

export const MODE_SOURCE_TEXT: Readonly<Record<ModeSource, string>> = {
  SUPPLIED: "supplied",
  DEGRADED_FLOOR: "raised to DEGRADED — data feed lost (FR-016)",
  DEGRADED_FLOOR_NO_SUPPLIED_MODE: "DEGRADED — data feed lost, no mode supplied (FR-016)",
  NOT_SUPPLIED: "no system mode supplied",
};

/**
 * The mode to display.
 *
 * Rules, in order:
 *   1. Feed up, mode supplied      → the supplied mode, verbatim.
 *   2. Feed up, nothing supplied   → null. NOT NORMAL. Showing a reassuring mode nobody
 *                                    sent is the most dangerous substitution available.
 *   3. Feed lost, nothing supplied → DEGRADED.
 *   4. Feed lost, supplied is less severe than DEGRADED → DEGRADED (the floor).
 *   5. Feed lost, supplied is DEGRADED or more severe   → the supplied mode, untouched.
 */
export function displayedSystemMode(
  suppliedMode: SystemMode | null | undefined,
  status: ConnectionStatus,
): DisplayedMode {
  const supplied = suppliedMode ?? null;
  const feedLost = isFeedLost(status);

  if (!feedLost) {
    return {
      mode: supplied,
      source: supplied === null ? "NOT_SUPPLIED" : "SUPPLIED",
      suppliedMode: supplied,
      flooredByFeedLoss: false,
    };
  }

  if (supplied === null) {
    return {
      mode: "DEGRADED",
      source: "DEGRADED_FLOOR_NO_SUPPLIED_MODE",
      suppliedMode: null,
      flooredByFeedLoss: true,
    };
  }

  // The floor raises, never lowers. LOCAL_SAFE and STOP_UNSAFE pass through unchanged.
  if (MODE_SEVERITY[supplied] >= MODE_SEVERITY.DEGRADED) {
    return {
      mode: supplied,
      source: "SUPPLIED",
      suppliedMode: supplied,
      flooredByFeedLoss: false,
    };
  }

  return {
    mode: "DEGRADED",
    source: "DEGRADED_FLOOR",
    suppliedMode: supplied,
    flooredByFeedLoss: true,
  };
}

/** Convenience over `AppState`, so every screen reads one identical result. */
export function displayedModeFor(state: AppState): DisplayedMode {
  return displayedSystemMode(state.health?.systemMode ?? null, state.connection.status);
}
