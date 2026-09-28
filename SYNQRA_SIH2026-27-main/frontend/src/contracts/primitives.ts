/**
 * Contract primitives — M2.
 *
 * Source of truth: `requirements/task1-data-contract.md` §1.
 * Naming: normalized domain types use camelCase (MAD-F). Raw wire types keep the
 * contract's snake_case and live in `raw.ts` (MAD-E).
 *
 * Scope: these are shapes only. Nothing here computes an operational value.
 */

/** ISO-8601, UTC, millisecond precision. Kept as the exact string the source sent. */
export type Iso8601 = string;

export type VehicleId = string;
export type SegmentId = string;
export type NodeId = string;
export type SlotId = string;
export type CommandId = string;
export type RouteId = string;
export type ComponentId = string;

/**
 * Data quality. Contract §1.
 *
 * The four states are distinct and must never be collapsed:
 *  - MISSING — the complete datum was NOT supplied.
 *  - INVALID — the datum WAS supplied but failed validation.
 *  - STALE   — valid, but older than the configured threshold. Value is retained.
 *  - OK      — valid and within the threshold.
 *
 * A malformed payload must never become MISSING, and an INVALID datum is never
 * also reported as STALE — age is meaningless for something that failed validation.
 */
export type Quality = "OK" | "STALE" | "MISSING" | "INVALID";

/**
 * Provenance and freshness wrapper for every externally supplied datum.
 * Contract §1. Built only by `data/sourced.ts` — a second provenance wrapper is a defect.
 *
 * `value`, `timestamp` and `sourceId` are externally supplied.
 * `ageMs` and `quality` are the only fields Task 1 derives (contract §12 items 1–2).
 */
export interface Sourced<T> {
  /** null = not supplied. Never coerced to 0. */
  value: T | null;
  /** When the SOURCE produced the datum. Null only when nothing was supplied. */
  timestamp: Iso8601 | null;
  sourceId: ComponentId | null;
  /** Derived. Never NaN, never negative. Zero when age is not assessable. */
  ageMs: number;
  /** Derived. */
  quality: Quality;
}

/** A value with its supplied uncertainty. Contract §1. */
export interface Estimate {
  value: number | null;
  /** null = uncertainty not supplied. */
  sigma: number | null;
}

/** A timestamp normalized for arithmetic, alongside the original string (NFR-007). */
export interface NormalizedTimestamp {
  /** The exact string the source sent, preserved for traceability. */
  iso: Iso8601;
  /** Derived epoch milliseconds, for age arithmetic only. */
  epochMs: number;
}
