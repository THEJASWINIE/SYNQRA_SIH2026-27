# 05 — SENSOR HEALTH INTEGRATION REPORT
## FOG-ORCHESTRATOR 2.0 | SIH 2026-27 (Problem Statement: SIH26007)
### NMDC Bailadila Low-Visibility HEMM Safety & Operational Intelligence System
**Document ID:** `05_SENSOR_HEALTH_INTEGRATION_REPORT.md`  
**Phase:** 9 — Full Hardware + Software + HMI + Control Room + Digital Twin Integration  
**Date:** September 2026 | **Classification:** LEVEL 3 / LEVEL 4 (Software & HIL Validated)  
**Status:** COMPLETE & FROZEN  

---

## 1. Executive Summary & Integration Architecture

The Sensor Health layer operates as a non-invasive, fail-closed filter interposed between physical sensor acquisition and the Tier-1 Local Safety Governor, human-machine interfaces, and Digital Twin.

```
[ PHYSICAL SENSORS: Transmissometer, MPU6050 IMU, Wheel Hall Sensors, GNSS ]
                                │
                                ▼
[ SENSOR DATA HEALTH LAYER (integration_adapters/environmental_data_health.py) ]
  ├── Rule H1: Freshness & Staleness Tracking (30s degraded, 60s stale, 120s missing)
  ├── Rule H2: Schema, Non-Numeric, NaN/Inf Protection
  ├── Rule H3: Physical Range / Plausibility Clamping ([0.5, 2000] m)
  ├── Rule H4: Monotonic Sequence & Duplicate/Rollback Tracking
  ├── Rule H5: Rolling Window Stuck-At & Noise Dispersion Detection
  └── Rule H6: Dual-Source Analytical Conflict Cross-Check
                                │
                                ▼
                     [ SENSOR HEALTH RECORD ]
    { sensor_id, timestamp, value, quality, confidence, fault_code }
                                │
        +-----------------------+-----------------------+
        |                       |                       |
        v                       v                       v
[ OPERATOR HMI ]       [ CONTROL ROOM HMI ]     [ DIGITAL TWIN ]
"SENSOR: DEGRADED"    "Sensor Quality: DEGRADED" "State: UNCERTAIN/DEGRADED"
"Action: REDUCE SPEED" "Alert: HIGH - Degraded"  (Uncertainty NOT hidden)
        │                       │                       │
        +-----------------------+-----------------------+
                                │
                                ▼
                   [ LOCAL SAFETY GOVERNOR ]
    (Applies safety penalty, clamps v_safe to conservative floor)
```

---

## 2. 8-State Sensor Quality Enumeration & Actions

In compliance with Phase 9 Contract **IF-11**, every incoming sensor observation is classified into exactly one of eight canonical states:

| Quality State | Criteria / Triggering Fault Condition | Confidence | Safety Action | Digital Twin Representation |
|:---|:---|:---:|:---|:---|
| **VALID** | Fresh observation within physical limits; sequence monotonic | $1.00$ | Full operational safe speed envelope | Clear state mirror with high confidence |
| **DEGRADED** | Age $>30\text{ s}$, or mild noise variance, or single sequence gap | $0.70$ | Apply $30\%$ safety penalty to effective sightline | Displayed as `UNCERTAIN (0.70)` |
| **STALE** | Age $>60\text{ s}$ without fresh sample | $0.40$ | Apply $50\%$ safety penalty; clamp to local crawl | Displayed as `STALE (0.40)` |
| **MISSING** | Age $>120\text{ s}$ (grace period exceeded) or null/missing input | $0.00$ | Fail closed: assign conservative $R_{\text{eff}} = 8.0\text{ m}$ ($3.52\text{ m/s}$) | Marked as `SENSOR MISSING / DEGRADED FLOOR` |
| **STUCK** | Constant reading ($\sigma < 0.05\text{ m}$) sustained over $>300\text{ s}$ | $0.60$ | Flag sensor stuck; apply $30\%$ speed penalty | Marked as `SENSOR STUCK / UNCERTAIN` |
| **OUTLIER** | Physical range violation ($<0.5\text{m}$ or $>2000\text{m}$), or non-finite `NaN/Inf` | $0.00$ | Reject sample immediately; hold previous valid envelope | Outlier rejected; previous valid envelope held |
| **INCONSISTENT**| Dual redundant transmissometers disagree beyond $25\text{ m}$ margin | $0.50$ | Fails closed: select conservative minimum $\min(R_1, R_2)$ | Marked as `DISCORDANT SENSORS / UNCERTAIN` |
| **UNKNOWN** | Unhandled internal exception or uncalibrated startup state | $0.00$ | Default to blindout conservative halt ($v_{\text{safe}} = 0.0\text{ m/s}$) | Displayed as `UNKNOWN SENSOR STATE` |

---

## 3. Propagation Across Subsystems

### A. Operator HMI (Driver Screen)
- Displays: `Sensor: DEGRADED` in yellow/amber banner.
- Action: Suggests `REDUCE SPEED — SENSOR DEGRADED`.
- Never displays false all-clear when sensors are noisy or stuck.

### B. Control Room HMI
- Alerts: Generates `HIGH: Sensor health degraded` event.
- Fleet Card: Displays `Sensors: DEGRADED (0.70)` with active fault code.

### C. Digital Twin
- **Crucial Rule:** The Digital Twin **MUST NOT** hide sensor uncertainty by synthesizing a fake clean value.
- If real sensors are degraded, the Twin explicitly reflects `UNCERTAIN / DEGRADED` in its state store and visual overlay.

### D. Local Safety Governor
- Applies conservative penalty factor:
  $$R_{\text{effective}} = R_{\text{measured}} \times \text{confidence}$$
- Clamps $v_{\text{safe}}$ according to $R_{\text{effective}}$, guaranteeing stopping distance $S_{\text{stop}} \le R_{\text{effective}} - S_{\text{margin}}$.

---

## 4. Observability Boundaries & Honest Disclosures

1. **Stuck-at Fault Observability:** A stuck-at condition is mathematically indistinguishable from steady atmospheric fog during short observation windows ($<300\text{ s}$). The system detects stuck-at faults only after persistence across $>300\text{ s}$ with variance $\sigma < 0.05\text{ m}$.
2. **Systematic Calibration Bias:** Without an independent LiDAR or second reference sensor, single-sensor additive bias cannot be detected if readings stay within valid range ($[0.5, 2000]\text{ m}$).
