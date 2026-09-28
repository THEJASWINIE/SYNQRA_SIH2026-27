# FOG-ORCHESTRATOR 2.0 — SENSOR DEGRADATION RESEARCH & SCIENTIFIC VALIDATION REPORT
## Confidence-Aware Sensor/Data Health for Fog & Low-Visibility Open-Cast Mine Haulage

**Project Reference:** SIH26007 — Ministry of Mines / NMDC Problem Statement  
**Author:** Safety Systems Architect & Controls Engineering Lead  
**Audit Standard:** Formal 10-Tier Evidence Boundary (Tiers L1 to L10)  
**Date:** 2026-09-21  
**Decision Gate Classification:** **B — VALIDATED WITH LIMITATIONS**  

---

## 1. Problem
In open-cast iron ore mining (such as NMDC Bailadila Deposit-5), dense advection fog, seasonal atmospheric inversions, and fugitive dust clouds severely reduce line-of-sight visibility, frequently dropping perception distances below $15\text{ metres}$. Heavy Earthmoving Mining Machinery (HEMM)—specifically $165.5\text{-tonne}$ gross-weight haul trucks such as the BEML BH100—routinely navigate steep, unpaved haul road ramps with downhill grades ranging from $-8\%$ to $-12\%$.

On a $-8\%$ grade, the component of gravity parallel to the road opposes vehicle braking, significantly extending stopping distances. Under classical rigid-body kinematics:
$$S_{\text{stop}}(v) = v \tau_{\text{total}} + \frac{v^2}{2 a_{\text{dec}}}$$
where $\tau_{\text{total}}$ represents total reaction latency (sensor ingestion + computation + pneumatic/hydraulic brake line build-up) and $a_{\text{dec}}$ is the effective tire-road deceleration.

To prevent rear-end collisions and highwall runaways, vehicle operating speed must be strictly governed by the stopping distance constraint:
$$S_{\text{stop}}(v) + S_{\text{base}} \le R_{\text{effective}}$$
where $R_{\text{effective}}$ is the effective perception distance (visibility) and $S_{\text{base}}$ is a static safety buffer ($5.0\text{ m}$).

If environmental telemetry degrades—due to sensor link dropouts, buffer freezing, optical window icing, analog noise, or calibration drift—and reports an outdated or falsely optimistic visibility (e.g., reporting $50\text{ m}$ while actual visibility is $12\text{ m}$), the vehicle safe speed solver will over-permit velocity by up to $+5.82\text{ m/s}$ ($+20.9\text{ km/h}$). On a wet haul ramp ($\mu = 0.35$), this deficit creates an unavoidable collision hazard.

---

## 2. Research Gap
Prior heavy-equipment safety and fleet management literature presents a critical bifurcation:
1. **Opaque Deep-Learning Perception:** Advanced autonomous haulage research frequently proposes end-to-end deep learning or multi-modal neural sensor fusion (camera-LiDAR-radar). While capable in urban automotive settings, neural perception models cannot guarantee deterministic worst-case execution times (WCET), suffer from extreme distribution shift under pit dust/fog backscatter, and fail functional safety auditability requirements under ISO 19014 and IEC 61508.
2. **Commercial FMS Macro-Oversimplification:** Commercial Fleet Management Systems (e.g., Modular DISPATCH, Wenco) optimize shift-level haulage allocation over $15\text{--}60\text{ minute}$ horizons. They do not run real-time ($10\text{ Hz}$) dynamic stopping physics, treat visibility as a binary mine-wide scalar, and lack mechanisms to couple telemetry trust directly to local vehicle speed governors.

**The Gap:** There has been no lightweight, deterministic, rule-based data-health layer that bridges raw environmental telemetry and physical stopping distance solvers without bypassing onboard Level 1 vehicle safety authority or introducing unverified artificial intelligence.

---

## 3. Hypothesis
We hypothesize that:
> A bounded, auditable, rule-based data-health layer (evaluating freshness, range, sequence, and variance) that conservatively scales effective perception distance ($R_{\text{effective}}$) and enforces multi-frame recovery hysteresis will:
> 1. Eliminate stopping-envelope violations ($S_{\text{stop}} + S_{\text{base}} > R_{\text{true}}$) under detectable telemetry faults;
> 2. Maintain strict invariance of onboard command authority ($v_{\text{command}} \le v_{\text{safe}}$);
> 3. Migrate traffic congestion from high-hazard active downhill ramps into controlled, flat staging areas ($> 90\%$ reduction in hazardous ramp waiting);
> 4. Introduce negligible compute latency ($< 1.2\text{ ms}$ on embedded microcontrollers);
> while explicitly formalizing the mathematical boundary where single-source unreferenced data health cannot detect Class C plausible-but-wrong measurements.

