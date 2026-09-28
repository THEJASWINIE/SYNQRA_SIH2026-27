# FINAL SYSTEM BENCHMARK & RECONCILIATION REPORT
## FOG-ORCHESTRATOR 2.0 — SIH26007

### 1. Canonical Benchmark Table across 20 Matched Seeds
Horizon: 7200 s (2-hour shift) | Fleet: 6 x BEML BH100 (165.5 t) | Visibility: 12.0 m dense fog | Grade: -8%

| Configuration | Safety Violations | Completed Loads | Delivered Tonnage (t) | Steady Throughput (TPH) | Crusher Util (%) | Cycle Time (s) | Hazardous Ramp Wait (s) | Safe Staging Wait (s) | Total Wait (s) | Peak Queue (trucks) | Bottleneck Duration (s) | Recovery Time (s) | Safety Clamps |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Emergency Shutdown (All Halted) | 0.0 | 0.0 ± 0.0 | 0.0 | 0.0 (P50: 0.0) | 0.0% | 0.0 | 0.0 (P50: 0.0) | 7224.1 | 7224.1 | 0.0 | 7257.5 | 0.0 | 0 |
| Baseline A: No Orchestration (Unmanaged) | 12.4 | 25.5 ± 0.5 | 2333.2 | 1166.1 (P50: 1165.9) | 70.8% | 2078.2 | 859.4 (P50: 857.1) | 41.9 | 901.3 | 7.8 | 3539.0 | 1208.0 | 0 |
| Baseline B: Vehicle Safety Governor Only | 0.0 | 27.3 ± 0.5 | 2497.9 | 1249.8 (P50: 1251.8) | 75.9% | 1845.7 | 627.2 (P50: 627.7) | 88.2 | 715.4 | 5.8 | 2413.0 | 953.4 | 48 |
| Ablation L2: Safe Speed + Headway Awareness | 0.0 | 30.4 ± 0.6 | 2777.0 | 1388.6 (P50: 1385.8) | 84.3% | 1750.8 | 410.7 (P50: 411.4) | 219.7 | 630.5 | 3.4 | 1601.5 | 612.6 | 85 |
| Ablation L3: Road Capacity + Queue Prediction | 0.0 | 32.5 ± 0.6 | 2978.3 | 1493.5 (P50: 1492.0) | 90.7% | 1682.8 | 265.3 (P50: 266.4) | 365.3 | 630.7 | 2.1 | 950.6 | 384.6 | 114 |
| System C: Full FOG-Orchestrator (Dynamic Staging) | 0.0 | 34.9 ± 0.6 | 3188.8 | 1589.5 (P50: 1587.3) | 96.5% | 1632.5 | 142.3 (P50: 142.6) | 491.7 | 634.0 | 1.2 | 320.0 | 179.6 | 141 |


### 2. Rigorous Statistical Hypothesis Testing

#### Primary Endpoint: Hazardous Haul Ramp Waiting Time (L1 vs L4)
- **Baseline B (L1 Safety Only) Mean:** 627.20 s
- **System C (L4 Orchestrated) Mean:** 142.27 s
- **Absolute Reduction:** 484.93 s (**-77.36%**)
- **Paired Student's t-test:** $t = 141.71$, $p = 3.35e-30$
- **Wilcoxon Signed-Rank Test:** $W = 0.0$, $p = 1.91e-06$
- **Cohen's d Effect Size:** $d = 31.69$ (Extreme effect size)

#### Secondary Endpoint: Production Throughput (L0 vs L4)
- **Baseline A (L0 Unmanaged) Mean:** 1166.10 TPH
- **System C (L4 Orchestrated) Mean:** 1589.55 TPH
- **Absolute Gain:** 423.45 TPH (**+35.88%**)
- **Modeled Crusher Ceiling:** 1647.0 TPH (Utilization: 71.1% -> 96.6%)
- **Paired Student's t-test:** $t = 83.55$, $p = 7.54e-26$, Cohen's $d = 18.68$

#### Net Cycle Delay Reduction (Momentum Conservation)
- **Baseline B (L1 Total Wait):** 715.36 s
- **System C (L4 Total Wait):** 634.00 s
- **Net Savings per Trip:** 81.36 s (**-11.60%** net reduction)
- **Paired t-test:** $t = 17.58$, $p = 3.27e-13$, Cohen's $d = 3.93$
