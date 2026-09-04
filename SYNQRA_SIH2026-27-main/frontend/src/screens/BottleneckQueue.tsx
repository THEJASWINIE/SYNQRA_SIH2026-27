/**
 * S3 Bottleneck & Queue — M6.
 *
 * Satisfies HMI-FR-006 (bottleneck visualization), FR-007 (queue monitoring),
 * FR-008 (arrival-rate shaping).
 *
 * ==========================================================================
 *  EVERY VALUE ON THIS SCREEN IS SUPPLIED.
 *
 *  Nothing here computes bottleneck scores, queue evolution, queue predictions,
 *  arrival rates, service rates, utilization, criticality bands, metering
 *  decisions, hold/release decisions, queue limits, trend fitting, forecast
 *  generation, routes, trajectories, or any other Task 2 output.
 *
 *  The screen performs exactly the derivations on the closed list: data age,
 *  display ordering by supplied score (contract §12 item 6), and unit
 *  formatting. Ranking is a SORT of a SUPPLIED score, never a recomputation.
 *
 *  No control, no command, no acknowledgement, no actuation. The screen is
 *  read-only by construction — it renders no form and no submit path.
 * ==========================================================================
 */

import {
  EmptyState,
  FreshnessIndicator,
  MetricCard,
  Panel,
  StatusBadge,
} from "../components/primitives";
import type {
  ArrivalPlan,
  BottleneckState,
  QueueForecastPoint,
  QueueHistoryPoint,
} from "../contracts/domain";
import { fmt, rankBottlenecks } from "../state/derive";
import { viewFreshness } from "../state/freshness";
import { useAppState, useFreshnessConfig, useNowMs } from "../state/useAppState";
import { criticalityToken, providerStatusToken } from "../theme/statusTokens";

/** Enum token to readable text, one-to-one. Adds no meaning the data layer did not send. */
function readable(token: string): string {
  return token.replace(/_/g, " ");
}

const UNAVAILABLE = "UNAVAILABLE";

// ---------------------------------------------------------------------------
// FR-006 — Bottleneck ranking
// ---------------------------------------------------------------------------

function BottleneckRow({ b }: { b: BottleneckState }) {
  return (
    <tr>
      <td className="mono">{b.nodeId}</td>
      <td>
        <StatusBadge token={criticalityToken(b.criticality)} />
      </td>
      <td>{fmt(b.bottleneckScore, 2)}</td>
      <td>{fmt(b.utilization, 2)}</td>
      <td>
        {fmt(b.queue, 0)} / {fmt(b.queueMax, 0)}
      </td>
      <td>{b.lambdaVph === null ? UNAVAILABLE : `${fmt(b.lambdaVph, 0)} vph`}</td>
      <td>{b.muVph === null ? UNAVAILABLE : `${fmt(b.muVph, 0)} vph`}</td>
    </tr>
  );
}

// ---------------------------------------------------------------------------
// FR-007 — Queue detail panels
// ---------------------------------------------------------------------------

