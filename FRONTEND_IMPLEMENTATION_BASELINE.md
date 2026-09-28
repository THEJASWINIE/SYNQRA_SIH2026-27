# FRONTEND IMPLEMENTATION BASELINE

**Project:** FOG-ORCHESTRATOR 2.0 — Technician / Control-Room HMI
**Date:** 2026-09-08
**Purpose:** State what the frontend actually is today, before any work against the
"COMPLETE HMI INTEGRATION & HANDOVER SPECIFICATION".
**Method:** repository inspection only. Nothing in this document is assumed.

---

## 0. FIRST FINDING — THE CITED SPECIFICATION IS NOT IN THIS REPOSITORY

A search of the whole tree for `*HANDOVER*`, `*HMI_INTEGRATION*` and `*COMPLETE_HMI*`
returns **no such specification document**. The only near matches are
`HARDWARE_HMI_INTEGRATION_AUDIT.md` (a hardware audit, not an HMI spec) and two Python
test scripts.

Consequence: the six-screen structure quoted in the request **cannot be verified against a
document in this repository**. It is treated below as a stated requirement from the
project owner, not as a repository artifact. Where it conflicts with what the repository
demonstrably contains, both are recorded and the conflict is escalated rather than
silently resolved.

---

## 1. EXISTING FRONTEND ARCHITECTURE

| Aspect | Actual implementation |
|---|---|
| Framework | React 19 + Vite + TypeScript (`exactOptionalPropertyTypes: true`) |
| Routing | **No router library.** `AppShell.tsx` holds `screenId` in `useState` and switches on it |
| State | Custom `AppStateStore` (`src/state/store.ts`) + `HmiContext`. No Redux/Zustand/Jotai |
| API client | `src/api/commandClient.ts` (commands), `src/api/observabilityClient.ts` (metrics) |
| Real-time | One WebSocket owned by `src/providers/LiveDataProvider.ts`. Screens never open one |
| Validation | Zod schemas in `src/contracts/` |
| Tests | vitest + `react-dom/server` `renderToString`, `environment: "node"`. **No jsdom, no Testing Library** (documented decision M4D-C) |
| Test count | **1177 passing**, 42 files. `npx tsc --noEmit` clean |

**Provider model.** Three interchangeable providers behind one interface:
`LiveDataProvider` (real backend), `MockDataProvider` (11 scenario JSON files),
`ReplayProvider` (recorded sessions). Screens are provider-agnostic — nothing branches on
which one is connected.

---

## 2. EXISTING SCREENS AND ROUTES

Fourteen screen components exist. Navigation is defined in `AppShell.tsx:186-256`.

**Primary navigation (canonical, as directed in the Phase 1 instruction):**

| Route id | Nav label | Component |
|---|---|---|
| `overview` | S1 Operations | `OperationsOverview.tsx` |
| `vehicle` | S2 Vehicle Detail | `VehicleDetail.tsx` |
| `safety` | S3 Safety / Environment | `SafetyEnvironment.tsx` |
| `dispatch` | S4 Dispatch | `DispatchSlots.tsx` |
| `alerts` | S5 Alerts | `AlertList.tsx` |
| `twin` | S6 Digital Twin | `DigitalTwin.tsx` |
| `diagnostics` | S7 System Health | `Diagnostics.tsx` |

**Secondary navigation ("Additional"):**

| Route id | Nav label | Component |
|---|---|---|
| `operator` | Operator | `OperatorView.tsx` |
| `bottleneck` | Bottleneck | `BottleneckQueue.tsx` |
| `replay` | Replay | `EventReplay.tsx` |

**Embedded, not separately routed:** `MineMap.tsx` (inside S1 and S6),
`ScenarioPicker.tsx` (inside S1), `FailureInjectionLab.tsx` (routed at `AppShell.tsx:317`).

---

## 3. CONFLICT WITH THE STATED SPECIFICATION — BLOCKING

The specification names six screens. The repository implements seven plus three
additional. **Every screen the specification asks for already exists.** Only the numbering
and grouping differ.

| Spec screen | Exists? | Currently reached as |
|---|---|---|
| S1 Operations | YES | S1 Operations |
| S2 Vehicle | YES | S2 Vehicle Detail |
| S3 Bottleneck & Queue | YES | **Additional → Bottleneck** |
| S4 Dispatch & Slots | YES | S4 Dispatch |
| S5 Replay | YES | **Additional → Replay** |
| S6 Diagnostics | YES | **S7 System Health** |

Screens the specification does not number, which exist and are fully implemented and
test-locked: **S3 Safety / Environment** (28 tests), **S5 Alerts** (45 tests),
**S6 Digital Twin** (33 tests), **Operator** (23 tests).

