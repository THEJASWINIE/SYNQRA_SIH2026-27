# SENSOR DEGRADATION RESEARCH CONTRIBUTION STATEMENT
## FOG-ORCHESTRATOR 2.0 — Scientific & Architectural Demarcation
**Project:** SIH26007 — Fog & Low-Visibility Mining Fleet Orchestrator  
**Audit Date:** 2026-09-21  
**Lead Auditor:** Systems Architect & Safety-Critical Verification Auditor  
**Audit Standard:** Strict Epistemic Demarcation Protocol (§28)

---

## 1. Formal Demarcation of Research Contribution

To prevent unwarranted claims of novelty and ensure strict scientific integrity, the contributions of this research extension are categorized into four distinct layers:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ 1. KNOWN COMPONENTS (Prior Art & Baseline Engineering)                      │
│    - Rule-based schema, range, and sequence checks (FDIA literature)        │
│    - Longitudinal vehicle physics (Coulomb friction, grade resistance)      │
│    - Level 1 Local Vehicle Safety Governor (pre-existing frozen core)      │
│    - Macro fleet management dispatch (commercial FMS standards)             │
├─────────────────────────────────────────────────────────────────────────────┤
│ 2. INTEGRATION CONTRIBUTION (Core Architectural Work)                      │
│    - Direct causal coupling: Telemetry Confidence ➔ R_effective Scaling     │
│    - Downstream coupling: R_effective ➔ Multi-Constraint v_stop ➔ v_command │
│    - Fleet coupling: Degraded Confidence ➔ Ramp Capacity Slot Throttling    │
│    - Inviolable hierarchy preservation: Zero actuator authority in health   │
├─────────────────────────────────────────────────────────────────────────────┤
│ 3. EXPERIMENTAL FINDINGS (Empirically Validated Facts)                      │
│    - 100% elimination of stopping violations under complete loss & conflict │
│    - 96.7% reduction in stale exposure; residual 120s matches T_GRACE window│
│    - 100% reduction in hazardous downhill ramp waiting via staged queueing   │
│    - 10,000-sample Safety Monte Carlo with zero safety invariant violations │
├─────────────────────────────────────────────────────────────────────────────┤
│ 4. UNRESOLVED LIMITATIONS (Hard Scientific Boundaries)                      │
│    - Class C plausible-but-wrong telemetry (D13) unobservable single-source │
│    - Persistent sensor bias (D7) indistinguishable from valid atmosphere    │
│    - Single-source stuck-at variance (D6) cannot reconstruct ground truth   │
│    - Physical validation bounded to ESP32 HIL; no active-mine hauler trials │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Explicit Breakdown

### A. What Was Already Known (Not Claimed as Novel)
1. **Telemetry Ingestion Filtering:** Freshness timeouts, rolling variance checks, sequence monotonicity counters, and type/schema validators are established techniques across aerospace, automotive (ISO 26262), and industrial process control (IEC 61508). We do not claim novelty for these basic diagnostic primitives.
2. **Physics-Based Stopping Distance Equations:** The analytical quadratic calculation of braking distance:
   $$S_{\text{stop}}(v) = v \cdot \tau_{\text{total}} + \frac{v^2}{2 a_{\text{dec}}}$$
   is standard heavy automotive mechanical engineering (ISO 3450).
3. **Local Safety Governance:** The concept that an onboard vehicle governor overrides external central dispatch was established in Phase 1–8 of FOG-ORCHESTRATOR 2.0.

### B. What Is the Actual Integration Contribution
The genuine contribution of this extension is **closed-loop causal coupling across four operational tiers**:
1. **Bridging the Environmental Telemetry Gap:** Discovering and proving that environmental visibility previously bypassed data-health trust filtering, directly threatening stopping distance safety during sudden fog banks.
2. **Deterministic, Fail-Closed Parameter Scaling:** Formulating an auditable, non-ML scaling policy that converts telemetry health states (`HEALTHY`, `DEGRADED`, `STALE`, `CONFLICTING`, `UNAVAILABLE`) into explicit physical boundaries ($R_{\text{effective}}$) without introducing optimistic replacement guesses.
3. **Multi-Tier Causal Propagation:** Enforcing that degraded sensor health automatically tightens physical stopping distance envelopes, clamps local speed commands, expands regulated traffic headway, and throttles ramp admission slots.
4. **Preserving Operational Authority:** Demonstrating that data health can inform global capacity without ever acquiring authority to directly actuate brakes or override local vehicle safety governors.

### C. What Was Experimentally Demonstrated
1. **Stopping Envelope Closure:** In a 30-matched-seed benchmark (840 simulation runs across 14 scenarios), Treatment B1 completely eliminated stopping envelope violations under complete sensor loss ($D12$) and multi-source conflict ($D9$), and reduced violations by $96.7\%$ under stale telemetry ($D5$) and communication severance ($D11$).
2. **Hazardous Queue Relocation:** Quantified that traffic orchestration does not merely reduce waiting—it relocates dwell time from high-risk $-8\%$ downhill ramps into flat, controlled staging zones, achieving a **100% reduction in hazardous ramp waiting** ($725.4\text{ s} \to 0.0\text{ s}$, $p < 10^{-22}$).
3. **Mathematical Safety Closure:** Verified across 10,000 randomized Monte Carlo samples that $v_{\text{command}} \le v_{\text{safe}}$ and $S_{\text{stop}} + S_{\text{base}} \le R_{\text{effective}}$ hold with zero violations.

### D. What Remains Unresolved (Hard Real-World Limitations)
1. **Class C Plausible-But-Wrong Telemetry (D13):** If an unreferenced optical sensor reports $50\text{ m}$ visibility during dense $5\text{ m}$ fog with valid headers and reasonable variance, software data health is mathematically powerless to detect the error.
2. **Persistent Systematic Sensor Bias (D7):** An additive offset $+30\text{ m}$ cannot be distinguished from a valid atmospheric condition by single-channel receivers.
3. **Stuck-At Ground Truth Ambiguity (D6):** Zero variance indicates a frozen signal, but does not provide the true visibility value required to compute safe speed.
4. **Physical Deployment Scope:** Vehicle dynamics remain validated in high-fidelity 1D simulation (Tier L9) and embedded ESP32 CAN-TWAI HIL benches (Tier L7). No physical brake actuators were deployed on a 165.5-tonne BEML BH100 truck in an operating open-cast mine pit.
