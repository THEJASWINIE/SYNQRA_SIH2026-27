# FINAL D5–D13 CAUSAL FORENSIC AUDIT
## FOG-ORCHESTRATOR 2.0 — Forensic Reconcilation of Degradation Scenarios
**Project:** SIH26007 — Fog & Low-Visibility Mining Fleet Orchestrator  
**Audit Date:** 2026-09-21  
**Auditor:** Systems Architect & Safety-Critical Verification Auditor  
**Audit Standard:** Forensic Causal Traceability Protocol (§2, §22)

---

## 1. Executive Summary of Forensic Reconcilation

This document provides the definitive, per-scenario causal analysis of Scenarios D5 through D13. It establishes the mathematical, physical, and architectural mechanisms governing each failure mode, reconciling all residual violations and firmly establishing the observability boundaries of single-source data validation.

```
                                CAUSAL TRACE CHAIN
┌───────────┐    ┌─────────────┐    ┌─────────────┐    ┌──────────┐    ┌──────────┐
│ INJECTED  │ ──►│ TELEMETRY   │ ──►│ DATA HEALTH │ ──►│ R_eff    │ ──►│ CANONICAL│
│ FAULT     │    │ INGESTION   │    │ DIAGNOSIS   │    │ SCALING  │    │ PHYSICS  │
└───────────┘    └─────────────┘    └─────────────┘    └──────────┘    └──────────┘
                                                                             │
                                                                             ▼
┌───────────┐    ┌─────────────┐    ┌─────────────┐    ┌──────────┐    ┌──────────┐
│ STOPPING  │ ◄──│ STOPPING    │ ◄──│ APPLIED     │ ◄──│ LOCAL    │ ◄──│ v_safe   │
│ MARGIN    │    │ DISTANCE    │    │ SPEED       │    │ GOVERNOR │    │ ENVELOPE │
└───────────┘    └─────────────┘    └─────────────┘    └──────────┘    └──────────┘
```

---

## 2. Granular Forensic Dossiers: Scenarios D5 to D13

### Scenario D5: Stale Telemetry (Frozen Link)
- **Fault Injected:** Uplink dies at $t=1800\text{ s}$ during sudden fog influx; packets cease arriving.
- **Ground Truth Visibility:** $12.0\text{ m}$ ($t \in [1800, 5400]\text{ s}$).
- **Reported Telemetry:** Zero packets after $t=1800\text{ s}$; last received value was $50.0\text{ m}$.
- **Health State Transitions:**
  - $t \in [1800, 1830)\text{ s}$ (Elapsed $< 30\text{ s}$): `HEALTHY` (Confidence $1.0$).
  - $t \in [1830, 1860)\text{ s}$ (Elapsed $30\text{ to }60\text{ s}$): `DEGRADED` (Confidence $0.70$).
  - $t \in [1860, 1920)\text{ s}$ (Elapsed $60\text{ to }120\text{ s}$): `STALE` (Confidence $0.40$).
  - $t \ge 1920\text{ s}$ (Elapsed $\ge 120\text{ s}$): `UNAVAILABLE` (Confidence $0.0$).
- **$R_{\text{effective}}$ Dynamic:** $50.0\text{ m} \to 35.0\text{ m} \to 25.0\text{ m} \to 8.0\text{ m}$.
- **$v_{\text{safe}}$ Dynamic:** $11.11\text{ m/s} \to 10.83\text{ m/s} \to 10.14\text{ m/s} \to 2.69\text{ m/s}$ ($9.7\text{ km/h}$).
- **$v_{\text{command}}$:** Clamped strictly to $v_{\text{safe}}$ by Level 1 governor.
- **Stopping Margin:** 
  - For $t \in [1800, 1920)\text{ s}$: Negative (violates $12.0\text{ m}$ true envelope).
  - For $t \ge 1920\text{ s}$: $+5.20\text{ m} \ge 0$ ($S_{\text{stop}} = 3.0\text{ m} + 5.0\text{ m} = 8.0\text{ m} \le 12.0\text{ m}$).
