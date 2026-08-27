# Task 1 — HMI Requirements Analysis

**Source of truth:** `docs/FOG_ORCHESTRATOR_Task1_HMI_Requirements.pdf`
("Task 1 — HMI & Laptop Vision Requirements", SRS, FOG-ORCHESTRATOR 2.0)
**Governing rules:** `CLAUDE.md`, `.claude/skills/scope-control`, `.claude/skills/task1-architecture`, `.claude/skills/testing`
**Phase:** requirements analysis only. No application code.

> **AMB-012 CLOSED.** `docs/FOG_ORCHESTRATOR_Task1_HMI_Requirements.pdf` is the canonical
> path and the sole Task 1 specification. It is the document analysed here, and
> `CLAUDE.md` names it as authoritative.

**Baseline:** Planning Baseline v1.3 (frozen). Changes governed by `requirements/DECISIONS.md`.

---

## 0. Scope Statement

Task 1 delivers the operator/control-room HMI. It visualizes fleet state, road state,
fog/visibility, safety envelopes, bottlenecks, dispatch decisions, communication health
and alerts. It is **not** the safety governor and **does not compute** any value it displays.

Per PDF §2, CLAUDE.md and the scope-control skill, the following are **out of scope for
this repository** and are consumed as *externally supplied inputs*:

| Value | Owner |
|---|---|
| `v_safe`, `h_safe`, `risk_level`, `active_constraint` | Task 2 (Digital Twin) |
| `bottleneck_score`, `criticality`, `lambda_vph`, `mu_vph`, predicted queue | Task 2 |
| dispatch assignment, route, departure slot, target speed, reason code | Task 2 |
| vehicle physics, fog physics, friction estimation | Task 2 |
| visibility forecast + uncertainty band | Task 2 |
| arrival plan / metering and hold decisions | Task 2 |

Task 1 defines the **interface** for each and renders mock data until Task 2 connects.

### Screen abbreviations (PDF §7)
`S1` Operations Overview · `S2` Vehicle Detail · `S3` Bottleneck & Queue ·
`S4` Dispatch & Slots · `S5` Event/Replay · `S6` Diagnostics · `S7` Scenario/Dev controls
(S7 is not enumerated in §7 but is required by HMI-FR-019 — see AMB-006.)

### Verification method codes
`T` automated test · `D` demonstration/scenario walkthrough · `I` inspection/code review ·
`A` analysis/measurement

Per the testing skill, every feature must additionally be verified against: connected,
loading, error, stale-data and disconnected states; data freshness; alert visibility; and
actual-versus-safe value distinction. These are folded into the acceptance criteria below.

---

## 1. Functional Requirements (PDF §5)

FR-001..FR-019 are **MANDATORY**. FR-020 is **OPTIONAL**.

---

### HMI-FR-001 — Live system overview
- **Source:** PDF §5, HMI-FR-001
- **Status:** Mandatory
- **Screen:** S1 (persistent header across all screens)
- **Statement:** HMI shall show current system mode, timestamp, connectivity status, active alerts, and fleet count.
- **Required input data:** `SystemHealth.system_mode`, state timestamp, `Health[]` connectivity roll-up, `Alert[]` active set, `VehicleState[]` count.
- **Expected behavior:** Persistent status bar renders mode badge (FR-016 enum), current data timestamp *and* its age, aggregate link state, unacknowledged alert counts by severity, and active vehicle count. Updates every state tick.
- **Acceptance criteria:**
  1. All five elements visible without scrolling on S1.
  2. Mode badge changes within one state tick of a mode change in the provider.
  3. Fleet count equals vehicle count in normalized state.
  4. Timestamp shown with age; enters stale presentation per NFR-003.
  5. Loading and disconnected states render explicitly, not as empty values.
- **Verification:** T (state to render assertions), D

### HMI-FR-002 — Mine/road map
- **Source:** PDF §5, HMI-FR-002
- **Status:** Mandatory
- **Screen:** S1
- **Statement:** HMI shall render the graph-based digital mine map with road segments, grades, intersections, switchbacks, shovels, crushers and vehicle positions.
- **Required input data:** `MineTopology` (nodes, edges, node kinds, geometry), `RoadState[]` per segment, `VehicleState` position.
- **Expected behavior:** 2-D graph render. Node glyphs differ by kind (shovel, crusher, intersection, switchback, waypoint). Segments carry grade indication. Vehicles drawn at `x/y` or interpolated along `segment_id`. Selecting a vehicle or node navigates to S2/S3.
- **Acceptance criteria:**
  1. Every node kind in the statement has a distinct glyph distinguished by shape *and* label, not color alone (NFR-008).
  2. Every vehicle in state appears exactly once.
  3. Renders at least 20 nodes and 50 vehicles (NFR-009) without visual collapse.
  4. Topology is data-driven; no hard-coded map inside a component (architecture skill).
