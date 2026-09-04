# HMI-NFR-008 — Greyscale / no-colour-only audit

**Milestone:** M11
**Date:** 2026-08-27
**Verdict:** **PASS** for the eight state dimensions audited; two dimensions are
**NOT APPLICABLE** because the states they describe do not yet exist in the product.

---

## 1. The requirement

HMI-NFR-008 requires that operational state never be conveyed by colour alone: every state
must also be readable as text or shape. This matters in a control room with a projector, a
poor monitor, or a colour-blind operator.

Two audit methods are combined, because either alone is weak:

- **I (inspection)** — the token source is read to confirm every state carries a `label`
  and a `glyph` alongside its `colour`.
- **T (test)** — screen tests strip colour from the rendered markup before asserting, so a
  test cannot pass on a colour attribute; and a real browser is rendered under a
  `grayscale(1)` filter with assertions on text.

## 2. The token contract

`frontend/src/theme/statusTokens.ts` defines a `StatusToken` as `{ label, glyph, colour }`.
Its own comment states the rule: *"A component that reaches for a colour without the
matching text or glyph is a defect."* Every enumerated state below was read from source.

### 2.1 System mode (FR-016)

| State | Label | Glyph |
|---|---|---|
| NORMAL | `NORMAL` | ● |
| CAUTION | `CAUTION` | ◆ |
| DEGRADED | `DEGRADED` | ◐ |
| LOCAL_SAFE | `LOCAL-SAFE` | ■ |
| STOP_UNSAFE | `STOP / UNSAFE` | ▲ |

### 2.2 Alert severity (FR-014)

| State | Label | Glyph |
|---|---|---|
| INFO | `INFO` | ℹ |
| WARNING | `WARNING` | ◆ |
| CRITICAL | `CRITICAL` | ▲ |

### 2.3 Risk level and criticality (FR-004, FR-006)

| State | Label | Glyph |
|---|---|---|
| LOW | `LOW` | ● |
| MODERATE / MEDIUM | `MODERATE` / `MEDIUM` | ◆ |
| HIGH | `HIGH` | ◆ |
| CRITICAL | `CRITICAL` | ▲ |
| UNKNOWN | `UNKNOWN` | ? |

`HIGH` and `MODERATE`/`MEDIUM` share a glyph but differ in label, so they remain
distinguishable without colour.

### 2.4 Freshness / data quality (NFR-003)

From `frontend/src/state/freshness.ts`. The comment on `freshnessLabel` states it is
*"always non-empty, so freshness never depends on a colour to be communicated (NFR-008)"*.

| Quality | Label | Glyph |
|---|---|---|
| OK | `CURRENT` | ● |
| STALE | `STALE` | ◐ |
| MISSING | `UNAVAILABLE` | ○ |
| INVALID | `INVALID` | ▲ |
| *(threshold unconfigured)* | `AGE ONLY — NOT CLASSIFIED` | ◌ |

The unconfigured case is itself a labelled state rather than a blank — the operator is told
that classification did not happen, instead of being shown an unmarked value.

### 2.5 Connection / provider status (FR-013)

| State | Label | Glyph |
|---|---|---|
| IDLE | `Idle` | ○ |
| CONNECTING | `Connecting` | ◐ |
| CONNECTED | `Connected` | ● |
| RECONNECTING | `Reconnecting` | ◐ |
| DISCONNECTED | `Disconnected` | ▲ |
| ERROR | `Provider error` | ▲ |

`CONNECTING` and `RECONNECTING` share a glyph; their labels differ.

### 2.6 Slot status, including conflict (FR-009)

| State | Label | Glyph |
|---|---|---|
| RESERVED | `RESERVED` | ▢ |
| ACTIVE | `ACTIVE` | ● |
| RELEASED | `RELEASED` | ○ |
| EXPIRED | `EXPIRED` | × |
| **CONFLICT** | `CONFLICT` | ▲ |
| UNKNOWN | `UNKNOWN` | ? |

