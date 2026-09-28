# PHASE 7.3.4 — REPRODUCIBILITY FROM CLEAN STATE AUDIT
## FOG-ORCHESTRATOR 2.0 — SIH26007 / NMDC BAILADILA IRON ORE COMPLEX

---

### Executive Summary

As part of the hostile Phase 7.3.4 adversarial audit, this document establishes the protocol for **clean-state zero-manual-intervention reproduction** of all headline findings, statistical distributions, physical force derivations, and benchmark datasets.

Any external evaluator or peer reviewer must be able to clone the repository onto an air-gapped or fresh computing environment, execute a single set of standardized shell commands, and reproduce every headline figure within numerical floating-point tolerances ($< 10^{-6}$ relative error).

---

### 1. System Requirements & Environment Baseline

| Component | Minimum Specification | Audited Configuration | Notes |
| :--- | :--- | :--- | :--- |
| **Operating System** | Linux (Ubuntu 22.04+) or Windows 10/11 | Windows 11 Enterprise / x86_64 | Platform-agnostic Python code |
| **Python Runtime** | Python 3.10+ | Python 3.14.0rc2 / CPython 64-bit | Pure Python / standard numerical stack |
| **Core Dependencies** | `numpy>=1.24.0`, `scipy>=1.10.0`, `pandas>=2.0.0`, `pyyaml>=6.0`, `pytest>=7.0.0` | Sourced via standard pip | No closed-source or vendor SDKs |
| **Memory / CPU** | 4 GB RAM / 2 Cores | 16 GB RAM / 8 Cores | Full 30-seed simulation completes in < 25 s |
| **Storage** | 500 MB free space | Workspace local storage | CSV datasets total < 15 MB |

---

### 2. End-to-End Clean State Reproduction Procedure

To regenerate all canonical tables, CSV artifacts, unit test assertions, and adversarial audit outputs, execute the following commands in sequence from the workspace root:

```bash
# -------------------------------------------------------------
# STEP 1: VERIFY RUNTIME ENVIRONMENT & DEPENDENCIES
# -------------------------------------------------------------
python --version
pip install -r requirements.txt  # numpy, scipy, pandas, pyyaml, pytest

# -------------------------------------------------------------
# STEP 2: RUN CANONICAL UNIT & INTEGRATION TEST REGRESSION SUITE
# Verifies all 888 system assertions across physics, safety, queues,
# communication protocols, and adversarial invariants.
# -------------------------------------------------------------
pytest tests/ -v

# -------------------------------------------------------------
# STEP 3: EXECUTE INDEPENDENT FIRST-PRINCIPLES PHYSICS AUDIT
# (Attacks #1, #2, #3, #4, #5, #6, #12, #13, #21, #22, #23, #24, #25)
# Generates:
#   - data/phase7_3_4_adhesion_audit.csv
#   - data/phase7_3_4_deceleration_sensitivity.csv
#   - data/phase7_3_4_service_decel_sensitivity.csv
#   - data/phase7_3_4_safety_buffer_sensitivity.csv
#   - data/phase7_3_4_chattering_audit.csv
#   - data/phase7_3_4_quadratic_grid.csv
#   - data/phase7_3_4_recovery_timeline.csv
# -------------------------------------------------------------
python experiments/run_phase7_3_4_independent_physics.py

# -------------------------------------------------------------
# STEP 4: EXECUTE LONG-HORIZON FLEET SIMULATION & CAUSALITY AUDIT
# (Attacks #9, #10, #11, #26, #27, #28)
# Runs N=30 seeds x 5 levels (7200s, 600s warmup discarded).
# Generates:
#   - data/phase7_3_4_crusher_sensitivity.csv
#   - data/phase7_3_4_30_seeds_reproduction.csv
#   - data/phase7_3_4_statistical_audit.csv
#   - data/phase7_3_4_event_timeline.csv
# -------------------------------------------------------------
python experiments/run_phase7_3_4_independent_throughput.py

# -------------------------------------------------------------
# STEP 5: EXECUTE INDEPENDENT MONTE CARLO & ADVERSARIAL OVERRIDE AUDIT
# (Attacks #14, #15, #20)
# Runs N=10,000 randomized dynamic trials under extreme conditions.
# Generates:
#   - data/phase7_3_4_independent_monte_carlo.csv
#   - data/phase7_3_4_invariants_summary.csv
#   - data/phase7_3_4_packet_loss_audit.csv
#   - data/phase7_3_4_adversarial_central_matrix.csv
# -------------------------------------------------------------
python experiments/run_phase7_3_4_independent_monte_carlo.py

# -------------------------------------------------------------
# STEP 6: EXECUTE PHYSICAL SENSITIVITY & HARDWARE BENCH PROVENANCE AUDIT
# (Attacks #7, #8, #16, #17, #22)
# Generates:
#   - data/phase7_3_4_latency_provenance.csv
#   - data/phase7_3_4_actuator_sensitivity.csv
#   - data/phase7_3_4_brake_provenance.csv
#   - data/phase7_3_4_rf_bench_protocol.csv
#   - data/phase7_3_4_j1939_scoping.csv
#   - data/phase7_3_4_mass_sensitivity.csv
# -------------------------------------------------------------
python experiments/run_phase7_3_4_sensitivity.py

# -------------------------------------------------------------
# STEP 7: EXECUTE FAIL-OPEN STATIC CODE SCAN & CLAIM LANGUAGE AUDIT
# (Attacks #19, #30)
# Scans codebase for silent fallbacks, overclaiming keywords, and unhandled branches.
# Generates:
#   - data/phase7_3_4_fail_open_audit.csv
#   - data/phase7_3_4_claim_language_audit.csv
# -------------------------------------------------------------
python experiments/run_phase7_3_4_adversarial_audit.py
```

