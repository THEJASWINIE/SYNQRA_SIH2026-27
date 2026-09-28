# 01 — EXECUTIVE SUMMARY
## FOG-ORCHESTRATOR 2.0 — Sensor / Data Degradation Research
**Project:** SIH26007 — Safe and Efficient Mine Vehicle Operation in Fog / Low Visibility  
**Date:** 2026-09-21  
**Status:** RESEARCH COMPLETE — DECISION REACHED  
**Report Type:** Pre-implementation research. NO code written.

---

## 1. Research Mandate

Determine whether a **Sensor / Data Health / Degradation Layer** should be inserted between
environmental/vehicle telemetry and the existing physics + safety governor, and whether this
materially improves system robustness without introducing unsafe complexity.

---

## 2. Architecture Assessed

`
ENVIRONMENT STATE (r_effective, mu, grade)
         ↓
  fog_safe.environment.EnvironmentState
         ↓
  fog_safe.safety.solve_safe_speed
   (v_safe = min(v_stop, v_retarder, v_traction, v_curve, v_mine))
         ↓
  LocalVehicleSafetyGovernor (v_applied <= v_safe, I1-I12)
         ↓
  VEHICLE ACTUATOR / COMMAND
`

Telemetry enters via:
`
ESP32 LoRa V2V / Wi-Fi / Serial Gateway
         ↓
telemetry_ingest.py (NormalizedTelemetry)
         ↓
TelemetryQualityFilter
         ↓
TwinStateStore
`

---

## 3. Key Findings

### 3.1 What already exists

| Capability | Module | Assessment |
|---|---|---|
| Freshness / staleness detection | TelemetryQualityFilter (LIVE/DELAYED/STALE/OFFLINE) | EXISTS — vehicle telemetry only |
| NaN / Inf / negative value rejection | LocalVehicleSafetyGovernor.update_local_safety_state() | EXISTS — for v_safe only |
| Invalid friction fail-closed | fog_safe.safety.solve_safe_speed (mu <= 0 → v_safe = 0) | EXISTS |
| Invalid curve_radius fail-closed | fog_safe.safety D002 three-way branch | EXISTS |
| Communication failure handling | fail_safe_controller (DEGRADED_COMMUNICATION, NO_GATEWAY) | EXISTS |

### 3.2 What is MISSING

| Gap | Impact | Current Behavior |
|---|---|---|
| **Environmental data freshness** — visibility_m / r_effective has no freshness timestamp in the safety solver | Stale visibility feeds solver silently | SILENT STALE STATE |
| **Environmental plausibility** — no range check on visibility_m upstream of r_effective | Negative/extreme values possible | UNGUARDED |
| **Cross-source disagreement** — no mechanism to detect two conflicting visibility sources | Conflicting-source failure class undetectable | UNDETECTABLE |
| **Stuck-at detection** — no rate-of-change check on visibility | Stuck sensor indistinguishable from stable conditions | UNDETECTABLE |
| **Spatial representativeness** — single mine-wide visibility value for all road segments | Zone B (8m) vs Zone A (50m) — system uses single value | SAFETY RISK |
| **Plausible-but-wrong** — sensor reports 50m while actual is 5m | Cannot detect without independent source | EXPLICIT LIMITATION |

### 3.3 Safety Impact

Critical coupling:
`
visibility_m → r_effective → v_stop calculation → v_safe → v_applied
`
A stale or wrong r_effective DIRECTLY affects v_safe computation.
TelemetryQualityFilter guards vehicle telemetry (RPM, speed, IMU).
It does NOT guard environmental inputs (visibility, friction, grade).
This is the principal demonstrated safety gap.

---

## 4. Prior Art Assessment

| Finding | Evidence Level |
|---|---|
| Sensor degradation in mining HEMM is common practice for vehicle sensors | L5 (research literature) |
| Visibility sensor fault detection in mines is a known research area | L5 (peer-reviewed) |
| Uncertainty-aware haulage orchestration is a partial research gap | L5/L8 |
| Single-point visibility for zone-differentiated haul roads is a documented limitation | L5 (spatial meteorology) |
| NMDC uses mine weather stations but zone-level visibility is not documented | L2 (NMDC ICCC docs) |

---

## 5. Standards Scope

| Standard | Applicable Scope |
|---|---|
| ISO 17757 (ASAMS) | Requires perception system integrity. NOT mandatory for FMS orchestration. |
| IEC 61508 | lambda_DU concept relevant to Class C (plausible-but-wrong). Guidance, not mandate. |
| SAE J1939 | Vehicle ECU CAN. Environmental visibility NOT transmitted via J1939 from BH100. |
| ISO 19014 | Performance-based. Does not specify sensor quality checking. |

---

## 6. Implementation Decision

**DECISION: C — IMPLEMENT CONFIDENCE-AWARE SAFETY STATE**

Rationale:
1. The gap is specific: environmental input freshness and plausibility are unguarded.
2. The fix is minimal: one EnvironmentalDataHealth module (~200 LOC) upstream of EnvironmentState.
3. Safety authority chain is preserved: health layer modifies r_effective conservatively; never commands actuators.
4. Plausible-but-wrong is explicitly marked LIMITATION.
5. Full sensor fusion NOT justified: no redundant visibility sensors exist on the prototype.
6. Rule-based approach is sufficient: explainable, auditable, reproducible.

---

## 7. Minimum Architecture Proposed

`
INPUT TELEMETRY
      ↓
DATA HEALTH (NEW — EnvironmentalDataHealth)
  * freshness_timeout (visibility_m, r_effective)
  * range_check (0 < visibility_m <= 2000 m)
  * stuck_at_detection (delta_vis/delta_t < threshold for T seconds)
  * confidence state: HEALTHY / DEGRADED / STALE / UNAVAILABLE
      ↓
ENVIRONMENTAL STATE (r_effective — conservatively set on DEGRADED/STALE)
      ↓
PHYSICS MODEL (solve_safe_speed)
      ↓
LOCAL SAFETY GOVERNOR (final authority, unchanged)
      ↓
SAFE SPEED / COMMAND
`

Data State, Communication State, and Safety State remain SEPARATE enums.

---

## 8. Final Answer

"Does adding sensor/data degradation handling materially improve
FOG-ORCHESTRATOR's safety robustness enough to justify its added complexity?"

**YES (PARTIAL)**

- YES for environmental data freshness and plausibility — demonstrated gap, minimal fix.
- PARTIAL for cross-source disagreement — detectable only if a second source exists.
- NO for plausible-but-wrong class — cannot be solved without hardware not on this prototype.
- NO for full sensor fusion — no data to fuse; unjustified complexity.

Added complexity: ~1 module (~200 LOC), 1 enum, 1 YAML config block.
Safety improvement: closes 2 of 5 environmental-data failure paths.
Remaining limitations: documented in Report 12.
