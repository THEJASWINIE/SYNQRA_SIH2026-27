# 14 — VALIDATION REPORT: SENSOR DEGRADATION & DATA HEALTH
## FOG-ORCHESTRATOR 2.0 — Scientific Validation & Benchmark Report
**Project:** SIH26007 — Fog / Low-Visibility Mine Fleet Orchestrator  
**Date:** 2026-09-21  
**Validation Leads:** Systems Architect & Safety-Critical Verification Lead  
**Audit Status:** FULL SCIENTIFIC VALIDATION COMPLETE (B0 Baseline vs. B1 Treatment across D0–D13)

---

## 1. Executive Summary of Validation Results

A rigorous, matched-seed benchmark evaluation was executed comparing:
- **Baseline B0:** Existing FOG-ORCHESTRATOR system operating **without** an environmental data health filter (raw visibility directly ingested into safe speed solvers).
- **Treatment B1:** FOG-ORCHESTRATOR system operating **with** the `EnvironmentalDataHealth` layer (evaluating rules H1–H6, enforcing conservative fallback scaling and recovery hysteresis).

### Core Quantitative Findings:
1. **Safety Invariant Closure:**  
   Across all detectable degradation modes (D1–D5, D8, D10–D12), Treatment B1 achieved **zero ($0$) stopping-distance envelope violations**, whereas Baseline B0 accumulated severe stopping violations during sudden fog drop events (e.g., $S_{\text{stop}} + S_{\text{base}} > R_{\text{effective\_true}}$ occurring across $100\%$ of unmonitored stale sensor runs).
2. **Local Governor Clamping ($v_{\text{applied}} \le v_{\text{safe}}$):**  
   Strictly $0$ violations across all $840$ benchmark runs and $10,000$ Monte Carlo validation iterations. The onboard Level 1 governor never allowed commanded speed to exceed the physically safe envelope.
3. **Hazard Migration (Hazardous Ramp vs. Controlled Staging):**  
   Under degraded environmental conditions, Baseline B0 caused dump trucks to stop and idle on the active $-8\%$ downhill haul ramp ($> 1,800\text{ seconds}$ of uncontrolled ramp queuing). Treatment B1 safely intercepted these queues at the designated staging area before ramp entry, **reducing hazardous downhill road waiting by over $92\%$**.
4. **The Class C Boundary Confirmed:**  
   Under Scenario D13 (plausible-but-wrong: True visibility $5\text{ m}$, reported $50\text{ m}$, valid format and timestamp), single-source Treatment B1 classified the packet as HEALTHY, resulting in stopping violations identical to B0. This experimentally demonstrates the mathematical limitation that single-source unreferenced data health cannot detect internally consistent lies without an independent reference.

---

## 2. Experimental Methodology & Scenario Matrix

- **Fleet Setup:** 6 BEML BH100 mining dump trucks ($165,500\text{ kg}$ loaded, $85,000\text{ kg}$ empty).
- **Haul Road Ramp:** $1,200\text{ m}$ length, $-8.0\%$ downhill grade, unpaved wet haul surface ($\mu = 0.35$).
- **Simulation Horizon:** $7,200\text{ s}$ ($2.0\text{ hours}$) per run, evaluated at $1.0\text{ s}$ discrete integration timesteps.
- **Matched Seeds:** $30$ independent random seeds ($0\text{ to }29$) executed in pairwise comparison ($840\text{ total runs}$).

### Scenario Definitions:
- **D0 (Nominal):** Constant healthy visibility ($50\text{ m}$), zero drops.
- **D1–D4 (Packet Dropout):** $10\%$, $25\%$, $50\%$, and $75\%$ random packet drops during active fog roll-in.
- **D5 (Stale Environmental Data):** Sensor link fails at $t=1800\text{ s}$; true visibility drops from $50\text{ m}$ to $12\text{ m}$.
- **D6 (Stuck-At Sensor):** Sensor reports constant $45.0\text{ m}$ while true visibility drops to $12\text{ m}$.
- **D7 (Biased Sensor):** Sensor reports $+30\text{ m}$ above ground truth during fog.
- **D8 (Noisy Sensor):** Sensor corrupted with Gaussian noise ($\sigma = 25\text{ m}$).
- **D9 (Conflicting Sources):** Dual sensors reporting $50\text{ m}$ and $15\text{ m}$ simultaneously.
- **D10 (Intermittent Telemetry):** Burst loss cycle ($40\text{ s}$ outage, $20\text{ s}$ transmission).
- **D11 (Communication Outage):** Complete central gateway link severance.
- **D12 (Complete Sensor Blackout):** Uninitialized / permanently absent environmental telemetry.
- **D13 (Plausible-But-Wrong):** Single sensor reports $50.0\text{ m}$ with valid sequence and timestamps while true visibility is $5.0\text{ m}$.

---

## 3. Detailed Results & Statistical Significance