**Why this cannot be resolved unilaterally.** The S1–S7 structure was established by an
explicit written instruction from the project owner ("Normalize the primary navigation to
this canonical SIH structure"), is documented in `AppShell.tsx:32-41` as
"CANONICAL SIH SCREENS", and is asserted by tests. The specification's rule 14 forbids
replacing the six-screen structure without repository evidence — but the repository
evidence points the *other* way, at S1–S7. Two directives from the same owner conflict.

**Nothing has been renumbered. This decision is escalated to the project owner.**

Three options, none of which requires deleting a screen:

- **A — Keep S1–S7, map the spec onto it.** Zero risk, zero test churn. The spec's S3 and
  S5 stay reachable under "Additional".
- **B — Renumber the primary nav to the spec's six**, demoting Safety/Environment, Alerts
  and Digital Twin to "Additional". Label-only change; ~3 test files need updating. No
  screen is deleted and no functionality is lost.
- **C — Present both numberings.** Rejected: two names for one screen is exactly the
  ambiguity this HMI exists to avoid.

---

## 4. EXISTING BACKEND CONTRACTS (verified in `backend/app/main.py`)

| Endpoint | Method | Consumed by frontend today |
|---|---|---|
| `/api/health` | GET | `BackendHealth.tsx`, S7 |
| `/api/mode` | GET | not consumed |
| `/api/observability` | GET | `ProviderHost.tsx` → S7 |
| `/api/vehicles` | GET | `LiveDataProvider` |
| `/api/telemetry` | POST | producers only (not the HMI) |
| `/api/hardware/telemetry` | POST | hardware ingress (not the HMI) |
| `/api/commands` | POST | `commandClient.ts` → S4 only |
| `/api/commands/history` | GET | not consumed |
| `/api/twin/snapshot` | GET | `LiveDataProvider`, `game_ui` canonical client |
| `/api/twin/vehicles/{id}` | GET | not consumed |
| `/ws/live`, `/api/ws` | WS | `LiveDataProvider` (one connection) |

---

## 5. DATA-TRUTH LAYER — ALREADY BUILT

`src/state/dataStatus.ts` is the single interpretation of data state, added in Phase 8 and
covered by 32 tests.

- **Data states:** `CURRENT | STALE | UNKNOWN | UNAVAILABLE`
- **Provenance:** `PHYSICAL`, `PHYSICAL (derived)`, `SIMULATION`, `--`
- **Service:** `ONLINE | OFFLINE | UNKNOWN` — never derived from data freshness
- **Unavailable:** `--` in a value slot, `UNAVAILABLE` in a status slot. **Never 0**

The specification asks for provenance states `PHYSICAL / DERIVED / MODEL / SIMULATED /
UNAVAILABLE / STALE` and freshness `CURRENT / STALE / DEGRADED / INVALID / UNAVAILABLE`.
The implemented vocabulary differs deliberately: **provenance and freshness are separate
axes** (a value can be `SIMULATION` *and* `STALE`), and collapsing `STALE` into the
provenance list would merge them. `MODEL` and `DEGRADED` have no backend producer today.

---

## 6. MISSING BACKEND CONTRACTS — DO NOT FABRICATE

Measured against the running backend. Each is required by a specification section and has
**no live producer**.

| Spec section | Field | Status |
|---|---|---|
| S1-C Fog/environment | visibility, fog state, forecast, confidence | `/api/twin/snapshot` returns `environment: {}` |
| S1-E Road capacity | capacity, utilization, H_safe | `roads: {}` |
| S1-F Bottleneck | BottleneckScore, arrival/service rate | contract exists; **MOCK/REPLAY only** |
| S1-G Orchestrator | HOLD / RELEASE / REROUTE, expected effect | contract exists; **MOCK/REPLAY only** |
| S1-H V2V/V2I | latency, packet loss, confidence | contract exists; **MOCK/REPLAY only** |
| S2 Motion | position, heading | in `NEVER_FROM_HARDWARE` — **no sensor exists** |
| S2 Safety | v_safe, H_safe, stopping margin, active constraint | no safety solver runs in the HMI backend process |
| S6 Sensors | GNSS | **no GNSS hardware exists** |
| S4 Command lifecycle | `VALIDATED`, `HARDWARE_RECEIVED`, `PHYSICAL_STATE_CONFIRMED` | backend has `ACCEPTED / SENT / ACKNOWLEDGED / EXECUTED / REJECTED / TIMEOUT` only |

The specification's 10-state command lifecycle exceeds the backend's 6 states. The missing
four **must render as not-reached**, never as inferred.

---

## 7. FILES THAT MUST NOT BE MODIFIED

- `src/state/freshness.ts` — the single freshness derivation (M4D-E)
- `src/state/dataStatus.ts` — the single data-state vocabulary (Phase 8)
- `src/providers/*.ts` — provider contract; changing it desynchronises all three
- `src/contracts/*.ts` — frozen schemas
- `src/screens/MineMap.tsx` — refuses invented coordinates (M4D-F); reused by S1 and S6
- `src/screens/architecture.test.ts` — the boundary guards
- Backend `app/main.py` — out of frontend scope

## 8. FILES THAT WOULD CHANGE UNDER OPTION B

`src/screens/AppShell.tsx` (nav labels + route ids only),
`src/screens/render.test.tsx`, `src/state/providerSwitch.test.tsx`,
`src/state/scale.test.tsx` (assertions naming nav labels).

---

## 9. HONEST SUMMARY

The frontend is **not a greenfield build**. It is a working, test-locked, provider-agnostic
control-room HMI with a single data-truth layer, every screen the specification names, and
1177 passing tests.

The gap is **not missing screens**. It is:

1. a **numbering conflict** requiring an owner decision (§3);
2. **absent backend producers** for environment, safety, bottleneck, orchestrator and
   V2V data in LIVE mode (§6) — these already render `UNAVAILABLE` and must continue to;
3. a **command lifecycle shorter than specified** (§6), which must not be padded out with
   inferred states.

No screen should be built to display data that no producer supplies.
