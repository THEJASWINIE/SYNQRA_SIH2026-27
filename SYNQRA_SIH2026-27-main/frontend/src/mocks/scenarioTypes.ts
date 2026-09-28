/**
 * Scenario types — M3.
 *
 * Follows the structure in `.claude/skills/mock-scenarios/SKILL.md` §Scenario Structure.
 *
 * A scenario is AUTHORED DATA, not a program. It says what values appear at which step.
 * It never says what the values ought to be — that would be a Task 2 algorithm wearing a
 * mock's clothing (mock-scenarios skill, Core Rule).
 */

import type { MessageType } from "../contracts/raw";

/** The five FR-019 families, plus `test` for the failure-mode scenarios. */
export type ScenarioFamily =
  | "fog"
  | "friction"
  | "grade"
  | "fleet-density"
  | "communication-loss"
  | "test";

/**
 * A connection-level change declared by a step.
 *
 * Failures are data, not branching logic inside the provider (mock-scenarios skill
 * §Failure Representation).
 */
export interface StepEffects {
  /** Force a status transition. */
  status?: "CONNECTING" | "CONNECTED" | "RECONNECTING" | "DISCONNECTED" | "ERROR";
  /** Accompanying typed error, using the M2 `ProviderError` kinds. */
  error?: {
    kind: "INITIALIZATION" | "TRANSPORT" | "PROTOCOL" | "ABORTED";
    message: string;
    retryable?: boolean;
  };
  /** Stop emitting while staying in the current status — the "stale feed" case. */
  haltEmission?: boolean;
  /** Resume emitting. */
  resumeEmission?: boolean;
  /** Explicitly remove entities. MID-C: absence never means deletion. */
  deletions?: {
    vehicles?: string[];
    safety?: string[];
    road?: string[];
    forecasts?: string[];
    bottlenecks?: string[];
    arrivals?: string[];
    slots?: string[];
    dispatch?: string[];
  };
}

/**
 * Raw payloads to publish at a step, keyed by contract message type.
 *
 * These are wire-format (snake_case) payloads, exactly as the real producer would send
 * them, so mock data travels the same validate → normalize → patch path as live data.
 * A mock that bypassed validation would prove nothing about M12.
 */
export type StepEmissions = Partial<Record<MessageType, unknown[]>>;

export interface ScenarioStep {
  /** 0-based. Fixes emission order. */
  index: number;
  /** Offset from scenario start. NOT wall-clock time. */
  atMs: number;
  emit?: StepEmissions;
  effects?: StepEffects;
}

export interface Scenario {
  id: string;
  name: string;
  description: string;
  family: ScenarioFamily;
  provider: "MOCK";
  /** Nominal spacing between steps. Playback speed is governed by the injected scheduler. */
  stepIntervalMs: number;
  steps: ScenarioStep[];
}

/**
 * What FR-019 needs in order to list scenarios. Derived from scenario files — never
 * maintained as a separate hand-written list, which would drift.
 */
export interface ScenarioDescriptor {
  id: string;
  name: string;
  description: string;
  family: ScenarioFamily;
  stepCount: number;
  durationMs: number;
}

/** Typed miss. An unknown id is a normal outcome, not an exception. */
export interface ScenarioNotFound {
  kind: "SCENARIO_NOT_FOUND";
  id: string;
  available: string[];
}

export type ScenarioLookup =
  | { ok: true; scenario: Scenario }
  | { ok: false; error: ScenarioNotFound };
