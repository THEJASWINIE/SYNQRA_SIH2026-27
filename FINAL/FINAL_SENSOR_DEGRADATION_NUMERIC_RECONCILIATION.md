# FINAL NUMERIC RECONCILIATION
## FOG-ORCHESTRATOR 2.0 / SIH26007 — Sensor Degradation Research Extension

**Document Status:** AUTHORITATIVE NUMERIC FREEZE  
**Evaluation Date:** 2026-09-21  
**Auditor:** Principal Safety-Critical Systems Auditor & Lead Scientific Validator  
**Classification:** Research Evidence Reconciliation Register  

---

### 1. Master Headline Metric Register

Every headline number appearing in the Executive Summary, Final Report, Presentation Slides, and Scientific Papers must match the definitions and exact values in this register:

| Metric Name | Value | Unit | Definition | Source File & Location | Code Symbol / Expression | Seed Count | Evidence Tier | Canonical Status |
|---|---|---|---|---|---|---|---|---|
| **Command Authority Violations** | `0` | count | Instances where $v_{\text{command}} > v_{\text{safe}}$ | `experiments/run_sensor_degradation_benchmark.py` L447 | `violations_v_command` | 30 seeds + 10k MC | **L9 Simulation** | **LOCKED (Zero)** |
| **Total Simulation Runs** | `840` | runs | 14 scenarios $\times$ 30 seeds $\times$ 2 modes | `experiments/run_sensor_degradation_benchmark.py` L376 | `len(SCENARIOS) * NUM_SEEDS * 2` | 30 matched | **L9 Simulation** | **LOCKED (840)** |
| **Monte Carlo Sample Count** | `10,000` | samples | Parameterized random safety evaluations | `experiments/run_sensor_degradation_benchmark.py` L396 | `n_samples = 10000` | N/A | **L9 Simulation** | **LOCKED (10k)** |
| **Hazardous Road Waiting Reduction** | `100.0%` | % | Downhill -8% ramp waiting eliminated ($725.4\text{s} \to 0.0\text{s}$) | `FINAL/FINAL_SENSOR_DEGRADATION_RESULTS.csv` Col 6–7 | `(B0_haz - B1_haz) / B0_haz` | 30 matched | **L9 Simulation** | **LOCKED (100%)** |
| **Benchmark Modeled Haulage Tonnage** | `5,796.0` | tonnes | Multi-bay unconstrained fleet haulage over 2 hours | `experiments/run_sensor_degradation_benchmark.py` L353 | `trips_completed * 80.5` | 30 matched | **L9 Simulation** | **Benchmark Spec** |
| **Benchmark Haulage Discharge Rate** | `2,898.0` | TPH | Rate of haulage dumping ($5,796.0\text{ t} / 2.0\text{ hr}$) | `FINAL/THROUGHPUT_DEFINITION.md` Sec 3 | `tonnage / 2.0` | 30 matched | **L9 Simulation** | **Benchmark Spec** |
| **Primary Crusher Bottleneck Ceiling** | `1,647.0` | TPH | Deposit-5 single-pocket 200s slot intake ceiling | `reports/15_FINAL_EVIDENCE_MATRIX.md` L32 | `(3600 / 200.0) * 91.5` | Analytical | **L2 / L3** | **Canonical Spec** |
| **Benchmark Operational Payload** | `80.5` | tonnes | Net payload with heavy-liner tare chassis | `experiments/run_sensor_degradation_benchmark.py` L98 | `PAYLOAD_TONNES = 80.5` | Analytical | **L6 Assumption** | **Benchmark Spec** |
| **Canonical Factory Rated Payload** | `91.5` | tonnes | BEML BH100 rated factory payload (100 short tons) | `reports/18_FINAL_CANONICAL_PARAMETERS.yaml` L36 | `payload_rated_kg: 91500.0` | Analytical | **L2 OEM Doc** | **Canonical Spec** |
| **Certified Machine Gross Weight** | `165.5` | tonnes | BEML BH100 certified gross operating mass | `reports/14_FINAL_BH100_EVIDENCE.md` L19 | `mass_loaded: 165500.0` | Analytical | **L2 OEM Doc** | **Canonical Spec** |
| **D5 / D11 Residual Stopping Violations**| `120` | count | Stopping violations during 120s grace period | `FINAL/FINAL_D5_D13_FORENSIC_AUDIT.md` Sec 2 | `stopping_violations` | 30 matched | **L9 Simulation** | **LOCKED (120)** |
| **D6 / D7 / D13 Stopping Violations** | `3,601` | count | Unobservable false telemetry stopping violations | `FINAL/FINAL_SENSOR_DEGRADATION_RESULTS.csv` Col 5 | `stopping_violations` | 30 matched | **L9 Simulation** | **LOCKED (3601)** |
| **D10 Residual Stopping Violations** | `40` | count | Violations during initial 40s drop window | `FINAL/D10_TRACE_SEED_0.csv` | `df['violation'].sum()` | 30 matched | **L9 Simulation** | **LOCKED (40)** |
| **D8 Stopping Violation Mitigation** | `7.9%` | % | Reduction under Gaussian noise ($1,805.6 \to 1,663.5$) | `FINAL/FINAL_SENSOR_DEGRADATION_RESULTS.csv` Row 10 | `(1805.6 - 1663.5) / 1805.6` | 30 matched | **L9 Simulation** | **LOCKED (7.9%)** |
| **D9 Dual Conflict Mitigation** | `100.0%` | % | Violations eliminated via $\min(R_1, R_2)$ | `FINAL/FINAL_SENSOR_DEGRADATION_RESULTS.csv` Row 11 | `stopping_violations` | 30 matched | **L9 Simulation** | **LOCKED (100%)** |
| **D12 Total Blackout Mitigation** | `100.0%` | % | Violations eliminated via immediate 8m floor | `FINAL/FINAL_SENSOR_DEGRADATION_RESULTS.csv` Row 14 | `stopping_violations` | 30 matched | **L9 Simulation** | **LOCKED (100%)** |
| **Fallback Crawling Visibility Floor** | `8.0` | meters | Configured floor under total sensor loss | `fog_safe/config.py` / `integration_adapters/` | `R_UNAVAILABLE_MIN_m = 8.0` | N/A | **L6 Assumption** | **Canonical Spec** |
| **Safe Speed at 8m Crawling Floor** | `9.7` | km/h | Safe speed resulting from 8m floor ($2.69\text{ m/s}$) | `tests/test_data_health_to_safety_chain.py` L180 | `v_safe_down_kmh` | Analytical | **L9 Simulation** | **Canonical Spec** |
| **Core Regression Test Pass Count** | `1,047` | tests | Full test suite regression passes | `tests/` (83 test files) | `pytest -q` | N/A | **L9 Simulation** | **LOCKED (1047)** |

