---
name: mock-scenarios
description: Mock Scenario Engineering Skill
---

# Mock Scenario Engineering Skill

## Purpose

This skill governs Task 1 mock data and deterministic scenario development.

The mock system exists only to provide realistic test inputs for the HMI.

It is NOT a Digital Twin.

It MUST NOT reproduce Task 2 physics, prediction, optimization, or simulation
algorithms.

The authoritative project rules are defined by `AGENTS.md`,
`requirements/DECISIONS.md` and the frozen planning baseline. If this skill
conflicts with those documents, the governing documents take precedence.

## Core Rule

**Mock data is authored, not simulated.**

Mock scenarios are predefined data sequences, not physics generators.

Allowed:

- scripted values
- deterministic state transitions
- predefined vehicle paths
- predefined fog values
- predefined queue values
- predefined bottleneck values
- predefined dispatch values
- predefined alerts
- predefined communication failures
- predefined recovery sequences

Forbidden:

- calculating v_safe
- calculating h_safe
- simulating vehicle physics
- calculating friction
- predicting queues
- calculating bottleneck scores
- optimizing dispatch
- optimizing routes
- simulating fog physics
- reconstructing Digital Twin algorithms

## Determinism

Every scenario must be deterministic.

Same:

- scenario
- configuration
- seed where applicable

must produce the same sequence.

Scenarios should be replayable exactly.

## Scenario Structure

A scenario should contain explicit timestamped or step-based states.

Conceptually:

```ts
Scenario
  id
  name
  description
  duration
  steps[]
```

Each step declares what is emitted at that point and, optionally, what changes
about the connection itself.

```ts
Step
  index        // 0-based, fixes emission order
  atMs         // offset from scenario start, NOT wall-clock time
  emit         // raw contract payloads to publish at this step
  effects      // optional connection/emission changes
```

Rules that make the structure work:

1. **Steps are offset-based, not wall-clock.** Playback maps `atMs` onto an
   injected time source, so the same file runs instantly under test and at
   real speed in a demo.
2. **`emit` carries raw wire payloads**, in the same shape the real producer
   sends. Mock data must travel the same validation and normalization path as
   live data; a mock that bypasses validation proves nothing about the real
   integration.
3. **Timestamps are stamped at emission from the injected clock**, so a
   committed scenario does not become stale merely by ageing on disk. This is
   the only value the playback layer derives, and it is a data-path property,
   not an operational one.
4. **`effects` is where failures live** — declarative data, never branching
   logic inside the provider.
5. **No conditionals, no branching, no state machine deciding what "should"
   happen.** The provider replays; the file decides.

## Deterministic Playback

Determinism is a hard requirement, not a convenience. Four mechanisms:

1. **Injected clock.** The provider receives a clock. Tests supply a fake;
   production supplies the system clock. Playback never calls the current time
   directly.
2. **Injected scheduler.** A scheduler abstraction rather than bare timers.
   Tests use a manual scheduler and advance it step by step. No test may
   depend on real wall-clock waiting.
3. **No runtime randomness.** No random number generation anywhere in the mock
   path. Where variation is wanted, it is authored into the file. Where a seed
   is not needed because nothing is generated, do not add one — an unused seed
   implies generation happens somewhere.
4. **Ordered, indexed steps.** Emission order is file order.

Two runs of the same scenario must produce an identical sequence of emissions,
and two independent provider instances must agree. Both are testable
properties, and both should have a test.

## Failure Representation

Failures are declared in scenario data and surfaced through the project's
typed error models. Do not invent a parallel error vocabulary.

Distinguish two families, because they mean different things to an operator:

- **Data failure** — a payload was supplied and was wrong. The pipe is fine.
- **Transport failure** — the pipe is broken. It says nothing about the data.

Guidance:

| Failure | Representation |
|---|---|
| Unknown scenario id | Initialization error; not retryable |
| Malformed scenario file | Initialization error, caught at load, before any emission |
| Scripted link loss | Transport error, retryable, with a status transition |
| Scripted protocol fault | Protocol error |
| Deliberate teardown | Aborted — not a fault |
| Deliberately malformed payload in a scenario | Travels the normal validation path and fails there |

