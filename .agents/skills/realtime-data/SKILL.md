---
name: realtime-data
description: Realtime Data and Provider Boundary Skill
---

# Realtime Data and Provider Boundary Skill

## Purpose

This skill governs implementation of Task 1 data ingestion, validation,
normalization, freshness, provenance, quality, provider abstractions, and
provider error handling.

Task 1 is an HMI and supervisory visualization system.

Task 1 consumes externally supplied operational data.

Task 1 MUST NOT implement Digital Twin computation, prediction, optimization,
simulation, or operational intelligence that belongs to Task 2.

The authoritative project rules are defined by:

1. `AGENTS.md`
2. `requirements/DECISIONS.md`
3. `requirements/task1-data-contract.md`
4. `requirements/task1-requirements.md`
5. `requirements/task1-traceability.md`
6. `requirements/task1-implementation-plan.md`
7. `requirements/task1-risks-and-ambiguities.md`

If this skill conflicts with those documents, the governing documents take
precedence.

---

# 1. Core Architectural Boundary

The required conceptual flow is:

External Source
      ↓
Raw Contract Payload
      ↓
Validation
      ↓
Normalization
      ↓
Provenance / Freshness Metadata
      ↓
Typed Provider Boundary
      ↓
Application State
      ↓
HMI

The HMI must not consume arbitrary unvalidated external payloads directly.

The HMI must consume normalized, typed data.

---

# 2. Task 1 Consumes — Task 2 Computes

The following distinction is mandatory.

## Task 1 MAY

- receive externally supplied values
- validate payload shape
- validate required fields
- normalize payload structure
- normalize timestamps
- attach source metadata
- calculate data age from timestamps
- determine freshness or staleness according to configured rules
- detect communication/provider failure
- display quality or validity metadata
- display externally computed predictions
- display externally computed recommendations
- display externally computed KPIs
- sort data for display
- perform display-only comparisons permitted by the frozen baseline
- expose typed provider errors

## Task 1 MUST NOT

- calculate safe speed
- calculate safe headway
- derive `h_safe`
- predict queues
- forecast bottlenecks
- optimize dispatch
- optimize routes
- generate arrival plans
- simulate vehicles
- simulate fog
- simulate traffic
- simulate operational physics
- generate operational KPIs from simulation history
- infer Digital Twin outputs from raw telemetry
- replace missing Task 2 data with locally invented algorithms

If an externally supplied value is missing, Task 1 must represent the value as
unavailable, stale, invalid, or errored as appropriate.

Task 1 must not silently calculate a substitute.

---

# 3. Source of Truth for Domain Types

Do not invent domain entities, fields, enums, or message semantics.

Before creating or changing a domain type:

1. Check `requirements/task1-data-contract.md`.
2. Check the traceability document.
3. Check the authoritative PDF.
4. Check `requirements/DECISIONS.md`.
5. Check unresolved ambiguities.

If the specification does not define a required field or semantic:

- do not invent operational meaning
- record the gap if required by the project workflow
- use a clearly bounded typed placeholder only where the frozen baseline permits it
- do not disguise assumptions as authoritative requirements

---

# 4. The Sourced<T> Rule

Every datum originating outside the HMI boundary must carry provenance and
freshness information through one consistent mechanism.

Use the project's canonical `Sourced<T>` model as defined by
`requirements/task1-data-contract.md` §1. That document is authoritative; the
form below is the same structure expressed in the normalized (camelCase) domain
naming approved for M2.

```ts
type Quality = "OK" | "STALE" | "MISSING" | "INVALID";

interface Sourced<T> {
  value: T | null;        // null = not supplied. Never coerce to 0.
  timestamp: Iso8601;     // when the SOURCE produced it — externally supplied
  sourceId: ComponentId;  // externally supplied
  ageMs: number;          // locally derived
  quality: Quality;       // locally derived
}
```

Rules that travel with it:

1. **One wrapper, one construction site.** `Sourced<T>` values are built in a
   single module. A second provenance wrapper is a defect.
2. **`value: null` is a first-class state.** Never `0`, never `""`, never a
   sentinel value.
3. **A raw number reaching a component is a defect.** Components consume
   `Sourced<T>`, not bare values.
