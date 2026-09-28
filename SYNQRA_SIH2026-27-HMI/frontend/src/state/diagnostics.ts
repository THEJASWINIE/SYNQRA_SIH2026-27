/**
 * Freshness overview per message type — M10. NFR-003.
 *
 * ==========================================================================
 *  A COUNT OF WHAT THE DATA PATH HOLDS. NOTHING OPERATIONAL.
 *
 *  This module groups the entities already in `AppState` by the contract
 *  message type that carries them, and reports each one's age and quality
 *  using the SINGLE existing freshness mechanism (`state/freshness.ts`).
 *  There is no second freshness system and no second definition of stale.
 *
 *  It computes no safety value, no queue, no bottleneck, no dispatch, no ETA,
 *  no route and no risk. The only derivations are the two already on the
 *  closed list: data age, and quality against a CONFIGURED threshold.
 *
 *  M10D-A: it keeps NO counters of its own. Message counts come from the
 *  producer on `Health.messagesReceived` / `.messagesDropped`. What is counted
 *  here is how many ENTITIES the store currently holds and what quality each
 *  one resolves to — a property of the data path, not a message tally.
 * ==========================================================================
 */

import type { FreshnessConfig } from "../config/freshness";
import type { AppState } from "../contracts/appState";
import type { Quality } from "../contracts/primitives";
import { type FreshnessView, viewFreshness } from "./freshness";

export interface MessageTypeFreshness {
  /** The contract message type carrying these entities. */
  messageType: string;
  /** How many entities of this type the store holds. Zero is a real answer. */
  count: number;
  /**
   * Quality tallies. Null when no threshold is configured — NOT evaluated, which is a
   * different statement from "all current" (AMB-014, M8D-B).
   */
  qualities: Record<Quality, number> | null;
  /** Oldest age across the entities, or null when age is not assessable. */
  oldestAgeMs: number | null;
  /** The oldest entity's freshness view, for rendering a marker and its age. */
  oldest: FreshnessView | null;
}

export interface FreshnessOverview {
  rows: MessageTypeFreshness[];
  thresholdConfigured: boolean;
  /** Entities across every type. */
  totalEntities: number;
}

/**
 * Which `AppState` slices carry which message type.
 *
 * Ordered deliberately, so the overview reads the same on every render — and ordered to
 * match the contract's message list rather than alphabetically, so a reader comparing the
 * screen against the contract does not have to hunt.
 */
const SLICE_TIMESTAMPS: readonly {
  messageType: string;
  timestamps: (state: AppState) => string[];
}[] = [
  {
    messageType: "VehicleState",
    timestamps: (s) => Object.values(s.vehicles).map((v) => v.timestamp),
  },
  {
    messageType: "SafetyState",
    timestamps: (s) => Object.values(s.safety).map((v) => v.timestamp),
  },
  { messageType: "RoadState", timestamps: (s) => Object.values(s.road).map((v) => v.timestamp) },
  {
    messageType: "VisibilityForecast",
    timestamps: (s) => Object.values(s.forecasts).map((v) => v.issuedAt),
  },
  {
    messageType: "BottleneckState",
    timestamps: (s) => Object.values(s.bottlenecks).map((v) => v.timestamp),
  },
  {
    messageType: "ArrivalPlan",
    timestamps: (s) => Object.values(s.arrivals).map((v) => v.issuedAt),
  },
  { messageType: "SlotState", timestamps: (s) => Object.values(s.slots).map((v) => v.startTime) },
  {
    messageType: "DispatchCommand",
    timestamps: (s) => Object.values(s.dispatch).map((v) => v.timestamp),
  },
  { messageType: "Alert", timestamps: (s) => s.alerts.map((a) => a.timestamp) },
  { messageType: "EventRecord", timestamps: (s) => s.events.map((e) => e.timestamp) },
  { messageType: "SystemHealth", timestamps: (s) => (s.health ? [s.health.timestamp] : []) },
  { messageType: "KpiSnapshot", timestamps: (s) => (s.kpis ? [s.kpis.timestamp] : []) },
  { messageType: "CVResult", timestamps: (s) => (s.cv ? [s.cv.timestamp] : []) },
  { messageType: "MineTopology", timestamps: () => [] },
];

function emptyTally(): Record<Quality, number> {
  return { OK: 0, STALE: 0, MISSING: 0, INVALID: 0 };
}

/**
 * Freshness of everything currently held, grouped by message type.
 *
 * With no threshold configured, ages are still reported and `qualities` is null. Nothing
 * is classified, and nothing is assumed current — PAD-G forbids inventing the threshold
 * AMB-014 leaves open.
 *
 * A malformed timestamp resolves to `INVALID`, never `STALE`: age is meaningless for a
 * datum that failed to parse, and an INVALID datum is never also reported stale.
 */
export function freshnessOverview(
  state: AppState,
  config: FreshnessConfig | null,
  nowMs: number,
): FreshnessOverview {
  const rows: MessageTypeFreshness[] = [];
  let totalEntities = 0;

  for (const slice of SLICE_TIMESTAMPS) {
    const timestamps = slice.timestamps(state);
    totalEntities += timestamps.length;

    if (timestamps.length === 0) {
      rows.push({
        messageType: slice.messageType,
        count: 0,
        qualities: config === null ? null : emptyTally(),
        oldestAgeMs: null,
        oldest: null,
      });
      continue;
    }

    const tally = emptyTally();
    let oldestAgeMs: number | null = null;
    let oldest: FreshnessView | null = null;

    for (const timestamp of timestamps) {
      const view = viewFreshness(timestamp, config, nowMs);
      if (view.quality !== null) tally[view.quality] += 1;

      if (view.ageMs !== null && (oldestAgeMs === null || view.ageMs > oldestAgeMs)) {
        oldestAgeMs = view.ageMs;
        oldest = view;
      }
      // An entity with no assessable age still deserves a marker if nothing older exists.
      if (oldest === null) oldest = view;
    }

    rows.push({
      messageType: slice.messageType,
      count: timestamps.length,
      qualities: config === null ? null : tally,
      oldestAgeMs,
      oldest,
    });
  }

  return { rows, thresholdConfigured: config !== null, totalEntities };
}

/** Rows carrying at least one entity. The overview shows every type; summaries use this. */
export function populatedRows(overview: FreshnessOverview): MessageTypeFreshness[] {
  return overview.rows.filter((r) => r.count > 0);
}
