# 09 — STATISTICAL METHODOLOGY & HYPOTHESIS TESTING AUDIT
## FOG-ORCHESTRATOR 2.0 — PHASE 7.3.1 AUDIT REPORT

| Document ID | Canonical File Path | Date | Audit Status | Dataset Reference |
| :--- | :--- | :--- | :--- | :--- |
| **REP-731-09** | `reports/09_STATISTICAL_REVALIDATION.md` | 2026-09-18 | **FROZEN / LOCKED** | `data/phase7_3_statistics.csv` |

---

### 1. Forensic Audit of the Historical Significance Claim

Early benchmark drafts reported:
$$\text{Historical Claim: } t = 56.4, \quad p < 10^{-15}, \quad \text{Cohen's } d = 14.4$$

#### Forensic Methodological Critique:
1. **Misapplication of Independent Two-Sample Test**:
   * The historical test calculated an independent two-sample t-test comparing pooled variance across runs, ignoring that the simulation evaluated the **exact same pseudo-random seeds** across different capability levels.
   * Treating paired seed runs as independent samples inflates degrees of freedom and creates an artificially compressed standard error, yielding an unphysically massive effect size ($d = 14.4$).
2. **Methodological Correction**:
   * Because identical initial seeds (Seeds 1001 to 1030) generate correlated operational noise profiles, the valid statistical test is a **Paired Two-Tailed Student's t-test** on within-seed differences ($\Delta_i = x_{i, \text{Level 1}} - x_{i, \text{Level 4}}$).
   * To account for potential non-normality in queue duration tails, results must be corroborated using the non-parametric **Wilcoxon Signed-Rank Test**.

---

### 2. Rigorous Paired Hypothesis Testing Results (N = 30 Seeds)

```
========================================================================================================================
METRIC EVALUATED             MEAN DIFF (Δ)   PAIRED t-STAT    p-VALUE (t-test) WILCOXON W   p-VALUE (Wilcoxon) COHEN'S d
========================================================================================================================
Hazardous Ramp Waiting (s)   -483.8 s        t = 18.4215      p = 3.12e-14     W = 0.0      p = 1.86e-09       d = 3.3634
Throughput Gain (TPH)        +420.2 TPH      t = 34.6210      p = 4.12e-24     W = 0.0      p = 1.86e-09       d = 6.3218
Net Total Cycle Delay (s)    -82.8 s         t = 9.8542       p = 4.28e-11     W = 0.0      p = 1.86e-09       d = 1.7992
========================================================================================================================
```

---

### 3. Verification of Statistical Assumptions

#### A. Pairing Validity:
Each comparison evaluates seed pair $(S_{i, \text{Level 1}}, S_{i, \text{Level 4}})$. The environmental disturbance (fog arrival time, fog density noise, and shovel loading variation) is identical between paired observations, ensuring that difference scores $\Delta_i$ isolate purely the effect of orchestration.

#### B. Normality of Differences:
* Shapiro-Wilk test on paired differences for hazardous ramp queue waiting: $W = 0.962, p = 0.354$ (Accept $H_0$; normal distribution confirmed).
* Shapiro-Wilk test on paired throughput differences: $W = 0.971, p = 0.582$ (Accept $H_0$; normal distribution confirmed).
* Because difference scores are normally distributed, the **Paired Student's t-test is fully justified and mathematically valid**.

#### C. Non-Parametric Corroboration:
The Wilcoxon signed-rank test evaluates median shift without distributional assumptions. In all 30 paired comparisons:
* In $30\text{ out of }30$ seeds, Level 4 exhibited strictly lower hazardous ramp waiting than Level 1 ($W = 0.0, p = 1.86 \times 10^{-9}$).
* In $30\text{ out of }30$ seeds, Level 4 exhibited strictly higher sustained throughput than Level 0 ($W = 0.0, p = 1.86 \times 10^{-9}$).

---

### 4. Interpretation of Effect Sizes

* **Hazardous Ramp Waiting ($d = 3.36$)**:  
  Exceeds Cohen's threshold for a "very large" effect ($d > 1.2$). The reduction of $483.8\text{ seconds}$ represents more than $3.3$ standard deviations of separation, proving that queue relocation is an overwhelming operational effect.
* **Net Total Cycle Delay ($d = 1.80$)**:  
  Confirms that the $-11.60\%$ net cycle delay reduction ($-82.8\text{ s}$) is a genuine, statistically significant efficiency improvement rather than simulation noise.

All statistical outputs are frozen in `data/phase7_3_statistics.csv`.
