---
name: task1-architecture
description: Architecture rules for the FOG-ORCHESTRATOR Task 1 HMI. Use when planning or modifying frontend, backend, data flow, APIs, or integration.
---

# Task 1 Architecture

The HMI must work independently before Task 2 is integrated.

## Required Data Flow

Data Provider
    ↓
Normalization Layer
    ↓
Typed Application State
    ↓
React HMI

## Providers

Support two conceptual providers:

1. MockDataProvider
2. LiveDataProvider

MockDataProvider is used during independent development.

LiveDataProvider will later consume the agreed Task 2 integration interface.

## Architecture Rules

- UI components must not directly consume raw mock JSON.
- Transport logic must not be embedded inside visual components.
- Centralize schemas and types.
- Normalize external data before it reaches application state.
- Keep the data source replaceable.
- Do not require Task 2 to be complete for Task 1 development.

## Required Major Screens

1. Operations Overview
2. Vehicle Detail
3. Bottleneck & Queue
4. Dispatch & Slots
5. Event & Replay
6. Diagnostics

## Before Making Architectural Changes

Check:

1. Does this preserve provider abstraction?
2. Does this introduce Task 2 functionality?
3. Does this make integration harder?
4. Is the feature independently testable with mock data?