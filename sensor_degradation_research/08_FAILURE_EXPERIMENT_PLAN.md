# 08 — FAILURE EXPERIMENT PLAN
## FOG-ORCHESTRATOR 2.0 — Controlled Sensor Degradation Experiment Design
**Date:** 2026-09-21  
**Scope:** Experiment design only. Does not replace canonical benchmark. No code written yet.

---

## 1. Experiment Structure

All experiments extend the existing canonical benchmark (20 matched seeds, 7200 s, 6 trucks).
Everything else is identical to the canonical benchmark.
The independent variable is the sensor/data degradation type injected into visibility_m.

Primary safety metric (non-negotiable): unsafe commands (v_command > v_safe) = 0.

---

## 2. Baseline

**D0 — Normal Data**
- visibility_m = canonical scenario value (12 m, dense fog)
- No degradation injected
- Result: canonical throughput, safety invariant holds 100%
- Purpose: Comparison baseline for all D-scenarios

---

## 3. Degradation Scenarios

### D1 — 10% Packet Dropout
- **Injection:** 10% of visibility measurement packets dropped uniformly at random
- **Expected Data State:** DEGRADED (occasional)
- **Purpose:** Low-level communication noise; verify no false alarms
- **Hysteresis Behaviour:** System should remain HEALTHY for isolated drops, DEGRADED only after N consecutive drops

### D2 — 25% Packet Dropout
- **Injection:** 25% random packet loss on visibility stream
- **Expected Data State:** DEGRADED → periodic STALE events
- **Purpose:** Moderate loss; verify degraded-mode activates, throughput impact is measured

### D3 — 50% Packet Dropout
- **Injection:** 50% random packet loss
- **Expected Data State:** Frequent STALE
- **Purpose:** Stress test; verify safety invariant holds even under heavy degradation

### D4 — 75% Packet Dropout
- **Injection:** 75% random packet loss
- **Expected Data State:** STALE → UNAVAILABLE episodes
- **Purpose:** Near-complete loss; verify UNAVAILABLE fallback activates

### D5 — Stale Environmental Data
- **Injection:** Visibility measurement stream stops at t=1800 s (25 min into run); no updates for 3600 s
- **Expected Data State:** HEALTHY → DEGRADED (T_DEGRADED_ENV=30s) → STALE → UNAVAILABLE (T_GRACE=120s)
- **Purpose:** Verify staleness timeout and fallback progression

### D6 — Stuck-At Visibility
- **Injection:** At t=1800 s, sensor locks to last value (e.g., 12 m), does not change for 3600 s
  While true_visibility transitions from 12 m → 5 m (fog thickening scenario)
- **Expected Data State:** Stuck-at check: DEGRADED flag at T_STUCK_MIN=300 s
- **Purpose:** Verify stuck-at detection; measure whether v_safe is appropriately reduced despite stuck reading
- **Critical Measurement:** Unsafe commands during the 300 s before stuck-at detection activates

### D7 — Visibility Bias (Sensor Over-Reading)
- **Injection:** visibility_m = true_visibility + 15 m (constant positive offset)
  true_visibility = 12 m → reported = 27 m
- **Expected Data State:** HEALTHY (bias not detectable without second source)
- **Purpose:** Demonstrate Class C limitation. The system CANNOT detect this.
- **Expected Result:** v_safe computed for 27 m, not 12 m. Unsafe gap documented as LIMITATION.
- **Measurement:** Delta v_safe at true 12 m vs. computed v_safe at reported 27 m

### D8 — High Noise
- **Injection:** visibility_m += N(0, 10 m) per sample (Gaussian noise, σ=10 m)
- **Expected Data State:** DEGRADED (noise check H4 triggers)
- **Purpose:** Verify noise detection and conservative r_effective penalty

### D9 — Conflicting Sensors
- **Injection (simulated):** Second source injected at visibility_B = 8 m while primary visibility_A = 25 m
  |A-B| = 17 m > CONFLICT_THRESHOLD=15 m (tunable)
- **Expected Data State:** CONFLICTING → r_effective = min(25, 8) = 8 m
- **Purpose:** Verify conservative min-selection under conflict
- **Note:** This requires the second-source infrastructure; simulation only

### D10 — Intermittent Sensor
- **Injection:** Alternating 10 s valid / 10 s absent pattern throughout the run
- **Expected Data State:** Oscillating HEALTHY/DEGRADED/STALE
- **Purpose:** Verify hysteresis prevents rapid state oscillation; verify recovery behaviour