The source records that `CONFLICT` carries a distinct glyph *as well as* a distinct colour
specifically because FR-009 AC3 requires conflicts to be unmistakable.

### 2.7 Dispatch state (FR-010)

| State | Label | Glyph |
|---|---|---|
| RECOMMENDED | `RECOMMENDED` | ◇ |
| ISSUED | `ISSUED` | ◆ |
| ACKNOWLEDGED | `ACKNOWLEDGED` | ✓ |
| SUPERSEDED | `SUPERSEDED` | ↷ |
| REJECTED | `REJECTED` | × |

### 2.8 Replay state (FR-017)

Replay is not a colour at all. `frontend/src/screens/AppShell.tsx` renders the literal text
`▶ REPLAY — NOT LIVE` in the shell whenever the provider is `REPLAY`, on every screen.

## 3. Screen-by-screen browser sweep

Headless Edge `Edg/151.0.4129.107`, a `html{filter:grayscale(1)!important}` style injected,
`nominal` scenario. Harness `scratchpad/verify-m11.mjs`, section D.

| Screen | Renders under greyscale | State conveyed in words |
|---|---|---|
| S1 Operations | pass | pass |
| S2 Vehicle | pass | pass |
| S3 Bottleneck | pass | pass |
| S4 Dispatch | pass | pass |
| S5 Replay | pass | pass |
| S6 Diagnostics | pass | pass |

Additional DOM audit on the same run: every status marker element carries non-empty text —
**9 markers examined, 0 empty**. A marker rendered as a bare coloured shape with no text
would have failed this check.

## 4. Automated coverage

Colour-stripping assertions are not new at M11; they are built into the screen tests from
M4 onward. Each of these strips `color:` declarations and hex literals from the markup
*before* asserting:

| Test file | Screens covered |
|---|---|
| `frontend/src/screens/render.test.tsx` | S1, vehicle cards, alert rows, map |
| `frontend/src/screens/vehicleDetail.test.tsx` | S2 |
| `frontend/src/screens/bottleneckQueue.test.tsx` | S3 |
| `frontend/src/screens/dispatchSlots.test.tsx` | S4 |
| `frontend/src/screens/eventReplay.test.tsx` | S5 |
| `frontend/src/screens/diagnostics.test.tsx` | S6 |
| `frontend/src/screens/alertList.test.tsx` | Alert list |
| `frontend/src/state/scale.test.tsx` | S1 at 50 vehicles (new at M11) |

## 5. Dimensions audited, and two that are not applicable

| Dimension NFR-008 names | Status |
|---|---|
| Safety | PASS — risk level, envelope and headway violations carry `▲` plus violation text |
| Severity | PASS — §2.2 |
| Criticality | PASS — §2.3 |
| Freshness | PASS — §2.4 |
| Connection | PASS — §2.5 |
| System mode | PASS — §2.1 |
| Conflicts | PASS — §2.6, distinct glyph *and* label |
| Replay state | PASS — §2.8, explicit text on every screen |
| *Acknowledgement state* | **NOT APPLICABLE** — no acknowledgement UI exists (M9D-F, blocked on ROLE-001) |
| *Role / permission state* | **NOT APPLICABLE** — no role infrastructure exists (GAP-ROLE-001) |

The last two rows are recorded rather than quietly omitted: they must be audited when the
states they describe are built, and that audit belongs to whichever milestone builds them.

## 6. Limitation

This audit establishes that state is **available** as text and shape. It does not establish
legibility at a given viewing distance, on a specific control-room display, or under a
specific ambient light level. That is a human-factors review on the target hardware, and it
belongs to deployment, not to M11.

## 7. Result

**HMI-NFR-008: PASS.** No state in the shipped product is conveyed by colour alone, on any
of the six screens, verified by source inspection, by colour-stripped automated tests, and
by a real browser under a greyscale filter.
