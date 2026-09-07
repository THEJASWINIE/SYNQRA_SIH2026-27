/**
 * Phase 10 — Failure Injection / Demo Lab Client.
 *
 * Dedicated API transport and evaluation logic for Phase 10 Failure Injection.
 *
 * Architectural boundaries:
 *   - Screens never call fetch directly (Phase 8 §23 rule).
 *   - No new backend endpoints.
 *   - Never calls /api/hardware/telemetry.
 *   - All injections carry SIMULATION provenance.
 *   - Pure evaluators are independent of UI and testable with mock fetch.
 */

import { API_BASE_URL } from "./healthClient";
import {
  fetchObservability,
  type TelemetryCounters,
  type CommandGatewayCounters,
} from "./observabilityClient";

// =====================================================================
// SCENARIO TYPES
// =====================================================================

export type ScenarioStatus = "IDLE" | "RUNNING" | "PASS" | "FAIL" | "MANUAL";

export interface ScenarioResult {
  status: ScenarioStatus;
  expected: string;
  observed: string;
  evidence: string;
}

export interface ScenarioDefinition {
  id: string;
  title: string;
  description: string;
}

export interface LogEntry {
  timestamp: string;
  scenario: string;
  request: string;
  response: string;
  result: ScenarioStatus;
}

// =====================================================================
// SCENARIO DEFINITIONS
// =====================================================================

export const SCENARIOS: ScenarioDefinition[] = [
  {
    id: "telemetry-pause",
    title: "1. Telemetry Pause / Recovery",
    description: "Verifies ONLINE → STALE → ONLINE transition when telemetry pauses and resumes.",
  },
  {
    id: "malformed-json",
    title: "2. Malformed JSON",
    description: "Sends invalid JSON to /api/telemetry. Expects HTTP 400, no cache/Twin mutation.",
  },
  {
    id: "invalid-speed-type",
    title: "3. Invalid Speed Type",
    description: 'Sends speed="fast" (string). Expects HTTP 400, rejected before mutation.',
  },
  {
    id: "negative-speed",
    title: "4. Negative Speed",
    description: "Sends speed=-5.0. Expects HTTP 400, rejected before mutation.",
  },
  {
    id: "duplicate-sequence",
    title: "5. Duplicate Sequence",
    description: "Sends identical sequence twice. Both HTTP 200; Twin rejects duplicate (counter Δ=+1).",
  },
  {
    id: "out-of-order",
    title: "6. Out-of-Order Sequence",
    description: "Sends higher sequence then lower. Both HTTP 200; Twin rejects OOO (counter Δ=+1).",
  },
  {
    id: "unknown-vehicle",
    title: "7. Unknown Vehicle Command",
    description: 'Sends command for "GHOST_TRUCK_X". HTTP 200, status=UNKNOWN_VEHICLE.',
  },
  {
    id: "invalid-action",
    title: "8. Invalid Command Action",
    description: 'Sends action="EXPLODE". Expects HTTP 400.',
  },
  {
    id: "duplicate-command",
    title: "9. Duplicate Command ID",
    description: "Sends same command_id twice. First: ACCEPTED. Second: DUPLICATE.",
  },
  {
    id: "oversized-payload",
    title: "10. Oversized Payload",
    description: "Sends > 64 KiB body to /api/telemetry. Expects HTTP 413, no mutation.",
  },
];

// =====================================================================
// PURE EVALUATORS — tested independently
// =====================================================================