---

## 4. Existing Architecture
FOG-ORCHESTRATOR 2.0 operates under an inviolable 5-level control hierarchy:
- **Level 0:** Hardware Watchdog & Physical Emergency Stop.
- **Level 1:** Local Vehicle Safety Governor (`LocalVehicleSafetyGovernor`) — **Final Operational Authority**.
- **Level 2:** Command Gateway Ingestion & Validation.
- **Level 3:** Central Fleet Orchestrator & Capacity Controller.
- **Level 4:** Predictive What-If & Bottleneck Simulation.
- **Level 5:** Authoritative 3D Digital Twin & HMIs.

Prior to this research extension, vehicle telemetry (wheel speed, RPM, IMU) was guarded by `TelemetryQualityFilter`, but environmental visibility ($R_{\text{vis}}$) was fed directly into `EnvironmentState` without quality, age, or range checks.

---

## 5. Data-Health Architecture
The `EnvironmentalDataHealth` module implements six auditable verification rules:
- **Rule H1 (Freshness & Staleness):**  
  Age $a = t_{\text{now}} - t_{\text{timestamp}}$.  
  If $a > 120.0\text{ s} \to \text{UNAVAILABLE}$ ($R_{\text{eff}} = 8.0\text{ m}$, confidence $0.0$).  
  Else if $a > 60.0\text{ s} \to \text{STALE}$ ($R_{\text{eff}} = R_{\text{last}} \times 0.50$, confidence $0.40$).  
  Else if $a > 30.0\text{ s} \to \text{DEGRADED}$ ($R_{\text{eff}} = R_{\text{last}} \times 0.70$, confidence $0.70$).  
  Else $\to \text{HEALTHY}$ ($R_{\text{eff}} = R_{\text{vis}}$, confidence $1.00$).
- **Rule H2 (Schema & Type):** Rejects non-numeric, string, dict, NaN, and $\pm\infty$ values, failing closed to UNAVAILABLE ($8.0\text{ m}$).
- **Rule H3 (Plausibility Range):** Clamps visibility to $[1.0\text{ m}, 300.0\text{ m}]$.
- **Rule H4 (Sequence Monotonicity):** Detects duplicate sequences, rollbacks, and gaps.
- **Rule H5 (Variance & Noise):** Rolling window of 10 samples: flags constant/stuck-at signal behavior if $\sigma < 0.05\text{ m}$ over $\ge 300\text{ s}$; flags excessive noise if $\sigma > 20.0\text{ m}$.
- **Rule H6 (Cross-Source Conflict):** If secondary sensor differs by $> 25.0\text{ m}$, sets CONFLICTING and resolves to $\max(5.0, \min(A, B) \times 0.70)$.
- **Recovery Hysteresis:** Enforces $2$ consecutive clean observations to recover from STALE, and $3$ consecutive clean observations to recover from UNAVAILABLE.
- **Fail-Closed Boundary:** Module wrapped in robust exception guards; any crash defaults to UNAVAILABLE ($R_{\text{eff}} = 8.0\text{ m}$).

---

## 6. Failure Taxonomy
We classified sensor failure modes into five structural classes (F01–F16):
- **Class A (Temporal / Availability):** F01 (Total Link Loss), F02 (Periodic Packet Loss), F03 (Burst Dropout), F08 (Stale Telemetry), F09 (Intermittent Comm).
- **Class B (Signal / Value Corruption):** F05 (Stuck-At Sensor), F06 (Calibration Bias), F07 (Analog Noise), F10 (Sequence Rollback / Replay), F11 (Out-of-Range), F12 (Schema / NaN / Non-Finite).
- **Class C (Dangerous Undetected / Plausible-But-Wrong):** F15 (Sensor reports $50\text{ m}$ when reality is $5\text{ m}$, with valid format and timestamps).
- **Class D (Spatial Inconsistency):** F14 (Single point weather station applied across non-uniform micro-climate pit zones).
- **Class E (Multi-Source Disagreement):** F16 (Dual sensors disagreeing beyond tolerance).

---

## 7. Experimental Method
Deterministic fault injection was implemented in `experiments/run_sensor_degradation_benchmark.py`:
- Synthetic fault timeline rolls in between $t=1800\text{ s}$ and $t=5400\text{ s}$ of a $7200\text{ s}$ run.
- 14 distinct scenarios (D0 through D13) were executed across 30 matched random seeds (Seeds 0 to 29) under two operational modes:
  - **B0 (Baseline — Without Data Health):** Raw sensor pass-through; holds stale scalar upon packet loss.
  - **B1 (Treatment — With Data Health):** Rule-based health pipeline with conservative factor scaling and recovery hysteresis.
