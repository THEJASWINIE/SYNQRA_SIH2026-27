# ARCHITECTURE STATUS — SYNQRA / FOG-ORCHESTRATOR

Status as of P9. Every claim below is backed by a test or a command in
[VERIFICATION_MATRIX.md](VERIFICATION_MATRIX.md). Where something is unverified it says
so; nothing here is asserted from reading code alone.

**Provenance of all evidence in this document: SIMULATION and EMULATED.**
No physical ESP32 was connected during P0–P9. Nothing here claims physical validation.

---

## 1. What is authoritative

| Concern | Single authority | Everything else |
|---|---|---|
| Digital Twin state | `SYNQRA_SIH2026-27-main/twin/twin_state_store.py` (`TwinStateStore`) | The HMI backend cache and the Pygame renderer are CLIENTS |
| Safety / physics | `fog_safe/` (`solve_safe_speed`) | `models/vehicle_physics.py` is a documented ADAPTER over it |
| Telemetry entry | `telemetry_ingest.py` (`TelemetryIngestor`) | REST, WebSocket, serial and V2V all converge here |
| Commands | `command_gateway.py` (`CommandGateway`) | The vehicle's local governor stays Tier-1 authoritative |
| Twin → client shape | `twin_projection.py` (`build_vehicle_projection`) | REST and WebSocket serve the SAME function's output |
| Timing thresholds | `config/integration_config.json` via `integration_adapters/config_paths.load_timeouts()` | No literal thresholds at use sites |

There is no second Twin, no second solver, and no second ingestion path.

## 2. Process boundaries

See [ARCHITECTURE_DIAGRAM.md](ARCHITECTURE_DIAGRAM.md). Three processes can run, in any
combination:

1. **HMI backend** — `uvicorn app.main:app` from `SYNQRA_SIH2026-27-HMI/backend/`.
   Owns the in-process `TwinStateStore`, the ingestor, the command gateway.
2. **React frontend** — `npm run dev` from `SYNQRA_SIH2026-27-HMI/frontend/`.
   Pure presentation. Holds UI state only.
3. **Pygame visualiser** — `python game_ui.py` from `SYNQRA_SIH2026-27-main/`.
   Runs its own simulator and its own in-process Twin; it is a Twin READER, not an owner.

The Pygame process and the backend process do NOT currently share one Twin instance —
each holds its own. That is a real limitation, stated in §7.

## 3. Data provenance model

Every dynamic field carries `value / timestamp / source / origin / quality / clock_domain`.

* `source` — how the value was produced: `HARDWARE`, `SIMULATION`, `DERIVED`, `CONFIGURED`, `UNKNOWN`
* `origin` — what the derivation ultimately rests on. `source=DERIVED, origin=HARDWARE`
  must never be shown as `HARDWARE`, and must never be shown as simulation either.
* `clock_domain` — `WALL_CLOCK` or `SIMULATION`. Freshness is only ever evaluated within
  one domain; a simulation timestamp is never compared to epoch time.

**UNAVAILABLE is not zero, and not a safety fallback.** A missing safe speed renders as
`--` in Pygame and `SAFETY DATA UNAVAILABLE` in the operator HMI. It never becomes
`NORMAL`, never becomes `0`, and never becomes the old hardcoded `13.89 m/s`.

## 4. Provenance cannot be self-declared

A client cannot make its data physical by saying so. Provenance is decided by the
transport it arrived on:

| Ingress | Provenance | Closed in |
|---|---|---|
| `POST /api/hardware/telemetry` | HARDWARE | P3 |
| `POST /api/telemetry` | SIMULATION (`data_quality` forced to `SIMULATED`) | **P9** |
| `WS /api/ws` inbound | SIMULATION | P5.1 |
| Serial gateway | caller-declared, defaulting to SIMULATION | P3 |

`TRUCK_02`'s speed is PWM-derived, so it is published as `source=DERIVED`, never as a
measured speed (`PWM_DERIVED_SPEED_VEHICLES` in `telemetry_ingest.py`).

## 5. Hardware-status honesty (P9)

`HMI_MODE` used to latch to `LIVE` on the first hardware packet and never clear, so
`/api/mode` kept reporting `LIVE` long after an ESP32 was unplugged. Mode is now reported
from evidence: a VALIDATED packet on the physical ingress within
`offline_threshold_seconds`. `/api/mode` and `/api/observability` distinguish
`hardware_seen` (it happened once) from `hardware_connected` (it is happening now).

## 6. Observability (P9)

`GET /api/observability` exposes the counters the ingestor and gateway already kept:
accepted / duplicate / out_of_order / invalid / unknown_vehicle, and
accepted / rejected / duplicate / stale / unsafe / timeout. A component that is not wired
reports `null`, never `0`.

The gateway's `rejected` counter was previously always `0` while the specific buckets
filled — an operator reading it would have concluded nothing was ever refused. `rejected`
is now the total of every refusal at the gate (`timeout` excluded: a timed-out command was
accepted first).

## 7. Known limitations

1. **Two Twin instances.** The Pygame process and the backend process each construct their
   own `TwinStateStore`. Unifying them needs an out-of-process Twin or an IPC hop; neither
   was in P0–P9 scope.
2. **AMB-014 unresolved.** The HMI stale-timeout threshold has no authoritative value. The
   frontend deliberately supplies NO default and fails loudly (`config/freshness.ts`).
   Backend freshness is separately configured; the two are not the same number and should
   not be conflated. **No value was invented.**
3. **The visualiser Twin now evaluates freshness.** Until P10 it was built with
   `stale_after_s=None`, so under the P1 rule freshness was never evaluated in that
   process and the renderer could not show STALE. It now uses the same configured
   `max_telemetry_age_seconds` as the backend and the command gateway. No value was
   invented.
4. **`pygame` is not installed**, so `SYNQRA_SIH2026-27-main/tests/test_ui.py::test_08`
   fails on import. The render-path semantics are covered headlessly by
   `tests/test_game_ui_render_smoke.py` instead.
5. **No physical hardware run.** Every result is SIMULATION or EMULATED.
6. **`fog_orchestrator/` contains a second safety governor and a second `DigitalTwin`.**
   It is reachable only from three verification scripts and is not on any live path, but it
   has not been merged or removed. See §3 of the P9 report.
7. **Vehicle expiry/removal is deferred.** A vehicle never leaves the Twin; it only goes
   stale. Deliberate, agreed at P1.
8. **CORS is now restricted** to `HMI_CORS_ORIGINS` (default localhost:5173). A LAN demo
   must set that variable — see [DEMO_RUNBOOK.md](DEMO_RUNBOOK.md).

## 8. Frozen contracts

* **V2V packet format** `STATE,TRUCK_0x,seq,rpm,speed,ax,ay,az,gx,gy,gz` — unchanged
  through P0–P9. The format carries no time field, so parser arrival time is never
  promoted to a measurement timestamp.
* **`SYNQRA_SIH2026-27-main/V0_1_BASELINE/`** — frozen reference implementation. Kept,
  never modified, and excluded from collection (basename clash) by
  `SYNQRA_SIH2026-27-main/pytest.ini`.
* **`esp32_code/`** firmware — unchanged apart from the credential extraction into
  `secrets.example.h` agreed at P0.
