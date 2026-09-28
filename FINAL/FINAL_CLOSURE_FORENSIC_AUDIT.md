# FINAL CLOSURE FORENSIC AUDIT
## FOG-ORCHESTRATOR 2.0 / SIH26007 — Sensor Degradation Research Extension

**Document Status:** AUTHORITATIVE EVIDENCE FREEZE  
**Evaluation Date:** 2026-09-21  
**Auditor:** Principal Safety-Critical Systems Auditor, Simulation Validator & Scientific Evidence Reviewer  
**Classification:** Research Audit & Scientific Review Artifact  

---

### 1. Current Research Architecture

The FOG-ORCHESTRATOR 2.0 system implements a strict, non-negotiable 5-tier safety and orchestration hierarchy. The Data-Health Layer is strictly diagnostic; it operates as an input validation pre-filter for the Digital Twin and NEVER holds actuator, throttle, or steering authority:

```
ENVIRONMENT / VEHICLE TELEMETRY
            ↓
    DATA HEALTH LAYER (H1–H6)
  [Diagnostic Validation & Fail-Closed]
            ↓
     VALIDATED TWIN STATE
 [Conservative Effective Visibility R_eff]
            ↓
       VEHICLE PHYSICS
  [Tire-Road Friction, Mass, Slope, Aero]
            ↓
  LOCAL SAFETY GOVERNOR (Level 1)
       [v_safe Solver — SUPREME]
            ↓
     ROAD CAPACITY CONTROLLER
  [Headway Expansion & Ramp Metering]
            ↓
   QUEUE / BOTTLENECK CONTROLLER
 [Holding Trucks in Safe Level Staging]
            ↓
    CENTRAL FLEET ORCHESTRATION
 [Slot Allocation & Route Optimization]
            ↓
      VEHICLE ACTUATION
[Local Governor Enforces v_command <= v_safe]
```

#### Authority Ordering:
$$\text{LOCAL SAFETY GOVERNOR} > \text{ROAD INFRASTRUCTURE} > \text{CENTRAL ORCHESTRATION} > \text{DISPATCH OPTIMIZATION}$$

---

### 2. Current Data-Health Implementation (H1–H6)

The data health pre-filter is implemented in `integration_adapters/environmental_data_health.py` as an entirely deterministic, auditable, rule-based state machine without black-box AI/ML or Kalman filters:

- **Check H1 (Freshness & Staleness):** Evaluates elapsed arrival time against thresholds:
  - $\Delta t \le T_{\text{DEGRADED}} (30.0\text{ s}) \implies \text{HEALTHY}$ ($R_{\text{eff}} = R_{\text{raw}}$)
  - $30.0\text{ s} < \Delta t \le T_{\text{STALE}} (60.0\text{ s}) \implies \text{DEGRADED}$ ($R_{\text{eff}} = 0.70 \times R_{\text{raw}}$)
  - $60.0\text{ s} < \Delta t \le T_{\text{GRACE}} (120.0\text{ s}) \implies \text{STALE}$ ($R_{\text{eff}} = 0.50 \times R_{\text{last\_valid}}$)
  - $\Delta t > T_{\text{GRACE}} (120.0\text{ s}) \implies \text{UNAVAILABLE}$ ($R_{\text{eff}} = 8.0\text{ m}$ crawling floor)
- **Check H2 (Schema & Numeric Validity):** Rejects non-numeric types, `NaN`, and `Inf` instantaneously into `UNAVAILABLE`.
- **Check H3 (Physical Plausibility Bounds):** Strictly enforces $V_{\text{min}} = 1.0\text{ m} \le R \le V_{\text{max}} = 300.0\text{ m}$.
- **Check H4 (Sequence Monotonicity & Replay Detection):** Bounded history tracker rejects non-positive sequence deltas.
- **Check H5 (Signal Dynamics & Stuck-at Signal Detection):** Rolling 10-sample window monitors standard deviation. If $\sigma < 0.05\text{ m}$ for $t > 300.0\text{ s}$, detects constant/stuck-at signal behavior.
- **Check H6 (Multi-Source Cross-Consistency):** Compares primary and secondary visibility sensors. If $|R_1 - R_2| > 25.0\text{ m}$, selects $R_{\text{eff}} = 0.70 \times \min(R_1, R_2)$.

---

### 3. Current Benchmark Configuration