function QueueHistoryTable({ history }: { history: QueueHistoryPoint[] }) {
  if (history.length === 0) {
    return <p className="faint">No history points supplied.</p>;
  }
  return (
    <table className="data-table" aria-label="Measured queue history">
      <thead>
        <tr>
          <th>Time</th>
          <th>Queue</th>
        </tr>
      </thead>
      <tbody>
        {history.map((point) => (
          <tr key={point.at}>
            <td className="mono">{point.at}</td>
            <td>{fmt(point.queue, 0)}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

function QueueForecastTable({ forecast }: { forecast: QueueForecastPoint[] }) {
  if (forecast.length === 0) {
    return <p className="faint">No forecast points supplied.</p>;
  }
  return (
    <table className="data-table" aria-label="Supplied queue forecast">
      <thead>
        <tr>
          <th>Time</th>
          <th>Queue</th>
          <th>σ</th>
        </tr>
      </thead>
      <tbody>
        {forecast.map((point) => (
          <tr key={point.at}>
            <td className="mono">{point.at}</td>
            <td>{fmt(point.queue, 0)}</td>
            <td>{point.sigma === null ? "—" : fmt(point.sigma, 1)}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

function QueueDetail({ b }: { b: BottleneckState }) {
  return (
    <div>
      <h3 className="mono">{b.nodeId}</h3>
      <div className="metrics">
        <MetricCard
          label="Queue"
          value={fmt(b.queue, 0)}
          {...(b.queueMax !== null ? { unit: `/ ${fmt(b.queueMax, 0)}` } : {})}
          footer="current / max"
        />
        <MetricCard
          label="Arrival rate (λ)"
          value={b.lambdaVph === null ? UNAVAILABLE : fmt(b.lambdaVph, 0)}
          {...(b.lambdaVph !== null ? { unit: "vph" } : {})}
          footer="supplied"
        />
        <MetricCard
          label="Service rate (μ)"
          value={b.muVph === null ? UNAVAILABLE : fmt(b.muVph, 0)}
          {...(b.muVph !== null ? { unit: "vph" } : {})}
          footer="supplied"
        />
        <MetricCard label="Utilization" value={fmt(b.utilization, 2)} footer="supplied" />
      </div>

      <div style={{ marginTop: "1rem" }}>
        <h4>Measured history</h4>
        {b.queueHistory !== null ? (
          <QueueHistoryTable history={b.queueHistory} />
        ) : (
          <p className="faint">QUEUE HISTORY NOT SUPPLIED</p>
        )}
      </div>

      <div style={{ marginTop: "1rem" }}>
        <h4>Forecast (supplied by Task 2)</h4>
        {b.queueForecast !== null ? (
          <QueueForecastTable forecast={b.queueForecast} />
        ) : (
          <p className="faint">QUEUE FORECAST NOT SUPPLIED</p>
        )}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// FR-008 — Arrival shaping
// ---------------------------------------------------------------------------

function ArrivalDetail({ plan }: { plan: ArrivalPlan }) {
  return (
    <div>
      <h3 className="mono">{plan.nodeId}</h3>
      <div className="faint" style={{ marginBottom: "0.5rem" }}>
        Issued at: <span className="mono">{plan.issuedAt}</span>
      </div>

      <div className="grid-2">
        <div>
          <h4>Planned arrivals</h4>
          {plan.planned.length === 0 ? (
            <p className="faint">No planned arrival data supplied.</p>
          ) : (
            <table className="data-table" aria-label="Planned arrivals">
              <thead>
                <tr>
                  <th>Time</th>
                  <th>Count</th>
                </tr>
              </thead>
              <tbody>
                {plan.planned.map((point) => (
                  <tr key={point.at}>
                    <td className="mono">{point.at}</td>
                    <td>{fmt(point.count, 0)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
        <div>
          <h4>Actual arrivals</h4>
          {plan.actual.length === 0 ? (
            <p className="faint">No actual arrival data supplied.</p>
          ) : (
            <table className="data-table" aria-label="Actual arrivals">
              <thead>
                <tr>
                  <th>Time</th>
                  <th>Count</th>
                </tr>
              </thead>
              <tbody>
                {plan.actual.map((point) => (
                  <tr key={point.at}>
                    <td className="mono">{point.at}</td>
                    <td>{fmt(point.count, 0)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>

      <div style={{ marginTop: "1rem" }}>
        <h4>Active metering / hold decisions</h4>
        {plan.activeDecisions.length === 0 ? (
          <p>NO ACTIVE METERING</p>
        ) : (
          <table className="data-table" aria-label="Active metering decisions">
            <thead>
              <tr>
                <th>Vehicle</th>
                <th>Decision</th>
                <th>Until</th>
                <th>Reason code</th>
              </tr>
            </thead>
            <tbody>
              {plan.activeDecisions.map((d) => (
                <tr key={`${d.vehicleId}-${d.decision}`}>
                  <td className="mono">{d.vehicleId}</td>
                  <td>{readable(d.decision)}</td>
                  <td className="mono">{d.until ?? "—"}</td>
                  <td>{d.reasonCode}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// S3 screen
// ---------------------------------------------------------------------------

export function BottleneckQueue() {
  const state = useAppState();
  const config = useFreshnessConfig();
  const nowMs = useNowMs();

  const ranked = rankBottlenecks(state.bottlenecks);
  const arrivals = Object.values(state.arrivals);

  const fresh = (timestamp: string | null | undefined) => viewFreshness(timestamp, config, nowMs);

  return (
    <>
      {/* FR-006 — Bottleneck ranking */}
      <Panel title="Bottleneck ranking" note="sorted by supplied score, descending">
        {ranked.length === 0 ? (
          <EmptyState
            headline="NO BOTTLENECK DATA SUPPLIED"
            detail="The data layer has supplied no bottleneck state. Task 1 does not compute bottleneck scores."
          />
        ) : (
          <table className="data-table" aria-label="Bottleneck ranking">
            <thead>
              <tr>
                <th>Node</th>
                <th>Criticality</th>
                <th>Score</th>
                <th>Utilization</th>
                <th>Queue</th>
                <th>λ (arrival)</th>
                <th>μ (service)</th>
              </tr>
            </thead>
            <tbody>
              {ranked.map((b) => (
                <BottleneckRow key={b.nodeId} b={b} />
              ))}
            </tbody>
          </table>
        )}
        {ranked.length > 0 && (
          <div className="faint" style={{ marginTop: "0.5rem" }}>
            {ranked.length} node(s). Ranking is a sort of a supplied score; no scoring formula
            exists in this repository.
          </div>
        )}
      </Panel>

      {/* FR-007 — Queue monitoring (per-node detail) */}
      <Panel title="Queue detail" note="per-node queue, rates and trend">
        {ranked.length === 0 ? (
          <EmptyState
            headline="NO QUEUE DATA SUPPLIED"
            detail="Queue data arrives with bottleneck state. None has been supplied."
          />
        ) : (
          ranked.map((b) => (
            <div key={b.nodeId} style={{ marginBottom: "1.5rem" }}>
              <QueueDetail b={b} />
              <div style={{ marginTop: "0.5rem" }}>
                <FreshnessIndicator view={fresh(b.timestamp)} />
              </div>
            </div>
          ))
        )}
      </Panel>

      {/* FR-008 — Arrival shaping */}
      <Panel title="Arrival shaping" note="planned vs actual, metering decisions">
        {arrivals.length === 0 ? (
          <EmptyState
            headline="ARRIVAL DATA UNAVAILABLE"
            detail="No arrival plan has been supplied. Task 1 does not generate arrival plans or metering decisions (AMB-002)."
          />
        ) : (
          arrivals.map((plan) => (
            <div key={plan.nodeId} style={{ marginBottom: "1.5rem" }}>
              <ArrivalDetail plan={plan} />
              <div style={{ marginTop: "0.5rem" }}>
                <FreshnessIndicator view={fresh(plan.issuedAt)} />
              </div>
            </div>
          ))
        )}
      </Panel>

      {/* Provenance */}
      <Panel title="Connection" note="data source">
        <div className="metrics">
          <MetricCard
            label="Status"
            value={state.connection.status}
            footer={<StatusBadge token={providerStatusToken(state.connection.status)} />}
          />
          <MetricCard
            label="Provider"
            value={state.connection.provider}
            footer={state.connection.scenarioName ?? "none"}
          />
        </div>
        {state.connection.error ? (
          <div className="faint" style={{ marginTop: "0.5rem" }}>
            {state.connection.error}
          </div>
        ) : null}
      </Panel>
    </>
  );
}