- **Violation Count:** Baseline B0 = 3,601; Treatment B1 = 120 (**96.7% reduction**).
- **Root Cause of Remaining 120:** Mathematical consequence of engineering parameter $T_{\text{GRACE\_PERIOD}} = 120.0\text{ s}$. The health layer deliberately avoids premature emergency stopping during brief radio shadow switchbacks. During those 120 seconds, stopping distance exceeds $12\text{ m}$.
- **Detection Status:** Initial degradation detected at $t=1830\text{ s}$ ($30.0\text{ s}$ latency).
- **Safety Status:** Validated graceful degradation to crawling floor.
- **Evidence Level:** L9 Simulation / L7 HIL verified.
- **Final Interpretation:** B1 successfully eliminates $3481\text{ s}$ of exposure, confining violations strictly to the configured grace period.

---

### Scenario D6: Stuck-At Sensor
- **Fault Injected:** Telemetry value frozen at $45.0\text{ m}$ while true visibility drops to $12.0\text{ m}$ at $t=1800\text{ s}$.
- **Ground Truth Visibility:** $12.0\text{ m}$.
- **Reported Telemetry:** Valid 1 Hz packets continuously reporting $45.0\text{ m}$ with valid sequence and timestamp.
- **Health State Transitions:**
  - In a 10-sample rolling buffer at 1 Hz, elapsed buffer duration is $9.0\text{ s}$, which cannot satisfy $T_{\text{STUCK\_MIN}} = 300.0\text{ s}$. Remains `HEALTHY`.
  - If buffer is extended to $300\text{ s}$, triggers `DEGRADED` (Fault: `STUCK_AT`) at $t=2100\text{ s}$.
- **$R_{\text{effective}}$ Dynamic:** $45.0\text{ m}$ (or $31.5\text{ m}$ if DEGRADED).
- **$v_{\text{safe}}$ Dynamic:** $11.11\text{ m/s}$ (or $9.60\text{ m/s}$).
- **Stopping Margin:** Negative throughout ($S_{\text{stop}} \approx 14.8\text{ m} > 12.0\text{ m}$).
- **Violation Count:** Baseline B0 = 3,601; Treatment B1 = 3,601 (**0% reduction**).
- **Root Cause:** Fundamental ambiguity of single-source variance. A sensor reporting constant $45.0\text{ m}$ on a clear afternoon has zero variance and is correct; in a sudden fog bank, it has zero variance and is wrong. Even if flagged as `DEGRADED` with a conservative 30% penalty ($31.5\text{ m}$), $31.5\text{ m} > 12.0\text{ m}$, failing to prevent stopping violations without an independent reference.
- **Detection Status:** Undetected in nominal buffer / $300\text{ s}$ detection latency in extended buffer.
- **Safety Status:** **NEGATIVE RESULT — Unresolved without independent sensor reference.**
- **Evidence Level:** L9 Simulation / Mathematical Boundary.
- **Final Interpretation:** Preserved as an honest scientific boundary: single-source statistical variance cannot reconstruct missing physical ground truth.

---

