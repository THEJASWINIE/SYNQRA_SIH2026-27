/**
 * Scenario data tests — M3.
 * Covers required tests 1 (registry), 2 (schema), 3 (validation path), 4 (normalization),
 * 20 (scale).
 *
 * These assert the SHAPE and SCOPE of the authored data. Behaviour under playback is
 * tested in `providers/MockDataProvider.test.ts`.
 */

import { describe, expect, it } from "vitest";
import type { MessageType } from "../contracts/raw";
import { validateMessage } from "../data/validate";
import { resolveTimeTokens } from "../providers/MockDataProvider";
import { getScenario, listScenarios, scenarioIds } from "./registry";
import { parseScenario } from "./scenarioSchema";
import type { ScenarioFamily } from "./scenarioTypes";

const NOW_MS = Date.parse("2026-01-01T00:00:00.000Z");
const RECEIVED_AT = "2026-01-01T00:00:00.000Z";

const EXPECTED_IDS = [
  "nominal",
  "fog-rolling-in",
  "friction-degradation",
  "steep-grade",
  "fleet-density-high",
  "communication-loss",
  "stale-feed",
  "disconnect-reconnect",
  "slot-conflict",
  "envelope-violation",
  "scale",
];

/** The five families FR-019 names by hand. */
const FR019_FAMILIES: ScenarioFamily[] = [
  "fog",
  "friction",
  "grade",
  "fleet-density",
  "communication-loss",
];

describe("registry completeness (test 1)", () => {
  it("registers all eleven scenarios", () => {
    expect(scenarioIds().sort()).toEqual([...EXPECTED_IDS].sort());
  });

  it("exposes a descriptor per scenario", () => {
    expect(listScenarios()).toHaveLength(EXPECTED_IDS.length);
  });

  it("descriptors are derived from the files, not hand-maintained", () => {
    for (const descriptor of listScenarios()) {
      const lookup = getScenario(descriptor.id);
      expect(lookup.ok).toBe(true);
      if (!lookup.ok) continue;
      expect(descriptor.name).toBe(lookup.scenario.name);
      expect(descriptor.stepCount).toBe(lookup.scenario.steps.length);
    }
  });

  it("every FR-019 family is represented", () => {
    const families = new Set(listScenarios().map((d) => d.family));
    for (const family of FR019_FAMILIES) {
      expect(families.has(family), `missing family: ${family}`).toBe(true);
    }
  });

  it("an unknown id returns a typed not-found, and does not throw", () => {
    const lookup = getScenario("no-such-scenario");
    expect(lookup.ok).toBe(false);
    if (lookup.ok) return;
    expect(lookup.error.kind).toBe("SCENARIO_NOT_FOUND");
    expect(lookup.error.available.length).toBe(EXPECTED_IDS.length);
  });
});

describe("scenario schema validation (test 2)", () => {
  it.each(EXPECTED_IDS)("%s validates against the schema", (id) => {
    const lookup = getScenario(id);
    expect(lookup.ok).toBe(true);
    if (!lookup.ok) return;
    expect(parseScenario(lookup.scenario).ok).toBe(true);
  });

  it("rejects non-sequential step indexes", () => {
    const result = parseScenario({
      id: "x",
      name: "x",
      description: "x",
      family: "test",
      provider: "MOCK",
      stepIntervalMs: 1000,
      steps: [
        { index: 0, atMs: 0 },
        { index: 5, atMs: 1000 },
      ],
    });
    expect(result.ok).toBe(false);
  });

  it("rejects a decreasing atMs", () => {
    const result = parseScenario({
      id: "x",
      name: "x",
      description: "x",
      family: "test",
      provider: "MOCK",
      stepIntervalMs: 1000,
      steps: [
        { index: 0, atMs: 5000 },
        { index: 1, atMs: 1000 },
      ],
    });
    expect(result.ok).toBe(false);
  });

  it("rejects an unknown top-level key", () => {
    expect(
      parseScenario({
        id: "x",
        name: "x",
        description: "x",
        family: "test",
        provider: "MOCK",
        stepIntervalMs: 1000,
        steps: [{ index: 0, atMs: 0 }],
        surprise: true,
      }).ok,
    ).toBe(false);
  });
});