- Total experimental scale: $14 \times 30 \times 2 = \mathbf{840\text{ closed-loop simulation runs}}$.

---

## 8. D5–D13 Forensic Results

| Scenario ID | Fault Description | B0 Envelope Violations | B1 Envelope Violations | Detection Latency | Causal Mechanism & Forensic Finding |
|---|---|---|---|---|---|
| **D5_stale_env** | Telemetry link freeze | 3,601.0 | 120.0 | 30.0 s | **96.7% mitigation.** 120 residual violations correspond exactly to the 120s $T_{\text{GRACE}}$ timeout transition before the 8m crawl floor activates. |
| **D6_stuck_at** | Sensor frozen at 45m | 3,601.0 | 3,601.0 | 300.0 s | **Negative Result.** Constant signal detected at 300s, but single-source variance cannot reconstruct ground truth (12m). |
| **D7_biased_sensor** | Sensed = True + 30m | 3,601.0 | 3,601.0 | Undetected | **Class C Unobservable.** Valid schema, fresh timestamps, plausible range; physically invisible without redundant sensors. |
| **D8_noisy_sensor** | Gaussian $\sigma=25\text{m}$ noise | 1,805.6 | 1,663.5 | 3.5 s | **7.9% reduction.** Dynamic throttling dampens noise spikes; modest physical improvement due to filter phase lag. |
| **D9_conflicting** | Dual sources (50m vs 15m) | 3,601.0 | 0.0 | 1.0 s | **100% elimination.** Redundant sensor divergence resolved conservatively via $0.70 \times \min(R_1, R_2) = 10.5\text{ m}$. |
| **D10_intermittent** | 40s drop / 20s active cycle | 40.0 | 40.0 | 30.0 s | **Negative Result.** 40 violations occur solely during the first 40s drop window before the 20m packet is latched. |
| **D11_comm_loss** | Central comms severed | 3,601.0 | 120.0 | 30.0 s | **96.7% mitigation.** Identical to D5; proves local vehicle governor enforces crawl floor independently. |
| **D12_complete_loss** | Zero telemetry from start | 3,601.0 | 0.0 | 0.0 s | **100% elimination.** Fails closed immediately to 8.0m floor ($v_{\text{safe}} = 9.7\text{ km/h}$) from $t=0$. |
| **D13_plausible_wrong**| Reported 50m (true 5m) | 3,601.0 | 3,601.0 | Undetected | **Class C Unobservable.** Single-source data health mathematically cannot detect internally consistent false telemetry. |

---

## 9. Command-Authority Safety Results
- **Invariant Tested:** $v_{\text{command}} \le v_{\text{safe}}$
- **Measured Violations:** **0 violations** across all 840 simulation runs and all 10,000 Monte Carlo randomized trials.
- **Statement:**
  > *"No violations of the tested command-authority invariant $v_{\text{command}} \le v_{\text{safe}}$ were observed."*
- The Level 1 `LocalVehicleSafetyGovernor` strictly enforced its authority, preventing the central fleet orchestrator or optimizer from commanding speeds above the computed safe speed.

---

## 10. Stopping-Envelope Results
- **Invariant Tested:** $S_{\text{stop}}(v_{\text{command}}) + S_{\text{base}} \le R_{\text{true}}$
- **Measured Outcome:**
  > *"Ground-truth stopping-envelope violations remained for fault modes where the reported environmental measurement was inconsistent with ground truth."*
- Stopping-envelope violations were completely eliminated in D0, D1, D9, and D12, and reduced by 96.7% in D5 and D11.
- Stopping-envelope violations remained unmitigated in D6, D7, and D13, explicitly demonstrating the physical observability boundary of single-source sensing.

---

## 11. Hazardous Road Waiting
- **Definition:** Uncontrolled dwell time spent stopped in stationary queues on the active $-8.0\%$ downhill fogged haul ramp.
- **Baseline B0 Mean:** $725.4\text{ seconds}$ per run.
- **Treatment B1 Mean:** $\mathbf{0.0\text{ seconds}}$ per run.
- **Reduction:** **$100.0\%$ reduction in hazardous downhill road waiting** ($p = 1.05 \times 10^{-23}$, paired t-test).
- **Mechanism:** Central orchestration meters entry onto the ramp, holding vehicles whenever fog drops ramp capacity from 4 trucks to 2 trucks.

---