### Scenario D7: Sensor Bias (+30m Offset)
- **Fault Injected:** $+30.0\text{ m}$ additive offset to all true readings ($R_{\text{reported}} = R_{\text{true}} + 30\text{ m}$).
- **Ground Truth Visibility:** $12.0\text{ m}$ ($t \in [1800, 5400]\text{ s}$).
- **Reported Telemetry:** $42.0\text{ m}$ with valid headers, sequence, timestamp, and natural variance.
- **Health State Transitions:** Strictly `HEALTHY` (Confidence $1.0$).
- **$R_{\text{effective}}$ Dynamic:** $42.0\text{ m}$.
- **$v_{\text{safe}}$ Dynamic:** $11.11\text{ m/s}$ ($40.0\text{ km/h}$).
- **Stopping Margin:** Negative ($-16.3\text{ m}$).
- **Violation Count:** Baseline B0 = 3,601; Treatment B1 = 3,601 (**0% reduction**).
- **Root Cause:** **Class C — Fundamentally unobservable without independent reference.** An optical transmissometer reading $42\text{ m}$ when reality is $12\text{ m}$ is physically indistinguishable from a day where visibility is genuinely $42\text{ m}$.
- **Detection Status:** Undetected.
- **Safety Status:** **NEGATIVE RESULT — Unresolved prototype limitation.**
- **Evidence Level:** L9 Simulation.
- **Final Interpretation:** Proves that software validation cannot substitute for redundant hardware sensing modalities.

---

### Scenario D8: High-Variance Analog Noise
- **Fault Injected:** Gaussian noise $\mathcal{N}(0, 25^2)$ added to true visibility.
- **Ground Truth Visibility:** $20.0\text{ m}$.
- **Reported Telemetry:** Noisy measurements fluctuating between $1.0\text{ m}$ and $75.0\text{ m}$.
- **Health State Transitions:** Chattering between `HEALTHY` and `DEGRADED` (when standard deviation $> 20.0\text{ m}$).
- **$R_{\text{effective}}$ Dynamic:** Fluctuates dynamically with $0.70$ penalty during noisy bursts.
- **Stopping Margin:** Intermittently violated when noise creates positive spikes before variance detection triggers.
- **Violation Count:** Baseline B0 = 1,805.6; Treatment B1 = 1,663.5 (**7.9% reduction**).
- **Root Cause:** Rule-based variance detection acts retrospectively over a window ($N=10$). Individual positive spikes pass through before the window std dev exceeds threshold. Aggressive low-pass filtering was deliberately avoided to prevent phase lag during sudden fog onset.
- **Detection Status:** Intermittent detection ($3.5\text{ s}$ mean latency).
- **Safety Status:** Modest operational filtering; safety closure not guaranteed under severe noise.
- **Evidence Level:** L9 Simulation.
- **Final Interpretation:** Documents the fundamental trade-off between transient noise rejection and safety-critical fog detection latency.

---

### Scenario D9: Conflicting Multi-Source Telemetry
- **Fault Injected:** Primary sensor reports $50.0\text{ m}$; secondary sensor reports $15.0\text{ m}$ (Discrepancy $= 35.0\text{ m} > 25.0\text{ m}$).
- **Ground Truth Visibility:** $15.0\text{ m}$.
- **Reported Telemetry:** Dual streams with active spatial or hardware divergence.
- **Health State Transitions:** Immediately enters `CONFLICTING` (Fault: `CROSS_SOURCE_CONFLICT`).
- **$R_{\text{effective}}$ Dynamic:** $\min(50.0, 15.0) \times 0.70 = 10.5\text{ m}$.
- **$v_{\text{safe}}$ Dynamic:** $3.86\text{ m/s}$ ($13.9\text{ km/h}$).
- **Stopping Margin:** $+4.50\text{ m} \ge 0$ ($S_{\text{stop}} = 5.5\text{ m} + 5.0\text{ m} = 10.5\text{ m} \le 15.0\text{ m}$).
- **Violation Count:** Baseline B0 = 3,601; Treatment B1 = 0 (**100% elimination**).
- **Root Cause:** Multi-source validation allows unambiguous conflict identification; conservative resolution ($\min(R_1, R_2) \times 0.70$) guarantees stopping closure.
- **Detection Status:** Immediate ($1.0\text{ s}$ latency).
- **Safety Status:** Strongly validated under dual-sensor architecture.
- **Evidence Level:** L9 Simulation (Simulated independent sources).
- **Final Interpretation:** Definitive proof that hardware redundancy resolves the single-source observability boundary.

---

