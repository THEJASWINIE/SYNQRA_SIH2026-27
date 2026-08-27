# Failure-scenario verification record — NFR-012, NFR-004, NFR-003

**Milestone:** M11
**Date:** 2026-08-27

---

## 1. Scope

This record covers what the HMI does when the data path misbehaves: the feed stops, the
link drops, the link returns, and data ages with no threshold configured. It is the
executed evidence for **HMI-NFR-012** (recovery / graceful degradation), **HMI-NFR-004**
(availability) and the observable half of **HMI-NFR-003** (freshness).

Every scenario below is an **authored M3 scenario**, played through the real application.
No scenario file was created or modified for this milestone.

## 2. Cross-screen sweep — feed stop (`communication-loss`)

Browser: headless Edge `Edg/151.0.4129.107` over CDP, Vite dev server on `localhost:5173`,
FastAPI backend on `127.0.0.1:8000`. Harness `scratchpad/verify-m11.mjs`, section B.

| Screen | Renders | System mode in shell |
|---|---|---|
| S1 Operations | pass | `DEGRADED — raised to DEGRADED, data feed lost (FR-016)` |
| S2 Vehicle | pass | `DEGRADED` |
| S3 Bottleneck | pass | `DEGRADED` |
| S4 Dispatch | pass | `DEGRADED` |
| S5 Replay | pass | `DEGRADED` |
| S6 Diagnostics | pass | `DEGRADED` |

Additional observations on the same run:

| Property | Observed |
|---|---|
| Last values retained rather than blanked | 2 vehicles still shown after the feed stopped |
| Alert raised on comm loss | 1 row: `WARNING · Data feed lost: V2I link lost · COMM_LOSS · SYSTEM DATA_PATH · DISCONNECTED · origin HMI — data path` |
| Alert origin marked as HMI-derived | yes — `ORIGIN HMI — DATA PATH` (M8D-A) |
| Degraded state reaches every screen, not just S1 | yes, all six |
| Console errors | 0 |

**The mode transition is explained on screen**, not merely displayed: the shell carries
`raised to DEGRADED — data feed lost (FR-016)`.

## 3. Cross-screen sweep — silent feed (`stale-feed`)

The distinguishing case: the link is **up**, but no data arrives.

| Property | Observed |
|---|---|
| System mode | `NORMAL` — **not** forced to DEGRADED |
| Displayed age advances while the feed is silent | `VehicleState 2 · 7.2 s ago` → `10.2 s ago` |
| Freshness threshold state | `▲ FRESHNESS THRESHOLD NOT CONFIGURED` shown explicitly |
| Quality classification | `AGE ONLY — NOT CLASSIFIED`, `n/e` in every quality column |
| All six screens render | S1–S6 pass |

This is the correct and deliberate behaviour, and it is the one most easily got wrong: a
silent feed on a healthy link is **not** the same failure as a lost link, and the HMI does
not conflate them. Ages keep advancing so the operator can see data going old, while the
system refuses to *classify* anything as stale because **no authoritative timeout exists**
(AMB-014, HMI-NFR-003). The screen says so in words rather than defaulting to a number this
project is not authorised to choose:

> `VITE_PLACEHOLDER_NFR003_STALE_TIMEOUT_MS is not configured. NFR-003 requires a
> configurable staleness timeout; the specification states no value (AMB-014, unresolved).
> Supply one explicitly — no default is authorized.`

Consequently `STALE ALERTING INACTIVE — NO FRESHNESS THRESHOLD CONFIGURED (AMB-014)` is
displayed on S1. **Stale data is never presented as current**, but neither is it flagged
stale, because flagging requires the missing threshold. This is the precise reason NFR-003
is PARTIAL rather than PASS.

## 4. Recovery — `disconnect-reconnect` (NFR-004)

### 4.1 In the browser

| Property | Observed |
|---|---|
| Vehicle count before loss | 2 |
| Vehicle count after reconnection | 2 |
| Duplicate vehicles after recovery | **0** (2 unique of 2) |
| Vehicle ids identical before and after | yes |
| System mode after recovery | `NORMAL` — no longer DEGRADED |
| S6 freshness after recovery | `VehicleState 2 · 6.5 s ago` — fresh data flowing again |

### 4.2 Automated

`frontend/src/state/recovery.test.ts` (new at M11), 9 tests, all passing:

| Assertion | Result |
|---|---|
| Fleet count unchanged before and after recovery | pass |
| Re-emission after reconnect updates rather than adds | pass |
| Every slice still keyed by entity id after recovery | pass |
| No duplicate alert id after recovery | pass |
| No duplicate event id after recovery | pass |
| Every vehicle still has its matching safety state | pass |
| Recovered timestamp is post-reconnection, not pre-loss | pass |
| No pre-loss value presented as current after recovery | pass |
| Recovery does not resurrect entities a scenario reset removed | pass |

The eighth assertion is the load-bearing one: the pre-loss datum, judged at the
post-recovery clock, would read `STALE`; the value actually held reads `OK`. A stale
reading is therefore not being shown as live.

Pre-existing coverage in `frontend/src/state/lifecycle.test.ts` (M4) already proved the
recovery *arc* — loss, ageing, reconnection, fresh values. M11 added only the coherence
half that was missing.

### 4.3 Limitation, stated plainly

**This is not evidence about a real transport.** It exercises the authored mock
disconnect/reconnect scenario. What it establishes is that the store's merge semantics
survive a reconnection without duplicating or corrupting state — a property of the HMI,
independent of transport. Reconnection behaviour of an actual link is M12 (TECH-001), and
NFR-004 remains PARTIAL for that reason.

## 5. Backend-down / feed-healthy separation

Verified at M10 and unchanged: the HMI backend health indicator is independent of the data
feed. With the backend stopped and the feed healthy, S6 showed the backend `UNREACHABLE`
while the feed continued and the system mode stayed `NORMAL` (M10 browser run, 7/7). The
converse was re-confirmed in this milestone's run: under `communication-loss` the backend
indicator stayed reachable while the feed was lost.

## 6. Failure modes exercised in the automated suite

Additional data-path failures already carry automated coverage and were re-run as part of
the full suite (§ the M11 report):

| Failure | Coverage |
|---|---|
| Malformed payload → `INVALID`, never `MISSING` | `data/validate.test.ts`, `state/diagnostics.test.ts` |
| Empty timestamp → `MISSING`, never `INVALID` | `state/diagnostics.test.ts` |
| Unknown scenario id → `ERROR` status, not a silent no-op | `state/lifecycle.test.ts` |
| Disconnect cancels all scheduled work | `state/lifecycle.test.ts` |
| Scenario switch discards the previous mine | `state/lifecycle.test.ts`, `state/recovery.test.ts` |
| Validation failures surfaced to the operator | `screens/diagnostics.test.tsx` (D11 fix, M10) |
| Acknowledgement rejected during replay | `providers/ReplayProvider.test.ts` |

## 7. Result

| Requirement | Status | Reason |
|---|---|---|
| HMI-NFR-012 Recovery | **PASS** | Feed stop degrades gracefully on all six screens; values retained, ages advance, mode transition explained, recovery restores fresh data |
| HMI-NFR-004 Availability | **PARTIAL** | Coherence after reconnection fully evidenced; real-transport recovery does not exist to test (M12, TECH-001) |
| HMI-NFR-003 Freshness | **PARTIAL** | Age display and non-classification fully evidenced; "flagged stale after a configurable timeout" cannot be demonstrated while AMB-014 leaves the timeout unset |
