# Task 1 — Risks and Ambiguities

Each item states the issue, its impact, the **assumption made** so planning could proceed,
and what decision is needed. Nothing here blocks the requirements phase; several items
block specific milestones and are marked accordingly.

**Baseline:** Planning Baseline v1.3 (frozen). Changes governed by `requirements/DECISIONS.md`.

**Severity:** `HIGH` = blocks or invalidates a milestone · `MEDIUM` = causes rework ·
`LOW` = cosmetic or documentation only.

---

## A. Specification Ambiguities

### AMB-001 — `h_safe` units and headway source — HIGH
FR-005 requires "current headway and required `H_safe`". PDF §9 `SafetyState` supplies
`h_safe` but **not current headway**, and does not state whether `h_safe` is a distance
(metres) or a time gap (seconds). Neither is a lead-vehicle reference defined, though
FR-005 speaks of "vehicle pairs".

- **Impact:** FR-005 cannot be rendered correctly or tested against a real value. A units
  mismatch would display a plausible but wrong safety number — the worst failure class on
  a safety screen.
- **Assumption:** `h_safe` in metres; `headway_current` and `lead_vehicle_id` added as
  contract extensions E-04, supplied by Task 2.
- **Decision needed:** confirm units; confirm Task 2 supplies current headway and the pair
  partner. **Blocks M5.**

### AMB-002 — No arrival-plan message — HIGH
FR-008 requires planned vs actual arrivals and active metering/holding decisions. PDF §9
defines no message carrying any of it.

- **Impact:** FR-008 has no data source. Worse, "planned arrivals" is precisely the kind of
  value Task 1 must not compute — deriving it locally would implement arrival shaping,
  a Task 2 responsibility.
- **Assumption:** `ArrivalPlan` (contract extension E-10) is supplied by Task 2.
- **Decision needed:** confirm Task 2 will produce it, and that "planned arrivals" means a
  schedule rather than a live rate target. **Blocks M6.**

### AMB-003 — KPI provenance — MEDIUM
FR-018 names seven KPIs. PDF §9 defines no KPI message, and §11 does not say who computes
them. Throughput, cycle time and recovery time are all derivable from a telemetry history
that the HMI happens to hold.

- **Impact:** the tempting implementation — compute KPIs in the HMI from recorded history —
  is a scope violation: it means Task 1 computing operational metrics over a simulation it
  does not own. Getting this wrong is a silent boundary breach.
- **Assumption:** `KpiSnapshot` (E-16) is supplied by Task 2; the HMI displays only.
- **Decision needed:** confirm Task 2 owns KPI computation. If the team decides the HMI
  should aggregate them, that is an **explicit scope grant** and must be recorded, not
  assumed. **Affects M4 and M11.**

### AMB-004 — NFR-001 and NFR-002 thresholds are missing from the specification — HIGH
The PDF's NFR-001 (Performance) requirement cell is **empty in the document's text layer**,
and NFR-002 (Command latency) begins mid-sentence: "…conditions; measured separately from
vehicle actuation latency." CV-004's latency threshold is likewise absent. The numbers were
lost in the document, not in extraction — no numeric threshold exists anywhere in the file
for these three rows.

- **Impact:** three mandatory-to-verify requirements have no pass criterion. They can be
  *measured* but not *passed or failed*.
- **Assumption:** **none. No value is invented.** Each missing threshold is carried as a
  named configuration placeholder requiring authoritative confirmation:
  `PLACEHOLDER_NFR001_REFRESH`, `PLACEHOLDER_NFR002_COMMAND_LATENCY`,
  `PLACEHOLDER_CV004_LATENCY`. M11 measures and reports actual values against each
  placeholder without asserting a pass or fail.
- **Decision needed:** obtain the intended thresholds, or a corrected specification. Until
  then these requirements are measurable but not passable, and M11 records them as
  unverifiable-as-specified. **Blocks NFR-001 and NFR-002 sign-off** (not implementation —
  see PAD-G).