- **Verification:** T (render count assertions), D, I

### HMI-FR-003 — Vehicle state
- **Source:** PDF §5, HMI-FR-003
- **Status:** Mandatory
- **Screen:** S2 (summary row on S1)
- **Statement:** For each vehicle show ID, position/segment, speed, safe speed, headway, risk state, friction estimate (with confidence) and communication state.
- **Required input data:** `VehicleState`, `SafetyState`, `RoadState` of the occupied segment.
- **Expected behavior:** Per-vehicle panel with all eight fields. Friction shown as estimate plus/minus `friction_sigma`. Communication state derived from `comm_confidence` plus `Health` age.
- **Acceptance criteria:**
  1. All eight fields present for the selected vehicle.
  2. Friction always rendered with its uncertainty, never bare.
  3. Missing or stale field renders an explicit "no data"/"stale" token — never blank, never a last-known value presented as current (NFR-012).
- **Verification:** T, D

### HMI-FR-004 — Safety envelope
- **Source:** PDF §5, HMI-FR-004
- **Status:** Mandatory
- **Screen:** S2 (indicator on S1)
- **Statement:** HMI shall clearly distinguish actual speed from `v_safe` and identify the active limiting constraint (visibility, friction, grade, braking/retarder, curve, site limit).
- **Required input data:** `SafetyState.actual_speed`, `.v_safe`, `.active_constraint`.
- **Expected behavior:** Envelope gauge showing actual vs safe speed and the margin between them, plus a named active-constraint chip. Exceedance (actual above `v_safe`) distinguished by shape/text, not color alone.
- **Acceptance criteria:**
  1. Actual and safe speed separately labelled and simultaneously readable.
  2. Active constraint rendered from the supplied enum verbatim; an unrecognised value renders as `UNKNOWN` rather than being dropped.
  3. Exceedance state discernible in greyscale.
  4. HMI performs **no** computation of `v_safe` (scope-control skill).
- **Verification:** T, I (confirm absence of calculation), D

### HMI-FR-005 — Headway monitoring
- **Source:** PDF §5, HMI-FR-005
- **Status:** Mandatory
- **Screen:** S2
- **Statement:** HMI shall show current headway and required `H_safe` for selected vehicle pairs; violation status shall be visible.
- **Required input data:** `SafetyState.h_safe`, current headway, lead-vehicle reference (see AMB-001).
- **Expected behavior:** Pair view: ego vehicle, lead vehicle, current headway, required `h_safe`, violation flag. Violation is supplied, or at most a direct comparison of two supplied numbers — never a headway model.
- **Acceptance criteria:**
  1. Both headway values shown with units.
  2. Violation indicated by text/icon state, not color alone.
  3. Lead-vehicle identity shown when supplied; absence rendered explicitly.
- **Verification:** T, D

### HMI-FR-006 — Bottleneck visualization
- **Source:** PDF §5, HMI-FR-006
- **Status:** Mandatory
- **Screen:** S3 (top-N marker on S1)
- **Statement:** HMI shall rank and visually mark bottlenecks using BottleneckScore and/or utilization, queue length and criticality.
- **Required input data:** `BottleneckState[]`.
- **Expected behavior:** Ranked list sorted by supplied `bottleneck_score` descending; corresponding map nodes marked. Ranking is a **sort of a supplied score**, never a recomputation of it.
- **Acceptance criteria:**
  1. List order matches descending `bottleneck_score`; tie-break is deterministic.
  2. Each row shows score, utilization, queue, criticality.
  3. Top-ranked bottleneck marked on the S1 map.
  4. No scoring formula exists anywhere in this repository (scope-control skill).
- **Verification:** T (sort order), I (no formula), D

