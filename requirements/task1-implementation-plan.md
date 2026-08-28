# Task 1 — Implementation Plan

**Specification:** `docs/FOG_ORCHESTRATOR_Task1_HMI_Requirements.pdf` (canonical path; sole Task 1 specification). "PDF §n" below refers to this document.
**Baseline:** Planning Baseline v1.3 (frozen). Changes governed by `requirements/DECISIONS.md`.

**Phase:** planning only. Nothing in this document has been built.
**Rules in force:** `CLAUDE.md`, scope-control skill, task1-architecture skill, testing skill.

## Sequencing Principle

Milestones are ordered so the HMI is demonstrable end-to-end on mock data long before
Task 2 exists (CLAUDE.md: "The HMI must work independently using mock data"). The
provider boundary is built in M2/M3, before any screen, so no screen is ever written
against raw JSON and later retrofitted.

Every milestone ends with the testing skill's completion report: files changed,
verification performed, test results, remaining limitations. "Code written" is never
"done".

## Standing Verification Gate (every milestone)

Applied to each milestone before it is called complete:

1. Lint passes.
2. Type check passes.
3. Milestone tests pass.
4. Application starts.
5. Feature demonstrated in the running app.
6. Failure states exercised: loading, error, stale data, disconnected.
7. **Scope audit:** confirm no Task 2 algorithm was introduced. Grep the diff for
   computation over `v_safe`, `h_safe`, `bottleneck_score`, queue prediction, dispatch or
   route selection. Anything found is a defect, not a feature.
8. Limitations reported explicitly.

Milestone-specific tests below are *in addition* to this gate.

---

## M1 — Foundation

- **Goal:** a running, empty, verifiable shell with the project's rules encoded in tooling.
- **Features:**
  - Repository structure: `frontend/`, `backend/`, `shared/`, `docs/`, `requirements/`.
  - React frontend scaffold (technology baseline §10 plus architecture skill), FastAPI backend scaffold.
  - Lint, format, type check, test runner wired and runnable by one documented command each.
  - `README.md` with clean-machine setup steps (NFR-010).
  - Config/env handling; no credentials in source (NFR-011).
  - Shared status-token set: every state gets a text/icon token, so no display can depend on color alone (NFR-008).
  - Architecture record stating the HMI is advisory-only (NFR-005, OPS-001).
- **Files/components likely required:** `README.md`, `frontend/package.json`, `frontend/src/main.tsx`, `frontend/src/theme/statusTokens.ts`, `backend/app/main.py`, `backend/pyproject.toml`, `.env.example`, lint/type/test configs, CI workflow with a secret scan.
- **Dependencies:** none.
- **Tests:** one smoke test each side (frontend renders, backend health endpoint responds); secret-scan job.
- **Definition of done:** clean-machine checkout runs frontend and backend from README steps alone; lint, type check and both smoke tests pass in CI; secret scan passes; no application feature exists yet.

---

## M2 — Shared Schemas and Data Contracts

- **Goal:** the contract in `task1-data-contract.md` exists as centralized types on both
  sides, with the freshness mechanism built in from the start.
- **Features:**
  - TypeScript types for every message in the data contract.
  - Mirrored Pydantic models in the backend.
  - `Sourced<T>` wrapper and the freshness/staleness derivation (NFR-003).
  - Normalization layer: external message shape to `AppState`, including unknown-enum
    handling (unrecognised value becomes `UNKNOWN`, never dropped).
  - `DataProvider` interface definition. No implementation yet.
  - Configurable staleness timeout (configuration, not a component literal).