4. `value` and `timestamp` and `sourceId` are externally supplied. `ageMs` and
   `quality` are locally derived and are the only two fields Task 1 computes.

---

# 5. Timestamp Rules

Timestamps are the foundation of freshness. Getting them wrong makes stale data
look current, which is the exact failure NFR-012 exists to prevent.

1. The contract type is `Iso8601` — UTC, millisecond precision.
2. Parse once at normalization. Retain **both** the original ISO string, for
   display and audit fidelity (NFR-007), and a derived epoch-milliseconds value
   for arithmetic.
3. A timestamp without a timezone offset is **invalid**. Never coerce it to
   local time.
4. An unparseable timestamp is **invalid**.
5. A datum with no timestamp is **invalid** — freshness cannot be assessed
   without one.
6. A timestamp in the future beyond a configured tolerance is **invalid**. A
   negative age must never be reported as "very fresh".
7. `ageMs` must never be emitted as `NaN` or as a negative number.

## Source time versus receipt time

Both are needed, and they are not interchangeable.

- **Source time** (`Sourced.timestamp`) is when the producer created the datum.
  Age is derived from this, per the closed derivation list.
- **Receipt time** is when the HMI received the batch. It belongs on the
  provider update envelope, not inside `Sourced<T>` — it is a property of the
  delivery, not of each field, and duplicating it per field is waste.

Clock skew between the source and the HMI is a recorded integration risk. Task 1
records the material needed to measure skew. Task 1 does **not** correct for it
by inventing a calibration the specification has not authorized.

---

# 6. Quality and Freshness Semantics

Four states. They are distinct and must never be collapsed into one another.

| Quality | Meaning | Value present |
|---|---|---|
| `MISSING` | The complete datum was **not supplied** | No — `null` |
| `INVALID` | The datum **was supplied** but failed validation | No — `null` |
| `STALE` | The datum is valid but its age exceeds the configured timeout | **Yes** |
| `OK` | The datum is valid and within the configured timeout | Yes |

## The rule that is easiest to get wrong

**Never convert a malformed payload into `MISSING`.**

`MISSING` means nothing arrived. `INVALID` means something arrived and was
wrong. Collapsing the second into the first hides an integration fault behind
what looks like a quiet link, and an operator cannot tell a silent source from a
broken one.

Worked examples:

| Situation | Quality |
|---|---|
| No `SafetyState` received at all | `MISSING` |
| `SafetyState` received, but `actual_speed` has an invalid type | `INVALID` |
| `SafetyState` received, but a required field is absent | `INVALID` |
| `SafetyState` received with an optional field explicitly `null` | that field is `MISSING` |
| Valid `SafetyState` whose age exceeds the configured timeout | `STALE` |
| Valid, current `SafetyState` | `OK` |

## Precedence

Evaluate in this order; the first match wins:

1. Nothing supplied → `MISSING`
2. Supplied but failed validation → `INVALID` (regardless of age)
3. Valid but age exceeds the timeout → `STALE`
4. Otherwise → `OK`

An invalid datum is never also reported as stale or fresh. Age is meaningless
for something that failed validation.

## Stale is not unavailable

`STALE` keeps its value and is rendered with an explicit age marking. `MISSING`
has no value to render. Conflating them either hides real data or fabricates
absence.

Connection status is **orthogonal** to datum quality. A disconnected provider
does not mark individual data invalid — previously received readings simply age
into `STALE`. That behaviour is required by NFR-012 and must emerge from the age
rule rather than being special-cased.

## The staleness timeout

NFR-003 requires the timeout to be **configurable**. It must be configuration,
never a literal inside a component or a rendering path.

The specification does not state its numeric value. Do not invent one. Carry it
as a named placeholder requiring authoritative confirmation, and let tests inject
the threshold so the freshness mechanism is fully testable independent of the
real value.

---

# 7. Validation

Validation runs **before** normalization, always. Nothing reaches normalization
unparsed, and normalization never receives `unknown`.

```
unknown payload
   → schema validation
   → ok:   raw contract payload → normalization
   → fail: typed validation failure → quality INVALID
```

Rules:

