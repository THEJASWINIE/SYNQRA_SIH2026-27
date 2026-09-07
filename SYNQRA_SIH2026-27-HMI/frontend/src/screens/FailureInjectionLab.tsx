/**
 * Phase 10 — Failure Injection / Demo Lab.
 *
 * A SIMULATION / TEST ONLY panel that demonstrates SYNQRA's resilience and
 * validation behaviour by triggering failure scenarios through existing
 * validated API pathways.
 *
 * ARCHITECTURAL BOUNDARIES:
 *   - No new backend endpoints.
 *   - No new WebSocket transports.
 *   - No new command transports.
 *   - Never uses POST /api/hardware/telemetry.
 *   - Never directly mutates Twin, cache, or authoritative HMI state.
 *   - All injections carry SIMULATION provenance.
 *   - Screen calls no fetch directly; transport is owned by demoLabClient.
 */

import { useState, useCallback, useRef } from "react";
import { Panel, EmptyState } from "../components/primitives";
import {
  SCENARIOS,
  createScenarioRunners,
  type ScenarioStatus,
  type ScenarioResult,
  type LogEntry,
} from "../api/demoLabClient";

const MAX_LOG_ENTRIES = 50;

export function FailureInjectionLab() {
  const [results, setResults] = useState<Record<string, ScenarioResult>>({});
  const [running, setRunning] = useState<Record<string, boolean>>({});
  const [log, setLog] = useState<LogEntry[]>([]);
  const [runningAll, setRunningAll] = useState(false);
  const runnersRef = useRef(createScenarioRunners());

  const addLog = useCallback((entry: LogEntry) => {
    setLog((prev) => [entry, ...prev].slice(0, MAX_LOG_ENTRIES));
  }, []);

  const runScenario = useCallback(
    async (id: string) => {
      const runner = runnersRef.current[id];
      if (!runner) {
        // Scenario 1 is MANUAL
        setResults((prev) => ({
          ...prev,
          [id]: {
            status: "MANUAL" as ScenarioStatus,
            expected: "ONLINE → STALE → ONLINE",
            observed: "Requires external producer control",
            evidence:
              "Stop run_live_demo.py → wait ~4s → observe STALE via /api/vehicles → " +
              "restart run_live_demo.py → observe ONLINE",
          },
        }));
        addLog({
          timestamp: new Date().toISOString().slice(11, 23),
          scenario: id,
          request: "MANUAL — requires operator action",
          response: "N/A",
          result: "MANUAL",
        });
        return;
      }

      setRunning((prev) => ({ ...prev, [id]: true }));
      try {
        const result = await runner();
        setResults((prev) => ({ ...prev, [id]: result }));
        addLog({
          timestamp: new Date().toISOString().slice(11, 23),
          scenario: id,
          request: SCENARIOS.find((s) => s.id === id)?.title ?? id,
          response: result.observed,
          result: result.status,
        });
      } catch (error) {
        const msg = error instanceof Error ? error.message : "Unknown error";
        setResults((prev) => ({
          ...prev,
          [id]: {
            status: "FAIL",
            expected: "Scenario should complete",
            observed: `Error: ${msg}`,
            evidence: msg,
          },
        }));
        addLog({
          timestamp: new Date().toISOString().slice(11, 23),
          scenario: id,
          request: SCENARIOS.find((s) => s.id === id)?.title ?? id,
          response: `ERROR: ${msg}`,
          result: "FAIL",
        });
      } finally {
        setRunning((prev) => ({ ...prev, [id]: false }));
      }
    },
    [addLog],
  );

  const runAll = useCallback(async () => {
    setRunningAll(true);
    for (const scenario of SCENARIOS) {
      await runScenario(scenario.id);
    }
    setRunningAll(false);
  }, [runScenario]);

  const resetDemo = useCallback(() => {
    setResults({});
    setRunning({});
    setLog([]);
  }, []);

  // Aggregate counts
  const passCount = Object.values(results).filter((r) => r.status === "PASS").length;
  const failCount = Object.values(results).filter((r) => r.status === "FAIL").length;
  const manualCount = Object.values(results).filter((r) => r.status === "MANUAL").length;
  const totalRun = Object.keys(results).length;

  return (
    <section className="hmi-screen" aria-label="Failure Injection / Demo Lab">
      {/* ——— PROMINENT BANNER ——— */}
      <div className="demo-lab-banner" role="alert">
        <div className="demo-lab-banner-title">⚠ SIMULATION / TEST ONLY — NOT A PRODUCTION CONTROL</div>
        <p>No physical vehicle control is performed by this panel.</p>
      </div>

      <Panel title="Failure Injection / Demo Lab" note="Phase 10">
        {/* ——— ACTIONS ——— */}
        <div className="demo-lab-actions">
          <button
            type="button"
            className="demo-lab-btn demo-lab-btn-primary"
            onClick={runAll}
            disabled={runningAll}
          >
            {runningAll ? "Running…" : "▶ Run All"}
          </button>
          <button
            type="button"
            className="demo-lab-btn"
            onClick={resetDemo}
            disabled={runningAll}
          >
            ↻ Reset Demo
          </button>
          {totalRun > 0 && (
            <span className="demo-lab-aggregate">
              {passCount > 0 && <span className="demo-lab-status-pass">✓ {passCount} PASS</span>}
              {failCount > 0 && <span className="demo-lab-status-fail">✗ {failCount} FAIL</span>}
              {manualCount > 0 && <span className="demo-lab-status-manual">⊘ {manualCount} MANUAL</span>}
            </span>
          )}
        </div>

        {/* ——— SCENARIO CARDS ——— */}
        <div className="demo-lab-grid">
          {SCENARIOS.map((scenario) => {
            const result = results[scenario.id];
            const isRunning = running[scenario.id] ?? false;
            const status: ScenarioStatus = isRunning ? "RUNNING" : (result?.status ?? "IDLE");

            return (
              <div key={scenario.id} className="demo-lab-card" data-status={status}>
                <div className="demo-lab-card-head">
                  <h3>{scenario.title}</h3>
                  <span className={`demo-lab-status demo-lab-status-${status.toLowerCase()}`}>
                    {status}
                  </span>
                </div>
                <p className="demo-lab-card-desc">{scenario.description}</p>

                <button
                  type="button"
                  className="demo-lab-btn demo-lab-btn-inject"
                  onClick={() => runScenario(scenario.id)}
                  disabled={isRunning || runningAll}
                >
                  {isRunning ? "Running…" : "Inject"}
                </button>

                {result && (
                  <div className="demo-lab-evidence">
                    <dl>
                      <dt>Expected</dt>
                      <dd>{result.expected}</dd>
                      <dt>Observed</dt>
                      <dd>{result.observed}</dd>
                      <dt>Evidence</dt>
                      <dd>{result.evidence}</dd>
                    </dl>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </Panel>

      {/* ——— EVENT LOG ——— */}
      <Panel title="Injection Event Log" note={`${log.length} entries (max ${MAX_LOG_ENTRIES})`}>
        {log.length === 0 ? (
          <EmptyState headline="NO INJECTIONS YET" detail="Run a scenario to see results here." />
        ) : (
          <table className="demo-lab-log">
            <thead>
              <tr>
                <th>Time</th>
                <th>Scenario</th>
                <th>Request</th>
                <th>Response</th>
                <th>Result</th>
              </tr>
            </thead>
            <tbody>
              {log.map((entry, i) => (
                <tr key={`${entry.timestamp}-${i}`}>
                  <td className="mono">{entry.timestamp}</td>
                  <td>{entry.scenario}</td>
                  <td>{entry.request}</td>
                  <td>{entry.response}</td>
                  <td>
                    <span className={`demo-lab-status demo-lab-status-${entry.result.toLowerCase()}`}>
                      {entry.result}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Panel>
    </section>
  );
}
