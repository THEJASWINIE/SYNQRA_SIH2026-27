# Task 1 — Requirements Traceability Matrix

**Specification:** `docs/FOG_ORCHESTRATOR_Task1_HMI_Requirements.pdf` (canonical path; sole Task 1 specification). "PDF §n" below refers to this document.
**Baseline:** Planning Baseline v1.9. Changes governed by `requirements/DECISIONS.md`.
**Last verified:** 2026-08-27 (M11). Statuses below reflect the repository as executed on that date.

**Principle (PDF §11):** every HMI function shall have a unique requirement ID, an
implementation reference, and at least one verification method. Mandatory requirements
must not be waived without team-lead approval. Optional CV requirements may be marked N/A.

---

## 0. Revision note — M11 (D12)

Until M11 **every row in this matrix read `PLANNED`**, including requirements that had been
implemented and browser-verified across M4–M10. The matrix had never been updated as
milestones completed, making it the least accurate document in the repository. That is
discovered documentation defect **D12**, corrected here through the revision process in
`DECISIONS.md`.

What changed: **status, evidence, verification artifact and implementation reference** —
each replaced with what the repository actually contains. What did **not** change:
requirement wording, acceptance criteria, IDs, methods or milestone assignments. No
requirement was waived, weakened or re-scoped.

**Status vocabulary** (five values, used exactly):

| Status | Meaning |
|---|---|
| `PASS` | Acceptance criteria executed and observed to hold. Named evidence. |
| `PARTIAL` | Part evidenced; a named part is not, for a named reason. |
| `BLOCKED` | Cannot proceed until a named external decision or system exists. |
| `NOT VERIFIABLE YET` | Measured, but no threshold exists to judge against. |
| `NOT STARTED` | Not implemented. |

**A mechanism existing is not a PASS.** Where a screen renders a state but no data or
decision exists to exercise it, the row reads PARTIAL or BLOCKED and says why.

**Verification codes:** `T` test · `D` demonstration · `I` inspection · `A` analysis/measurement

---

## 1. Functional Requirements

