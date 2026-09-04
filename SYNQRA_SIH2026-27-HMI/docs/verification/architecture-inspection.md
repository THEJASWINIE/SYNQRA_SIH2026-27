# HMI-NFR-005 — Safety separation: architecture inspection record

**Milestone:** M11
**Date:** 2026-08-27
**Method:** `I` (inspection) + `D` (demonstration)
**Verdict:** **PASS** for the architecture as built. See §6 for the one limit on that claim.

---

## 1. Why this document exists

HMI-NFR-005 requires that the HMI be architecturally separated from safety-critical control:
it must not be able to actuate equipment or override a safety decision. Its verification
method is **inspection**, not test — and until M11 no inspection record existed. The
separation was real in the code but unwritten, which is not the same as verified.

This is that record. Every claim below was re-checked against the repository on the date
above, not carried forward from an earlier milestone's assertion.

## 2. The governing decisions

| Decision | Content |
|---|---|
| PAD-A | Task 1 is an HMI and supervisory visualization system |
| PAD-B | Task 1 does not directly actuate vehicles or equipment |
| PAD-C | Task 1 may *display* externally supplied commands, recommendations, dispatch states and slot assignments |
| PAD-D | Task 1 may acknowledge HMI alerts and events; acknowledgement must never imply that an underlying safety condition has been removed |
| PAD-E | Digital Twin computation, prediction, optimization and simulation must arrive as external provider data |
| PAD-F | `h_safe`, headway, arrival plans, queue forecasts and KPIs must not be locally invented |
| ADR-001 | `docs/adr/ADR-001-hmi-advisory-only.md` — the advisory-only architecture record |

## 3. Inspection A — no actuation or override path exists

The `DataProvider` interface is the *only* outbound surface of the HMI. It exposes exactly
one method that travels outward: `sendAcknowledgement(alertId, actor)`.

`frontend/src/providers/DataProvider.ts` states the boundary in the interface itself: the
provider may not override safety, may not actuate equipment, and whether the HMI may issue
commands at all remains AMB-008.

**This is enforced by test, not merely by comment.** Three separate suites assert that the
forbidden methods do not exist on the shipped objects:

| Test | Asserts absent |
|---|---|
| `providers/DataProvider.test.ts` | `sendCommand`, `issueCommand`, `override`, `actuate` |
| `providers/MockDataProvider.test.ts` | same set, on the concrete provider |
| `providers/ReplayProvider.test.ts` | same set, on the replay provider |
| `screens/alertList.test.tsx` | no rendered control labelled `override`, `send command`, `execute`, `dispatch now`, `actuate` |

A repository-wide grep for actuation verbs on 2026-08-27 returned **no production
occurrence**: every hit is either a test asserting absence, or the interface comment
describing the prohibition.

**One near-match, examined and cleared:** `ReplayProvider.setSpeed()` is the *replay
playback rate* (0.5×, 1×, 2×, 4×), not a vehicle speed command. It changes only how fast a
recorded session is stepped through, and `ReplayProvider.sendAcknowledgement` unconditionally
rejects with `ABORTED`. Naming it `setSpeed` in a mining context is unfortunate; it is
recorded here so a future reader does not have to re-derive that it is harmless.

## 4. Inspection B — no Task 2 computation

A repository-wide grep for `computeVSafe`, `calculateVSafe`, `computeHSafe`, `calcHeadway`,
`predictQueue`, `optimizeDispatch`, `optimizeRoute`, `simulate`, `physics`, `frictionModel`
across all production sources returned **one** hit: a comment in `contracts/domain.ts`
describing CV values as *not* physics-derived. No implementation.

The permitted derivations are a **closed list** of exactly **nine** items in
`requirements/task1-data-contract.md` §12, re-counted on 2026-08-27 and confirmed at nine:

1. `age_ms` for any datum
2. `quality` against the configured timeout
3. `connection.status`
4. `STALE_DATA` and `COMM_LOSS` alerts
5. Forcing displayed `system_mode` to at least `DEGRADED` on feed loss (NFR-012)
6. Bottleneck list sort order, from the *supplied* score
7. Alert ordering, from *supplied* severity and timestamp
8. Boolean comparisons of two supplied numbers, display only
9. The display-only map coordinate, from supplied `segment_id`

Every one is a property of the data path or of presentation. None computes an operational
value. The list is deliberately closed: adding a tenth requires an approved decision, and
M10 explicitly declined to add one (M10D-A, supplied counters only).

## 5. Inspection C — the layering holds

| Rule | Verified |
|---|---|
| Transport appears in exactly one place | `fetch` occurs once in production code: `api/healthClient.ts`. No `WebSocket`, `XMLHttpRequest` or `EventSource` anywhere. |
| One module imports a concrete provider | `state/ProviderHost.tsx` is the sole importer of `MockDataProvider` and `ReplayProvider`. No screen or component imports either. |
| Screens read normalized state only | Screens consume `AppState` through `useAppState` / `HmiContext`; none imports raw mock JSON. |
| One merge implementation | `data/patch.ts` is shared by Mock, Replay and (future) Live. The store delegates rather than re-interpreting patch semantics. |
| One freshness definition | `state/freshness.ts`. `state/diagnostics.ts` consumes it rather than defining a second notion of stale. |

The required flow — `Provider → normalization → typed AppState → HMI` — is intact, which is
what makes the safety separation structural rather than a matter of discipline: a screen has
no object through which to reach a vehicle.

## 6. Demonstration — acknowledgement does not clear a condition

PAD-D's requirement is behavioural, and it is demonstrated rather than asserted:

- `MockDataProvider.sendAcknowledgement` sets `Alert.acknowledged = { by, at }` and emits an
  event. It does **not** set `active: false`, and it changes no safety value.
- The alert remains in the active set after acknowledgement; only its acknowledgement
  metadata changes.
- `ReplayProvider.sendAcknowledgement` always rejects — a historical record cannot be
  acknowledged into a different history.

## 7. The one limit on this verdict

This inspection covers **the architecture as built against mock data**. The `LiveDataProvider`
does not exist (M12, TECH-001). When it does, this record must be re-executed against it,
because the property being claimed — that no outbound path can actuate — is a property of the
provider surface, and a new provider is a new surface.

Recorded as a re-verification obligation on M12, not as a caveat that weakens the present
finding: for every provider that exists today, the separation holds.

## 8. Result

**HMI-NFR-005: PASS.** No actuation path, no override path, no Task 2 computation, and a
layering that makes the separation structural. Re-verify at M12 against `LiveDataProvider`.