## 12. Staging Waiting
- **Definition:** Controlled dwell time spent holding in flat, safe staging areas at the pit top prior to ramp clearance.
- **Baseline B0 Mean:** $0.0\text{ seconds}$.
- **Treatment B1 Mean:** $382.0\text{ s}$ to $5,726.0\text{ s}$ (depending on fog severity).
- **Mechanism:** When visibility drops below $25.0\text{ m}$, expanded safe headway requires vehicle spacing to increase, causing excess trucks to queue in the staging yard.

---

## 13. Total Waiting
- **Definition:** Sum of hazardous road waiting and controlled staging waiting.
- **Baseline B0 Mean:** $725.4\text{ seconds}$.
- **Treatment B1 Mean:** $382.0\text{ s}$ to $5,726.0\text{ s}$.
- **Finding:** Total waiting is **NON-ZERO**. The system does not eliminate total waiting when fog slows the mine; it **relocates** dangerous, uncontrolled queuing off the $-8\%$ downhill ramp into a safe, flat staging yard.

---

## 14. Throughput Definition
- **Measured Value:** $5,796.0\text{ Tonnes}$ over a 2-hour simulation ($2,898.0\text{ TPH}$).
- **Formal Definition:** **Modeled Completed Haulage Tonnage (Multi-Bay Unconstrained)**.
- **Reconciliation with Crusher Bottleneck ($1,647.0\text{ TPH}$):**  
  The benchmark models pit-to-dump road haulage discharging into unconstrained multi-bay dump areas with a 90-second tipping cycle. It represents free-flowing road transit capacity ($36\text{ dumps/hr} \times 80.5\text{ t} = 2,898\text{ TPH}$). It cannot be fed continuously into a single-pocket primary gyratory crusher (which has a 200s slot bottleneck limiting intake to $1,647\text{ TPH}$ at $91.5\text{ t}$ or $1,449\text{ TPH}$ at $80.5\text{ t}$) without creating massive stationary queues at the crusher apron.

---

## 15. Payload Provenance
- **Canonical Factory Rating:** **$91.5\text{ tonnes}$** ($91,500\text{ kg}$) — BEML BH100 OEM certified payload ($74.0\text{ t}$ tare $+ 91.5\text{ t}$ payload $= 165.5\text{ t}$ GVW, Tier L2).
- **Benchmark Operational Spec:** **$80.5\text{ tonnes}$** ($80,500\text{ kg}$) — NMDC Bailadila Deposit-5 heavy abrasive rock-box wear liner configuration ($85.0\text{ t}$ tare $+ 80.5\text{ t}$ payload $= 165.5\text{ t}$ GVW, Tier L6).
- **Physical Invariance:** Braking deceleration $a_{\text{dec}}$ and stopping distance depend strictly on **Gross Operating Mass ($165.5\text{ t}$)**. Because both specifications enforce identical GVW, all physical stopping calculations and safe speed envelopes are identical.
- Detailed audit in: `FINAL/PAYLOAD_PROVENANCE.md`.

---

## 16. Statistical Analysis
Pairwise statistical significance was calculated on matched seeds across all 420 paired trials:
- **Stopping Envelope Violations:**  
  Baseline B0 Mean: $1,932.7\text{ violations}$ | Treatment B1 Mean: $910.8\text{ violations}$  
  Paired t-test: $t = 12.87, \quad \mathbf{p = 3.40 \times 10^{-33}}$  
  Wilcoxon signed-rank test: $W = 0.0, \quad \mathbf{p = 3.57 \times 10^{-27}}$
- **Hazardous Downhill Waiting Time:**  
  Baseline B0 Mean: $725.4\text{ s}$ | Treatment B1 Mean: $\mathbf{0.0\text{ s}}$  
  Paired t-test: $t = 10.98, \quad \mathbf{p = 1.05 \times 10^{-23}}$  
  Wilcoxon signed-rank test: $W = 0.0, \quad \mathbf{p = 3.22 \times 10^{-72}}$

---

## 17. Monte Carlo
A 10,000-sample randomized Monte Carlo sweep verified parameter extremes ($\text{Mass} \in [85, 165.5]\text{ t}$, $\text{Grade} \in [-14\%, +14\%]$, $\mu \in [0.15, 0.70]$, $R_{\text{vis}} \in [3, 200]\text{ m}$, $\tau_{\text{total}} \in [0.3, 1.8]\text{ s}$):
- Command Authority Violations ($v_{\text{command}} \le v_{\text{safe}}$): **0 violations** ($100.00\%$ compliance).
- Stopping Margin Invariant under modeled input ($S_{\text{stop}} + S_{\text{base}} \le R_{\text{effective}}$): **0 violations**.
- *Note:* This Monte Carlo validates the safety governor under the modeled environmental input; it does not validate detection of sensor misrepresentation.

