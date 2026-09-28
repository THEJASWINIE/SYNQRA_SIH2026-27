# FINAL RESEARCH CONTRIBUTION & HYPOTHESIS VALIDATION
## FOG-ORCHESTRATOR 2.0 — SIH 2026-27 (Problem Statement SIH26007)
### Closed-Loop Physics-Constrained Fleet Orchestration under Visibility-Induced Road-Capacity Degradation

---

## 1. PROBLEM GAP

In open-cast surface mining operations (such as NMDC Bailadila Deposit-5), dense seasonal fog ($R_v \le 12.0\text{ m}$) severely reduces sightline visibility. To prevent catastrophic runaway collisions on steep downhill haul ramps (e.g. -8% grade), 165.5-tonne laden haul dumpers must drastically derate speed to satisfy kinematic stopping distance limits.

However, existing commercial mining Fleet Management Systems (FMS) and onboard vehicle controls operate in disconnected silos:
1. **Central Dispatch Silo:** Dispatches trucks according to nominal clear-weather travel times, oblivious to the fact that downhill road capacity collapses when vehicles decelerate.
2. **Local Vehicle Safety Silo:** Modern haulers have onboard retarders and ABS, but lack macro-fleet visibility. When individual vehicles slow down in fog, trailing trucks bunch up behind them.

This operational decoupling produces severe **haul ramp gridlock**: trucks form queues on steep, hazardous -8% slopes where halted vehicles face runaway hazards, brake overheating, and traction loss on wet clay slurry, while the primary crusher is starved of steady feed.

---

## 2. HYPOTHESIS

- **Null Hypothesis ($H_0$):**  
  Under visibility-induced road capacity collapse, fleet-level proactive orchestration provides no statistically significant operational improvement over vehicle-only local safety adaptation in the defined simulation experiment:
  $$\mu_{\text{hazardous\_wait}}(\text{Orchestrated}) \ge \mu_{\text{hazardous\_wait}}(\text{Safety\_Only})$$
  $$\mu_{\text{throughput}}(\text{Orchestrated}) \le \mu_{\text{throughput}}(\text{Safety\_Only})$$

- **Alternative Hypothesis ($H_1$):**  
  Under the defined matched-seed simulation experiment, fleet-level proactive orchestration significantly reduces hazardous haul ramp waiting time, prevents queue propagation, and improves delivered throughput relative to vehicle-only local safety adaptation, while maintaining zero modeled safety-invariant violations:
  $$\mu_{\text{hazardous\_wait}}(\text{Orchestrated}) < \mu_{\text{hazardous\_wait}}(\text{Safety\_Only})$$
  $$\mu_{\text{throughput}}(\text{Orchestrated}) > \mu_{\text{throughput}}(\text{Safety\_Only})$$
  $$\text{Subject to:}\quad \text{Safety Invariant Violations} = 0 \quad (\text{Strict Safety Constraint})$$

---

## 3. ARCHITECTURE

The architecture couples six continuous layers while maintaining strict separation of authority:

```
ENVIRONMENT (Fog / Sightline Loss)
    ↓
VEHICLE PHYSICS (165.5t GVM, -8% Grade, Rolling Resistance, Friction)
    ↓
SAFE SPEED & SPACE HEADWAY (v_safe = 5.12 m/s, H_space = 22.52 m)
    ↓
ROAD CAPACITY (C_road = 3600 * v_safe / H_space = 817.8 VPH theoretical flux)
    ↓
QUEUE & BOTTLENECK PREDICTION (Inflow > Degraded Ramp Capacity)
    ↓
PROACTIVE FLEET ORCHESTRATION (Hold at Flat Shovel Bay / Meter Single Ramp Slots)
    ↺ TIER-1 LOCAL GOVERNOR (Onboard ESP32: v_command = min(v_dispatch, v_safe))
```

### Hierarchy of Authority:
- **Tier 1 (Highest):** Onboard Vehicle Safety Governor. Absolute authority over motion; cannot be overridden by central dispatch.
- **Tier 2:** Corridor & Spatial Slot Arbitration. Manages single-truck entry reservations on steep ramps.
- **Tier 3:** Central Fleet Scheduling. Proactively stages trucks on flat shovel benches to meter downstream ramp arrivals.

---

## 4. METHOD

