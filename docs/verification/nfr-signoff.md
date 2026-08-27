# Task 1 — Non-functional requirement sign-off

**Milestone:** M11
**Date:** 2026-08-27
**Baseline:** Planning Baseline v1.9 (`requirements/DECISIONS.md`)

The authoritative per-requirement matrix — every FR, NFR, derived and optional requirement —
is `requirements/task1-traceability.md`. **This document is the NFR evidence detail behind
it**, and the two must agree.

---

## 1. Summary

| Status | Count | Requirements |
|---|---|---|
| **PASS** | 5 | NFR-005, NFR-006, NFR-008, NFR-009, NFR-012 |
| **PARTIAL** | 5 | NFR-003, NFR-004, NFR-007, NFR-010, NFR-011 |
| **NOT VERIFIABLE YET** | 2 | NFR-001, NFR-002 |

Nothing is marked passed on the
grounds that a mechanism exists; every PASS below names executed evidence.

## 2. Vocabulary

| Status | Meaning |
|---|---|
| **PASS** | The acceptance criterion was executed and observed to hold. |
| **PARTIAL** | Part of the criterion is evidenced; a named part is not, for a named reason. |
| **BLOCKED** | Cannot proceed until a named external decision or system exists. |
| **NOT VERIFIABLE YET** | Measurable and measured, but no threshold exists to judge against. |

## 3. The twelve requirements

### HMI-NFR-001 — Performance · **NOT VERIFIABLE YET**

| | |
|---|---|
| Method | A, T |
| Evidence | `docs/verification/perf.md`; `frontend/verification/nfr001-render.ts`; browser measurement via `scratchpad/perf-m11.mjs` |
| Measured | S1 at 50 vehicles: server render p50 **7.2 ms**; browser frame interval p50 **16.6 ms** (60 fps); **5 long tasks (53–73 ms) in 12 s**; `mergePatch` 0.006 ms; presentation tick 0.001 ms |
| Missing | An authoritative value for `PLACEHOLDER_NFR001_REFRESH` |
| Blocked by | **AMB-004**, unresolved |
| Owner | Specification owner; re-measure on production build and target hardware at M12 |

**Not marked passed.** A verdict against an unfilled placeholder would be an invented
threshold.

### HMI-NFR-002 — Command latency · **NOT VERIFIABLE YET**

| | |
|---|---|
| Method | A, I |
| Evidence | `docs/verification/latency.md`; `frontend/verification/nfr002-ack-latency.ts` |
| Measured | `sendAcknowledgement` → patch applied at store, n=200: p50 **0.0096 ms**, p95 0.0196 ms, max 0.195 ms |
| Scope | Acknowledgement only (PAD-B, AMB-008). No transport. No operator gesture — no acknowledgement UI exists (M9D-F) |
| Missing | `PLACEHOLDER_NFR002_COMMAND_LATENCY`; a ruling on AMB-008; a real transport |
| Blocked by | **AMB-004**, **AMB-008** |
| Owner | Specification owner; transport at M12 (TECH-001) |

### HMI-NFR-003 — Data freshness · **PARTIAL**

| | |
|---|---|
| Method | T, D |
| Evidence | `state/freshness.test.ts` (18), `data/freshness.test.ts` (29), `state/diagnostics.test.ts` (21), `screens/diagnostics.test.tsx` (58); browser: age advanced 7.2 s → 10.2 s under `stale-feed` |
| Verified | Age computed and displayed per datum; `INVALID` never `MISSING`; empty never `INVALID`; quality reported as **not evaluated** rather than assumed clean when no threshold is set |
| **Missing** | *"Stale is visually flagged after a configurable timeout"* cannot be demonstrated: **the timeout has no value** |
| Blocked by | **AMB-014**, unresolved |
| Owner | Specification owner |

The mechanism is complete and injected; only the number is absent. The HMI states this on
screen rather than defaulting: *"No authoritative timeout has been configured … no default
is assumed."*

### HMI-NFR-004 — Availability · **PARTIAL**

