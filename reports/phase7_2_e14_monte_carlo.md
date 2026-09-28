# EXPERIMENT E14 — MONTE CARLO SAFETY ROBUSTNESS REPORT

**Project:** FOG-ORCHESTRATOR 2.0 (SIH 2026-27 — SIH26007)  
**Classification:** Stochastic Safety Robustness Analysis (10,000 Scenarios)  
**Evidence Level:** L9 — Computational Monte Carlo Analysis  
**Dataset Reference:** [`data/monte_carlo_results.csv`](file:///c:/Users/JAGADEESH%20M/OneDrive/Documents/SIH-2026-27/data/monte_carlo_results.csv) (Sampled 2,000 runs)  

---

## 1. Audit Disclaimer

> [!NOTE]
> **METHODOLOGY CLASSIFICATION**  
> This experiment constitutes a computational **Monte Carlo robustness analysis** across 10,000 multi-dimensional environmental and vehicular parameter combinations. It is not an ISO 26262 ASIL-D or IEC 61508 formal probabilistic certification.

---

## 2. Parameter Sampling Ranges (Uniform Random Distributions)

| Parameter Description | Variable | Sampled Range | Justification / Engineering Basis |
|:---|:---:|:---:|:---|
| **Operating Mass** | $m$ | 74,000 kg – 165,500 kg | BEML BH100 tare weight to maximum gross vehicle weight |
| **Tire-Road Friction** | $\mu$ | 0.20 – 0.65 | Extreme wet mud/slurry to dry crushed aggregate |
| **Civil Road Grade** | $\theta$ | -8.0% to +8.0% | DGMS permissible maximum haul road slope range |
| **Atmospheric Visibility** | $R_{\text{eff}}$ | 3.0 m – 100.0 m | Extreme dense fog blackout to clear day |
| **Local Safety Latency** | $\tau_{\text{local}}$ | 0.350 s – 0.650 s | Nominal pipeline to extreme cold-hydraulic lag |

---

## 3. Robustness Results Across 10,000 Scenarios

| Performance Metric | Total Count | Rate (%) | P95 Value | P99 Value | Worst-Case Observed |
|:---|:---:|:---:|:---:|:---:|:---:|
| **Stopping Distance Violations ($S_{\text{stop}} > R_{\text{eff}}$)** | **0** | **0.00%** | N/A | N/A | **0 (Zero Violations)** |
| **Minimum Remaining Sight Margin** | 10,000 | 100% Valid | +4.12 m | +1.85 m | **+0.00 m (At $v_{\text{safe}}$ boundary)** |
| **Safe Speed Invariant Violations** | **0** | **0.00%** | N/A | N/A | **0 (Zero Violations)** |
| **Dense Fog Safe Halts ($R_{\text{eff}} \le 5\text{ m}$)** | 204 runs | 2.04% | 0.0 m/s | 0.0 m/s | **0.00 m/s (Strict Zero Speed)** |

---

## 4. Key Engineering Takeaway

Because the local safety governor solves the inverse quadratic stopping equation with explicit parameter adaptation, changing grade, mass, or friction dynamically compresses the allowable speed. In 10,000 randomly selected operational conditions, the vehicle never entered an unrecoverable braking state.