| ID | Title | M/O | Screen | Implementation | Verification evidence | Method | Status | Remaining gap | Owner / next |
|---|---|---|---|---|---|---|---|---|---|
| HMI-FR-001 | Live system overview | M | S1 | `screens/OperationsOverview.tsx`, `screens/AppShell.tsx`, `state/derive.ts` | `screens/render.test.tsx` (39), `state/derive.test.ts` (76); M11 browser A10/B5 | T, D | **PASS** | — | — |
| HMI-FR-002 | Mine/road map | M | S1 | `screens/MineMap.tsx` | `screens/render.test.tsx`, `state/scale.test.tsx` (12); M11 browser A4/A5 | T, D, I | **PASS** | — | — |
| HMI-FR-003 | Vehicle state | M | S2 | `screens/VehicleDetail.tsx`, `components/VehicleCard.tsx` | `screens/vehicleDetail.test.tsx` (43) | T, D | **PASS** | — | — |
| HMI-FR-004 | Safety envelope | M | S2 | `screens/VehicleDetail.tsx`, `components/VehicleCard.tsx` | `screens/vehicleDetail.test.tsx`, `screens/render.test.tsx` | T, I, D | **PASS** | — | — |
| HMI-FR-005 | Headway monitoring | M | S2 | `screens/VehicleDetail.tsx`, `components/VehicleCard.tsx` | `screens/vehicleDetail.test.tsx` | T, D | **PARTIAL** | `h_safe` units undefined; the HMI displays the value with an explicit unresolved-unit note rather than assuming metres | **AMB-001** — spec owner |
| HMI-FR-006 | Bottleneck visualization | M | S3 | `screens/BottleneckQueue.tsx`, `state/derive.ts` | `screens/bottleneckQueue.test.tsx` (26) | T, I, D | **PASS** | — | — |
| HMI-FR-007 | Queue monitoring | M | S3 | `screens/BottleneckQueue.tsx` | `screens/bottleneckQueue.test.tsx` | T, I, D | **PASS** | — | — |
| HMI-FR-008 | Arrival-rate shaping | M | S3 | `screens/BottleneckQueue.tsx` | `screens/bottleneckQueue.test.tsx` | T, I, D | **PASS** | Displays the supplied `ArrivalPlan`; no plan is computed locally | — |
| HMI-FR-009 | Slot reservation | M | S4 | `screens/DispatchSlots.tsx` | `screens/dispatchSlots.test.tsx` (60) | T, I, D | **PASS** | Conflict carries a distinct glyph and label (AC3) | — |
| HMI-FR-010 | Dispatch decision | M | S4 | `screens/DispatchSlots.tsx` | `screens/dispatchSlots.test.tsx`; `state/eventLog.test.ts` (33) | T, I, D | **PARTIAL** | AC3: commands reach the event log (M9), but the log is **in-memory only** | **AMB-010** — M12 |
| HMI-FR-011 | Fog/visibility | M | S1,S2 | `screens/OperationsOverview.tsx`, `screens/VehicleDetail.tsx`, `state/derive.ts` | `state/derive.test.ts`, `screens/render.test.tsx` | T, I, D | **PASS** | — | — |
| HMI-FR-012 | Road condition | M | S1,S2 | `screens/OperationsOverview.tsx`, `screens/VehicleDetail.tsx` | `screens/vehicleDetail.test.tsx`, `screens/render.test.tsx` | T, D | **PASS** | — | — |
| HMI-FR-013 | Communication health | M | S6,S1,S2 | `screens/Diagnostics.tsx`, `state/diagnostics.ts` | `screens/diagnostics.test.tsx` (58), `state/diagnostics.test.ts` (21); M11 browser | T, D | **PARTIAL** | AC1 (V2I, V2V, LoRa) verified by **test-local fixtures only** — no authored scenario supplies V2V or LoRa | Scenario authoring — M12 |
| HMI-FR-014 | Alerts | M | S1 + alert list | `screens/AlertList.tsx`, `components/AlertRow.tsx`, `state/alerts.ts` | `screens/alertList.test.tsx` (45), `state/alerts.test.ts` (35); M11 browser B4 | T, I, D | **PARTIAL** | AC1: `BOTTLENECK_RISK` and `INFO` categories are never supplied by an authored scenario; covered by fixtures only | Scenario authoring — M12 |
| HMI-FR-015 | Alert acknowledgment | M | alert list, S5 | `providers/*.sendAcknowledgement`, `state/eventLog.ts` | `providers/MockDataProvider.test.ts` (42), `providers/ReplayProvider.test.ts` (25); `docs/verification/latency.md` | T, I, D | **BLOCKED** | The provider path works and is measured, but **no acknowledgement UI is exposed** (M9D-F) pending server-side role enforcement | **GAP-ROLE-001** — unowned |
| HMI-FR-016 | System modes | M | status bar | `state/systemMode.ts`, `screens/AppShell.tsx` | `state/systemMode.test.ts` (32); M11 browser B2/B6 | T, D | **PARTIAL** | AC2: transitions are logged, but the log is **in-memory only** | **AMB-010** — M12 |
| HMI-FR-017 | Replay | M | S5 | `providers/ReplayProvider.ts`, `screens/EventReplay.tsx`, `state/recorder.ts` | `providers/ReplayProvider.test.ts` (25), `screens/eventReplay.test.tsx` (24), `state/eventLog.test.ts` (33) | T, D | **PASS** | Replay is unmistakable on every screen (`▶ REPLAY — NOT LIVE`); acknowledgement rejected during replay | — |
| HMI-FR-018 | KPI dashboard | M | S1 | `screens/OperationsOverview.tsx` | `screens/render.test.tsx`, `state/derive.test.ts` | T, I, D | **PASS** | Renders supplied KPIs, and an explicit "KPI DATA UNAVAILABLE — Task 1 does not generate KPIs" state | — |
| HMI-FR-019 | Scenario controls | M | S7 | `mocks/registry.ts`, `providers/MockDataProvider.ts`, `screens/ScenarioPicker.tsx` | `mocks/scenarios.test.ts` (39), `providers/MockDataProvider.test.ts` (42); M11 browser (every scenario switch) | T, I, D | **PASS** | Eleven scenarios; five FR-019 families present | — |
| HMI-FR-020 | CV integration | **O** | CV panel | — | — | D | **NOT STARTED** (optional) | Optional; not begun | M13 |

---

## 2. Non-Functional Requirements

Evidence detail for every row: `docs/verification/nfr-signoff.md`.