- **Simulation Engine:** `experiments/run_sensor_degradation_benchmark.py`
- **Simulation Horizon:** $7,200.0\text{ seconds}$ ($2.0\text{ hours}$) per run
- **Fleet Size:** 6 BEML BH100 heavy haul dumpers
- **Haul Road Geometry:** $1,200.0\text{ m}$ length, continuous $-8.0\%$ downhill grade (empty return at $+8.0\%$)
- **Pavement Friction:** $\mu_{\text{effective}} = 0.35$ (wet unpaved haul road)
- **Nominal Visibility:** $50.0\text{ m}$ clear air; fog bank rolls in at $t=1800.0\text{ s}$ to $t=5400.0\text{ s}$ ($12.0\text{ m}$ in D5–D7, $15.0\text{ m}$ in D9, $20.0\text{ m}$ in D10, $5.0\text{ m}$ in D13)
- **Replication Scale:** 14 Scenarios (D0–D13) $\times$ 30 Matched Random Seeds $\times$ 2 Modes (B0 Unmonitored vs B1 Health-Aware) $= \mathbf{840\text{ Full Closed-Loop Simulation Runs}}$
- **Statistical Significance:** Evaluated using two-tailed paired Student's t-tests and Wilcoxon signed-rank tests ($p < 10^{-20}$).

---

### 4. Safety Invariant Definitions: Command Authority vs True Stopping Envelope

A fundamental scientific requirement of this audit is the strict formal separation of the two safety invariants:

#### Invariant A — Command Authority Invariant
$$\mathbf{v_{\text{command}} \le v_{\text{safe}}(R_{\text{reported}})}$$
- **Scope:** Verifies that the Level 1 `LocalVehicleSafetyGovernor` strictly clamps any speed command requested by the central fleet orchestrator to the mathematically solved safe speed $v_{\text{safe}}$.
- **Measurement:** Evaluated at every simulation second against the reported and validated state.
- **Audited Outcome:** **0 command-authority violations** across all 840 simulation runs and all 10,000 Monte Carlo randomized trials.

#### Invariant B — Physical Stopping Envelope Invariant
$$\mathbf{S_{\text{stop}}(v_{\text{command}}) + S_{\text{base}} \le R_{\text{true}}}$$
- **Scope:** Verifies whether the actual stopping distance required by the vehicle under maximum service braking ($a_{\text{dec}}$) and total lag ($\tau_{\text{total}} = 0.8\text{ s}$), plus base bumper buffer ($S_{\text{base}} = 5.0\text{ m}$), is strictly less than or equal to the **true physical environmental visibility** ($R_{\text{true}}$).
- **Measurement:** Evaluated strictly against the simulator's hidden ground-truth atmospheric state.
- **Audited Outcome:** Identifies the precise physical observability boundary when sensors misreport reality.

#### The Authoritative Invariant Separation Table (Averaged across 30 Matched Seeds):

| Scenario ID | Degradation Description | B0 Command Violations | B1 Command Violations | B0 True Envelope Violations | B1 True Envelope Violations | Causal Interpretation |
|---|---|---|---|---|---|---|
| **D0_nominal** | Clear air (50m constant) | 0 | 0 | 0.0 | 0.0 | Both invariants fully satisfied. |
| **D1_dropout_10** | 10% random packet drops | 0 | 0 | 0.0 | 0.0 | Absorbed by freshness buffer ($T_{\text{deg}} = 30\text{s}$). |
| **D2_dropout_25** | 25% random packet drops | 0 | 0 | 0.33 | 0.33 | Transient drops; negligible envelope impact. |
| **D3_dropout_50** | 50% random packet drops | 0 | 0 | 0.93 | 0.93 | Occasional brief degradation scaling. |
| **D4_dropout_75** | 75% random packet drops | 0 | 0 | 3.53 | 3.53 | Frequent 0.70 scaling; minor queue in staging. |
| **D5_stale_env** | Telemetry dies at fog entry | 0 | 0 | 3,601.0 | 120.0 | **96.7% mitigation.** 120 residual violations correspond to 120s timeout transition. |
| **D6_stuck_at** | Sensor stuck at 45m (true 12m) | 0 | 0 | 3,601.0 | 3,601.0 | **Negative Result.** Constant signal detected, but single sensor cannot observe true 12m. |
| **D7_biased_sensor** | Sensed = True + 30m | 0 | 0 | 3,601.0 | 3,601.0 | **Class C Unobservable.** Valid schema, fresh data, plausible range; physically invisible. |
| **D8_noisy_sensor** | Gaussian $\sigma=25\text{m}$ noise | 0 | 0 | 1,805.6 | 1,663.5 | **7.9% reduction.** Dynamic throttling dampens noise spikes; modest physical improvement. |
| **D9_conflicting** | Dual sources (50m vs 15m) | 0 | 0 | 3,601.0 | 0.0 | **100% elimination.** Redundant sensor divergence resolved conservatively via $\min(R_1, R_2)$. |
| **D10_intermittent** | 40s drop / 20s active cycle | 0 | 0 | 40.0 | 40.0 | **Negative Result.** 40 violations occur solely during initial 40s drop window before 20m packet. |
| **D11_comm_loss** | Central comms severed at $t=1800$ | 0 | 0 | 3,601.0 | 120.0 | **96.7% mitigation.** Identical to D5; local governor enforces 8m floor independently. |
| **D12_complete_loss** | Zero telemetry from start | 0 | 0 | 3,601.0 | 0.0 | **100% elimination.** Fails closed immediately to 8.0m floor ($v_{\text{safe}} = 9.7\text{ km/h}$). |
| **D13_plausible_wrong**| Reported 50m (true 5m) | 0 | 0 | 3,601.0 | 3,601.0 | **Class C Unobservable.** Single-source data cannot detect internally consistent false telemetry. |

