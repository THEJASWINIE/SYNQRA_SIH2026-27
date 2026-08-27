# Task 1 — Decision Register

**Specification:** `docs/FOG_ORCHESTRATOR_Task1_HMI_Requirements.pdf` (canonical path; sole Task 1 specification).
**Baseline:** Planning Baseline v1.3 — **FROZEN**.
**Scope:** this register is the controlling record for every provisional decision, open
ambiguity and assumption governing Task 1. Where this register and any other planning
document disagree, this register wins.

---

## 1. Planning Baseline

### 1.0 Revision History

| Version | Date | Type | Summary |
|---|---|---|---|
| v1 | Planning phase | Initial freeze | Baseline established: 41 mandatory requirements, 20 contract extensions, 13 ambiguities, 12 risks, PAD-A..PAD-G |
| v1.1 | Correction pass | **Documentation / path consistency only** | Governing instructions relocated from `docs/CLAUDE.md` to the repository root `CLAUDE.md`; cross-reference counts corrected |
| v1.2 | M2 proposal correction pass | **New ambiguity + approved implementation decisions** | AMB-014 registered (NFR-003 staleness timeout has no authoritative value); M2 approved architecture decisions MAD-A..MAD-G recorded |
| v1.3 | M3 proposal correction pass | **New implementation decisions** | mock-scenarios skill completed; M3 implementation decisions MID-A..MID-F recorded, including explicit patch deletion semantics |
| v1.3.1 | M4 correction pass | **Discovered defect — metadata only** | §1.2 baseline-state block corrected: it still read v1.2 and "M2 has not started" after M2 and M3 completed. Decision inventory updated with M4D-A..M4D-E. No requirement, contract, decision, ambiguity or architecture changed |
| v1.4 | M5 decision pass | **Discovered defect — closed derivation list** | The closed derivation list in `task1-data-contract.md` §12 omitted the map interpolation that frozen requirement HMI-FR-002 mandates. Item 9 added; M4D-F records the permitted transform and its prohibitions |
| v1.5 | M7 decision pass | **Discovered defects — documentation only** | D6: M4D-F was misfiled in §8 and is moved to §10. D7: M5 and M6 shipped without register entries — recorded as M5D-A..C and M6D-A..B in a new §11, and §1.2 milestone status corrected. M7 decisions recorded as M7D-A..E in a new §12, including the FR-010 AC3 partial non-conformance. No requirement, contract, architecture or ambiguity resolution changed |
| v1.6 | M8 decision pass | **Approved decisions + registered planning gap** | M8D-A..C recorded in a new §13: HMI-originated COMM_LOSS and STALE_DATA approved as mandated data-path derivations; STALE_DATA gated on the unresolved AMB-014 threshold; FR-015 acknowledgment deferred to M9. ROLE-001 registered as an unowned planning gap (GAP-ROLE-001). No requirement, contract, architecture or ambiguity resolution changed |
| v1.7 | M9 decision pass | **Approved decisions + two discovered defects** | M9D-A..F recorded in a new §14: in-memory session recording (AMB-010 option a), a separate append-only event log (D8), the observable-event derivation boundary, the D9 acknowledgement-state fix, the replay clock (D10), and acknowledgement UI held back pending server-side role enforcement. NFR-007 persistence recorded as a declared non-conformance. No requirement, contract or ambiguity resolution changed |
| v1.8 | M10 decision pass | **Approved decisions + one discovered defect** | M10D-A..C recorded in a new §15: supplied message counters only (no tenth closed derivation), validation failures surfaced read-only on S6 (D11), and the dead placeholder screen removed. No requirement, contract, architecture or ambiguity resolution changed |
| v1.9 | M11 verification pass | **Verification evidence + four discovered defects** | M11D-A..D recorded in a new §16. D12: the traceability matrix had never been updated and read `PLANNED` on all 37 rows — rebuilt against executed evidence, with no requirement wording, acceptance criterion or milestone assignment changed. D13 (CORS/preview origin), D14 (`README.md` stale) and D15 (four pre-existing lint errors) are recorded, not fixed. NFR-001 and NFR-002 recorded as NOT VERIFIABLE YET against unfilled placeholders. No requirement, contract, architecture or ambiguity resolution changed |

#### v1.9 entry

- **Type:** verification evidence plus four discovered defects (revision rule §1.3
  clause 3). No requirement, contract, architecture or ambiguity resolution changed.

- **M11 is a verification milestone.** It added no feature, no provider, no persistence,
  no role infrastructure and no transport. It added two test files, four measurement and
  evidence artifacts, and it replaced assertions with executed evidence.

- **Defect D12 — the traceability matrix was entirely stale.** Every one of the 37 rows in
  `requirements/task1-traceability.md` read `PLANNED`, including requirements implemented
  and browser-verified across M4–M10. A matrix that records nothing as done is worse than
  no matrix, because it is read as authoritative. **Resolution (M11D-A):** rebuilt against
  executed evidence, with a five-value status vocabulary. Requirement wording, acceptance
  criteria, IDs, verification methods and milestone assignments are unchanged; no
  requirement was waived, weakened or re-scoped.

- **Defect D13 — the preview/production origin is not in the default CORS allow-list.**
  `HMI_CORS_ORIGINS` defaults to the dev-server origins only (`:5173`). A production or
  `vite preview` build served from any other origin has its backend health call blocked,
  which the HMI correctly reports as UNREACHABLE. First observed at M10 against
  `vite preview` on `:4173`. **Not an application defect** — a deployment configuration
  gap. **Recorded, not fixed (M11D-D):** deployment configuration is M12, and silently
  widening a CORS policy during a verification milestone would be exactly the kind of
  unreviewed change this register exists to prevent.

- **Defect D14 — `README.md` is stale.** It states "Current stage: M1 — Foundation …
  There are no HMI screens yet", cites Planning Baseline v1.1, and lists M4–M10 as not
  yet built. Six screens exist and the register is at v1.9. The **setup and check
  instructions themselves were verified correct** (see
  `docs/verification/portability.md` §4); the staleness is in the surrounding narrative.
  **Recorded, not fixed:** rewriting `README.md` was not among the changes approved for
  M11.

- **Defect D15 — four pre-existing lint errors in M1–M10 code.** `npm run lint` reports
  four errors that predate M11: `screens/Diagnostics.tsx:377` (array index in a React
  key), `screens/DispatchSlots.tsx:143` (`aria-label` on an element whose role does not
  support it), `state/ProviderHost.tsx:261` (an unnecessary hook dependency) and
  `state/eventLog.test.ts:259` (unsafe optional chaining). All four are cosmetic or
  a11y-hygiene issues with no observed functional effect; none is a safety, scope or
  contract violation. The two files M11 added are clean. **Recorded, not fixed:** the
  approval for this milestone forbids refactoring completed milestones, and one of the
  four (the hook dependency) would change effect-run behaviour. Fixing them needs its own
  approval.

- **NFR-001 and NFR-002 are measured and NOT passed.** Both thresholds are unfilled
  placeholders (AMB-004). Figures are recorded in `docs/verification/perf.md` and
  `docs/verification/latency.md`, each stating explicitly that no verdict can be computed.
  This is the M11 definition of done, met as written.

- **Files affected:**

  | File | Change |
  |---|---|
  | `requirements/DECISIONS.md` | This entry; §1.0 row; §1.2 status, version and inventory; new §16 (M11D-A..D) |
  | `requirements/task1-traceability.md` | D12 — rebuilt against executed evidence |
  | `docs/verification/*.md` | Eight new evidence documents |
  | `frontend/src/state/scale.test.tsx` | New — NFR-009 |
  | `frontend/src/state/recovery.test.ts` | New — NFR-004 |
  | `frontend/verification/*.ts` | New — NFR-001 and NFR-002 measurement scripts |

- **What did not change:**
  - **No requirement changed.** Every requirement is quoted, never amended.
  - **No contract changed.** The closed derivation list was re-counted and remains at
    **nine** items.
  - **No architecture changed.** No provider, no state library, no persistence, no roles,
    no transport. No M1–M10 application file was modified.
  - **No ambiguity was resolved.** AMB-001, AMB-004, AMB-005, AMB-008, AMB-009, AMB-010
    and AMB-014 remain open, as does GAP-ROLE-001.
  - **No M3 scenario data changed.**

#### v1.8 entry

- **Type:** approved implementation decisions plus one discovered defect (revision rule
  §1.3 clause 3). No requirement, contract, architecture or ambiguity resolution changed.

- **Question Q1 — answered without widening the closed derivation list.** S6-a requires
  "message counts and latency per component". Those are SUPPLIED on
  `Health.messagesReceived` / `.messagesDropped` / `.latencyMs`, so displaying them needs
  no derivation. The M10 plan's phrasing hinted at HMI-side counters; counting the HMI's
  own deliveries would have been a **tenth** item on the closed list. The project owner
  ruled: supplied counters only. **The closed derivation list stays at nine items**
  (M10D-A).

- **Defect D11 — validation failures were recorded but invisible.**
  `MockDataProvider.diagnostics.validationFailures` has existed since M3 and was never
  exposed through `ProviderHost`, so nothing could display it. A payload that arrived and
  failed validation is the `INVALID` case the whole M2 design exists to distinguish from
  `MISSING` — and no operator or tester could see that it had happened. **Resolution
  (M10D-B):** surfaced read-only on S6.

- **R6 — the placeholder screen becomes dead code.** With S6 implemented,
  `PLACEHOLDER_SCREENS` is empty and `Placeholder.tsx` has no reachable consumer.
  Removed rather than left as a component that can never render (M10D-C).

- **Files affected:**

  | File | Change |
  |---|---|
  | `requirements/DECISIONS.md` | This entry; §1.0 row; §1.2 status and inventory; new §15 (M10D-A..C) |

- **What did not change:**
  - **No requirement changed.** FR-013, S6-a and NFR-003 are quoted, not amended.
  - **No contract changed.** `Health`, `SystemHealth`, `LINK_KINDS`, `HEALTH_STATES` and
    the nine-item closed derivation list are untouched.
  - **No architecture changed.** Every prior decision stands. S6 introduces no provider,
    no state library, no second freshness mechanism and no second health client.
  - **No ambiguity was resolved.** AMB-001, AMB-004, AMB-005, AMB-008, AMB-009, AMB-010
    and AMB-014 remain open, as does GAP-ROLE-001.
  - **No M3 scenario data changed.**

#### v1.7 entry

- **Type:** approved implementation decisions plus two discovered defects (revision rule
  §1.3 clause 3). No requirement, contract, architecture or ambiguity resolution changed.

- **Defect D8 — `AppState.events` cannot serve as an append-only log.** `data/patch.ts`
  applies `events` as a **replace-whole** slice, exactly as contract §13 specifies. Every
  delivery therefore replaces the entire array. That is right for a live set and wrong for
  an audit trail: M9 requires an append-only log and NFR-007 requires events be persisted
  and visible in S5. **Resolution (M9D-B):** the frozen semantics stay unchanged and a
  separate append-only log is added outside `AppState`. The contract is not amended.

- **Defect D9 — `sendAcknowledgement` never updated the alert.** `MockDataProvider`
  emitted an `ALERT_ACKNOWLEDGED` event but its patch carried only `events`; the `alerts`
  slice was untouched, so `Alert.acknowledged` stayed null forever. Latent since M3 because
  no UI ever called the method. **Resolution (M9D-D).**

- **Design consequence D10 — replay freshness.** Replayed data carries historical
  timestamps. Aged against the wall clock, every replayed value would read stale, and
  FR-017 AC1 requires scrubbing to *t* to reproduce the state recorded at *t* — including
  how fresh it was. **Resolution (M9D-E):** during replay the render clock follows the
  replay position. This is why `ClockState.replayPosition` has existed, unused, since M2.

- **AMB-010 remains UNRESOLVED.** M9D-A adopts the standing assumption's *frontend* half
  for this milestone only: in-memory session recording, no persistence. Recording
  ownership and retention are still owed by the team lead.

- **Files affected:**

  | File | Change |
  |---|---|
  | `requirements/DECISIONS.md` | This entry; §1.0 row; §1.2 status and inventory; new §14 (M9D-A..F) |

