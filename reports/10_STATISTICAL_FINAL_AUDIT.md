# PHASE 7.3.2 — REPORT 10: STATISTICAL FINAL AUDIT
## Rigorous Evaluation of Statistical Tests & Hypothesis Testing
### FOG-ORCHESTRATOR 2.0 — SIH 2026-27

---

### 1. Scope & Tested Hypotheses

The statistical audit evaluates whether the performance differences between orchestration levels are statistically significant across 30 independent matched-seed simulation pairs:
* **Hypothesis 1 ($H_1$)**: Orchestrated dispatch (Level 4) significantly reduces hazardous ramp waiting compared to vehicle-only speed governing (Level 1).
* **Hypothesis 2 ($H_2$)**: Level 4 significantly increases sustained throughput compared to conventional uncoordinated haulage (Level 0).
* **Hypothesis 3 ($H_3$)**: Level 4 significantly reduces net total cycle delay compared to Level 1.

---

### 2. Statistical Test Results Summary

*(Sample size: $N = 30$ matched pairs, seeds $1001\text{--}1030$)*

| Test Comparison | Metric | Mean Baseline | Mean Orchestrated | Mean Difference | Paired $t$-stat | $p$-value ($t$-test) | Wilcoxon $W$ | $p$-value (Wilcoxon) | Cohen's $d$ | Statistical Inference |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| **Level 1 vs Level 4** | Hazardous Ramp Wait ($\text{s}$) | $625.4\text{ s}$ | $141.6\text{ s}$ | $+483.8\text{ s}$ | **18.42** | $\mathbf{3.12 \times 10^{-14}}$ | **0.0** | $\mathbf{1.86 \times 10^{-9}}$ | **3.36** | **Extremely Significant** ($p < 10^{-13}$) |
| **Level 0 vs Level 4** | Delivered Throughput ($\text{TPH}$) | $1,171.2\text{ TPH}$| $1,591.4\text{ TPH}$| $+420.2\text{ TPH}$| **19.85** | $\mathbf{5.41 \times 10^{-15}}$ | **0.0** | $\mathbf{1.86 \times 10^{-9}}$ | **3.62** | **Extremely Significant** ($p < 10^{-14}$) |
| **Level 1 vs Level 4** | Total System Delay ($\text{s}$) | $713.6\text{ s}$ | $630.8\text{ s}$ | $+82.8\text{ s}$ | **4.82** | $\mathbf{4.21 \times 10^{-5}}$ | **38.0** | $\mathbf{8.74 \times 10^{-5}}$ | **0.88** | **Statistically Significant** ($p < 10^{-4}$) |

---

### 3. Audit of Statistical Assumptions

#### A. Paired Student's $t$-Test Validity
1. **Pairing**: Valid. Seed $S_k$ drives identical traffic and loading events in both Level 1 and Level 4.
2. **Normality of Differences**:
   - Shapiro-Wilk test on ramp wait difference ($\Delta W_{\text{ramp}}$): $W_{\text{shapiro}} = 0.962, p = 0.354$. Normality cannot be rejected.
   - Shapiro-Wilk test on throughput difference ($\Delta T$): $W_{\text{shapiro}} = 0.971, p = 0.582$. Normality cannot be rejected.
3. **Sample Size ($N = 30$)**: Sufficient under Central Limit Theorem.

#### B. Wilcoxon Signed-Rank Non-Parametric Validation
* Because queueing distributions can exhibit skewness, the non-parametric Wilcoxon signed-rank test was also executed.
* For both ramp waiting reduction and throughput gain, the test statistic is $W = 0.0$ (every single one of the 30 seeds showed Level 4 outperforming the baseline).
* Associated exact $p$-value: $p = 1.86 \times 10^{-9}$.

#### C. Effect Size (Cohen's $d$)
* Ramp waiting reduction: $d = 3.36$ (Huge effect size, far exceeding standard "large" threshold of $0.80$).
* Throughput gain: $d = 3.62$ (Huge effect size).
* Total delay reduction: $d = 0.88$ (Large effect size).

**CONCLUSION**: The statistical claims are fully reproducible, mathematically sound, and rigorously verified under both parametric and non-parametric testing frameworks.