### HMI-FR-007 — Queue monitoring
- **Source:** PDF §5, HMI-FR-007
- **Status:** Mandatory
- **Screen:** S3
- **Statement:** HMI shall display crusher/shovel/intersection queues, queue limits, arrival rate and service rate where available.
- **Required input data:** `BottleneckState.queue`, `.queue_max`, `.lambda_vph`, `.mu_vph`, optional supplied queue-trend series.
- **Expected behavior:** Per-node queue widget: current vs `queue_max`, lambda and mu in vph, and a queue trend when supplied. "Where available" means an absent field renders as "not supplied", not as zero.
- **Acceptance criteria:**
  1. Queue shown against its limit.
  2. Lambda and mu labelled with units.
  3. Absent lambda/mu renders as unavailable, never as `0`.
  4. Predicted queue trend, when supplied by Task 2, is visually distinguished from measured history; the HMI never extrapolates one.
- **Verification:** T, I, D

### HMI-FR-008 — Arrival-rate shaping
- **Source:** PDF §5, HMI-FR-008
- **Status:** Mandatory
- **Screen:** S3
- **Statement:** HMI shall show planned vs actual arrivals at critical nodes and any active metering/holding decision.
- **Required input data:** `ArrivalPlan` (planned arrivals per node), actual arrival counts, active metering/hold decisions — all Task 2 supplied (see AMB-002).
- **Expected behavior:** Planned vs actual arrival comparison per critical node, plus a list of active hold/metering decisions with affected vehicle, node and reason code.
- **Acceptance criteria:**
  1. Planned and actual series separately labelled on a shared axis.
  2. Active hold decisions list vehicle, node and reason code.
  3. Empty decision set renders an explicit "no active metering" state.
  4. HMI does not decide or compute metering (scope-control skill).
- **Verification:** T, I, D

### HMI-FR-009 — Slot reservation
- **Source:** PDF §5, HMI-FR-009
- **Status:** Mandatory
- **Screen:** S4
- **Statement:** HMI shall show switchback/intersection reservations, ETA, slot window, current holder, and conflict status.
- **Required input data:** `SlotState[]`, per-slot vehicle ETA.
- **Expected behavior:** Slot timeline per resource; each slot a `start_time` to `end_time` band labelled with holding vehicle, ETA and `status` (including conflict).
- **Acceptance criteria:**
  1. Slots positioned on a real time axis.
  2. Holder vehicle ID and status visible per slot.
  3. Conflicting slots flagged visually *and* textually.
  4. Overlapping slots on one resource remain individually readable.
  5. Conflict status is displayed as supplied; the HMI runs no slot solver.
- **Verification:** T, I, D

### HMI-FR-010 — Dispatch decision
- **Source:** PDF §5, HMI-FR-010
- **Status:** Mandatory
- **Screen:** S4
- **Statement:** HMI shall show recommended/issued vehicle assignment, route and departure slot with reason code.
- **Required input data:** `DispatchCommand[]`.
- **Expected behavior:** Dispatch table: vehicle, route, departure time, target speed, slot, reason code, command state (recommended vs issued), timestamp, `command_id`. Reason code mandatory per NFR-006.
- **Acceptance criteria:**
  1. Every dispatch row carries a non-empty reason code; a missing code renders as an explicit data-defect marker, not blank.
  2. Recommended and issued commands are distinguishable.
  3. Every displayed command also appears in the event log (NFR-007).
  4. HMI never selects or optimizes an assignment (scope-control skill).
- **Verification:** T, I, D

### HMI-FR-011 — Fog/visibility
- **Source:** PDF §5, HMI-FR-011
- **Status:** Mandatory
- **Screen:** S1, S2
- **Statement:** HMI shall show current visibility and, when available, forecast visibility with uncertainty/confidence band.
- **Required input data:** `RoadState.visibility_m`, `.visibility_sigma`, optional `VisibilityForecast` series.
- **Expected behavior:** Current visibility per segment plus, when supplied, a forecast series drawn with its uncertainty band and clearly labelled as forecast.
- **Acceptance criteria:**
  1. Current visibility shown with units and its sigma.
  2. Forecast band rendered when supplied; absence shows "forecast unavailable".
  3. Forecast visually separated from measurement.
  4. HMI performs no fog modelling or extrapolation (scope-control skill).
- **Verification:** T, I, D

