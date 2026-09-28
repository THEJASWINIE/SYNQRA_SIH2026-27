/**
 * S7 System Health (formerly S6 Diagnostics) — M10 + Phase 5. FR-013, S6-a, NFR-003.
 *
 * Phase 5 added the observability-backed health sections at the top. They read
 * `AppState.observability`, which ProviderHost populates from GET /api/observability.
 * THIS SCREEN ISSUES NO OBSERVABILITY REQUEST OF ITS OWN and starts no polling loop.
 * The `/api/health` liveness check below is a DIFFERENT question and is preserved.
 *
 * ==========================================================================
 *  THE DATA-PATH TRUTH SCREEN. NOTHING OPERATIONAL IS COMPUTED HERE.
 *
 *  No v_safe, no h_safe, no queue, no bottleneck, no dispatch, no ETA, no
 *  route, no risk, no prediction. The only derivations are the two already on
 *  the closed list: data age from a supplied timestamp, and quality against a
 *  CONFIGURED threshold.
 *
 *  M10D-A — message counts are SUPPLIED on `Health.messagesReceived` and
 *  `.messagesDropped`. The HMI keeps no counter of its own, and an absent
 *  counter renders UNAVAILABLE, never 0.
 *
 *  TWO AGES, NEVER CONFLATED. `Health.ageMs` is supplied by the producer.
 *  The age beside a freshness marker is derived by Task 1 from a timestamp.
 *  The contract calls these out as distinct, so this screen labels them
 *  distinctly.
 *
 *  TWO FAILURE DOMAINS, NEVER MERGED. Backend health (`GET /api/health`,
 *  M1) says whether the HMI's own service is reachable. Provider status says
 *  whether operational data is arriving. The backend can be up while the feed
 *  is silent, and an operator needs to know which failed.
 *
 *  NO OPERATIONAL CONTROL. No acknowledge, no command, no override, no
 *  actuation, no form, no input. The validation panel is read-only (M10D-B):
 *  no retry, no reset, no re-injection.
 * ==========================================================================
 */

import { useCallback, useEffect, useState } from "react";
import { API_BASE_URL, fetchHealth, type HealthResult } from "../api/healthClient";
import {
  EmptyState,
  FreshnessIndicator,
  MetricCard,
  Panel,
  StatusBadge,
} from "../components/primitives";
import type { Health } from "../contracts/domain";
import { LINK_KINDS } from "../contracts/enums";
import { fmt } from "../state/derive";
import { freshnessOverview } from "../state/diagnostics";
import { formatAge, viewFreshness } from "../state/freshness";
import { useHmi } from "../state/ProviderHost";
import {
  deriveSystemHealth,
  formatAgeSeconds,
  formatCounter,
  HEALTH_GLYPH,
  OBSERVABILITY_STATUS_DETAIL,
  OBSERVABILITY_STATUS_TEXT,
  UNAVAILABLE_TEXT,
} from "../state/systemHealth";
import { displayedModeFor, MODE_SOURCE_TEXT } from "../state/systemMode";
import { useAppState, useFreshnessConfig, useNowMs } from "../state/useAppState";
import { providerStatusToken, systemModeToken } from "../theme/statusTokens";

/** Enum token to readable text, one-to-one. Adds no meaning the data layer did not send. */
function readable(token: string): string {
  return token.replace(/_/g, " ");
}

const UNAVAILABLE = "UNAVAILABLE";

/**
 * A supplied counter. Absent renders UNAVAILABLE, never 0 (M10D-A) — a zero is a value,
 * an absent counter is not, and showing one as the other would report a link as having
 * dropped nothing when nothing is known.
 */
function Counter({ value }: { value: number | null }) {
  return value === null ? (
    <span className="dim">{UNAVAILABLE}</span>
  ) : (
    <span className="mono">{fmt(value, 0)}</span>
  );
}

function LinkRow({ link }: { link: Health }) {
  return (
    <tr>
      <td className="mono">{link.linkKind ?? <span className="dim">NOT SUPPLIED</span>}</td>
      <td className="mono">{link.componentId}</td>
      <td>{readable(link.state)}</td>
      <td>
        {link.latencyMs === null ? (
          <span className="dim">{UNAVAILABLE}</span>
        ) : (
          <span className="mono">
            {fmt(link.latencyMs, 0)}
            <span className="metric-unit">ms</span>
          </span>
        )}
      </td>
      {/* SUPPLIED age. Distinct from the Task 1 derived age in the freshness column. */}
      <td>
        {link.ageMs === null ? (
          <span className="dim">{UNAVAILABLE}</span>
        ) : (
          <span className="mono">
            {fmt(link.ageMs, 0)}
            <span className="metric-unit">ms</span>
          </span>
        )}
      </td>
      <td>
        <Counter value={link.messagesReceived} />
      </td>
      <td>
        <Counter value={link.messagesDropped} />
      </td>
      <td className="mono">{link.errorCode ?? <span className="dim">none supplied</span>}</td>
    </tr>
  );
}

