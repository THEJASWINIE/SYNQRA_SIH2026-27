# FINAL SCIENTIFIC FORENSIC AUDIT
## FOG-ORCHESTRATOR 2.0 — Comprehensive Architectural & Verification Path Trace
**Project:** SIH26007 — Fog & Low-Visibility Mining Fleet Orchestrator  
**Audit Date:** 2026-09-21  
**Lead Auditor:** Systems Architect & Safety-Critical Verification Auditor  
**Audit Standard:** Forensic Traceability Protocol (§1)

---

## 1. Complete Path Traceability Matrix

### 1. Implementation Path
- **Core Module:** [`integration_adapters/environmental_data_health.py`](file:///c:/Users/JAGADEESH%20M/OneDrive/Documents/SIH-2026-27/integration_adapters/environmental_data_health.py)
  - Exports: `DataState`, `FaultCode`, `ValidatedSignal`, `EnvironmentalHealthConfig`, `EnvironmentalDataHealth`, `VehicleDataHealth`, `DataHealthManager`.
  - Exported through: [`integration_adapters/__init__.py`](file:///c:/Users/JAGADEESH%20M/OneDrive/Documents/SIH-2026-27/integration_adapters/__init__.py).
  - Scope: Bounded, rule-based diagnostic layer. Zero ML / DL dependencies. Evaluates checks H1–H6.

### 2. Benchmark Execution Path
- **Benchmark Script:** [`experiments/run_sensor_degradation_benchmark.py`](file:///c:/Users/JAGADEESH%20M/OneDrive/Documents/SIH-2026-27/experiments/run_sensor_degradation_benchmark.py)
  - Scale: 14 scenarios ($D0$–$D13$) $\times$ 30 matched seeds ($0$–$29$) $\times$ 2 system modes ($B0$ vs. $B1$) = 840 simulation runs.
  - Simulation Horizon: $7200\text{ s}$ ($2.0\text{ hours}$) per run at $1.0\text{ s}$ discrete timestep.
  - Reproducibility Manifest: [`FINAL/SENSOR_DEGRADATION_REPRODUCIBILITY.yaml`](file:///c:/Users/JAGADEESH%20M/OneDrive/Documents/SIH-2026-27/FINAL/SENSOR_DEGRADATION_REPRODUCIBILITY.yaml).

### 3. Canonical Safety Path
- **Physics Solver:** [`fog_safe/safety.py`](file:///c:/Users/JAGADEESH%20M/OneDrive/Documents/SIH-2026-27/fog_safe/safety.py)
  - Method: `solve_safe_speed(vehicle, road, env, comm, mu_effective, r_effective)`
  - Constraint: $v_{\text{safe}} = \min(v_{\text{stop}}, v_{\text{retarder}}, v_{\text{traction}}, v_{\text{curve}}, v_{\text{mine}})$.
  - Analytical Stopping Solver: Model 6 quadratic solution for $(v \cdot \tau_{\text{total}}) + \frac{v^2}{2 a_{\text{dec}}} + S_{\text{base}} \le R_{\text{effective}}$.
- **Local Vehicle Safety Governor:** [`fog_orchestrator/core/safety_governor.py`](file:///c:/Users/JAGADEESH%20M/OneDrive/Documents/SIH-2026-27/fog_orchestrator/core/safety_governor.py)
  - Authority: Level 1 Supreme Authority. Clamps any external speed request to $v_{\text{applied}} = \min(v_{\text{command}}, v_{\text{safe}})$.

### 4. Data-Health Ingestion Path
- **Ingestion Contract:** `EnvironmentalDataHealth.update(visibility_m, timestamp, sequence, source_id, secondary_visibility_m) -> ValidatedSignal`
- **Fallback Ingestion Contract:** `EnvironmentalDataHealth.get_current_health() -> Tuple[r_effective, DataState, confidence]`
- **Scaling Rules:**
  - `HEALTHY` $\implies R_{\text{effective}} = R_{\text{raw}}$
  - `DEGRADED` $\implies R_{\text{effective}} = \max(5.0\text{ m}, R_{\text{raw}} \times 0.70)$
  - `STALE` $\implies R_{\text{effective}} = \max(5.0\text{ m}, R_{\text{raw\_last}} \times 0.50)$
  - `CONFLICTING` $\implies R_{\text{effective}} = \max(5.0\text{ m}, \min(R_1, R_2) \times 0.70)$
  - `UNAVAILABLE` $\implies R_{\text{effective}} = 8.0\text{ m}$ (Crawling floor)

### 5. Fault Injection Path
- **Injection Point:** `experiments/run_sensor_degradation_benchmark.py::simulate_scenario()` lines 190–233.
- **Fault Taxonomy:**
  - $D0$: Nominal clear air ($50\text{ m}$).
  - $D1$–$D4$: Bernouilli packet drops ($10\%$, $25\%$, $50\%$, $75\%$).
  - $D5$: Link freeze at $t=1800\text{ s}$ during sudden fog influx ($12\text{ m}$).
  - $D6$: Constant stuck signal ($45\text{ m}$) during fog ($12\text{ m}$).
  - $D7$: Additive offset $+30\text{ m}$ during fog.
  - $D8$: Zero-mean Gaussian noise $\mathcal{N}(0, 25^2)$.
  - $D9$: Dual sensor divergence ($50\text{ m}$ vs. $15\text{ m}$).
  - $D10$: Periodic 40s drop / 20s active cycle during fog.
  - $D11$: Uplink severance at $t=1800\text{ s}$.
  - $D12$: Complete blackout from $t=0$.
  - $D13$: Class C plausible-but-wrong ($50\text{ m}$ reported, $5\text{ m}$ true).

### 6. Metric Calculation Path
- **Stopping Violations:** Evaluated against ground-truth visibility:
  $$\text{Violations} = \sum_{t=0}^{T} \mathbb{I}\left( S_{\text{stop}}(v_{\text{command}}, a_{\text{dec}}, \tau) + S_{\text{base}} > R_{\text{vis\_true}}(t) \right)$$
- **Command Overspeed Violations:** Evaluated against safe envelope:
  $$\text{Violations} = \sum_{t=0}^{T} \mathbb{I}\left( v_{\text{command}} > v_{\text{safe}} + 10^{-6} \right)$$
- **Hazardous Ramp Waiting:** Dwell time stopped on the active $-8.0\%$ downhill ramp ($1200\text{ m}$).
- **Staging Waiting:** Dwell time held safely in the top flat staging area.
- **Completed Haulage Tonnage:**
  $$\text{Tonnage} = \text{Trips Completed} \times 80.5\text{ Tonnes}$$

### 7. Result Aggregation Path
- **Raw Run Records:** [`sensor_degradation_research/RESULTS.csv`](file:///c:/Users/JAGADEESH%20M/OneDrive/Documents/SIH-2026-27/sensor_degradation_research/RESULTS.csv) and [`FINAL/SENSOR_DEGRADATION_RESULTS.csv`](file:///c:/Users/JAGADEESH%20M/OneDrive/Documents/SIH-2026-27/FINAL/SENSOR_DEGRADATION_RESULTS.csv) (840 rows).
- **Scenario Summary:** [`sensor_degradation_research/SCENARIO_RESULTS.csv`](file:///c:/Users/JAGADEESH%20M/OneDrive/Documents/SIH-2026-27/sensor_degradation_research/SCENARIO_RESULTS.csv) (28 rows: 14 scenarios $\times$ 2 modes).
- **Statistical Significance Tests:** Paired t-tests and Wilcoxon signed-rank tests across 420 matched seed pairs.

---

## 2. Reconciled Contradiction Ledger

| Item | Previous Ambiguity / Conflict | Reconciled Forensic Reality | Section Trace |
|---|---|---|---|
| **D5 Residual Violations** | Stated as "120 violations remain during transition" without proving timeline | Reconciled: 120 violations correspond exactly to $T_{\text{GRACE}} = 120.0\text{ s}$ timeout window before crawling floor. Genuine physical violation window, not an accounting bug. | §3, `FINAL_D5_D13_FORENSIC_AUDIT.md` |
| **D6 Failure** | Stated as 3601 violations despite H5 stuck-at detector existing | Reconciled: Single-source variance cannot determine ground truth. Even if flagged DEGRADED, $0.70 \times 45\text{ m} = 31.5\text{ m} > 12\text{ m}$. Preserved as permanent negative result. | §4, `FINAL_D5_D13_FORENSIC_AUDIT.md` |
| **D7 Failure** | Stated as 3601 violations | Reconciled: Additive bias with valid variance is Class C unobservable without redundant physical sensors. | §5, `FINAL_D5_D13_FORENSIC_AUDIT.md` |
| **D10 Violations** | Stated as 40 violations in both B0 and B1 | Reconciled: Violations occur exclusively during the first 40s drop window when fog rolled in before telemetry arrived. | §8, `FINAL_D5_D13_FORENSIC_AUDIT.md` |
| **Throughput Semantics** | Termed "throughput" which could be confused with single-pocket crusher ceiling (1647 TPH) | Reconciled: Explicitly defined as "Modeled Completed Haulage Tonnage" across unconstrained fleet cycle, not single-pocket crusher bottleneck. | §10, `FINAL_FORENSIC_AUDIT.md` |
| **Hazardous Waiting** | Stated as "Waiting reduced by 100%" | Reconciled: Hazardous ramp waiting reduced to $0.0\text{ s}$; waiting was relocated into controlled staging. Total waiting is non-zero. | §11, `FINAL_FORENSIC_AUDIT.md` |
