/**
 * DataProvider — INTERFACE DECLARATION ONLY. M2.
 *
 * Source of truth: `requirements/task1-data-contract.md` §13.
 *
 * NO IMPLEMENTATION EXISTS IN M2 AND NONE MAY BE ADDED HERE.
 * `MockDataProvider` is M3, `ReplayProvider` is M9, `LiveDataProvider` is M12.
 *
 * The interface is what makes those three interchangeable. Four properties keep the swap
 * safe, and each is a rule this file exists to hold (realtime-data skill §9):
 *
 *   1. One output shape — providers emit a normalized `ProviderPatch`, never raw frames.
 *   2. Validation and normalization live OUTSIDE the provider, shared by all three.
 *   3. One status vocabulary, whatever "disconnected" physically means.
 *   4. Selection by injection — a screen that imports a concrete provider is a defect.
 */

import type { AppStatePatch, ConnectionStatus, ProviderKind } from "../contracts/appState";
import type { Iso8601 } from "../contracts/primitives";
import type { ProviderError } from "../data/errors";

/**
 * One delivery from a provider, before validation.
 *
 * `receivedAt` is the HMI's own clock reading for the batch. It is deliberately here and
 * not inside `Sourced<T>`: receipt time is a property of the delivery, not of each field,
 * and duplicating it per field would be waste.
 *
 * It exists so clock skew (RISK-I4) can be MEASURED at M12. Task 1 does not correct for
 * skew — that would be inventing a calibration nobody has authorized.
 */
export interface ProviderUpdate {
  receivedAt: Iso8601;
  /** Raw and untrusted. Must pass through `data/validate.ts` before use. */
  payload: unknown;
}

/**
 * Entity ids to remove, per keyed collection of `AppState`.
 *
 * Only the eight `Record`-keyed slices appear here. The collection-valued slices
 * (`alerts`, `events`) are replace-whole, and the singleton slices (`topology`, `health`,
 * `kpis`, `cv`) are replaced or left alone by `changes`.
 */
export interface EntityDeletions {
  vehicles?: readonly string[];
  safety?: readonly string[];
  road?: readonly string[];
  forecasts?: readonly string[];
  bottlenecks?: readonly string[];
  arrivals?: readonly string[];
  slots?: readonly string[];
  dispatch?: readonly string[];
}

/**
 * What a provider hands to its subscribers. MID-C.
 *
 * `Partial<AppState>` structurally cannot distinguish "no news about this vehicle" from
 * "this vehicle is gone". Left implicit, one of two failures is certain: entities that
 * vanish because an update happened not to mention them, or entities that linger after
 * genuine removal. On a fleet-monitoring display the first is the more dangerous.
 *
 * So deletion travels its own channel. `AppStatePatch` remains EXACTLY
 * `Partial<AppState>` as the frozen contract §13 specifies — this wraps it, and does not
 * redefine it.
 *
 * Semantics:
 *   - key missing from `changes`      → NO CHANGE
 *   - key present with an entity      → UPSERT
 *   - id listed in `deletions`        → DELETE
 *
 * Merge order is deletions first, then changes. An entity in both therefore survives:
 * that is a re-add, not a race.
 */
export interface ProviderPatch {
  changes: AppStatePatch;
  deletions?: EntityDeletions;
}

export type StatusListener = (status: ConnectionStatus, error: ProviderError | null) => void;

export type UpdateListener = (patch: ProviderPatch) => void;

/** Returned by subscribe/onStatusChange. Calling it detaches the listener. */
export type Unsubscribe = () => void;

export interface DataProvider {
  /** Which provider this is. Drives `AppState.connection.provider`; FR-017 requires replay to be unmistakable. */
  readonly kind: ProviderKind;

  /**
   * Establish the source. Explicit rather than implicit-on-import, so initialization
   * failure is observable and testable.
   * Rejects with a `ProviderError` shaped failure; never throws a bare value.
   */
  connect(): Promise<void>;

  /** Tear down deterministically. Required for NFR-004 reconnect testing and React cleanup. */
  disconnect(): Promise<void>;

  /**
   * Emits normalized partial updates; never raw transport frames.
   * Returns an unsubscribe function, so a leak is impossible by construction.
   *
   * Carries a `ProviderPatch` so deletion is explicit (MID-C) — a missing key means
   * "no change", never "removed".
   */
  subscribe(onUpdate: UpdateListener): Unsubscribe;

  /**
   * Observe lifecycle transitions.
   *
   * Without this, connection status would have to be inferred from data silence, which
   * cannot distinguish "no news" from "no link" — and NFR-012's DEGRADED behaviour
   * depends on telling those apart.
   */
  onStatusChange(listener: StatusListener): Unsubscribe;

  /**
   * HMI ALERT/EVENT ACKNOWLEDGEMENT ONLY.
   *
   * Supported by contract §13 and permitted by PAD-D. Acknowledgement changes display
   * state and writes an audit record (NFR-007). It never clears, suppresses or downgrades
   * the underlying condition, and safety-critical local protection never depends on it
   * (FR-015).
   *
   * It MUST NOT:
   *   - issue vehicle commands
   *   - override safety
   *   - change vehicle control state
   *   - modify v_safe
   *   - modify h_safe
   *   - trigger dispatch
   *   - actuate equipment
   *
   * Whether the HMI may issue commands at all (AMB-008) and what "override" means
   * (AMB-009) are UNRESOLVED. Retaining this method is not a ruling on either; PAD-B's
   * safe default — display and acknowledge only — continues to hold.
   *
   * Rejected while the provider is REPLAY (FR-017).
   */
  sendAcknowledgement(alertId: string, actor: string): Promise<void>;
}