- **What did not change:**
  - **No requirement changed.** FR-017, S5-a, NFR-007, FR-010 AC3, FR-016 AC2, FR-015 and
    ROLE-001 are quoted, not amended. Where unmet, they are recorded as unmet.
  - **No contract changed.** `EventRecord`, `EVENT_CATEGORIES`, `AppState`,
    `AppStatePatch` and the replace-whole `events` semantics are untouched.
  - **No architecture changed.** PAD-A..G, MAD-A..G, MID-A..F, M4D-A..F, M5D-A..C,
    M6D-A..B, M7D-A..E and M8D-A..C stand. `ReplayProvider` is the third implementation of
    the existing `DataProvider` interface, exactly as it was declared for in M2.
  - **No ambiguity was resolved.** AMB-001, AMB-004, AMB-005, AMB-008, AMB-009, AMB-010
    and AMB-014 remain open, as does GAP-ROLE-001.
  - **No M3 scenario data changed.**

#### v1.6 entry

- **Type:** approved implementation decisions plus one registered planning gap.
  **No defect, no correction.**

- **M8D-A — the two mandated data-path derivations are approved.** The M8 audit surfaced a
  tension between a blanket "no alert generation, no mode calculation" instruction and four
  mandatory baseline items that require exactly two narrow derivations: FR-014 AC4,
  FR-016 AC3, OPS-003 and NFR-012. The tension was reported rather than resolved by
  implementation, and the project owner ruled that both proceed. Both were already on the
  closed derivation list (`task1-data-contract.md` §12 items 4 and 5) and both concern the
  HMI's own data path, not the mine. **No new derivation is added to the closed list by
  this revision.**

- **M8D-B — STALE_DATA alerting is gated on AMB-014.** The stale half of FR-014 AC4 needs a
  staleness threshold, and AMB-014 remains UNRESOLVED. The mechanism is implemented; its
  activation is conditional, and the HMI says so explicitly when unconfigured. PAD-G is
  untouched: no threshold is invented, and no default is chosen.

- **M8D-C — FR-015 acknowledgment is deferred to M9.** Its AC2 requires a timestamped log
  event and its AC3 requires role gating; neither exists. Offering acknowledgment without
  the audit record would breach NFR-007 the moment the control appeared.

- **GAP-ROLE-001 registered.** ROLE-001 (Mandatory, derived) — "the HMI shall gate actions
  by role; override shall never be offered for safety-critical items" — has no owning
  milestone anywhere in the implementation plan and no implementation. Recorded in §13 so
  it stops being invisible. **Not implemented in M8**; no role infrastructure is invented.

- **Files affected:**

  | File | Change |
  |---|---|
  | `requirements/DECISIONS.md` | This entry; §1.0 row; §1.2 status and inventory; new §13 (M8D-A..C, GAP-ROLE-001) |

- **What did not change:**
  - **No requirement changed.** FR-014, FR-015, FR-016, NFR-007, NFR-012, OPS-003 and
    ROLE-001 are quoted, not amended.
  - **No contract changed.** The closed derivation list is unchanged — items 4 and 5
    already covered both approved derivations.
  - **No architecture changed.** PAD-A..G, MAD-A..G, MID-A..F, M4D-A..F, M5D-A..C,
    M6D-A..B and M7D-A..E stand.
  - **No ambiguity was resolved.** AMB-001, AMB-004, AMB-005, AMB-008, AMB-009 and AMB-014
    remain open. AMB-005's standing position — "system mode supplied; HMI forces at least
    DEGRADED on data-path loss only" — is confirmed by M8D-A, not altered by it.
  - **No M3 scenario data changed.**

#### v1.5 entry

- **Type:** discovered defects (revision rule §1.3 clause 3) plus approved implementation
  decisions. **Documentation only.** No code behaviour is changed by this entry.

- **Defect D6 — `M4D-F` was filed in the wrong section.** It was written into §8, the M3
  decision section, between MID-F and §9, instead of §10 where M4D-A..E live. Cause: an
  insertion during the M5 pass matched a fallback anchor when the intended one did not
  exist. The decision text was always correct and complete; only its location was wrong.
  **Correction:** the block is moved verbatim to the end of §10, with an inline note
  recording the move. No wording changed.

- **Defect D7 — M5 and M6 shipped without register entries.** Both milestones were
  implemented and approved, but neither recorded its decisions, and §1.2 still read
  "M5 Vehicle Detail — in progress" and "M6 onward — not started" after both were
  complete. M6 was implemented in a separate tool, which is how the register fell behind.
  **Correction:** a new §11 records M5D-A..C and M6D-A..B retrospectively, and §1.2 is
  restated. Recording these late does not change them; they are the decisions the
  implemented code already embodies, read back from it and from the milestone reviews.

- **Registered limitation R1 — FR-010 AC3.** Recorded as **M7D-C**: "every displayed
  command also appears in the event log" cannot be satisfied while no scenario emits
  `EventRecord` and no event log exists. It is **not claimed as passed for M7** and must
  be re-verified at M9. Fabricating an event log to close it is explicitly prohibited.

- **Approved for M7 — test-local fixtures.** Recorded as **M7D-D**: the authored-data
  gaps (`ISSUED` state, alternate slot statuses, missing reason codes, null ETA/route/
  target speed, multi-row ordering, degraded states) are covered by fixtures inside the
  test file. **No M3 scenario file is modified.** The consequence is recorded rather than
  hidden: FR-010 AC2 has no browser coverage and is not claimed as browser-verified.

- **Files affected:**

  | File | Correction |
  |---|---|
  | `requirements/DECISIONS.md` | This entry; §1.0 row; §1.2 status and inventory; M4D-F moved into §10; new §11 (M5D, M6D); new §12 (M7D) |

- **What did not change:**
  - **No requirement changed.** FR-009 and FR-010 are quoted, not amended. S2-b is
    recorded as unmet, not weakened.
  - **No contract changed.** `DispatchCommand`, `SlotState`, `AppState` and the closed
    derivation list are untouched.
  - **No architecture changed.** PAD-A..G, MAD-A..G, MID-A..F and M4D-A..F stand.
  - **No ambiguity was resolved.** AMB-001, AMB-004, AMB-008, AMB-009 and AMB-014 remain
    open. M7D-A explicitly declines to rule on AMB-008 or AMB-009.
  - **No scope was widened.** M7D-B's time-axis projection is display positioning of
    supplied timestamps, the same class as M4D-F, and does not extend the closed
    derivation list beyond presentation.
  - **No M3 scenario data changed.**

#### v1.4 entry

- **Type:** discovered defect (revision rule §1.3 clause 3 — a planning document is wrong
  on its own terms). **This is NOT a scope grant.** No new PAD is required, because the
  frozen baseline already mandates the behaviour; the defect is that a second frozen
  document failed to list it.

- **Defect (D5):** the frozen baseline contradicts itself on map position.

  `task1-requirements.md`, HMI-FR-002 (Mandatory), expected behaviour states:

  > Vehicles drawn at `x/y` **or interpolated along `segment_id`**.

  and acceptance criterion 2 requires:

  > Every vehicle in state appears exactly once.

  `task1-data-contract.md` E-01 describes `VehicleState.position.offset_m` as
  "distance along segment, **for map interpolation**".

  But the **closed derivation list** in `task1-data-contract.md` §12 listed only eight
  derivations, none of which is a map coordinate. The scope-control skill requires that
  list to be closed and auditable, so an implementer reading §12 alone must conclude that
  interpolation is forbidden — while FR-002 mandates it.

- **How it was found:** M4 browser verification. Every one of the eleven M3 scenarios
  supplies `segment_id` and `offset_m` but no `x`/`y`, so the Mine Map rendered topology
  with **zero** vehicles placed and every vehicle listed as `POSITION UNAVAILABLE`
  ("2 vehicles · 0 positioned"). M4 followed §12 and the prohibition it was given, and in
  doing so did not satisfy FR-002 acceptance criterion 2. The tension was reported rather
  than resolved by implementation.

- **Impact:** M4's Mine Map is a partial non-conformance with HMI-FR-002 until corrected.
  No safety value, no operational value and no other screen is affected — the defect is
  confined to where a marker is drawn.

- **Correction:**
  1. `task1-data-contract.md` §12 closed derivation list gains **item 9**, the display-only
     map coordinate, so the list matches FR-002 and E-01.
  2. **M4D-F** (§10) records the permitted transform, its inputs, and the explicit
     prohibitions that bound it.
  3. The M4 Mine Map is updated to perform the transform.

- **Files affected:**

  | File | Correction |
  |---|---|
  | `requirements/DECISIONS.md` | This entry; §1.0 row; new M4D-F in §10 |
  | `requirements/task1-data-contract.md` | §12 closed derivation list: item 9 added |
  | `CLAUDE.md` | Decision-register pointer extended to M4D and M5D |

- **What did not change:**
  - **No requirement changed.** HMI-FR-002 is quoted, not amended; its statement,
    expected behaviour and acceptance criteria are untouched. Every other requirement is
    untouched.
  - **No contract type changed.** `VehiclePosition`, `TopologySegment`, `MineTopology`,
    `AppState` and `AppStatePatch` are byte-identical. Only the prose derivation list
    gained an item.
  - **No architecture decision changed.** PAD-A..G, MAD-A..G, MID-A..F and M4D-A..E stand.
  - **No ambiguity was resolved.** AMB-001, AMB-004, AMB-008, AMB-009 and AMB-014 remain
    open. In particular this says nothing about `h_safe` units.
  - **No scope was widened.** Task 1 gains no computation it did not already owe under
    FR-002. The Task 1 / Task 2 split is untouched.
  - **No M3 scenario data changed.**

#### v1.3.1 entry

- **Type:** discovered defect (revision rule §1.3 clause 3). **Metadata only.**

- **Defect (D4):** the §1.2 *Baseline state* block was never updated when the baseline was
  revised to v1.3 and when M2 and M3 were implemented. It read:

  > - Frozen. Current version v1.2.
  > - **Implementation status:** ... M2 has not started; no provider, no contract types,
  >   no normalization layer, no application state, no screen exists.

  Both statements were false. The baseline had been at v1.3 since the M3 proposal
  correction pass, and M2 and M3 were complete and approved. The block also omitted
  MID-A..MID-F and M4D-A..M4D-E from the decision inventory.

- **How it was found:** re-reading the register during the M4 correction pass. Reported
  to the project owner rather than silently corrected, and corrected only on explicit
  instruction.

- **Impact:** documentation only. §1.2 is a summary of state recorded authoritatively
  elsewhere in this register — §1.0 already carried the v1.3 row, and §7, §8 and §10 carry
  the decisions themselves. No implementation, requirement or decision was ever taken from
  the stale block. The risk was misdirection of a future reader, not a wrong build.

- **Correction:** §1.2 restated to reflect Planning Baseline v1.3; M1, M2 and M3 complete;
  M4 not started; and the full decision inventory including MID-A..F and M4D-A..E.

- **Files affected:**

  | File | Correction |
  |---|---|
  | `requirements/DECISIONS.md` | This entry; §1.0 row; §1.2 baseline-state block |

- **What did not change:**
  - **No requirement changed.** All 41 mandatory and 7 optional requirements are untouched.
  - **No contract changed.** The frozen data contract, `AppState` and `AppStatePatch` are
    untouched.
  - **No decision changed.** PAD-A..G, MAD-A..G, MID-A..F and M4D-A..E are unaltered in
    substance; §1.2 merely now counts them.
  - **No ambiguity was resolved.** AMB-004, AMB-008, AMB-009 and AMB-014 remain open.
  - **No architecture changed.**
  - **No scope boundary changed.**
  - **The authoritative specification is unchanged.**
  - The baseline version itself is **not** re-frozen at a new number for content reasons;
    v1.3.1 records a metadata correction to the v1.3 baseline, not a new baseline.

#### v1.3 entry

