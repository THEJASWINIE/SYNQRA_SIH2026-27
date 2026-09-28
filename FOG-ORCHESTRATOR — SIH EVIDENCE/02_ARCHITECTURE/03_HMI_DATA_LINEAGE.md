# FOG-ORCHESTRATOR 2.0 — HMI Data Lineage & Contract Traceability
**Document ID:** `DOC-02-ARCH-03` | **Audited Standard:** Rule 6 Compliance (Zero Client-Side Physics)

---

## 1. Compliance with Rule 6: Proving Frontend is Pure Projection

In accordance with **Rule 6 of `AGENTS.md`**, frontend clients must NEVER independently calculate or fabricate:
- Vehicle position or velocity
- Safe speed ceilings
- Environmental visibility or road friction
- Fleet hazard status

All frontend display values are strictly bound to authoritative backend telemetry fields:

| HMI Display Field | Authoritative Backend Source | Transport Mechanism | Provenance Tag |
| :--- | :--- | :--- | :--- |
| **Actual Speed ($m/s$)** | `twin_state_store.vehicles[id].speed_mps` | WebSocket `/ws/telemetry` | `PHYSICAL (DERIVED)` |
| **Wheel RPM** | `twin_state_store.vehicles[id].rpm` | WebSocket `/ws/telemetry` | `PHYSICAL (DERIVED)` |
| **Safe Speed Limit ($v_{safe}$)** | `twin_state_store.vehicles[id].safe_speed_mps` | WebSocket `/ws/telemetry` | `MATHEMATICAL / PHYSICS` |
| **Visibility ($m$)** | `twin_state_store.environment.visibility_m` | WebSocket `/ws/telemetry` | `INJECTED WEATHER CONDITION` |
| **Road Surface Friction ($\mu$)**| `twin_state_store.roads[road_id].friction_mu` | WebSocket `/ws/telemetry` | `GEODATA ESTIMATE` |
| **Governor Warning State** | `twin_state_store.vehicles[id].governor_state` | WebSocket `/ws/telemetry` | `SOFTWARE VERIFIED` |
| **Communication Freshness** | `current_time - telemetry.received_at` | Client timestamp delta | `NETWORK HEALTH` |

---

## 2. In-Cab Operator Console Contract (`speedContract.ts`)

The operator screen continuously evaluates the difference between actual vehicle speed ($v_{actual}$) and safe governed speed ($v_{safe}$):
- $\Delta v = v_{actual} - v_{safe}$
- If $\Delta v \le 0.00	ext{ m/s}$: **NORMAL (Green)** — Vehicle operating within safe physics envelope.
- If $0.00 < \Delta v \le 0.15	ext{ m/s}$: **CAUTION (Amber)** — Vehicle approaching safe speed limit.
- If $\Delta v > 0.15	ext{ m/s}$: **SLOW DOWN (Flashing Red + Audio)** — Vehicle exceeding safe speed; instructs driver to decelerate.
- If $F_{fog} \le 0.10$: **SEVERE FOG STOP / CRAWL (Red)** — Visibility below 30m; instructs driver to hold at designated refuge bay.