### Scenario D10: Intermittent Telemetry (40s Drop / 20s Active)
- **Fault Injected:** 40 seconds of packet drops followed by 20 seconds of healthy packets, repeating every 60 seconds.
- **Ground Truth Visibility:** $20.0\text{ m}$ ($t \in [1800, 5400]\text{ s}$).
- **Reported Telemetry:** Packets absent for 40s, then arrive for 20s.
- **Health State Transitions:** In each 60s cycle: $0..30\text{ s}$ elapsed $\implies$ `HEALTHY`; $30..40\text{ s}$ elapsed $\implies$ `DEGRADED`; $40..60\text{ s}$ $\implies$ `HEALTHY`.
- **$R_{\text{effective}}$ Dynamic:** During first 40s drop: $50.0\text{ m} \to 35.0\text{ m}$. For all subsequent drops: $20.0\text{ m} \to 14.0\text{ m}$.
- **Stopping Margin:** Negative strictly during the first 40 seconds ($t \in [1800, 1840]\text{ s}$). Margin $\ge 0$ for all subsequent 3560 seconds.
- **Violation Count:** Baseline B0 = 40.0; Treatment B1 = 40.0 (**0% reduction**).
- **Root Cause:** The 40 violations occur exclusively during the very first drop interval when fog rolls in while communication is absent. Because $T_{\text{DEGRADED}} = 30\text{ s}$, the system maintains 50m for 30s, and the 30% penalty ($35\text{ m}$) still exceeds $20\text{ m}$. Once the first 20m packet arrives at $t=1840\text{ s}$, both B0 and B1 latch 20m, preventing any violations in subsequent drops.
- **Detection Status:** Detected at $30.0\text{ s}$.
- **Safety Status:** Residual violation window during initial transition; zero stopping violations observed in subsequent cycles within the tested model scope.
- **Evidence Level:** L9 Simulation.
- **Final Interpretation:** Reconciles the residual 40 violations as an unavoidable transition window under single-channel radio drops.

---

### Scenario D11: Uplink Communication Severance
- **Fault Injected:** Total RF link drop at $t=1800\text{ s}$; central telemetry completely lost.
- **Ground Truth Visibility:** $12.0\text{ m}$.
- **Reported Telemetry:** Zero packets after $t=1800\text{ s}$.
- **Health State Transitions:** Same as D5. Transitions to `UNAVAILABLE` at $t=1920\text{ s}$.
- **$R_{\text{effective}}$ Dynamic:** $8.0\text{ m}$ crawling speed floor after 120s.
- **$v_{\text{safe}}$ Dynamic:** $2.69\text{ m/s}$ ($9.7\text{ km/h}$).
- **Stopping Margin:** $+5.20\text{ m} \ge 0$ for all $t \ge 1920\text{ s}$.
- **Violation Count:** Baseline B0 = 3,601; Treatment B1 = 120 (**96.7% reduction**).
- **Root Cause:** Local vehicle governor takes autonomous authority upon watchdog timeout, clamping speed to fail-safe crawling floor.
- **Detection Status:** Detected at $30\text{ s}$, locked at $120\text{ s}$.
- **Safety Status:** Validated autonomous fail-safe.
- **Evidence Level:** L9 Simulation / L7 HIL verified.
- **Final Interpretation:** Proves that local vehicle safety functions independently of central cloud/server availability.

---

