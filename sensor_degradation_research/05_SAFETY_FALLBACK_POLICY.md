# 05 — SAFETY FALLBACK POLICY
## FOG-ORCHESTRATOR 2.0 — Exact Behavior for 10 Failure Cases
**Date:** 2026-09-21  
**Authority Hierarchy:** Local Safety Governor (Tier-1) > Central Orchestration (Tier-3)

All policies are derived from safety logic. No arbitrary choices.

---

## Policy Derivation Principle

For every case, determine the correct action by asking:
1. What is the WORST CASE physically possible state?
2. What speed does the safety envelope require for that worst case?
3. Is the current v_safe computed with RELIABLE inputs?

If not → apply conservative r_effective → lower v_safe → lower v_command.
The local safety governor always applies the final clamp.

---

## CASE 1 — Visibility HEALTHY

**Condition:** data_state = HEALTHY. Fresh measurement, in-range, not stuck.

**Action:** CONTINUE  
**r_effective:** = visibility_m (unmodified)  
**v_safe:** Computed normally from solve_safe_speed  
**HMI display:** ENVIRONMENTAL DATA: HEALTHY | VISIBILITY: [value] m  
**Rationale:** Full trust in measurement. Normal operation.

---

## CASE 2 — Visibility STALE

**Condition:** data_state = STALE. Age between T_DEGRADED_ENV and T_STALE_ENV, or between T_STALE_ENV and T_GRACE_PERIOD end.

**Sub-case 2a — Within grace period (T_STALE_ENV ≤ age ≤ T_GRACE_PERIOD):**

**Action:** RESTRICT  
**r_effective:** = max(last_known_vis * STALE_FACTOR, R_MIN)  
**v_safe:** Recomputed with reduced r_effective → lower speed permitted  
**HMI display:** ENVIRONMENTAL DATA: STALE | APPLYING CONSERVATIVE VISIBILITY  
**Rationale:** Last known value may no longer represent current conditions.  
Fog could have deteriorated. Conservative penalty applied.  
Local governor clamps final speed.

**Sub-case 2b — Post grace period:**

**Action:** RESTRICT to STAGE  
**r_effective:** = R_UNAVAILABLE_MIN (8.0 m)  
**v_safe:** Recomputed with R_UNAVAILABLE_MIN → very low or zero speed  
**HMI display:** ENVIRONMENTAL DATA: UNAVAILABLE — STAGING VEHICLE  
**Rationale:** Cannot assume any visibility after extended absence. Must assume worst case.

---

## CASE 3 — Visibility UNAVAILABLE

**Condition:** data_state = UNAVAILABLE. All sources absent or failed.

**Action:** RESTRICT → STAGE  
**r_effective:** = R_UNAVAILABLE_MIN (8.0 m)  
**v_safe:** Computed with R_UNAVAILABLE_MIN. At -8% grade: v_safe ≈ 1.5–2.5 m/s.  
**HMI display:** ENVIRONMENTAL DATA: UNAVAILABLE — SPEED RESTRICTED  
**Rationale:** Without any visibility data, the system cannot certify a safe speed.  
Minimum conservative assumption applied. If the vehicle is already staged, hold position.  
Local safety governor enforces the resulting v_safe ceiling.

---

## CASE 4 — Visibility Conflicts with Independent Source

**Condition:** data_state = CONFLICTING. |vis_A - vis_B| > CONFLICT_THRESHOLD.

**Action:** RESTRICT  
**r_effective:** = min(vis_A, vis_B) — always use the more conservative value  
**v_safe:** Recomputed with conservative r_effective  
**HMI display:** ENVIRONMENTAL DATA: CONFLICTING — USING CONSERVATIVE VALUE  
**Rationale:** When sources disagree, we cannot know which is correct.  
The conservative (lower visibility) value is safer because:  
  - If lower is correct: vehicle is safe.  
  - If higher is correct: we accept a small throughput cost.  
  - If we use higher and it is wrong: vehicle may be unsafe.

**Note:** CONFLICTING state NOT currently detectable (no second source on prototype).  
This policy is a design requirement for future infrastructure integration.

---

## CASE 5 — Vehicle Speed Signal STALE

**Condition:** TelemetryQualityFilter returns quality = STALE or OFFLINE for vehicle speed.

**Action:** RESTRICT → STOP  
**v_safe:** Cannot be applied without knowing current vehicle speed.  
The local governor has last_known_speed; if it exceeds v_safe at last computation, STOP.  
**HMI display:** VEHICLE TELEMETRY: STALE — UNABLE TO CONFIRM SPEED  
**Rationale:** Without confirmed current speed, the stopping distance calculation cannot be validated.  
This is Invariant I5 (stale vehicle speed triggers safe fallback) — ALREADY IMPLEMENTED.

---

## CASE 6 — Vehicle Speed Sources Disagree

**Condition:** Encoder-derived speed vs. V2V-reported speed differ by > SPEED_CONFLICT_THRESHOLD.

