# 04 — DATA HEALTH ARCHITECTURE
## FOG-ORCHESTRATOR 2.0 — Minimum Data Health Layer Design
**Date:** 2026-09-21  
**Decision:** C — Confidence-Aware Safety State  
**Status:** PRE-IMPLEMENTATION DESIGN. No code written.

---

## 1. Design Principles

1. The health layer MODIFIES environmental state conservatively.  
2. It NEVER commands actuators directly.  
3. It NEVER overrides the local safety governor.  
4. It produces a DATA STATE enum: HEALTHY / DEGRADED / STALE / CONFLICTING / UNAVAILABLE.  
5. DATA STATE, COMMUNICATION STATE, and VEHICLE SAFETY STATE remain separate.  
6. Implementation is rule-based only. No ML.

---

## 2. Architecture Diagram

`
TELEMETRY SOURCES
  └── Mine Weather Station (visibility_m)
  └── FMS Environmental Data (grade, condition)
  └── Vehicle J1939 (speed, RPM, brake — future BH100 integration)
  └── ESP32 Prototype (wheel encoder, IMU, LoRa)
           │
           ▼
    ┌─────────────────────────────────────────┐
    │     EnvironmentalDataHealth (NEW)        │
    │                                          │
    │  For visibility_m:                       │
    │    1. freshness_check(t_now, t_received, T_stale_env)
    │    2. range_check(0 < vis <= 2000 m)     │
    │    3. stuck_at_check(rolling_window)     │
    │    4. noise_check(std_dev rolling)       │
    │    5. conflict_check(if 2nd source)      │
    │                                          │
    │  Outputs:                                │
    │    data_state: HEALTHY/DEGRADED/STALE/   │
    │                CONFLICTING/UNAVAILABLE   │
    │    r_effective_health: float             │
    │      (= visibility_m if HEALTHY)         │
    │      (= conservative_fallback if DEGRADED/STALE)
    │      (= r_unavailable_min if UNAVAILABLE)│
    └─────────────────────────────────────────┘
           │
           ▼
    EnvironmentState(r_effective=r_effective_health, ...)
           │
           ▼
    fog_safe.safety.solve_safe_speed(...)
           │
           ▼
    LocalVehicleSafetyGovernor (UNCHANGED — final authority)
           │
           ▼
    v_applied ≤ v_safe (invariant I1, unchanged)
`

---

## 3. State Enumeration

### DataState (Environmental)
`
HEALTHY     — fresh, in-range, not stuck, passes all checks
DEGRADED    — one check failed (e.g., slightly stale, marginal noise)
              → conservative r_effective penalty applied
STALE       — freshness timeout exceeded (> T_stale_env)
              → use T_grace period at last known value, then r_unavailable
CONFLICTING — two sources disagree beyond threshold
              → use minimum (most conservative) of the two values
UNAVAILABLE — all sources absent or failed all checks
              → use r_unavailable_min (minimum safe assumption)
`

### CommunicationState (Existing — unchanged)
`
NORMAL
DEGRADED_COMMUNICATION
STALE_COMMAND
NO_GATEWAY
INVALID_COMMAND
UNSAFE_COMMAND
`

### VehicleSafetyState (Existing — unchanged)
`
NORMAL
RESTRICTED
STAGED
STOP
EMERGENCY_STOP
RECOVERY
`

These three state enums DO NOT merge.

---

## 4. Health Check Rules

### Rule H1 — Freshness Timeout
`
if (t_now - t_last_vis_received) > T_STALE_ENV:
    data_state = STALE
elif (t_now - t_last_vis_received) > T_DEGRADED_ENV:
    data_state = DEGRADED
`
Parameters (proposed, config-file driven):
- T_DEGRADED_ENV = 30 s (visibility measurement becoming stale)
- T_STALE_ENV = 60 s (visibility measurement fully stale)
- T_GRACE_PERIOD = 120 s (hold last known before UNAVAILABLE)

### Rule H2 — Range Check
`
if visibility_m <= 0 or visibility_m > V_MAX_PLAUSIBLE:
    data_state = DEGRADED (or UNAVAILABLE if repeated)
    reject_value = True
`
Parameters:
- V_MAX_PLAUSIBLE = 2000 m (meteorological maximum for fog context)
- V_MIN_PLAUSIBLE = 0.5 m (below this, sensor/road sensor noise floor)

### Rule H3 — Stuck-At Detection
`
if std_dev(rolling_window_N) < STUCK_THRESHOLD and window_age > T_STUCK_MIN:
    data_state = DEGRADED (potential stuck-at)
`
Parameters:
- N = 10 samples
- STUCK_THRESHOLD = 0.1 m/sample (below this → stuck flag)
- T_STUCK_MIN = 300 s (5 minutes — only flag if stable for 5 min)
Note: TRUE LIMITATION — in genuinely constant fog, this gives false positives.
Action: Flag DEGRADED, not UNAVAILABLE. Operator alert only.

