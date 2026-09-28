# HMI-NFR-002 — Command latency measurement report

**Milestone:** M11
**Date of measurement:** 2026-08-27
**Verdict:** **NOT VERIFIABLE YET** — measured, not passed.

---

## 1. What NFR-002 can mean in this repository

HMI-NFR-002 concerns the latency of a command from operator action to acknowledgement.
Two constraints bound what can honestly be measured here:

1. **Task 1 issues no commands.** PAD-B fixes the HMI as advisory-only, and AMB-008
   (command issuance) and AMB-009 (override) are unresolved. The only command-shaped path
   that exists in the codebase is `DataProvider.sendAcknowledgement`, which acknowledges an
   *HMI alert* and — per PAD-D — never implies that the underlying safety condition has
   been cleared.
2. **There is no acknowledgement UI.** M9D-F deferred it while ROLE-001 and NFR-011
   server-side role enforcement do not exist. The path is therefore exercised at the
   **provider boundary**, not from an operator gesture.

So this report measures the acknowledgement path, and says so plainly rather than
presenting it as an end-to-end operator round trip. **No command issuance was added to
measure this.**

The threshold `PLACEHOLDER_NFR002_COMMAND_LATENCY` is unfilled (AMB-004). No verdict is
computed.

## 2. Environment

| | |
|---|---|
| OS | Microsoft Windows 11 Home Single Language, build 26200 |
| CPU | 16 logical cores |
| Node | v24.18.0 |
| Provider | `MockDataProvider`, in-process, manual scheduler (virtual time) |
| Transport | **NONE** |

## 3. Method

Script: `frontend/verification/nfr002-ack-latency.ts` — run with
`npx vite-node verification/nfr002-ack-latency.ts`.

1. Load the authored `envelope-violation` scenario, which supplies one acknowledgeable
   alert (`A-HW-1`, WARNING / UNSAFE_HEADWAY).
2. Start a timer, call `provider.sendAcknowledgement(alertId, actor)`.
3. Stop the timer when the resulting `ProviderPatch` has been merged and applied to
   `AppStateStore` — that is, when the acknowledgement is *observable in application
   state*, not merely when the promise settles.
4. 200 samples after 20 warm-up iterations.

Timing the patch's arrival, rather than the promise, is deliberate: an acknowledgement the
operator cannot see is not an acknowledgement.

## 4. Results

| Measurement | n | min | p50 | p95 | p99 | max | mean |
|---|---|---|---|---|---|---|---|
| `sendAcknowledgement` → patch applied at store | 200 | 0.0066 | **0.0096** | 0.0196 | 0.0701 | 0.1947 | 0.0121 |

Figures in milliseconds.

**Observability check (not a timing figure):** after the call,
`Alert.acknowledged` reads `{"by":"operator-219","at":"2026-01-01T00:00:20.000Z"}` — the
acknowledgement is visible on the alert itself, not only in the event log. This is the
D9 fix (M9D-D) confirmed at runtime.

## 5. What this figure is and is not

**Is:** the HMI's own contribution to acknowledgement latency — validation, normalization,
patch construction, merge and store commit — measured to sub-microsecond resolution. It is
a floor: roughly ten microseconds at the median.

**Is not:**

- an end-to-end round trip. There is no transport; the mock provider emits in-process.
  Network, serialization, broker and server-side handling are all absent, and all of them
  will dominate the figure above once they exist (TECH-001, M12).
- an operator-initiated measurement. No acknowledgement control is rendered (M9D-F), so
  the input-handling and re-render portion of a real gesture is not included.
- evidence of conformance. There is no threshold to conform to.

## 6. What would change the verdict

| Needed | Owner |
|---|---|
| An authoritative value for `PLACEHOLDER_NFR002_COMMAND_LATENCY` (AMB-004) | Specification owner |
| A ruling on AMB-008 — whether Task 1 issues commands at all | Specification owner |
| Server-side role enforcement, unblocking the acknowledgement UI (ROLE-001, FR-015) | M12 |
| A real transport to measure across (TECH-001) | M12 |

Until then HMI-NFR-002 remains **NOT VERIFIABLE YET**, and the scope of what was measured
must be quoted with the figure.