1. Validation is total. There is no cast-and-hope path.
2. Unsafe type assertions that bypass runtime validation are defects. This
   includes `as SomeType`, `as unknown as`, `any`, and suppression comments in
   the data path.
3. Validation failures are **typed return values, never thrown exceptions**.
4. A failure must carry enough structure to identify what was wrong and where —
   the message type, the field path, what was expected, what arrived.
5. **One bad field does not discard a whole batch.** Sibling data remains
   usable. A single schema drift from the producer must not blank the HMI.

---

# 8. Normalization

Normalization converts a validated raw payload into the normalized domain shape.

1. Raw wire types use the contract's snake_case representation.
2. Normalized domain types use camelCase.
3. **Unknown enum values normalize to `UNKNOWN`. They are never dropped and
   never rejected.** The original value is preserved where the contract requires
   it to be rendered verbatim.
4. Normalization is a pure transform: raw in, domain out. It performs no
   arithmetic on operational values, no aggregation, no inference.
5. Normalization does not fill gaps. An absent value stays absent and is
   represented by quality, not by a substituted number.

---

# 9. Provider Boundary

## What belongs inside a provider

- transport (HTTP, WebSocket, MQTT, file replay, timer-driven mock)
- reconnect and backoff
- producing raw payloads
- emitting lifecycle status transitions

## What belongs outside, shared by every provider

- validation
- normalization
- `Sourced<T>` construction
- freshness and quality classification
- the application state shape

Validation and normalization are **not** per-provider. All providers hand raw
payloads to one shared path. This is what makes swapping a provider incapable of
changing screen behaviour.

## Provider independence

The future architecture is:

```
Mock Provider   \
Replay Provider  ---->  same normalized data boundary  ---->  HMI
Live Provider   /
```

Four properties make the swap safe, and each must be preserved:

1. **One output shape.** Providers emit normalized partial state updates, never
   raw transport frames. A screen cannot tell which provider produced them.
2. **Shared validation and normalization**, not three parallel implementations.
3. **A common status vocabulary**, regardless of whether "disconnected" means a
   closed socket, an exhausted mock script, or the end of a replay file.
4. **Selection by injection, not import.** Screens receive a provider. A screen
   that imports a concrete provider module is a defect.

Consequence: adding a provider adds one file implementing one interface. It
touches no screen.

## Acknowledgement is not command issuance

Where the provider boundary exposes acknowledgement, its semantics are:

> **HMI alert/event acknowledgement only.**

Acknowledgement changes display state and writes an audit record. It must not:

- issue vehicle commands
- override safety
- change vehicle control state
- modify `v_safe`
- modify `h_safe`
- trigger dispatch
- actuate equipment

Acknowledging an alert never clears, suppresses or downgrades the underlying
condition, and safety-critical local protection never depends on it.

Whether the HMI may issue commands at all, and what "override" means, are
**unresolved ambiguities**. Do not resolve either by implementing behaviour.

---

# 10. Provider Errors

Two error families, kept separate because they mean different things to an
operator.

**Validation failure** — this payload is bad, the pipe is fine. Marks the
affected datum `INVALID`. Does not change connection status.

**Provider error** — the pipe is bad, and it says nothing about the data.
Drives connection status. Never marks individual data `INVALID`; previously
received values age into `STALE` on their own.

Rules:

1. Both are typed results. A promise rejection escaping the provider boundary is
   a defect.
2. A transport failure must be distinguishable from a data failure at the type
   level, not by inspecting a message string.
3. Provider errors carry whether they are retryable, so reconnect logic does not
   have to guess.
4. Initialization failure is distinct from a failure after a working connection.

---

# 11. Closed Derivation Boundary

`requirements/task1-data-contract.md` §12 defines a **closed list** of values
Task 1 may derive. Every one is a property of the data path or of presentation,
never a property of the mine.

Task 1 derives only:

1. `ageMs` for any datum — now minus source timestamp
2. `quality` — from age against the configured timeout, and from validation
3. connection status
4. alerts of category `STALE_DATA` and `COMM_LOSS`
5. forcing displayed system mode to at least `DEGRADED` when the feed is lost
6. sort order of the bottleneck list from the supplied score
7. alert ordering from supplied severity and timestamp
8. boolean comparisons of two supplied numbers, for display only, used solely
   when the producer has not supplied the flag

