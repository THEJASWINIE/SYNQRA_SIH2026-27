# EXPERIMENT E13 — STATISTICAL REPRODUCIBILITY REPORT

**Project:** FOG-ORCHESTRATOR 2.0 (SIH 2026-27 — SIH26007)  
**Classification:** Multi-Seed Statistical Verification & Hypothesis Testing  
**Evidence Level:** L9 — Monte Carlo Simulation (30 Independent Seeds)  
**Dataset Reference:** [`data/fleet_results.csv`](file:///c:/Users/JAGADEESH%20M/OneDrive/Documents/SIH-2026-27/data/fleet_results.csv)  

---

## 1. Experimental Methodology

To eliminate cherry-picked runs, 30 independent pseudorandom seeds (`SEED = 20260918` through `20260947`) were evaluated across all three operating policies under identical haul road topologies, truck fleet sizes (12 dumpers), and stochastic fog dissipation profiles.

---

## 2. Statistical Metrics Breakdown across 30 Seeds

### A. Hazardous Haul Road Queue Waiting ($W_{\text{road}}$, seconds)

| Policy | Mean (s) | Median (s) | Std Dev (s) | P5 (s) | P95 (s) | 95% Conf. Interval (s) |
|:---|:---:|:---:|:---:|:---:|:---:|:---:|
| **A: No Orchestration** | 848.2 | 845.6 | 63.4 | 742.1 | 951.8 | [825.5, 870.9] |
| **B: Vehicle Safety Only** | 619.4 | 621.1 | 39.8 | 554.2 | 684.5 | [605.2, 633.6] |
| **C: FOG-Orchestrator** | **141.6** | **139.8** | **24.6** | **102.4** | **181.5** | **[132.8, 150.4]** |

### B. Steady-State Crusher Throughput (TPH)

| Policy | Mean (TPH) | Median (TPH) | Std Dev (TPH) | P5 (TPH) | P95 (TPH) | 95% Conf. Interval (TPH) |
|:---|:---:|:---:|:---:|:---:|:---:|:---:|
| **A: No Orchestration** | 1,098.4 | 1,095.2 | 44.2 | 1,025.0 | 1,170.5 | [1,082.6, 1,114.2] |
| **B: Vehicle Safety Only** | 1,381.2 | 1,380.5 | 34.6 | 1,324.0 | 1,438.0 | [1,368.8, 1,393.6] |
| **C: FOG-Orchestrator** | **1,591.4** | **1,592.8** | **24.8** | **1,550.0** | **1,630.0** | **[1,582.5, 1,600.3]** |

---

## 3. Hypothesis Testing & Effect Size

1. **Reduction in Hazardous Haul Road Queue Waiting (Policy C vs. Policy B):**  
   - Absolute reduction: **-477.8 seconds per truck cycle** (-77.1%)
   - Two-sample Student's t-test: $t = 56.4$, $p < 10^{-15}$ (Statistically highly significant)
   - Cohen's $d$ Effect Size: $d = 14.4$ (Massive real-world effect)

2. **Crusher Throughput Improvement (Policy C vs. Policy B):**  
   - Absolute gain: **+210.2 TPH** (+15.2% utilization of crusher bottleneck)
   - Two-sample Student's t-test: $t = 27.1$, $p < 10^{-12}$ (Statistically highly significant)
   - Cohen's $d$ Effect Size: $d = 6.9$ (Large effect)
