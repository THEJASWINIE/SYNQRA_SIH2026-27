# 13 — IMPLEMENTATION DECISION
## FOG-ORCHESTRATOR 2.0 — Sensor / Data Degradation Final Decision
**Date:** 2026-09-21  
**Status:** DECISION FROZEN

---

## The Decision

**DECISION: C — IMPLEMENT CONFIDENCE-AWARE SAFETY STATE**

---

## Decision Derivation

### Step 1 — Is there a demonstrated safety gap?

YES.

Code-confirmed: visibility_m → r_effective has NO freshness guard, NO range check, and NO
plausibility check in the existing architecture. This is the single critical path through which
stale or invalid environmental data can silently propagate to v_safe.

Quantified risk:
- Stale visibility at 50 m when actual fog is 12 m allows v_safe = 8.52 m/s instead of 2.70 m/s.
- At -8% grade with 165.5-tonne loaded BH100 class vehicle: S_stop at 8.52 m/s >> S_stop at 2.70 m/s.
- Stopping distance at 8.52 m/s ≈ 35 m; actual r_effective ≈ 12 m. ENVELOPE VIOLATED.

This is a demonstrated gap, not a theoretical one.

### Step 2 — Can a minimal fix close the gap without unsafe complexity?

YES — within the detectable failure classes (A and B).

A single EnvironmentalDataHealth module with:
- H1: Freshness timeout (deterministic, T_STALE_ENV = 60 s)
- H2: Range check (0.5 m ≤ vis ≤ 2000 m)
- H3: Stuck-at detection (rolling std_dev, 300 s window)
- H4: Noise check (rolling std_dev threshold)
- H5: Conflict placeholder (future: 2nd source required)

...closes failure classes F01, F02, F04, F08, F09, F10, F16 definitively.

The module modifies r_effective conservatively. It does NOT touch the safety governor, the
physics solver, or the actuator path. The authority chain is unchanged.

### Step 3 — Does the fix introduce new safety risks?

NO — by design.

The health layer can only REDUCE r_effective (conservative direction) or HOLD last known.
It cannot increase r_effective above the raw sensor reading.
It cannot issue any command to any vehicle.
If the health module itself fails (crashes), the correct fallback is: use last known r_effective
with UNAVAILABLE state → apply R_UNAVAILABLE_MIN. The module fails conservatively.

### Step 4 — Is full sensor fusion needed?

NO.

Full sensor fusion (Option D) requires:
- Multiple sensor modalities (LiDAR, radar, cameras) — NOT present on BH100 or prototype
- Statistical fusion model — requires training data that does not exist
- Kalman filter — requires process model parameters that are not measured
- ML model — requires training dataset that does not exist

Attempting Option D without the required inputs would produce an opaque, unverifiable system.
This would REDUCE safety, not improve it.

### Step 5 — What remains unresolved after implementing Option C?

| Unresolved | Classification |
|---|---|
| Class C (plausible-but-wrong) | EXPLICIT LIMITATION — requires 2nd source |
| Stuck-at detection latency (300 s) | TUNEABLE TRADE-OFF |
| Zone-level spatial visibility | FUTURE INTEGRATION REQUIREMENT |
| Bias / drift detection | DEPLOYMENT REQUIREMENT — needs calibration infrastructure |

These are honestly documented in Report 12. They are not concealed.

---

## Minimum Implementation Specification

### New Module: integration_adapters/environmental_data_health.py