- **Files/components likely required:** `shared/contracts/*.ts`, `backend/app/schemas/*.py`, `frontend/src/state/appState.ts`, `frontend/src/state/normalize.ts`, `frontend/src/state/freshness.ts`, `frontend/src/providers/DataProvider.ts`, `config/freshness.json`.
- **Dependencies:** M1.
- **Tests:** normalization round-trip for each message type; unknown enum value maps to `UNKNOWN`; missing field yields `quality: "MISSING"` and never `0`; age crossing the timeout flips `OK` to `STALE`.
- **Definition of done:** every contract message has a type on both sides and a normalization test; the freshness rule is proven by test at the state layer, before any UI depends on it; type check passes.
- **Traces:** NFR-003, NFR-012, and the input side of every FR.

---

## M3 — Mock Data and Scenarios

- **Goal:** `MockDataProvider` can drive the entire contract, including every failure mode,
  so all later milestones are independently developable and testable.
- **Features:**
  - `MockDataProvider` implementing `DataProvider`, emitting normalized patches on a tick.
  - Named scenarios (FR-019): fog, friction, grade, fleet-density, communication-loss.
  - Additional test scenarios: nominal, stale-feed, disconnect/reconnect, slot-conflict, envelope-violation, scale (50 vehicles / 20 nodes, NFR-009).
  - Scenario picker UI restricted to the developer/tester role (S7).
  - Deterministic seeding so tests and demos are reproducible.
- **Files/components likely required:** `frontend/src/providers/MockDataProvider.ts`, `mocks/scenarios/*.json`, `mocks/topology.json`, `frontend/src/components/ScenarioPicker.tsx`.
- **Dependencies:** M2.
- **Tests:** each named scenario loads and produces valid normalized state; the scale scenario yields 50 vehicles and 20 nodes; the comm-loss scenario stops emission and drives `quality: "STALE"`; scenario switching leaves no residue from the previous scenario.
- **Definition of done:** all five FR-019 scenario families plus the failure scenarios load and drive state; no component reads a scenario file directly; determinism verified by repeated identical runs.
- **Scope note:** mock scenarios contain **pre-baked** values for `v_safe`, `h_safe`, scores and queue forecasts. They must not contain a physics or queueing model, which would be a Task 2 algorithm wearing a mock's clothing. This is checked in the M3 scope audit.
- **Traces:** FR-019, NFR-009, NFR-012, and the data supply for all screens.

---

## M4 — Operations Overview (S1)

- **Goal:** the primary situational screen, driven entirely by mock data.
- **Features:** persistent status bar (FR-001); graph mine map with node kinds, grades, vehicles (FR-002); active-bottleneck marker (FR-006 display half); current fog state (FR-011); road-condition layer (FR-012); top alerts panel (FR-014 display half); KPI panel (FR-018); mode badge (FR-016 display half); selection navigating to S2/S3.
- **Files/components likely required:** `components/StatusBar`, `components/MineMap`, `components/MapLayers/{Fog,RoadCondition,Bottleneck}`, `components/KpiPanel`, `components/TopAlerts`, `screens/OperationsOverview`, selectors in `state/selectors`.
- **Dependencies:** M2, M3.
- **Tests:** status bar renders all five FR-001 elements; every vehicle appears exactly once; each node kind renders its distinct glyph; scale scenario renders without collapse; unsupplied KPI renders as unavailable rather than `0`; stale scenario marks values stale on this screen.
- **Definition of done:** S1 shows every item PDF §7 lists for it, on mock data, with stale and disconnected states visibly correct; greyscale check passes (NFR-008).
- **Traces:** FR-001, 002, 006, 011, 012, 014, 016, 018; NFR-003, 008, 009.

---

## M5 — Vehicle Detail (S2)

