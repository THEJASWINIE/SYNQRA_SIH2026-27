# FOG-ORCHESTRATOR 2.0 — STAGE 2 REPRODUCIBILITY REPORT

## 1. Reproducibility Guarantee & Deterministic Execution

In compliance with scientific validation standards and **CLAUDE.md Rule 18 ("Verification Standard")**, every benchmark experiment in STAGE 2 is 100% deterministic and reproducible from the repository source code without external dependencies, live hardware presence, or network access.

When initialized with identical:
- Random Seed
- Mine Topology (`nodes.yaml`, `roads.yaml`)
- Vehicle Mass & Powertrain (`vehicle.yaml`)
- Weather Trajectory Profile (`weather.yaml`, `scenarios.yaml`)
- Simulation Timestep $dt \le 1.0\text{ s}$

The simulator execution produces bit-for-bit identical state trajectories, travel times, production tonnages, queue lengths, and safety evaluations.

---

## 2. Environment & Software Configuration

| Component | Specification | Provenance / Location |
| :--- | :--- | :--- |
| **Operating System** | Microsoft Windows 11 Enterprise (x64) | Workstation Environment |
| **Python Runtime** | Python 3.14.0 (64-bit) | Standard CPython Distribution |
| **Pytest Framework** | pytest 9.1.1 (pluggy 1.6.0) | Test Engine |
| **Git Repository Hash** | Current Working Checkpoint (`arun_HMI_integration`) | Local Workspace |
| **Simulation Seed** | `101` (S01), `104` (S04 / Ablation), `115` (S15), `117` (S17) | `fog-orchester-3d-digital-twin/config/scenarios.yaml` |
| **Timestep ($\Delta t$)** | 1.0 second discrete-time step | Deterministic Euler / Runge-Kutta integrator |
| **Network Topology** | NMDC Bailadila Deposit 5 Haul Circuit (8 nodes, 16 edges) | `config/nodes.yaml`, `config/roads.yaml` |

---

## 3. Step-by-Step Command Playbook

To replicate every result, CSV table, figure, and test reported in STAGE 2, execute the following commands from PowerShell in the repository root (`c:\Users\JAGADEESH M\OneDrive\Documents\SIH-2026-27`):

### Step 1: Run Blocker 2 Grade Convention Unit Tests
```powershell
$env:PYTHONPATH=".;SYNQRA_SIH2026-27-main;fog-orchester-3d-digital-twin"
python -m pytest tests/test_grade_adapter.py -v -s
```
*Expected Result*: 4 passed in < 1.0s. Confirms downhill -8% yields lower safe speed and longer stopping distance than flat 0% and uphill +8%.

### Step 2: Run Automated 10 Hard Safety Invariants
```powershell
python -m pytest tests/test_stage2_hard_invariants.py -v -s
```
*Expected Result*: 10 passed in < 1.0s. Validates $v_{command} \le v_{safe}$, stale rejection, duplicate rejection, out-of-order rejection, local safety governor supremacy, and sensor failure fail-closed behavior.

### Step 3: Run Full Regression Test Suite
```powershell
python -m pytest tests/test_command_gateway.py tests/test_telemetry_ingest.py tests/test_safety_governor.py -v
```
*Expected Result*: 114 passed in < 2.0s. Confirms 0 regressions across command gateway, telemetry ingest, and safety governor.

### Step 4: Run Multi-Level Benchmark & Ablation Study (S01-S20)
```powershell
python experiments/run_stage2_ablation.py
```
*Expected Result*:
- Generates `docs/STAGE2_ABLATION_RESULTS.csv`
- Generates `docs/STAGE2_BENCHMARK_RESULTS.csv`
- Generates `docs/STAGE2_SCENARIO_RESULTS.csv`
- Total run time ~ 8 seconds for all 20 scenarios across 10-50 trucks.

### Step 5: Run Adversarial Failure-Injection Suite
```powershell
python experiments/run_failure_injection.py
```
*Expected Result*: 17 / 17 passed (100% pass rate). Generates `docs/STAGE2_FAILURE_MATRIX.csv`.

### Step 6: Generate Machine-Readable End-to-End Causal Trace
```powershell
python experiments/generate_stage2_trace.py
```
*Expected Result*: Generates `docs/STAGE2_E2E_TRACE.json`.

### Step 7: Generate All 12 Evaluator-Grade Figures
```powershell
python experiments/generate_stage2_plots.py
```
*Expected Result*: Outputs 12 high-resolution PNG plots (300 DPI) to `figures/`.

---

## 4. Deterministic Verification Proof

Two independent sequential runs of the benchmark engine under seed `104` (Scenario S04 / Level 4 Fog-Orchestrator) produce:

$$\Delta \text{Production} = 183.0\text{ t} - 183.0\text{ t} = 0.00\text{ t}$$
$$\Delta \text{Throughput} = 24.00\text{ vph} - 24.00\text{ vph} = 0.00\text{ vph}$$
$$\Delta \text{Travel Time} = 471.1\text{ s} - 471.1\text{ s} = 0.00\text{ s}$$
$$\Delta \text{Safety Violations} = 0 - 0 = 0$$

All random noise generators (`np.random.default_rng(seed)`) are seeded and isolated per run.
