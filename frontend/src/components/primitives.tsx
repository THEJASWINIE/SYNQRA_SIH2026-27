/**
 * Reusable S1 primitives — M4.
 *
 * Small, one responsibility each, no transport or provider logic. Every one that shows a
 * state renders a label and a glyph alongside any colour, so the display survives
 * greyscale (NFR-008).
 *
 * Nothing here computes an operational value. These components render what they are
 * given.
 */

import type { ReactNode } from "react";
import { type FreshnessView, formatAge, freshnessGlyph, freshnessLabel } from "../state/freshness";
import type { StatusToken } from "../theme/statusTokens";

// ---------------------------------------------------------------------------

export function Panel({
  title,
  note,
  children,
}: {
  title: string;
  note?: ReactNode;
  children: ReactNode;
}) {
  return (
    <section className="panel" aria-label={title}>
      <div className="panel-head">
        <h2>{title}</h2>
        {note ? <span className="panel-note">{note}</span> : null}
      </div>
      <div className="panel-body">{children}</div>
    </section>
  );
}

// ---------------------------------------------------------------------------

/**
 * A status chip.
 *
 * The glyph is `aria-hidden` and the label carries the meaning, so the state is readable
 * by a screen reader, in greyscale, and on a washed-out control-room monitor alike.
 */
export function StatusBadge({ token, prefix }: { token: StatusToken; prefix?: string }) {
  return (
    <span className="badge" style={{ color: token.colour }}>
      <span aria-hidden="true">{token.glyph}</span>
      <span>
        {prefix ? `${prefix} ` : ""}
        {token.label}
      </span>
    </span>
  );
}

// ---------------------------------------------------------------------------

/**
 * Empty states are real product states, not gaps.
 *
 * `NO ACTIVE ALERTS` is an answer. A blank panel is not — an operator cannot tell it
 * apart from a panel that failed to load.
 */
export function EmptyState({ headline, detail }: { headline: string; detail?: string }) {
  return (
    <p className="empty">
      <strong>{headline}</strong>
      {detail ? <span>{detail}</span> : null}
    </p>
  );
}

// ---------------------------------------------------------------------------

export function MetricCard({
  label,
  value,
  unit,
  footer,
}: {
  label: string;
  /** Already formatted. Absent values arrive as an explicit marker, never as 0. */
  value: string;
  unit?: string;
  footer?: ReactNode;
}) {
  return (
    <div className="metric">
      <dt>{label}</dt>
      <dd>
        {value}
        {unit ? <span className="metric-unit">{unit}</span> : null}
      </dd>
      {footer ? <div className="faint">{footer}</div> : null}
    </div>
  );
}

// ---------------------------------------------------------------------------

/**
 * Data age and, where a threshold is configured, its classification.
 *
 * When AMB-014's threshold is unconfigured, this shows the age and says
 * `AGE ONLY — NOT CLASSIFIED`. It does not show OK, and it does not quietly imply
 * currency by showing nothing.
 */
export function FreshnessIndicator({ view }: { view: FreshnessView }) {
  const age = formatAge(view.ageMs);
  return (
    <span className="freshness">
      <span aria-hidden="true">{freshnessGlyph(view)}</span>
      <span>{freshnessLabel(view)}</span>
      {age ? <span>· {age}</span> : null}
      {!view.thresholdConfigured && view.quality === null ? (
        <span className="unresolved">· threshold unset</span>
      ) : null}
    </span>
  );
}