/** Generate a unique test ID to avoid polluting real state. */
export function demoId(prefix: string): string {
  return `DEMO-${prefix}-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
}

/** Generate a fresh sequence number guaranteed to be above live simulator sequence. */
export function demoSequence(): number {
  return 10_000_000 + Math.floor(Math.random() * 80_000_000);
}

export function evaluateHttpRejection(
  httpStatus: number,
  expectedStatus: number,
  detail: string,
): ScenarioResult {
  const pass = httpStatus === expectedStatus;
  return {
    status: pass ? "PASS" : "FAIL",
    expected: `HTTP ${expectedStatus}`,
    observed: `HTTP ${httpStatus}`,
    evidence: pass
      ? `Backend rejected with ${expectedStatus}: ${detail}`
      : `Expected HTTP ${expectedStatus}, got ${httpStatus}: ${detail}`,
  };
}

export function evaluateCounterDelta(
  counterName: string,
  before: number | null,
  after: number | null,
  expectedDelta: number,
): ScenarioResult {
  if (before === null || after === null) {
    return {
      status: "FAIL",
      expected: `${counterName} Δ=${expectedDelta}`,
      observed: `${counterName} before=${before}, after=${after}`,
      evidence: "Counter unavailable (null) — cannot verify",
    };
  }
  const delta = after - before;
  const pass = delta === expectedDelta;
  return {
    status: pass ? "PASS" : "FAIL",
    expected: `${counterName} Δ=${expectedDelta}`,
    observed: `${counterName}: ${before} → ${after} (Δ=${delta})`,
    evidence: pass
      ? `Counter incremented by exactly ${expectedDelta}`
      : `Expected Δ=${expectedDelta}, got Δ=${delta}`,
  };
}

export function evaluateCommandStatus(
  httpStatus: number,
  bodyStatus: string | null,
  expectedBodyStatus: string,
): ScenarioResult {
  const pass = bodyStatus === expectedBodyStatus;
  return {
    status: pass ? "PASS" : "FAIL",
    expected: `response.status = "${expectedBodyStatus}"`,
    observed: `HTTP ${httpStatus}, response.status = "${bodyStatus}"`,
    evidence: pass
      ? `Backend returned expected status: ${expectedBodyStatus}`
      : `Expected "${expectedBodyStatus}", got "${bodyStatus}"`,
  };
}

// =====================================================================
// API HELPERS — transport layer
// =====================================================================

export interface HttpResult {
  status: number;
  body: Record<string, unknown> | null;
  detail: string;
}

export async function postTelemetryRaw(
  rawBody: string,
  fetchImpl: typeof fetch = fetch,
): Promise<HttpResult> {
  try {
    const response = await fetchImpl(`${API_BASE_URL}/api/telemetry`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: rawBody,
    });
    let body: Record<string, unknown> | null = null;
    let detail = "";
    try {
      const parsed: unknown = await response.json();
      if (typeof parsed === "object" && parsed !== null) {
        body = parsed as Record<string, unknown>;
        detail =
          typeof body.detail === "string"
            ? body.detail
            : typeof body.status === "string"
              ? body.status
              : JSON.stringify(body);
      }
    } catch {
      detail = `HTTP ${response.status} (no JSON body)`;
    }
    return { status: response.status, body, detail };
  } catch (error) {
    return {
      status: 0,
      body: null,
      detail: error instanceof Error ? error.message : "Network error",
    };
  }
}

export async function postTelemetryJson(
  payload: Record<string, unknown>,
  fetchImpl: typeof fetch = fetch,
): Promise<HttpResult> {
  return postTelemetryRaw(JSON.stringify(payload), fetchImpl);
}

export async function postCommand(
  payload: Record<string, unknown>,
  fetchImpl: typeof fetch = fetch,
): Promise<HttpResult> {
  try {
    const response = await fetchImpl(`${API_BASE_URL}/api/commands`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    let body: Record<string, unknown> | null = null;
    let detail = "";
    try {
      const parsed: unknown = await response.json();
      if (typeof parsed === "object" && parsed !== null) {
        body = parsed as Record<string, unknown>;
        detail =
          typeof body.detail === "string"
            ? body.detail
            : typeof body.message === "string"
              ? body.message
              : typeof body.status === "string"
                ? body.status
                : JSON.stringify(body);
      }
    } catch {
      detail = `HTTP ${response.status} (no JSON body)`;
    }
    return { status: response.status, body, detail };
  } catch (error) {
    return {
      status: 0,
      body: null,
      detail: error instanceof Error ? error.message : "Network error",
    };
  }
}

export async function getObsCounters(
  fetchImpl: typeof fetch = fetch,
): Promise<{
  ingest: TelemetryCounters | null;
  gateway: CommandGatewayCounters | null;
}> {
  const result = await fetchObservability({ fetchImpl });
  if (result.kind !== "ok") return { ingest: null, gateway: null };
  return {
    ingest: result.snapshot.telemetryIngest,
    gateway: result.snapshot.commandGateway,
  };
}

// =====================================================================
// SCENARIO RUNNERS
// =====================================================================

export type ScenarioRunner = (fetchImpl?: typeof fetch) => Promise<ScenarioResult>;

export function createScenarioRunners(
  fetchImpl: typeof fetch = fetch,
): Record<string, () => Promise<ScenarioResult>> {
  return {
    "malformed-json": async () => {
      const r = await postTelemetryRaw("{bad json here}", fetchImpl);
      return evaluateHttpRejection(r.status, 400, r.detail);
    },

    "invalid-speed-type": async () => {
      const r = await postTelemetryJson(
        { vehicle_id: "TRUCK_01", speed: "fast" },
        fetchImpl,
      );
      return evaluateHttpRejection(r.status, 400, r.detail);
    },

    "negative-speed": async () => {
      const r = await postTelemetryJson(
        { vehicle_id: "TRUCK_01", speed: -5.0 },
        fetchImpl,
      );
      return evaluateHttpRejection(r.status, 400, r.detail);
    },

    "duplicate-sequence": async () => {
      const before = await getObsCounters(fetchImpl);
      const seq = demoSequence();
      const payload = { vehicle_id: "TRUCK_01", sequence_number: seq, speed: 2.0 };
      await postTelemetryJson(payload, fetchImpl);
      await postTelemetryJson(payload, fetchImpl);
      const after = await getObsCounters(fetchImpl);
      return evaluateCounterDelta(
        "duplicate",
        before.ingest?.duplicate ?? null,
        after.ingest?.duplicate ?? null,
        1,
      );
    },

    "out-of-order": async () => {
      const before = await getObsCounters(fetchImpl);
      const highSeq = demoSequence();
      const lowSeq = highSeq - 100;
      await postTelemetryJson(
        { vehicle_id: "TRUCK_01", sequence_number: highSeq, speed: 3.0 },
        fetchImpl,
      );
      await postTelemetryJson(
        { vehicle_id: "TRUCK_01", sequence_number: lowSeq, speed: 1.0 },
        fetchImpl,
      );
      const after = await getObsCounters(fetchImpl);
      return evaluateCounterDelta(
        "out_of_order",
        before.ingest?.outOfOrder ?? null,
        after.ingest?.outOfOrder ?? null,
        1,
      );
    },

    "unknown-vehicle": async () => {
      const cmdId = demoId("UV");
      const r = await postCommand(
        {
          command_id: cmdId,
          vehicle_id: "GHOST_TRUCK_X",
          action: "STOP",
          target_speed: 0.0,
          reason: "DEMO_LAB_TEST",
        },
        fetchImpl,
      );
      const bodyStatus = typeof r.body?.status === "string" ? r.body.status : null;
      return evaluateCommandStatus(r.status, bodyStatus, "UNKNOWN_VEHICLE");
    },

    "invalid-action": async () => {
      const r = await postCommand(
        {
          command_id: demoId("IA"),
          vehicle_id: "TRUCK_01",
          action: "EXPLODE",
          target_speed: 1.0,
          reason: "DEMO_LAB_TEST",
        },
        fetchImpl,
      );
      return evaluateHttpRejection(r.status, 400, r.detail);
    },

    "duplicate-command": async () => {
      const cmdId = demoId("DC");
      const r1 = await postCommand(
        {
          command_id: cmdId,
          vehicle_id: "TRUCK_01",
          action: "STOP",
          target_speed: 0.0,
          reason: "DEMO_LAB_TEST",
        },
        fetchImpl,
      );
      const r2 = await postCommand(
        {
          command_id: cmdId,
          vehicle_id: "TRUCK_01",
          action: "STOP",
          target_speed: 0.0,
          reason: "DEMO_LAB_TEST",
        },
        fetchImpl,
      );
      const firstStatus = typeof r1.body?.status === "string" ? r1.body.status : null;
      const secondStatus = typeof r2.body?.status === "string" ? r2.body.status : null;
      const pass = secondStatus === "DUPLICATE";
      return {
        status: pass ? "PASS" : "FAIL",
        expected: 'First: ACCEPTED/REJECTED. Second: response.status = "DUPLICATE"',
        observed: `First: ${firstStatus}. Second: ${secondStatus}`,
        evidence: pass
          ? `Command ${cmdId} correctly rejected as duplicate on second submission`
          : `Expected DUPLICATE for second submission, got "${secondStatus}"`,
      };
    },

    "oversized-payload": async () => {
      const big = "A".repeat(70000);
      const r = await postTelemetryRaw(
        JSON.stringify({ vehicle_id: "TRUCK_01", data: big }),
        fetchImpl,
      );
      return evaluateHttpRejection(r.status, 413, r.detail);
    },
  };
}
