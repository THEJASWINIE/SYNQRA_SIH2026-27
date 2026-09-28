# HMI Frontend Engineering Skill

## Purpose

This skill governs the implementation of the FOG-ORCHESTRATOR 2.0 Task 1
Human-Machine Interface.

Task 1 is an operator/control-room supervisory HMI.

The HMI visualizes externally supplied operational state.

It does NOT implement the Digital Twin, vehicle physics, safety calculations,
optimization, prediction, or other Task 2 intelligence.

The authoritative functional specification is:

docs/FOG_ORCHESTRATOR_Task1_HMI_Requirements.pdf

The governing project and architecture rules are defined by:

- AGENTS.md
- requirements/DECISIONS.md
- requirements/task1-requirements.md
- requirements/task1-traceability.md
- requirements/task1-data-contract.md
- requirements/task1-implementation-plan.md
- requirements/task1-risks-and-ambiguities.md

If this skill conflicts with those documents, the governing documents take
precedence.

Related skills:

- `.Codex/skills/scope-control/SKILL.md` — Task 1 / Task 2 boundary
- `.Codex/skills/task1-architecture/SKILL.md` — provider and data flow
- `.Codex/skills/realtime-data/SKILL.md` — validation, normalization, freshness
- `.Codex/skills/mock-scenarios/SKILL.md` — authored scenario data
- `.Codex/skills/safety-visualization/SKILL.md` — actual-versus-safe presentation
- `.Codex/skills/testing/SKILL.md` — verification discipline

---

# 1. Core HMI Principle

The HMI must optimize for:

1. Safety awareness
2. Situation awareness
3. Data freshness
4. Operational clarity
5. Fast comprehension
6. Traceability
7. Graceful degraded states

The interface is intended for an operator who needs to understand the state of
the mine/fleet quickly.

Do not design it as a generic SaaS dashboard.

Do not optimize for decorative visual effects at the expense of operational
readability.

Prefer:

- clear over decorative
- useful over flashy
- scannable over dense
- explicit over implied

---

# 2. Task 1 / Task 2 Boundary

## Task 1 may

- display externally supplied operational state
- display externally calculated safety values
- display externally calculated forecasts
- display externally calculated bottleneck scores
- display externally calculated queue states
- display externally calculated dispatch decisions
- visualize communications
- visualize alerts
- visualize system modes
- provide replay controls
- provide developer/tester scenario controls
- display KPIs supplied by the data layer
- acknowledge permitted HMI alerts/events

## Task 1 must not

- calculate v_safe
- calculate h_safe
- calculate stopping distance
- calculate friction
- predict queues
- calculate bottleneck scores
- optimize dispatch
- optimize routes
- generate arrival plans
- simulate vehicles
- simulate fog
- simulate physics
- generate Digital Twin outputs
- actuate vehicles/equipment
- issue vehicle commands
- implement safety override behavior

If Task 1 needs an unavailable Task 2 result:

- represent it as unavailable, stale, invalid, or missing as appropriate
- do not invent an algorithmic substitute

## The two derivations Task 1 does perform

Only two derived quantities are sanctioned, and neither is an operational value:

1. **Data age** — `ageMs`, computed from a supplied timestamp against the HMI
   clock. A property of the data path, not of the mine.
2. **Display comparison and ordering** — comparing two supplied values for
   presentation, and sorting supplied values for display. Permitted by the frozen
   data contract §12 item 6.

Comparing a supplied `actualSpeed` against a supplied `vSafe` to render a
violation marker is a display comparison and is allowed. Computing either value
is not.

---

# 3. Application State Boundary

React UI components must consume normalized application state.

Do not allow UI components to consume:

- raw API payloads
- raw scenario JSON
- WebSocket frames
- provider-specific structures
- backend-specific structures

Required conceptual flow:

DataProvider
    ↓
Validation
    ↓
Normalization
    ↓
Application State
    ↓
React HMI
    ↓
Visual Components

Provider-specific logic belongs outside the visual component tree.

---

# 4. State and Provider Independence

The HMI must not know whether data came from:

- MockDataProvider
- ReplayProvider
- LiveDataProvider

The same HMI components must render normalized state regardless of provider.

Do not write:

```text
if mock ...
if replay ...
if live ...
```

inside a visual component.

The single legitimate exception is a component whose subject IS provider status —
a connection indicator, a provider badge, a diagnostics panel. Such a component
reads `AppState.connection`, which is normalized application state, not a
provider object.

## Provider selection lives at one boundary

