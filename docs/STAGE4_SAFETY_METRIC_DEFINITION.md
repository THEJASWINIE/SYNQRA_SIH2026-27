# STAGE 4 — SAFETY METRIC MATHEMATICAL & CODE DEFINITION

This document audits the exact code location, logic, and mathematical formulation defining a "Safety Violation" across the FOG-ORCHESTRATOR 2.0 evaluation pipeline.

---

## 1. Code Definition in the Evaluation Pipeline

In `experiments/run_stage3_robustness_and_sensitivity.py` (lines 135–139):

```python
r_state = sim.state.roads.get(v.road_edge)
v_safe_limit = r_state.safe_speed_mps if r_state else 11.11
if v.speed_v > v_safe_limit + 1e-3:
    speed_violations += 1
```

And in line 152:
```python
"safety_violations": int(sim.state.safety_violations_count + speed_violations)
```

Where:
- `sim.state.safety_violations_count` tracks physical vehicle collisions ($d_{\text{actual}} < L_{\text{truck}}$). Throughout all Stage 3 and Stage 4 tests, `sim.state.safety_violations_count == 0` (zero collisions).
- Therefore, the safety violation counter evaluated in the benchmark is **strictly and exclusively a speed limit exceedance metric**:
  $$\text{Safety Violation} \iff v_{\text{actual}}(t) > v_{\text{safe\_limit}}(t) + 0.001\text{ m/s}$$

---

## 2. Classification Against Prompt Hypotheses

| Candidate Definition | Matches Code? | Evaluation |
|:---|:---:|:---|
| **A. $v_{\text{actual}} > v_{\text{safe}}$** | **YES** | **This is the exact metric evaluated.** Any timestep where a vehicle's instantaneous linear velocity exceeds the road segment's safe speed by $> 1.0\text{ mm/s}$ increments the violation counter. |
| **B. $v_{\text{command}} > v_{\text{safe}}$** | NO | Command-level violations are tracked separately under `clamped_count` (`target_spd > v_safe + 1e-3`). They are clamped by the governor and do not increment `safety_violations`. |
| **C. $\text{headway} < h_{\text{safe}}$** | NO | Longitudinal headway is actively maintained by car-following logic with a hard lower bound of $15.52\text{ m}$ ($L_{\text{truck}} + d_{\text{margin}}$). |
| **D. Collision** | NO | Direct collisions increment `sim.state.safety_violations_count`, which was $0.0$ across all seeds. |
| **E. Stopping-distance violation** | DERIVED | $v_{\text{safe}}$ is derived from stopping distance. Thus, exceeding $v_{\text{safe}}$ implies travel faster than the stopping horizon. |
| **F. Prediction constraint violation** | NO | MILP/MPC constraint violations trigger status warnings, not benchmark violation counters. |

---

## 3. Physical Significance of the Evaluated Metric

1. **Not a Catastrophic Failure**:
   - The metric does NOT indicate that a truck struck another vehicle or ran off the haul road.
   - It records a transient speed overshoot where actual ground velocity temporarily exceeded the calculated maximum safe velocity envelope on that specific road segment.
2. **Strictness of the Threshold**:
   - The numerical tolerance is $+1.0\text{ mm/s}$ ($10^{-3}\text{ m/s}$), representing extreme mathematical conservatism ($0.0036\text{ km/h}$).
   - Any finite deceleration across a road boundary where the speed limit drops (e.g., from $4.731\text{ m/s}$ down to $4.134\text{ m/s}$) can trigger this metric if the vehicle does not complete its deceleration prior to crossing the segment boundary.