- **Goal:** per-vehicle view, with the actual-versus-safe distinction unmistakable.
- **Features:** vehicle panel with all eight FR-003 fields; safety envelope showing actual vs `v_safe` plus active-constraint chip (FR-004); headway pair view with `h_safe` and violation status (FR-005); grade (S2-a); recent trend history (S2-b); per-vehicle visibility, road condition and communication state.
- **Files/components likely required:** `components/VehiclePanel`, `components/SafetyEnvelope`, `components/HeadwayPair`, `components/VehicleTrend`, `screens/VehicleDetail`, `state/history` (rolling buffer of received values).
- **Dependencies:** M4.
- **Tests:** all eight fields render; friction never renders without its sigma; exceedance state distinguishable in greyscale; missing `v_safe` renders "no data" and never a computed substitute; trend buffer bounded and correct.
- **Definition of done:** S2 shows every item PDF §7 lists for it; the envelope is verified as display-only by inspection; failure states correct.
- **Scope note:** `state/history` stores what arrived. It does not smooth, filter or predict.
- **Traces:** FR-003, 004, 005, 011, 012, 013 (per-vehicle), S2-a, S2-b; NFR-008.

---

## M6 — Bottleneck and Queue (S3)

- **Goal:** bottleneck and queue situational awareness, with supplied scores only.
- **Features:** ranked bottleneck list sorted by supplied `bottleneck_score` (FR-006); per-node queue widgets against `queue_max` with lambda and mu (FR-007); measured queue history and supplied queue forecast rendered distinctly; planned vs actual arrivals plus active metering/hold decisions (FR-008).
- **Files/components likely required:** `components/BottleneckList`, `components/QueuePanel`, `components/QueueTrendChart`, `components/ArrivalShaping`, `screens/BottleneckQueue`.
- **Dependencies:** M4 (map marker), M3.
- **Tests:** list order matches descending supplied score with a deterministic tie-break; absent lambda/mu renders unavailable and never `0`; forecast series visually and structurally separated from history; empty metering set renders its explicit state.
- **Definition of done:** S3 shows every item PDF §7 lists for it; scope audit confirms no scoring, queueing or prediction formula exists in the diff.
- **Traces:** FR-006, 007, 008.

---

## M7 — Dispatch and Slots (S4)

- **Goal:** dispatch and slot visibility with mandatory explainability.
- **Features:** dispatch table with assignment, route, departure, target speed, slot, reason code, recommended-vs-issued state (FR-010); reason code and limiting variables surfaced (NFR-006); slot timeline per resource with window, holder, ETA, conflict status (FR-009); route highlight on the S1 map.
- **Files/components likely required:** `components/DispatchTable`, `components/SlotTimeline`, `components/ReasonCode`, `screens/DispatchSlots`.
- **Dependencies:** M4, M6.
- **Tests:** every dispatch row carries a reason code and a missing one renders as a defect marker rather than blank; recommended and issued are distinguishable; slots position correctly on the time axis; overlapping slots stay individually readable; conflict flagged visually and textually.
- **Definition of done:** S4 shows every item PDF §7 lists for it; every displayed command is present in the event log; scope audit confirms no assignment or route selection logic.
- **Traces:** FR-009, 010; NFR-006; OPS-002.

---

## M8 — Alerts and Safety Visualization

- **Goal:** the prioritized alert system and the system-mode machine.
- **Features:** alert list with all six FR-014 categories, deterministic severity-then-recency ordering; HMI-originated stale-data and comm-loss alerts derived from age; acknowledgment for advisory/operational alerts with log write (FR-015); non-acknowledgeable safety-critical alerts; five-state mode badge with logged transitions (FR-016).
- **Files/components likely required:** `components/AlertList`, `components/AlertItem`, `components/ModeBadge`, `state/alerts`, `state/systemMode`, `state/eventLog` (write points).
- **Dependencies:** M2 (freshness), M4.
- **Tests:** all six categories representable; ordering deterministic across shuffled input; acknowledging a safety-critical alert never clears its indicator; each acknowledgment writes one timestamped event with actor; every mode transition writes one event; severity readable in greyscale.
- **Definition of done:** alerts and modes correct across nominal, stale, comm-loss and violation scenarios; scope audit confirms the four Task 2 alert categories are consumed, not computed.
- **Traces:** FR-014, 015, 016; NFR-007, 008; OPS-003.

---

## M9 — Event Logging and Replay (S5)

