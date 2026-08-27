/**
 * One alert row — M4, extended at M8.
 *
 * Severity, category and subject are all SUPPLIED for producer alerts, and FIXED per
 * category for the HMI's two data-path alerts. This component renders them and never
 * assigns, promotes or suppresses a severity.
 *
 * PROVENANCE IS VISIBLE (M8D-A). An alert the HMI originated is marked as such, in text,
 * so an operator can tell "Task 2 says this truck is unsafe" from "my own feed went
 * quiet". Collapsing the two would misattribute a data-path fault to the mine.
 *
 * No acknowledgement control exists here. FR-015 is deferred to M9 (M8D-C): its AC2 needs
 * a timestamped audit event and its AC3 needs role gating, and neither exists. An
 * acknowledgement that wrote no audit record would breach NFR-007 the moment it appeared.
 */

import type { Alert } from "../contracts/domain";
import type { FreshnessView } from "../state/freshness";
import { severityToken } from "../theme/statusTokens";
import { FreshnessIndicator, StatusBadge } from "./primitives";

export function AlertRow({ alert, freshness }: { alert: Alert; freshness: FreshnessView }) {
  const fromHmi = alert.origin === "HMI";

  return (
    <div className={`alert-row${fromHmi ? " hmi-origin" : ""}`}>
      <div>
        <StatusBadge token={severityToken(alert.severity)} />
      </div>
      <div>
        <div>{alert.message}</div>
        <div className="alert-subject">
          {alert.category} · {alert.subject.kind} {alert.subject.id}
          {alert.reasonCode ? ` · ${alert.reasonCode}` : ""}
          {fromHmi ? (
            <>
              {" · "}
              <span className="origin-hmi">ORIGIN HMI — DATA PATH</span>
            </>
          ) : (
            " · ORIGIN TASK2 — SUPPLIED"
          )}
        </div>
        {alert.acknowledged !== null ? (
          <div className="faint">
            acknowledged by {alert.acknowledged.by} at {alert.acknowledged.at}
          </div>
        ) : null}
      </div>
      <div>
        <FreshnessIndicator view={freshness} />
        {alert.acknowledgeable ? null : <div className="faint">not acknowledgeable</div>}
      </div>
    </div>
  );
}
