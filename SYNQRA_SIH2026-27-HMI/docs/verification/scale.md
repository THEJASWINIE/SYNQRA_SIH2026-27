# HMI-NFR-009 — Scale verification report

**Milestone:** M11
**Date:** 2026-08-27
**Verdict:** **PASS** — 50 vehicles and 20 nodes render correctly and remain interactive.

---

## 1. The requirement and the gap M11 closed

HMI-NFR-009 requires the HMI to handle **50 vehicles and a 20-node topology**, rendering
correctly and remaining interactive.

Before M11 the authored `scale` scenario existed and was checked for its **shape only**, by
`frontend/src/mocks/scenarios.test.ts` ("scale scenario (test 20)"), which asserts that the
JSON contains 20 nodes and 50 `VehicleState` entries. **Nothing had ever rendered it.** The
requirement's actual acceptance language — *renders correctly and remains interactive* —
was unevidenced.

M11 closes that with two independent bodies of evidence: an automated render test and a
real-browser run.

## 2. The fixture

`frontend/src/mocks/scenarios/scale.json` (M3, unmodified by M11):

| Content | Count |
|---|---|
| Topology nodes | 20 |
| Topology segments | 20 |
| `VehicleState` | 50 |
| `SafetyState` | 50 |
| `RoadState` | 20 |
| `SystemHealth` | 1 |

No scenario data was created or altered for this milestone.

## 3. Evidence A — automated render test

`frontend/src/state/scale.test.tsx` (new at M11). 12 tests, all passing. It plays the
**shipped** scenario through the **shipped** provider into the **shipped** store and
renders the **shipped** screens — no hand-built fixture stands in for any of that.

| What is asserted | Result |
|---|---|
| Store holds 50 vehicles, 20 nodes after playback | pass |
| A `SafetyState` exists for every vehicle | pass |
| 20 segments, 20 `RoadState` | pass |
| Every slice keyed by entity id; no duplicate key | pass |
| S1 renders exactly 50 vehicle cards | pass |
| No vehicle rendered twice; rendered set equals stored set | pass |
| Card order is deterministic and id-sorted across two independent runs | pass |
| Map summary reports 20 nodes and accounts for all 50 vehicles (placed + unavailable) | pass |
| Every vehicle id appears as readable text | pass |
| S1 legible with colour stripped at scale (NFR-008) | pass |
| S6 counts 50 `VehicleState`, 50 `SafetyState`, 20 `RoadState` | pass |
| S6 reports no quality tally while the threshold is unconfigured, even at scale | pass |
| S6 renders against the scale load | pass |

The test asserts **no time budget**, because none is specified (AMB-004). Timing is
reported separately in `perf.md`.

## 4. Evidence B — real browser

Headless Microsoft Edge `Edg/151.0.4129.107` over CDP against the running application
(Vite dev server, `localhost:5173`). Harness: `scratchpad/verify-m11.mjs`, section A.

| Check | Observed |
|---|---|
| Scale scenario selectable from S1 | clicked |
| Vehicle cards rendered | **50** |
| Duplicate vehicles | **0** (50 unique of 50) |
| Map summary label | `Mine map: 20 nodes, 50 vehicles placed, 0 position unavailable` |
| Node elements actually in the SVG | **20** |
| Content height on S1 | 6910 px — real content, no collapse |
| Horizontal overflow | none (`scrollWidth` 739) |
| Vehicle card click opens S2 on that vehicle | yes (`V-1`) |
| All six screens reachable while the scale feed runs | S1–S6 all reachable |
| Displayed age advances under scale load | 8.6 s → 11.6 s |
| S6 counts at scale | `VehicleState 50`, `SafetyState 50`, `RoadState 20` |
| Console errors | **0** |

**Interactivity is demonstrated, not assumed:** a card was clicked, S2 opened on the
correct vehicle, every screen was navigated, and the 1 Hz presentation tick kept advancing
throughout.

## 5. Performance characteristic at scale (reported, not judged)

From `perf.md`: at 50 vehicles the browser holds a **16.6 ms median frame interval**
(60 fps), with **five long tasks (53–73 ms)** observed in a 12-second window on S1 — the
cost of re-rendering 50 vehicle cards on each 1 Hz tick. S6 showed none at the same load.

This is a measured characteristic, not a defect: no requirement states a frame budget
(AMB-004). It is recorded so the threshold owner can judge it.

## 6. Limitations

- The load is the **authored maximum** (50/20), which is exactly what NFR-009 states. No
  claim is made about behaviour beyond it.
- Measured against **mock data over no transport**. Live-feed behaviour at scale is M12.
- Measured on a **development build** on a developer laptop, not a production build on an
  operator workstation.

## 7. Result

**No application defect was exposed by scale testing.** Two harness defects were found and
fixed in the scratchpad harness during the run — a panel `aria-label` shadowing the map's
own label, and an alert-row selector that did not match the rendered class — neither of
which is a defect in the application. No M1–M10 code was modified.

HMI-NFR-009: **PASS**, within the limitations in §6.