- **Goal:** the audit trail and time-based replay, sharing one state path with live.
- **Features:** append-only event log with all S5-a categories; event timeline UI; recording of state history; `ReplayProvider` implementing `DataProvider`; replay controls (play, pause, scrub, speed); global replay-mode indication; commands and acknowledgments disabled during replay.
- **Files/components likely required:** `state/eventLog`, `components/EventTimeline`, `components/ReplayControls`, `providers/ReplayProvider`, `backend/app/logging/*`, `screens/EventReplay`.
- **Dependencies:** M8 (log write points), M2 (provider interface).
- **Tests:** scrubbing to time *t* reproduces the state recorded at *t*; every event category appears on the timeline; replay indication present on every screen; acknowledgment rejected while in replay; log is append-only.
- **Definition of done:** a recorded scenario replays through all previously built screens with no screen-level special-casing; PDF §12 items 6 and traceability obligations satisfied.
- **Traces:** FR-017; NFR-007; S5-a.

---

## M10 — Diagnostics (S6)

- **Goal:** the developer/tester and reviewer view of data-path truth.
- **Features:** per-component health table with state, `latency_ms`, `age_ms`, error code; link kinds V2V, V2I and LoRa (FR-013); message counts received and dropped (S6-a); data-freshness overview per message type; backend health; degraded-mode surfacing to S1.
- **Files/components likely required:** `components/DiagnosticsTable`, `components/FreshnessGrid`, `components/CommHealthTable`, `screens/Diagnostics`.
- **Dependencies:** M2, M8.
- **Tests:** all three link kinds render; `age_ms` visibly increases while the feed is stopped; degraded state propagates to S1 within one tick; counters increment against a known scripted message sequence.
- **Definition of done:** S6 shows every item PDF §7 lists for it; comm-loss scenario demonstrated end to end from S6 to the S1 status bar.
- **Traces:** FR-013; S6-a; NFR-003.

---

## M11 — Testing and Failure Scenarios

- **Goal:** prove the non-functional requirements rather than assert them.
- **Features:**
  - Feed-stop test: every affected value marked stale, mode forced to DEGRADED (NFR-012).
  - Disconnect/reconnect test: clean recovery, no duplicated or incoherent entities (NFR-004).
  - Scale test at 50 vehicles / 20 nodes (NFR-009).
  - Performance measurement and written report against `PLACEHOLDER_NFR001_REFRESH` (NFR-001). No threshold is invented.
  - Command-latency instrumentation and measured report against `PLACEHOLDER_NFR002_COMMAND_LATENCY`, isolated from actuation (NFR-002). No threshold is invented.
  - Greyscale/no-color-only audit across all screens (NFR-008).
  - Clean-machine setup verification (NFR-010).
  - Cross-screen failure-state sweep per the testing skill: connected, loading, error, stale, disconnected on every screen.
- **Files/components likely required:** `test/failure/*.spec`, `test/scale.spec`, `docs/verification/perf.md`, `docs/verification/latency.md`, latency instrumentation in the provider layer.
- **Dependencies:** M4 through M10.
- **Tests:** all of the above, as the deliverable itself.
- **Definition of done:** every NFR has either a passing test or a written measured report; NFR-001 and NFR-002 reports state the measured value against an unfilled configuration placeholder and record the requirement as unverifiable-as-specified (AMB-004), pending authoritative confirmation. Neither is marked passed.
- **Traces:** all twelve NFRs; PDF §12 item 3.

---

## M12 — Task 2 Integration Preparation

- **Goal:** make integration a provider swap.
- **Features:**
  - Published integration contract document derived from `task1-data-contract.md`, including all twenty extension items for Task 2 agreement.
  - Transport decision documented (WebSocket, MQTT or local bus) per TECH-001.
  - `LiveDataProvider` skeleton against the agreed transport, behind the same `DataProvider` interface, with reconnect and backoff.
  - Contract-conformance tests runnable against a Task 2 endpoint or a recorded capture.
  - Role gating enforced in the backend, not only in the UI (ROLE-001, NFR-011).
  - Version/compatibility handling for contract drift.