Exactly one module in the application may import a concrete provider. Every other
module reads application state.

Approved M4 structure:

MockDataProvider
      ↓
ProviderHost          ← the ONLY module importing a concrete provider
      ↓
AppStateStore
      ↓
useSyncExternalStore
      ↓
React components

A screen that imports `MockDataProvider` is a defect. So is a component that
receives a provider instance as a prop.

---

# 5. State Management

Approved for M4 and binding until explicitly changed:

- **No Redux. No Zustand. No additional state library.**
- Application state lives in a plain `AppStateStore` module holding one `AppState`
  value.
- Patches are applied through the shared `data/patch.ts` merge, never re-implemented.
- React subscribes through `useSyncExternalStore`, which is a React built-in and is
  precisely the external-store subscription primitive.

A dependency is not added for what a built-in already does.

## Patch semantics are not re-interpreted in the UI

The store applies the provider's `ProviderPatch` exactly as the data layer defines:

- key missing from `changes` → NO CHANGE
- key present with an entity → UPSERT
- id listed in `deletions` → DELETE

Merge order is deletions first, then changes.

A component must never infer that an entity was removed because it was absent from
an update. Absence means "no news".

## Local component state

Local state is appropriate for:

- selected vehicle
- open/closed panel
- modal state
- filters
- UI preferences
- navigation position

Local state is NOT appropriate for authoritative operational domain data.

Do not copy operational values into component state. A copied value is a value
that can silently go stale independently of the one the data layer maintains.

---

# 6. Sourced<T>, Freshness and Quality

## The four qualities

| Quality | Meaning | Has a value to render |
|---|---|---|
| `OK` | Valid and current | yes |
| `STALE` | Valid, age exceeds the configured threshold | yes — render it, marked |
| `MISSING` | The complete datum was never supplied | no |
| `INVALID` | The datum was supplied but failed validation | no |

Two rules are load-bearing:

- **Malformed data must never become MISSING.** A payload that arrived and failed
  validation is `INVALID`. Collapsing the two hides an integration fault behind
  what looks like a quiet link.
- **Invalid data must not also be treated as stale.** Age is meaningless for
  something that failed validation.

A `STALE` value keeps its value and is still rendered. Stale means "a real reading,
too old to trust as current" — not "nothing to show".

## Where freshness is applied

The frozen data contract holds `AppState` entities **unwrapped** — `VehicleState`,
not `Sourced<VehicleState>`. This is deliberate and is not to be changed.

Freshness is therefore derived **at the rendering boundary**, from each entity's own
supplied timestamp, using the existing `data/sourced.ts` machinery. There is exactly
one place `Sourced<T>` values are constructed. A second provenance wrapper, or a
second site that assembles one, is a defect.

## The display ticker

Displayed ages advance only if something re-renders. One display timer may drive
that re-render.

The ticker recomputes `ageMs` from supplied timestamps and does nothing else. It
must never generate, interpolate, extrapolate or advance an operational value.
A ticker that moved a vehicle, decayed a visibility figure, or aged a queue toward
a predicted value would be a simulation, and is prohibited.

## The unresolved threshold — AMB-014

HMI-NFR-003 requires stale data to be flagged after a *configurable* timeout. The
specification never states the value. AMB-014 is UNRESOLVED and PAD-G forbids
inventing one.

Approved HMI behaviour when the threshold is not configured:

- show a persistent, explicit banner: **FRESHNESS THRESHOLD NOT CONFIGURED**
- state that data age is still shown
- state that stale classification is not evaluated
- state that no authoritative timeout has been configured
- **do not invent a threshold, and do not silently choose a default**

While `isAuthoritative` is false, anything rendering staleness marks the threshold
provisional.

---

# 7. Safety Visualization

Governed in full by `.Codex/skills/safety-visualization/SKILL.md`. That skill is
binding; this section states only what the frontend must never lose sight of.

Always make these distinctions obvious:

ACTUAL SPEED versus SAFE SPEED

Current headway versus required H_safe

Both members of each pair are supplied by Task 2. Task 1 displays both and compares
them for presentation. Task 1 computes neither.

Never rely on colour alone. Every safety signal carries:

- a text label
- a numeric value with units
- a glyph or icon where useful
- colour as supporting information only

Safety information must remain fully understandable in greyscale.

---

# 8. Alerts

Support the alert categories the contract defines, including:

- unsafe speed
- unsafe headway
- bottleneck risk
- communication loss
- stale data
- slot conflict

Every important alert renders:

