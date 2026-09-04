# FOG-ORCHESTRATOR 2.0 — VISIBILITY TO VELOCITY TEST PLAN

**Date**: 2026-08-29  
**Author**: Verification & Validation Team  
**Scope**: Deterministic Verification Plan for Digital Twin Visibility $\rightarrow$ Physics Safe Velocity $\rightarrow$ Vehicle Velocity Command

---

## 1. Objective

Validate that changes in Digital Twin visibility pass through the authoritative physics solver (`fog_safe.safety.solve_safe_speed`), generate corresponding safe velocities, transport them via `TwinVelocityAdapter` to `DispatchCommandMessage`, and verify local safety governor clamping on physical vehicle emulators.

---

## 2. Test Suite Matrix (T1 – T8)

| Test ID | Scenario Description | Initial Visibility | Target Visibility | Expected Physics Behavior | Expected Command Action | Expected Safety Governor ACK |
|---|---|---|---|---|---|---|
| **T1** | Clear Visibility Baseline | — | $50.0\text{ m}$ | Physics computes $v_{\text{safe}} > 10.0\text{ m/s}$ ($36\text{ km/h}$) | Transport $v_{\text{safe}}$ to command interface | `ACCEPTED` / `CLAMPED` to $v_{\text{safe}}$ |
| **T2** | Moderate Fog Reduction | $50.0\text{ m}$ | $30.0\text{ m}$ | Physics decreases $v_{\text{safe}}$ dynamically | Command velocity matches new $v_{\text{safe}}$ | `ACCEPTED` / `CLAMPED` to lower $v_{\text{safe}}$ |
| **T3** | Dense Fog Reduction | $30.0\text{ m}$ | $15.0\text{ m}$ | Physics decreases $v_{\text{safe}}$ further ($< 6\text{ m/s}$) | Command velocity matches new $v_{\text{safe}}$ | `ACCEPTED` / `CLAMPED` to dense fog limit |
| **T4** | Downward Dynamic Step Chain | $50\text{ m}$ | $50 \rightarrow 30 \rightarrow 15\text{ m}$ | Physics output decreases monotonically | Commands decrease synchronously | Local governor enforces step-down ceilings |
| **T5** | Upward Recovery Transition | $15\text{ m}$ | $15 \rightarrow 30 \rightarrow 50\text{ m}$ | Physics output increases monotonically | Commands increase synchronously | Local governor allows speed recovery |
| **T6** | High-Frequency Rapid Oscillations | Variable | Oscillating $50 \leftrightarrow 15\text{ m}$ | No stale timestamp or command reuse | Timestamps strictly increase | Latest physics velocity executed |
| **T7** | Invalid Sensor Input | $30.0\text{ m}$ | `NaN` / $-5.0\text{ m}$ | Fallback to $0.0\text{ m/s}$ / minimum safe speed | Emit emergency fallback `STOP` command | Emergency local hold executed |
| **T8** | Unsafe Command Speed | $15.0\text{ m}$ | $15.0\text{ m}$ ($v_{\text{safe}} \approx 5.4\text{ m/s}$) | Dispatch requested speed $12.0\text{ m/s}$ | Command contains requested $12.0\text{ m/s}$ | `CLAMPED` by local safety governor to $v_{\text{safe}}$ |

---

## 3. Automated & Hardware Verification Runner

Executed via [`verify_visibility_velocity_integration.py`](file:///c:/Users/JAGADEESH%20M/OneDrive/Documents/SIH-2026-27/verify_visibility_velocity_integration.py).
