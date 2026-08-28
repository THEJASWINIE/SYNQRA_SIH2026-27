/**
 * HMI backend health indicator — M4, carrying forward the M1 connectivity proof.
 *
 * ============================================================================
 *  THIS IS NOT THE OPERATIONAL DATA FEED.
 *
 *  `GET /api/health` reports whether the HMI's own backend is reachable. The
 *  operational data path — provider status, per-datum freshness — is a
 *  DIFFERENT FAILURE DOMAIN and is reported separately in the shell. The
 *  backend can be up while the operational feed is silent, and the operator
 *  needs to be able to tell which has failed. The two must never be merged into
 *  one indicator.
 * ============================================================================
 *
 * Full backend diagnostics — message counts, latency history, component health — are S6
 * Diagnostics and arrive at M10. This is the compact indicator only.
 */

import { useCallback, useEffect, useState } from "react";
import { fetchHealth, type HealthResult } from "../api/healthClient";
import { type ConnectionState, connectionToken } from "../theme/statusTokens";

export function BackendHealth() {
  const [state, setState] = useState<ConnectionState>("idle");
  const [result, setResult] = useState<HealthResult | null>(null);

  const check = useCallback(async (signal?: AbortSignal) => {
    setState("connecting");
    const outcome = await fetchHealth(signal);
    if (signal?.aborted) return;
    setResult(outcome);
    setState(outcome.kind === "ok" ? "connected" : "error");
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    void check(controller.signal);
    return () => controller.abort();
  }, [check]);

  const token = connectionToken(state);

  return (
    <div className="hmi-header-slot">
      <dt>Backend (HMI)</dt>
      <dd>
        {/* Glyph and label always render; colour is an enhancement only (NFR-008). */}
        <span aria-hidden="true" style={{ color: token.colour }}>
          {token.glyph}
        </span>{" "}
        <span>{token.label}</span>{" "}
        {result?.kind === "ok" ? (
          <span className="faint">{result.latencyMs} ms</span>
        ) : result?.kind === "error" ? (
          <span className="faint">unreachable</span>
        ) : null}
      </dd>
    </div>
  );
}