- severity, as text
- the alert message
- the subject it concerns
- a timestamp or age
- a glyph or icon where useful
- colour as supporting information only

Ordering is by severity, then recency. That ordering is a display sort on supplied
values and is permitted.

Critical alerts appear above lower-priority content. Do not place an operational
warning below a chart.

## Acknowledgement

Acknowledgement is **HMI alert/event acknowledgement only** (PAD-D).

It changes display state and writes an audit record. It never clears, suppresses or
downgrades the underlying condition.

It must NOT:

- issue vehicle commands
- override safety
- change vehicle control state
- modify v_safe
- modify h_safe
- trigger dispatch
- actuate equipment

Safety-critical alerts are not acknowledgeable (FR-015); honour the contract's
`acknowledgeable` flag rather than deciding in the component.

Whether the HMI may issue commands at all (AMB-008) and what "override" means
(AMB-009) remain UNRESOLVED. Do not build UI that presumes either.

---

# 9. System Modes

The contract defines five:

NORMAL · CAUTION · DEGRADED · LOCAL_SAFE · STOP_UNSAFE

The current mode is supplied by the data layer. The HMI displays it and never
derives, infers or promotes it.

The mode must be visible in the primary application shell, on every screen. Do not
hide it in Diagnostics only.

An unrecognised mode value is handled by the contract's unknown-tolerant enum
behaviour, not by a component guessing an equivalent.

When the mode is unavailable, show it as unavailable. Do not default to NORMAL —
displaying a reassuring mode that was never supplied is the most dangerous
substitution this HMI can make.

---

# 10. The Six HMI Screens

| Screen | Content | Milestone |
|---|---|---|
| S1 Operations Overview | mine map, vehicles, active bottleneck, current fog state, top alerts, throughput, system mode | M4 |
| S2 Vehicle Detail | vehicle id, position/segment, actual speed, safe speed, headway, safe headway, risk, friction, grade, communication, active constraint, recent trend | M5 |
| S3 Bottleneck & Queue | bottleneck ranking, utilization, queue length, queue limits, arrival rate, service rate, queue trend, criticality | M6 |
| S4 Dispatch & Slots | vehicle assignment, departure time, route, target speed, slot timeline, ETA, reason code, conflict status | M7 |
| S5 Event / Replay | event timeline, fog events, alerts, commands, queue changes, violations, recovery, time-based playback | M9 |
| S6 Diagnostics | data freshness, telemetry status, backend health, message counts, latency, communication state | M10 |

Build incrementally. Do not implement all six screens at once.

A screen not yet built exists as a navigation target rendering an explicit
`NOT IMPLEMENTED — milestone Mn` panel. Structure without content is honest;
a dead nav link is not.

---

# 11. Operations Overview (S1)

S1 must immediately answer:

1. What is the current system mode?
2. Are there critical alerts?
3. Where are the vehicles?
4. Where is the bottleneck?
5. What are the fog/visibility conditions?
6. Is the fleet operating normally?
7. Is the data fresh?

Required hierarchy — warnings above charts:

SYSTEM MODE / CONNECTION / SCENARIO / FRESHNESS STATE
        ↓
CRITICAL ALERTS
        ↓
MINE MAP + FLEET
        ↓
FOG / VISIBILITY · ACTIVE BOTTLENECK
        ↓
KPI / THROUGHPUT

Do not place critical operational warnings below low-priority charts.

---

# 12. Mine Map

The mine map is a graph/map visualization. A photorealistic 3D mine is NOT required.

Render from **supplied topology** and **supplied vehicle positions**:

- roads and road segments
- intersections and switchbacks
- shovels and crushers
- vehicles
- bottleneck indicators

Prohibited absolutely:

- trajectory interpolation
- tweening or animated movement between updates
- dead reckoning
- any frontend vehicle simulation
- inferring a position from speed and elapsed time

A vehicle moves on the map when, and only when, a new supplied position arrives.

If a vehicle position is unavailable, show **POSITION UNAVAILABLE**. Do not guess a
position, do not reuse the last known point as if current without marking it, and
do not hide the vehicle — an operator losing sight of a truck is a safety event.

If topology has not been supplied, show the map area as unavailable rather than
rendering an empty frame that reads as an empty mine.

---

# 13. Vehicle Presentation

Vehicle cards are compact and scannable. Actual and safe values appear together,
both labelled:

```text
TRUCK-07     ACTUAL 45 km/h
             SAFE   29 km/h   ▲ OVER SAFE SPEED
             RISK HIGH · CONSTRAINT LOW_VISIBILITY
             ● 2.1 s ago
```