---

### 2. Discrepancy Audits & Mathematical Reconciliations

#### Discrepancy 1: Payload Discrepancy ($80.5\text{ t}$ vs $91.5\text{ t}$)
- **The Audit Finding:**  
  $91.5\text{ tonnes}$ represents clean-chassis OEM rated factory payload ($74.0\text{ t}$ empty $+ 91.5\text{ t}$ payload $= 165.5\text{ t}$ GVW).  
  $80.5\text{ tonnes}$ represents an operational open-pit configuration with $11.0\text{ tonnes}$ of heavy steel rock-box wear liners ($85.0\text{ t}$ empty $+ 80.5\text{ t}$ payload $= 165.5\text{ t}$ GVW).
- **Physical Invariance:**  
  Vehicle dynamics and stopping calculations depend strictly on **Gross Mass ($165.5\text{ t}$)**. Because both specifications enforce identical GVW, deceleration $a_{\text{dec}}$ and stopping distance $S_{\text{stop}}$ are identical.
- **Tonnage Conversion:**  
  $72\text{ trips} \times 80.5\text{ t} = \mathbf{5,796.0\text{ t}}$. (If converted to factory payload: $72 \times 91.5\text{ t} = \mathbf{6,588.0\text{ t}}$).

#### Discrepancy 2: Throughput Discrepancy ($2,898\text{ TPH}$ vs $1,647\text{ TPH}$)
- **The Audit Finding:**  
  The Deposit-5 primary gyratory crusher pocket is physically constrained to a $200.0\text{-second}$ dump cycle per truck ($18.0\text{ trucks/hr}$), creating a hard production ceiling of $1,647.0\text{ TPH}$ (at $91.5\text{ t}$) or $1,449.0\text{ TPH}$ (at $80.5\text{ t}$).
- **Mathematical Reconciliation:**  
  The benchmark modeled haulage transit across the haul road into unconstrained multi-bay tipping bays with a 90-second cycle ($36.0\text{ trucks/hr}$).  
  $$36\text{ trucks/hr} \times 80.5\text{ t} = \mathbf{2,898.0\text{ TPH}}$$
  $2,898.0\text{ TPH}$ represents **free-flowing multi-bay road transit capacity**, exactly $2.0\times$ the single-pocket crusher ceiling.

#### Discrepancy 3: Waiting-Time Semantics
- **The Audit Finding:**  
  Hazardous downhill $-8\%$ ramp waiting was reduced from $725.4\text{ s} \to 0.0\text{ s}$ ($100\%$ reduction).
- **Relocation Mechanism:**  
  Total waiting was **NOT** reduced to zero. Controlled staging waiting increased ($0 \to 382..5726\text{ s}$). The system relocated dangerous downhill queues to safe level staging areas.