That last row matters. A scenario carrying an intentionally malformed message
exercises the invalid path end to end, and proves the rule that a malformed
payload becomes INVALID and never MISSING.

Errors are returned or emitted as typed values. A raw throw escaping the
provider boundary is a defect.

## Provider Status Transitions

Use the project's existing connection-status vocabulary. Do not introduce a
second status enum.

Every status change has exactly one of two causes:

1. **Lifecycle** — connect and disconnect.
2. **Scenario data** — a step's `effects` declares the transition.

The provider must never *infer* status from data silence. Telling "no news"
apart from "no link" is precisely why an explicit status channel exists, and
inference destroys that distinction.

## Stale-Data Handling

**The provider must never assign a quality value.**

Not OK, not STALE, not MISSING, not INVALID. The provider supplies data and
events. Validation, normalization, timestamp handling and the freshness rules
determine the resulting quality.

A mock that stamps `STALE` directly would prove nothing: it would test the
scenario file, not the freshness machinery the real system depends on.

Staleness is produced the honest way — emission stops, time advances, age
passes the configured threshold, and the quality flips on its own.

Keep these two cases distinct, and give each its own scenario:

| Scenario | Status | Emission | Result |
|---|---|---|---|
| stale feed | stays CONNECTED | stops | data ages to STALE |
| communication loss | goes DISCONNECTED | stops | data ages to STALE |

Both produce stale data; only one changes status. If the HMI cannot tell them
apart, its degraded-mode behaviour is not actually working — and this pair is
how that gets found.

The staleness threshold is injected. No scenario or test may depend on a
threshold value the specification has not supplied.

## Recovery

Recovery is scripted as a complete arc, not merely a return to normal:

1. Steady valid data.
2. Failure — status transition plus typed error.
3. Silence, during which data ages and values are retained, not blanked.
4. Reconnection in progress.
5. Connection restored, fresh data with current timestamps.
6. Quality returns to normal on its own.

What must be asserted after recovery: no duplicated entities, no incoherent
merge, and **no stale value presented as current**. The last is the failure
that would otherwise be invisible.

## Scope Boundaries

Every operational value must come from scenario data as an authored literal.

`v_safe`, `h_safe`, `bottleneck_score`, `queue_forecast`, `friction`,
`visibility`, dispatch results and arrival plans are **authored inputs**. None
may be calculated at runtime from visibility, grade, friction, mass, speed,
braking, or any other quantity.

No runtime operational generator is permitted.

Where a large fixture is needed, a one-time generation script is acceptable as
bookkeeping only. The committed output is the authoritative artifact, and the
script must contain constants alone — no physics formulas, no trajectory
calculations, no queue evolution, no spacing calculations, no randomness.
There is no runtime generator.

Scenario files must not encode mine dynamics as behaviour. A file describing
what values appear at which step is a scenario. A file, or a generator,
computing what the values *ought* to be is a Task 2 algorithm wearing a mock's
clothing.

## Testing

Cover at least:

- registry completeness
- scenario schema validation
- the validation pipeline — mock payloads travel the real path
- normalization
- deterministic repeated playback
- independent provider determinism
- lifecycle
- timer cancellation on teardown
- initialization failure
- malformed scenario rejection
- communication loss
- stale feed, distinct from communication loss
- invalid payload yielding INVALID, never MISSING
- recovery
- explicit deletion semantics
- scenario switching leaving no residue
- scale
- acknowledgement boundary
- patch merge behaviour

Discipline:

- Inject the clock and the scheduler. **No test may depend on real wall-clock
  waiting.**
- Inject the staleness threshold.
- A test stub must never become a shipped provider.

## Completion Discipline

Do not claim completion because code was written.

Before reporting mock or scenario work complete:

1. Run linting.
2. Run type checking.
3. Run the tests.
4. Exercise the failure states, not only the happy path.
5. Audit for prohibited computation, and review every match individually. A
   comment stating absence is a pass; an implementation is a defect.
6. Confirm every operational value traces to an authored literal.
7. Confirm no unresolved ambiguity was silently resolved.
8. Report what was verified, what was not, and every known limitation.

An unverified claim of completion is worse than an admitted gap, because it
removes the reason to look.
