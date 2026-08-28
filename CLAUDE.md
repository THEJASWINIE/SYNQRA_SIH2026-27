# FOG-ORCHESTRATOR 2.0 — TASK 1

## Authoritative Specification

The single authoritative functional specification for Task 1 is:

`docs/FOG_ORCHESTRATOR_Task1_HMI_Requirements.pdf`

This is the canonical path. There is no second Task 1 specification. Every document,
plan and reference in this repository shall cite exactly this path.

## Planning Baseline

Planning Baseline v1.3 is frozen. See `requirements/DECISIONS.md`.
The six planning documents in `requirements/` are the controlled inputs to
implementation and change only through the revision rule in `DECISIONS.md`.

## Project Ownership

This repository is exclusively for Task 1: the Human-Machine Interface (HMI).

Task 2, the Digital Twin, is being developed independently by another team.

Do not implement Task 2 functionality in this repository.

## Task 1 Responsibilities

Task 1 owns:

- Operations Overview
- Vehicle Detail
- Bottleneck and Queue visualization
- Dispatch and Slots visualization
- Event logging and Replay
- Diagnostics
- Alerts
- Communication health visualization
- KPI visualization
- Scenario controls
- Optional laptop-side Computer Vision after mandatory HMI completion

## Task 2 Responsibilities — OUT OF SCOPE

Do not implement:

- Vehicle physics
- Mine simulation
- Digital Twin algorithms
- Fog physics
- Safe speed calculations
- Safe headway calculations
- Bottleneck algorithms
- Queue prediction algorithms
- Dispatch optimization
- Route optimization

Task 1 receives these values through a data interface and visualizes them.

## Architecture Rule

The HMI must work independently using mock data.

The architecture must support:

MockDataProvider
    ↓
Normalized Application State
    ↓
HMI

Later:

Task 2 API / WebSocket / MQTT
    ↓
LiveDataProvider
    ↓
Normalized Application State
    ↓
HMI

UI components must not directly depend on raw mock data.

## Provisional Architecture Decisions

Binding until the authoritative specification or the integration team explicitly
states otherwise. Recorded in full, with owners and revisit conditions, in
`requirements/DECISIONS.md` (PAD-A through PAD-G). Implementation decisions approved for
M2 onward are recorded there as MAD-A through MAD-G, M3 implementation
decisions as MID-A through MID-F, and M4 implementation decisions as M4D-A
through M4D-F.

- **A.** Task 1 is an HMI and supervisory visualization system.
- **B.** Task 1 does not directly actuate vehicles or equipment.
- **C.** Task 1 may display externally supplied commands, recommendations, dispatch
  states and slot assignments.
- **D.** Task 1 may acknowledge HMI alerts and events where required. Acknowledgement
  must never imply that an underlying safety condition has been removed.
- **E.** Values belonging to Digital Twin computation, prediction, optimization or
  simulation must be received as external provider data.
- **F.** Current headway, `h_safe`, arrival plans, queue forecasts and operational KPIs
  must not be locally invented or algorithmically generated when their source is
  undefined. Use typed mock inputs during independent development.

## Missing Numerical Thresholds

Where the specification omits a numeric threshold, do not invent one. Represent it as a
named configuration placeholder marked as requiring authoritative confirmation, and state
the measured value alongside it. Known cases: HMI-NFR-001, HMI-NFR-002, CV-004, and
**HMI-NFR-003** — the staleness timeout, which the specification requires to be
configurable but never assigns a value (AMB-014).

## Engineering Rules

Before writing code:

1. Inspect the existing repository.
2. Explain the implementation plan.
3. Identify affected files.
4. Implement only the requested milestone.
5. Do not modify unrelated code.
6. Run relevant tests and checks.
7. Do not claim completion without verification.

## Current Status

Project stage: FOUNDATION

Do not implement the full application yet.
Do not implement any Digital Twin algorithms.

The immediate objective is to establish the requirements,
architecture, repository structure, and implementation plan.