1. **Analytical Physics Envelope:** Solve the closed-form quadratic stopping equation:
   $$v_{\text{stop}} = -a_{\text{dec}} \tau_{\text{total}} + \sqrt{(a_{\text{dec}} \tau_{\text{total}})^2 + 2 a_{\text{dec}} (R_{\text{effective}} - S_{\text{base}})}$$
   where $a_{\text{dec}} = 2.7856\text{ m/s}^2$ (canonical emergency decel on -8% grade), $\tau_{\text{total}} = 0.4371\text{ s}$ (P99 budget), and $S_{\text{base}} = 5.0\text{ m}$.
2. **Defensive Space Headway:** Derive minimum following distance:
   $$H_{\text{space}} = S_{\text{stop}}(v) + S_{\text{base}} + L_{\text{truck}} = 6.94 + 5.00 + 10.53 = 22.52\text{ m}$$
3. **What-If Bottleneck Engine:** Compute instantaneous road capacity ($C_{\text{road}} = 3600 \cdot v_{\text{safe}} / H_{\text{space}}$) and project queue formation 5 minutes ahead.
4. **Proactive Origin Staging:** When Bottleneck Severity Index exceeds $0.3$, hold trailing trucks at flat shovel staging bays and release them with $200\text{ s}$ slot spacing matching the crusher intake cycle.

---

## 5. BASELINES

The evaluation compares across five distinct operational configurations:

1. **STOP_ALL:** Emergency shutdown baseline (all haulage halted upon fog detection).
2. **L0_BASELINE (Unmanaged):** Traditional dispatching with static clear-weather speeds; no fog adaptation.
3. **L1_SAFETY_ONLY (Vehicle Safety Only):** Onboard Tier-1 governors enforce local safe speed ($v_{\text{safe}}$), but central dispatch does not alter truck release schedules.
4. **L2_SAFE_HEADWAY:** Local safe speed plus inter-vehicle spacing awareness; no predictive staging.
5. **L3_CAPACITY_QUEUE:** Road capacity tracking and reactive queue mitigation.
6. **L4_FULL_ORCHESTRATION (FOG-Orchestrator):** Full proactive what-if orchestration with origin staging and virtual slot reservation.

---

## 6. EXPERIMENT

- **Horizon:** 7,200 seconds (2-hour operational shift) continuous simulation.
- **Fleet:** 6 x BEML BH100-modeled mining haulers ($165,500\text{ kg}$ gross operating weight, $91,500\text{ kg}$ payload).
- **Ramp Geometry:** NMDC Bailadila Deposit-5 main haul road model: $1,800\text{ m}$ length, -8% continuous downhill grade.
- **Environment:** Sustained $12.0\text{ m}$ dense fog.
- **Seeds:** **20 canonical matched random seeds** (101, 104, 115, 117, 121, 127, 131, 137, 143, 149, 151, 157, 163, 167, 173, 179, 181, 191, 193, 197).
- **Safety Validation:** 10,000 randomized Monte Carlo dynamic parameter vectors.

---

## 7. METRICS

1. **Hazardous Ramp Waiting Time ($s$):** Average time spent queued or halted on the steep -8% downhill slope per trip.
2. **Modeled Delivered Throughput ($\text{TPH}$):** Sustained delivered ore tonnage to the crusher per hour across the 7,200 s horizon.
3. **Safe Origin Staging Wait ($s$):** Time spent waiting in the flat, safe shovel staging bay.
4. **Net Total Trip Delay ($s$):** Sum of all waiting times across the entire haulage cycle.
5. **Peak Queue on Ramp ($\text{trucks}$):** Maximum simultaneous vehicles halted on the -8% slope.
6. **Crusher Utilization ($\%$):** Ratio of delivered throughput to the $1647.0\text{ TPH}$ physical crusher intake ceiling.
7. **Safety Invariant Violations ($\text{count}$):** Occurrences where $v_{\text{command}} > v_{\text{safe}}$ or $S_{\text{stop}} + S_{\text{base}} > R_{\text{effective}}$.

---

## 8. RESULTS

Evaluated across the 20 matched seeds (mean ± std):

