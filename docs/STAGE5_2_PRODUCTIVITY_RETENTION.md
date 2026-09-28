# STAGE 5.2: PRODUCTIVITY RETENTION BENCHMARK
**Rigorous, Non-Circular Productivity Retention ($PR = Q_{\text{fog}} / Q_{\text{clear}} \times 100$) Across Fog Regimes**  
**Project:** FOG-ORCHESTRATOR 2.0 (SIH 2026-27 — NMDC Bailadila Iron Ore Haulage)  
**Status:** VALIDATED EVIDENCE — CIRCULAR FORMULAS ELIMINATED  

---

## 1. Forensic Audit & Correction of Productivity Retention

In previous Stage 5 audits, the benchmark metric "Productivity Retention" ($PR$) was erroneously formulated as:
$$PR_{\text{invalid}} = \frac{\text{Actual Delivered TPH}}{\text{Fog-Feasible Capacity Ceiling}} \times 100$$
Because the denominator was scaled down to the degraded capacity of fog, a system that halted completely or delivered 1 load was trivially reported as "100% PR", which obscured the real, severe production loss caused by fog.

In Stage 5.2, **Productivity Retention is strictly defined against the actual clear-weather production baseline**:
$$PR = \frac{Q_{\text{fog}}}{Q_{\text{clear}}} \times 100 \quad [\%]$$
where:
- $Q_{\text{clear}}$ is the actual delivered tonnage per hour completed under clear-weather baseline conditions ($V = 100\text{ m}$, dry surface).
- $Q_{\text{fog}}$ is the actual delivered tonnage per hour completed under the specific fog condition, keeping fleet size, mine layout, and simulation duration identical.

---

## 2. Empirical Productivity Retention Results

Data logged in [`docs/STAGE5_2_PRODUCTIVITY_RETENTION.csv`](file:///c:/Users/JAGADEESH%20M/OneDrive/Documents/SIH-2026-27/docs/STAGE5_2_PRODUCTIVITY_RETENTION.csv) over a 30-minute ($1{,}800\text{ s}$) haulage execution:

| Visibility ($V$) | Safe Ramp Speed ($v_{\text{safe}}$) | Clear Baseline ($Q_{\text{clear}}$) | Actual Fog Production ($Q_{\text{fog}}$) | Delivered Tonnes ($1{,}800\text{ s}$) | Productivity Retention ($PR$) | Physical Operational State |
| :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| **$100\text{ m}$** | $8.33\text{ m/s}$ ($30\text{ km/h}$) | $3{,}294.0\text{ TPH}$ | $3{,}294.0\text{ TPH}$ | $1{,}647.0\text{ t}$ ($18\text{ loads}$) | **$100.0\%$** | `NOMINAL_CLEAR` |
| **$50\text{ m}$** | $8.33\text{ m/s}$ ($30\text{ km/h}$) | $3{,}294.0\text{ TPH}$ | $3{,}294.0\text{ TPH}$ | $1{,}647.0\text{ t}$ ($18\text{ loads}$) | **$100.0\%$** | `DEGRADED_FLOW` |
| **$25\text{ m}$** | $8.33\text{ m/s}$ ($30\text{ km/h}$) | $3{,}294.0\text{ TPH}$ | $2{,}013.0\text{ TPH}$ | $1{,}006.5\text{ t}$ ($11\text{ loads}$) | **$61.1\%$** | `DEGRADED_FLOW` (Wet surface) |
| **$12\text{ m}$** | $4.79\text{ m/s}$ ($17\text{ km/h}$) | $3{,}294.0\text{ TPH}$ | $732.0\text{ TPH}$ | $366.0\text{ t}$ ($4\text{ loads}$) | **$22.2\%$** | `DEGRADED_FLOW` (Speed reduced) |
| **$10\text{ m}$** | $3.93\text{ m/s}$ ($14\text{ km/h}$) | $3{,}294.0\text{ TPH}$ | $732.0\text{ TPH}$ | $366.0\text{ t}$ ($4\text{ loads}$) | **$22.2\%$** | `DEGRADED_FLOW` (Speed reduced) |
| **$8\text{ m}$** | $2.88\text{ m/s}$ ($10\text{ km/h}$) | $3{,}294.0\text{ TPH}$ | $183.0\text{ TPH}$ | $91.5\text{ t}$ ($1\text{ load}$) | **$5.6\%$** | `DEGRADED_FLOW` (Severe crawl) |
| **$5\text{ m}$** | **$0.00\text{ m/s}$** | $3{,}294.0\text{ TPH}$ | **$0.0\text{ TPH}$** | **$0.0\text{ t}$** ($0\text{ loads}$) | **$0.0\%$** | `HALT_ZERO_MOVEMENT` |
| **$4\text{ m}$** | **$0.00\text{ m/s}$** | $3{,}294.0\text{ TPH}$ | **$0.0\text{ TPH}$** | **$0.0\text{ t}$** ($0\text{ loads}$) | **$0.0\%$** | `HALT_ZERO_MOVEMENT` |
| **$3\text{ m}$** | **$0.00\text{ m/s}$** | $3{,}294.0\text{ TPH}$ | **$0.0\text{ TPH}$** | **$0.0\text{ t}$** ($0\text{ loads}$) | **$0.0\%$** | `HALT_ZERO_MOVEMENT` |

---

## 3. Scientific Meaning of Productivity Retention

1. **Severe Fog Imposes an Inflexible Physical Tax:**
   As visibility drops from $100\text{ m}$ down to $8\text{ m}$, actual production falls by $94.4\%$ (from $3{,}294\text{ TPH}$ to $183\text{ TPH}$). This decline is not an engineering defect; it is a direct consequence of Newton's second law and braking physics on wet iron ore ramps. To pretend that production is retained at $100\%$ under severe fog is scientifically fraudulent.
2. **What FOG-ORCHESTRATOR Actually Protects:**
   The role of FOG-ORCHESTRATOR is **NOT to artificially defeat the physics of fog**, but rather:
   - To **safely extract the maximum physically permissible tonnage** in the $10\text{ m} \to 25\text{ m}$ visibility window ($22.2\%\dots 61.1\%$ retention) where unassisted manual mines shut down completely due to lack of visibility.
   - To **prevent catastrophic equipment collisions** while operating in this degraded regime.
   - To **prevent accordion queue formation** on hazardous single-lane mountain switchbacks.
   - To **instantly recover to $100\%$ production** the moment fog lifts above $50\text{ m}$, eliminating the $30\text{--}60\text{ minute}$ post-fog administrative restart delays common in conventional mine dispatch.