- **Files/components likely required:** `docs/integration/data-contract.md`, `docs/integration/transport-decision.md`, `frontend/src/providers/LiveDataProvider.ts`, `backend/app/transport/*`, `backend/app/auth/roles.py`, `test/contract/*.spec`.
- **Dependencies:** M2, M11.
- **Tests:** contract-conformance suite against a recorded or stub Task 2 feed; provider swap leaves every screen unchanged; role gating rejects unauthorized actions server-side; reconnect and backoff behave.
- **Definition of done:** the HMI runs against a stub live feed with no screen changed; transport choice documented; all extension items either agreed with Task 2 or listed as open.
- **Traces:** TECH-001, ROLE-001, NFR-004, NFR-011; the Task 2 dependency trace in the traceability matrix.

---

## M13 — Optional Laptop Computer Vision

- **Status:** OPTIONAL. Started only after M1 through M12 are verified complete (CLAUDE.md).
- **Goal:** a non-safety-critical perception aid displayed in the HMI.
- **Features:** camera or recorded-video ingestion (CV-001); visibility proxy plus confidence (CV-002); optional detector (CV-003); latency measurement (CV-004); graceful failure with explicit unavailable status (CV-005); publication with timestamp, source ID and confidence (CV-006); HMI CV panel with frame, estimate and overlays, labelled non-authoritative (FR-020, OPS-004).
- **Files/components likely required:** `cv/ingest.py`, `cv/visibility.py`, `cv/detect.py`, `cv/publish.py`, `frontend/src/components/CvPanel.tsx`.
- **Dependencies:** M12.
- **Tests:** camera-failure sets status unavailable and no stale frame is presented as current; published payload validates against `CVResult`.
- **Definition of done:** demonstrated on test footage, **or** explicitly marked Not Implemented per PDF §11/§12 — which does not affect Task 1 completion.
- **Constraint:** laptop-side only; no ESP32 inference.

---

## Milestone Dependency Order

```
M1 Foundation
  └─ M2 Schemas/Contracts
       └─ M3 Mock Data & Scenarios
            └─ M4 Operations Overview (S1)
                 ├─ M5 Vehicle Detail (S2)
                 ├─ M6 Bottleneck & Queue (S3)
                 │    └─ M7 Dispatch & Slots (S4)
                 └─ M8 Alerts & Modes
                      └─ M9 Event Log & Replay (S5)
                           └─ M10 Diagnostics (S6)
                                └─ M11 Testing & Failure Scenarios
                                     └─ M12 Task 2 Integration Prep
                                          └─ M13 Optional CV
```

M5, M6 and M8 can proceed in parallel after M4; all three converge before M9.

---

## Mandatory-Requirement Coverage by Milestone

| Milestone | Mandatory requirements delivered |
|---|---|
| M1 | NFR-005, NFR-010, NFR-011 (partial), NFR-008 (tokens), OPS-001 |
| M2 | NFR-003, NFR-012 (state layer) |
| M3 | FR-019, NFR-009 (data) |
| M4 | FR-001, 002, 006, 011, 012, 014 (display), 016 (display), 018 |
| M5 | FR-003, 004, 005, S2-a, S2-b |
| M6 | FR-006, 007, 008 |
| M7 | FR-009, 010, NFR-006, OPS-002 |
| M8 | FR-014, 015, 016, NFR-007, OPS-003 |
| M9 | FR-017, S5-a |
| M10 | FR-013, S6-a |
| M11 | NFR-001, 002, 004, 008, 009, 012 (verified) |
| M12 | TECH-001, ROLE-001, NFR-011 (complete) |
| M13 | (optional only) FR-020, CV-001..006, OPS-004 |

All 41 mandatory requirements are assigned. FR-020, OPS-004 and CV-001..006 are the
optional set and are confined to M13.