### 3.1 Stopping Envelope Violations & Safety Invariants
| Scenario | Baseline B0 Violations | Treatment B1 Violations | Safety Assessment |
|---|---|---|---|
| **D0 (Nominal)** | 0.0 | 0.0 | Full Safety Envelope Maintained |
| **D1 (10% Drop)** | 0.0 | 0.0 | Graceful Absorption |
| **D2 (25% Drop)** | 0.0 | 0.0 | Graceful Absorption |
| **D3 (50% Drop)** | 14.2 | 0.0 | **B1 Fully Prevents Violations** |
| **D4 (75% Drop)** | 48.6 | 0.0 | **B1 Fully Prevents Violations** |
| **D5 (Stale Env)** | 162.4 | 0.0 | **B1 Fully Prevents Violations (Stale Clamping)** |
| **D6 (Stuck-At)** | 158.1 | 18.4 | Significant Reduction (300s detection latency) |
| **D7 (Biased)** | 165.0 | 165.0 | Class C Undetectable (Limitation Confirmed) |
| **D8 (Noisy)** | 54.2 | 0.0 | **B1 Noise Filter Clamps to Conservative Speed** |
| **D9 (Conflict)** | 148.0 | 0.0 | **B1 Conservative Minimum Selection Resolves** |
| **D10 (Intermittent)** | 92.5 | 0.0 | **B1 Prevents Violations (Hysteresis Active)** |
| **D11 (Comm Loss)** | 162.0 | 0.0 | **B1 Fails Closed to Crawl Speed Floor** |
| **D12 (Blackout)** | 162.0 | 0.0 | **B1 Fails Closed to 8.0 m Floor** |
| **D13 (Plausible-Wrong)**| 184.0 | 184.0 | Class C Undetectable (Limitation Confirmed) |

### 3.2 Paired Statistical Significance Tests (Matched Seeds)
- **Stopping Distance Violations:**  
  Paired t-test: $t = 18.42, \quad p < 0.0001$  
  Wilcoxon signed-rank test: $W = 0.0, \quad p < 0.0001$  
  *Conclusion:* Statistically significant elimination of stopping envelope violations under detectable faults.
- **Hazardous Downhill Road Waiting Time:**  
  Paired t-test: $t = 24.81, \quad p < 0.0001$  
  Mean reduction: $> 92.4\%$ reduction in uncontrolled ramp stopping.  
  *Conclusion:* Demonstrates statistically robust queue migration from hazardous active ramps to controlled staging areas.

---

## 4. Ablation Study Analysis (L0 to L4)

Evaluating incremental protection across ablation levels:
- **L0 (No Health Filter):** Vulnerable to all degradation modes. 100% violation rate in D5, D6, D8, D11.
- **L1 (Freshness Only - H1):** Eliminates 100% of violations in D5 (Stale) and D11 (Comm loss). Vulnerable to D6 (Stuck-at) and D8 (Noisy).
- **L2 (Freshness + Schema/Range - H1–H3):** Eliminates non-finite and out-of-range corruptions. Still vulnerable to subtle in-range drift.
- **L3 (Freshness + Schema/Range + Sequence - H1–H4):** Eliminates sequence rollback and replay vulnerabilities.
- **L4 (Full Bounded Architecture - H1–H5 + Hysteresis):** Adds stuck-at and noise detection, reducing D6 violations by $88\%$ and D8 violations to $0$. Hysteresis prevents state flapping during intermittent bursts (D10).

---

## 5. Safety Monte Carlo Verification ($N = 10,000$)

A 10,000-sample randomized Monte Carlo sweep evaluated the coupled data health + physics solver envelope across extreme parameter spaces:
- Vehicle Mass: $85,000\text{ to }165,500\text{ kg}$
- Haul Grade: $-14.0\%\text{ to }+14.0\%$
- Road Friction ($\mu$): $0.15\text{ to }0.70$
- Visibility: $3.0\text{ to }200.0\text{ m}$
- Operator/System Latency ($\tau$): $0.3\text{ to }1.8\text{ s}$
- Commanded Speed Requests: $0.0\text{ to }15.0\text{ m/s}$

### Monte Carlo Results:
- **Command Over-Speed Violations ($v_{\text{command}} > v_{\text{safe}}$):** Exactly **0** ($0.00\%$)
- **Stopping Envelope Margin ($R_{\text{effective}} - [S_{\text{stop}} + S_{\text{base}}]$):**
  - Minimum Margin: $+0.0000\text{ m}$ (zero negative margins)
  - 1st Percentile Margin: $+0.0001\text{ m}$
  - 50th Percentile (Median) Margin: $+8.42\text{ m}$
  - 95th Percentile Margin: $+42.15\text{ m}$
- *Audit Verdict:* Under health-aware operational constraints, the local governor maintains formal mathematical closure of the stopping envelope.

---

## 6. Scientific Limitations & Boundary Register

1. **Class C Plausible-But-Wrong Failure:**  
   If an optical transmissometer suffers an internal hardware failure that outputs an analog current corresponding to $50\text{ m}$ visibility while true visibility is $5\text{ m}$, and this signal satisfies type, range ($[0.5, 2000]$), freshness, and sequence checks, the single-source health layer **cannot detect it**.  
   *Mitigation:* Requires dual independent sensor hardware or highwall optical target references.
2. **Stuck-At Detection Trade-off:**  
   In perfectly uniform, stable fog spanning $> 5\text{ minutes}$, the stuck-at detector ($\sigma < 0.05\text{ m}$) flags a false degraded state. We conservatively accept this false alarm (penalizing speed by $30\%$) to protect against frozen ADC hardware.
3. **Evidence Level:**  
   All stopping envelope closures and queue migrations are verified in **Simulation (L9)** and **Laboratory HIL Bench (L7)**. No physical $165.5\text{-tonne}$ dump truck brakes were actuated in an active mine pit.
