# Safety Visualization Skill

## Purpose

This skill governs how the Task 1 HMI presents safety-critical information.

It applies wherever the HMI renders a safety value: Operations Overview vehicle
cards, Vehicle Detail, alerts, the mine map, replay, and diagnostics.

The authoritative functional specification is:

docs/FOG_ORCHESTRATOR_Task1_HMI_Requirements.pdf

Governing documents:

- CLAUDE.md
- requirements/DECISIONS.md
- requirements/task1-requirements.md
- requirements/task1-data-contract.md
- requirements/task1-risks-and-ambiguities.md

Related skills:

- `.claude/skills/hmi-frontend/SKILL.md` — general HMI implementation
- `.claude/skills/scope-control/SKILL.md` — Task 1 / Task 2 boundary
- `.claude/skills/realtime-data/SKILL.md` — freshness and quality

If this skill conflicts with those documents, the governing documents take
precedence.

---

# 1. The One Rule

**Every safety value the HMI displays is supplied by Task 2. Task 1 renders it and
compares supplied values for presentation. Task 1 computes none of them.**

The HMI's job is to make an externally computed safety state obvious, current, and
impossible to misread. It is not to decide what is safe.

---

# 2. Actual Speed versus v_safe

## What is supplied

The contract supplies both members of the pair on `SafetyState`:

| Field | Meaning | Source |
|---|---|---|
| `actualSpeed` | measured vehicle speed | supplied |
| `vSafe` | safe speed | **SUPPLIED BY TASK 2** |

## What the HMI must show

Both values, together, each labelled, each with units:

```text
ACTUAL SPEED
38 km/h

SAFE SPEED
20 km/h

STATUS
CRITICAL

ACTIVE CONSTRAINT
LOW VISIBILITY
```

Requirements:

- Both values appear in the same visual grouping. A safe speed shown on a different
  screen from the actual speed answers nothing.
- Both carry explicit units. A unit implied by column position is not a unit.
- Both carry an explicit label. `38 / 20` is not a display.
- The exceedance is stated in **text**, not implied by colour or position:
  `OVER SAFE SPEED`, or equivalent wording.

## The permitted comparison

Comparing supplied `actualSpeed` against supplied `vSafe` to render a violation
marker is a **display comparison**, explicitly permitted by the frozen data contract
§12 item 6.

Prohibited, without exception:

- computing `v_safe`
- computing stopping distance
- computing or adjusting for friction
- applying a margin, factor, buffer or rounding to a supplied `v_safe`
- deciding a threshold at which a speed "counts" as unsafe

The comparison is `actualSpeed > vSafe`. Nothing more. If Task 2 supplies
`envelopeViolation`, prefer the supplied flag and show the comparison alongside it;
do not overrule a supplied flag with a locally computed opinion.

## When a member of the pair is absent

`vSafe` is nullable. If it is not supplied:

- show `SAFE SPEED — UNAVAILABLE`
- still show the actual speed
- **do not render a violation marker**, because there is nothing to violate
- do not substitute a site limit, a previous value, or any other figure as if it
  were the safe speed

A missing safe speed is itself operationally significant. Show it; do not paper
over it.

---

# 3. Current Headway versus h_safe

## What is supplied

| Field | Meaning | Source |
|---|---|---|
| `headwayCurrent` | current headway | supplied |
| `hSafe` | required safe headway | **SUPPLIED BY TASK 2** |
| `leadVehicleId` | the vehicle ahead | supplied |
| `headwayViolation` | violation flag, if Task 2 evaluates it | supplied |

## Units are unresolved — AMB-001

The specification does not state whether `h_safe` is a distance or a time. AMB-001
is **UNRESOLVED**.

Consequently:

- **Do not label `h_safe` with an assumed unit.** Do not write `m` and do not write
  `s` on the strength of a guess.
- Render the unit as supplied, or mark it explicitly as unresolved.
- Do not convert between distance and time. A conversion needs a speed and an
  assumption, and both would be invented.
- Do not compare `headwayCurrent` against `hSafe` if the two are not known to share
  a unit. An unlabelled numeric comparison across unknown units is worse than no
  comparison, because it looks authoritative.

Where Task 2 supplies `headwayViolation`, that flag is the safe thing to display.

## What the HMI must show

Both values with labels, the lead vehicle identified, and any supplied violation
stated in text:

```text
CURRENT HEADWAY
41

REQUIRED H_SAFE
60          (unit unresolved — AMB-001)

LEAD VEHICLE
TRUCK-03

▲ HEADWAY VIOLATION
```

Prohibited:

- computing `h_safe`
- deriving headway from positions, speeds or timestamps
- modelling following distance
- inferring a lead vehicle the data layer did not supply

---

# 4. Risk Visualization

`riskLevel` is supplied on `SafetyState`. Values: `LOW`, `MODERATE`, `HIGH`,
`CRITICAL`, `UNKNOWN`.

Requirements:

- Render the level as **text**. `RISK HIGH`, not a coloured dot alone.
- `UNKNOWN` renders as `RISK UNKNOWN` — never as `LOW`, never blank, never omitted.
- The band names are not defined in the specification (AMB-007). Do not invent band
  boundaries, do not map a numeric value onto a band, and do not re-band a supplied
  level.
- Do not derive a risk level from speed, headway, visibility, friction or any other
  value. Risk arrives supplied or not at all.

An unavailable risk level is shown as unavailable. A blank cell reads as "fine".

---

# 5. Active Constraint

`activeConstraint` is supplied. Contract values:

`VISIBILITY` · `FRICTION` · `GRADE` · `BRAKING_RETARDER` · `CURVE` · `SITE_LIMIT` ·
`NONE` · `UNKNOWN`

The active constraint is *why* the safe speed is what it is. It is the single most
useful field for operator comprehension and must be shown alongside the
actual-versus-safe pair, not buried in a detail view.

Requirements:

- Render as readable text. A raw enum token is acceptable only if no clearer label
  exists; a human-readable rendering is preferred and must map one-to-one.
- `NONE` and `UNKNOWN` are distinct and must render distinctly. "No constraint is
  active" and "we were not told" are different operator situations.
- Do not deduce the constraint from other fields. If visibility is poor and the
  constraint says `FRICTION`, display `FRICTION`. The HMI does not second-guess
  Task 2.

---

# 6. Text, Numeric and Icon Requirements

Every safety element carries, at minimum:

1. **A text label** — what the value is.
2. **A numeric value with units** — where the datum is numeric and the unit is known.
3. **A severity or status word** — where a state is being communicated.
4. **A glyph or icon** — where it aids fast scanning.
5. **Colour** — supporting only.

A safety element that carries only a colour, only a glyph, or only a number is a
defect.

Icons and glyphs are marked `aria-hidden` and never carry meaning alone; the
adjacent text carries it.

---

# 7. Colour Must Not Be the Only Signal

NFR-008 requires that critical information never depend on colour alone.

Concretely:

- A red row must also say `CRITICAL`.
- A red speed must also say `OVER SAFE SPEED`.
- A green status must also say `WITHIN LIMITS` or equivalent.
- A colour change without an accompanying text change communicates nothing to an
  operator with a colour vision deficiency, on a sun-washed control-room display,
  or on a degraded monitor.

The test is greyscale: **strip all colour and the safety state must still be fully
readable.** This is testable and must be tested — assert on text, not on colour.

Do not use colour to distinguish two states that differ in nothing else. Do not
encode severity ordering in hue alone.

---

# 8. Stale and Invalid Safety Data

Safety data is exactly where a silently stale value does the most harm. The HMI must
never present a stale safety value as current.

| Quality | Value shown | Marking |
|---|---|---|
| `OK` | yes | normal presentation, age available |
| `STALE` | **yes — the real reading is kept** | explicit `STALE` marker and the age |
| `MISSING` | no — nothing was supplied | `UNAVAILABLE` |
| `INVALID` | no — supplied but failed validation | `INVALID` |

Rules:

- A `STALE` safety value is still rendered, marked, with its age:
  `STALE DATA — last update 13.4 s ago`.
- A malformed payload is `INVALID`, **never** `MISSING`. Collapsing the two hides an
  integration fault behind what looks like a quiet link.
- An `INVALID` datum is never also reported as `STALE`. Age is meaningless for
  something that failed validation.
- Do not render a violation marker from stale or invalid inputs without stating that
  the inputs are stale or invalid. A violation computed from an old reading is a
  claim about the past presented as the present.
- Do not hide a stale safety value to avoid showing something questionable. Hiding
  it removes the operator's ability to judge.

## When the freshness threshold is unconfigured

HMI-NFR-003 requires a configurable staleness timeout; the specification states no
value (AMB-014, UNRESOLVED). PAD-G forbids inventing one.

While unconfigured:

- show the persistent banner **FRESHNESS THRESHOLD NOT CONFIGURED**
- continue showing data age
- do **not** evaluate or display stale classification
- do **not** invent a threshold or silently choose a default

## Disconnected and degraded

A disconnected provider does not freeze the safety display. Values continue to age
on their own, which is how NFR-012's degrade-rather-than-freeze behaviour emerges.