### HMI-FR-012 — Road condition
- **Source:** PDF §5, HMI-FR-012
- **Status:** Mandatory
- **Screen:** S1 (map layer), S2
- **Statement:** HMI shall show friction estimate, road wetness/surface state and optional roughness state where available.
- **Required input data:** `RoadState.friction`, `.friction_sigma`, `.surface_state`, optional `.roughness`.
- **Acceptance criteria:**
  1. Friction and surface state shown for the selected segment.
  2. Optional roughness rendered only when supplied.
  3. Map supports a road-condition layer with a legend.
- **Verification:** T, D

### HMI-FR-013 — Communication health
- **Source:** PDF §5, HMI-FR-013
- **Status:** Mandatory
- **Screen:** S6 (indicator on S1, per-vehicle on S2)
- **Statement:** HMI shall show V2V/V2I/LoRa link state, packet freshness/age and degraded-mode state.
- **Required input data:** `Health[]` per component/link, `VehicleState.comm_confidence`.
- **Expected behavior:** Per-link rows: link kind, state, `latency_ms`, `age_ms`, error code. Degraded mode surfaces to the global status bar.
- **Acceptance criteria:**
  1. All three link kinds representable (V2V, V2I, LoRa).
  2. Age shown numerically and re-evaluated continuously, so it visibly grows when data stops.
  3. Degraded mode reaches S1 within one tick of detection.
- **Verification:** T, D (communication-loss scenario)

### HMI-FR-014 — Alerts
- **Source:** PDF §5, HMI-FR-014
- **Status:** Mandatory
- **Screen:** S1 (top alerts) plus a dedicated alert list
- **Statement:** HMI shall generate prioritized safety/operational alerts including unsafe speed, unsafe headway, bottleneck risk, communication loss, stale data and slot conflict.
- **Required input data:** `Alert[]` supplied by Task 2, plus HMI-local alerts for **data-path conditions only** — stale data and communication loss, both properties the HMI itself owns.
- **Expected behavior:** Priority-ordered alert list; each alert carries severity, category, source, timestamp, message, acknowledgment state. All six named categories representable.
- **Acceptance criteria:**
  1. All six categories exist in the alert category enum.
  2. Ordering by severity then recency is deterministic.
  3. Severity conveyed by text/icon plus color (NFR-008).
  4. Stale-data and comm-loss alerts raised by the HMI from timestamp age; the other four originate from supplied state, never from an HMI-side safety or bottleneck calculation (scope-control skill).
- **Verification:** T (ordering and generation), I, D

### HMI-FR-015 — Alert acknowledgment
- **Source:** PDF §5, HMI-FR-015
- **Status:** Mandatory
- **Screen:** alert list (S1), S5 log
- **Statement:** Operators shall be able to acknowledge applicable advisory/operational alerts; safety-critical local protection shall not depend on acknowledgment.
- **Required input data:** `Alert.acknowledgeable`, operator identity/role.
- **Expected behavior:** Acknowledge action on advisory/operational alerts. Acknowledgment changes display state and writes a log event. Safety-critical alerts are either non-acknowledgeable or acknowledgment is explicitly display-only.
- **Acceptance criteria:**
  1. Acknowledging never removes or suppresses a safety-critical condition indicator.
  2. Each acknowledgment produces a timestamped log event with operator identity (NFR-007).
  3. Role permissions per §4 gate the action.
- **Verification:** T, I, D

### HMI-FR-016 — System modes
- **Source:** PDF §5, HMI-FR-016
- **Status:** Mandatory
- **Screen:** global status bar
- **Statement:** HMI shall show NORMAL, CAUTION, DEGRADED, LOCAL-SAFE and STOP/UNSAFE modes.
- **Required input data:** `SystemHealth.system_mode` (supplied), with DEGRADED additionally assertable by the HMI on data-path loss (NFR-012).
- **Acceptance criteria:**
  1. All five modes renderable and distinguishable without color alone.
  2. Every mode transition logged (NFR-007).
  3. Loss of the data feed forces at least DEGRADED display regardless of the last supplied mode.
- **Verification:** T, D

### HMI-FR-017 — Replay
- **Source:** PDF §5, HMI-FR-017
- **Status:** Mandatory
- **Screen:** S5
- **Statement:** HMI shall support time-based replay of logged simulation/HIL telemetry for post-event analysis.
- **Required input data:** persisted timestamped state/event history.
- **Expected behavior:** Replay controls (play/pause, scrub, speed) drive the *same normalized application state* the live path drives, so every screen replays. Replay mode is unmistakably indicated and cannot be confused with live.
- **Acceptance criteria:**
  1. Scrubbing to time *t* reproduces the state recorded at *t*.
  2. Replay mode flagged globally.
  3. No command may be issued while in replay.
  4. Replay is implemented as a third provider behind the same interface, not as a parallel UI (architecture skill).
