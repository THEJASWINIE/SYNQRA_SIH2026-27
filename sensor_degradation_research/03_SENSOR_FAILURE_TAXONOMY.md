# 03 — SENSOR FAILURE TAXONOMY
## FOG-ORCHESTRATOR 2.0 — Rigorous Failure Classification
**Date:** 2026-09-21  
**Scope:** All 16 failure classes analyzed for environmental and vehicle data inputs.

---

## Failure Class Separation (Prompt Section 5)

Three fundamentally distinct failure classes:

| Class | Description | Example | Detectable? |
|---|---|---|---|
| A | DATA UNAVAILABLE | Visibility sensor stops transmitting | YES — staleness timeout |
| B | DATA INVALID / IMPLAUSIBLE | visibility_m = -20 m | YES — range check |
| C | DATA AVAILABLE BUT WRONG | Sensor reports 50 m; actual 5 m | NO without independent source |

Class C is the hardest and is an **EXPLICIT LIMITATION** of this architecture.

---

## Failure Matrix — All 16 Classes

### F01 — SENSOR DROPOUT
- **Description:** Sensor stops transmitting entirely.
- **Detection Mechanism:** Freshness timeout on received timestamp. Absence of updates for T_stale seconds.
- **Detection Latency:** T_stale (configurable; proposed: 10 s for visibility, 3 s for vehicle speed)
- **False Positive Risk:** LOW — unambiguous absence of signal
- **False Negative Risk:** LOW
- **Required Fallback:** Class A → USE LAST KNOWN for T_grace, then STALE → UNAVAILABLE
- **Affects v_safe:** YES — if visibility dropout, r_effective becomes stale
- **Affects Road Capacity:** YES — conservative assumption required
- **Affects Fleet Orchestration:** YES — slow / stage affected trucks
- **Current Architecture Handles:** PARTIALLY — TelemetryQualityFilter handles vehicle dropout; environmental dropout NOT handled

### F02 — STALE DATA
- **Description:** Data continues to be sent but measurement is temporally outdated.
- **Detection Mechanism:** Timestamp comparison vs. current time; age_s > threshold
- **Detection Latency:** One polling cycle after threshold crossed
- **False Positive Risk:** MEDIUM — clock skew, transmission delay could cause false stale
- **False Negative Risk:** LOW if timestamps are accurate
- **Required Fallback:** DEGRADED → conservative r_effective fallback
- **Affects v_safe:** YES directly via r_effective
- **Current Architecture Handles:** PARTIALLY — vehicle speed staleness detected; visibility staleness NOT detected

### F03 — COMMUNICATION LOSS
- **Description:** Transport layer fails; no packets received.
- **Detection Mechanism:** FailSafeState.NO_GATEWAY, LoRa RSSI monitoring, WebSocket disconnect detection
- **Detection Latency:** max_command_age_s = 1.0 s (current config)
- **False Positive Risk:** LOW
- **False Negative Risk:** LOW
- **Required Fallback:** Local safety governor operates independently (invariant I3)
- **Affects v_safe:** NO directly — local governor continues with last valid v_safe
- **Current Architecture Handles:** YES — fully handled (I3, DEGRADED_COMMUNICATION, NO_GATEWAY states)

### F04 — OUT-OF-RANGE VALUE
- **Description:** Reported value outside physically possible range.
- **Detection Mechanism:** Range check: 0 < visibility_m <= V_MAX; -1 < mu <= 1.0; -90 < grade < 90
- **Detection Latency:** Immediate (synchronous check on ingestion)
- **False Positive Risk:** LOW — physical limits are well-defined
- **False Negative Risk:** LOW
- **Required Fallback:** Class B → REJECT value; use conservative default or UNAVAILABLE
- **Affects v_safe:** YES — invalid mu or r_effective would propagate to solver without this check
- **Current Architecture Handles:** PARTIALLY — mu <= 0 is caught by safety solver; visibility range NOT checked upstream

