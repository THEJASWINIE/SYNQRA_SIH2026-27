/**
 * Scenario registry — M3.
 *
 * Scenario files are imported statically so Vite bundles them and the registry cannot
 * drift from what is on disk. Every file is validated at module load: a malformed
 * scenario must fail here, before a provider can emit anything from it.
 *
 * Descriptors are DERIVED from the scenario files. There is deliberately no hand-written
 * descriptor list to fall out of step with them.
 *
 * FR-019 note (MID-D): this module is the headless half of scenario controls. The React
 * picker is M4. Nothing here renders.
 */

import { parseScenario } from "./scenarioSchema";
import communicationLoss from "./scenarios/communication-loss.json";
import disconnectReconnect from "./scenarios/disconnect-reconnect.json";
import envelopeViolation from "./scenarios/envelope-violation.json";
import fleetDensityHigh from "./scenarios/fleet-density-high.json";
import fogRollingIn from "./scenarios/fog-rolling-in.json";
import frictionDegradation from "./scenarios/friction-degradation.json";
import nominal from "./scenarios/nominal.json";
import scale from "./scenarios/scale.json";
import slotConflict from "./scenarios/slot-conflict.json";
import staleFeed from "./scenarios/stale-feed.json";
import steepGrade from "./scenarios/steep-grade.json";
import type { Scenario, ScenarioDescriptor, ScenarioLookup } from "./scenarioTypes";

/** Raw imports, before validation. */
const RAW_SCENARIOS: readonly unknown[] = [
  nominal,
  fogRollingIn,
  frictionDegradation,
  steepGrade,
  fleetDensityHigh,
  communicationLoss,
  staleFeed,
  disconnectReconnect,
  slotConflict,
  envelopeViolation,
  scale,
];

/**
 * Validate every scenario at load.
 *
 * A malformed scenario file is a build-time defect, not a runtime surprise, so this
 * throws rather than degrading. It runs once, at module initialization, before any
 * provider exists — which is why `connect()` can rely on a resolved scenario being sound.
 */
function loadAll(): Map<string, Scenario> {
  const map = new Map<string, Scenario>();

  for (const raw of RAW_SCENARIOS) {
    const parsed = parseScenario(raw);
    if (!parsed.ok) {
      const id =
        typeof raw === "object" && raw !== null && "id" in raw
          ? String((raw as { id: unknown }).id)
          : "(unknown)";
      throw new Error(`Invalid scenario "${id}": ${parsed.issues.join("; ")}`);
    }
    const scenario = parsed.value as Scenario;
    if (map.has(scenario.id)) {
      throw new Error(`Duplicate scenario id "${scenario.id}"`);
    }
    map.set(scenario.id, scenario);
  }

  return map;
}

const SCENARIOS = loadAll();

function describe(scenario: Scenario): ScenarioDescriptor {
  const lastStep = scenario.steps[scenario.steps.length - 1];
  return {
    id: scenario.id,
    name: scenario.name,
    description: scenario.description,
    family: scenario.family,
    stepCount: scenario.steps.length,
    durationMs: lastStep ? lastStep.atMs : 0,
  };
}

/** FR-019 data. Ordered by registration, so listings are stable. */
export function listScenarios(): ScenarioDescriptor[] {
  return [...SCENARIOS.values()].map(describe);
}

/** An unknown id is a normal outcome with a typed result, not an exception. */
export function getScenario(id: string): ScenarioLookup {
  const scenario = SCENARIOS.get(id);
  if (!scenario) {
    return {
      ok: false,
      error: { kind: "SCENARIO_NOT_FOUND", id, available: [...SCENARIOS.keys()] },
    };
  }
  return { ok: true, scenario };
}

export function scenarioIds(): string[] {
  return [...SCENARIOS.keys()];
}
