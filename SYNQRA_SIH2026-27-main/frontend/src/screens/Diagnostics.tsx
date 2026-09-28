/**
 * S6 Diagnostics — M10. FR-013, S6-a, NFR-003.
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
import { formatAge } from "../state/freshness";
import { useHmi } from "../state/ProviderHost";
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

  return (
    <>
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