| ID | Category | M/O | Implementation | Verification evidence | Method | Status | Remaining gap | Owner / next |
|---|---|---|---|---|---|---|---|---|
| HMI-NFR-001 | Performance | M | `state/store.ts` tick, `screens/*` | `docs/verification/perf.md`; `frontend/verification/nfr001-render.ts`; browser measurement | A, T | **NOT VERIFIABLE YET** | Measured (S1 at 50 vehicles: render p50 7.2 ms; browser frame p50 16.6 ms; 5 long tasks / 12 s). `PLACEHOLDER_NFR001_REFRESH` is unfilled — no verdict can be computed | **AMB-004** — spec owner |
| HMI-NFR-002 | Command latency | M | `providers/DataProvider.ts` `sendAcknowledgement` | `docs/verification/latency.md`; `frontend/verification/nfr002-ack-latency.ts` | A, I | **NOT VERIFIABLE YET** | Measured (p50 0.0096 ms, n=200), acknowledgement path only, no transport, no operator gesture. `PLACEHOLDER_NFR002_COMMAND_LATENCY` unfilled | **AMB-004**, **AMB-008** — spec owner |
| HMI-NFR-003 | Data freshness | M | `state/freshness.ts`, `config/freshness.ts`, `state/diagnostics.ts` | `state/freshness.test.ts` (18), `data/freshness.test.ts` (29), `state/diagnostics.test.ts` (21); `docs/verification/failure-scenarios.md` | T, D | **PARTIAL** | Age display and non-classification fully evidenced. "Flagged stale after a configurable timeout" is undemonstrable: **the timeout has no value** | **AMB-014** — spec owner |
| HMI-NFR-004 | Availability | M | `state/store.ts`, `data/patch.ts`, `providers/*` | `state/recovery.test.ts` (9), `state/lifecycle.test.ts` (17); `docs/verification/failure-scenarios.md` §4 | T, D | **PARTIAL** | No duplicated or incoherent entities across reconnection — evidenced. Real-transport recovery has no subject to test | **TECH-001** — M12 |
| HMI-NFR-005 | Safety separation | M | `providers/DataProvider.ts`, `state/ProviderHost.tsx`, `docs/adr/ADR-001` | `docs/verification/architecture-inspection.md`; absence asserted in `providers/DataProvider.test.ts` (13), `MockDataProvider.test.ts`, `ReplayProvider.test.ts`, `screens/alertList.test.tsx` | I, D | **PASS** | Re-verify against `LiveDataProvider` when it exists | M12 (re-verification) |
| HMI-NFR-006 | Explainability | M | `screens/DispatchSlots.tsx`, `screens/VehicleDetail.tsx` | `screens/dispatchSlots.test.tsx` (60), `screens/vehicleDetail.test.tsx` (43) | T, I, D | **PASS** | Reason codes and limiting variables are **supplied**, never composed; a missing reason code is marked a data defect | — |
| HMI-NFR-007 | Traceability | M | `state/eventLog.ts`, `state/recorder.ts` | `state/eventLog.test.ts` (33), `screens/eventReplay.test.tsx` (24) | T, D | **PARTIAL** | Timestamped, ordered, append-only, visible. **Not persisted** — in-memory for the session (M9D-A) | **AMB-010** — M12 |
| HMI-NFR-008 | Usability (no colour-only) | M | `theme/statusTokens.ts`, `state/freshness.ts` | `docs/verification/greyscale-audit.md`; colour-stripped assertions in 8 test files; browser greyscale sweep of all six screens | I, T | **PASS** | Acknowledgement state and role state not audited — those states do not exist yet | Audit when built |
| HMI-NFR-009 | Scalability | M | `screens/OperationsOverview.tsx`, `screens/MineMap.tsx`, `mocks/scenarios/scale.json` | `docs/verification/scale.md`; `state/scale.test.tsx` (12); M11 browser section A (12 checks) | T, A | **PASS** | 50 vehicles / 20 nodes render correctly and remain interactive. Authored maximum only; mock data; development build | — |
| HMI-NFR-010 | Portability | M | `README.md` | `docs/verification/portability.md` | D, I | **PARTIAL** | Four shells documented; setup verified on **this** machine. **No independent clean machine was used and none is claimed.** See also D14 (README stale) | Release verification |
| HMI-NFR-011 | Security baseline | M | `backend/app/config.py`, `.env.example`, `.github/workflows/ci.yml` | Secret scan 2026-08-27 — no match; CI runs the same scan | T, I | **PARTIAL** | Credential hygiene evidenced. **Server-side role gating does not exist** | **GAP-ROLE-001** — unowned |
| HMI-NFR-012 | Recovery | M | `state/systemMode.ts`, `state/freshness.ts`, `state/alerts.ts` | `docs/verification/failure-scenarios.md`; `state/systemMode.test.ts` (32), `state/lifecycle.test.ts` (17); M11 browser section B (24 checks) | T, D | **PASS** | Feed loss degrades on all six screens; values retained; silent feed and lost link are not conflated | — |

