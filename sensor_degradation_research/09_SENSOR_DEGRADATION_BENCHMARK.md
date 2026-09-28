# 09 — SENSOR DEGRADATION BENCHMARK (DESIGN)
## FOG-ORCHESTRATOR 2.0 — Benchmark Protocol and Expected CSV Schema
**Date:** 2026-09-21  
**Status:** DESIGN. Benchmark execution follows after implementation decision approval.

---

## 1. Benchmark Identity

**Name:** FOG-ORCHESTRATOR Sensor Degradation Benchmark  
**Version:** SD-1.0  
**Seeds:** 20 matched seeds (identical to canonical Phase 7 / FINAL benchmark)  
**Simulation Duration:** 7200 s per seed  
**Trucks:** 6  
**Grade:** -8% (descent, worst case)  
**Base Visibility:** 12 m (Dense Fog scenario — canonical L2)  
**Scenarios:** D0 (baseline) + D1–D12 (degradation) = 13 scenarios × 20 seeds = 260 runs

---

## 2. CSV Schema (sensor_degradation_results.csv)

Each row = one simulation run.

| Column | Type | Description |
|---|---|---|
| scenario_id | str | D0, D1, D2, ..., D12 |
| degradation_type | str | NONE / DROPOUT_10 / DROPOUT_25 / STALE / STUCK_AT / BIAS / NOISE / CONFLICT / INTERMITTENT / COMM_LOSS / FULL_LOSS |
| seed | int | Random seed (0–19, matched to canonical) |
| duration_s | float | Simulation duration in seconds |
| n_trucks | int | 6 |
| base_visibility_m | float | 12.0 |
| grade_pct | float | -8.0 |
| unsafe_commands | int | COUNT of v_command > v_safe (PRIMARY SAFETY METRIC) |
| envelope_violations | int | COUNT of S_stop + S_base > R_effective |
| detection_latency_s | float | Time from injection to correct data_state activation |
| fallback_latency_s | float | Time from STALE/UNAVAILABLE to r_effective reduction |
| false_alarms | int | DEGRADED state when data was actually HEALTHY |
| missed_degradation | int | HEALTHY state when data was actually degraded |
| completed_dumps | int | Total completed loading/dumping cycles |
| throughput_t | float | Modelled delivered haulage throughput (tonnes) |
| ramp_waiting_s | float | Total ramp waiting time across all trucks (s) |
| staging_waiting_s | float | Total staging waiting time (s) |
| total_waiting_s | float | Total delay time (s) |
| bottleneck_duration_s | float | Duration of bottleneck condition (s) |
| recovery_time_s | float | Time to restore HEALTHY after degradation resolves (s) |
| data_state_healthy_pct | float | % of simulation time data_state=HEALTHY |
| data_state_degraded_pct | float | % of simulation time data_state=DEGRADED |
| data_state_stale_pct | float | % of simulation time data_state=STALE |
| data_state_unavailable_pct | float | % of simulation time data_state=UNAVAILABLE |
| r_effective_mean_m | float | Mean r_effective applied during run |
| r_effective_min_m | float | Minimum r_effective applied |
| v_safe_mean_ms | float | Mean safe speed |
| evidence_level | str | SIMULATION |
| reproducibility_seed | int | Same as seed for verification |

---

## 3. Success Criteria

| Criterion | Threshold | Measurement |
|---|---|---|
| SC1 — Safety invariant | unsafe_commands = 0 for ALL D-scenarios | Per run; aggregate |
| SC2 — Stale data detection | detection_latency_s ≤ T_STALE_ENV + 1 cycle | D5, D10 |
| SC3 — Degraded state triggers conservative behaviour | r_effective_mean < base in DEGRADED/STALE runs | D2–D5 |
| SC4 — Communication loss preserves local safety | unsafe_commands = 0 during D11 comm loss window | D11 |
| SC5 — Sensor disagreement uses conservative value | r_effective = min(A,B) in D9 | D9 |
| SC6 — No unexplained throughput artifact | throughput_D0_health ≈ throughput_D0_baseline (±2%) | D0 vs baseline |
| SC7 — Added complexity is small | EnvironmentalDataHealth LOC ≤ 250 | Code review |
| SC8 — Reproducibility | Same seed produces identical results across runs | Verification |
| SC9 — Plausible-but-wrong is marked LIMITATION | D7 bias scenario documented as NOT DETECTABLE | D7 report |

---

## 4. Benchmark Reproducibility Configuration

`yaml
# sensor_degradation_benchmark_config.yaml
benchmark:
  name: "Sensor Degradation Benchmark SD-1.0"
  version: "1.0.0"
  seeds: [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19]
  duration_s: 7200
  n_trucks: 6
  grade_pct: -8.0
  base_visibility_m: 12.0
  
scenarios:
  D0: {type: "NONE", params: {}}
  D1: {type: "DROPOUT", params: {rate: 0.10}}
  D2: {type: "DROPOUT", params: {rate: 0.25}}
  D3: {type: "DROPOUT", params: {rate: 0.50}}
  D4: {type: "DROPOUT", params: {rate: 0.75}}
  D5: {type: "STALE", params: {start_s: 1800, duration_s: 3600}}
  D6: {type: "STUCK_AT", params: {start_s: 1800, duration_s: 3600, true_vis_final_m: 5.0}}
  D7: {type: "BIAS", params: {offset_m: 15.0, true_vis_m: 12.0}}
  D8: {type: "NOISE", params: {std_m: 10.0}}
  D9: {type: "CONFLICT", params: {source_B_vis_m: 8.0}}
  D10: {type: "INTERMITTENT", params: {valid_s: 10, absent_s: 10}}
  D11: {type: "COMM_LOSS", params: {start_s: 3600, duration_s: 600}}
  D12: {type: "FULL_LOSS", params: {start_s: 1800}}

health_config:
  T_DEGRADED_ENV_s: 30
  T_STALE_ENV_s: 60
  T_GRACE_PERIOD_s: 120
  T_STUCK_MIN_s: 300
  STUCK_THRESHOLD: 0.1
  NOISE_THRESHOLD_m: 15.0
  CONFLICT_THRESHOLD_m: 15.0
  V_MAX_PLAUSIBLE_m: 2000.0
  V_MIN_PLAUSIBLE_m: 0.5
  DEGRADED_FACTOR: 0.7
  STALE_FACTOR: 0.5
  R_MIN_m: 5.0
  R_UNAVAILABLE_MIN_m: 8.0
`

---

## 5. Evidence Classification

All benchmark results will be classified:

| Evidence Type | Label |
|---|---|
| Simulation with health layer active | SIMULATION — health layer modeled |
| Canonical benchmark (no health layer) | SIMULATION — canonical Phase 7 |
| Physical BH100 validation | NOT PERFORMED — DEPLOYMENT REQUIREMENT |

Never claim physical mine validation from these results.