### D11 — Communication Loss
- **Injection:** Full LoRa/WebSocket communication loss at t=3600 s for 600 s
- **Expected Data State:** COMM_STATE = NO_GATEWAY; local safety governor active independently
- **Purpose:** Verify Invariant I3 holds (local safety operates independently of central comms)
- **Existing Verification:** Already tested in Phase 8 HIL (HIL-11 to HIL-20); extend with environmental context

### D12 — Complete Environmental Data Loss
- **Injection:** All visibility/environmental data ceases at t=1800 s permanently
- **Expected Data State:** UNAVAILABLE
- **v_safe Action:** R_UNAVAILABLE_MIN = 8 m applied → v_safe ≈ 1.5–2.5 m/s at -8% grade
- **Fleet Action:** Trucks STAGE; production effectively halts
- **Purpose:** Verify graceful degradation; verify safety invariant holds at full loss

---

## 4. Metrics per Scenario

For each D0–D12:

**Safety Metrics (PRIMARY):**
1. Unsafe commands: count(v_command > v_safe)
2. Stopping envelope violations: count(S_stop + S_base > R_effective)
3. Detection latency: time from injection start to correct data_state activation (s)
4. Fallback latency: time from STALE/UNAVAILABLE state to r_effective reduction (s)

**Quality Metrics:**
5. False alarms: DEGRADED state triggered when data was actually HEALTHY
6. Missed degradation: HEALTHY state maintained when data was actually degraded

**Throughput Metrics (SECONDARY):**
7. Completed dumps
8. Ramp waiting time (s)
9. Staging waiting time (s)
10. Total waiting time (s)
11. Bottleneck duration (s)
12. Recovery time after degradation resolves (s)

**Primary assertion:** For every scenario D1–D12, unsafe commands = 0.

---

## 5. Plausible-But-Wrong Experiment (Section 11 — MANDATORY)

**Setup:**
- True visibility (ground truth in simulation) = 5 m
- Reported visibility (sensor output) = 50 m
- Duration: 600 s (10 minutes)

**What the system has:**
- visibility_m = 50 m → data_state = HEALTHY (passes all range and freshness checks)
- r_effective = 50 m
- v_safe computed at r_effective = 50 m → much higher than safe at 5 m

**What the system DOES NOT have:**
- Any mechanism to detect that reported 50 m ≠ true 5 m
- A second independent source
- A vehicle-mounted range sensor

**Expected Result:**
- data_state = HEALTHY (incorrect classification)
- v_safe computed for 50 m visibility ≈ 8.5 m/s at -8% grade
- Actual safe speed at 5 m visibility ≈ 2.7 m/s at -8% grade
- UNSAFE GAP = 8.5 - 2.7 = 5.8 m/s over-permission

**Classification:** EXPLICIT ARCHITECTURE LIMITATION  
**Marking:** This scenario must be reported as NOT DETECTABLE with available signals.  
**Mitigation partial:** Conservative r_effective factor (if applied) would reduce but NOT eliminate the gap.

---

## 6. Spatial Visibility Experiment (Section 12)

**Zone Configuration:**
`
Zone A (pit rim / loading) : visibility = 50 m
Zone B (upper haul road)   : visibility = 20 m
Zone C (mid-gradient)      : visibility = 8 m
Zone D (pit floor)         : visibility = 5 m
`

**Scenario A:** Single mine-wide visibility = 50 m (Zone A reading applied everywhere)  
**Scenario B:** Zone-differentiated visibility (vehicle assigned to its current zone's value)

**Measurement:** v_safe per truck per zone under both scenarios.

**Expected Finding:**
- Scenario A allows trucks in Zone D to travel at v_safe for 50 m visibility (≈ 8+ m/s)
- Scenario B restricts trucks in Zone D to v_safe for 5 m visibility (≈ 2.7 m/s)
- SAFETY IMPLICATION: Using single-point visibility is a systematic over-permission for pit-floor zones

**Classification:** FUTURE INTEGRATION REQUIREMENT (not implemented in current prototype)

---

## 7. Benchmark Comparison (Section 13)

Run in parallel:
- Original L0/L1/L2/L3/L4 canonical benchmark (unchanged)
- Original + Data Health Layer benchmark (D0 baseline with health checks active)
- Original + D5 (Stale) scenario

Compare:
- throughput
- queue behaviour
- waiting times
- bottleneck duration
- safety invariant counts

**Goal:** Demonstrate graceful degradation (throughput conservatively reduced under degradation)
without artificial improvement. The health layer should NOT improve baseline throughput.
