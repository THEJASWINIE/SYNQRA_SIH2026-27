/**
 * Typed error models — M2.
 *
 * Two families, kept separate because they mean different things to an operator
 * (realtime-data skill §10):
 *
 *   ValidationFailure — this payload is bad. The pipe is fine.
 *   ProviderError     — the pipe is bad. It says nothing about the data.
 *
 * Both are returned values, never thrown. A promise rejection escaping the provider
 * boundary is a defect.
 */

import type { Iso8601 } from "../contracts/primitives";
import type { MessageType } from "../contracts/raw";

/** One thing that was wrong, and where. */
export interface ValidationIssue {
  /** Dotted path to the offending field, e.g. `position.segment_id`. */
  path: string;
  /** What the schema required. */
  expected: string;
  /** What arrived. */
  received: string;
  message: string;
}

/**
 * A payload was supplied and failed validation.
 *
 * This yields quality INVALID for the affected datum — never MISSING. MISSING means
 * nothing arrived; conflating the two hides an integration fault behind what looks like
 * a quiet link (realtime-data skill §6).
 */
export interface ValidationFailure {
  kind: "VALIDATION";
  messageType: MessageType;
  issues: ValidationIssue[];
  receivedAt: Iso8601;
}

export type ProviderErrorKind =
  /** Failed before a working connection was ever established. */
  | "INITIALIZATION"
  /** Lost or could not reach the source. */
  | "TRANSPORT"
  /** Reached the source but the exchange was malformed at the transport level. */
  | "PROTOCOL"
  /** Cancelled deliberately, e.g. component unmount. Not a fault. */
  | "ABORTED";

/**
 * The transport failed. Drives connection status; never marks individual data INVALID —
 * previously received values age into STALE on their own, which is NFR-012's required
 * behaviour.
 */
export interface ProviderError {
  kind: ProviderErrorKind;
  message: string;
  cause: string | null;
  occurredAt: Iso8601;
  /** So reconnect logic does not have to guess. */
  retryable: boolean;
}

export type DataPathError = ValidationFailure | ProviderError;

export function isValidationFailure(error: DataPathError): error is ValidationFailure {
  return error.kind === "VALIDATION";
}

export function isProviderError(error: DataPathError): error is ProviderError {
  return error.kind !== "VALIDATION";
}

export function providerError(
  kind: ProviderErrorKind,
  message: string,
  options: { cause?: string; retryable?: boolean; occurredAt: Iso8601 },
): ProviderError {
  return {
    kind,
    message,
    cause: options.cause ?? null,
    occurredAt: options.occurredAt,
    retryable: options.retryable ?? kind === "TRANSPORT",
  };
}