Every card carries:

- vehicle identifier
- actual speed with units
- safe speed with units
- an explicit textual marker when actual exceeds safe
- risk level as text
- active constraint as text
- data age or quality

A field the data layer did not supply renders as unavailable, not as zero, not as a
dash that could be read as a value, and never as a locally derived substitute.

---

# 14. Charts

Use a chart only when it answers an operational question. A chart that decorates a
panel is complexity with no operator value.

Legitimate subjects: speed trend, visibility trend, queue trend, utilization,
throughput, KPI history.

Every chart carries:

- units
- a time axis
- readable labels
- the current value where appropriate
- quality/freshness information when relevant

Do not infer a trend that does not exist in supplied data. Supplied history and
supplied forecast are different series and must be drawn distinguishably — a
forecast is a Task 2 output, and blending it into measured history misrepresents
which is which. Never extrapolate a forecast the data layer did not supply.

---

# 15. Empty and Degraded States

Empty states are real product states, not placeholder gaps. Name them explicitly:

NO ACTIVE ALERTS
NO ACTIVE BOTTLENECK
NO ACTIVE SLOT CONFLICT
POSITION UNAVAILABLE
VISIBILITY DATA UNAVAILABLE
FRESHNESS THRESHOLD NOT CONFIGURED

Do not manufacture data merely to fill a visual panel. A scenario in which nothing
is wrong must render as a scenario in which nothing is wrong.

Do not build only the happy path. These states must all exist and all be visible:

- loading
- current
- stale
- missing
- invalid
- disconnected
- reconnecting
- provider error
- backend error
- degraded

Distinguish the failure domains. HMI backend health and operational data health are
different failures and must not be merged into one indicator — the backend can be up
while the operational feed is silent, and the operator needs to know which.

Distinguish "no news" from "no link". A silent feed on a live connection and a
dropped connection are different operator situations.

---

# 16. Accessibility

NFR-008 requires that critical information never depend on colour alone.

Every display state is turned into something renderable through one mechanism that
carries a label and a glyph alongside its colour. A component that reaches for a
colour without the matching text or glyph is a defect.

Additional requirements:

- semantic HTML and meaningful landmark/section labelling
- alerts announced through an appropriate live region or `role="alert"`
- decorative glyphs marked `aria-hidden`, with the meaning carried by adjacent text
- keyboard reachability for every interactive control
- units always written out, never implied by position
- adequate contrast, verified rather than assumed

Test by asserting against text. A test that passes only because of a colour proves
nothing about an operator who cannot rely on that colour.

---

# 17. Component Architecture

Prefer reusable components where appropriate. Candidates:

StatusBadge · SeverityBadge · FreshnessIndicator · AlertRow · MetricCard ·
VehicleCard · VehicleStatus · ConnectionIndicator · DataAge · TrendChart · Panel

Rules:

- Do not over-engineer components before the first working screen exists.
- Each reusable component has one clear responsibility.
- No component built speculatively for a screen not yet in scope.
- No abstraction with a single use and no second use in sight.
- Presentation components take normalized values as props and hold no transport,
  provider or fetching logic.

Transport logic must never be embedded inside a visual component.

---

# 18. Navigation

The application shell owns navigation and the global status header.

The shell must display, on every screen:

- system mode
- connection status
- active provider and, where applicable, active scenario
- freshness state, including the unconfigured-threshold banner

Navigation targets exist for all six screens from the first shell. Unimplemented
screens render an explicit milestone placeholder.

Navigation state is local UI state. It is not operational data and does not belong
in the application store beyond what a route needs.

---

# 19. Scenario Picker

The scenario picker is a **developer/tester capability**, not an operator control.
Present it as such.

It must consume `listScenarios()` / `getScenario()` or the approved provider and
application abstraction.

It must NOT:

- read scenario JSON directly
- calculate scenario data
- create a second state system

It should show:

- scenario name
- description
- scenario family
- which scenario is active

Selecting a scenario routes through the provider boundary — disconnect, reset the
store, load, connect. One state system, one store, one lifecycle.

Because no single scenario exercises every S1 panel, S1 is verified across several
scenarios. Scenario data files are **not** modified to manufacture activity for a
screen; a scenario is authored data and changing it to make a panel look busy
corrupts the evidence it exists to provide.

---

# 20. Performance

Use the authoritative Task 1 requirements. NFR-001 and NFR-002 numerical thresholds
are missing from the specification (AMB-004) and must not be invented — represent
them as named configuration placeholders and state the measured value alongside.