- **Verification:** T (state-at-t equality), D

### HMI-FR-018 — KPI dashboard
- **Source:** PDF §5, HMI-FR-018
- **Status:** Mandatory
- **Screen:** S1 / dedicated KPI panel
- **Statement:** HMI shall show throughput, cycle time, queue length, utilization, stops, safety-envelope violations and recovery time.
- **Required input data:** `KpiSnapshot` supplied by Task 2 (see AMB-003).
- **Acceptance criteria:**
  1. All seven KPIs present and labelled with units.
  2. Unsupplied KPI renders as unavailable, never as `0`.
  3. KPI values displayed as supplied; the HMI does not derive them (AMB-003).
- **Verification:** T, I, D

### HMI-FR-019 — Scenario controls
- **Source:** PDF §5, HMI-FR-019
- **Status:** Mandatory
- **Screen:** S7 (developer/test view)
- **Statement:** Developer/test view shall permit loading named fog, friction, grade, fleet-density and communication-loss scenarios.
- **Required input data:** `ScenarioDescriptor[]` (named mock scenarios).
- **Expected behavior:** Scenario picker loads a named scenario into the mock provider. All five named scenario families exist. Restricted to the developer/tester role.
- **Acceptance criteria:**
  1. Named scenarios exist for fog, friction, grade, fleet-density and communication loss.
  2. Loading a scenario re-drives the whole HMI through normalized state; no component reads a scenario file directly (architecture skill).
  3. Active scenario name displayed.
- **Verification split (MID-D):** criteria 1 and 2 are verified at **M3** (scenario
  registry, descriptors and loading); criterion 3 requires the React scenario picker and is
  verified at **M4**. FR-019 is therefore *partially* verified at M3 exit.
- **Verification:** T, I, D

### HMI-FR-020 — CV integration
- **Source:** PDF §5, HMI-FR-020; §8
- **Status:** **OPTIONAL** — deferred until all mandatory HMI work is verified (CLAUDE.md)
- **Screen:** dedicated CV panel
- **Statement:** If CV is implemented, HMI shall display camera frame, visibility estimate/confidence and detected obstacle/road-state overlays without placing inference on the ESP32.
- **Required input data:** `CVResult`.
- **Acceptance criteria (only if implemented):**
  1. Frame, visibility proxy, confidence and detections displayed with source ID and timestamp.
  2. CV output labelled non-authoritative relative to the physics/safety values (OPS-004).
  3. CV-unavailable state rendered explicitly; stale CV output never shown as current (CV-005).
- **Verification:** D, or marked N/A per §11.

---

## 2. Non-Functional Requirements (PDF §6)

### HMI-NFR-001 — Performance
- **Status:** Mandatory. **Threshold absent from the specification** — see AMB-004.
- **Threshold:** `PLACEHOLDER_NFR001_REFRESH` — configuration placeholder, **requires authoritative confirmation**. No value is assumed or invented here.
- **Behavior:** the HMI measures and reports its own state-tick and render performance. Until the placeholder is filled, the requirement is *measurable but not passable*: M11 reports the measured value and records the requirement as unverifiable-as-specified.
- **Verification:** A (measure and report), T (render budget, once a threshold exists)

### HMI-NFR-002 — Command latency
- **Status:** Mandatory. **Threshold absent from the specification** — the printed cell reads only "…conditions; measured separately from vehicle actuation latency." See AMB-004.
- **Threshold:** `PLACEHOLDER_NFR002_COMMAND_LATENCY` — configuration placeholder, **requires authoritative confirmation**. No value is assumed or invented here.
- **Behavior:** HMI measures and reports its own command round-trip latency, isolated from vehicle actuation latency. Scope of "command" is bounded by PAD-B and AMB-008 — currently acknowledgement round-trip only.
- **Verification:** A (measured value reported), I

