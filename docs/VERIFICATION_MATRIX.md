# VERIFICATION MATRIX

Status is one of **PASS**, **FAIL**, **NOT TESTED**. Nothing is marked PASS on the strength
of code having been written.

**Provenance: SIMULATION / EMULATED throughout. No physical ESP32 was connected.**

Suite results recorded at the end of P9:

| Suite | Command | Result |
|---|---|---|
| Root Python | `python -m pytest -q` (repo root) | **414 passed, 0 failed** |
| Main sub-repo | `python -m pytest -q` (SYNQRA_SIH2026-27-main) | **49 passed, 1 failed** |
| Frontend | `npx vitest run` | **884 passed** |
| Frontend types | `npx tsc --noEmit` | **clean** |
| HMI backend contracts | `python -m pytest tests -q` (HMI/backend) | **33 passed** |
| Main backend contracts | `python -m pytest tests -q` (main/backend) | **33 passed** |
| Live smoke | `python verify_p9_end_to_end.py` | **12/12 PASS** |
| P10 full chain | `python verify_p10_final.py` | **22/22 PASS** |
| P10 cross-process contract | `python verify_p10_live_contract.py` | **8/8 PASS** |

The one failure is `tests/test_ui.py::test_08_headless_ui_step_and_render` —
`ModuleNotFoundError: No module named 'pygame'`. Environment, not code; pygame was
deliberately not installed. The render semantics it would cover are covered headlessly by
`tests/test_game_ui_render_smoke.py`.

---

## 1. Definition of Done (root `CLAUDE.md` §28)

| # | Requirement | Status | Evidence |
|---|---|---|---|
| 1 | Hardware telemetry enters through a defined ingestion contract | PASS | `tests/test_telemetry_ingest.py`; smoke F |
| 2 | Invalid telemetry is safely rejected | PASS | `tests/test_telemetry_ingest.py`, `tests/test_failure_modes.py`; smoke D |
| 3 | Valid telemetry updates Twin state | PASS | `test_backend_forwards_hardware_telemetry_to_canonical_twin`; smoke G |
| 4 | Twin state carries timestamps and freshness | PASS | `tests/test_twin_state_store.py`, `tests/test_clock_domains.py` |
| 5 | Physical and simulated assets coexist | PASS | `tests/test_hybrid_coexistence.py` |
| 6 | `game_ui.py` reads Twin state | PASS | `tests/test_game_ui_twin_client.py` |
| 7 | Technician HMI reads Twin state | PASS | `frontend/src/data/twinVehicle.test.ts`, `providers/LiveDataProvider` suites |
| 8 | Operator HMI reads Twin state | PASS | `frontend/src/screens/operatorView.test.tsx` |
| 9 | Frontend reflects live hardware telemetry when available | PASS | `twinVehicle.test.ts`; browser-verified in P6.1 |
| 10 | WebSocket updates work | PASS | `tests/test_ws_ingestion_boundary.py`, `tests/test_twin_projection.py`; smoke J |
| 11 | Safety solver uses Twin state | PASS | `tests/test_physics_unification.py`, `twin/ui_domain.py` |
| 12 | Commands originate from authoritative safety logic | PASS | `tests/test_command_gateway.py` |
| 13 | Existing V2V protocol remains compatible | PASS | `tests/test_physical_v2v_payload.py`, `test_v2v_hmi_integration.py` |
| 14 | Stale data is handled | PASS | `tests/test_stale_data.py`, `tests/test_clock_domains.py` |
| 15 | Hardware disconnection is handled | PASS | `test_mode_reports_live_only_while_hardware_is_recent` (**P9**); smoke B/F |
| 16 | Command timeout / fallback is handled | PASS | `tests/test_command_gateway.py` (`expire_pending`) |
| 17 | Units are documented | PASS | `docs/ARCHITECTURE_STATUS.md`, module docstrings; SI internally |
| 18 | Configuration is centralized | PASS | `test_freshness_thresholds_come_from_configuration` (**P9**) |
| 19 | Automated tests pass | PASS | table above (one environment failure, stated) |
| 20 | Manual end-to-end test passes | PASS | live smoke 12/12, §4 below |
| 21 | No fake physical validation is claimed | PASS | every artefact labels SIMULATION / EMULATED |

