/**
 * Freshness configuration — M2. MAD-D.
 *
 * ============================================================================
 *  PLACEHOLDER_NFR003_STALE_TIMEOUT_MS
 *
 *  NOT AUTHORITATIVE. NO PRODUCTION DEFAULT EXISTS.
 *
 *  HMI-NFR-003 requires stale data to be "visually flagged after a configurable
 *  timeout" but the specification never states what that timeout is. This is
 *  registered as AMB-014 in `requirements/DECISIONS.md` and is UNRESOLVED.
 *
 *  Under PAD-G no value may be invented. Consequently this module supplies NO
 *  default. The threshold must be provided explicitly by configuration, and
 *  tests inject it. Reading it without a configured value fails loudly rather
 *  than silently substituting a number that nobody authorized.
 *
 *  Why this one matters more than the other placeholders: NFR-001, NFR-002 and
 *  CV-004 affect sign-off only. This threshold changes what an operator sees.
 *  Set too long, genuinely stale safety data reads as current — the exact
 *  failure NFR-012 exists to prevent. Set too short, everything flickers stale
 *  and the flag stops meaning anything.
 *
 *  Resolution required from: the specification owner.
 *  Open question to put alongside it: whether one global timeout suffices, or
 *  whether message classes need separate ones. Visibility and dispatch data
 *  plausibly age at very different rates. The specification does not say, and
 *  this module does not assume.
 * ============================================================================
 */

/** The environment variable that supplies the threshold. */
export const STALE_TIMEOUT_ENV_KEY = "VITE_PLACEHOLDER_NFR003_STALE_TIMEOUT_MS";

export interface FreshnessConfig {
  /** Age in milliseconds beyond which a valid datum is STALE. */
  staleTimeoutMs: number;
  /**
   * False until the specification owner supplies an authoritative value.
   * Anything rendering freshness may use this to mark the threshold provisional.
   */
  isAuthoritative: boolean;
}

export type FreshnessConfigResult =
  | { ok: true; config: FreshnessConfig }
  | { ok: false; reason: string };

/**
 * Read the threshold from configuration.
 *
 * Deliberately returns a failure rather than a fallback when unset. A default here would
 * be an invented threshold wearing a sensible-looking number, which PAD-G forbids and
 * which nobody would ever notice.
 */
export function readFreshnessConfig(
  env: Record<string, string | undefined> = import.meta.env as unknown as Record<
    string,
    string | undefined
  >,
): FreshnessConfigResult {
  const raw = env[STALE_TIMEOUT_ENV_KEY];

  if (raw === undefined || raw.trim() === "") {
    return {
      ok: false,
      reason:
        `${STALE_TIMEOUT_ENV_KEY} is not configured. NFR-003 requires a configurable ` +
        "staleness timeout; the specification states no value (AMB-014, unresolved). " +
        "Supply one explicitly — no default is authorized.",
    };
  }

  const parsed = Number(raw);
  if (!Number.isFinite(parsed) || parsed <= 0) {
    return {
      ok: false,
      reason: `${STALE_TIMEOUT_ENV_KEY} must be a positive number of milliseconds; received "${raw}".`,
    };
  }

  return {
    ok: true,
    config: { staleTimeoutMs: parsed, isAuthoritative: false },
  };
}

/**
 * Build a configuration explicitly. This is how tests inject a threshold, so the
 * freshness mechanism is verifiable without depending on the unresolved real value.
 */
export function freshnessConfig(staleTimeoutMs: number): FreshnessConfig {
  return { staleTimeoutMs, isAuthoritative: false };
}