### F05 — STUCK-AT VALUE
- **Description:** Sensor continuously reports identical value despite changing physical conditions.
- **Detection Mechanism:** Rate-of-change check over sliding window: |Δvalue/Δt| < ε for N consecutive samples
- **Detection Latency:** N * sampling_interval (must be tuned; ~60 s for visibility)
- **False Positive Risk:** MEDIUM — in truly stable fog, visibility can genuinely be constant
- **False Negative Risk:** MEDIUM — threshold tuning is critical; if ε too large, stuck detection fails
- **Required Fallback:** DEGRADED → conservative fallback after detection
- **Affects v_safe:** YES — if visibility stuck HIGH while actual drops LOW, v_safe is over-estimated
- **Current Architecture Handles:** NO — no stuck-at detection for any environmental input

### F06 — BIAS / OFFSET
- **Description:** Sensor systematically reads different from true value by a constant offset.
- **Detection Mechanism:** Cross-source comparison; calibration record; trend analysis
- **Detection Latency:** Extended — requires comparison over time or independent source
- **False Positive Risk:** HIGH without independent reference
- **False Negative Risk:** HIGH — indistinguishable from true measurement without ground truth
- **Required Fallback:** Mark CONFIDENCE_LOW; apply conservative modifier if bias detected
- **Affects v_safe:** YES — systematic offset in visibility directly biases r_effective and v_safe
- **Current Architecture Handles:** NO — no bias detection in any module

### F07 — DRIFT
- **Description:** Sensor reading slowly diverges from true value over time.
- **Detection Mechanism:** Long-term trend analysis; calibration comparison; cross-source divergence
- **Detection Latency:** Long — hours to days
- **False Positive Risk:** MEDIUM — environmental drift could be real
- **False Negative Risk:** HIGH — slow drift may pass all short-window checks
- **Required Fallback:** Requires calibration event or independent validation
- **Affects v_safe:** YES — gradual over-reading of visibility leads to gradual v_safe over-estimate
- **Current Architecture Handles:** NO

### F08 — HIGH NOISE
- **Description:** Sensor output has high-frequency variance without a clear stuck-at or bias pattern.
- **Detection Mechanism:** Standard deviation of rolling window; spike filter (IQR clipping)
- **Detection Latency:** Short — typically 5–10 samples
- **False Positive Risk:** LOW in calm conditions; MEDIUM in turbulent atmospheric conditions
- **False Negative Risk:** LOW
- **Required Fallback:** Smooth or filter; flag as DEGRADED if noise exceeds threshold
- **Affects v_safe:** YES — noisy visibility causes fluctuating r_effective and therefore fluctuating v_safe
- **Current Architecture Handles:** NO

### F09 — INTERMITTENT DATA
- **Description:** Sensor alternates between valid data and silence/invalid data.
- **Detection Mechanism:** Packet loss rate tracking; hysteresis on quality state
- **Detection Latency:** Few packet cycles
- **False Positive Risk:** LOW — packet loss rate is observable
- **False Negative Risk:** LOW
- **Required Fallback:** DEGRADED state; hold last valid with decay; packet_loss > threshold → STALE
- **Affects v_safe:** YES — intermittent visibility causes uncertain r_effective
- **Current Architecture Handles:** PARTIALLY — TelemetryQualityFilter tracks loss rate for vehicle packets; not for environmental data

### F10 — TIMESTAMP ERROR
- **Description:** Packet timestamp is wrong (future, past, or identical to previous packet).
- **Detection Mechanism:** Timestamp validity check: |t_source - t_received| < T_skew_max; monotonicity check
- **Detection Latency:** Immediate
- **False Positive Risk:** LOW
- **False Negative Risk:** LOW if check is implemented
- **Required Fallback:** Use received_at as fallback; flag as DEGRADED
- **Affects v_safe:** YES — incorrect timestamp causes wrong staleness classification
- **Current Architecture Handles:** PARTIALLY — NormalizedTelemetry.measurement_timestamp falls back to received_at; no explicit skew check

### F11 — SEQUENCE ERROR
- **Description:** Out-of-order or duplicate packet sequences.
- **Detection Mechanism:** BoundedSequenceTracker (existing); last_accepted_sequence comparison
- **Detection Latency:** Immediate (per-packet)
- **False Positive Risk:** LOW
- **False Negative Risk:** LOW
- **Required Fallback:** Reject duplicate; drop out-of-order; flag sequence_integrity = OUT_OF_ORDER
- **Affects v_safe:** LOW if latest packet accepted — stale data risk only if out-of-order packet used
- **Current Architecture Handles:** YES — BoundedSequenceTracker fully handles vehicle telemetry