---

### 3. Headline Metric Verification Checkpoints

Upon completion of the above commands, verify that the generated CSV outputs match the following canonical values exactly:

#### A. Fleet Throughput (Canonical Experiment: `THROUGHPUT_FINAL_L0_L4_V1`, 7,200 s, 600 s warmup discarded)
- **Baseline (Level 0, Unmanaged Haulage)**:
  - Canonical Throughput: $\mathbf{1,171.2\text{ TPH}}$ (Crusher Utilization: $71.1\%$)
  - 30-Seed Batch Mean: $1,170.29 \pm 25.05\text{ TPH}$
- **Full Orchestration (Level 4, Dynamic Origin Staging)**:
  - Canonical Throughput: $\mathbf{1,591.4\text{ TPH}}$ (Crusher Utilization: $96.6\%$)
  - 30-Seed Batch Mean: $1,594.39 \pm 30.65\text{ TPH}$
- **Authoritative Improvement**:
  - Absolute Gain: $\mathbf{+420.2\text{ TPH}}$ ($1,591.4 - 1,171.2$)
  - Relative Gain: $\mathbf{+35.88\%} \approx \mathbf{+35.9\%}$
  - 30-Seed Paired Student's t-test: $t = 58.02$, $p = 1.50 \times 10^{-31}$
  - Wilcoxon Signed-Rank Test: $W = 0.0$, $p = 1.86 \times 10^{-9}$
  - Effect Size: Cohen's $d = 10.59$ (extremely large effect size)

#### B. Hazardous Ramp Waiting Reduction & Conservation
- **Ramp Incline Waiting ($-8\%$ Haul Ramp)**:
  - Level 0: $625.4\text{ s/trip}$
  - Level 4: $141.6\text{ s/trip}$
  - Reduction: $-483.8\text{ s/trip}$ ($-77.36\%$ reduction on hazardous incline)
- **Shovel Staging Bay Waiting (Flat Bench)**:
  - Level 0: $88.2\text{ s/trip}$
  - Level 4: $489.2\text{ s/trip}$
  - Addition: $+401.0\text{ s/trip}$ (safely queued at zero incline)
- **Net Cycle Delay**:
  - Level 0: $713.6\text{ s/trip}$
  - Level 4: $630.8\text{ s/trip}$
  - Net Savings: $-82.8\text{ s/trip}$ ($-11.60\%$ overall cycle delay reduction)

#### C. Closed-Loop Safety & Invariant Exposure
- **Randomized Monte Carlo Trials**: $N = 10,000$ independent trials.
- **Moving Overspeed / Margin Violations ($v > 0$)**: $0 / 10,000$ ($0.0\%$).
- **Dense Fog Blindout Violations ($R \le 5.0\text{ m} \implies v_{\text{cmd}} = 0$)**: $0 / 2,014$ dense fog trials ($0.0\%$).
- **Central Adversarial Override Attempts**: $0 / 500$ accepted ($100\%$ rejected by Tier-1 Local Safety Governor).

---

### 4. Deterministic Seed Audit & Randomization Integrity

To ensure that statistical independence across the $N = 30$ simulation runs is genuine:
1. **Per-Seed Decoupling**: Each seed $s \in \{1, 2, \dots, 30\}$ initializes an independent `numpy.random.Generator(PCG64(seed))` instance.
2. **Dynamic Haulage Variation**:
   - Initial truck release jitter: $\mathcal{U}(-15, +15)\text{ s}$.
   - Fog visibility field fluctuations: $\mathcal{N}(\mu=15\text{ m}, \sigma=2.5\text{ m})$.
   - Crusher dump duration: $\mathcal{N}(\mu=200\text{ s}, \sigma=12\text{ s})$.
   - Shovel loading cycle: $\mathcal{N}(\mu=180\text{ s}, \sigma=10\text{ s})$.
3. **No Hardcoded Lookahead**: The optimizer receives only historical and current Digital Twin state; no future stochastic realizations are leaked to dispatch logic.

---

### 5. Reproducibility Guarantee

Every parameter used in the simulation and physical derivation is codified in:
- `config/fog_orchestrator_canonical.yaml`
- `fog_safe/vehicle.py`
- `fog_safe/braking.py`
- `fog_safe/safety.py`

There are **zero manual steps, zero hidden spreadsheets, and zero proprietary binaries** required to reproduce all findings of FOG-ORCHESTRATOR 2.0.
