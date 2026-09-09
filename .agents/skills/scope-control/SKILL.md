---
name: scope-control
description: Component ownership and authority boundaries for the merged SYNQRA / FOG-ORCHESTRATOR system. Use when planning, implementing, reviewing, or modifying any project functionality.
---

# SYNQRA Scope Control

This repository is the **merged SYNQRA / FOG-ORCHESTRATOR system**. It contains the
Digital Twin, the physics/safety engine, telemetry ingestion, hardware firmware, the
command path, the Technician HMI and the `game_ui.py` visualization.

The authoritative project-level instruction set is the **root `AGENTS.md`**. This skill
does not override it and must never contradict it. Where this skill is silent, `AGENTS.md`
governs.

Scope control here is **not** "Task 1 versus Task 2". Both halves are in scope. Scope
control is about **which component owns which responsibility**, so that no second
authoritative implementation is created.

## Authoritative Components (rulings — do not re-litigate)

| Responsibility | Authoritative implementation |
|---|---|
| Digital Twin state | `SYNQRA_SIH2026-27-main/twin/` + its `models/`, `network`, `state` components |
| Physics / safety solver | `fog_safe/` (single runtime engine) |
| Physics compatibility shim | `SYNQRA_SIH2026-27-main/models/vehicle_physics.py` — adapter to `fog_safe`, not a solver |
| Offline benchmark / study path | `fog_orchestrator/` — not a runtime safety path |
| Frozen baseline | `SYNQRA_SIH2026-27-main/V0_1_BASELINE/` — read-only |
| Local vehicle safety authority | Tier-1 governor on the vehicle — central orchestration never overrides it |

Backend stores and frontend stores are **caches / projections** of Twin state. They are
never authoritative.

## Layer Ownership

### Presentation layer owns (React HMI, `game_ui.py`, Operator HMI)

- Visualization and rendering
- Monitoring and operator awareness
- Vehicle state display
- Safety state display
- Bottleneck, queue, dispatch and slot visualization
- Replay
- Diagnostics
- Data freshness display
- Communication health display
- KPI display
- Scenario controls
- Mock data for independent HMI development
- UI state: selection, filters, presentation state, connection state

### Presentation layer must NOT own

- Authoritative vehicle speed, position, heading
- Safe speed, safe headway, commanded speed
- Visibility, friction, road or environment state
- Safety state or command state
- Any mutation of authoritative vehicle state

A presentation component that computes one of those, or writes one back into a store, is
a defect. It reads the value from the Twin, via the backend, and displays it.

### Domain layer owns (Twin, physics/safety, orchestration, command gateway)

- Digital Twin state, relationships and synchronization
- Vehicle, road, mine and environment models
- Fog and environment simulation
- Vehicle dynamics and road simulation
- Safe speed and safe headway calculation
- Queue prediction, bottleneck computation
- Dispatch and route optimization
- Command generation, validation and gating

## Decision Rule

The presentation layer **displays** values that the domain layer **computed**.

Before adding a computation, find its owner in the table above and extend that component.
If the computation has no owner yet, name the owner explicitly before writing code —
do not let it land wherever it was convenient.

If a presentation feature needs domain data that does not exist yet, define a typed
interface and mock it, rather than computing it in the UI.

## Duplication Rule

Never create a second implementation of an authoritative responsibility.

Before implementing, check whether it already exists (`AGENTS.md` §4, §27). If two
implementations exist, identify the authoritative one, adapt the weaker one to it, and
deprecate rather than silently maintain both.

## Provenance Rule

Every value carries its provenance: `SIMULATION`, `HARDWARE` or `HYBRID`.

Never label synthetic, PWM-derived, assumed or emulated values as measured physical
telemetry. Never invent position, heading, friction or visibility and present it as a
hardware measurement.

## Before Completing Work

Verify explicitly:

1. No second Digital Twin, physics engine, safety solver or state store was created.
2. No presentation component computes or mutates authoritative state.
3. Provenance is explicit for every value introduced.
4. The frozen V2V packet format is unchanged.
