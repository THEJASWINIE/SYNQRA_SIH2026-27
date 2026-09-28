/**
 * Dedicated alert list — M8. FR-014.
 *
 * FR-014 places alerts on "S1 (top alerts) plus a dedicated alert list". S1 keeps the
 * prioritized summary; this is the full list, grouped by provenance.
 *
 * ==========================================================================
 *  EVERY PRODUCER ALERT IS SUPPLIED. THE HMI ORIGINATES EXACTLY TWO.
 *
 *  UNSAFE_SPEED, UNSAFE_HEADWAY, BOTTLENECK_RISK and SLOT_CONFLICT arrive
 *  from Task 2 and are rendered verbatim. COMM_LOSS and STALE_DATA are the
 *  HMI's own data-path alerts (M8D-A) and are marked as such.
 *
 *  No severity is assigned, promoted or computed. No risk is scored. No
 *  operational alert is fabricated. Ordering is the existing display sort.
 *
 *  NO ACKNOWLEDGEMENT CONTROL. FR-015 is deferred to M9 (M8D-C). The screen
 *  is read-only by construction: no form, no submit path, no button.
 * ==========================================================================
 */

import { AlertRow } from "../components/AlertRow";
import { EmptyState, Panel, StatusBadge } from "../components/primitives";
import { ALERT_CATEGORIES } from "../contracts/enums";
import { assessStale, mergedAlerts, STALE_ALERTING_INACTIVE_TEXT } from "../state/alerts";
import { viewFreshness } from "../state/freshness";
import { displayedModeFor, MODE_SOURCE_TEXT } from "../state/systemMode";
import { useAppState, useFreshnessConfig, useNowMs } from "../state/useAppState";
import { providerStatusToken, severityToken, systemModeToken } from "../theme/statusTokens";

export function AlertList() {
  const state = useAppState();
  const config = useFreshnessConfig();
  const nowMs = useNowMs();

  const merged = mergedAlerts(state, config, nowMs);
  const stale = assessStale(state, config, nowMs);
  const mode = displayedModeFor(state);

  /**
   * `rankAlerts` already excludes inactive alerts, so this list is the active set. A
   * history of cleared alerts belongs to the M9 event timeline, not here — retaining
   * resolved alerts on a live list would compete for attention with current ones.
   */
  const active = merged.all;
  const critical = active.filter((a) => a.severity === "CRITICAL");

  const fresh = (timestamp: string | null | undefined) => viewFreshness(timestamp, config, nowMs);

  return (
    <>
      {/* System mode, repeated here because an alert list without the mode is half a
          picture. Same derivation the shell uses — one source, no drift. */}
      <Panel title="System mode" note="FR-016 · supplied, with the FR-016 AC3 floor">
        <div className="mode-row">
          {mode.mode === null ? (
            <span className="dim">NO SYSTEM MODE SUPPLIED</span>
          ) : (
            <StatusBadge token={systemModeToken(mode.mode)} />
          )}
          <span className="faint">{MODE_SOURCE_TEXT[mode.source]}</span>
          <StatusBadge token={providerStatusToken(state.connection.status)} />
        </div>
        {mode.flooredByFeedLoss ? (
          <p className="faint">
            The data feed is lost, so the displayed mode is raised to DEGRADED (FR-016 AC3, OPS-003,
            NFR-012). Supplied mode was <strong>{mode.suppliedMode ?? "not supplied"}</strong> and
            is unchanged in state.
          </p>
        ) : null}
      </Panel>

      <Panel
        title="Active alerts"
        note={`FR-014 · ${critical.length} critical of ${active.length} active`}
      >
        {active.length === 0 ? (
          <EmptyState
            headline="NO ACTIVE ALERTS"
            detail="No supplied alert is active and no HMI data-path condition is present."
          />
        ) : (
          active.map((alert) => (
            <AlertRow key={alert.alertId} alert={alert} freshness={fresh(alert.timestamp)} />
          ))
        )}
      </Panel>

      <Panel title="Alert provenance and coverage" note="FR-014 AC1 · M8D-A">
        <dl className="fields">
          <div className="field">
            <dt>Supplied by Task 2</dt>
            <dd>{merged.supplied.length}</dd>
            <div className="faint">rendered verbatim; never re-severitied</div>
          </div>
          <div className="field">
            <dt>Originated by the HMI</dt>
            <dd>{merged.derived.length}</dd>
            <div className="faint">COMM_LOSS and STALE_DATA only — data-path conditions</div>
          </div>
          <div className="field">
            <dt>Stale alerting</dt>
            <dd>{merged.staleAlertingActive ? "ACTIVE" : "INACTIVE"}</dd>
            <div className="faint">
              {merged.staleAlertingActive
                ? `threshold configured; ${stale.staleLabels?.length ?? 0} value(s) beyond it`
                : "no freshness threshold configured"}
            </div>
          </div>
        </dl>

        {/* M8D-B — AMB-014 unresolved. Stated, never worked around. */}
        {merged.staleAlertingActive ? null : (
          <div className="hmi-banner" role="status">
            <div className="hmi-banner-title">▲ {STALE_ALERTING_INACTIVE_TEXT}</div>
            <p>
              Data age is still shown throughout the HMI, but staleness is not classified and no
              STALE_DATA alert can be raised. HMI-NFR-003 requires a configurable timeout and the
              specification states no value (AMB-014, unresolved). No default is assumed.
            </p>
          </div>
        )}

        <p className="faint">
          Categories in the contract: {ALERT_CATEGORIES.join(", ")}. The HMI originates only
          COMM_LOSS and STALE_DATA; the other four arrive from Task 2 and are never fabricated here.
        </p>
        <p className="unresolved">
          FR-015 acknowledgement is NOT implemented in this milestone. It requires a timestamped
          audit event (NFR-007) and role gating, neither of which exists yet — both arrive with M9.
          No acknowledgement control is offered.
        </p>
      </Panel>

      <Panel title="Severity key" note="NFR-008 · readable without colour">
        <div className="severity-key">
          {(["CRITICAL", "WARNING", "INFO"] as const).map((severity) => (
            <StatusBadge key={severity} token={severityToken(severity)} />
          ))}
        </div>
        <p className="faint">
          Every severity carries a label and a glyph as well as a colour. Ordering is by severity,
          then recency, then alert id — deterministic for any input order.
        </p>
      </Panel>
    </>
  );
}