## 2. Safety and honesty invariants

| Invariant | Status | Evidence |
|---|---|---|
| UNAVAILABLE ≠ 0 ≠ safety fallback | PASS | `test_unavailable_is_not_zero_and_not_a_safety_fallback` |
| No `v_safe` never renders as NORMAL | PASS | `operatorAction.test.ts`, `operatorView.test.tsx` |
| Safety state is never colour-only | PASS | `operatorView.test.tsx` (colour stripped before every assertion) |
| μ ≤ 0 or non-finite fails CLOSED (`v_safe = 0`) | PASS | `fog_safe` `_invalid_friction_result`, `tests/test_physics_unification.py` |
| `source=DERIVED, origin=HARDWARE` never collapses to HARDWARE | PASS | `tests/test_twin_projection.py`, `operatorView.test.tsx` |
| PWM-derived speed never published as measured | PASS | `test_pwm_derived_speed_is_never_projected_as_hardware` |
| Simulation fields never stale against the wall clock | PASS | `tests/test_clock_domains.py`, `test_twin_projection.py` |
| A client cannot declare HARDWARE provenance (WS) | PASS | `tests/test_ws_ingestion_boundary.py`; smoke J |
| A client cannot declare LIVE provenance (HTTP) | PASS | `test_mock_ingress_cannot_declare_itself_live` (**P9**); smoke E |
| A disconnected ESP32 is not reported as connected | PASS | `test_mode_reports_live_only_while_hardware_is_recent` (**P9**) |
| Rejections are visible, not silently zero | PASS | `test_rejected_counter_counts_every_refusal` (**P9**); smoke I |
| Absent components report null, not zero | PASS | `test_observability_reports_null_not_zero_for_absent_components` (**P9**) |
| Gateway never raises a commanded speed | PASS | `tests/test_command_gateway.py` |
| One malformed packet never kills the backend | PASS | `tests/test_failure_modes.py`; smoke D + L |

## 3. Configuration and environment

| Check | Status | Evidence |
|---|---|---|
| Config resolves from any working directory | PASS | executed from 6 directories incl. outside the repo; `test_config_is_found_from_any_working_directory` |
| Freshness thresholds come from `integration_config.json` | PASS | `test_freshness_thresholds_come_from_configuration` |
| No credentials in tracked source | PASS | repo-wide grep for password/ssid/secret/token literals: no match |
| No debug/eval endpoints on the HMI backend | PASS | grep of `backend/app/`: no match |
| CORS restricted to configured origins | PASS | `backend/app/main.py`; behaviour change documented in the runbook |
| AMB-014 (HMI stale timeout) resolved | **NOT TESTED — UNRESOLVED** | no authoritative value exists; frontend supplies no default and fails loudly. Deliberate. |

## 4. Live end-to-end smoke (real uvicorn process)

Backend started from `SYNQRA_SIH2026-27-HMI/backend/` on port 8077, driven over real
HTTP and a real WebSocket. **12/12 PASS.**

| Case | Check | Status |
|---|---|---|
| A | `/api/health` responds | PASS |
| B | mode is MOCK before any hardware packet | PASS |
| C | Twin, ingestor and gateway are attached | PASS |
| D | malformed telemetry rejected with HTTP 400 | PASS |
| E | mock ingress cannot declare itself LIVE | PASS |
| F | hardware ingress flips mode to LIVE | PASS |
| G | Twin projection carries provenance; no fabricated `position_s` | PASS |
| H | unknown vehicle refused AND counted | PASS |
| I | command rejection increments the aggregate counter | PASS |
| J | WebSocket connects; forged HARDWARE provenance downgraded to SIMULATION | PASS |
| K | malformed WebSocket frame answered `MALFORMED_JSON`, socket stays alive | PASS |
| L | server still healthy after the whole sweep | PASS |

## 5. P10 - the full causal chain (`verify_p10_final.py`)