---

### 5. D5–D13 Causal Forensic Analysis

#### D5: Stale Telemetry Link Freeze (120 Residual Violations)
- **Event Timeline (Seed 0):** At $t=1800.0\text{ s}$, telemetry packets cease completely while ground-truth visibility drops from $50.0\text{ m} \to 12.0\text{ m}$.
- **Transition Stages:**
  - $t \in [1800, 1830)\text{ s}$ ($\Delta t \le 30\text{s}$): HEALTHY ($R_{\text{eff}} = 50.0\text{ m}, v_{\text{safe}} = 40.0\text{ km/h}$).
  - $t \in [1830, 1860)\text{ s}$ ($30\text{s} < \Delta t \le 60\text{s}$): DEGRADED ($R_{\text{eff}} = 35.0\text{ m}, v_{\text{safe}} = 39.0\text{ km/h}$).
  - $t \in [1860, 1920)\text{ s}$ ($60\text{s} < \Delta t \le 120\text{s}$): STALE ($R_{\text{eff}} = 25.0\text{ m}, v_{\text{safe}} = 30.6\text{ km/h}$).
  - $t \ge 1920\text{ s}$ ($\Delta t > 120.0\text{ s}$): UNAVAILABLE ($R_{\text{eff}} = 8.0\text{ m}, v_{\text{safe}} = 9.7\text{ km/h}$).
- **Causal Proof:** At $R_{\text{eff}} = 50\text{m}, 35\text{m}, 25\text{m}$, the required stopping distance exceeds $12.0\text{ m}$. At $t \ge 1920\text{ s}$, $R_{\text{eff}} = 8.0\text{ m} \implies S_{\text{stop}} + S_{\text{base}} = 8.0\text{ m} \le 12.0\text{ m}$. The remaining **120 violations** are genuine physical stopping violations during the configured 120s grace period, NOT an accounting bug.

#### D6: Stuck-at Constant Telemetry (3,601 Violations)
- Sensed signal remains constant at $45.0\text{ m}$ while true visibility drops to $12.0\text{ m}$.
- **Terminology Rule:** "Constant/stuck-at signal detection" is permitted. "Sensor proven faulty" is **FORBIDDEN** without an independent reference.
- Check H5 detects $\sigma = 0.0$ after 300 seconds and drops state to DEGRADED ($0.70 \times 45.0\text{ m} = 31.5\text{ m}$). However, because $31.5\text{ m} > 12.0\text{ m}$, stopping envelope violations continue unabated. Single-source signal processing cannot reconstruct missing atmospheric reality.

#### D7: Systematic Calibration Bias (+30m)
- True visibility $= 12.0\text{ m}$; reported visibility $= 42.0\text{ m}$.
- Timestamp is fresh, sequence is monotonic, range $[1, 300]\text{ m}$ is valid, variance is natural.
- **Authoritative Classification:** **CLASS C — PLAUSIBLE / SYSTEMATICALLY WRONG SINGLE-SOURCE DATA**. Persistent systematic bias is mathematically unobservable from a single internally consistent stream.