### AMB-005 — Vehicle mode versus system mode — MEDIUM
FR-016 lists five modes for the system. PDF §9 `VehicleState.mode` is unenumerated. It is
unclear whether a vehicle uses the same five values, a different set, or whether system
mode is an aggregate of vehicle modes.

- **Impact:** if system mode is an *aggregate*, computing it in the HMI is a judgement about
  fleet safety state — arguably Task 2's. If it is supplied, no issue.
- **Assumption:** system mode is **supplied** by Task 2; the HMI only forces at least
  DEGRADED on data-path loss (its own concern). Vehicle mode reuses the same enum plus
  `UNKNOWN`.
- **Decision needed:** confirm the vehicle mode value set and that system mode is supplied.
  **Affects M8.**

### AMB-006 — No screen defined for scenario controls — LOW
FR-019 requires a developer/test view for scenario loading. PDF §7 enumerates only S1..S6
and does not include it.

- **Impact:** minor; a mandatory FR has no listed screen.
- **Assumption:** an S7 developer/scenario view, role-restricted to developer/tester.
- **Decision needed:** confirm S7 is acceptable, or that scenario controls belong inside S6
  Diagnostics. **Affects M3.**

### AMB-007 — Enum value sets not specified — MEDIUM
`risk_level`, `criticality`, surface/wetness state and the reason-code vocabulary are all
named by the PDF but never enumerated.

- **Impact:** the HMI must map each to a visual state. Guessed bands become wrong-looking
  displays after integration, and reason codes with no vocabulary cannot be expanded into
  the human text NFR-006 implies.
- **Assumption:** four-level bands for risk and criticality, an `UNKNOWN` member on every
  enum, and reason codes rendered verbatim when unmapped.
- **Decision needed:** obtain the value sets and the reason-code vocabulary from Task 2.
  **Affects M5, M6, M7.**

### AMB-008 — May the HMI issue commands, or only display them? — HIGH
FR-010 says "recommended/issued". NFR-002 measures **command latency**. NFR-007 logs
"issued/received commands". §4 grants the control-room operator "dispatch recommendations"
and "acknowledge/override non-safety advisory actions". Together these imply an outbound
command path — but PDF §12 (completion) and the CLAUDE.md responsibility list mention only
visualization and acknowledgment.

- **Impact:** large. An outbound command path changes the backend, the security model
  (NFR-011), the role model (ROLE-001) and the safety argument (NFR-005). Building it
  speculatively is waste; discovering it is required at M12 is rework.
- **Assumption:** **Task 1 is display plus acknowledgment only.** The provider interface
  exposes `sendAcknowledgement` and nothing else. `DispatchCommand.state` distinguishes
  recommended from issued for *display*, with issuance performed elsewhere.
- **Decision needed:** confirm before M7. If the HMI must issue commands, M7 and M12 both
  expand and an operator-authorization design is needed. **Blocks M7 scope.**

### AMB-009 — "Override" scope for the control-room operator — MEDIUM
§4 permits the control-room operator to "acknowledge/override non-safety advisory actions".
Override is not defined anywhere else in the specification, and no FR describes it.

- **Impact:** an undefined mutating capability adjacent to safety displays.
- **Assumption:** override is **out of scope** for Task 1 until specified; only
  acknowledgment is implemented. Safety-critical items are never overridable in any case.
- **Decision needed:** define override, or confirm its exclusion. **Affects M8, M12.**

### AMB-010 — Replay data source and retention — MEDIUM
FR-017 requires replay of "logged simulation/HIL telemetry" but does not say who records it,
where it is stored, or for how long.

- **Impact:** determines whether the HMI backend owns a recording store (a real persistence
  design) or merely reads Task 2's logs.
- **Assumption:** the HMI backend records the normalized state and event stream it receives,
  with a bounded retention window; it does not depend on Task 2 log files.
- **Decision needed:** confirm ownership and retention. **Affects M9.**

### AMB-011 — Mine topology source — MEDIUM
FR-002 requires a graph-based mine map. PDF §9 defines no topology message.