| | |
|---|---|
| Method | T, D |
| Evidence | `state/recovery.test.ts` (9, new at M11), `state/lifecycle.test.ts` (17); browser section C |
| Verified | Reconnection restores fresh data; fleet count unchanged (2 → 2); **zero duplicate vehicles, alerts or events**; every slice still keyed by entity id; recovered timestamp is post-reconnection; no pre-loss value presented as current; mode returns to `NORMAL` |
| **Missing** | Recovery of a **real transport**. There is none |
| Blocked by | TECH-001 / M12 |
| Owner | M12 |

The HMI-side property — merge semantics survive reconnection coherently — is fully
evidenced. The transport-side property does not yet have a subject.

### HMI-NFR-005 — Safety separation · **PASS**

| | |
|---|---|
| Method | I, D |
| Evidence | `docs/verification/architecture-inspection.md` (written at M11 — the method is inspection and no record previously existed) |
| Verified | No actuation or override path in production code; absence asserted by test in three provider suites and one screen suite; nine-item closed derivation list re-counted and intact; `fetch` in exactly one module; `ProviderHost` the sole importer of a concrete provider; acknowledgement does not clear a condition (PAD-D) |
| Re-verify | At M12 against `LiveDataProvider`, a new outbound surface |
| Owner | M12 for re-verification only |

### HMI-NFR-006 — Explainability · **PASS**

| | |
|---|---|
| Method | T, I, D |
| Evidence | `screens/dispatchSlots.test.tsx` (60), `screens/vehicleDetail.test.tsx` (43), `screens/bottleneckQueue.test.tsx` (26) |
| Verified | Dispatch decisions render the **supplied** `reasonCode` and `limitingVariables`; a missing reason code is marked as a **data defect** rather than silently omitted; S2 renders the supplied `activeConstraint` alongside the safety envelope |
| Note | Every explanation is *supplied*, never composed by the HMI (PAD-E/PAD-F) — which is what makes it explainable rather than plausible |

### HMI-NFR-007 — Traceability · **PARTIAL**

| | |
|---|---|
| Method | T, D |
| Evidence | `state/eventLog.test.ts` (33), `screens/eventReplay.test.tsx` (24) |
| Verified | Events are timestamped, ordered, append-only (no remove, truncate or clear by design), and visible on S5 with exact-frame replay and no interpolation |
| **Missing** | *"Persisted."* The log is **in-memory for the session only** (M9D-A) |
| Blocked by | **AMB-010** — persistence ownership undefined |
| Owner | M12 |

Declared as a non-conformance at M9 and still open. Nothing about it has changed.

### HMI-NFR-008 — Usability / no colour-only · **PASS**

| | |
|---|---|
| Method | I, T |
| Evidence | `docs/verification/greyscale-audit.md`; colour-stripped assertions in eight test files; browser greyscale sweep of all six screens |
| Verified | Eight state dimensions audited at source — system mode, severity, risk/criticality, freshness, connection, slot status incl. conflict, dispatch state, replay — every state carries a label **and** a glyph. Browser: all six screens legible under `grayscale(1)`; 9 status markers examined, **0 colour-only** |
| Not applicable | Acknowledgement state and role state — the states do not exist yet (M9D-F, GAP-ROLE-001); audit them when they are built |
| Limitation | Availability of text is proven; legibility on control-room hardware is a human-factors review at deployment |

### HMI-NFR-009 — Scalability · **PASS**

| | |
|---|---|
| Method | T, A |
| Evidence | `docs/verification/scale.md`; `frontend/src/state/scale.test.tsx` (12, new at M11); browser section A (12 checks) |
| Verified | 50 vehicles / 20 nodes played through the real provider into the real store and rendered by the real screens. **50 cards, 0 duplicates, 0 omissions**; map label `20 nodes, 50 vehicles placed, 0 position unavailable`; 20 node elements in the SVG; deterministic id ordering; content height 6910 px with no horizontal overflow; a card click opened S2 on the right vehicle; all six screens reachable under load; the 1 Hz tick kept advancing; S6 counted 50/50/20; **0 console errors** |
| Characteristic | 60 fps median with 5 long tasks per 12 s at scale (`perf.md`) — reported, not judged; no frame budget is specified |
| Limitation | Authored maximum only; mock data, no transport; development build |