#### D8: Gaussian Atmospheric Noise ($\sigma = 25.0\text{ m}$)
- High noise variance trips H5 into DEGRADED, throttling $R_{\text{eff}} \times 0.70$.
- Stopping violations drop from $1,805.6 \to 1,663.5$ (**7.9% reduction**). The improvement is modest because heavily filtering noise introduces phase delay during genuine fog transitions.

#### D9: Dual Conflicting Optical Transmissometers
- Source 1 reports $50.0\text{ m}$; Source 2 reports $15.0\text{ m}$ ($|50 - 15| = 35.0\text{ m} > 25.0\text{ m}$).
- Check H6 triggers `CONFLICTING` at $t=1801.0\text{ s}$, applying:
  $$R_{\text{eff}} = 0.70 \times \min(R_1, R_2) = 0.70 \times 15.0 = \mathbf{10.5\text{ m}}$$
- Since $10.5\text{ m} \le 15.0\text{ m}$, stopping violations drop to **0.0 (100% elimination)**.
- **Evidence Boundary Note:** These are **simulated independent sources**, not field-validated physical hardware sensors.

#### D10: Intermittent Wireless Dropout (40s Drop / 20s Alive)
- **Causal Mechanism Proven in `FINAL/D10_TRACE_SEED_0.csv`:**
  - Fog arrives at $t=1800.0\text{ s}$ ($R_{\text{true}} = 20.0\text{ m}$), exactly when the transmitter enters its 40s silence window ($t \in [1800, 1840)\text{ s}$).
  - For 40 seconds, B1 holds $50.0\text{ m}$ ($t=1800..1829$) then degrades to $35.0\text{ m}$ ($t=1830..1839$), both exceeding $20.0\text{ m}$.
  - At $t=1840.0\text{ s}$, the first $20.0\text{ m}$ packet arrives. $R_{\text{eff}}$ drops to $14.0\text{ m} \le 20.0\text{ m}$.
  - For the remaining 3,560 seconds, even during subsequent 40s dropouts, the latched value is $\le 20.0\text{ m}$, yielding zero violations.
  - All 40 violations occur strictly during that initial 40s drop window. B1 cannot improve over B0 because $T_{\text{DEGRADED}} = 30\text{ s}$ and $T_{\text{STALE}} = 60\text{ s}$ do not scale down to $\le 20\text{ m}$ within 40 seconds.

#### D11: RF Uplink Severance to Central Server
- Severance at $t=1800.0\text{ s}$. Local `LocalVehicleSafetyGovernor` continues running on onboard ECU.
- After 120s grace period, local governor drops to $8.0\text{ m}$ crawl floor independently of central server.
- **Proved Hierarchy:** Loss of central communication does NOT cause runaway unsafe motion; local safety remains autonomous and supreme.

#### D12: Complete Environmental Blackout from Initialization
- Transmissometer completely offline from $t=0$.
- Ingestor initializes directly in `UNAVAILABLE`, enforcing $R_{\text{eff}} = 8.0\text{ m}$ ($v_{\text{safe}} = 9.7\text{ km/h}$).
- **0 stopping violations (100% elimination)** throughout the entire 2-hour run.

#### D13: Plausible-But-Wrong Single-Source Obscuration (Class C)
- Reported $= 50.0\text{ m}$; Ground Truth $= 5.0\text{ m}$.
- All syntactic, temporal, and statistical sanity checks pass.
- **Audit Verdict:** The failure to detect D13 is **PRESERVED AS A FUNDAMENTAL RESEARCH LIMITATION**. Single-source sensing mathematically cannot detect a false report that falls within plausible physical limits.

---

### 6. Payload Provenance Reconciliation

- **Canonical Specification:** **$91.5\text{ tonnes}$** ($91,500\text{ kg}$) — BEML BH100 OEM certified payload ($74.0\text{ t}$ tare $+ 91.5\text{ t}$ payload $= 165.5\text{ t}$ GVW, Tier L2).
- **Sensor Degradation Benchmark:** **$80.5\text{ tonnes}$** ($80,500\text{ kg}$) — NMDC Deposit-5 heavy abrasive rock body liner configuration ($85.0\text{ t}$ tare $+ 80.5\text{ t}$ payload $= 165.5\text{ t}$ GVW, Tier L6).
- **Invariance Proof:** Both configurations enforce identical loaded mass ($165.5\text{ t}$), ensuring vehicle deceleration, stopping distances, and safe speed calculations are identical.
- Documented in: `FINAL/PAYLOAD_PROVENANCE.md`.