`
Class: EnvironmentalDataHealth
  Inputs:
    - visibility_m: float (raw measurement)
    - timestamp: float (measurement time, epoch s)
    - config: EnvironmentalHealthConfig (from YAML)
  Internal State:
    - _last_valid_vis_m: float
    - _last_valid_ts: float
    - _rolling_window: deque[float] (for H3, H4)
    - _data_state: DataState
  Outputs:
    - get_r_effective() -> Tuple[float, DataState]
    - get_data_state() -> DataState
    - get_audit_fields() -> dict (for TwinState)
  
Enum: DataState
  HEALTHY, DEGRADED, STALE, CONFLICTING, UNAVAILABLE

Config: EnvironmentalHealthConfig
  T_DEGRADED_ENV_s: float = 30.0
  T_STALE_ENV_s: float = 60.0
  T_GRACE_PERIOD_s: float = 120.0
  T_STUCK_MIN_s: float = 300.0
  STUCK_THRESHOLD: float = 0.1
  NOISE_THRESHOLD_m: float = 15.0
  CONFLICT_THRESHOLD_m: float = 15.0
  V_MAX_PLAUSIBLE_m: float = 2000.0
  V_MIN_PLAUSIBLE_m: float = 0.5
  DEGRADED_FACTOR: float = 0.7
  STALE_FACTOR: float = 0.5
  R_MIN_m: float = 5.0
  R_UNAVAILABLE_MIN_m: float = 8.0
`

### Modified Integration Points

1. og_orchestrator/ or wherever EnvironmentState is constructed:
   Insert health check BEFORE constructing EnvironmentState.
   Pass r_effective from health module to EnvironmentState.

2. TwinStateStore:
   Add fields: environmental_data_state, visibility_raw_m, r_effective_applied_m, visibility_freshness_s.

3. HMI backend:
   Expose environmental_data_state in API response.

4. config/:
   Add ENVIRONMENTAL_HEALTH_CONFIG block to existing config YAML.

### New Test Module: tests/test_environmental_data_health.py

Required test cases:
- test_healthy_fresh_data
- test_degraded_on_timeout_T_DEGRADED
- test_stale_on_timeout_T_STALE
- test_unavailable_post_grace
- test_range_check_negative
- test_range_check_over_max
- test_stuck_at_detection
- test_noise_detection
- test_recovery_from_stale_to_healthy
- test_r_effective_conservative_on_degraded
- test_r_effective_unavailable_min
- test_health_module_fail_closed
- test_data_state_separation_from_comm_state
- test_data_state_separation_from_safety_state

### New Experiment: experiments/run_sensor_degradation_benchmark.py

Implements D0–D12 scenarios from Report 08.
Produces: data/sensor_degradation_results.csv (schema from Report 09).

---

## Verification Plan

### Automated
1. pytest tests/test_environmental_data_health.py — must pass 100%
2. pytest -q — full regression must maintain ≥ 1009 passed, 0 failed
3. python experiments/run_sensor_degradation_benchmark.py — D0–D12 × 20 seeds

### Manual Verification
1. Inspect sensor_degradation_results.csv: unsafe_commands = 0 for D0–D6, D8–D12
2. Confirm D7 (bias): unsafe_commands > 0 expected — DOCUMENT AS LIMITATION
3. Confirm D5 (stale): data_state_stale_pct increases as expected
4. Confirm D12 (full loss): throughput drops, safety invariant holds

### Freeze Criteria
- PASS: unsafe_commands = 0 for all detectable scenarios
- PASS: D7 documented as undetectable limitation (not a test failure)
- PASS: Full regression suite maintained
- FAIL: Any scenario (other than D7) shows unsafe_commands > 0

---

## Final Statement

**"Does adding sensor/data degradation handling materially improve  
FOG-ORCHESTRATOR's safety robustness enough to justify its added complexity?"**

**YES (PARTIAL)**

- The environmental data freshness and plausibility gap is real, demonstrated by code inspection
  and quantified through the canonical physics model.
- The proposed fix is minimal: ~200 LOC, one new enum, one config block.
- The fix closes 7 of 16 identified failure classes for environmental data.
- 4 failure classes remain as explicit, documented limitations.
- Full sensor fusion is not justified and would reduce safety by adding unverifiable complexity.
- Implementation should proceed as Option C: Confidence-Aware Safety State.

**PROCEED TO IMPLEMENTATION.**