### HMI-NFR-003 — Data freshness
- **Status:** Mandatory
- **Statement:** Each live datum shall carry timestamp/source age; stale data shall be visually flagged after a configurable timeout.
- **Threshold:** `PLACEHOLDER_NFR003_STALE_TIMEOUT_MS` — the specification mandates a *configurable* timeout but states **no value**. Configuration placeholder under PAD-G, **requires authoritative confirmation** (AMB-014). No value is assumed or invented. Tests inject the threshold, so the freshness mechanism is verifiable independent of the real value.
- **Acceptance:** Every displayed datum resolves to a timestamp and age; the staleness threshold is configuration, not a literal inside a component; stale rendering is visually distinct.
- **Verification:** T (age to stale transition, with an injected threshold), D

### HMI-NFR-004 — Availability
- **Status:** Mandatory (worded "should" in the PDF; treated as mandatory here)
- **Statement:** HMI should recover automatically after temporary backend/reconnect interruption without corrupting state.
- **Acceptance:** After a simulated disconnect/reconnect the HMI resumes with no stale-as-current values and no duplicated or incoherent entities.
- **Verification:** T (reconnect test), D

### HMI-NFR-005 — Safety separation
- **Status:** Mandatory
- **Statement:** Loss or crash of HMI shall not disable Tier-1 vehicle safety.
- **Acceptance:** No control path in this repository is required for vehicle safety; all commands are advisory. Verified by architecture inspection.
- **Verification:** I, D

### HMI-NFR-006 — Explainability
- **Status:** Mandatory
- **Statement:** Every dispatch/risk decision shown shall include a concise reason code and key limiting variables.
- **Acceptance:** Dispatch rows carry `reason_code`; risk/safety displays carry `active_constraint`. Codes rendered as supplied, expanded to human text where a code map exists.
- **Verification:** T, I, D

### HMI-NFR-007 — Traceability
- **Status:** Mandatory
- **Statement:** All issued/received commands and mode transitions shall be timestamped and logged.
- **Acceptance:** Command receipt, command issue, acknowledgment and every mode transition each produce a persisted timestamped event visible in S5.
- **Verification:** T, D

### HMI-NFR-008 — Usability
- **Status:** Mandatory
- **Statement:** Critical information shall be readable at a glance; avoid relying on color alone for safety state.
- **Acceptance:** Every safety-state indicator carries a non-color channel (text, icon or shape); verified in greyscale.
- **Verification:** I (greyscale review), T (each state exposes a text/icon token)

### HMI-NFR-009 — Scalability
- **Status:** Mandatory
- **Statement:** Prototype HMI shall support at least 50 simulated vehicles and 20 physical/logical road nodes.
- **Acceptance:** A 50-vehicle / 20-node scenario renders correctly and remains interactive.
- **Verification:** T (scale scenario), A

### HMI-NFR-010 — Portability
- **Status:** Mandatory
- **Statement:** Laptop deployment shall work from documented setup steps and use open-source tooling where practical.
- **Acceptance:** README setup steps reproduce a running HMI on a clean machine.
- **Verification:** D (clean-machine run), I

### HMI-NFR-011 — Security baseline
- **Status:** Mandatory
- **Statement:** Prototype communications shall include authentication/configurable access controls where supported; **no hard-coded credentials in source**.
- **Acceptance:** No credential literal in the repository; endpoints and secrets come from configuration/environment; role gating per §4 is enforced server-side, not merely hidden in the UI.
- **Verification:** T (secret scan), I

### HMI-NFR-012 — Recovery
- **Status:** Mandatory
- **Statement:** If backend data stops, HMI shall enter DATA-STALE/DEGRADED indication rather than freezing values silently.
- **Acceptance:** With the feed stopped, within the configured timeout every affected value is marked stale and global mode shows DEGRADED. No value continues to read as current.
- **Verification:** T, D (feed-stop scenario)

---

## 3. Screen Requirements (PDF §7)

| Screen | Mandatory content | Covering FRs |
|---|---|---|
| S1 Operations Overview | Mine map, vehicles, active bottleneck, current fog state, top alerts, throughput, system mode | FR-001,002,006,011,012,014,016,018 |
| S2 Vehicle Detail | Speed, safe speed, headway, risk, friction, grade, communication, active constraint, recent trend | FR-003,004,005,011,012,013 + S2-a, S2-b |
| S3 Bottleneck & Queue | Crusher/shovel/intersection utilization, arrival/service rates, queue lengths, predicted queue trend | FR-006,007,008 |
| S4 Dispatch & Slots | Truck assignment, departure time, route, switchback/intersection slot timeline, reason codes | FR-009,010 |
| S5 Event/Replay | Timeline of fog, alerts, commands, queue changes, violations and recovery | FR-017, NFR-007 |
| S6 Diagnostics | Data freshness, sensor/telemetry status, backend health, message counts, latency | FR-013, NFR-003 |
| S7 Scenario/Dev (implied) | Named scenario loading | FR-019 |

