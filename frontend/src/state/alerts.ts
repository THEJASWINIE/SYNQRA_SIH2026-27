/**
 * Alert merging and HMI data-path alerts — M8. M8D-A, M8D-B.
 *
 * ==========================================================================
 *  THE HMI MAY ORIGINATE EXACTLY TWO ALERT CATEGORIES.
 *
 *  COMM_LOSS  — the HMI's own feed is lost (connection.status).
 *  STALE_DATA — a supplied, valid datum has aged past the CONFIGURED
 *               threshold.
 *
 *  Both are mandated by FR-014 AC4 and sit on the closed derivation list as
 *  item 4. `ALERT_ORIGINS` carries the matching comment: "The HMI may
 *  originate only STALE_DATA and COMM_LOSS (contract §8)."
 *
 *  UNSAFE_SPEED, UNSAFE_HEADWAY, BOTTLENECK_RISK and SLOT_CONFLICT are
 *  PRODUCER CATEGORIES. Nothing here fabricates one, and nothing here
 *  assigns, promotes or computes a severity or a risk.
 *
 *  DERIVED ALERTS ARE VIEW DATA. They are produced at render time and are
 *  never written back into `AppState` or the provider. A derived alert stored
 *  beside a supplied one becomes indistinguishable from it on the next patch,
 *  and would then outlive the condition that produced it.
 *
 *  DERIVED ALERTS NEVER OVERWRITE A SUPPLIED ALERT. Ids are namespaced and a
 *  collision resolves in favour of the supplied alert.
 * ==========================================================================
 */

import type { FreshnessConfig } from "../config/freshness";
import type { AppState } from "../contracts/appState";
import type { Alert } from "../contracts/domain";
import { rankAlerts } from "./derive";
import { isFeedLost } from "./systemMode";

/** Prefix for every HMI-originated alert id, so provenance survives even in a raw dump. */
export const HMI_ALERT_ID_PREFIX = "HMI:";

export const COMM_LOSS_ALERT_ID = `${HMI_ALERT_ID_PREFIX}COMM_LOSS`;
export const STALE_DATA_ALERT_ID = `${HMI_ALERT_ID_PREFIX}STALE_DATA`;

/** Shown when AMB-014 leaves the threshold unconfigured (M8D-B). */
export const STALE_ALERTING_INACTIVE_TEXT =
  "STALE ALERTING INACTIVE — NO FRESHNESS THRESHOLD CONFIGURED";

export function isHmiOriginated(alert: Alert): boolean {
  return alert.origin === "HMI";
}

/**
 * The supplied timestamps the HMI watches for staleness.
 *
 * Every entry is a timestamp the data layer supplied. Nothing is generated; this only
 * decides which supplied values are in scope for an age check.
 */
function suppliedTimestamps(state: AppState): { label: string; timestamp: string }[] {
  const entries: { label: string; timestamp: string }[] = [];

  for (const vehicle of Object.values(state.vehicles)) {
    entries.push({ label: `vehicle ${vehicle.vehicleId}`, timestamp: vehicle.timestamp });
  }
  for (const safety of Object.values(state.safety)) {
    entries.push({ label: `safety ${safety.vehicleId}`, timestamp: safety.timestamp });
  }
  for (const road of Object.values(state.road)) {
    entries.push({ label: `segment ${road.segmentId}`, timestamp: road.timestamp });
  }
  if (state.health !== null) {
    entries.push({ label: "system health", timestamp: state.health.timestamp });
  }

  return entries;
}

export interface StaleAssessment {
  /** Null when no threshold is configured — NOT evaluated, never assumed fresh. */
  staleLabels: string[] | null;
  oldestAgeMs: number | null;
  thresholdConfigured: boolean;
}

/**
 * Which supplied data has aged past the configured threshold.
 *
 * With no threshold this returns `staleLabels: null` and raises nothing. PAD-G forbids
 * inventing a value, and AMB-014 leaves NFR-003 without one, so the honest answer is
 * "not evaluated" rather than a guess in either direction (M8D-B).
 *
 * A timestamp that cannot be parsed is INVALID, not stale — age is meaningless for a
 * datum that failed validation, and an INVALID datum is never also reported as STALE.
 */
