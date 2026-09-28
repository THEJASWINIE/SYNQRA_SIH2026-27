# HMI-NFR-001 — Performance measurement report

**Milestone:** M11
**Date of measurement:** 2026-08-27
**Verdict:** **NOT VERIFIABLE YET** — measured, not passed.

---

## 1. Why this is a measurement and not a test

HMI-NFR-001 requires the operator view to refresh within a stated interval. **The
specification states no interval.** The requirement is carried in
`requirements/task1-requirements.md` against the named placeholder
`PLACEHOLDER_NFR001_REFRESH`, which is unfilled and recorded as **AMB-004**.

A pass/fail cannot be computed against a number that does not exist, and PAD-G forbids
inventing one. This report therefore states what the system actually does, in figures that
can be compared against the authoritative threshold the moment it is supplied. Nothing
here should be read as conformance.

No test in the gating suite asserts a time budget, deliberately: such a test would either
encode an invented budget or flake on a loaded machine.

## 2. Environment

| | |
|---|---|
| OS | Microsoft Windows 11 Home Single Language, build 26200 |
| CPU | 16 logical cores |
| Node | v24.18.0 |
| Browser | Microsoft Edge `Edg/151.0.4129.107`, headless (`--headless=new`), driven over CDP |
| Server | Vite 7 dev server, `http://localhost:5173` |
| Backend | FastAPI on `127.0.0.1:8000` (running; it does not participate in render timing) |

**Stated limitation:** this is a development build served by the Vite dev server on a
developer laptop under an unmeasured background load. It is not a production build, not
production hardware, and not an operator workstation. A control-room figure must be
re-measured on the target machine at M12. Nothing here can substitute for that.

## 3. Scenarios measured

| Scenario | Vehicles | Nodes | Purpose |
|---|---|---|---|
| `nominal` | 2 | 20 | Baseline |
| `scale` | 50 | 20 | The NFR-009 load — the worst case this repository authors |

## 4. Measurement A — server-render cost (Node)

Script: `frontend/verification/nfr001-render.ts` — run with
`npx vite-node verification/nfr001-render.ts`.
200 samples per figure after 20 warm-up iterations. Figures in milliseconds.

| Measurement | n | min | p50 | p95 | max | mean |
|---|---|---|---|---|---|---|
| S1 render (nominal) | 200 | 0.957 | 1.080 | 11.339 | 13.898 | 2.207 |
| S6 render (nominal) | 200 | 1.101 | 1.248 | 2.324 | 3.251 | 1.387 |
| store tick (nominal) | 200 | 0.002 | 0.002 | 0.002 | 0.017 | 0.002 |
| mergePatch (nominal) | 200 | 0.001 | 0.001 | 0.003 | 0.019 | 0.002 |
| **S1 render (scale)** | 200 | 6.303 | **7.222** | 84.059 | 97.299 | 11.671 |
| **S6 render (scale)** | 200 | 1.069 | **1.169** | 16.623 | 23.852 | 3.524 |
| store tick (scale) | 200 | 0.001 | 0.001 | 0.002 | 0.011 | 0.001 |
| mergePatch (scale) | 200 | 0.006 | 0.006 | 0.006 | 0.007 | 0.006 |

Notes, stated rather than smoothed:

- `renderToString` is a **string** render in Node. It is an upper-bound proxy for
  component cost, not a browser paint. Measurement B is the browser figure.
- The p95/max columns are dominated by garbage collection pauses in a single-process
  benchmark loop. The p50 is the representative figure; the tail is reported because
  hiding it would be dishonest, not because it is characteristic.
- **State cost does not scale badly.** `mergePatch` at 50 vehicles is 0.006 ms and the
  presentation tick is ~0.001 ms. The cost of scale is in rendering 50 cards, not in the
  data path.

## 5. Measurement B — in-browser frame behaviour

Script: `scratchpad/perf-m11.mjs`, driving the running application in headless Edge.
12 seconds of observation per row. `frame interval` is the gap between consecutive
`requestAnimationFrame` callbacks; `long tasks` are `PerformanceObserver` `longtask`
entries (>50 ms of blocked main thread).

| View | DOM nodes | frame p50 | frame p95 | frame max | long tasks (12 s) |
|---|---|---|---|---|---|
| nominal / S1 | 329 | 16.6 ms | 17.8 ms | 40.1 ms | **0** |
| **scale / S1** | 1797 | **16.6 ms** | 18.0 ms | 73.7 ms | **5** (min 53, p50 60, max 73 ms) |
| scale / S6 | 382 | 16.7 ms | 18.0 ms | 40.0 ms | **0** |

Reading of these figures:

- At 50 vehicles the application **holds 60 fps at the median** (16.6 ms is the vsync
  interval). The interface does not degrade into sluggishness at the NFR-009 load.
- **Five long tasks in twelve seconds on S1 at scale.** The presentation tick is 1 Hz
  (`TICK_INTERVAL_MS = 1000`), so roughly twelve re-renders occurred in the window and
  about five of them blocked the main thread for 53–73 ms. This is the honest cost of
  re-rendering 50 vehicle cards once per second.
- **This is reported, not fixed.** It is not a defect against any stated requirement,
  because no requirement states a frame budget. Optimising it during M11 would be a
  refactor of completed milestones, which is out of scope for this milestone. It is
  recorded here so that whoever fills in `PLACEHOLDER_NFR001_REFRESH` can see immediately
  whether it matters.
- S6 shows no long tasks at the same load: it aggregates 120 entities into 14 rows rather
  than rendering a card each.

## 6. What would change the verdict

| Needed | Owner |
|---|---|
| An authoritative value for `PLACEHOLDER_NFR001_REFRESH` (AMB-004) | Specification owner |
| Re-measurement on a production build (`npm run build` + a real server) | M12 |
| Re-measurement on the target operator workstation | M12 / integration |
| Measurement against live transport rather than in-process mock data | M12 (TECH-001) |

Until the first row is supplied, HMI-NFR-001 remains **NOT VERIFIABLE YET**. It is not
marked passed, and no figure above should be quoted as conformance.