Optimize only after measuring.

Avoid unnecessary:

- full-tree renders
- expensive map redraws
- uncontrolled chart updates
- duplicate state
- repeated normalization

Normalization happens once, in the data path. A component that re-normalizes is
both a performance fault and a correctness fault, because it creates a second
definition that can drift.

Performance claims require actual measurements. "Should be fast" is not a result.

---

# 21. Testing

Governed by `.Codex/skills/testing/SKILL.md`. HMI-specific requirements follow.

Put logic in pure functions so it is testable without a DOM. Store merges, mode and
connection derivation, alert ordering, freshness classification, violation detection
and map projection are all pure and all must be tested directly.

Render assertions use `react-dom/server`. Approved for M4: **do not add jsdom,
@testing-library/react, or other UI testing dependencies.** Automated click testing
is added later, when interaction complexity justifies it.

At minimum, cover:

- store merge and reset
- provider status transitions
- scenario selection logic
- alert severity ordering
- freshness classification, per quality
- actual-versus-safe violation marker
- topology projection from supplied coordinates
- missing values
- invalid values
- stale values
- disconnected state
- no-alert state
- no-bottleneck state
- threshold-unconfigured state

For safety visualization, explicitly test that `actualSpeed > vSafe` produces a
**textual** violation marker. Assert against text, not colour.

Do not declare completion from compilation alone.

---

# 22. Browser Verification

A UI feature is not complete until it has been exercised in a running browser.

For every HMI milestone:

1. Start the frontend.
2. Start required backend/provider services.
3. Load a realistic mock scenario.
4. Open the browser.
5. Navigate to the screen.
6. Exercise the normal state.
7. Exercise the critical state.
8. Exercise stale and disconnected states.
9. Inspect the console for errors.
10. Verify the visual hierarchy — warnings above charts.
11. Verify no broken layouts.
12. Verify safety information remains readable without colour.

Record which scenarios were used for which state. Because coverage is spread across
scenarios, naming them is part of the evidence.

---

# 23. Scope Audit

Before completing any HMI milestone, search the changed surface for:

v_safe · h_safe · predict · forecast · optimize · simulate · physics ·
friction calculation · queue calculation · bottleneck calculation ·
dispatch optimization · route optimization · actuate · override · command issuance

Review every result.

Inbound references such as:

```text
vehicle.safety.vSafe
```

are allowed — that is consumption.

Local implementations such as:

```text
calculateSafeSpeed(...)
```

are prohibited — that is Task 2.

Also audit for the frontend-specific failure modes:

- arithmetic on operational values beyond display comparison and ordering
- interpolation, tweening or extrapolation of any supplied series
- a component importing a concrete provider
- a component reading raw JSON or a raw payload
- a second `Sourced<T>` construction site
- an invented threshold or default where the specification states none
- a default that substitutes a reassuring value for an unsupplied one

---

# 24. Completion Discipline

Never report "complete" merely because code was generated.

A milestone is complete only when:

- the implementation exists
- the requirements it claims are addressed
- tests pass
- lint passes
- type-check passes
- the production build passes
- browser verification passes for UI work
- failure states are tested
- the scope audit passes
- no hidden Task 2 functionality exists
- no unintended next-milestone work exists

Report evidence: exact files changed, exact commands run, exact results, and what
was NOT implemented.

Stop at the milestone boundary. Never silently continue into the next milestone.

---

# 25. Change Discipline

Do not modify frozen planning documents casually.

If a genuine contract or requirement defect is found:

1. Stop.
2. Explain the defect.
3. Identify the impact.
4. Use the project's revision process in `requirements/DECISIONS.md`.
5. Record the decision.
6. Only then change the implementation.

Do not silently reinterpret requirements. Do not perform unrelated refactoring. Do
not add a dependency for convenience.

Before adding any dependency:

- explain what capability it provides
- confirm it is necessary
- check whether an installed dependency or a platform built-in already covers it
- state production or development scope

Do not introduce a UI framework merely for styling convenience.

---

# 26. Final Principle

Task 1 exists to make externally produced intelligence:

VISIBLE · UNDERSTANDABLE · TRACEABLE · TIMELY · OPERATIONALLY USEFUL

without becoming the intelligence engine itself.

When information is unavailable: SHOW UNAVAILABLE.

When information is stale: SHOW STALE.

When a computation belongs to Task 2: CONSUME IT. Do not recreate it.

When safety information conflicts: MAKE THE SAFETY STATE OBVIOUS.