Distinguish, in text:

- `DISCONNECTED` — no link
- silent feed on a live link — no news
- `DEGRADED` — supplied system state

These are different operator situations and must not share one indicator.

---

# 9. No Local Safety Calculations

Prohibited in the HMI, without exception:

- calculating `v_safe`
- calculating `h_safe`
- calculating stopping distance
- calculating or estimating friction
- modelling braking, retarder capability or grade effects
- modelling vehicle dynamics or following distance
- computing a safety envelope
- deriving a risk level or risk score
- deriving an active constraint
- predicting, forecasting or extrapolating any safety quantity
- interpolating a safety value between updates

If a safety value is unavailable, the HMI shows it as unavailable. **It does not
compute a substitute.** A locally invented safe speed is indistinguishable, on
screen, from an authoritative one — which makes it the most dangerous possible
defect in this repository.

Permitted, and only these:

- rendering supplied values
- computing `ageMs` from a supplied timestamp against the HMI clock
- comparing two supplied values, in the same unit, for display
- sorting supplied values for display
- formatting and unit presentation where the unit is known

---

# 10. No Modification of Task 2 Safety Outputs

A supplied safety value is displayed as supplied.

Prohibited:

- applying a safety margin, buffer or factor
- rounding in a direction that changes meaning — never round a safe speed up, and
  never round an actual speed down
- clamping to a plausible range
- smoothing, filtering or averaging across updates
- overriding a supplied violation flag with a locally computed comparison
- suppressing a supplied violation because it "looks wrong"
- reordering severity so a critical item is not first
- substituting a default when a value is absent

Formatting for display — decimal places, unit rendering, human-readable labels — is
permitted, provided it does not change which side of a threshold a value falls on.

Acknowledgement changes display and audit state only (PAD-D). It never clears,
suppresses or downgrades the underlying safety condition, and safety-critical alerts
are not acknowledgeable (FR-015) — honour the contract's `acknowledgeable` flag.

---

# 11. Testing

Every safety presentation needs an explicit test. At minimum:

- `actualSpeed > vSafe` produces a **textual** violation marker — asserted against
  text, not colour
- `actualSpeed <= vSafe` produces no violation marker
- `vSafe` absent produces `UNAVAILABLE` and **no** violation marker
- `riskLevel` `UNKNOWN` renders as unknown, not as low and not as blank
- `activeConstraint` `NONE` and `UNKNOWN` render distinctly
- a stale safety value renders its value **and** a stale marker with its age
- an invalid safety value renders `INVALID`, never `MISSING`
- a missing safety value renders `UNAVAILABLE`
- the disconnected state renders explicitly
- the unconfigured-threshold banner renders and stale classification is suppressed
- headway is not compared across units while AMB-001 is unresolved

Greyscale assertion: safety tests inspect rendered text. A test that passes only
because a colour attribute was present proves nothing about NFR-008.

---

# 12. Browser Verification

Safety visualization is not complete until verified in a running browser.

Required steps:

1. Start the frontend and required provider services.
2. Load a scenario that produces a safety violation. `envelope-violation` exercises
   the supplied violation path; `fog-rolling-in` and `friction-degradation` exercise
   constraint changes. Do not modify scenario data to manufacture a violation.
3. Confirm the actual and safe values appear together, both labelled, both with
   units where the unit is known.
4. Confirm the violation is stated in text.
5. Confirm the active constraint and risk level are visible and readable.
6. **Disable colour** — greyscale filter, or inspect with colour rendering removed —
   and confirm the safety state remains fully understandable.
7. Load `stale-feed` and confirm stale safety values are shown with their values and
   an explicit stale marker.
8. Load `communication-loss` and confirm the disconnected state is explicit and
   distinct from a silent feed.
9. Run with the freshness threshold unconfigured and confirm the banner appears and
   stale classification is not evaluated.
10. Confirm a vehicle with no supplied safe speed shows `UNAVAILABLE` and no
    violation marker.
11. Inspect the console for errors.
12. Confirm safety content sits above lower-priority content in the visual hierarchy.

Record which scenario exercised which state. Coverage is spread across scenarios by
approved decision, so naming them is part of the evidence.

---

# 13. Final Principle

When safety information conflicts, **make the safety state obvious.**

When a safety value is unavailable, **show unavailable.**

When a safety value is stale, **show stale, and show the value.**

When the computation belongs to Task 2, **consume it — never recreate it.**

The operator must be able to tell, at a glance and without colour, whether a vehicle
is within its externally computed safety envelope, and how current that judgement is.