---

## 18. HIL Evidence
Reusing the Phase 8 HIL framework (`tests/test_phase8_hil.py`):
- 60 out of 60 test cases passed.
- Communication link severance correctly triggers Level 1 governor fallback within $1.0\text{ s}$ watchdog timeout.
- Data health state transitions execute on physical ESP32 microcontrollers in $< 1.15\text{ ms}$.

---

## 19. Hardware Evidence
Every claim is strictly partitioned:
- **ESP32 Microcontroller & MPU6050 IMU:** Bench Measured (Tier L7).
- **TRUCK_01 Speed:** LM393 Optical Pulse Encoder (Tier L7).
- **TRUCK_02 Speed:** PWM-derived motor velocity (Tier L9 Synthetic; NOT an encoder measurement).
- **GNSS:** Completely absent on prototype (`GNSS_EQUIPPED_VEHICLES = frozenset()`).
- **BEML BH100 Dynamics:** Analytically modeled (Tier L2/L9); no physical truck brakes actuated.

---

## 20. Prior Art
- Prior art in mining HEMM focuses on autonomous collision avoidance (ASAMS) via expensive onboard LiDAR/radar or macro-FMS scheduling.
- The FOG-ORCHESTRATOR 2.0 contribution is an **engineering systems integration contribution**: creating an auditable, rule-based data-health link that dynamically scales stopping envelopes and migrates queues into staging areas without requiring opaque neural networks.

---

## 21. Standards Relevance
- **ISO 17757:2019:** Design informed by supervisory and perception integrity principles (Clause 4.3). Not certified.
- **ISO 19014:2018:** Functional safety diagnostic coverage principles applied. Not certified.
- **IEC 61508:** Class C failure analyzed as $\lambda_{\text{DU}}$ (Dangerous Undetected). Fail-closed architecture enforced.
- **SAE J1939:** CAN PGNs 65265 and 61444 analyzed as candidate deployment interfaces.

---

## 22. Limitations
1. **Class C (Plausible-But-Wrong):** Single-source data health cannot detect an internally consistent lie without an independent reference.
2. **Stuck-At False Alarms:** In truly invariant fog lasting $> 300\text{ s}$, the stuck-at check applies a conservative 30% penalty.
3. **Simulation Boundary:** Fleet throughput and vehicle dynamics are demonstrated in simulation, not field-measured in an active mine pit.
4. **Transient Grace Period:** During the 120s timeout budget, residual stopping violations can occur during sudden fog onset.

---

## 23. Threats to Validity
- **Construct Validity:** True optical scatter in open-pit coal dust may deviate from idealized Gaussian visibility profiles.
- **Internal Validity:** Simulated communication latency modeled as deterministic steps rather than multi-path Rayleigh fading.
- **External Validity:** Human operator compliance to speed advisories in real low visibility is unmeasured.

---

## 24. Research Contribution
We demonstrate a bounded, auditable rule-based data-health mechanism that propagates detectable telemetry degradation into a physics-constrained local safety governor and fleet-orchestration layer, while explicitly characterizing the observability boundary of single-source sensing.

---

## 25. Hostile Judge Questions
All 20 adversarial challenges are resolved in `FINAL/SENSOR_DEGRADATION_JUDGE_QA.md`, including mathematical proofs of D6/D13 observability limits, why AI was rejected, and why 80.5t operational payload was chosen.

---

## 26. Demo
A deterministic 90-second demonstration sequence proves the complete causal chain:
$$\text{Sensor Fault Injection} \to \text{Data Health Transition} \to \text{Conservative } R_{\text{eff}} \to v_{\text{safe}} \text{ Clamping} \to \text{Staging Holding}$$

---

## 27. Final Verdict
$$\mathbf{GRADE\ B\ —\ VALIDATED\ WITH\ LIMITATIONS}$$
The architecture demonstrates complete mathematical and empirical command-authority invariant closure ($v_{\text{command}} \le v_{\text{safe}}$) under all tested conditions, and completely eliminates hazardous downhill road waiting ($725.4\text{ s} \to 0.0\text{ s}$). Grade B is awarded because single-source Class C faults are mathematically unresolvable without redundant sensors, and field trials remain future work.

---

## 28. Required Field Experiment
1. Deploy dual cross-path optical transmissometers on an active NMDC iron ore haul road bench to measure spatial variance.
2. Intercept BEML BH100 CAN bus via isolated hardware logger to record authentic J1939 PGN broadcast rates.
3. Measure RF packet loss in active pit highwall switchbacks under real dust and moisture conditions.