---

### 7. Throughput Semantics Reconciliation

- **Headline Value:** $5,796.0\text{ Tonnes}$ over 2 hours ($2,898.0\text{ TPH}$).
- **Exact Formulation:** $\text{Trips Completed} \times 80.5\text{ Tonnes} = 72 \times 80.5 = 5,796.0\text{ t}$.
- **Precise Name:** **"Modeled Completed Haulage Tonnage"**.
- **Reconciliation with Crusher Bottleneck ($1,647.0\text{ TPH}$):**  
  The benchmark models unconstrained multi-bay open tipping with a 90-second dump cycle per truck. It represents pit-to-dump road transit capacity. It cannot be fed continuously into a single-pocket primary gyratory crusher (which has a 200s slot bottleneck limiting intake to $1,647\text{ TPH}$ at $91.5\text{ t}$ or $1,449\text{ TPH}$ at $80.5\text{ t}$).
- Documented in: `FINAL/THROUGHPUT_DEFINITION.md`.

---

### 8. Waiting-Time Semantics: Hazardous vs Staging Waiting

The benchmark separately quantifies:
1. **Hazardous Ramp Waiting:** Time spent stopped in unmanaged queues on the $-8.0\%$ downhill fogged haul road.
   - B0 Unmonitored: $250.0\text{ s}$ to $5,726.0\text{ s}$ (Mean: $725.4\text{ s}$).
   - B1 Health-Aware: $\mathbf{0.0\text{ s}}$ across all 14 scenarios (**100% reduction in hazardous road waiting**, $p < 10^{-22}$).
2. **Controlled Staging Waiting:** Time spent holding in flat, safe staging areas at the pit top before ramp dispatch.
   - B0: $0.0\text{ s}$.
   - B1: $382.0\text{ s}$ to $5,726.0\text{ s}$.
3. **Total Waiting:** Sum of hazardous and staging waiting.
   - Total waiting is **NON-ZERO**. The system does not magically eliminate waiting when dense fog restricts ramp throughput; it **relocates** dangerous stationary queues off the haul ramp into safe holding zones.

---

### 9. Evidence Boundary (Tiers L1–L10)

All claims are classified strictly per the Evidence Boundary framework:
- **Tier L2 (OEM Documented):** BEML BH100 tare ($74\text{t}$), GVW ($165.5\text{t}$), dimensions ($10.52\text{m} \times 5.52\text{m}$).
- **Tier L6 (Engineering Assumption):** Health thresholds ($T_{\text{deg}}=30\text{s}, T_{\text{stale}}=60\text{s}, T_{\text{grace}}=120\text{s}, R_{\text{floor}}=8\text{m}$), heavy-tare chassis ($85\text{t}$ tare, $80.5\text{t}$ payload).
- **Tier L7 (Bench Measured):** ESP32 packet serialization, SPI/UART latency ($<5\text{ms}$), deduplication ring buffer.
- **Tier L9 (Simulation):** 14-scenario degradation benchmark, fleet queuing, closed-loop safety envelope evaluation.
- **NOT FIELD VALIDATED:** No physical BEML BH100 brake line was actuated; no active open-cast mine trial was executed; no native OEM J1939 CAN bus was tapped.

---

### 10. Remaining Scientific Limitations

1. **Plausible-but-Wrong Telemetry (Class C):** A single sensor reporting false clear air within valid ranges cannot be detected without independent redundant hardware.
2. **Stuck-at Without Reference (D6):** Zero variance flags constant signals, but cannot reconstruct ground truth.
3. **Transient Grace Period Risk (D5/D11):** The 120s timeout budget permits 120s of residual stopping violations during sudden fog onset.
4. **Single-Source Bias (D7):** Constant offsets are invisible to single-stream statistical filters.
5. **No Independent Optical Reference:** Optical transmissometer accuracy degrades in dust/rain mixtures.

---

### 11. Final Research Verdict

$$\mathbf{GRADE\ B\ —\ VALIDATED\ WITH\ LIMITATIONS}$$

The research demonstrates an auditable, rule-based data-health architecture that successfully closes the causal loop between telemetry degradation, vehicle physics, and fleet orchestration, achieving 100% elimination of hazardous downhill waiting and full command-authority compliance ($v_{\text{command}} \le v_{\text{safe}}$), while honestly characterizing the fundamental observability limits of single-source sensing.