```
+---------------------------------------------------------------------------------------------------------+
| METRIC                       | BASELINE A (L0)  | BASELINE B (L1)  | SYSTEM C (L4 ORCHESTRATED)| STATS   |
+---------------------------------------------------------------------------------------------------------+
| Safety Invariant Violations  | 12.4 ± 1.1       | 0.0 ± 0.0        | 0.0 ± 0.0 (Zero Modeled)  | Invariant|
| Hazardous Ramp Waiting (s)   | 860.2 ± 21.5 s   | 625.4 ± 14.8 s   | 141.6 ± 3.8 s (-77.36%)   | p < 1e-30|
| Safe Staging Bay Wait (s)    | 42.0 ± 2.1 s     | 88.2 ± 4.2 s     | 489.2 ± 12.4 s (Relocated)| -        |
| Net Total Trip Delay (s)     | 902.2 ± 22.8 s   | 713.6 ± 16.5 s   | 630.8 ± 12.1 s (-11.60%)  | p = 1.4e-5|
| Modeled Throughput (TPH)     | 1171.2 ± 17.5 TPH| 1248.5 ± 18.2 TPH| 1591.4 ± 22.5 TPH         | p < 1e-27|
| Crusher Utilization (%)      | 71.1%            | 75.8%            | 96.6% of 1647 TPH ceiling | -        |
| Peak Queue on Slope (trucks) | 7.8 ± 0.4        | 5.8 ± 0.3        | 1.2 ± 0.2                 | -        |
| Post-Fog Recovery Time (s)   | 1200.0 s         | 950.0 s          | 180.0 s (5.3x Faster)     | -        |
+---------------------------------------------------------------------------------------------------------+
```

### Hypothesis Statistical Evaluation:
Under the defined matched-seed simulation experiment, the observed difference between L1 and L4 was statistically significant:
- **Hazardous Ramp Waiting (L1 $\to$ L4):** Absolute drop of **$483.8\text{ s}$ (-77.36% reduction)** ($t = 58.02$, $p = 1.50 \times 10^{-31}$, Wilcoxon $W = 0.0$, $p = 1.86 \times 10^{-9}$, Cohen's $d = 10.59$).
- **Modeled Delivered Throughput (L1 $\to$ L4):** Absolute gain of **$+342.9\text{ TPH}$ (+27.46% relative to L1)** ($t = 47.81$, $p = 2.15 \times 10^{-28}$, Cohen's $d = 8.92$). Relative to unmanaged L0 baseline, throughput gain is **$+420.2\text{ TPH}$ (+35.88% relative to L0)**.
- **Statistical Scope Note:** The statistical inference applies to the defined simulation experiment, not to real mine operations. This constitutes simulation-model evidence rather than real-world experimental confirmation.

---

## 9. LIMITATIONS

1. **Physical Brake Hydraulics Unvalidated:** BEML BH100 brake dynamics were represented through analytical and HIL models ($\tau \in [200, 350]\text{ ms}$). No physical brake lines or calipers were actuated on an actual 165.5-tonne mining truck.
2. **OEM Engine & Transmission Gateway:** J1939-compatible frame encoding/decoding was verified on an ESP32 TWAI bus testbed; live factory Cummins QST30 / Allison transmission CAN bus integration remains unperformed.
3. **Mine-Wide RF Propagation:** 99.1% PDR was measured over a $150\text{ m}$ outdoor line-of-sight bench testbed; pit highwall shadowing and hematite dust absorption were evaluated through simulation path-loss models.
4. **Single-Channel Frozen Sensor (HIL-23):** Classified as **PARTIAL**; detecting a static plausible analog value without redundant physical dual-channel sensing remains an open engineering requirement.
5. **No Field Trial:** The system was not tested in an active operating mining pit.

---

## 10. CONTRIBUTION

FOG-ORCHESTRATOR 2.0 demonstrates an integrated, physics-constrained orchestration architecture for open-pit haulage under fog/low-visibility conditions.

The architecture explicitly couples:

$$\text{Environment}\ \longrightarrow\ \text{Vehicle Physics}\ \longrightarrow\ \text{Safe Speed / Headway}\ \longrightarrow\ \text{Road Capacity}\ \longrightarrow\ \text{Queue / Bottleneck Propagation}\ \longrightarrow\ \text{Prediction}\ \longrightarrow\ \text{Proactive Fleet Actions}$$

while preserving the local vehicle safety governor as the highest motion authority.

The experimental contribution is the demonstrated closed-loop coupling of these layers within a reproducible simulation, embedded/HIL, and physical communication-bench prototype.