**Action:** RESTRICT — use lower (more conservative) speed as confirmed speed  
**Rationale:** If encoder says 5 m/s but V2V says 8 m/s, assume 8 m/s for safety margin.  
This prevents understating stopping distance.  
**Note:** TRUCK_02 speed is PWM-derived (synthetic), not encoder-measured. Never use  
TRUCK_02 speed as encoder-confirmed. This is an existing architectural constraint.

---

## CASE 7 — Environmental State Uncertain While Vehicle is Moving

**Condition:** data_state transitions from HEALTHY to DEGRADED or STALE while vehicle is in motion.

**Action:** RESTRICT (immediate)  
**Process:**
1. Recompute v_safe with conservative r_effective immediately.
2. If new v_safe < current speed: local governor issues CLAMP (decelerate to new v_safe).
3. HMI alert: ENVIRONMENTAL DATA DEGRADED — REDUCING SPEED.
**Rationale:** Uncertainty in visibility while moving means the stopping distance assumption may be violated.  
Deceleration is the safe response.

---

## CASE 8 — Environmental State Uncertain While Vehicle Is Already in Constrained Segment

**Condition:** data_state = DEGRADED or STALE while vehicle is on narrow road / switchback / loaded descent.

**Action:** STAGE (do not proceed further into constrained segment until data restores)  
**Process:**
1. Apply R_UNAVAILABLE_MIN as r_effective.
2. v_safe computed with R_UNAVAILABLE_MIN may be very low or near zero.
3. Vehicle stages at entry point or last safe stopping area.
4. Fleet orchestration is notified: do not dispatch more vehicles to this segment.
**Rationale:** A constrained segment has reduced passing space and higher collision consequence.  
Unknown visibility in such a segment is higher risk than an open haul road.

---

## CASE 9 — Communication Fails While Data Remains Locally Valid

**Condition:** WebSocket / LoRa / Gateway fails. Local environmental data (if cached) is still fresh.  
fail_safe_controller enters DEGRADED_COMMUNICATION or NO_GATEWAY state.

**Action:** CONTINUE locally (reduced orchestration)  
**Process:**
1. Local safety governor continues operating (Invariant I3 — already verified in HIL testing).
2. Last valid locally-cached r_effective used until it expires (T_STALE_ENV).
3. If environmental data also becomes stale, transition to CASE 2/3.
4. Central orchestration cannot issue new commands until communication restores.
**Rationale:** Communication loss must NOT disable local safety. This is the core architecture principle.  
Local governor is always the final authority regardless of central connectivity.

---

## CASE 10 — Communication Returns After Degraded State

**Condition:** WebSocket / LoRa reconnects. fail_safe_controller enters RECOVERY state.

**Action:** CONTROLLED RECOVERY  
**Process:**
1. fail_safe_controller requires defined valid sequence resynchronization (Invariant I10).
2. Environmental data health re-evaluates first incoming visibility measurement.
3. If fresh and valid: data_state = HEALTHY; r_effective restored to measured value.
4. If measurement is stale or invalid: data_state = STALE; conservative fallback maintained.
5. v_safe gradually relaxes to allow-through as data confidence rebuilds (hysteresis).
**HMI display:** COMMUNICATION RESTORED — VERIFYING ENVIRONMENTAL DATA  
**Rationale:** Recovery must not immediately assume all data is good.  
Both communication state AND environmental data state must independently confirm HEALTHY  
before full operational speed is permitted.

---

## Policy Summary Table

| Case | Trigger | Action | r_effective | v_safe Effect |
|---|---|---|---|---|
| 1 | HEALTHY vis | CONTINUE | = visibility_m | Normal |
| 2a | STALE (grace) | RESTRICT | * STALE_FACTOR | Reduced |
| 2b | STALE (post-grace) | STAGE | = R_UNAVAILABLE_MIN | Very low |
| 3 | UNAVAILABLE | STAGE | = R_UNAVAILABLE_MIN | Very low |
| 4 | CONFLICTING | RESTRICT | = min(A, B) | Reduced |
| 5 | Speed stale | STOP | N/A (speed unknown) | Zero |
| 6 | Speed disagree | RESTRICT | N/A | Use conservative speed |
| 7 | Env uncertain (moving) | RESTRICT | * DEGRADED_FACTOR | Reduced |
| 8 | Env uncertain (constrained) | STAGE | = R_UNAVAILABLE_MIN | Very low |
| 9 | Comm fail (data valid) | CONTINUE (local) | Last cached | Unchanged |
| 10 | Comm restore | CONTROLLED RECOVERY | Rebuilt from fresh data | Gradually restored |

---

## Safety Authority Chain (Unchanged)

`
DATA HEALTH MODULE
    ↓
may only modify r_effective conservatively
    ↓
ENVIRONMENT STATE
    ↓
PHYSICS SOLVER (solve_safe_speed)
    ↓
LOCAL SAFETY GOVERNOR (final authority)
    ↓
v_applied ≤ v_safe (INVARIANT I1, non-negotiable)
    ↓
ACTUATOR
`

The data health module NEVER calls any actuator function.
The fleet orchestration layer NEVER overrides local safety governor.
