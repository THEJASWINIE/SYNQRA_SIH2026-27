/**
 * Timestamp normalization — M2.
 *
 * Rules from the realtime-data skill §5 and the frozen contract §1.
 *
 * Timestamps are the foundation of freshness. Getting them wrong makes stale data look
 * current, which is exactly the failure NFR-012 exists to prevent. Every rule below
 * exists to make a wrong timestamp loud rather than plausible.
 */

import type { Iso8601, NormalizedTimestamp } from "../contracts/primitives";

export type TimestampResult =
  | { ok: true; value: NormalizedTimestamp }
  | { ok: false; reason: TimestampRejection };

export type TimestampRejection =
  | "ABSENT"
  | "NOT_A_STRING"
  | "UNPARSEABLE"
  | "NO_TIMEZONE"
  | "TOO_FAR_FUTURE";

/**
 * How far ahead of the HMI clock a source timestamp may be before it is rejected.
 *
 * This is a tolerance for ordinary clock jitter between machines, not a staleness
 * threshold — the staleness threshold is NFR-003's, which has no authoritative value
 * (AMB-014) and is supplied by configuration. This tolerance is a validity bound: past
 * it, a timestamp is not "very fresh", it is wrong.
 *
 * Clock skew between the source and the HMI is a recorded integration risk (RISK-I4).
 * Task 1 records what is needed to measure skew at M12. It does not correct for it.
 */
export const FUTURE_TOLERANCE_MS = 60_000;

/**
 * An ISO-8601 string must carry timezone information: a trailing `Z`, or a `+hh:mm` /
 * `-hh:mm` offset after the time portion.
 *
 * A string without one is rejected rather than assumed to be local time. Silent
 * local-time coercion is the bug class that makes a stale reading look fresh.
 */
function hasTimezone(value: string): boolean {
  if (/[zZ]$/.test(value)) return true;
  // Offset must follow the time part, so only look after 'T'.
  const timePart = value.includes("T") ? value.slice(value.indexOf("T")) : "";
  return /[+-]\d{2}:?\d{2}$/.test(timePart);
}

/**
 * Normalize a source timestamp.
 *
 * Returns the original string untouched alongside a derived epoch value. The original is
 * preserved because NFR-007 traceability requires the exact string the source sent; the
 * epoch value exists only so age arithmetic does not re-parse on every read.
 */
export function normalizeTimestamp(input: unknown, nowMs: number): TimestampResult {
  if (input === null || input === undefined) {
    return { ok: false, reason: "ABSENT" };
  }
  if (typeof input !== "string") {
    return { ok: false, reason: "NOT_A_STRING" };
  }
  if (input.trim() === "") {
    return { ok: false, reason: "ABSENT" };
  }
  if (!hasTimezone(input)) {
    return { ok: false, reason: "NO_TIMEZONE" };
  }

  const epochMs = Date.parse(input);
  if (!Number.isFinite(epochMs)) {
    return { ok: false, reason: "UNPARSEABLE" };
  }
  if (epochMs > nowMs + FUTURE_TOLERANCE_MS) {
    return { ok: false, reason: "TOO_FAR_FUTURE" };
  }

  return { ok: true, value: { iso: input as Iso8601, epochMs } };
}

/**
 * Age of a datum, in milliseconds.
 *
 * Never NaN, never negative. A timestamp slightly ahead of the local clock — ordinary
 * skew, within tolerance — yields 0 rather than a negative number, because a negative
 * age silently reading as "very fresh" is precisely what must not happen.
 */
export function ageMsFrom(epochMs: number, nowMs: number): number {
  if (!Number.isFinite(epochMs) || !Number.isFinite(nowMs)) return 0;
  const age = nowMs - epochMs;
  return age > 0 ? age : 0;
}