- **Reason for revision:** two items arising from the M3 proposal review.

  1. **`mock-scenarios/SKILL.md` was truncated** — 69 lines, one unclosed code fence,
     ending mid-sketch at the `Scenario` structure. Every section after "Scenario
     Structure" was absent. The same defect class as the `realtime-data` skill in v1.1.
     Completed in this pass without inventing requirements.
  2. **M3 implementation decisions approved.** Six decisions were put to the project owner
     during the M3 proposal review and approved. Recorded as MID-A..MID-F (§8) so
     implementation rests on the register rather than on conversation history. One of them,
     MID-C, defines patch deletion semantics that the frozen contract left open.

- **Files affected:**

  | File | Correction |
  |---|---|
  | `.claude/skills/mock-scenarios/SKILL.md` | Completed: 69 to 288 lines, 12 sections, fences closed |
  | `requirements/DECISIONS.md` | This entry; new §8 (MID-A..F); baseline label to v1.3 |
  | `requirements/task1-requirements.md` | HMI-FR-019 verification split across M3/M4 (MID-D); baseline label to v1.3 |
  | `requirements/task1-traceability.md` | HMI-FR-019 row split across M3/M4; baseline label to v1.3 |
  | `requirements/task1-implementation-plan.md` | Baseline label to v1.3 |
  | `requirements/task1-data-contract.md` | Baseline label to v1.3 |
  | `requirements/task1-risks-and-ambiguities.md` | Baseline label to v1.3 |
  | `CLAUDE.md` | Baseline label to v1.3; MID pointer |

- **What did not change:**
  - **No functional requirement changed.** All 41 mandatory and 7 optional requirements
    retain their statements, sources and acceptance criteria. HMI-FR-019's statement and
    acceptance criteria are unchanged; only the milestone at which each criterion is
    *verified* was made explicit.
  - **No architecture decision changed.** PAD-A..G and MAD-A..G are unaltered.
  - **The frozen data contract is unchanged.** In particular `AppStatePatch` remains
    exactly `Partial<AppState>` as contract §13 specifies, and `AppState` entities remain
    unwrapped. MID-B and MID-C were deliberately designed to avoid amending either.
  - **No scope boundary changed.** The closed derivation list stands.
  - **No ambiguity was resolved.** AMB-008, AMB-009 and AMB-014 remain open and untouched.
  - **The authoritative specification is unchanged.**

#### v1.2 entry

- **Reason for revision:** two items arising from the M2 proposal review.

  1. **AMB-014 discovered.** HMI-NFR-003 requires a "configurable timeout" after
     which data is flagged stale, but the specification never states its numeric value.
     This is a fourth unfilled threshold alongside NFR-001, NFR-002 and CV-004, and it was
     not previously recorded. It is more consequential than the other three: those affect
     sign-off only, whereas the staleness timeout changes *what an operator sees* — set too
     long, genuinely stale safety data reads as current, which is the exact failure NFR-012
     exists to prevent. Raised under §1.3 clause 3 (discovered defect).
  2. **M2 implementation decisions approved.** Seven decisions were put to the project
     owner during the M2 proposal review and approved. They are recorded here as MAD-A
     through MAD-G (§7) so that implementation does not rest on conversation history.

- **Files affected:**

  | File | Correction |
  |---|---|
  | `requirements/DECISIONS.md` | This entry; AMB-014 added to §4; PAD-G placeholder table extended; new §7 (MAD-A..G); baseline label to v1.2 |
  | `requirements/task1-risks-and-ambiguities.md` | AMB-014 narrative added; baseline label to v1.2 |
  | `requirements/task1-requirements.md` | HMI-NFR-003 threshold notation records the placeholder; baseline label to v1.2 |
  | `requirements/task1-implementation-plan.md` | Baseline label to v1.2 |
  | `requirements/task1-traceability.md` | HMI-NFR-003 row records the placeholder; baseline label to v1.2 |
  | `requirements/task1-data-contract.md` | Baseline label to v1.2 |
  | `CLAUDE.md` | Baseline label to v1.2; PAD range and known placeholder list updated |

- **What did not change:**
  - **No functional requirement changed.** All 41 mandatory and 7 optional requirements
    retain their statements, sources, acceptance criteria and verification methods.
    HMI-NFR-003's statement is unchanged; only the notation recording that its threshold is
    an unfilled placeholder was added.
  - **No existing architecture decision changed.** PAD-A through PAD-G are unaltered in
    substance; PAD-G's placeholder table gained one row, which is what PAD-G exists to hold.
  - **No scope boundary changed.** The Task 1 / Task 2 split and the closed derivation list
    are untouched.
  - **No data contract message changed.** Extensions E-01..E-20 stand as written.
  - **No ambiguity was resolved.** AMB-008, AMB-009 and AMB-004 remain open and untouched;
    AMB-014 is *added* as open, not answered.
  - **The authoritative specification is unchanged:**
    `docs/FOG_ORCHESTRATOR_Task1_HMI_Requirements.pdf`, unmodified, at the same path.

#### v1.1 entry

- **Reason for revision:** the governing project instructions moved from `docs/CLAUDE.md`
  to `CLAUDE.md` at the repository root. Every live citation of the old path became stale.
  Two cross-references in the root `CLAUDE.md` were also numerically short: it cited
  "PAD-A through PAD-F" when PAD-G exists, and "five planning documents" when the
  baseline contains six. Discovered during the post-relocation repository re-inspection and
  raised under the §1.3 revision rule, clause 3 (*discovered defect — a planning document is
  found wrong on its own terms*).

- **Files affected:**

  | File | Correction |
  |---|---|
  | `CLAUDE.md` | "PAD-A through PAD-F" to "PAD-A through PAD-G"; "five planning documents" to "six planning documents"; baseline label to v1.1 |
  | `requirements/DECISIONS.md` | 3 live path citations updated; this revision-history section added; baseline label to v1.1 |
  | `requirements/task1-requirements.md` | 2 live path citations updated; baseline label to v1.1 |
  | `requirements/task1-implementation-plan.md` | 1 live path citation updated; baseline label to v1.1 |
  | `requirements/task1-risks-and-ambiguities.md` | Baseline label added at v1.1 (the document previously carried none) |
  | `requirements/task1-traceability.md` | Baseline label to v1.1 |
  | `requirements/task1-data-contract.md` | Baseline label to v1.1 |

  The baseline is a single versioned set, so all six documents carry the v1.1 label even
  where a document had no other correction. `task1-traceability.md` and
  `task1-data-contract.md` were otherwise untouched.

- **Nature of this revision:** **documentation and path consistency correction only.**

- **What did not change:**
  - **No functional requirement changed.** All 41 mandatory and 7 optional requirements
    retain their statements, sources, acceptance criteria and verification methods.
  - **No architecture decision changed.** PAD-A through PAD-G are unaltered in substance,
    ownership and revisit conditions.
  - **No scope boundary changed.** The Task 1 / Task 2 split, the closed derivation list and
    the scope-control decision rule are untouched.
  - **No data contract changed.** All contract messages and extensions E-01..E-20 stand.
  - **No ambiguity resolution changed.** AMB-012 and AMB-013 remain CLOSED; the ten open
    items remain open at unchanged severity, ownership and provisional position.
  - **No risk, assumption or milestone content changed.**
  - **The authoritative specification is unchanged:**
    `docs/FOG_ORCHESTRATOR_Task1_HMI_Requirements.pdf`, unmodified, at the same path.

- **Historical references preserved:** citations of `docs/CLAUDE.md` inside the AMB-012
  CLOSED entries in this file and in `task1-risks-and-ambiguities.md` intentionally describe
  the repository state at the time of the earlier correction pass and are left as written,
  each annotated with the later relocation. They are history, not live pointers.

### 1.1 Contents

| Document | Role |
|---|---|
| `requirements/task1-requirements.md` | Requirement extraction, acceptance criteria, verification methods |
| `requirements/task1-traceability.md` | Requirement-to-implementation-to-verification matrix |
| `requirements/task1-data-contract.md` | Conceptual typed data contract and provider interface |
| `requirements/task1-implementation-plan.md` | Milestones M1–M13 |
| `requirements/task1-risks-and-ambiguities.md` | Risks, ambiguities, assumptions |
| `requirements/DECISIONS.md` | This register |

### 1.2 Baseline state

Corrected in v1.3.1; decision inventory and version updated in v1.4; milestone status and M5/M6/M7 decision inventory corrected in v1.5 (defects D6, D7).

- Frozen. **Current version v1.9.**
- Content: 41 mandatory requirements, 7 optional, 20 data-contract extensions (E-01..E-20),
  **14 ambiguities (2 closed, 12 open)**, 12 risks, 14 assumptions (1 withdrawn).
- Decision inventory:
  - 7 provisional architecture decisions — PAD-A..G (§2)
  - 7 M2 approved architecture decisions — MAD-A..G (§7)
  - 6 M3 approved implementation decisions — MID-A..F (§8)
  - 6 M4 approved implementation decisions — M4D-A..F (§10)
  - 3 M5 and 2 M6 implementation decisions — M5D-A..C, M6D-A..B (§11)
  - 5 M7 approved implementation decisions — M7D-A..E (§12)
  - 3 M8 approved implementation decisions — M8D-A..C (§13)
  - 1 registered planning gap — GAP-ROLE-001 (§13)
  - 6 M9 approved implementation decisions — M9D-A..F (§14)
  - 3 M10 approved implementation decisions — M10D-A..C (§15)
  - 4 M11 approved verification decisions — M11D-A..D (§16)
- **Implementation status:**
  - **M1 Foundation — COMPLETE and approved.** React/Vite/TypeScript frontend, FastAPI
    backend, `GET /api/health`, connectivity proof, lint/type-check/test.
  - **M2 Typed Data Foundation — COMPLETE and approved.** Contract types both sides,
    runtime validation, normalization, `Sourced<T>`, freshness configuration,
    `DataProvider` interface declaration, backend Pydantic mirrors, cross-language
    fixtures.
  - **M3 Mock Provider and Scenarios — COMPLETE and approved.** `MockDataProvider`,
    deterministic scheduler, injected clock, scenario registry, eleven authored scenario
    files, patch assembly with explicit deletion semantics.
  - **M4 HMI Application State and Operations Overview — COMPLETE.** Application state
    store, provider host, render-time freshness, application shell, navigation, S1
    Operations Overview, mine map, scenario picker, S2–S6 placeholders.
  - **M5 Vehicle Detail (S2) — COMPLETE.** Safety envelope, vehicle state, headway,
    occupied segment, per-vehicle communication, provenance. S2-b recent trend is a
    declared partial non-conformance (M5D-C).
  - **M6 Bottleneck & Queue (S3) — COMPLETE.** Bottleneck ranking by supplied score,
    queue and utilization display, supplied history and forecast drawn distinctly,
    supplied arrival decisions. No metering control (M6D-B).
  - **M7 Dispatch & Slots (S4) — COMPLETE.** Slot conflicts, slot timeline over supplied
    times, dispatch assignments, provenance. FR-010 AC3 is a declared partial
    non-conformance pending M9 (M7D-C).
  - **M8 Alerts & System Modes — COMPLETE.** Merged supplied and HMI data-path alerts,
    alert provenance, dedicated alert list, DEGRADED display floor. FR-015 deferred
    (M8D-C); stale alerting inactive while AMB-014 is open (M8D-B).
  - **M9 Event Logging and Replay (S5) — COMPLETE.** Append-only event log, session
    recorder, `ReplayProvider`, replay clock, S5 timeline. NFR-007 persistence is a
    declared non-conformance (M9D-A); FR-015 acknowledgement remains deferred (M9D-F).
  - **M10 Diagnostics (S6) — COMPLETE.** Supplied communication health, freshness by
    message type, backend health kept separate from feed health, validation failures
    surfaced read-only. With S6 the six mandatory HMI screens are all implemented.
  - **M11 Final NFR / Requirements Verification — COMPLETE.** NFR-009 verified at
    50 vehicles / 20 nodes by test and in a real browser; NFR-004 recovery coherence,
    NFR-012 cross-screen feed-stop sweep, NFR-008 greyscale audit, NFR-005 architecture
    inspection record, NFR-010 portability record, and NFR-001/NFR-002 measurement
    reports. The traceability matrix was rebuilt (D12). **No application defect was found
    by scale testing.** Statuses: 23 PASS, 11 PARTIAL, 3 BLOCKED, 2 NOT VERIFIABLE YET,
    2 NOT STARTED, across 41 mandatory requirements.
  - M12 onward — not started.