- **Impact:** without a supplied topology, the map is either hard-coded (violating the
  architecture skill's data-driven rule) or invented.
- **Assumption:** `MineTopology` (E-17) is supplied by Task 2 or from a shared static
  configuration; a mock topology is used until then.
- **Decision needed:** confirm the owner and format of the topology. **Affects M4, M12.**

### AMB-012 — Specification file name — **CLOSED**
Confirmed by the project owner and by directory inspection: the authoritative Task 1
specification is `docs/FOG_ORCHESTRATOR_Task1_HMI_Requirements.pdf`, and there is no second
Task 1 specification.

- **Resolution:** that path is now the canonical citation. `docs/CLAUDE.md` (since
  relocated to the repository root as `CLAUDE.md`) carries an
  "Authoritative Specification" section naming it as the single source of truth, and every
  reference across the five planning documents uses it verbatim. No stale filename remains
  anywhere in the repository.
- **Status:** CLOSED. No further action.

### AMB-013 — Skill directory name typo — **RESOLVED**
`.claude/skills/scope-controlclear/` contained a `SKILL.md` whose frontmatter declared
`name: scope-control`, confirming the directory name was a typo.

- **Resolution:** directory renamed to `.claude/skills/scope-control/`. No duplicate was
  created — the target path was checked as absent before the rename, and the rename moved
  the existing directory rather than copying it. References in the planning documents were
  updated to the corrected path.
- **Observed during inspection, not an error:** five further skill directories exist and
  are **empty** (no `SKILL.md`): `hmi-frontend`, `mock-scenarios`, `realtime-data`,
  `replay`, `safety-visualization`. These are placeholders, not naming errors, so they were
  left untouched. If they are intended to hold skills, they need content before they affect
  anything; if they are accidental, they can be removed. **Decision needed (LOW).**

### AMB-014 — NFR-003 staleness timeout has no authoritative value — HIGH
HMI-NFR-003 requires that stale data be "visually flagged after a configurable timeout",
but the specification never states what that timeout is. Discovered during the M2 proposal
review and registered in Planning Baseline v1.2.

- **Impact:** this is the fourth unfilled numerical threshold, alongside NFR-001, NFR-002
  and CV-004 (AMB-004) — and the most consequential of the four. The other three affect
  sign-off only. This one changes *what an operator sees*: set too long, genuinely stale
  safety data reads as current, which is precisely the failure NFR-012 exists to prevent;
  set too short, every value flickers stale and the flag stops meaning anything.
- **Assumption:** **none. No value is invented.** The threshold is carried as the named
  configuration placeholder `PLACEHOLDER_NFR003_STALE_TIMEOUT_MS` under PAD-G. No
  production default is authoritative, and the placeholder is marked as such at its
  definition site (MAD-D).
- **Why this does not block M2:** the freshness *mechanism* is fully testable regardless,
  because tests inject the threshold rather than depending on its real value. What cannot
  be done without an authoritative value is claiming NFR-003 verified in production terms.
- **Decision needed:** the specification owner supplies the value, or confirms a value for
  the prototype. Worth asking at the same time whether a single global timeout suffices, or
  whether message classes need different ones — visibility and dispatch data plausibly age
  at very different rates, but the specification does not say and this analysis does not
  assume. **Blocks NFR-003 sign-off, not implementation.**

---

## B. Integration Risks

### RISK-I1 — The data contract is largely an extension of the PDF — HIGH
Twenty of the contract's message groups or fields (E-01..E-20) are **not** in PDF §9. Seven
whole messages are absent from the specification: `VisibilityForecast`, `ArrivalPlan`,
`Alert`, `EventRecord`, `SystemHealth`, `KpiSnapshot`, `MineTopology`.

- **Impact:** if Task 2 designs its output independently, the normalization layer absorbs a
  wide mismatch, or screens are rebuilt.
- **Mitigation:** publish the contract to the Task 2 team **now**, in the requirements
  phase, rather than at M12. Treat every unagreed extension as a live risk. The normalization
  layer exists precisely to absorb the residual difference.

### RISK-I2 — Transport not chosen — MEDIUM
PDF §10 offers WebSocket, MQTT or a local bus and requires only that the choice be
documented (TECH-001).

- **Impact:** each implies different reconnect, ordering and backpressure behavior, which
  NFR-004 and NFR-012 depend on.
- **Mitigation:** keep transport strictly inside `LiveDataProvider` (architecture skill:
  transport logic must not live in visual components) so the choice is deferrable to M12
  at low cost. Decide with Task 2 before M12 begins.

### RISK-I3 — Update cadence and partial-update semantics unknown — MEDIUM
Whether Task 2 sends full snapshots or deltas, at what rate, and whether messages are
ordered, is unspecified.

- **Impact:** affects the state-merge design and NFR-001 performance.
- **Mitigation:** design `subscribe` around `Partial<AppState>` patches, which tolerates both
  snapshot and delta styles; test both in mock scenarios at M3.

### RISK-I4 — Timestamp source and clock skew — MEDIUM
`age_ms` drives staleness, alerts and DEGRADED mode. If Task 2 timestamps come from a
differently-synchronised clock than the HMI's, staleness will be systematically wrong.

- **Impact:** false stale alerts, or worse, stale data never flagged — directly defeating
  NFR-012.
- **Mitigation:** treat clock offset as a calibrated quantity, not an assumed zero. Measure
  observed offset at M12, expose it in Diagnostics (S6), and make the staleness timeout
  configurable so it can be tuned against real link behavior. Never assume the two clocks
  agree because they should.

### RISK-I5 — Task 2 schedule dependency — MEDIUM
Task 2 is developed by another team on an unknown schedule.

- **Impact:** if Task 1 waited, nothing would ship.
- **Mitigation:** already the plan's core principle — M1..M11 complete entirely on mock data;
  only M12 requires Task 2. This risk is structurally contained.

---

## C. Scope Risks

### RISK-S1 — Scope creep through "just derive it" — HIGH
The highest-probability boundary breach is not a decision to implement Task 2, but a small
convenience: computing a KPI from history (AMB-003), extrapolating a queue line because the
chart looks bare (FR-007), interpolating a visibility forecast, or comparing values to
"determine" a violation.

- **Impact:** duplicated and divergent logic between Task 1 and Task 2, producing two
  different answers to a safety-adjacent question.
- **Mitigation:** the data contract carries a **closed list** of the eight values the HMI may
  derive (§12 of the contract), all of them properties of the data path rather than of the
  mine. Every milestone's verification gate includes a scope audit of the diff. Anything not
  on the list must arrive from a provider.

### RISK-S2 — Mock data becoming a simulator — HIGH
Realistic mock scenarios invite a physics or queueing model behind them. That model would be
a Task 2 algorithm living in this repository under a different name.

- **Impact:** direct violation of CLAUDE.md and the scope-control skill, discovered late.
- **Mitigation:** mock scenarios are **pre-baked recorded sequences**, not generators.
  Explicitly checked in the M3 scope audit.

### RISK-S3 — Optional CV consuming mandatory time — MEDIUM
CV is visible and demo-friendly; the mandatory HMI is larger and less exciting.

- **Impact:** mandatory requirements unfinished at the deadline.
- **Mitigation:** CV is confined to M13, after M12. PDF §11 and §12 permit marking it
  Not Implemented with no effect on Task 1 completion.

### RISK-S4 — Command issuance scope (see AMB-008) — HIGH
Ambiguous enough to change the backend, security and safety argument. Listed here too
because it is a scope risk, not only an ambiguity.

- **Mitigation:** resolve before M7 begins. Until resolved, display plus acknowledgment only.

---

## D. Missing-Data Assumptions

Assumptions made so that planning could complete. **Each is a place where the plan is wrong
if the assumption is wrong.**

| # | Assumption | If wrong |
|---|---|---|
| A-01 | `h_safe` is in metres | Safety display shows a plausible wrong value; M5 rework |
| A-02 | Task 2 supplies current headway and lead-vehicle ID | FR-005 cannot be satisfied at all |
| A-03 | Task 2 supplies `ArrivalPlan` | FR-008 has no data source; M6 blocked |
| A-04 | Task 2 supplies `KpiSnapshot` | Either FR-018 is unsatisfiable, or Task 1 scope expands |
| A-05 | Task 2 supplies `queue_forecast` | The "predicted queue trend" on S3 cannot be shown |
| A-06 | Task 2 supplies `VisibilityForecast` | FR-011's forecast half is permanently unavailable |
| A-07 | Task 2 supplies `MineTopology` | The map is hard-coded, breaking the architecture rule |
| A-08 | Task 2 supplies `Alert` for the four non-data-path categories | Alert generation would move into Task 1 — a scope breach |
| A-09 | System mode is supplied, not aggregated by the HMI | Mode logic becomes an HMI judgement about fleet safety |
| A-10 | Task 1 does not issue commands | M7 and M12 both expand; new authorization design needed |
| A-11 | The HMI backend owns replay recording | M9 redesigned around Task 2 log files |
| A-12 | *(withdrawn)* No performance target is assumed. Thresholds are unfilled configuration placeholders | n/a — nothing invented, so nothing to be wrong |
| A-13 | Enum value sets are four-level bands with `UNKNOWN` | Visual state mapping wrong after integration |
| A-14 | Override is out of scope | A mutating capability is missing from the plan |

---

## E. Verification Risks

### RISK-V1 — Two mandatory NFRs have no pass criterion — HIGH
NFR-001 and NFR-002 (see AMB-004). PDF §12 requires "all mandatory HMI functional
requirements verified"; these two are non-functional but still mandatory, and cannot be
signed off as specified.

- **Mitigation:** M11 produces measured values plus an explicit statement that the threshold
  is absent from the specification. Sign-off requires team-lead input, per PDF §11's rule
  that mandatory requirements are not waived without approval.

### RISK-V2 — "Verified" claimed from passing tests alone — MEDIUM
The testing skill is explicit: a feature is not complete because code was written. Screen
work is especially prone to green unit tests over a screen that is unreadable, or correct
only in the nominal state.

- **Mitigation:** the standing verification gate requires the app to be started and the
  failure states exercised, on every milestone — not only at M11.

### RISK-V3 — Greyscale/color-only compliance drifts — LOW
NFR-008 is easy to satisfy at M1 and easy to erode by M10, one convenient red badge at a time.

- **Mitigation:** shared status tokens defined once at M1 (text or icon per state), plus a
  no-color-only test and a greyscale review pass in the gate.

---

## F. Items Requiring Decision Before Implementation Starts

Ordered by the milestone they block.

| Priority | Item | Blocks |
|---|---|---|
| 1 | AMB-008 / RISK-S4 — does the HMI issue commands? | M7, M12, security design |
| 2 | AMB-004 — NFR-001/NFR-002 thresholds missing from the PDF | NFR sign-off |
| 3 | AMB-001 — `h_safe` units and headway source | M5 |
| 4 | AMB-002 — arrival-plan message | M6 |
| 5 | AMB-003 — who computes KPIs | M4, M11 |
| 6 | RISK-I1 — publish the data contract to Task 2 now | M12, and all mock shapes |
| 7 | AMB-011 — topology owner and format | M4 |
| 8 | AMB-007 — enum value sets and reason-code vocabulary | M5, M6, M7 |
| 9 | AMB-005 — vehicle vs system mode | M8 |
| 10 | AMB-010 — replay recording ownership and retention | M9 |
| 11 | AMB-009 — override definition or exclusion | M8 |
| 12 | RISK-I2 — transport choice (TECH-001) | M12 |
| 13 | AMB-006 — S7 screen placement | M3 |
| 14 | AMB-012, AMB-013 — file name and skill directory name | none |

Items 1 through 5 are the ones worth resolving before M1 begins; the rest can be resolved
in parallel with foundation work.
