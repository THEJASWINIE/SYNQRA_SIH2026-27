---
name: scope-control
description: Enforce strict Task 1 versus Task 2 boundaries for FOG-ORCHESTRATOR 2.0. Use when planning, implementing, reviewing, or modifying project functionality.
---

# Task 1 Scope Control

This repository is exclusively for Task 1: the Human-Machine Interface.

Before implementing any feature, determine whether it belongs to Task 1 or Task 2.

## Task 1 Owns

- Visualization
- Monitoring
- Alerts
- Operator awareness
- Vehicle state display
- Safety state display
- Bottleneck visualization
- Queue visualization
- Dispatch visualization
- Slot visualization
- Replay
- Diagnostics
- Data freshness display
- Communication health display
- KPI display
- Scenario controls
- Mock data for independent HMI development

## Task 2 Owns

Do not implement:

- Digital Twin algorithms
- Vehicle physics
- Fog physics
- Road simulation
- Safe speed calculation
- Safe headway calculation
- Queue prediction
- Bottleneck computation
- Dispatch optimization
- Route optimization
- Physics-based simulation

## Decision Rule

Task 1 visualizes externally provided values.

Task 2 calculates, predicts, optimizes, or simulates those values.

If a feature requires Task 2 data that is unavailable, create a typed interface and mock data rather than implementing the Task 2 algorithm.

Before completing work, explicitly verify that no Task 2 responsibility has been duplicated.