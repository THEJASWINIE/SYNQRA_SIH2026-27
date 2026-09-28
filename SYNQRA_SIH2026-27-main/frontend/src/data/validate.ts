/**
 * Runtime validation — M2.
 *
 * The gate between untrusted external payloads and everything downstream. Nothing
 * reaches normalization unparsed, and normalization never receives `unknown`
 * (realtime-data skill §7).
 *
 * Validation is TOTAL: there is no cast-and-hope path. Failures are returned as typed
 * values, never thrown.
 */

import type { z } from "zod";
import { type MessageType, RAW_SCHEMAS } from "../contracts/raw";
import type { ValidationFailure, ValidationIssue } from "./errors";

export type ValidationResult<T> =
  | { ok: true; value: T }
  | { ok: false; failure: ValidationFailure };

/** Render a zod issue as a contract-level issue with a readable path. */
function toIssue(issue: z.core.$ZodIssue): ValidationIssue {
  const path = issue.path.length > 0 ? issue.path.join(".") : "(root)";
  const expected = "expected" in issue && issue.expected ? String(issue.expected) : issue.code;
  const received = "received" in issue && issue.received ? String(issue.received) : "invalid";
  return { path, expected, received, message: issue.message };
}

/**
 * Validate one payload against its contract schema.
 *
 * A failure here means the payload WAS supplied and was wrong — the caller must map it to
 * quality INVALID, never MISSING.
 */
export function validateMessage<K extends MessageType>(
  messageType: K,
  payload: unknown,
  receivedAt: string,
): ValidationResult<z.infer<(typeof RAW_SCHEMAS)[K]>> {
  const schema = RAW_SCHEMAS[messageType];
  const parsed = schema.safeParse(payload);

  if (parsed.success) {
    return { ok: true, value: parsed.data as z.infer<(typeof RAW_SCHEMAS)[K]> };
  }

  return {
    ok: false,
    failure: {
      kind: "VALIDATION",
      messageType,
      issues: parsed.error.issues.map(toIssue),
      receivedAt,
    },
  };
}

/**
 * Validate a batch of payloads of one message type.
 *
 * ONE BAD ITEM DOES NOT DISCARD THE BATCH. Valid siblings are returned alongside the
 * failures, so a single schema drift from the producer cannot blank the HMI
 * (realtime-data skill §7 rule 5).
 */
export function validateMany<K extends MessageType>(
  messageType: K,
  payloads: readonly unknown[],
  receivedAt: string,
): {
  valid: z.infer<(typeof RAW_SCHEMAS)[K]>[];
  failures: ValidationFailure[];
} {
  const valid: z.infer<(typeof RAW_SCHEMAS)[K]>[] = [];
  const failures: ValidationFailure[] = [];

  for (const payload of payloads) {
    const result = validateMessage(messageType, payload, receivedAt);
    if (result.ok) {
      valid.push(result.value);
    } else {
      failures.push(result.failure);
    }
  }

  return { valid, failures };
}
