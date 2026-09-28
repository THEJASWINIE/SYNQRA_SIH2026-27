# 09 — SENSOR-DEGRADATION INTELLIGENCE INTEGRATION REPORT
## FOG-ORCHESTRATOR 2.0 | SIH 2026-27 (Problem Statement: SIH26007)
### NMDC Bailadila Deposit-5 Low-Visibility HEMM Safety System
**Phase 9: Hardware + Software Integration**
**Date:** September 2026 | **Classification:** LEVEL 3 / LEVEL 4 (Software & HIL Validated)

---

## 1. INTEGRATION ARCHITECTURE & DATA FLOW

The newly integrated Sensor Data Health layer operates as a non-invasive filter interposed between raw physical/emulated sensors and the Local Safety Governor:

```
[ EXISTING PHYSICAL SENSORS ]
  ├── Optical Transmissometer (Visibility)
  ├── Dual Wheel Speed Sensors (Longitudinal Velocity)
  ├── 6-DOF MPU6050 IMU (Accelerations & Angular Rates)
  └── Haul Road DTM / Inclinometer (Grade Profile)
                 │
                 ▼
[ RAW SENSOR MEASUREMENTS ]
                 │
                 ▼
[ SENSOR DATA HEALTH LAYER (IF-11) ]
  ├── Rule H1: Freshness & Staleness Tracking (30s degraded, 60s stale, 120s grace)
  ├── Rule H2: Schema, Non-Numeric, NaN/Inf Protection
  ├── Rule H3: Physical Range / Plausibility Clamping ([0.5, 2000] m)
  ├── Rule H4: Monotonic Sequence & Duplicate/Rollback Tracking
  ├── Rule H5: Rolling Window Stuck-At & Noise Dispersion Detection
  └── Rule H6: Dual-Source Analytical Conflict Cross-Check
                 │
                 ▼
[ STANDARDIZED SENSOR HEALTH RECORD ]
  { sensor_id, timestamp, value, quality, confidence, fault_code, last_valid_ts }
                 │
                 ▼
[ LOCAL VEHICLE SAFETY GOVERNOR ]
  (Adjusts effective visibility R_eff & scales speed ceiling conservatively)
```

---

## 2. STANDARDIZED SENSOR QUALITY ENUMERATION & CONTRACT

In compliance with Phase 9 Contract **IF-11**, every sensor signal produces a structured `SensorHealthRecord` classifying data quality into exactly one of eight canonical states:

| Quality State | Criteria / Triggering Fault Condition | Default Confidence | Safety Action |
| :--- | :--- | :--- | :--- |
| **VALID** | Fresh observation within plausibility bounds, sequence strictly increasing | $1.00$ | Full operational safe speed permitted |
| **DEGRADED** | Age $>30\text{ s}$, or mild noise variance, or single sequence gap | $0.70$ | Apply $30\%$ safety penalty to effective sightline |
| **STALE** | Age $>60\text{ s}$ without fresh sample | $0.40$ | Apply $50\%$ safety penalty; clamp to local crawl |
| **MISSING** | Age $>120\text{ s}$ (grace period exceeded) or null/missing input | $0.00$ | Fail closed: assign conservative $R_{\text{eff}} = 8.0\text{ m}$ ($3.52\text{ m/s}$) |
| **STUCK** | Constant reading ($\sigma < 0.05\text{ m}$) sustained over $>300\text{ s}$ | $0.60$ | Flag sensor stuck; apply $30\%$ speed penalty |
| **OUTLIER** | Physical range violation ($<0.5\text{m}$ or $>2000\text{m}$), or non-finite `NaN/Inf` | $0.00$ | Reject sample immediately; hold previous valid envelope |
| **INCONSISTENT** | Dual redundant transmissometers disagree beyond $25\text{ m}$ margin | $0.50$ | Fails closed: select conservative minimum $\min(R_1, R_2)$ |
| **UNKNOWN** | Unhandled internal exception or uncalibrated startup state | $0.00$ | Default to blindout conservative halt ($v_{\text{safe}} = 0.0\text{ m/s}$) |

---

## 3. OBSERVABILITY LIMITATIONS & HONESTY DISCLOSURE

In accordance with Section 5 of the Master Prompt:
1. **Stuck-at Faults:** Observable **only after persistence** across the 300-second window ($10$ consecutive identical samples). Instantaneous stuck detection is mathematically unobservable.
2. **Systematic Bias:** Constant additive calibration errors (e.g. $+15\text{ m}$ offset on a $10\text{ m}$ fog sightline) are **FUNDAMENTALLY UNOBSERVABLE** with a single sensor without an independent optical LiDAR reference.
3. **Internally Consistent False Data:** Adversarial or corrupted data that mimics valid physical dynamics cannot be detected by rule-based heuristic checks without cross-source analytical redundancy.
4. **Transparent Documentation:** The system logs active fault codes (`ERR_STUCK`, `ERR_TIMEOUT`, `ERR_RANGE`, `CROSS_SOURCE_CONFLICT`) and exposes confidence scores directly to the Operator HMI.

---

## 4. TEST SUITE VERIFICATION

- Tested via `tests/test_environmental_data_health.py` (17 tests), `tests/test_data_health_to_safety_chain.py` (21 tests), and `tests/test_phase9_hardware_software_integration.py` (HIL tests 04, 05, 06).
- **Results:** **38 passed, 0 failed in 1.77s**.
- **Fail-Closed Verification:** 100% of injected corrupted, non-finite, missing, or stuck signals triggered conservative safe speed reduction. Zero safety violations occurred.