### F12 — DUPLICATE DATA
- **Description:** Identical packets received multiple times (replay or network artifact).
- **Detection Mechanism:** BoundedSequenceTracker (existing)
- **Detection Latency:** Immediate
- **Affects v_safe:** LOW
- **Current Architecture Handles:** YES — for vehicle telemetry

### F13 — CROSS-SENSOR DISAGREEMENT
- **Description:** Two independent sources for the same quantity report significantly different values.
- **Detection Mechanism:** |value_A - value_B| > disagreement_threshold → CONFLICTING state
- **Detection Latency:** One sample period after second source arrives
- **False Positive Risk:** MEDIUM — spatial variation could be real, not a sensor fault
- **False Negative Risk:** MEDIUM — if both sensors are biased in same direction, no disagreement detected
- **Required Fallback:** Use minimum (conservative) of the two; flag CONFLICTING
- **Affects v_safe:** YES — if disagreement on visibility, conservative (lower) value is required
- **Current Architecture Handles:** NO — only one visibility input exists; second source not available in prototype

### F14 — SPATIALLY STALE ENVIRONMENTAL DATA
- **Description:** Measurement valid at point A is used as representative for point B far away.
- **Detection Mechanism:** Zone-association of measurement location vs. vehicle location; requires spatial metadata
- **Detection Latency:** N/A — requires spatial infrastructure
- **Required Fallback:** Apply spatial uncertainty penalty to r_effective for distant segments
- **Affects v_safe:** YES — single mine-wide visibility may be optimistic for zones with dense pockets of fog
- **Current Architecture Handles:** NO — single visibility value applied uniformly

### F15 — PLAUSIBLE BUT WRONG DATA (CLASS C)
- **Description:** Sensor reports a value within plausible range but incorrect (true vis = 5 m; reported = 50 m).
- **Detection Mechanism:** REQUIRES independent source (second sensor, vehicle-mounted range sensor, or V2V cross-comparison)
- **Detection Latency:** UNDEFINED — cannot detect without independent reference
- **False Negative Risk:** VERY HIGH — by definition, the value passes all range and freshness checks
- **Required Fallback:** CANNOT determine appropriate fallback without detecting the failure
- **Affects v_safe:** YES — CRITICALLY. Reported 50 m → v_stop ≈ 8.5 m/s; actual safe speed at 5 m → ~2.7 m/s
- **Current Architecture Handles:** NO — EXPLICIT LIMITATION
- **Mitigation (partial):** Conservative r_effective < visibility_m factor; stuck-at detection as proxy

### F16 — COMPLETE ENVIRONMENTAL DATA UNAVAILABILITY
- **Description:** All environmental data sources (weather stations, FMS) cease to provide data.
- **Detection Mechanism:** Global staleness timeout on all environmental inputs
- **Detection Latency:** T_stale after last valid environmental packet
- **Required Fallback:** UNAVAILABLE → apply minimum safe speed policy (e.g., v_max_unavailable = v_mine_limit / 2)
- **Affects v_safe:** YES — must fall back to conservative minimum
- **Current Architecture Handles:** NO — no defined behavior for environmental data total loss

---

## Summary by Failure Class

| ID | Name | Detected? | Affects v_safe? | Architecture Gap? |
|---|---|---|---|---|
| F01 | Sensor Dropout | PARTIAL | YES | YES (env only) |
| F02 | Stale Data | PARTIAL | YES | YES (env only) |
| F03 | Communication Loss | YES | NO | NO |
| F04 | Out-of-Range Value | PARTIAL | YES | YES (vis upstream) |
| F05 | Stuck-At Value | NO | YES | YES |
| F06 | Bias/Offset | NO | YES | YES |
| F07 | Drift | NO | YES | YES |
| F08 | High Noise | NO | YES | YES |
| F09 | Intermittent Data | PARTIAL | YES | YES (env only) |
| F10 | Timestamp Error | PARTIAL | YES | YES |
| F11 | Sequence Error | YES | LOW | NO |
| F12 | Duplicate Data | YES | LOW | NO |
| F13 | Cross-Sensor Disagreement | NO | YES | YES (no 2nd source) |
| F14 | Spatially Stale Env Data | NO | YES | YES |
| F15 | Plausible But Wrong | NO | CRITICAL | EXPLICIT LIMITATION |
| F16 | Complete Env Unavailability | NO | YES | YES |