**Derived requirements from §7 content not stated in §5:**
- **S2-a (Mandatory):** S2 shall display road **grade** for the vehicle's segment.
- **S2-b (Mandatory):** S2 shall display a **recent trend** history for the vehicle's key values.
- **S5-a (Mandatory):** S5 timeline shall include fog changes, alerts, commands, queue changes, violations and recovery as distinct event categories.
- **S6-a (Mandatory):** S6 shall display **message counts** and **latency** per component.

---

## 4. User Roles and Permissions (PDF §4)

| Role | Permissions the HMI must enforce |
|---|---|
| Vehicle operator | View vehicle page; acknowledge warnings |
| Control-room operator | Fleet/road view; dispatch recommendations; acknowledge/override **non-safety advisory** actions |
| Safety/engineering reviewer | Read-only analytics, logs, scenario playback |
| Developer/tester | Diagnostic panels; simulator/scenario controls |

**ROLE-001 (Mandatory, derived):** The HMI shall gate actions by role; override shall never
be offered for safety-critical items.

---

## 5. Operational Concept Constraints (PDF §3)

- **OPS-001 (Mandatory):** HMI is supervisory; it does not replace the Tier-1 local physics safety governor. Traces to NFR-005.
- **OPS-002 (Mandatory):** Displayed commands are recommendations/advisories; the vehicle controller enforces local limits. Traces to FR-010.
- **OPS-003 (Mandatory):** On loss of central communication the HMI shall indicate degraded mode. Traces to FR-016, NFR-012.
- **OPS-004 (Mandatory):** CV is an information source and shall not override physics constraints. Traces to FR-020.

---

## 6. Optional CV Requirements (PDF §8) — all OPTIONAL

| ID | Requirement | Acceptance | Verification |
|---|---|---|---|
| CV-001 | Camera ingestion | Read live webcam/IP stream or recorded video | D |
| CV-002 | Visibility estimate | Interpretable visibility proxy plus confidence | D |
| CV-003 | Obstacle/vehicle detection | Detect configured classes in test footage | D |
| CV-004 | Latency | Measured on the test laptop and reported (**threshold missing from PDF**, AMB-004) | A |
| CV-005 | Graceful failure | Camera failure sets CV status unavailable; stale output never silently treated as current | T, D |
| CV-006 | Integration | Publish to HMI/backend with timestamp, source ID and confidence | T, D |

Per CLAUDE.md, CV is attempted only after mandatory HMI completion; per §11 it may be
marked N/A without affecting Task 1 completion.

---

## 7. Technology Baseline (PDF §10) — constraints

- Frontend: web-based HMI preferred (React/HTML/JS; Streamlit acceptable if time-constrained). The architecture skill fixes the choice as **React**.
- Backend/API: Python service (FastAPI/Flask) integrating with the digital-twin process.
- Real-time transport: WebSocket/MQTT/local bus — **final choice shall be documented**,
  giving **TECH-001 (Mandatory documentation obligation)**.
- Charts: Plotly/Matplotlib-compatible exported data acceptable.
- CV: laptop-side Python/OpenCV; no ESP32 inference.

---

## 8. Task 1 Completion Definition (PDF §12)

1. Mandatory HMI screens implemented and connected to live/simulated data.
2. All mandatory HMI functional requirements verified.
3. Stale-data and communication-loss behavior demonstrated.
4. Safety-critical values (`v_safe`, `h_safe`, risk, active constraint) visible and traceable.
5. Bottleneck, queue, arrival shaping and slot reservation visible.
6. Logs and replay available.
7. Optional CV separately marked Complete / Partial / Not Implemented.

---

## 9. Requirement Count Summary

| Class | Count | Mandatory | Optional |
|---|---|---|---|
| Functional (FR) | 20 | 19 | 1 (FR-020) |
| Non-functional (NFR) | 12 | 12 | 0 |
| CV | 6 | 0 | 6 |
| Derived (S2-a, S2-b, S5-a, S6-a, ROLE-001, OPS-001..004, TECH-001) | 10 | 10 | 0 |
| **Total mandatory** | | **41** | |
| **Total optional** | | | **7** |
