# FINAL REPRODUCIBILITY & VERIFICATION PACKAGE
## FOG-ORCHESTRATOR 2.0 — SIH 2026-27 (Problem Statement SIH26007)
### Step-by-Step Instructions, Environment Specification, Seed Definitions & Cryptographic Hashes

---

## 1. Execution Environment Specification

To ensure reproducible execution across independent evaluator test environments, the system configuration is cryptographically locked:

- **Operating System:** Microsoft Windows 11 (build 26100) / Linux x86_64 compatible
- **Python Runtime:** Python 3.14.0 (MSC v.1944 64 bit / standard CPython)
- **Core Dependencies:** `numpy`, `scipy`, `pandas`, `matplotlib`, `pytest`
- **Git Commit Hash:** `4a3aa4721912f04ecb34f31d8b718e6b352fecd4`
- **HIL Configuration File:** [`config/PHASE8_HIL_CONFIG.yaml`](file:///c:/Users/JAGADEESH%20M/OneDrive/Documents/SIH-2026-27/config/PHASE8_HIL_CONFIG.yaml)
- **Config SHA-256 Checksum:** `b52ab9e586325544c86917a058c0e535ba4977adc3dfe4e6b9b8fce765154e52`

---

## 2. Seed Definitions

### 2.1 The 20 Canonical Benchmark Seeds (Prompt Section 10)
All multi-seed comparative benchmarks between Baseline A (L0), Baseline B (L1), and System C (L4) must execute using this locked sequence of 20 pseudorandom seeds:

```python
CANONICAL_SEEDS = [
    101, 104, 115, 117, 121, 127, 131, 137, 143, 149,
    151, 157, 163, 167, 173, 179, 181, 191, 193, 197
]
```

### 2.2 Monte Carlo Random Seed
The 10,000-scenario safety validation sweep executes with a fixed initialization seed:

```python
MONTE_CARLO_SEED = 54321  # Samples N = 10,000 parameter vectors
```

---

## 3. Step-by-Step Reproduction Commands

To reproduce the entire validation suite and re-generate all outputs from scratch, execute the following commands from the workspace root:

### Step 1: Run Full Automated Regression Test Suite
Executes all 1,010 unit and integration tests across kinematics, governor, Digital Twin, CAN/TWAI bus, and fail-safe state machines:

```powershell
C:\Python314\python.exe -m pytest -q
```
**Expected Outcome:** `1009 passed, 1 skipped, 0 failed in ~18.5 seconds`.

### Step 2: Run Master Benchmark Engine
Executes the closed-loop causal trace, visibility sweep, 20-seed fleet benchmark, 10,000-trial Monte Carlo test, communication matrix, and generates all 9 figures:

```powershell
C:\Python314\python.exe experiments/run_final_master_benchmark.py
```
**Expected Outcome:** `BENCHMARK COMPLETED SUCCESSFULLY in ~4.0 seconds`.  
Generates:
- `FINAL/FINAL_E2E_TRACE.json` (201 timestamps)
- `FINAL/visibility_safe_speed.csv` & `.md`
- `FINAL/FINAL_BENCHMARK.csv` (120 rows) & `FINAL_BENCHMARK.md`
- `FINAL/FINAL_SAFETY_VALIDATION.csv` (2,000 recorded samples from 10k runs)
- `FINAL/FINAL_COMMUNICATION_VALIDATION.csv` (14 conditions)
- `FINAL/FINAL_SCENARIO_MATRIX.csv` & `FINAL_HIL_VALIDATION.csv` (30 scenarios)
- `FINAL/figures/*.png` (9 publication figures)

### Step 3: Run Evidence & Contradiction Registers Generator
Generates the authoritative CSV matrices for claims, contradictions, and hardware classifications:

```powershell
C:\Python314\python.exe experiments/generate_final_registers_and_matrices.py
```
**Expected Outcome:** Generates:
- `FINAL/FINAL_HARDWARE_EVIDENCE_MATRIX.csv`
- `FINAL/FINAL_EVIDENCE_MATRIX.csv`
- `FINAL/FINAL_CLAIM_REGISTER.csv`
- `FINAL/FINAL_CONTRADICTION_REGISTER.csv`

### Step 4: Run HIL Bus & Actuator Validation
Executes the dedicated hardware-in-the-loop validation benchmark across 30 failure injection scenarios and operational grids:

```powershell
C:\Python314\python.exe experiments/run_phase8_hil_validation.py
```
**Expected Outcome:** `PHASE 8 HIL BENCHMARK COMPLETED` (writes `data/phase8_hil_results.csv`).

---

## 4. Verification Checksums for Generated Assets

| Artifact File | Relative Path | Size | SHA-256 Checksum | Cryptographic Purpose |
|---|---|---|---|---|
| `run_final_master_benchmark.py` | [`experiments/run_final_master_benchmark.py`](file:///c:/Users/JAGADEESH%20M/OneDrive/Documents/SIH-2026-27/experiments/run_final_master_benchmark.py) | 46,008 B | `165618b6df35df159fc466e512c6976c18f5a73564a4d13e15ef2cc9e95bc118` | Authoritative Benchmark Engine |
| `FINAL_BENCHMARK.csv` | [`FINAL/FINAL_BENCHMARK.csv`](file:///c:/Users/JAGADEESH%20M/OneDrive/Documents/SIH-2026-27/FINAL/FINAL_BENCHMARK.csv) | 16,903 B | `deb7db76fcbb363ac546377331b3cc279a90fcadfec7e5ad45d64c12522540dc` | 120-row master fleet benchmark across 20 seeds |
| `FINAL_SAFETY_VALIDATION.csv`| [`FINAL/FINAL_SAFETY_VALIDATION.csv`](file:///c:/Users/JAGADEESH%20M/OneDrive/Documents/SIH-2026-27/FINAL/FINAL_SAFETY_VALIDATION.csv) | 205,303 B | `aa859156e9f0cb6a2181dd44e1297d69edcadd6d096fc11c7fb35e8125c41006` | 10,000 Monte Carlo safety trials (zero violations) |
| `FINAL_CANONICAL_MODEL.yaml` | [`FINAL/FINAL_CANONICAL_MODEL.yaml`](file:///c:/Users/JAGADEESH%20M/OneDrive/Documents/SIH-2026-27/FINAL/FINAL_CANONICAL_MODEL.yaml) | 8,925 B | `31a1345927925e6c708b221f11d4c1978420137e614d200eb33ef9520becd231` | Machine-readable parameter source of truth |
| `FINAL_E2E_TRACE.json` | [`FINAL/FINAL_E2E_TRACE.json`](file:///c:/Users/JAGADEESH%20M/OneDrive/Documents/SIH-2026-27/FINAL/FINAL_E2E_TRACE.json) | 149,185 B | `9dab02d302eb32881574615d545128313202be05ba7f5b8dc2a7fb3446727898` | 201-second closed-loop causal chain trace |
| `FINAL_NUMERIC_RECONCILIATION.md` | [`FINAL/FINAL_NUMERIC_RECONCILIATION.md`](file:///c:/Users/JAGADEESH%20M/OneDrive/Documents/SIH-2026-27/FINAL/FINAL_NUMERIC_RECONCILIATION.md) | ~10 KB | Verified against CSVs | Definitive forensic reconciliation audit |
| `e2e_causal_chain.png` | [`FINAL/figures/e2e_causal_chain.png`](file:///c:/Users/JAGADEESH%20M/OneDrive/Documents/SIH-2026-27/FINAL/figures/e2e_causal_chain.png) | ~250 KB | Image Asset | 300 DPI high-resolution causal chain diagram |
| `baseline_comparison.png`| [`FINAL/figures/baseline_comparison.png`](file:///c:/Users/JAGADEESH%20M/OneDrive/Documents/SIH-2026-27/FINAL/figures/baseline_comparison.png) | ~118 KB | Image Asset | Modeled throughput bar chart with error bars and 1647 TPH ceiling |
| `waiting_comparison.png` | [`FINAL/figures/waiting_comparison.png`](file:///c:/Users/JAGADEESH%20M/OneDrive/Documents/SIH-2026-27/FINAL/figures/waiting_comparison.png) | ~98 KB | Image Asset | Hazardous haul ramp waiting time reduction comparison |
