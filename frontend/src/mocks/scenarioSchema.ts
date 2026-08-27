/**
 * Scenario file schema — M3.
 *
 * Scenario files are validated, not trusted because they happen to be ours. A malformed
 * scenario must fail at load with a typed error, before a single emission — otherwise the
 * failure surfaces later as mysterious bad data (mock-scenarios skill §Failure
 * Representation).
 */

import { z } from "zod";
import { MESSAGE_TYPES } from "../contracts/raw";

const familySchema = z.enum([
  "fog",
  "friction",
  "grade",
  "fleet-density",
  "communication-loss",
  "test",
]);

const effectsSchema = z
  .object({
    status: z.enum(["CONNECTING", "CONNECTED", "RECONNECTING", "DISCONNECTED", "ERROR"]).optional(),
    error: z
      .object({
        kind: z.enum(["INITIALIZATION", "TRANSPORT", "PROTOCOL", "ABORTED"]),
        message: z.string(),
        retryable: z.boolean().optional(),
      })
      .optional(),
    haltEmission: z.boolean().optional(),
    resumeEmission: z.boolean().optional(),
    deletions: z
      .object({
        vehicles: z.array(z.string()).optional(),
        safety: z.array(z.string()).optional(),
        road: z.array(z.string()).optional(),
        forecasts: z.array(z.string()).optional(),
        bottlenecks: z.array(z.string()).optional(),
        arrivals: z.array(z.string()).optional(),
        slots: z.array(z.string()).optional(),
        dispatch: z.array(z.string()).optional(),
      })
      .optional(),
  })
  .strict();

/**
 * Emissions are keyed by contract message type. The payloads themselves are `unknown`
 * here on purpose: they are validated per-message by `data/validate.ts` at emission time,
 * on the real path. Validating them twice, in two places, would let the two definitions
 * drift.
 */
const KNOWN_MESSAGE_TYPES = new Set<string>(MESSAGE_TYPES);

const emitSchema = z
  .record(z.string(), z.array(z.unknown()))
  .refine((emit) => Object.keys(emit).every((key) => KNOWN_MESSAGE_TYPES.has(key)), {
    message: `emit keys must be contract message types: ${MESSAGE_TYPES.join(", ")}`,
  });

const stepSchema = z
  .object({
    index: z.number().int().nonnegative(),
    atMs: z.number().int().nonnegative(),
    emit: emitSchema.optional(),
    effects: effectsSchema.optional(),
  })
  .strict();

export const scenarioSchema = z
  .object({
    id: z.string().min(1),
    name: z.string().min(1),
    description: z.string().min(1),
    family: familySchema,
    provider: z.literal("MOCK"),
    stepIntervalMs: z.number().int().positive(),
    steps: z.array(stepSchema).min(1),
  })
  .strict()
  .refine((s) => s.steps.every((step, i) => step.index === i), {
    message: "step.index must be sequential from 0 — emission order is file order",
  })
  .refine((s) => s.steps.every((step, i) => i === 0 || step.atMs >= (s.steps[i - 1]?.atMs ?? 0)), {
    message: "step.atMs must be non-decreasing",
  });

export type ScenarioParseResult =
  | { ok: true; value: z.infer<typeof scenarioSchema> }
  | { ok: false; issues: string[] };

export function parseScenario(input: unknown): ScenarioParseResult {
  const parsed = scenarioSchema.safeParse(input);
  if (parsed.success) return { ok: true, value: parsed.data };
  return {
    ok: false,
    issues: parsed.error.issues.map(
      (i) => `${i.path.length > 0 ? i.path.join(".") : "(root)"}: ${i.message}`,
    ),
  };
}
