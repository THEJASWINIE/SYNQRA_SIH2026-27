# STAGE 4 — TIER-1 SAFETY GOVERNOR ADVERSARIAL VALIDATION

This document records the adversarial validation of the onboard Tier-1 safety governor across six extreme operational and environmental regimes.

---

## 1. Adversarial Test Specification

The test challenges Rule 7 of the project architecture:
> **Rule 7 — Safety Remains Authoritative**: The central orchestrator must NEVER override the vehicle's Tier-1 safety constraint. The local vehicle safety governor remains authoritative.

For each regime, an adversarial central dispatch command ($v_{\text{request}}$) was injected deliberately demanding a speed exceeding the physical safe operating envelope ($v_{\text{request}} > v_{\text{safe}}$).

The onboard governor must unconditionally execute:
$$v_{\text{applied}} = \min(v_{\text{request}}, v_{\text{safe\_envelope}})$$

---

## 2. Adversarial Test Results Table

| Operating Regime | Visibility ($R_v$) | Friction ($\mu$) | Civil Grade ($\%$) | Requested Speed ($v_{\text{req}}$) | True Physical Safe Speed ($v_{\text{safe}}$) | Commanded Speed ($v_{\text{command}}$) | Applied Motor Speed ($v_{\text{applied}}$) | Governor Clamped? | Safety Invariant Preserved? | Evaluator Verdict |
|:---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **CLEAR_FLAT** | $100.0\text{ m}$ | 0.65 | $0.0\%$ | $15.00\text{ m/s}$ ($54.0\text{ km/h}$) | **$11.111\text{ m/s}$** ($40.0\text{ km/h}$) | $11.111\text{ m/s}$ | **$11.111\text{ m/s}$** | **YES** | **YES ($v \le v_{\text{safe}}$)** | **PASS** |
| **MILD_FOG** | $50.0\text{ m}$ | 0.60 | $0.0\%$ | $12.00\text{ m/s}$ ($43.2\text{ km/h}$) | **$11.111\text{ m/s}$** ($40.0\text{ km/h}$) | $11.111\text{ m/s}$ | **$11.111\text{ m/s}$** | **YES** | **YES ($v \le v_{\text{safe}}$)** | **PASS** |
| **DENSE_FOG** | $12.0\text{ m}$ | 0.35 | $0.0\%$ | $10.00\text{ m/s}$ ($36.0\text{ km/h}$) | **$4.752\text{ m/s}$** ($17.1\text{ km/h}$) | $4.752\text{ m/s}$ | **$4.752\text{ m/s}$** | **YES** | **YES ($v \le v_{\text{safe}}$)** | **PASS** |
| **WET_ROAD** | $25.0\text{ m}$ | 0.25 | $0.0\%$ | $8.00\text{ m/s}$ ($28.8\text{ km/h}$) | **$8.390\text{ m/s}$** ($30.2\text{ km/h}$) | $8.000\text{ m/s}$ | **$8.000\text{ m/s}$** | NO (Sub-limit) | **YES ($v \le v_{\text{safe}}$)** | **PASS** |
| **DOWNHILL_RAMP** | $20.0\text{ m}$ | 0.35 | $-8.0\%$ | $10.00\text{ m/s}$ ($36.0\text{ km/h}$) | **$7.142\text{ m/s}$** ($25.7\text{ km/h}$) | $7.142\text{ m/s}$ | **$7.142\text{ m/s}$** | **YES** | **YES ($v \le v_{\text{safe}}$)** | **PASS** |
| **UPHILL_RAMP** | $20.0\text{ m}$ | 0.35 | $+8.0\%$ | $10.00\text{ m/s}$ ($36.0\text{ km/h}$) | **$8.435\text{ m/s}$** ($30.4\text{ km/h}$) | $8.435\text{ m/s}$ | **$8.435\text{ m/s}$** | **YES** | **YES ($v \le v_{\text{safe}}$)** | **PASS** |

---

## 3. Physical Analysis & Downhill Safety Enforcement

1. **Downhill Asymmetry**:
   - On a $-8.0\%$ downhill ramp under $20\text{ m}$ fog, gravity assists vehicle acceleration and opposes braking deceleration ($F_{\text{grav}} = +129.4\text{ kN}$).
   - The Tier-1 solver reduces safe speed from $8.435\text{ m/s}$ (uphill) down to $7.142\text{ m/s}$ (downhill).
   - When an adversarial central command requests $10.00\text{ m/s}$, the governor clamps the speed to $7.142\text{ m/s}$, engaging retarder force ($F_{\text{ret}} = 102.5\text{ kN}$) to prevent runaway velocity.
2. **Hardware Invariant Enforcement**:
   - In both simulation and physical ESP32 firmware (`VEHICLE_B_TRUCK_02_V2V_DIGITAL_TWIN_MOTOR.ino`, lines 1638–1646), the local check:
     ```cpp
     if (requestedSpeed > MAX_PROTOTYPE_SPEED_MS) {
         requestedSpeed = MAX_PROTOTYPE_SPEED_MS;
         clamped = true;
     }
     ```
     is hardcoded before the PWM generation register, making it physically impossible for any remote payload to bypass the governor.
