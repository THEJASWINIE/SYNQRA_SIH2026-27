# 15 — REPRODUCIBILITY & SCIENTIFIC AUDIT GUIDE
## FOG-ORCHESTRATOR 2.0 — Sensor Degradation Benchmark
**Project:** SIH26007 — Safe and Efficient Mine Haulage in Low Visibility  
**Date:** 2026-09-21  
**Audit Standard:** 100% Deterministic Reproducibility Across Matched Seeds

---

## 1. Reproducibility Mandate & Artifact Contract

To ensure that every number, figure, table, and statistical test reported in this research can be independently replicated by external reviewers, evaluators, or safety auditors, this repository maintains:

1. **Deterministic Pseudorandom Generation:** All synthetic packet drops, sensor noises, and Monte Carlo samplings are seeded with explicit integer seeds (`seed=0..29` for matched benchmarks, `seed=42` for Monte Carlo).
2. **Synchronized Clocks:** Simulation scenarios use explicit simulated timestamps, preventing wall-clock jitter from corrupting timeout transitions.
3. **Canonical Physics Parameters:** Vehicle weights, grades, coefficients of rolling resistance, and brake reaction times are frozen in `fog_safe/` and `FINAL/FINAL_CANONICAL_MODEL.yaml`.
4. **Machine-Readable Manifests:** Raw outputs are saved to standard CSV and YAML files.

---

## 2. Environment & Tooling Specifications

| Component | Specification / Version |
|---|---|
| **Operating System** | Windows 11 / Linux (Ubuntu 22.04 LTS verified) |
| **Python Runtime** | Python 3.10+ (tested on Python 3.14.0) |
| **Core Libraries** | `numpy>=1.26.0`, `scipy>=1.12.0`, `matplotlib>=3.8.0`, `pytest>=8.0.0` |
| **Hardware Platform** | Standard x86_64 workstation (zero GPU requirement; CPU only) |
| **Benchmark Runtime** | Approximately $60\text{--}90\text{ seconds}$ for 840 simulation runs + 10,000 Monte Carlo vectors |

---

## 3. Step-by-Step Replication Instructions

### Step 1: Verify Unit & Integration Tests
Execute the comprehensive data health test suite:
```bash
python -m pytest tests/test_environmental_data_health.py -v
```
*Expected Result:* 17 passed in $< 2.0\text{ s}$.

### Step 2: Execute Core Regression Tests
Verify that existing safety governors and telemetry boundaries remain intact:
```bash
python -m pytest tests/test_telemetry_ingest.py tests/test_failsafe_execution.py tests/test_command_gateway.py -v
```
*Expected Result:* 135 passed in $< 3.5\text{ s}$.

### Step 3: Run the Complete Failure-Injection Benchmark Suite
Run the 30-seed benchmark across all 14 degradation scenarios:
```bash
python experiments/run_sensor_degradation_benchmark.py
```
This single command automatically performs:
1. 840 full 2-hour haulage simulations ($14\text{ scenarios} \times 30\text{ seeds} \times 2\text{ modes}$).
2. 10,000-iteration safety Monte Carlo sampling.
3. L0–L4 ablation study across degradation modes.
4. Wilcoxon signed-rank and paired t-test significance calculations.
5. Automatic rendering of all 12 publication figures into `sensor_degradation_research/figures/`.
6. Export of `sensor_degradation_research/RESULTS.csv`, `SCENARIO_RESULTS.csv`, and `FINAL/SENSOR_DEGRADATION_RESULTS.csv`.

---

## 4. Generated Artifact Index

| Artifact Path | Description | Verification Hash / Size |
|---|---|---|
| `integration_adapters/environmental_data_health.py` | Authoritative data health module | Rule-based (H1–H6), fail-closed |
| `tests/test_environmental_data_health.py` | 17 unit/integration tests | 100% pass |
| `experiments/run_sensor_degradation_benchmark.py` | Master benchmark runner | Deterministic, reproducible |
| `sensor_degradation_research/RESULTS.csv` | Raw 840-run record matrix | Per-run metrics (stopping violations, waiting, throughput) |
| `sensor_degradation_research/SCENARIO_RESULTS.csv` | Aggregated scenario summary table | Mean, P95, and max metrics |
| `sensor_degradation_research/REPRODUCIBILITY_MANIFEST.csv` | Parameter provenance register | Classifications (L1 to L10) |
| `FINAL/SENSOR_DEGRADATION_REPRODUCIBILITY.yaml` | Machine-readable config snapshot | Frozen parameters & Monte Carlo summary |
| `sensor_degradation_research/figures/` | Directory of 12 publication plots | PNG format, 300 DPI |

---

## 5. Parameter Classification Audit

All parameters used in benchmark calculations are categorized according to the project's evidence hierarchy:

- **BEML BH100 Loaded Mass ($165,500\text{ kg}$):** Tier L2 (OEM Documented)
- **BEML BH100 Empty Mass ($85,000\text{ kg}$):** Tier L2 (OEM Documented)
- **Haul Road Grade ($-8.0\%$):** Tier L6 (Engineering Assumption)
- **Effective Friction Coefficient ($\mu = 0.35$):** Tier L6 (Engineering Assumption)
- **Total Brake Latency ($\tau = 0.80\text{ s}$):** Tier L6 (Engineering Assumption)
- **Degraded Freshness Timeout ($T_{\text{degraded}} = 30.0\text{ s}$):** Tier L6 (Engineering Parameter)
- **Stale Freshness Timeout ($T_{\text{stale}} = 60.0\text{ s}$):** Tier L6 (Engineering Parameter)
- **Grace Period ($T_{\text{grace}} = 120.0\text{ s}$):** Tier L6 (Engineering Parameter)
- **Degraded Factor ($0.70$):** Tier L6 (Engineering Parameter)
- **Stale Factor ($0.50$):** Tier L6 (Engineering Parameter)
- **Minimum Crawl Headway ($R_{\text{unavailable}} = 8.0\text{ m}$):** Tier L6 (Engineering Parameter)
- **Recovery Hysteresis ($2\text{--}3\text{ frames}$):** Tier L6 (Engineering Parameter)
