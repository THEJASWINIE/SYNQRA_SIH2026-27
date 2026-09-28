/**
 * Scenario picker — M4. FR-019, MID-D.
 *
 * A DEVELOPER / TESTER capability, labelled as such. Not an operator control.
 *
 * It consumes scenario descriptors through the application boundary — it never reads
 * scenario JSON, never imports the registry directly, and never computes scenario data.
 * Selecting a scenario routes through `ProviderHost`, which performs the full restart:
 * disconnect → reset → load → connect. One state system, not two.
 */

import { useHmi } from "../state/ProviderHost";

export function ScenarioPicker() {
  const { scenarios, activeScenarioId, selectScenario } = useHmi();

  return (
    <div className="scenario-list">
      {scenarios.map((scenario) => {
        const active = scenario.id === activeScenarioId;
        return (
          <button
            key={scenario.id}
            type="button"
            className="scenario-item"
            aria-pressed={active}
            onClick={() => selectScenario(scenario.id)}
          >
            <span className="scenario-name">
              {active ? "▶ " : ""}
              {scenario.name}
              {active ? " — ACTIVE" : ""}
            </span>
            <span className="scenario-meta">
              {" "}
              · family {scenario.family} · {scenario.stepCount} steps ·{" "}
              {(scenario.durationMs / 1000).toFixed(0)} s
            </span>
            <div className="scenario-desc">{scenario.description}</div>
          </button>
        );
      })}
    </div>
  );
}