- **Unresolved and load-bearing:** AMB-004 (NFR-001/NFR-002 thresholds), AMB-008 (may the
  HMI issue commands), AMB-009 (meaning of "override"), AMB-014 (NFR-003 staleness
  timeout). None may be resolved by implementation; PAD-G governs.

### 1.3 Revision rule

The baseline changes only by one of:

1. **Authoritative clarification** — the specification owner or Task 2 integration team
   confirms or contradicts an item here. Record the answer, close the item, bump to v1.x.
2. **Scope grant** — the team explicitly widens Task 1. Must be recorded as a new PAD with
   an owner, never assumed from silence.
3. **Discovered defect** — a planning document is found wrong on its own terms.

Every revision updates this register first, then the affected documents. Silent edits to a
planning document without a register entry are defects.

---

## 2. Provisional Architecture Decisions

Binding until explicitly overturned. "Provisional" means *decided and in force*, not
*undecided* — implementation proceeds on these, and only an authoritative statement
revisits them.

### PAD-A — Task 1 is an HMI and supervisory visualization system
- **Decision:** Task 1 is the operator/control-room human-machine interface and supervisory
  visualization layer. It is not a controller, not a governor, and not a simulator.
- **Owner:** Task 1 team lead.
- **Basis:** specification §1, §3; `CLAUDE.md`; scope-control skill.
- **Impact:** frames every other decision here. Determines that the repository contains no
  control loop and no physics.
- **Revisit when:** the specification owner redefines Task 1's role. Not expected.
- **Status:** in force.

### PAD-B — Task 1 does not directly actuate vehicles or equipment
- **Decision:** until the authoritative specification or the integration team explicitly
  confirms otherwise, Task 1 issues no actuation, no drive-by-wire signal, and no direct
  equipment command. The HMI's outbound surface is limited to PAD-D acknowledgement.
- **Owner:** Task 1 team lead, with integration team.
- **Basis:** specification §3 (the vehicle controller enforces local limits), NFR-005
  (HMI loss must not disable Tier-1 safety), §2 out-of-scope list.
- **Impact:** `DataProvider` exposes `sendAcknowledgement` and nothing else. No command
  authorization design, no actuation path, no safety case for outbound control.
- **Tension to be aware of:** FR-010 says "issued", NFR-002 measures "command latency",
  NFR-007 logs "issued/received commands", §4 mentions "override". These read as an
  outbound path. See AMB-008 — that ambiguity is *open*, and PAD-B is the safe default
  chosen while it stands open.
- **Revisit when:** AMB-008 is answered. If the answer is that Task 1 must issue commands,
  M7 and M12 expand, an operator-authorization design is required, and NFR-011 and ROLE-001
  both grow.
- **Status:** in force.

### PAD-C — Task 1 may display externally supplied commands, recommendations, dispatch states and slot assignments
- **Decision:** displaying a command is in scope. Producing, selecting or optimizing one is
  not.
- **Owner:** Task 1 team lead.
- **Basis:** FR-009, FR-010, NFR-006; §2 out-of-scope list (dispatch and route optimization).
- **Impact:** `DispatchCommand` and `SlotState` are inbound-only. `DispatchCommand.state`
  distinguishes RECOMMENDED from ISSUED **for display**, with issuance performed elsewhere
  under PAD-B.
- **Revisit when:** PAD-B is revisited.
- **Status:** in force.

### PAD-D — Acknowledgement never implies a safety condition has been removed
- **Decision:** Task 1 may acknowledge HMI alerts and events where required. Acknowledgement
  changes display and audit state only. It never clears, suppresses or downgrades the
  underlying condition, and safety-critical local protection never depends on it.
- **Owner:** Task 1 team lead.
- **Basis:** FR-015 verbatim; NFR-005.
- **Impact:** `Alert.acknowledgeable` gates the action. Acknowledging a safety-critical alert
  is either refused or explicitly display-only. Every acknowledgement writes a timestamped
  event with operator identity (NFR-007). A test asserts that acknowledgement never removes
  a safety indicator.
- **Revisit when:** never, without an explicit safety review. This is the one decision here
  that is a safety property rather than a scope convenience.
- **Status:** in force.

### PAD-E — Digital Twin values arrive as external provider data
- **Decision:** every value belonging to Digital Twin computation, prediction, optimization
  or simulation is received through a provider. None is computed in this repository.
- **Owner:** Task 1 team lead; data supplied by Task 2.
- **Basis:** `CLAUDE.md`; scope-control skill decision rule; specification §2.
- **Impact:** covers `v_safe`, `h_safe`, `risk_level`, `active_constraint`,
  `bottleneck_score`, `criticality`, `lambda_vph`, `mu_vph`, queue forecasts, visibility
  forecasts, friction estimates, dispatch assignments, routes and slot conflict status.
  Enforced by the **closed derivation list** in `task1-data-contract.md` §12 — the HMI may
  derive only eight named values, all properties of the data path (age, staleness,
  connection status, stale/comm alerts, forced DEGRADED, sort orders, display-only
  comparisons of two supplied numbers). Anything not on that list must arrive from a
  provider. Every milestone's verification gate audits the diff against this.
- **Revisit when:** adding to the closed list. Requires re-running the scope-control
  decision rule and a register entry — never a silent addition.
- **Status:** in force.

### PAD-F — Undefined-source values use typed mock inputs, never invention
- **Decision:** current headway, `h_safe`, arrival plans, queue forecasts and operational
  KPIs must not be locally invented or algorithmically generated while their source is
  undefined. Each is represented by a typed contract entry and supplied as mock data during
  independent development.
- **Owner:** Task 1 team lead; sources to be confirmed by Task 2.
- **Basis:** AMB-001, AMB-002, AMB-003; scope-control skill.
- **Impact:** this is the practical guard on PAD-E. The failure mode it prevents is subtle:
  a chart looks bare, so a trend line gets extrapolated; a KPI is missing, so it gets
  aggregated from history the HMI happens to hold. Both are Task 2 algorithms arriving by
  convenience rather than by decision.
- **Corollary — mock data is recorded, not generated:** mock scenarios are pre-baked
  sequences. A generator that produces plausible physics or queueing behaviour is a Task 2
  algorithm in disguise, and is a defect. Checked explicitly in the M3 scope audit.
- **Revisit when:** each source is confirmed. Confirmation converts the mock to a live
  provider field; it does not authorize local computation.
- **Status:** in force.

### PAD-G — Missing numerical thresholds are configuration placeholders, never invented values
- **Decision:** where the specification omits a numeric threshold, no value is assumed.
  The threshold is carried as a named configuration placeholder marked as requiring
  authoritative confirmation. The requirement is measured and reported; it is not marked
  passed.
- **Owner:** Task 1 team lead, escalating to the specification owner.
- **Basis:** planning correction pass instruction 4; specification §11 (mandatory
  requirements are not waived without team-lead approval).
- **Placeholders currently open:**

  | Placeholder | Requirement | What is missing |
  |---|---|---|
  | `PLACEHOLDER_NFR001_REFRESH` | HMI-NFR-001 Performance | The requirement cell is empty in the specification |
  | `PLACEHOLDER_NFR002_COMMAND_LATENCY` | HMI-NFR-002 Command latency | The cell begins mid-sentence: "…conditions; measured separately from vehicle actuation latency." |
  | `PLACEHOLDER_CV004_LATENCY` | CV-004 Latency (optional) | No threshold stated |
  | `PLACEHOLDER_NFR003_STALE_TIMEOUT_MS` | HMI-NFR-003 Data freshness | The requirement mandates a "configurable timeout" but states no value (AMB-014) |

- **Impact:** two mandatory NFRs are measurable but not passable. M11 reports measured
  values and records them as unverifiable-as-specified. This does **not** block
  implementation — only sign-off.
- **Revisit when:** the thresholds are supplied, or a corrected specification is issued.
- **Status:** in force.

---

## 3. Closed Items

### AMB-012 — Specification filename — **CLOSED**
- **Was:** the planning instruction referenced `docs/TASK1_HMI_SPEC.pdf`.
- **Resolution:** confirmed by the project owner and by directory inspection — the
  authoritative specification is `docs/FOG_ORCHESTRATOR_Task1_HMI_Requirements.pdf` and
  there is no second Task 1 specification. That path is now cited verbatim in
  `docs/CLAUDE.md` (since relocated to the repository root as `CLAUDE.md`) and in all five
  planning documents. A repository-wide grep confirms zero
  remaining references to the old filename.
- **Owner:** project owner. **Closed in:** planning correction pass.

### AMB-013 — Skill directory naming — **CLOSED**
- **Was:** `.claude/skills/scope-controlclear/` held a `SKILL.md` whose frontmatter declared
  `name: scope-control`, confirming a directory-name typo.
- **Resolution:** renamed to `.claude/skills/scope-control/`. The target path was verified
  absent beforehand and the existing directory was moved, not copied — **no duplicate skill
  directory was created**. Planning-document references updated.
- **Residual (LOW, open):** five skill directories exist and are **empty**, with no
  `SKILL.md`: `hmi-frontend`, `mock-scenarios`, `realtime-data`, `replay`,
  `safety-visualization`. These are placeholders rather than naming errors, so they were
  left untouched. They need either content or removal. Owner: Task 1 team lead.
- **Owner:** Task 1 team lead. **Closed in:** planning correction pass.

---

## 4. Open Ambiguities

Full narrative in `task1-risks-and-ambiguities.md`. This table is the controlling summary.

| ID | Question | Severity | Owner | Provisional position | Blocks | Mock-workable |
|---|---|---|---|---|---|---|
| AMB-008 | Does the HMI *issue* commands, or only display them? | HIGH | Integration team + team lead | PAD-B: display and acknowledge only | M7 scope, M12 security design | **No** — architectural, not a data shape |
| AMB-004 | NFR-001 / NFR-002 thresholds absent from the specification | HIGH | Specification owner | PAD-G: named placeholders, nothing invented | NFR-001 and NFR-002 **sign-off only** | n/a — not a data question |
| AMB-014 | NFR-003 mandates a configurable staleness timeout but states no value | HIGH | Specification owner | PAD-G: named placeholder `PLACEHOLDER_NFR003_STALE_TIMEOUT_MS`; tests inject the threshold | No production default is authoritative | **Yes** — mechanism is testable with an injected threshold |
| AMB-001 | `h_safe` units (m or s); no current headway or lead-vehicle field in §9 | HIGH | Task 2 | Metres; `headway_current` and `lead_vehicle_id` as extension E-04 | M5 **sign-off** | **Yes** — typed mock, units re-checked at M12 |
| AMB-002 | No arrival-plan message exists in §9 | HIGH | Task 2 | `ArrivalPlan` extension E-10, supplied | M6 **sign-off** | **Yes** — typed mock |
| AMB-003 | Who computes the seven KPIs? | MEDIUM | Task 2 + team lead | `KpiSnapshot` E-16 supplied; HMI displays only | M4, M11 | **Yes** — typed mock |
| AMB-011 | Who owns mine topology, and in what format? | MEDIUM | Task 2 | `MineTopology` E-17 supplied or shared static config | M4 | **Yes** — mock topology |
| AMB-007 | Enum value sets for risk, criticality, surface state; reason-code vocabulary | MEDIUM | Task 2 | Four-level bands, `UNKNOWN` on every enum, unmapped codes rendered verbatim | M5, M6, M7 | **Yes** — `UNKNOWN` handling absorbs drift |
| AMB-005 | Vehicle mode vs system mode: same enum? aggregate? | MEDIUM | Task 2 | System mode supplied; HMI forces at least DEGRADED on data-path loss only | M8 | **Yes** — typed mock |
| AMB-010 | Who records replay telemetry, and with what retention? | MEDIUM | Team lead | HMI backend records the normalized stream, bounded window | M9 | **Partly** — design choice, testable on mock |
| AMB-009 | What is "override" in §4? | MEDIUM | Team lead | Out of scope until defined; acknowledgement only | M8, M12 | **No** — capability question |
| AMB-006 | Screen placement for scenario controls (S7 vs inside S6) | LOW | Team lead | S7, role-restricted | M3 | **Yes** — cosmetic |
| — | Five empty skill directories | LOW | Team lead | Left in place | none | n/a |

