# 08 — STATISTICAL VALIDATION & EFFECT-SIZE REPORT

**Project:** FOG-ORCHESTRATOR 2.0 (SIH 2026-27 — SIH26007)  
**Classification:** Multi-Seed Inferential Statistics & Paired Hypothesis Testing  
**Dataset Reference:** [`data/phase7_3_statistics.csv`](file:///c:/Users/JAGADEESH%20M/OneDrive/Documents/SIH-2026-27/data/phase7_3_statistics.csv) (35 metric distributions)  
**Sample Size:** $N = 30$ independent pseudorandom seeds (`SEED = 20260918` to `20260947`)  
**Date of Audit:** 2026-09-18  

---

## 1. Audit of Phase 7.2 Statistical Significance Claims

> [!NOTE]
> **AUDIT OF $t = 56.4, p < 10^{-15}, d = 14.4$**  
> Phase 7.2 reported extremely high t-statistics for haul road queue waiting reduction. An audit was conducted to verify test validity:
> 1. **Paired Structure:** In discrete-event simulation benchmarks, the exact same pseudorandom seed drives truck departures, driver variations, and fog ingress across both Policy Level 1 and Policy Level 4. Therefore, an **independent two-sample t-test is invalid**, but a **paired-sample Student's t-test** ($df = 29$) is mathematically appropriate.
> 2. **Normality of Differences:** Differences ($\Delta = W_{\text{Level 4}} - W_{\text{Level 1}}$) satisfy the Shapiro-Wilk test for normality ($W = 0.962, p = 0.354 > 0.05$).
> 3. **Result:** The paired t-test yields $t = -56.4$ with $p = 4.2 \times 10^{-28}$. Non-parametric Wilcoxon signed-rank test yields $W = 0.0, p = 1.7 \times 10^{-9}$. Cohen's $d = 14.4$.
> 4. **Important Qualification:** While statistically indisputable within the simulation seed population, this proves **algorithmic reproducibility across random variations**, not field empirical noise.

---

## 2. Statistical Metric Distributions Across 30 Seeds

### A. Hazardous Haul Road Queue Waiting ($W_{\text{road}}$, seconds)

| Orchestration Level | Mean (s) | Median (s) | Std Dev (s) | P5 (s) | P95 (s) | 95% Conf. Interval (s) |
|:---|:---:|:---:|:---:|:---:|:---:|:---:|
| **Level 0: No Orchestration** | 860.2 | 858.4 | 48.6 | 782.1 | 938.4 | [842.8, 877.6] |
| **Level 1: Vehicle Safety Only** | 625.4 | 627.1 | 34.2 | 568.5 | 679.2 | [613.2, 637.6] |
| **Level 2: Road Capacity Aware** | 410.1 | 412.5 | 29.8 | 362.4 | 458.1 | [399.4, 420.8] |
| **Level 3: Predictive Bottleneck** | 245.3 | 243.8 | 24.6 | 206.2 | 284.5 | [236.5, 254.1] |
| **Level 4: Full FOG-Orchestrator** | **141.6** | **139.8** | **22.4** | **105.1** | **178.4** | **[133.6, 149.6]** |

### B. Steady-State Crusher Throughput (TPH)

| Orchestration Level | Mean (TPH) | Median (TPH) | Std Dev (TPH) | P5 (TPH) | P95 (TPH) | 95% Conf. Interval (TPH) |
|:---|:---:|:---:|:---:|:---:|:---:|:---:|
| **Level 0: No Orchestration** | 1,085.2 | 1,082.4 | 39.8 | 1,018.5 | 1,148.2 | [1,071.0, 1,099.4] |
| **Level 1: Vehicle Safety Only** | 1,375.4 | 1,374.8 | 29.5 | 1,326.4 | 1,422.1 | [1,364.8, 1,386.0] |
| **Level 2: Road Capacity Aware** | 1,460.1 | 1,458.9 | 24.6 | 1,418.2 | 1,498.5 | [1,451.3, 1,468.9] |
| **Level 3: Predictive Bottleneck** | 1,530.2 | 1,532.1 | 19.8 | 1,496.4 | 1,561.2 | [1,523.1, 1,537.3] |
| **Level 4: Full FOG-Orchestrator** | **1,591.4** | **1,592.8** | **21.8** | **1,552.4** | **1,624.1** | **[1,583.6, 1,599.2]** |

---

## 3. Paired Hypothesis Tests & Effect Sizes (Level 4 vs. Level 1)

All comparisons evaluate differences for each seed: $\Delta_i = X_{4,i} - X_{1,i}$ ($N = 30$).

| Evaluated Metric | Mean Difference ($\Delta$) | Paired Student's $t$ ($df=29$) | $p$-value ($t$-test) | Wilcoxon Signed-Rank $W$ | $p$-value (Wilcoxon) | Cohen's $d$ Effect Size | Substantive Meaning |
|:---|:---:|:---:|:---:|:---:|:---:|:---:|:---|
| **Hazardous Road Waiting ($W_{\text{road}}$)** | **-483.8 s** | **$t = -56.4$** | **$4.2 \times 10^{-28}$** | **$W = 0.0$** | **$1.7 \times 10^{-9}$** | **$d = 14.4$** | Enormous reduction in hazardous ramp queueing |
| **Total System Waiting ($W_{\text{total}}$)** | **-82.8 s** | **$t = -11.2$** | **$1.4 \times 10^{-11}$** | **$W = 0.0$** | **$1.7 \times 10^{-9}$** | **$d = 2.05$** | Statistically significant net cycle delay reduction |
| **Steady-State Production** | **+216.0 TPH** | **$t = +27.1$** | **$2.8 \times 10^{-20}$** | **$W = 0.0$** | **$1.7 \times 10^{-9}$** | **$d = 6.90$** | Large improvement in crusher bottleneck utilization |
| **Peak Haul Road Queue Size** | **-4.6 trucks** | **$t = -31.8$** | **$4.1 \times 10^{-22}$** | **$W = 0.0$** | **$1.7 \times 10^{-9}$** | **$d = 8.12$** | Virtually eliminates multi-truck downhill queues |
| **Recovery Time ($T_{\text{recov}}$)** | **-162.0 s** | **$t = -42.6$** | **$8.9 \times 10^{-25}$** | **$W = 0.0$** | **$1.7 \times 10^{-9}$** | **$d = 10.8$** | Drastically accelerates return to normal platooning |

**Conclusion:**  
Every performance benefit of Level 4 FOG-Orchestrator over Level 1 autonomous safety is statistically significant across 30 seeds ($p < 10^{-9}$), with massive effect sizes ($d > 2.0$).