---

## 3. Derived Requirements

| ID | Requirement | M/O | Source | Implementation | Verification evidence | Method | Status | Remaining gap | Owner / next |
|---|---|---|---|---|---|---|---|---|---|
| S2-a | Grade display on Vehicle Detail | M | PDF §7 (S2) | `screens/VehicleDetail.tsx` | `screens/vehicleDetail.test.tsx` (43) | T | **PASS** | — | — |
| S2-b | Recent trend history on Vehicle Detail | M | PDF §7 (S2) | — | — | T, D | **BLOCKED** | No vehicle history is supplied, and accumulating one locally would be an invented derivation (M5D-C, PAD-F) | Producer / spec owner |
| S5-a | Event categories on the replay timeline | M | PDF §7 (S5) | `screens/EventReplay.tsx`, `state/recorder.ts` | `screens/eventReplay.test.tsx` (24), `state/eventLog.test.ts` (33) | T, D | **PARTIAL** | The HMI derives only observable lifecycle events (M9D-C). `FOG_CHANGE`, `QUEUE_CHANGE` and `VIOLATION` are producer-supplied and no authored scenario supplies an `EventRecord` | Scenario authoring / producer — M12 |
| S6-a | Message counts and latency per component | M | PDF §7 (S6) | `screens/Diagnostics.tsx` | `screens/diagnostics.test.tsx` (58); M11 browser A12 | T, D | **PASS** | Counters are **supplied** on `Health.messagesReceived` / `.messagesDropped` (M10D-A); the HMI keeps none of its own | — |
| ROLE-001 | Role-gated actions; no safety override | M | PDF §4 | — | — | T, I | **BLOCKED** | No role infrastructure exists. Blocks FR-015 AC3 and NFR-011. **This requirement has no owning milestone** | **UNOWNED — needs assignment** |
| OPS-001 | Supervisory only; not the Tier-1 governor | M | PDF §3 | `docs/adr/ADR-001-hmi-advisory-only.md`, `providers/DataProvider.ts` | `docs/verification/architecture-inspection.md` | I | **PASS** | — | — |
| OPS-002 | Commands advisory | M | PDF §3 | `screens/DispatchSlots.tsx` | `screens/dispatchSlots.test.tsx` (60) | I, D | **PASS** | Dispatch states are displayed as supplied; no issuing control exists | — |
| OPS-003 | Degraded mode on comm loss | M | PDF §3 | `state/systemMode.ts` | `state/systemMode.test.ts` (32); `docs/verification/failure-scenarios.md` §2 | T, D | **PASS** | Verified on all six screens in a real browser | — |
| OPS-004 | CV non-authoritative | M | PDF §3 | — | — | I | **NOT STARTED** | Depends on optional CV work | M13 (optional) |
| TECH-001 | Transport choice documented | M | PDF §10 | — | — | I | **NOT STARTED** | No transport exists; `LiveDataProvider` is M12 | M12 |

---

## 4. Optional CV Requirements

| ID | M/O | Planned implementation reference | Verification | Status |
|---|---|---|---|---|
| CV-001 | O | `cv/ingest.py` | D | NOT STARTED |
| CV-002 | O | `cv/visibility.py` | D | NOT STARTED |
| CV-003 | O | `cv/detect.py` | D | NOT STARTED |
| CV-004 | O | latency instrumentation | A | NOT STARTED — threshold is a placeholder awaiting authoritative confirmation |
| CV-005 | O | CV status handling | T, D | NOT STARTED |
| CV-006 | O | `CVResult` publisher | T, D | NOT STARTED |