describe("every authored payload passes the real M2 validation path (test 3)", () => {
  it.each(EXPECTED_IDS)("%s", (id) => {
    const lookup = getScenario(id);
    expect(lookup.ok).toBe(true);
    if (!lookup.ok) return;

    let checked = 0;
    for (const step of lookup.scenario.steps) {
      if (!step.emit) continue;
      for (const [type, payloads] of Object.entries(step.emit)) {
        for (const payload of payloads ?? []) {
          const resolved = resolveTimeTokens(payload, NOW_MS);
          const result = validateMessage(type as MessageType, resolved, RECEIVED_AT);
          if (!result.ok) {
            throw new Error(
              `${id} step ${step.index} ${type}: ${result.failure.issues
                .map((i) => `${i.path} ${i.message}`)
                .join("; ")}`,
            );
          }
          checked += 1;
        }
      }
    }
    expect(checked).toBeGreaterThan(0);
  });
});

describe("time tokens (test 4 support)", () => {
  it("resolves @now to an ISO timestamp", () => {
    expect(resolveTimeTokens("@now", NOW_MS)).toBe("2026-01-01T00:00:00.000Z");
  });

  it("resolves a positive offset", () => {
    expect(resolveTimeTokens("@now+60000", NOW_MS)).toBe("2026-01-01T00:01:00.000Z");
  });

  it("resolves a negative offset", () => {
    expect(resolveTimeTokens("@now-60000", NOW_MS)).toBe("2025-12-31T23:59:00.000Z");
  });

  it("leaves ordinary strings alone", () => {
    expect(resolveTimeTokens("V-1", NOW_MS)).toBe("V-1");
    expect(resolveTimeTokens("@nowhere", NOW_MS)).toBe("@nowhere");
  });

  it("recurses through objects and arrays", () => {
    const out = resolveTimeTokens({ a: ["@now", { b: "@now+1000" }] }, NOW_MS) as {
      a: [string, { b: string }];
    };
    expect(out.a[0]).toBe("2026-01-01T00:00:00.000Z");
    expect(out.a[1].b).toBe("2026-01-01T00:00:01.000Z");
  });

  it("no scenario file stores a wall-clock timestamp", () => {
    // Authored files carry offsets only, so a committed scenario cannot go stale on disk.
    for (const id of EXPECTED_IDS) {
      const lookup = getScenario(id);
      if (!lookup.ok) continue;
      const serialized = JSON.stringify(lookup.scenario);
      expect(serialized, `${id} contains an absolute timestamp`).not.toMatch(
        /"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}/,
      );
    }
  });
});

describe("scale scenario (test 20)", () => {
  it("carries 50 vehicles and a 20-node topology", () => {
    const lookup = getScenario("scale");
    expect(lookup.ok).toBe(true);
    if (!lookup.ok) return;

    const topologyStep = lookup.scenario.steps.find((s) => s.emit?.MineTopology);
    const vehicleStep = lookup.scenario.steps.find((s) => s.emit?.VehicleState);
    expect(topologyStep).toBeDefined();
    expect(vehicleStep).toBeDefined();

    const topology = topologyStep?.emit?.MineTopology?.[0] as { nodes: unknown[] };
    expect(topology.nodes).toHaveLength(20);
    expect(vehicleStep?.emit?.VehicleState).toHaveLength(50);
  });
});

describe("authored-data scope boundary", () => {
  it("scenario files are data only — no executable content", () => {
    for (const id of EXPECTED_IDS) {
      const lookup = getScenario(id);
      if (!lookup.ok) continue;
      const serialized = JSON.stringify(lookup.scenario);
      // A scenario says what values appear. It never says how to compute them.
      expect(serialized).not.toMatch(/function|=>|Math\.|eval\(/);
    }
  });

  it("supplied Task 2 values are present as literals", () => {
    const lookup = getScenario("fleet-density-high");
    expect(lookup.ok).toBe(true);
    if (!lookup.ok) return;
    const step = lookup.scenario.steps.find((s) => s.emit?.BottleneckState);
    const bottleneck = step?.emit?.BottleneckState?.[0] as { bottleneck_score: number };
    // Authored, not derived from lambda/mu or queue length.
    expect(typeof bottleneck.bottleneck_score).toBe("number");
  });
});