One continuous walk, in-process, **22/22 PASS**. Every hop calls the authoritative
component; the script computes nothing of its own.

| Hop | Claim | Status |
|---|---|---|
| 1 | environment reaches the canonical Twin | PASS |
| 2 | the fog_safe result is held by the Twin as `DERIVED` / origin `SIMULATION` | PASS |
| 3 | dense fog lowers v_safe (13.89 -> 1.55 m/s) | PASS |
| 4 | v_command never exceeds v_safe | PASS |
| 5 | a target above v_safe is REFUSED, and the refusal is counted | PASS |
| 6 | a target within v_safe is ACCEPTED | PASS |
| 7 | the vehicle local governor clamps a too-fast command (Tier-1 authoritative) | PASS |
| 8 | vehicle telemetry re-enters through the canonical ingestion boundary | PASS |
| 9 | emulated telemetry is NOT labelled as physical hardware | PASS |
| 10 | the Twin projects to the single REST/WS shape | PASS |
| 11 | the projected v_safe is the Twin value, unchanged | PASS |
| 12 | a hybrid vehicle keeps both domains distinct; neither overwrites the other | PASS |
| 12b | a field no source measures stays UNAVAILABLE, never fabricated | PASS |
| 13 | the HMI receives provenance, not a bare number | PASS |
| 14 | a fresh simulation-domain field reads CURRENT, evaluated in its own domain | PASS |
| 14b | staleness is detectable, and a stale value keeps its last known number | PASS |
| 15 | game_ui displays the Twin v_safe, not one of its own | PASS |
| 16 | an unavailable value renders as a marker, never as 0 or a speed | PASS |
| 17 | a missing ceiling never implies clearance | PASS |
| 18 | v_safe recovers when the fog clears (1.55 -> 13.89 m/s) | PASS |
| 19 | v_safe is monotonic in visibility across the sweep | PASS |
| 20 | reading and commanding never mutate Twin state | PASS |

Measured sweep, written to `results/P10_E2E_TRACE.csv`:

| visibility (m) | 50 | 30 | 10 | 6 | 30 | 50 |
|---|---|---|---|---|---|---|
| v_safe (m/s) | 13.89 | 12.00 | 4.26 | 1.55 | 12.00 | 13.89 |

The same chain runs under pytest as `tests/test_p10_chain.py`, which imports the runner
rather than reimplementing it, so the demo and the test cannot diverge.

## 6. P10 - the process boundary (`verify_p10_live_contract.py`)

A real uvicorn backend, a captured payload, and the frontend own schema. **8/8 PASS**.

| # | Claim | Status |
|---|---|---|
| 1 | telemetry accepted on the physical ingress | PASS |
| 2 | the backend serves a Twin projection (15 fields) | PASS |
| 3 | the response is captured verbatim to `contracts/fixtures/live/TwinVehicle.live.json` | PASS |
| 4 | no unmeasured field was fabricated (`position_s`, `heading_rad` both absent) | PASS |
| 5 | all 15 captured fields carry the full provenance envelope | PASS |
| 6 | the physical ingress is labelled `HARDWARE` | PASS |
| 7 | PWM-derived speed stays `DERIVED` with origin `HARDWARE` | PASS |
| 8 | the frontend parses the live capture with its real Zod schema (5 tests) | PASS |

**Falsifiability checked.** Renaming `rpm.source` to `rpm.src` inside the capture fails all
five frontend tests, naming the offending field path. The check is able to fail, so its
passing means something.

## 7. Not verified

| Item | Status | Why |
|---|---|---|
| Physical ESP32 telemetry | NOT TESTED | no hardware was connected in P0–P9 |
| Pygame render loop on screen | NOT TESTED | `pygame` deliberately not installed |
| LAN / multi-host deployment | NOT TESTED | single-host only; CORS change affects this — see runbook |
| Long-duration soak / memory behaviour | NOT TESTED | out of P0–P9 scope |
| Two-process shared Twin | NOT TESTED | the backend and Pygame processes hold separate instances by design today |