---

## 5. Standing Assumptions

Each is a place where the plan is wrong if the assumption is wrong. Numbering follows
`task1-risks-and-ambiguities.md` §D.

| # | Assumption | Governed by | If wrong |
|---|---|---|---|
| A-01 | `h_safe` is in metres | PAD-F | Plausible wrong value on a safety screen; M5 rework |
| A-02 | Task 2 supplies current headway and lead-vehicle ID | PAD-F | FR-005 unsatisfiable |
| A-03 | Task 2 supplies `ArrivalPlan` | PAD-F | FR-008 has no source; M6 blocked |
| A-04 | Task 2 supplies `KpiSnapshot` | PAD-F | FR-018 unsatisfiable, or Task 1 scope expands |
| A-05 | Task 2 supplies `queue_forecast` | PAD-E | S3 predicted queue trend cannot be shown |
| A-06 | Task 2 supplies `VisibilityForecast` | PAD-E | FR-011 forecast half unavailable |
| A-07 | Task 2 supplies `MineTopology` | PAD-E | Map hard-coded, breaking the architecture rule |
| A-08 | Task 2 supplies `Alert` for the four non-data-path categories | PAD-E | Alert generation moves into Task 1 — scope breach |
| A-09 | System mode is supplied, not aggregated by the HMI | PAD-E | Mode becomes an HMI judgement about fleet safety |
| A-10 | Task 1 does not issue commands | PAD-B | M7 and M12 expand; authorization design needed |
| A-11 | HMI backend owns replay recording | AMB-010 | M9 redesigned around Task 2 log files |
| A-12 | *(withdrawn — no performance target is assumed)* | PAD-G | n/a |
| A-13 | Enums are four-level bands with `UNKNOWN` | PAD-F | Visual state mapping wrong after integration |
| A-14 | Override is out of scope | AMB-009 | A mutating capability is missing from the plan |

---

## 6. Implementation Readiness

### 6.1 Genuinely blocked

| Item | Blocks | Why mock data does not help |
|---|---|---|
| AMB-008 / PAD-B | **M7 scope**, M12 security design | Whether an outbound command path exists is architecture, not a data shape. Mock data can carry a command either way; it cannot decide whether the HMI is allowed to send one. Building it speculatively is waste; discovering it at M12 is rework. |
| AMB-009 | M8, M12 (override only) | Same class: an undefined mutating capability. |
| AMB-004 / PAD-G | NFR-001 and NFR-002 **sign-off** | Not an implementation blocker. Work proceeds; the requirements simply cannot be marked passed. |

### 6.2 Workable on typed mock data

Everything else. AMB-001, AMB-002, AMB-003, AMB-005, AMB-006, AMB-007, AMB-010 and AMB-011
are all **data-shape** questions. Each has a typed contract entry and a mock supply, so
M1–M11 proceed on mock data exactly as `CLAUDE.md` requires, and integration at M12 is
a provider swap rather than a rewrite.

The residual risk is honest and bounded: each of these can be *wrong* at integration —
wrong units, wrong enum members, a differently-shaped message. The normalization layer
exists to absorb that, and the M12 contract-conformance suite exists to find it. What none
of them can do is stall M1.

### 6.3 Recommended before M1 begins

1. Answer **AMB-008** — it is the only open item that changes the architecture.
2. Publish `task1-data-contract.md` and its twenty extensions (E-01..E-20) to the Task 2
   team. Seven whole messages in it are absent from specification §9; the sooner Task 2 sees
   the shapes, the smaller the M12 gap.
3. Request the **AMB-004** thresholds, or a corrected specification.

Items 2 and 3 can run in parallel with M1. Only item 1 is worth waiting on, and only for M7.

---

## 7. M2 Approved Architecture Decisions

Put to the project owner during the M2 proposal review and **approved**. Recorded here so
implementation rests on the register rather than on conversation history. These govern M2
onward and are binding at the same level as the PADs.

### MAD-A — `zod` is approved for runtime validation
- **Decision:** `zod` is an approved **production** dependency of the frontend, used to
  validate untrusted provider payloads before normalization.
- **Rationale:** TypeScript types erase at compile time and provide nothing at runtime.
  The capability `zod` supplies that hand-written guards structurally cannot is a *single
  source of truth* — one schema yields both the validator and the inferred type, so the two
  cannot silently diverge. The rejected alternative was roughly 700–900 lines of hand-written
  guards for 15 nested messages, whose failure mode is a guard that passes data its type
  says is impossible.
- **Scope:** frontend only. The backend already has Pydantic v2; **no new backend
  dependency** is approved.
- **Revisit when:** validation moves out of the browser, or `zod` proves inadequate for a
  contract shape.

### MAD-B — Contract types live at `frontend/src/contracts/`
- **Decision:** approved **in place of** the frozen implementation plan's indicative
  `shared/contracts/*.ts`.
- **Rationale:** a top-level `shared/` holding only TypeScript would have exactly one
  consumer — the frontend build — while adding a path alias and build configuration for no
  present benefit. The plan's file list is prefixed "likely required" and is indicative.
- **Note:** this is a deviation from the frozen plan's file list, approved explicitly rather
  than assumed.

### MAD-C — `contracts/fixtures/*.json` is the shared cross-language artifact
- **Decision:** a top-level `contracts/fixtures/` directory holds one minimal valid payload
  per contract message plus invalid variants, parsed by **both** the TypeScript tests and
  the Python tests.
- **Rationale:** this is the one genuinely cross-language artifact in the project. It is
  what converts the backend Pydantic mirrors from dormant code into an active guard against
  TypeScript/Pydantic drift, satisfying the M2 definition of done ("a type on both sides").
- **Constraint:** fixtures are **contract-shape examples**, minimal and non-operational.
  They are not mock scenarios; scenarios are M3.

### MAD-D — `frontend/src/config/freshness.ts` is the typed configuration interface
- **Decision:** approved in place of the plan's indicative `config/freshness.json`.
- **Hard constraint:** it **MUST NOT contain an invented authoritative timeout.** The
  staleness threshold is carried as the placeholder `PLACEHOLDER_NFR003_STALE_TIMEOUT_MS`
  under PAD-G and AMB-014. No production default is authoritative.
- **Rationale for a typed module over JSON:** it can carry the placeholder marking and its
  non-authoritative warning at the definition site, which a bare JSON file cannot. NFR-003's
  requirement is that the timeout be *configuration rather than a component literal*; a typed
  configuration module satisfies that.

### MAD-E — Raw wire types use the contract's snake_case representation
- **Decision:** types representing the external payload as it arrives keep the field names
  written in `requirements/task1-data-contract.md` — `source_id`, `age_ms`, `visibility_m`.
- **Rationale:** the raw type's job is to describe what the producer actually sends.
  Renaming at the boundary would make the schema harder to check against the contract.

### MAD-F — Normalized domain types use camelCase
- **Decision:** types produced by normalization use camelCase — `sourceId`, `ageMs`.
- **Rationale:** matches the idiom M1 established (`latencyMs`), and the difference between
  the two families makes "has this been normalized yet?" visible in the type name itself.
- **Consequence:** the naming difference between the frozen contract's TypeScript snippets
  and the domain types is **intentional and approved**, not drift. Structure, nullability and
  enum membership remain exactly as the contract specifies.

### MAD-G — AMB-014 is approved for registration
- **Decision:** NFR-003's missing staleness timeout is registered as AMB-014 (§4) and its
  placeholder added to the PAD-G table (§2).
- **Rationale:** NFR-003 mandates a configurable timeout but states no value. Under PAD-G no
  value may be invented.
- **See:** AMB-014 in §4 and the narrative in `task1-risks-and-ambiguities.md`.

### Acknowledgement boundary — recorded under MAD

`DataProvider.sendAcknowledgement()` is retained in the M2 interface declaration because it
is explicitly supported by the frozen contract §13 and permitted by **PAD-D**.

Its semantics are exactly: **HMI alert/event acknowledgement only.**

It must **not**:

- issue vehicle commands
- override safety
- change vehicle control state
- modify `v_safe`
- modify `h_safe`
- trigger dispatch
- actuate equipment

Acknowledgement changes display state and writes an audit record (NFR-007). It never clears,
suppresses or downgrades the underlying condition, and safety-critical local protection never
depends on it (FR-015, PAD-D).

**AMB-008 and AMB-009 remain unresolved and are not resolved by this decision.** Retaining
an acknowledgement method is not a ruling on whether the HMI may issue commands, nor on what
"override" means. PAD-B's safe default continues to hold.

---

## 8. M3 Approved Implementation Decisions

Put to the project owner during the M3 proposal review and **approved**. Binding at the
same level as the PADs and MADs.

### MID-A — `frontend/src/data/patch.ts` is shared data-path infrastructure
- **Decision:** patch assembly lives outside the provider boundary, in the shared data
  path alongside validation and normalization.
- **Rationale:** M2 delivered per-message normalizers but nothing that assembles a
  `Partial<AppState>` from them — a gap found during M3 planning. Mock (M3), Replay (M9)
  and Live (M12) all need the identical path. Placing it inside `MockDataProvider` would
  guarantee three divergent copies, and would break the architecture rule that validation
  and normalization are shared rather than per-provider.
- **Consequence:** M3 delivers infrastructure that is arguably M2 work. Recorded here so
  it is visible as such rather than smuggled in.

### MID-B — `Sourced<T>` is applied at the rendering boundary, not inside `AppState`
- **Decision:** approved option (c). The frozen `AppState` shape is **unchanged** —
  entities are not wrapped in `Sourced<T>`. Freshness and provenance are derived at the
  rendering boundary in later HMI milestones, from each message's own timestamp together
  with the approved `Sourced<T>` semantics.
- **Context — a genuine tension in the frozen contract:** §1 states that "a component that
  renders a raw number instead of a `Sourced` value is a defect", while §12 defines
  `AppState` as holding bare domain objects. Both cannot hold literally.
- **Rationale:** 11 of the 15 contract messages already carry their own `timestamp`, so
  freshness is derivable per entity without restructuring state. Wrapping `AppState` would
  ripple through every later milestone for no capability gain.
- **Hard constraint:** the frozen contract is **not** amended to resolve this. The tension
  is recorded and managed, not edited away.
- **Revisit when:** M4 renders freshness and shows whether render-time derivation is
  sufficient in practice.

### MID-C — Patch deletion semantics are explicit
- **Decision:** a missing entity in a partial patch means **NO CHANGE**. It must never be
  interpreted as deletion. Deletion is represented explicitly, through a separate
  deletions channel carried alongside the patch.
- **Rationale:** `Partial<AppState>` cannot distinguish "no news about this vehicle" from
  "this vehicle is gone". Left implicit, one of two failures is certain: entities that
  vanish from a screen because an update happened not to mention them, or entities that
  linger forever after they are genuinely removed. On a fleet-monitoring display, a
  silently vanishing vehicle is the more dangerous of the two.
- **Constraint honoured:** `AppStatePatch` remains **exactly** `Partial<AppState>` as
  contract §13 specifies. The deletions channel is a sibling, not a redefinition, so the
  frozen contract type survives verbatim.
- **Consequence:** this requires a small change to the M2 `UpdateListener` signature —
  see §9. Reported rather than applied silently.
- **Verification:** explicit deletion semantics carry their own test.

### MID-D — `ScenarioPicker.tsx` defers to M4
- **Decision:** M3 delivers the headless half of FR-019 — `ScenarioDescriptor[]`, the
  scenario registry, and scenario loading/selection APIs. The React picker UI is M4.