**Anything not on this list must arrive from a provider.**

Adding to this list requires re-running the scope-control decision rule and
recording the change through the project's revision process. It is never a
silent addition.

The failure mode to watch for is not a decision to implement Task 2. It is a
small convenience: a chart looks bare so a trend gets extrapolated; a KPI is
absent so it gets aggregated from local history; a flag is missing so a
threshold gets applied. Each is a Task 2 algorithm arriving by accident.

---

# 12. M2 Scope

M2 is the **typed data foundation and provider boundary**. It builds the pipes,
not what flows through them.

## In scope

- TypeScript domain types for every contract message
- raw wire payload types
- runtime validation
- normalization, including unknown-enum handling
- canonical `Sourced<T>`
- source metadata, timestamp handling, age derivation
- freshness, staleness and quality representation
- typed provider result and error models
- the provider interface declaration, with no implementation
- minimal provider status semantics
- mirrored backend schemas where the frozen plan requires them
- unit tests for the whole data path

## Out of scope in M2

- any provider implementation — mock, replay or live
- mock scenarios
- replay engine or replay UI
- WebSocket or MQTT integration
- a real Task 2 connection
- any React store or state binding
- any HMI screen
- every Task 2 computation named in §2

If data required by Task 1 is missing, Task 1 represents it as unavailable,
invalid, stale or errored. Task 1 never invents an operational substitute.

---

# 13. Testing

The data path is where correctness is cheapest to establish and most expensive
to retrofit. Test it before any UI depends on it.

Required coverage:

1. valid payload accepted
2. missing required field within a supplied payload → `INVALID`
3. invalid types → `INVALID`
4. invalid enum values → `UNKNOWN`, never dropped
5. invalid timestamps → `INVALID`, age never negative or `NaN`
6. normalization round-trip per message type
7. source metadata preserved unaltered
8. data age calculated correctly
9. all four quality states reachable and distinct
10. stale data retains its value
11. unavailable data distinguished from invalid data
12. provider initialization failure
13. provider/transport failure
14. validation failure does not discard sibling data
15. typed error handling — nothing throws
16. boundary protection against local Task 2 computation

Discipline:

- **Inject the clock.** Never call the current time directly in freshness logic;
  tests must be deterministic and must not depend on wall time.
- **Inject the staleness threshold.** Tests must not depend on the placeholder's
  provisional value.
- Test stubs used to exercise provider failure paths live in the test file. A
  stub must never become a shipped provider.

---

# 14. Scope Audit

Run before declaring any data-layer work complete. Review every match
individually: a comment stating absence is a pass, an implementation is a defect.

## Prohibited computation

Search for:

```
predict  forecast  optimi[sz]e  simulat  physics  friction
v_safe  h_safe  safe.?speed  safe.?headway
bottleneck.*algorithm  queue.*algorithm
route.*optimi  dispatch.*optimi
actuate  override  command.?issu
```

Expected: matches only as inbound-only type or field names (receiving `h_safe`
is the point), or as comments asserting absence. Any assignment, arithmetic, or
function **producing** such a value is a defect.

## Structural checks

- no invented numerical thresholds; every threshold is a named placeholder or an
  authoritative value
- no raw external payload reaches the HMI without validation
- no unsafe type assertions bypass runtime validation
- no duplicate provenance wrapper
- no duplicate provider architecture
- no Task 2 output is locally generated
- no later-milestone work has leaked in — mock scenarios, replay, screens
- the frozen planning baseline is unchanged

---

# 15. Completion Discipline

Do not claim completion because code was written.

Before reporting any data-layer work complete:

1. Run linting.
2. Run type checking.
3. Run the tests.
4. Exercise the failure states, not only the happy path — invalid, missing,
   stale, disconnected.
5. Run the scope audit in §14 and review every match.
6. Confirm no unresolved ambiguity was silently resolved.
7. Report what was verified, what was not, and every known limitation.

An unverified claim of completion is worse than an admitted gap, because it
removes the reason to look.