**The gap M11 closed:** before this milestone the scale scenario was checked for its JSON
shape and had never been rendered.

### HMI-NFR-010 — Portability · **PARTIAL**

| | |
|---|---|
| Method | D, I |
| Evidence | `docs/verification/portability.md` |
| Verified | `README.md` documents setup for four shells with the differences called out — PowerShell, Command Prompt, Git Bash, Linux/macOS — plus execution-policy failure, activation check, and the `uvicorn not found` fallback. On this machine: prerequisites match, all three `.env.example` files present, venv resolves to the documented path, backend serves `/api/health`, dev server serves `:5173`, every documented check command runs |
| **Missing** | **No independent clean machine was used, and none is claimed.** No fresh clone, no venv created from scratch, no `npm install` into an empty tree, no Command Prompt run, no Linux or macOS run |
| Also | **D14** — `README.md` is stale (claims stage M1, baseline v1.1, "no HMI screens yet") |
| Owner | Release verification; D14 needs approval to fix |

### HMI-NFR-011 — Security baseline · **PARTIAL**

| | |
|---|---|
| Method | T, I |
| Evidence | Secret scan on 2026-08-27 across `*.ts, *.tsx, *.py, *.json, *.md, *.yml`: **no match**. `.env` gitignored, `.env.example` committed. All config via environment (`HMI_HOST`, `HMI_PORT`, `HMI_CORS_ORIGINS`, `VITE_API_BASE_URL`). CI runs the same scan (`.github/workflows/ci.yml`) |
| **Missing** | *"Role gating enforced server-side."* **No role infrastructure exists anywhere** |
| Blocked by | **GAP-ROLE-001** / ROLE-001 — unowned |
| Owner | M12 |

The credential-hygiene half is evidenced; the authorization half has no implementation to
verify. It is not partially built — it is absent, deliberately, because inventing roles was
forbidden (M8D ruling).

### HMI-NFR-012 — Recovery / graceful degradation · **PASS**

| | |
|---|---|
| Method | T, D |
| Evidence | `docs/verification/failure-scenarios.md`; `state/systemMode.test.ts` (32), `state/lifecycle.test.ts` (17), `state/alerts.test.ts` (35); browser section B (24 checks) |
| Verified | Under `communication-loss`: all six screens render and all six show `DEGRADED — data feed lost (FR-016)`; last values **retained, not blanked**; a `COMM_LOSS` alert is raised and marked `ORIGIN HMI — DATA PATH`. Under `stale-feed`: mode correctly stays `NORMAL`, ages advance, nothing is classified. Backend health stays independent of the feed in both directions |
| Note | The silent-feed and lost-link cases are **not conflated**, which is the failure this requirement most easily hides |

## 4. What blocks the five open requirements

| Requirement | Blocked on | Type | Owner |
|---|---|---|---|
| NFR-001 | AMB-004 — no refresh threshold | Specification | Spec owner |
| NFR-002 | AMB-004, AMB-008 | Specification | Spec owner |
| NFR-003 | AMB-014 — no staleness timeout | Specification | Spec owner |
| NFR-004 | TECH-001 — no transport | Implementation | M12 |
| NFR-007 | AMB-010 — persistence ownership | Specification → M12 | M12 |
| NFR-010 | No clean machine available | Environment | Release verification |
| NFR-011 | GAP-ROLE-001 — roles unowned | **Unassigned** | **Needs an owner** |

Four of the seven blockers are **decisions this project is forbidden to make for itself**.
They will not close through further engineering.

## 5. The one unowned item

**GAP-ROLE-001 / ROLE-001** has no owning milestone. It blocks FR-015 AC3 and NFR-011, and
it has been carried without an owner since M8. Every other open item above is assigned.

This is flagged, not resolved: assigning it is a planning decision.