### Scenario D12: Complete Environmental Sensor Loss (Blackout from t=0)
- **Fault Injected:** Environmental station completely dead from power-on; zero packets ever transmitted.
- **Ground Truth Visibility:** $20.0\text{ m}$ ($t \in [1800, 5400]\text{ s}$).
- **Reported Telemetry:** None.
- **Health State Transitions:** Permanently `UNAVAILABLE` from $t=0$.
- **$R_{\text{effective}}$ Dynamic:** Strictly $8.0\text{ m}$ crawling speed floor.
- **$v_{\text{safe}}$ Dynamic:** Strictly $2.69\text{ m/s}$ ($9.7\text{ km/h}$).
- **Stopping Margin:** $+7.0\text{ m} \ge 0$ continuously across entire 2 hours.
- **Violation Count:** Baseline B0 = 3,601; Treatment B1 = 0 (**100% elimination**).
- **Root Cause:** Fail-closed software initialization. The system refuses to authorize nominal speed without verified valid telemetry.
- **Detection Status:** Immediate ($0.0\text{ s}$ latency).
- **Safety Status:** Strongly validated fail-closed design.
- **Evidence Level:** L9 Simulation / L7 HIL verified.
- **Final Interpretation:** Confirms zero-telemetry fail-closed behavior.

---

### Scenario D13: Plausible-But-Wrong Telemetry (Class C)
- **Fault Injected:** True visibility drops to $5.0\text{ m}$, reported visibility stays at $50.0\text{ m}$ with valid headers, timestamp, sequence, and range.
- **Ground Truth Visibility:** $5.0\text{ m}$.
- **Reported Telemetry:** Valid 1 Hz packets of $50.0\text{ m}$.
- **Health State Transitions:** Strictly `HEALTHY` (False Negative).
- **$R_{\text{effective}}$ Dynamic:** $50.0\text{ m}$.
- **$v_{\text{safe}}$ Dynamic:** $11.11\text{ m/s}$ ($40.0\text{ km/h}$).
- **Stopping Margin:** Strongly negative ($-18.2\text{ m}$).
- **Violation Count:** Baseline B0 = 3,601; Treatment B1 = 3,601 (**0% reduction**).
- **Root Cause:** **Class C Fundamental Limitation.** Single-source telemetry validation is mathematically blind to plausible lies without physical ground truth reference.
- **Detection Status:** Undetected.
- **Safety Status:** **NEGATIVE RESULT — Hard Systemic Boundary.**
- **Evidence Level:** L9 Simulation / Mathematical Boundary.
- **Final Interpretation:** Permanent negative result documented as the primary boundary of single-sensor architectures.

---

## 3. Summary Reconciliation Table

| Scenario | Fault Type | B0 Violations | B1 Violations | Reduction | Detection Latency | Observability Boundary | Final Research Status |
|---|---|---|---|---|---|---|---|
| **D5** | Stale Telemetry | 3,601.0 | 120.0 | **96.7%** | 30.0 s | Governed by $T_{\text{GRACE}}$ | **VALIDATED** |
| **D6** | Stuck-At Sensor | 3,601.0 | 3,601.0 | **0.0%** | Undetected / 300 s | Ambiguous without Ref | **NEGATIVE RESULT** |
| **D7** | Sensor Bias | 3,601.0 | 3,601.0 | **0.0%** | Undetected | Class C Unobservable | **NEGATIVE RESULT** |
| **D8** | Analog Noise | 1,805.6 | 1,663.5 | **7.9%** | 3.5 s | Window Variance Lag | **PARTIAL** |
| **D9** | Multi-Source Conflict | 3,601.0 | 0.0 | **100.0%** | 1.0 s | Resolved by Dual Sensing | **VALIDATED (SIM)** |
| **D10** | Intermittent Telemetry | 40.0 | 40.0 | **0.0%** | 30.0 s | Initial Drop Latency | **ACKNOWLEDGED** |
| **D11** | Comm Loss | 3,601.0 | 120.0 | **96.7%** | 30.0 s | Governed by $T_{\text{GRACE}}$ | **VALIDATED** |
| **D12** | Complete Loss | 3,601.0 | 0.0 | **100.0%** | 0.0 s | Fail-Closed Design | **VALIDATED** |
| **D13** | Plausible-But-Wrong | 3,601.0 | 3,601.0 | **0.0%** | Undetected | Class C Unobservable | **NEGATIVE RESULT** |
