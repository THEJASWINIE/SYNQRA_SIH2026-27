# STAGE 5.2.1: FORENSIC PRODUCTIVITY RETENTION (PR) AUDIT
**Mathematical Integrity, Baseline Formulation, and Transient vs. Steady-State Distinctions**  
**Project:** FOG-ORCHESTRATOR 2.0 (SIH 2026-27 — NMDC Bailadila Iron Ore Complex)  
**Status:** EVIDENCE INTEGRITY GATE — ZERO CIRCULAR BENCHMARKING  

---

## 1. Executive Forensic Question

In Stage 5 audits, the benchmark metric "Productivity Retention" ($PR$) was corrected from circular scaling ($PR = Q_{\text{actual}} / C_{\text{fog}}$) to clear-weather baseline indexing ($PR = Q_{\text{fog}} / Q_{\text{clear}} \times 100$). 

This audit determines:
> **Do the reported PR values reflect true steady-state physical productivity retention, or do they measure transient simulation throughput over the defined 1,800-second window?**

### The Definitive Forensic Finding:
The reported $PR$ values **measure transient simulation throughput over the defined 1,800-second evaluation window**. Because the clear-weather baseline ($Q_{\text{clear}} = 3{,}294\text{ TPH}$) reflects the initial pre-staged shovel queue flush (18 dumps in 0.5 h), calculating $PR$ against this denominator provides an accurate, non-circular comparative index of **transient throughput retention**, but must not be cited as a steady-state annual mine production index.

---

## 2. Mathematical Audit of the PR Formulation

The formula executed in `run_productivity_retention_experiment()` is:
$$PR = \begin{cases} 
\min\left(100.0, \frac{Q_{\text{fog}}}{Q_{\text{clear}}} \times 100\right) & \text{if } Q_{\text{clear}} > 0 \text{ and } v_{\text{safe}} > 0 \\ 
0.0\% \text{ (Reported as N/A)} & \text{if } v_{\text{safe}} = 0 \text{ or } Q_{\text{clear}} = 0 
\end{cases}$$

### Verification of Audit Invariants:
1. **$Q_{\text{clear}} > 0$ Confirmed:** $Q_{\text{clear}} = 3{,}294.0\text{ TPH} > 0$. The baseline denominator is strictly non-zero.
2. **$Q_{\text{fog}}$ Grounded in Completed Events:** $Q_{\text{fog}}$ is derived solely from physical dump counts ($N_{\text{completed}} \times 91.5\text{ t} / 0.5\text{ h}$).
3. **Zero-Division Fallback Eliminated:** At $V \le 5\text{ m}$, $v_{\text{safe}} = 0.0\text{ m/s}$. The code sets $PR = 0.0\%$ and tags the status as `HALT_ZERO_MOVEMENT`. It does **not** perform $0/0 \to 100\%$.
4. **Cap at $100\%$:** No condition reports $PR > 100\%$.

---

## 3. Detailed PR Audit Table

From [`docs/STAGE5_2_PRODUCTIVITY_RETENTION.csv`](file:///c:/Users/JAGADEESH%20M/OneDrive/Documents/SIH-2026-27/docs/STAGE5_2_PRODUCTIVITY_RETENTION.csv):

| Visibility ($V$) | Safe Ramp Speed ($v_{\text{safe}}$) | $Q_{\text{clear}}$ Baseline | $Q_{\text{fog}}$ Actual | Measured $PR$ | Audit Assessment | Physical Operational Meaning |
| :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| **$100\text{ m}$** | $8.33\text{ m/s}$ | $3{,}294.0\text{ TPH}$ | $3{,}294.0\text{ TPH}$ | **$100.0\%$** | **VALID BASELINE** | Baseline clear-weather reference. Full dry speed. |
| **$50\text{ m}$** | $8.33\text{ m/s}$ | $3{,}294.0\text{ TPH}$ | $3{,}294.0\text{ TPH}$ | **$100.0\%$** | **VALID TRANSIENT** | Light fog does not impede $8.33\text{ m/s}$ ($30\text{ km/h}$) speed limit. |
| **$25\text{ m}$** | $8.33\text{ m/s}$ | $3{,}294.0\text{ TPH}$ | $2{,}013.0\text{ TPH}$ | **$61.1\%$** | **VALID TRANSIENT** | Wet road friction ($\mu=0.35$) increases safe headway; 11 dumps. |
| **$12\text{ m}$** | $4.79\text{ m/s}$ | $3{,}294.0\text{ TPH}$ | $732.0\text{ TPH}$ | **$22.2\%$** | **VALID TRANSIENT** | Speed halved; cycle time extends; 4 dumps completed. |
| **$10\text{ m}$** | $3.93\text{ m/s}$ | $3{,}294.0\text{ TPH}$ | $732.0\text{ TPH}$ | **$22.2\%$** | **VALID TRANSIENT** | Speed drops to $14\text{ km/h}$; 4 dumps completed. |
| **$8\text{ m}$** | $2.88\text{ m/s}$ | $3{,}294.0\text{ TPH}$ | $183.0\text{ TPH}$ | **$5.6\%$** | **VALID TRANSIENT** | Severe crawl ($10\text{ km/h}$); only 1 dump completed in $0.5\text{ h}$. |
| **$5\text{ m}$** | **$0.00\text{ m/s}$** | $3{,}294.0\text{ TPH}$ | **$0.0\text{ TPH}$** | **$0.0\%$ (`N/A`)** | **PROVEN ZERO** | Physical stopping distance exceeds sight distance. Full halt. |
| **$4\text{ m}$** | **$0.00\text{ m/s}$** | $3{,}294.0\text{ TPH}$ | **$0.0\text{ TPH}$** | **$0.0\%$ (`N/A`)** | **PROVEN ZERO** | Physical zero speed halt. |
| **$3\text{ m}$** | **$0.00\text{ m/s}$** | $3{,}294.0\text{ TPH}$ | **$0.0\text{ TPH}$** | **$0.0\%$ (`N/A`)** | **PROVEN ZERO** | Physical zero speed halt. |

---

## 4. Scientific Bounds & Mandatory Citation

1. **Transient vs. Steady-State Distinction:**
   In a multi-hour steady-state run where shovel queues reach statistical equilibrium, the clear-weather ceiling is $1{,}647\text{ TPH}$ ($18\text{ VPH}$). In the 1,800s experimental window, the pre-loaded initial state produced $3{,}294\text{ TPH}$. Therefore:
   - The $22.2\%$ PR at $10\text{ m}$ reflects that 4 loads were delivered versus 18 loads in the baseline.
   - If evaluated against the steady-state crusher ceiling ($1{,}647\text{ TPH}$), 4 loads in $0.5\text{ h}$ ($732\text{ TPH}$) represents:
     $$PR_{\text{steady-state}} = \frac{732.0}{1647.0} \times 100 = \mathbf{44.4\%}$$
2. **Mandatory Documentation Rule:**
   Whenever reporting Productivity Retention in academic or SIH evaluator presentations, the following caveat MUST be stated:
   > *"Productivity Retention ($PR$) is evaluated over the 1,800-second experimental window against the clear-weather transient baseline. At $10\text{ m}$ visibility, delivered tonnage is $22.2\%$ of the clear-weather initial flush rate and $44.4\%$ of steady-state crusher capacity. At $\le 5\text{ m}$ visibility, physical stopping constraints force a complete halt, yielding an honest $0.0\%$ retention."*