export function Diagnostics() {
  const state = useAppState();
  const config = useFreshnessConfig();
  const nowMs = useNowMs();
  const { validationFailures, freshnessReason } = useHmi();

  // -- backend health: the HMI's own service, a separate failure domain -----
  const [backend, setBackend] = useState<HealthResult | null>(null);
  const [checking, setChecking] = useState(true);

  const check = useCallback(async (signal?: AbortSignal) => {
    setChecking(true);
    const outcome = await fetchHealth(signal);
    if (signal?.aborted) return;
    setBackend(outcome);
    setChecking(false);
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    void check(controller.signal);
    return () => controller.abort();
  }, [check]);

  const links = state.health?.components ?? [];
  const overview = freshnessOverview(state, config, nowMs);
  const mode = displayedModeFor(state);
  const suppliedKinds = new Set(links.map((l) => l.linkKind).filter(Boolean));

  const observability = state.observability;
  const health = deriveSystemHealth(observability);
  const snapshot = observability.data;
  const stale = observability.status === "STALE";

  return (
    <>
      {/* 0 — SYSTEM HEALTH BANNER. Compact, scannable, never an invented aggregate. */}
      <Panel title="System health" note="GET /api/observability · via shared state">
        <dl className="fields">
          {health.map((line) => (
            <div className="field" key={line.label}>
              <dt>{line.label}</dt>
              <dd>
                <span aria-hidden="true">{HEALTH_GLYPH[line.state]}</span> {line.value}
              </dd>
              {line.detail ? <div className="faint">{line.detail}</div> : null}
            </div>
          ))}
        </dl>
      </Panel>

      {/* OBSERVABILITY LIFECYCLE. Distinct from service liveness further down. */}
      <Panel title="Observability" note="control-plane snapshot state">
        <dl className="fields">
          <div className="field">
            <dt>Snapshot state</dt>
            <dd>
              {stale ? "⚠ " : observability.status === "ERROR" ? "✕ " : ""}
              {OBSERVABILITY_STATUS_TEXT[observability.status]}
            </dd>
            <div className="faint">{OBSERVABILITY_STATUS_DETAIL[observability.status]}</div>
          </div>
          <div className="field">
            <dt>Last successful update</dt>
            <dd>{observability.fetchedAt ?? UNAVAILABLE_TEXT}</dd>
            <div className="faint">HMI receipt time of the last successful fetch</div>
          </div>
          <div className="field">
            <dt>Backend snapshot time</dt>
            <dd>
              {snapshot?.timestamp === null || snapshot?.timestamp === undefined
                ? UNAVAILABLE_TEXT
                : new Date(snapshot.timestamp * 1000).toISOString()}
            </dd>
          </div>
          {observability.error ? (
            <div className="field">
              <dt>Last error</dt>
              <dd>{observability.error}</dd>
            </div>
          ) : null}
        </dl>
        {stale ? (
          <p className="faint">
            Showing the last known good counters. They are NOT current, and they are not zeroed.
          </p>
        ) : null}
      </Panel>

      {/* TELEMETRY INGESTION COUNTERS */}
      <Panel
        title="Telemetry ingestion"
        note={stale ? "LAST KNOWN VALUES — STALE" : "counters reported by the backend"}
      >
        {snapshot?.telemetryIngest ? (
          <div className="metrics">
            <MetricCard label="Accepted" value={formatCounter(snapshot.telemetryIngest.accepted)} />
            <MetricCard label="Invalid" value={formatCounter(snapshot.telemetryIngest.invalid)} />
            <MetricCard
              label="Duplicate"
              value={formatCounter(snapshot.telemetryIngest.duplicate)}
            />
            <MetricCard
              label="Out of order"
              value={formatCounter(snapshot.telemetryIngest.outOfOrder)}
            />
            <MetricCard
              label="Unknown vehicle"
              value={formatCounter(snapshot.telemetryIngest.unknownVehicle)}
            />
          </div>
        ) : (
          <EmptyState
            headline="TELEMETRY COUNTERS UNAVAILABLE"
            detail="The backend has not supplied telemetry ingestion counters. They are not shown as zero."
          />
        )}
      </Panel>

      {/* COMMAND GATEWAY COUNTERS. Metrics only, never command records. */}
      <Panel
        title="Command gateway"
        note={stale ? "LAST KNOWN VALUES — STALE" : "counters only — not command history"}
      >
        {snapshot?.commandGateway ? (
          <>
            <div className="metrics">
              <MetricCard
                label="Accepted"
                value={formatCounter(snapshot.commandGateway.accepted)}
              />
              <MetricCard
                label="Rejected"
                value={formatCounter(snapshot.commandGateway.rejected)}
              />
              <MetricCard label="Unsafe" value={formatCounter(snapshot.commandGateway.unsafe)} />
              <MetricCard
                label="Unknown vehicle"
                value={formatCounter(snapshot.commandGateway.unknownVehicle)}
              />
              <MetricCard
                label="Duplicate"
                value={formatCounter(snapshot.commandGateway.duplicate)}
              />
              <MetricCard label="Stale" value={formatCounter(snapshot.commandGateway.stale)} />
              <MetricCard label="Invalid" value={formatCounter(snapshot.commandGateway.invalid)} />
              <MetricCard label="Timeout" value={formatCounter(snapshot.commandGateway.timeout)} />
            </div>
            <p className="faint">
              A refusal is the gateway working, not a fault. Command records live on S4 Dispatch;
              these are counters.
            </p>
          </>
        ) : (
          <EmptyState
            headline="COMMAND GATEWAY COUNTERS UNAVAILABLE"
            detail="The backend has not supplied command gateway counters. They are not shown as zero."
          />
        )}
      </Panel>

      {/* HARDWARE. Derived only from the backend's own hardware fields. */}
      <Panel title="Hardware" note="never inferred from backend or Twin availability">
        {snapshot?.hardware ? (
          <dl className="fields">
            <div className="field">
              <dt>Hardware seen</dt>
              <dd>
                {snapshot.hardware.hardwareSeen === null
                  ? UNAVAILABLE_TEXT
                  : snapshot.hardware.hardwareSeen
                    ? "YES"
                    : "NO"}
              </dd>
              <div className="faint">A physical packet has arrived at some point</div>
            </div>
            <div className="field">
              <dt>Hardware connected</dt>
              <dd>
                {snapshot.hardware.hardwareConnected === null
                  ? UNAVAILABLE_TEXT
                  : snapshot.hardware.hardwareConnected
                    ? "YES"
                    : "NO"}
              </dd>
              <div className="faint">A physical packet has arrived recently</div>
            </div>
            <div className="field">
              <dt>Last physical packet age</dt>
              <dd>{formatAgeSeconds(snapshot.hardware.ageSeconds)}</dd>
            </div>
            <div className="field">
              <dt>Backend mode</dt>
              <dd>{snapshot.mode ?? UNAVAILABLE_TEXT}</dd>
              <div className="faint">
                MOCK means the telemetry ingress is SIMULATED. It is not a malfunction, and it is
                not a statement about hardware.
              </div>
            </div>
          </dl>
        ) : (
          <EmptyState
            headline="HARDWARE STATUS UNAVAILABLE"
            detail="The backend has not supplied hardware status. No hardware state is inferred from it being reachable."
          />
        )}
      </Panel>

      {/* FLEET SUMMARY. Concise; vehicle detail lives on S2. */}
      <Panel title="Fleet summary" note="freshness from the canonical vehicle state">
        <div className="metrics">
          <MetricCard
            label="Vehicles in Twin (reported)"
            value={formatCounter(snapshot?.twinVehicleCount)}
            footer="backend metric"
          />
          <MetricCard
            label="Vehicles in HMI state"
            value={String(Object.keys(state.vehicles).length)}
            footer="canonical Twin projection"
          />
          <MetricCard
            label="WebSocket clients"
            value={formatCounter(snapshot?.websocketClients)}
            footer="HMI clients, not vehicles"
          />
        </div>
        {Object.keys(state.vehicles).length === 0 ? (
          <EmptyState
            headline="NO VEHICLE STATE SUPPLIED"
            detail="The Twin projection has supplied no vehicle. A reported count is a metric, not vehicle state."
          />
        ) : (
          <dl className="fields">
            {Object.values(state.vehicles).map((vehicle) => (
              <div className="field" key={vehicle.vehicleId}>
                <dt>{vehicle.vehicleId}</dt>
                <dd>
                  <FreshnessIndicator view={viewFreshness(vehicle.timestamp, config, nowMs)} />
                </dd>
              </div>
            ))}
          </dl>
        )}
      </Panel>

      {/* 1 — GLOBAL OPERATIONAL STATE */}
      <Panel title="Operational state" note="FR-013 · FR-016 · supplied">
        <div className="metrics">
          <MetricCard
            label="System mode"
            value={mode.mode === null ? "NOT SUPPLIED" : systemModeToken(mode.mode).label}
            footer={MODE_SOURCE_TEXT[mode.source]}
          />
          <MetricCard
            label="Connectivity (supplied)"
            value={state.health?.connectivity ?? UNAVAILABLE}
            footer="reported by the producer"
          />
          <MetricCard
            label="Fleet count (supplied)"
            value={state.health === null ? UNAVAILABLE : fmt(state.health.fleetCount, 0)}
          />
          <MetricCard
            label="Entities held"
            value={fmt(overview.totalEntities, 0)}
            footer="across every message type"
          />
        </div>
        <div className="row-between">
          <span className="faint">
            Data connection — operational telemetry
            {state.connection.error ? ` · ${state.connection.error}` : ""}
          </span>
          <StatusBadge token={providerStatusToken(state.connection.status)} />
        </div>
      </Panel>

      {/* 2 — COMMUNICATION HEALTH (FR-013, S6-a) */}
      <Panel
        title="Communication health"
        note={`FR-013 · S6-a · ${links.length} supplied component(s)`}
      >
        {links.length === 0 ? (
          <EmptyState
            headline="NO LINK HEALTH SUPPLIED"
            detail="SystemHealth has supplied no component rows. Task 1 does not synthesise link health."
          />
        ) : (
          <table className="data-table" aria-label="Supplied communication health">
            <thead>
              <tr>
                <th>Link kind</th>
                <th>Component</th>
                <th>State</th>
                <th>Latency (supplied)</th>
                <th>Age (supplied)</th>
                <th>Msgs received</th>
                <th>Msgs dropped</th>
                <th>Error code</th>
              </tr>
            </thead>
            <tbody>
              {links.map((link) => (
                <LinkRow key={link.componentId} link={link} />
              ))}
            </tbody>
          </table>
        )}

        {/* FR-013 AC1 — all three kinds must be representable. Which are actually
            supplied right now is stated, rather than implied by absence. */}
        <div className="link-kinds">
          {LINK_KINDS.map((kind) => (
            <span key={kind} className="badge">
              {kind}
              {suppliedKinds.has(kind) ? " · SUPPLIED" : " · not in this scenario"}
            </span>
          ))}
        </div>
        <p className="faint">
          Latency and age in this table are SUPPLIED by the producer. They are not the age Task 1
          derives from a timestamp — that appears in the freshness overview below, and the two are
          deliberately kept apart.
        </p>
      </Panel>

      {/* 3 — FRESHNESS OVERVIEW (NFR-003) */}
      <Panel
        title="Data freshness by message type"
        note={
          overview.thresholdConfigured
            ? "NFR-003 · classified against the configured threshold"
            : "NFR-003 · age only — threshold not configured"
        }
      >
        <table className="data-table" aria-label="Freshness by message type">
          <thead>
            <tr>
              <th>Message type</th>
              <th>Held</th>
              <th>Oldest age (derived)</th>
              <th>Quality</th>
              <th>Current</th>
              <th>Stale</th>
              <th>Invalid</th>
            </tr>
          </thead>
          <tbody>
            {overview.rows.map((row) => (
              <tr key={row.messageType}>
                <td className="mono">{row.messageType}</td>
                <td className="mono">{row.count}</td>
                <td className="mono">
                  {row.count === 0 ? (
                    <span className="dim">—</span>
                  ) : (
                    (formatAge(row.oldestAgeMs) ?? <span className="dim">not assessable</span>)
                  )}
                </td>
                <td>
                  {row.count === 0 ? (
                    <span className="dim">—</span>
                  ) : row.oldest ? (
                    <FreshnessIndicator view={row.oldest} />
                  ) : null}
                </td>
                <td className="mono">
                  {row.qualities === null ? <span className="dim">n/e</span> : row.qualities.OK}
                </td>
                <td className="mono">
                  {row.qualities === null ? <span className="dim">n/e</span> : row.qualities.STALE}
                </td>
                <td className="mono">
                  {row.qualities === null ? (
                    <span className="dim">n/e</span>
                  ) : (
                    row.qualities.INVALID
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>

        {overview.thresholdConfigured ? null : (
          <div className="hmi-banner" role="status">
            <div className="hmi-banner-title">▲ FRESHNESS THRESHOLD NOT CONFIGURED</div>
            <p>
              Ages are shown and continue to advance. Stale classification is{" "}
              <strong>not evaluated</strong>, so the quality columns read <code>n/e</code> — not
              evaluated, which is a different statement from "all current". HMI-NFR-003 requires a
              configurable timeout and the specification states no value (AMB-014, unresolved). No
              default is assumed.
            </p>
            {freshnessReason ? <p className="faint">{freshnessReason}</p> : null}
          </div>
        )}
        <p className="faint">
          Age here is DERIVED by Task 1 from each datum's supplied timestamp. A malformed timestamp
          resolves to INVALID, never STALE. An absent datum is MISSING, never INVALID.
        </p>
      </Panel>

      {/* 4 — BACKEND HEALTH — a different failure domain from the feed above */}
      <Panel title="HMI backend health" note="M1 · separate failure domain">
        <div className="metrics">
          <MetricCard
            label="Reachability"
            value={
              checking
                ? "CHECKING"
                : backend?.kind === "ok"
                  ? "REACHABLE"
                  : backend?.kind === "error"
                    ? "UNREACHABLE"
                    : UNAVAILABLE
            }
            footer={API_BASE_URL}
          />
          <MetricCard
            label="Round-trip latency"
            value={backend?.kind === "ok" ? fmt(backend.latencyMs, 0) : UNAVAILABLE}
            {...(backend?.kind === "ok" ? { unit: "ms" } : {})}
            footer="measured by the HMI"
          />
          <MetricCard
            label="Service"
            value={backend?.kind === "ok" ? backend.health.service : UNAVAILABLE}
          />
          <MetricCard
            label="Version"
            value={backend?.kind === "ok" ? backend.health.version : UNAVAILABLE}
          />
          <MetricCard
            label="Milestone"
            value={backend?.kind === "ok" ? backend.health.milestone : UNAVAILABLE}
          />
          <MetricCard
            label="Backend timestamp"
            value={backend?.kind === "ok" ? backend.health.timestamp.slice(11, 23) : UNAVAILABLE}
            footer="UTC, as reported"
          />
        </div>

        {backend?.kind === "error" ? (
          <p className="unresolved" role="alert">
            Backend unreachable: {backend.message}. Operational telemetry above is unaffected by
            this — the two are separate failure domains, and a silent feed and an unreachable
            backend are different faults.
          </p>
        ) : null}
        <p className="faint">
          This reports the HMI's own service. It is not the operational data feed, and the two are
          never merged into one indicator.
        </p>
      </Panel>

      {/* 5 — VALIDATION DIAGNOSTICS (M10D-B) — read-only */}
      <Panel
        title="Validation failures"
        note={`M10D-B · read-only · ${validationFailures.length} recorded`}
      >
        {validationFailures.length === 0 ? (
          <EmptyState
            headline="NO VALIDATION FAILURES RECORDED"
            detail="Every payload the provider delivered passed the contract schema this session."
          />
        ) : (
          <table className="data-table" aria-label="Recorded validation failures">
            <thead>
              <tr>
                <th>Message type</th>
                <th>Received at</th>
                <th>Field</th>
                <th>Expected</th>
                <th>Received</th>
                <th>Detail</th>
              </tr>
            </thead>
            <tbody>
              {validationFailures.flatMap((failure, failureIndex) =>
                failure.issues.map((issue, issueIndex) => (
                  // biome-ignore lint/suspicious/noArrayIndexKey: composite key includes index for list stability when issues lack unique IDs
                  <tr key={`${failure.messageType}-${failureIndex}-${issue.path}-${issueIndex}`}>
                    <td className="mono">{failure.messageType}</td>
                    <td className="mono">{failure.receivedAt.slice(11, 23)}</td>
                    <td className="mono">{issue.path}</td>
                    <td className="mono">{issue.expected}</td>
                    <td className="mono">{issue.received}</td>
                    <td>{issue.message}</td>
                  </tr>
                )),
              )}
            </tbody>
          </table>
        )}
        <p className="faint">
          A payload that arrived and failed the schema is INVALID, never MISSING — collapsing the
          two would hide an integration fault behind what looks like a quiet link. This panel is
          read-only: it offers no retry, no reset and no re-injection, and the provider's behaviour
          is not altered to populate it.
        </p>
      </Panel>
    </>
  );
}