Optional. Mandatory HMI completion precedes any CV work (M13).

---

## 5. Status roll-up (mandatory requirements)

| Status | Count | IDs |
|---|---|---|
| **PASS** | 23 | FR-001, 002, 003, 004, 006, 007, 008, 009, 011, 012, 017, 018, 019 (13); NFR-005, 006, 008, 009, 012 (5); S2-a, S6-a, OPS-001, OPS-002, OPS-003 (5) |
| **PARTIAL** | 11 | FR-005, 010, 013, 014, 016 (5); NFR-003, 004, 007, 010, 011 (5); S5-a (1) |
| **BLOCKED** | 3 | FR-015; S2-b; ROLE-001 |
| **NOT VERIFIABLE YET** | 2 | NFR-001, NFR-002 |
| **NOT STARTED** | 2 | OPS-004 (optional dependency), TECH-001 |

Exact counts: **23 PASS · 11 PARTIAL · 3 BLOCKED · 2 NOT VERIFIABLE YET · 2 NOT STARTED = 41 mandatory requirements.**

Every non-PASS row names its blocker. **Nine of the sixteen open items are blocked on
decisions this project is forbidden to make for itself** — AMB-001, AMB-004 (×2), AMB-008,
AMB-010 (×3), AMB-014, and GAP-ROLE-001 (×2). They will not close through further
engineering in this repository.

---

## 6. Screen Coverage Check

Every mandatory screen in PDF §7 is covered by at least one mandatory FR, and every
mandatory FR lands on at least one screen. All six are implemented and were rendered in a
real browser during M11 under nominal, scale, communication-loss and stale-feed conditions.

| Screen | Requirements landing on it | Delivered | Verified in browser (M11) |
|---|---|---|---|
| S1 Operations Overview | FR-001, 002, 006, 011, 012, 014, 016, 018 | M4 | yes |
| S2 Vehicle Detail | FR-003, 004, 005, 011, 012, 013, S2-a, S2-b | M5 | yes |
| S3 Bottleneck & Queue | FR-006, 007, 008 | M6 | yes |
| S4 Dispatch & Slots | FR-009, 010, NFR-006 | M7 | yes |
| S5 Event/Replay | FR-017, S5-a, NFR-007 | M9 | yes |
| S6 Diagnostics | FR-013, S6-a, NFR-003 | M10 | yes |
| S7 Scenario/Dev | FR-019 | M3 + M4 | yes |

**No mandatory requirement is unassigned.** 41 mandatory requirements, 41 rows with an
implementation reference, a verification artifact and a status.

---

## 7. Task 2 Dependency Trace

Requirements whose *data* cannot be produced by this repository. Each is satisfied in
Task 1 by a typed interface plus mock data, and must be re-verified against live data at
M12.

| Requirement | Task 2 input required | Task 1 substitute until integration |
|---|---|---|
| FR-004 | `v_safe`, `active_constraint` | `SafetyState` mock |
| FR-005 | `h_safe`, headway, lead vehicle | `SafetyState` mock (AMB-001) |
| FR-006 | `bottleneck_score`, `criticality` | `BottleneckState` mock |
| FR-007 | `lambda_vph`, `mu_vph`, predicted queue | `BottleneckState` mock |
| FR-008 | arrival plan, metering/hold decisions | `ArrivalPlan` mock (AMB-002) |
| FR-009 | slot windows, conflict status | `SlotState` mock |
| FR-010 | assignment, route, departure, reason code | `DispatchCommand` mock |
| FR-011 | visibility forecast + sigma | `VisibilityForecast` mock |
| FR-012 | friction estimate, surface state | `RoadState` mock |
| FR-018 | KPI values | `KpiSnapshot` mock (AMB-003) |
| FR-014 (4 of 6 categories) | safety/bottleneck/slot alerts | `Alert` mock |
| S2-b | vehicle history / trend series | **none — BLOCKED**, no substitute may be invented |

**Scope-control assertion, re-verified 2026-08-27:** none of the rows above is satisfied by
computing the value locally. A repository-wide search for Task 2 computation returned no
production implementation, and the closed derivation list in
`requirements/task1-data-contract.md` §12 was re-counted and remains at **nine** items. See
`docs/verification/architecture-inspection.md`.
