# ADR-001 — The HMI is advisory only

- **Status:** Accepted (M1)
- **Traces:** HMI-NFR-005 (safety separation), OPS-001, OPS-002, PAD-A, PAD-B, PAD-C, PAD-D
- **Baseline:** Planning Baseline v1.1

## Context

FOG-ORCHESTRATOR 2.0 splits into Task 1 (this repository, the HMI) and Task 2 (the Digital
Twin, developed independently). The specification is explicit that the HMI is a supervisory
layer sitting above, not inside, the safety chain:

- §3: the HMI "does not replace the Tier-1 local physics safety governor", and "the vehicle
  controller must enforce local safety limits".
- HMI-NFR-005: "Loss or crash of HMI shall not disable Tier-1 vehicle safety."

An architecture that lets the HMI participate in the safety path — by computing a limit, by
actuating equipment, or by having a vehicle depend on it — would violate all of the above,
and would do so quietly. This record fixes the boundary before any screen is built.

## Decision

**The HMI is advisory only.**

1. **No safety computation.** This repository computes no safe speed, safe headway, risk
   level, bottleneck score, queue prediction, dispatch assignment or route. Those values
   arrive from Task 2 through a provider and are visualized (PAD-E).
2. **No actuation.** No drive-by-wire signal, no direct equipment command. The outbound
   surface is limited to alert acknowledgement (PAD-B, PAD-D).
3. **Acknowledgement is not mitigation.** Acknowledging an alert changes display and audit
   state only. It never clears, suppresses or downgrades the underlying condition, and
   safety-critical local protection never depends on it (FR-015, PAD-D).
4. **Nothing depends on the HMI being alive.** If this process stops, vehicle safety is
   unaffected. That property is what makes the HMI safe to iterate on quickly.
5. **The derived-value list is closed.** The HMI derives only the eight data-path values
   enumerated in `requirements/task1-data-contract.md` §12 — age, staleness, connection
   status, stale/comm alerts, forced DEGRADED, sort orders, and display-only comparisons of
   two supplied numbers. Everything else must arrive from a provider.

## Consequences

- Every milestone's verification gate includes a scope audit against point 1 and point 5.
  A convenience calculation — extrapolating a queue line, aggregating a KPI from local
  history — is a defect, not a feature, because it silently duplicates Task 2 logic.
- The backend has no control endpoint. Adding one requires reopening AMB-008 and amending
  PAD-B through the revision process in `requirements/DECISIONS.md` §1.3.
- The HMI can be developed, restarted and demonstrated entirely on mock data without any
  safety consideration, because it holds no safety responsibility.

## Open item

**AMB-008** asks whether the HMI must *issue* commands, not merely display them. FR-010
("issued"), NFR-002 ("command latency") and NFR-007 ("issued/received commands") hint at an
outbound path, while §12 and `CLAUDE.md` describe visualization only. PAD-B holds the safe
default while that question is open. If it is answered "yes", this ADR is superseded rather
than quietly stretched.