- **Consequence:** **HMI-FR-019 is partially verified at M3 exit and completed at M4.**
  M3 satisfies acceptance criterion 1 (named scenarios exist for all five families) and
  criterion 2 (loading re-drives state through normalization). Criterion 3 (active
  scenario name displayed) requires the M4 UI.
- **Rationale:** the frozen M3 plan lists a picker component, but a picker needs a React
  store to drive, and no store exists until M4. Building UI in M3 would also contradict
  the M3 scope boundary.

### MID-E — Scenario files live at `frontend/src/mocks/`
- **Decision:** approved in place of the frozen plan's indicative root `mocks/`.
- **Rationale:** consistent with MAD-B. Scenario data is consumed only by the frontend.
  The genuinely cross-language artifact remains `contracts/fixtures/` (MAD-C).

### MID-F — No runtime seed
- **Decision:** the mock provider takes no seed parameter.
- **Rationale:** nothing is generated at runtime, so a seed would have nothing to seed.
  An unused seed parameter implies generation happens somewhere, which is precisely the
  impression the mock layer must not give. Determinism comes from ordered authored steps,
  an injected clock and an injected scheduler.
- **Constraint:** no random number generation anywhere in the mock path. Audited.


---

## 9. Known M2 change required by M3

**One M2 source change is required**, arising from MID-C.

`frontend/src/providers/DataProvider.ts` currently declares:

```ts
export type UpdateListener = (patch: AppStatePatch) => void;
```

`AppStatePatch` is `Partial<AppState>`, which structurally cannot carry a deletion. To
satisfy MID-C without amending the frozen contract, `UpdateListener` receives a wrapper
that carries the unchanged `AppStatePatch` alongside an explicit deletions channel.

- **Files touched:** `frontend/src/providers/DataProvider.ts` (type declaration) and
  `frontend/src/providers/DataProvider.test.ts` (one assertion).
- **What does not change:** `AppStatePatch` itself, `AppState`, the frozen contract, and
  every other M2 module.
- **Status:** reported for approval before implementation, per the M3 proposal's
  commitment that any required M2 change would return as a revision rather than a quiet
  edit.
---

## 10. M4 Approved Implementation Decisions

Put to the project owner during the M4 proposal review and **approved**. Binding at the
same level as the PADs, MADs and MIDs. Recorded here before implementation, per the
revision rule in §1.3.

### M4D-A — S1 verification spans multiple scenarios; M3 scenario data is not modified
- **Decision:** Operations Overview is verified across several existing M3 scenarios
  rather than against one scenario amended to contain every panel's subject. No scenario
  file is changed to manufacture S1 activity.
- **Basis:** a message-type audit of the eleven M3 scenarios found that no single
  scenario emits every slice S1 renders. `Alert` appears only in `envelope-violation` and
  `slot-conflict`; `BottleneckState` and `ArrivalPlan` only in `fleet-density-high`;
  `VisibilityForecast` only in `fog-rolling-in`; `KpiSnapshot` only in `nominal`; no
  scenario emits `EventRecord`. `nominal` emits neither `Alert` nor `BottleneckState`.
- **Rationale:** a nominal mine legitimately has no active alert and no active
  bottleneck. Adding authored alerts to `nominal` to fill S1 panels would corrupt the
  evidential value of the scenario and would reopen frozen M3 data for a presentation
  convenience.
- **Consequence:** `nominal` must render honest empty states — `NO ACTIVE ALERTS`,
  `NO ACTIVE BOTTLENECK` — and those empty states are first-class product states with
  their own tests. Alerts, bottlenecks, fog/visibility, slot conflicts and unsafe-speed
  conditions are exercised from the scenarios that already carry them, and the mapping
  from state to scenario is recorded as verification evidence.
- **Owner:** Task 1 team lead.
- **Revisit when:** a later milestone needs a scenario whose subject no existing scenario
  carries — `EventRecord` for S5 replay is the known case. That is new authored data for
  that milestone, not an amendment made to serve S1.
- **Status:** in force.

### M4D-B — Unconfigured freshness threshold renders an explicit banner
- **Decision:** when `VITE_PLACEHOLDER_NFR003_STALE_TIMEOUT_MS` is not configured, the
  application shell shows a persistent banner reading **FRESHNESS THRESHOLD NOT
  CONFIGURED**, stating that data age is still shown, that stale classification is not
  evaluated, and that no authoritative timeout has been configured. Data ages continue to
  display. `OK`/`STALE` classification is suppressed entirely.
- **Basis:** HMI-NFR-003 requires a configurable staleness timeout; the specification
  states no value. AMB-014 is UNRESOLVED. PAD-G forbids inventing a threshold.
  `config/freshness.ts` already fails rather than defaulting; this decision defines what
  the HMI does with that failure.
- **Rationale:** the alternative failure modes are both unacceptable. A silent default
  would present an unauthorized threshold as authoritative and nobody would notice. A
  blank or absent freshness display would let genuinely stale safety data read as
  current — the precise failure NFR-012 exists to prevent.
- **Consequence:** `frontend/.env.example` carries the variable, present but unset, and
  marked `DEVELOPMENT PLACEHOLDER — NOT AUTHORITATIVE`. A developer must consciously
  choose a development value; none is chosen for them. While `isAuthoritative` is false,
  anything rendering staleness marks the threshold provisional.
- **Owner:** specification owner supplies the authoritative value; Task 1 team lead owns
  the presentation.
- **Revisit when:** AMB-014 is closed by the specification owner. The open question
  recorded alongside it stands: whether one global timeout suffices, or whether message
  classes need separate ones.
- **Status:** in force.

### M4D-C — No UI testing dependencies are added for M4
- **Decision:** `jsdom`, `@testing-library/react` and other UI testing dependencies are
  **not** added in M4. Verification uses pure-function unit tests, `react-dom/server`
  render tests, and manual browser verification.
- **Basis:** dependency discipline in `CLAUDE.md` and the master engineering prompt;
  `react-dom/server` already carries M1's render tests without a DOM environment.
- **Rationale:** the substance of M4 — store merge, status derivation, scenario selection
  logic, alert ordering, freshness classification, violation detection, topology
  projection — is pure and fully testable with no DOM. Only the click binding on the
  scenario picker and navigation is left to manual verification, and that is a thin
  surface over logic that is itself tested.
- **Consequence:** M4 logic must be written as pure functions so it remains testable
  without a DOM. Every failure state gets a `renderToString` assertion against text.
  Browser verification per the testing and hmi-frontend skills is mandatory, not optional
  compensation.
- **Owner:** Task 1 team lead.
- **Revisit when:** interaction complexity justifies automated click testing — multi-step
  interactive flows, focus management, or a control whose behaviour cannot be expressed
  as a tested pure function.
- **Status:** in force.

### M4D-D — Application state binding structure
- **Decision:** the M4 binding is `MockDataProvider → ProviderHost → AppStateStore →
  useSyncExternalStore → React components`. No Redux, no Zustand, no additional state
  library. `ProviderHost` is the only module that directly imports a concrete provider.
- **Basis:** PAD-A, the architecture rule in `CLAUDE.md`, the task1-architecture skill,
  and `DataProvider.ts` property 4 — "selection by injection; a screen that imports a
  concrete provider is a defect".
- **Rationale:** `useSyncExternalStore` is a React built-in and is precisely the
  external-store subscription primitive. A state library would add a dependency for a
  capability already present.
- **Consequence:** components consume `AppState` and never receive a provider object.
  Patch application reuses the shared `data/patch.ts` merge rather than re-implementing
  patch semantics in the store.
- **Owner:** Task 1 team lead.
- **Revisit when:** M9 replay or M12 live integration introduces a state requirement the
  store cannot meet. Not expected — both arrive through the same `DataProvider` interface.
- **Status:** in force.

### M4D-E — Freshness is derived at the rendering boundary
- **Decision:** `AppState` entities remain unwrapped as the frozen contract §12
  specifies. Freshness is derived at render time from each entity's supplied timestamp,
  through the existing `data/sourced.ts` construction site. A display ticker drives
  re-render so displayed ages advance.
- **Basis:** MID-B, already approved for M3, applied at the point it takes effect.
- **Rationale:** avoids amending the frozen contract to resolve the §1/§12 tension, and
  avoids a second provenance mechanism.
- **Consequence:** the display ticker recomputes `ageMs` from supplied timestamps and
  nothing else. It must not generate, interpolate, extrapolate or advance any operational
  value — no `v_safe`, `h_safe`, friction, queue, bottleneck, dispatch, route or forecast.
  A ticker that moved a vehicle or decayed a supplied figure would be a simulation and is
  prohibited.
- **Owner:** Task 1 team lead.
- **Revisit when:** measurement shows render-time derivation is a performance problem.
  Optimize only after measuring (NFR-001/NFR-002 thresholds remain unresolved — AMB-004).
- **Status:** in force.

### M4D-F — Display-only map coordinate from supplied segment geometry
- **Decision:** the Mine Map may derive an `x`/`y` coordinate for a vehicle marker from
  **supplied** `segment_id`, **supplied** `offset_m` and **supplied** topology node
  geometry. This is a deterministic geometric visualization transform and nothing else.