### Rule H4 — Noise Check
`
if std_dev(rolling_window_N) > NOISE_THRESHOLD:
    data_state = DEGRADED
`
Parameters:
- NOISE_THRESHOLD = 15 m (standard deviation over 10 samples)

### Rule H5 — Cross-Source Conflict (Future — requires second source)
`
if |vis_source_A - vis_source_B| > CONFLICT_THRESHOLD:
    data_state = CONFLICTING
    r_effective_health = min(vis_source_A, vis_source_B)
`
Parameters:
- CONFLICT_THRESHOLD = 20 m

**This rule is NOT implementable on the current prototype (no second source).**  
Implementation: placeholder function returns HEALTHY when only one source exists.

---

## 5. Conservative Fallback Policy

| Data State | r_effective Assignment | Justification |
|---|---|---|
| HEALTHY | r_effective = visibility_m | Full trust in measurement |
| DEGRADED | r_effective = max(visibility_m * DEGRADED_FACTOR, R_MIN) | Apply penalty; DEGRADED_FACTOR = 0.7 |
| STALE (grace period) | r_effective = max(last_known * STALE_FACTOR, R_MIN) | Decayed trust; STALE_FACTOR = 0.5 |
| STALE (post-grace) | r_effective = R_UNAVAILABLE_MIN | Full conservative fallback |
| CONFLICTING | r_effective = min(source_A, source_B) | Most conservative available |
| UNAVAILABLE | r_effective = R_UNAVAILABLE_MIN | Minimum safe perception assumption |

Parameters:
- DEGRADED_FACTOR = 0.7 (configurable)
- STALE_FACTOR = 0.5 (configurable)
- R_MIN = 5.0 m (absolute physical floor — below this, v_safe → 0 anyway)
- R_UNAVAILABLE_MIN = 8.0 m (conservative: typical dense fog scenario; use L2 mode speed)

---

## 6. Integration Points

### 6.1 Where the health check inserts
`python
# CURRENT FLOW (no data health):
env = EnvironmentState(r_effective=visibility_m, mu_true=mu_prior)
result = solve_safe_speed(vehicle, road, env, comm, mu_effective)

# PROPOSED FLOW (with data health):
env_health = EnvironmentalDataHealth(config=health_config)
env_health.update(visibility_m=raw_vis_m, timestamp=t_received)
r_eff, data_state = env_health.get_r_effective()

env = EnvironmentState(r_effective=r_eff, mu_true=mu_prior)
result = solve_safe_speed(vehicle, road, env, comm, mu_effective)
# result.v_safe is now health-aware; safety governor unchanged
`

### 6.2 TwinStateStore additions (proposed)
`python
# New fields in vehicle/environment state store:
environmental_data_state: DataState      # HEALTHY/DEGRADED/STALE/...
visibility_freshness_s: float            # age of last visibility measurement
visibility_raw_m: float                  # raw reported value (for audit)
r_effective_applied_m: float             # actual r_effective used in solver
`

### 6.3 HMI additions (proposed)
`
ENVIRONMENTAL DATA: HEALTHY | DEGRADED | STALE | UNAVAILABLE
VISIBILITY SOURCE: STATION_A | DEGRADED | UNAVAILABLE
VISIBILITY (RAW): 12.4 m
VISIBILITY (APPLIED): 8.7 m  [DEGRADED — 30% penalty applied]
`

---

## 7. What the Health Layer Does NOT Do

- It does NOT command actuators.
- It does NOT call solve_safe_speed directly.
- It does NOT create a new v_safe path.
- It does NOT bypass LocalVehicleSafetyGovernor.
- It does NOT use ML, probabilistic fusion, or Kalman filtering.
- It does NOT claim to detect plausible-but-wrong data (Class C).
- It does NOT replace FMS environmental infrastructure.

---

## 8. Comparison of Approaches

| Approach | Explainability | Safety | Complexity | Data Requirements | Hackathon Feasible? |
|---|---|---|---|---|---|
| RULE-BASED (proposed) | HIGH | HIGH (deterministic) | LOW | Single sensor sufficient | YES |
| STATISTICAL ESTIMATION | MEDIUM | MEDIUM | MEDIUM | Multiple samples required | YES |
| KALMAN FILTER | LOW | MEDIUM | HIGH | Requires process model | PARTIAL |
| ML SENSOR FUSION | LOW | LOW (opaque) | VERY HIGH | Training data required | NO |

**Rule-based is the correct choice for this safety-critical, resource-constrained, prototype context.**