export function assessStale(
  state: AppState,
  config: FreshnessConfig | null,
  nowMs: number,
): StaleAssessment {
  if (config === null) {
    return { staleLabels: null, oldestAgeMs: null, thresholdConfigured: false };
  }

  const staleLabels: string[] = [];
  let oldestAgeMs: number | null = null;

  for (const entry of suppliedTimestamps(state)) {
    const epochMs = Date.parse(entry.timestamp);
    // Unparseable is INVALID and is reported by the freshness view, never as stale here.
    if (!Number.isFinite(epochMs)) continue;

    const ageMs = Math.max(nowMs - epochMs, 0);
    if (ageMs > config.staleTimeoutMs) {
      staleLabels.push(entry.label);
      if (oldestAgeMs === null || ageMs > oldestAgeMs) oldestAgeMs = ageMs;
    }
  }

  staleLabels.sort();
  return { staleLabels, oldestAgeMs, thresholdConfigured: true };
}

/**
 * The HMI's own data-path alerts. FR-014 AC4.
 *
 * Severity is FIXED per category, not computed: a lost feed is a WARNING about the link,
 * and stale data is a WARNING about age. Neither is a safety judgement, and neither is
 * escalated or de-escalated by anything the HMI observes about the mine.
 *
 * Both are `acknowledgeable: false` in M8 — no acknowledgment UI exists (M8D-C), and a
 * data-path condition clears when the condition clears, not when someone clicks.
 */
export function hmiDataPathAlerts(
  state: AppState,
  config: FreshnessConfig | null,
  nowMs: number,
): Alert[] {
  const alerts: Alert[] = [];
  const nowIso = new Date(nowMs).toISOString();

  if (isFeedLost(state.connection.status)) {
    alerts.push({
      alertId: COMM_LOSS_ALERT_ID,
      timestamp: state.connection.lastMessageAt ?? nowIso,
      severity: "WARNING",
      category: "COMM_LOSS",
      origin: "HMI",
      subject: { kind: "SYSTEM", id: "DATA_PATH" },
      message:
        state.connection.error !== null
          ? `Data feed lost: ${state.connection.error}`
          : "Data feed lost. Displayed values are the last supplied and are no longer updating.",
      reasonCode: state.connection.status,
      acknowledgeable: false,
      acknowledged: null,
      active: true,
    });
  }

  const stale = assessStale(state, config, nowMs);
  if (stale.staleLabels !== null && stale.staleLabels.length > 0) {
    alerts.push({
      alertId: STALE_DATA_ALERT_ID,
      timestamp: nowIso,
      severity: "WARNING",
      category: "STALE_DATA",
      origin: "HMI",
      subject: { kind: "SYSTEM", id: "DATA_PATH" },
      message: `${stale.staleLabels.length} supplied value(s) older than the configured threshold: ${stale.staleLabels.join(", ")}`,
      reasonCode: "STALE_DATA",
      acknowledgeable: false,
      acknowledged: null,
      active: true,
    });
  }

  return alerts;
}

export interface MergedAlerts {
  /** Supplied plus derived, ordered by severity then recency. */
  all: Alert[];
  supplied: Alert[];
  derived: Alert[];
  /** True when a threshold exists, so stale alerting is actually able to fire (M8D-B). */
  staleAlertingActive: boolean;
}

/**
 * Supplied alerts plus the HMI's data-path alerts, in one deterministic order.
 *
 * Supplied alerts are passed through UNCHANGED — not reordered internally, not re-worded,
 * not re-severitied. Ordering across the merged set is the existing `rankAlerts` display
 * sort, which is already deterministic on severity then recency then id.
 *
 * A derived alert whose id collides with a supplied one is DROPPED. Supplied data wins,
 * always. The `HMI:` prefix makes a genuine collision essentially impossible, but the
 * guard is cheap and the failure it prevents — a derived alert masking a real one — is not.
 */
export function mergedAlerts(
  state: AppState,
  config: FreshnessConfig | null,
  nowMs: number,
): MergedAlerts {
  const supplied = state.alerts;
  const suppliedIds = new Set(supplied.map((a) => a.alertId));

  const derived = hmiDataPathAlerts(state, config, nowMs).filter(
    (a) => !suppliedIds.has(a.alertId),
  );

  return {
    all: rankAlerts([...supplied, ...derived]),
    supplied: rankAlerts(supplied),
    derived,
    staleAlertingActive: config !== null,
  };
}
