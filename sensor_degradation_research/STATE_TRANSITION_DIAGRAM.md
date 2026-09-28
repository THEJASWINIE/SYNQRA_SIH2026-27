# STATE TRANSITION DIAGRAM
## FOG-ORCHESTRATOR 2.0 — EnvironmentalDataHealth State Machine
Date: 2026-09-21

## DataState Transitions

States: HEALTHY, DEGRADED, STALE, UNAVAILABLE, CONFLICTING

Transitions:

  [HEALTHY]
    --> DEGRADED  : (t_now - t_last_received) > T_DEGRADED_ENV (30s)
    --> DEGRADED  : noise_check() fails (std_dev > NOISE_THRESHOLD)
    --> DEGRADED  : stuck_at_check() triggers (after T_STUCK_MIN=300s)
    --> CONFLICTING: two sources disagree by > CONFLICT_THRESHOLD (future)
    --> STALE     : (t_now - t_last_received) > T_STALE_ENV (60s)
    --> UNAVAILABLE: (t_now - t_last_received) > T_GRACE_PERIOD (120s)
    --> UNAVAILABLE: range_check() fails (vis <= 0 or vis > 2000m) [repeated]

  [DEGRADED]
    --> HEALTHY   : fresh valid packet received, all checks pass, hysteresis N=2 samples
    --> STALE     : (t_now - t_last_received) > T_STALE_ENV (60s)
    --> UNAVAILABLE: (t_now - t_last_received) > T_GRACE_PERIOD (120s)

  [STALE]
    --> DEGRADED  : valid packet received (first valid after stale)
    --> HEALTHY   : N valid packets received (hysteresis, N=2)
    --> UNAVAILABLE: (t_now - t_last_received) > T_GRACE_PERIOD (120s)

  [UNAVAILABLE]
    --> STALE     : valid packet received (first fresh packet)
    --> DEGRADED  : N valid packets (hysteresis)
    --> HEALTHY   : N consecutive valid, in-range packets (hysteresis, N=3 for UNAVAILABLE recovery)

  [CONFLICTING]
    --> HEALTHY   : sources agree within CONFLICT_THRESHOLD again (future)
    --> STALE     : primary source becomes stale
    --> UNAVAILABLE: all sources fail

## r_effective Assignment per State

  HEALTHY     : r_effective = visibility_m (unmodified)
  DEGRADED    : r_effective = max(visibility_m * 0.7, R_MIN=5.0m)
  STALE (grace): r_effective = max(last_known * 0.5, R_MIN=5.0m)
  STALE (post) : r_effective = R_UNAVAILABLE_MIN = 8.0m
  UNAVAILABLE : r_effective = R_UNAVAILABLE_MIN = 8.0m
  CONFLICTING : r_effective = min(source_A, source_B)

## Hysteresis Rule

  Recovery from STALE/UNAVAILABLE requires N consecutive valid packets
  before transitioning back to HEALTHY.
  N = 2 from STALE, N = 3 from UNAVAILABLE.
  Purpose: prevent rapid oscillation when sensor is intermittent.

## Fail-Safe Behavior of the Health Module Itself

  If EnvironmentalDataHealth crashes or raises an unhandled exception:
    r_effective = R_UNAVAILABLE_MIN
    data_state = UNAVAILABLE
  The module fails conservatively (cannot increase r_effective on failure).