- **Basis:** HMI-FR-002 mandates it ("Vehicles drawn at `x/y` or interpolated along
  `segment_id`"); E-01 supplies `offset_m` expressly for it; D5 (v1.4) added it to the
  closed derivation list as item 9.
- **Inputs — all supplied, none invented:**
  - `VehiclePosition.segmentId`
  - `VehiclePosition.offsetM`
  - `TopologySegment.fromNode`, `.toNode`, `.lengthM`
  - `TopologyNode.x`, `.y`
- **The transform:** locate the segment, take its endpoints' supplied coordinates, and
  place the marker at the supplied fraction `offsetM / lengthM` along the straight line
  between them. Pure, deterministic, and a function of supplied data only — the same
  inputs always produce the same point, and no clock, no history and no previous position
  participates.
- **Explicitly prohibited, and none of these is enabled by this decision:**
  trajectory prediction · future position estimation · speed calculation · movement
  interpolation over time · animation or tweening between updates · dead reckoning ·
  route planning · path optimization · dispatch optimization · safety-envelope
  computation · physics simulation · any Task 2 computation · modifying any supplied
  safety value.
- **Insufficient geometry is not a licence to guess.** If the segment id is absent or
  unknown, an endpoint node is missing, a node coordinate is absent, `offsetM` is absent,
  or `lengthM` is absent or not positive, the vehicle renders **POSITION UNAVAILABLE**.
  It is never placed at an endpoint "near enough", never at the segment midpoint, and
  never at a previous position.
- **Owner:** Task 1 team lead.
- **Revisit when:** topology gains real polyline geometry rather than two endpoints, or
  Task 2 begins supplying `x`/`y` directly. Supplied `x`/`y` always takes precedence over
  the transform.
- **Status:** in force.

<!-- D6: M4D-F was originally written into §8 (M3 decisions) by an insertion error in the
     M5 pass. Moved here, into §10 where the other M4 decisions live, by revision v1.5.
     The text is unchanged; only its location was wrong. -->

---

## 11. M5 and M6 Approved Implementation Decisions

Recorded retrospectively by revision v1.5 (defect D7). M5 Vehicle Detail and M6 Bottleneck
& Queue were implemented and approved without register entries. The decisions below were
taken during those milestones and are in force; recording them late does not change them.

### M5D-A — Vehicle selection is UI state, held by the shell
- **Decision:** the selected vehicle is an id held in `AppShell` component state. S2 reads
  the vehicle out of `AppState` on every render and never keeps a copy.
- **Rationale:** the hmi-frontend skill lists "selected vehicle" as local UI state and
  forbids duplicating operational domain data. Holding a vehicle object rather than an id
  would create a second copy that ages independently of the store.
- **Consequence:** a vehicle removed from supplied state after selection renders
  `VEHICLE NOT IN CURRENT STATE` rather than a remembered snapshot.
- **Status:** in force.

### M5D-B — `HmiContext` is exported for test mounting only
- **Decision:** `state/ProviderHost.tsx` exports `HmiContext` so screens can be mounted in
  tests against a controlled `AppStateStore` without starting a provider.
- **Rationale:** required to test screens with populated state under M4D-C, which forbids
  jsdom and Testing Library. The alternative — injecting data through props — would have
  changed production component signatures to serve tests.
- **Constraint:** production code uses `useHmi`. A component reading the context directly,
  or a second provider of it, is a defect.
- **Status:** in force.

### M5D-C — S2-b recent trend is not implemented; no local history is accumulated
- **Decision:** S2 renders `TREND DATA NOT SUPPLIED`. No client-side time series of
  observed vehicle values is accumulated.
- **Rationale:** the data contract supplies no per-vehicle history. `BottleneckState`
  carries supplied `queueHistory`; `VehicleState` carries nothing equivalent. A locally
  accumulated series is not supplied data, would duplicate operational state, and would
  diverge from the source across reconnects and scenario switches.
- **Consequence:** **S2-b (Mandatory) is a declared partial non-conformance.** It is
  satisfiable either by Task 2 supplying a vehicle history series, or by the M9 replay
  timeline. Not to be closed by local accumulation.
- **Status:** in force. Re-verify at M9.

### M6D-A — S3 ranks by supplied score and computes no queue value
- **Decision:** S3 orders bottlenecks by the supplied `bottleneckScore` and renders
  supplied queue, utilization, arrival and service rates verbatim. Supplied
  `queueHistory` and supplied `queueForecast` are drawn as distinct series.
- **Rationale:** contract §12 item 6 permits ordering by a supplied score. Queue
  prediction is Task 2's, and blending a supplied forecast into measured history would
  misrepresent which is which (FR-011 AC3 reasoning, applied to queues).
- **Constraint:** no bottleneck score, criticality band, queue evolution, arrival rate,
  service rate or forecast is computed locally. No trend is fitted.
- **Status:** in force.

### M6D-B — S3 renders no metering control
- **Decision:** FR-008 arrival-rate shaping is displayed from supplied
  `ArrivalPlan.activeDecisions` (HOLD / METER / RELEASE with reason codes). S3 offers no
  control to issue, change or clear a metering decision.
- **Rationale:** AMB-008 and AMB-009 are unresolved. A hold/release control would be
  command issuance, which PAD-B's safe default forbids.
- **Status:** in force. Unchanged by M7.

---

## 12. M7 Approved Implementation Decisions

Put to the project owner during the M7 proposal review and **approved**.

### M7D-A — S4 is display-only; no control surface exists
- **Decision:** S4 Dispatch & Slots renders supplied `DispatchCommand` and `SlotState`
  and offers no operational control. No Dispatch Now, Approve, Apply Slot, Override,
  Release, Hold, Send Command, Execute, Apply Change, Modify Route or Modify Target Speed.
  No form and no submit path.
- **Basis:** FR-009 and FR-010 are both worded as display obligations ("shall show").
  FR-010 AC4: "HMI never selects or optimizes an assignment." FR-009 AC5: "the HMI runs
  no slot solver." PAD-B's safe default holds.
- **AMB-008 / AMB-009:** both remain UNRESOLVED. The contract's own comment on
  `DISPATCH_STATES` is decisive — the enum "describes what the producer reports, nothing
  the HMI may do." Rendering `RECOMMENDED` versus `ISSUED` is producer-reported metadata
  and is **not** a ruling on whether the HMI may issue anything.
- **Constraint:** a test asserts S4 renders zero `<button>` and zero `<form>` elements.
- **Status:** in force.

### M7D-B — The slot time axis is a display projection over supplied timestamps
- **Decision:** slot bands are positioned from supplied `startTime` and `endTime` against
  a window derived from the same supplied timestamps. Slots are grouped by supplied
  `resourceId`; overlapping slots on one resource stack into separate rows.
- **Basis:** FR-009 AC1 requires "slots positioned on a real time axis" and AC4 requires
  overlapping slots to remain individually readable. Same class of transform as M4D-F:
  supplied values to pixel offsets.
- **Constraint:** no slot is generated, moved, merged, resolved or scheduled. Where a
  resource's supplied times are unusable, that resource renders a timeline-unavailable
  state naming the missing input; no time is guessed. This permission does not extend
  beyond positioning bands that were supplied.
- **Status:** in force.

### M7D-C — FR-010 AC3 is a declared partial non-conformance during M7
- **Decision:** FR-010 acceptance criterion 3 — "every displayed command also appears in
  the event log (NFR-007)" — **cannot be satisfied in M7 and is NOT claimed as passed.**
- **Basis:** no M3 scenario emits `EventRecord`, and the event log is S5, delivered at M9.
- **Prohibited remedies, explicitly:** manufacturing event records, building a fake event
  log, or duplicating dispatch rows into an event stream. Any of these would fabricate
  evidence of traceability that does not exist, which is worse than the gap.
- **Consequence:** S4 states the limitation on screen rather than implying completeness.
- **Status:** open. **Must be re-verified when M9 introduces event/replay infrastructure.**

### M7D-D — Test-local fixtures cover authored-data gaps; M3 scenarios are not modified
- **Decision:** the following are covered by fixtures inside `dispatchSlots.test.tsx`,
  not by adding authored scenario data: `ISSUED` dispatch state, every `SlotStatus` value
  beyond `RESERVED` and `CONFLICT`, missing or empty reason codes, null ETA, null route,
  null target speed, multi-row deterministic ordering, and the degraded states.
- **Basis:** extends M4D-A. `slot-conflict` is the authored happy path and already
  supplies a complete `DispatchCommand` and a genuine `CONFLICT` pair; changing it to
  manufacture additional S4 activity would corrupt the evidence it exists to provide.
- **Consequence:** **FR-010 AC2 (recommended versus issued) has no browser coverage** and
  must not be claimed as browser-verified. It is verified by fixture only. Authored data
  containing an `ISSUED` command will eventually be required — sensibly alongside the
  `EventRecord` data M9 needs.
- **Status:** in force.

### M7D-E — Route is rendered as a supplied node chain, not drawn on the map
- **Decision:** `DispatchCommand.routeNodeIds` renders as a textual node chain on S4. It
  is not drawn on the mine map in M7.
- **Rationale:** FR-002 owns the map and is S1. Drawing a route there is cross-screen work
  outside M7's scope. No route is calculated, optimized or redrawn in either place.
- **Status:** in force.

---

## 13. M8 Approved Implementation Decisions

Put to the project owner during the M8 audit and **approved**.

### M8D-A — HMI-originated COMM_LOSS and STALE_DATA are approved data-path derivations
- **Decision:** the HMI may originate alerts of exactly two categories — `COMM_LOSS` and
  `STALE_DATA` — and may raise the displayed system mode to at least `DEGRADED` on
  data-path loss. Nothing else.
- **Basis, all mandatory and all pre-existing:**
  - **FR-014 AC4** — "Stale-data and comm-loss alerts raised by the HMI from timestamp age;
    the other four originate from supplied state, never from an HMI-side safety or
    bottleneck calculation."
  - **FR-016 AC3** — "Loss of the data feed forces at least DEGRADED display regardless of
    the last supplied mode."
  - **OPS-003** — "On loss of central communication the HMI shall indicate degraded mode."
  - **NFR-012** — "global mode shows DEGRADED"; no value continues to read as current.
  - Closed derivation list items **4** and **5** already carry both.
  - `ALERT_ORIGINS` carries an explicit `HMI` origin: "The HMI may originate only
    STALE_DATA and COMM_LOSS (contract §8)."
- **Why this is not Task 2 computation:** both concern the HMI's own data path. The HMI is
  not deciding that a truck is unsafe or that a node is congested; it is reporting that its
  own feed went quiet or that a datum it holds has aged out. Refusing them would leave four
  mandatory requirements unmet and would produce exactly the frozen-display failure NFR-012
  exists to prevent.
- **Explicitly prohibited, and unchanged:** fabricating `UNSAFE_SPEED`, `UNSAFE_HEADWAY`,
  `BOTTLENECK_RISK` or `SLOT_CONFLICT`; assigning, promoting or computing a severity;
  computing risk; computing an operational system mode; any prediction or simulation.
- **Constraints:**
  - Derived alerts are **view data**. They are never written back into `AppState` or the
    provider — a derived alert stored beside a supplied one becomes indistinguishable from
    it on the next patch.
  - Derived alerts never overwrite, replace or suppress a supplied alert.
  - Every derived alert carries `origin: "HMI"` and is displayed as distinct from supplied.
  - `AppState.health.systemMode` is **never mutated**. The floor applies to the displayed
    result only.
- **Owner:** Task 1 team lead.
- **Status:** in force.

### M8D-B — STALE_DATA alerting is gated on the configured NFR-003 threshold
- **Decision:** a `STALE_DATA` alert is raised only when a freshness threshold is
  configured **and** a supplied, valid datum's age exceeds it. With no threshold
  configured: age is still shown, stale classification is suppressed, no `STALE_DATA`
  alert is raised, and the HMI states explicitly that stale alerting is inactive because
  no threshold is configured.
- **Basis:** AMB-014 is UNRESOLVED and PAD-G forbids inventing a value. M4D-B already
  defines the unconfigured display behaviour; this extends the same rule to alerting.
- **Consequence:** **the stale half of FR-014 AC4 cannot be exercised in production or in
  the browser while AMB-014 is open.** The mechanism is implemented and unit-tested with an
  injected threshold; activation is not claimed. Re-verify when AMB-014 closes.
- **Quality semantics are unchanged:** malformed is `INVALID`, never `STALE`; absent is
  `MISSING`, never `INVALID`; an `INVALID` datum is never also reported stale.
- **Status:** in force.

### M8D-C — FR-015 acknowledgment is deferred to M9
- **Decision:** M8 implements **no** acknowledgment control, and no audit or event
  infrastructure.
- **Basis:** FR-015 AC2 requires "a timestamped log event with operator identity
  (NFR-007)" and AC3 requires role gating per §4. Neither the event log (M9) nor any role
  infrastructure (GAP-ROLE-001) exists.
- **Rationale:** an acknowledgment that writes no audit record would breach NFR-007 the
  moment the control appeared. `DataProvider.sendAcknowledgement` remains declared and
  implemented but **uncalled by any UI**, exactly as through M4–M7.
- **Consequence:** **FR-015 is unmet after M8** and is not claimed. Likewise FR-016 AC2
  (mode-transition logging) remains unmet pending M9.
- **AMB-008 / AMB-009:** untouched. Deferring acknowledgment rules on neither.
- **Status:** open. Re-verify at M9.

### GAP-ROLE-001 — Registered planning gap: role gating has no owning milestone
- **Requirement:** ROLE-001 (Mandatory, derived) — "The HMI shall gate actions by role;
  override shall never be offered for safety-critical items." PDF §4 defines four roles
  (vehicle operator, control-room operator, safety/engineering reviewer,
  developer/tester) with distinct permissions.
- **Gap:** no milestone in `task1-implementation-plan.md` owns ROLE-001, and no role or
  identity infrastructure exists anywhere in the repository. It is a mandatory requirement
  that would currently be missed silently at completion.
- **Registered, not resolved.** No role infrastructure is invented in M8.
- **Interaction with AMB-009:** ROLE-001 mentions "override", whose meaning is AMB-009 and
  UNRESOLVED. The half of ROLE-001 that says override "shall never be offered for
  safety-critical items" is currently satisfied vacuously — the HMI offers no override at
  all, on any screen.
- **Also blocked by this gap:** FR-015 AC3.
- **Owner:** team lead — needs a milestone assignment. Sensibly M9, alongside the audit
  trail that FR-015 AC2 requires.
- **Status:** open, unowned.

---

## 14. M9 Approved Implementation Decisions

Put to the project owner during the M9 audit and **approved**.

### M9D-A — In-memory session recording; NFR-007 persistence is a declared non-conformance
- **Decision:** M9 records the session in the browser, in memory. No backend persistence,
  no storage design, no retention policy.
- **Basis:** AMB-010 asks who records replay telemetry, where it is stored and for how
  long, and is **UNRESOLVED**. Building a persistence store on an unconfirmed assumption
  risks building the wrong one.
- **What this satisfies:** FR-017 in full — a recorded session replays through every
  existing screen with no screen-level special-casing, scrubbing reproduces recorded
  state, replay is flagged globally, and replay is a third provider behind the same
  interface.
- **What this does NOT satisfy, and is not claimed:** **NFR-007's "persisted"**. The
  acceptance text requires command receipt, command issue, acknowledgement and every mode
  transition to "produce a **persisted** timestamped event visible in S5". Events are
  visible in S5 and timestamped, but they do not survive a page reload.
  **NFR-007 is therefore PARTIAL, not PASS.** Recording it as passed would misrepresent
  an audit-trail guarantee, which is the last thing to be optimistic about.
- **Re-verify when:** AMB-010 is resolved and persistent storage is implemented.
- **Status:** in force. NFR-007 persistence **open**.

### M9D-B — `AppState.events` keeps replace-whole semantics; the audit log lives outside it
- **Decision:** the frozen replace-whole behaviour of `AppState.events` is unchanged. A
  separate append-only log holds the audit trail.
- **Basis:** defect D8. Contract §13 makes `events` replace-whole, which is correct for
  "the events in this delivery" and unusable as an append-only trail.
- **Consequence:** `AppState.events` remains the per-delivery channel. The log appends
  from it and never truncates. Historical entries are never mutated, never reordered and
  never dropped by a subsequent patch.
- **Status:** in force.

### M9D-C — Only HMI-observable lifecycle and data-path events may be derived
- **Decision:** the recorder may derive events for what the HMI itself observed happening
  to its own state:
  - communication loss and recovery (`COMM_LOSS`, `RECOVERY`)
  - an alert appearing in state (`ALERT_RAISED`)
  - a supplied system-mode transition (`MODE_TRANSITION`)
  - a supplied dispatch command appearing in state (`COMMAND_RECEIVED`)
  - an acknowledgement, once a permitted acknowledgement path exists
    (`ALERT_ACKNOWLEDGED`)
- **Prohibited, and not derived:** `FOG_CHANGE`, `QUEUE_CHANGE`, `VIOLATION`. These
  classify operational meaning — deciding that a visibility number constitutes a fog
  *change*, or that a value constitutes a *violation*, is Task 2's judgement. They are
  recorded **only** when a producer supplies them as `EventRecord` data.
- **Rule:** never turn an arbitrary numeric change into an operational event
  classification. Observing that an entity *appeared* is a data-path fact; deciding what a
  value *means* is not.
- **Consequence:** with no authored `EventRecord` data, three of nine categories cannot
  appear. Recorded honestly rather than filled in.
- **Status:** in force.

### M9D-D — `sendAcknowledgement` updates the alert as well as emitting the event (D9 fix)
- **Decision:** `MockDataProvider.sendAcknowledgement(alertId, actor)` sets
  `Alert.acknowledged = { by, at }` on the named alert **and** emits the
  `ALERT_ACKNOWLEDGED` event.
- **Basis:** defect D9 — the patch carried only `events`, so the alert's acknowledged
  field was never set and `AlertRow`'s acknowledgement display was unreachable.
- **Unchanged prohibitions (PAD-D):** acknowledgement changes display and audit state
  only. It never clears, suppresses or downgrades the underlying condition, never issues a
  vehicle command, never overrides safety, never modifies `v_safe` or `h_safe`, never
  triggers dispatch and never actuates anything. Safety-critical alerts remain
  non-acknowledgeable.
- **Status:** in force.

### M9D-E — During replay the render clock follows the replay position
- **Decision:** while replaying, `clock.replayPosition` holds the selected replay time and
  `clock.now` equals it. Outside replay, `replayPosition` is null and live clock behaviour
  is exactly as before.
- **Basis:** design consequence D10. FR-017 AC1 requires scrubbing to *t* to reproduce the
  state recorded at *t*; freshness is part of that state. Aged against the wall clock,
  every replayed value would read stale, which would be a false safety signal about a
  moment that was in fact current.
- **Constraint:** the live display ticker must not advance the clock while a replay
  position is set. Enforced in the store so no caller can break it.
- **Status:** in force.

### M9D-F — No acknowledgement UI in M9
- **Decision:** M9 fixes the acknowledgement **state path** (M9D-D) but exposes **no**
  acknowledgement control to the operator.
- **Basis:** FR-015 AC3 requires role gating per §4, and **NFR-011 requires that gating to
  be enforced server-side, not merely hidden in the UI**. No role infrastructure exists
  anywhere (GAP-ROLE-001) and the backend has no role enforcement.
- **Explicitly rejected:** a frontend-only permission check. It would satisfy nobody,
  would be trivially bypassable, and would create the appearance of gating where there is
  none.
- **Consequence:** **FR-015 remains unmet after M9** and is not claimed. The provider
  method stays available and correct for the milestone that can gate it properly.
- **Status:** open. Blocked on GAP-ROLE-001 and NFR-011.

---

## 15. M10 Approved Implementation Decisions

Put to the project owner during the M10 audit and **approved**.

### M10D-A — Supplied message counters only; the closed derivation list stays at nine
- **Decision:** S6 displays `Health.messagesReceived`, `Health.messagesDropped` and
  `Health.latencyMs` **as supplied**. The HMI keeps **no** delivery or message counter of
  its own.
- **Basis:** S6-a requires "message counts and latency per component", and the contract
  supplies all three per component (E-15). No derivation is needed to satisfy it.
- **Why this was a question at all:** the M10 plan entry mentions "counters increment
  against a known scripted message sequence", which reads as an HMI-side counter. That
  would have been a **tenth** entry on the closed derivation list in
  `task1-data-contract.md` §12, and the scope-control skill requires that list to stay
  closed and auditable. Rather than add one, the requirement is met from supplied data.
- **Constraint:** absent counters render **UNAVAILABLE**, never `0`. A zero is a value; an
  absent counter is not, and showing one as the other would misreport a healthy link as
  having dropped nothing when nothing is known.
- **Also constrained:** `Health.ageMs` is SUPPLIED by the producer and is distinct from
  the `ageMs` Task 1 derives from a timestamp (closed list item 1). The contract says so
  explicitly. S6 labels the two separately and never conflates them.
- **Status:** in force.

### M10D-B — Validation failures are surfaced read-only on S6 (D11 fix)
- **Decision:** `MockDataProvider.diagnostics.validationFailures` is exposed read-only
  through the existing application boundary and rendered on S6.
- **Basis:** defect D11. The failures have been recorded since M3 and were never reachable
  by any screen, so an `INVALID` payload — the case M2 exists to distinguish from
  `MISSING` — was invisible to operator and tester alike.
- **Read-only means read-only.** No retry control, no mutation control, no payload
  injection, no reset, no operational action. Provider behaviour is not altered to
  populate the panel, and failures are not counted independently of the provider's own
  record.
- **Consequence:** with no failures, S6 renders an explicit empty state rather than a
  blank panel that could be mistaken for "not checked".
- **Status:** in force.

### M10D-C — The placeholder screen is removed
- **Decision:** `screens/Placeholder.tsx` and its tests are deleted once S6 is
  implemented and `PLACEHOLDER_SCREENS` is empty.
- **Basis:** R6. With all six mandatory screens built, the component has no reachable
  consumer. A component that can never render is dead code that later readers must still
  reason about.
- **Constraint:** deleted only after verifying no remaining consumer. Its two consumers —
  `AppShell.tsx` and `render.test.tsx` — are updated in the same change.
- **Status:** in force.

---

## 16. M11 Approved Verification Decisions

M11 verified; it did not build. Every decision below constrains what evidence may be
claimed, not what the product does.

### M11D-A — The traceability matrix is rebuilt from executed evidence (D12)

`requirements/task1-traceability.md` read `PLANNED` on all 37 rows. It is rebuilt with a
five-value vocabulary — `PASS`, `PARTIAL`, `BLOCKED`, `NOT VERIFIABLE YET`,
`NOT STARTED` — and every row carries an implementation reference, a named verification
artifact, a remaining gap and an owner.

**The rule applied to every row: a mechanism existing is not a PASS.** Where a screen
renders a state but no data or decision exists to exercise it, the row reads PARTIAL or
BLOCKED and names the blocker. This is why FR-013 and FR-014 are PARTIAL despite complete
implementations — the authored scenarios supply no V2V link, no LoRa link, no
`BOTTLENECK_RISK` alert and no `INFO` alert, so those criteria are evidenced by test-local
fixtures only.

**Not changed:** requirement wording, acceptance criteria, IDs, verification methods,
milestone assignments. No waiver.

### M11D-B — NFR-001 and NFR-002 are measured and recorded as NOT VERIFIABLE YET

Both thresholds are unfilled placeholders (AMB-004). Measured figures are recorded in
`docs/verification/perf.md` and `docs/verification/latency.md`; **neither requirement is
marked passed**, and no test asserts a time budget.

Two scope statements are recorded with the figures rather than left implicit:

1. **NFR-002 measures the acknowledgement path only** — the sole command-shaped path that
   exists (PAD-B, AMB-008) — at the provider boundary, with no transport and no operator
   gesture, because no acknowledgement UI is exposed (M9D-F).
2. **NFR-001 is measured on a development build on a developer machine.** A control-room
   figure must be re-measured on the target hardware at M12.

**A measured value is not a pass.** Anyone quoting a figure from these reports must quote
its scope with it.

### M11D-C — Scale is verified against the shipped scenario through the shipped code path

NFR-009 is evidenced by `frontend/src/state/scale.test.tsx` and by a real-browser run, both
playing the authored `scale.json` through `MockDataProvider` into `AppStateStore` and into
the real screens. No hand-built fixture stands in for the scenario, the provider, the store
or the screens.

Result: **50 vehicle cards, zero duplicates, zero omissions**, `Mine map: 20 nodes,
50 vehicles placed, 0 position unavailable`, deterministic ordering, all six screens
reachable under load, the presentation tick still advancing, zero console errors.

**No application defect was exposed.** Two defects found during the run were in the
scratchpad browser harness — a panel `aria-label` shadowing the map's own label, and an
alert-row selector that did not match the rendered class — and both were fixed in the
harness. No M1–M10 file was modified.

Recorded as a measured characteristic, not a defect: at 50 vehicles S1 holds a 16.6 ms
median frame interval with five long tasks (53–73 ms) per twelve seconds, the cost of
re-rendering fifty cards on each 1 Hz tick. No frame budget is specified, so no judgement
is made.

### M11D-D — Three defects are recorded and deliberately not fixed

| Defect | Why not fixed at M11 |
|---|---|
| **D13** — preview/production origin absent from the default CORS allow-list | Deployment configuration is M12. Widening a CORS policy inside a verification milestone would be an unreviewed security-relevant change |
| **D14** — `README.md` stale (claims stage M1, baseline v1.1, no screens) | Not among the changes approved for M11. The setup and check instructions themselves were verified correct |
| **D15** — four pre-existing lint errors in M1–M10 code | The approval forbids refactoring completed milestones; one of the four would change hook effect-run behaviour |

Each needs its own approval. Recording a defect and leaving it visible is the correct
outcome for a verification milestone; fixing it quietly is not.

### M11 verification limits, recorded so they are not later overlooked

| Limit | Consequence |
|---|---|
| No independent clean machine | NFR-010 is PARTIAL; no clean-machine run is claimed |
| No real transport | NFR-004 PARTIAL, NFR-002 scope-limited; re-verify at M12 |
| No persistence | NFR-007 PARTIAL, FR-010 AC3 and FR-016 AC2 PARTIAL (AMB-010) |
| No role infrastructure | FR-015 BLOCKED, NFR-011 PARTIAL (GAP-ROLE-001, still unowned) |
| No supplied vehicle history | S2-b BLOCKED; no local accumulation (M5D-C, PAD-F) |
| No authored `EventRecord` | S5-a PARTIAL; three of the timeline categories are producer-supplied only (M9D-C) |
| Development build, developer hardware | NFR-001 figures are not control-room figures |

**GAP-ROLE-001 remains unowned.** It blocks FR-015 AC3 and NFR-011 and has been carried
without an owning milestone since M8. M11 re-flags it; assigning it is a planning decision,
not a verification one.
