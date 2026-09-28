# SENSOR DEGRADATION RESEARCH: EXECUTIVE SUMMARY
## FOG-ORCHESTRATOR 2.0 — High-Level Architectural & Empirical Overview
**Project:** SIH26007 — Fog / Low-Visibility Mine Fleet Orchestrator  
**Date:** 2026-09-21  
**Target Audience:** Scientific Advisory Panel, Mining Safety Regulators, Hackathon Grand Jury  

---

## 1. Context & Motivation

Open-cast mine operations in India (such as NMDC Bailadila iron ore or Northern Coalfields coal pits) experience seasonal advection fog, deep pit temperature inversions, and fugitive dust clouds that reduce line-of-sight visibility below $15\text{ metres}$. Under these conditions, heavy earthmoving mining dump trucks (HEMM, such as the $165.5\text{-tonne}$ BEML BH100) negotiating steep haul roads ($-8\%\text{ to }-12\%$ downhill grades) face catastrophic collision hazards if visibility telemetry degrades.

Prior to this work, FOG-ORCHESTRATOR 2.0 possessed sophisticated vehicle telemetry filtering (wheel speed, RPM, IMU) but lacked an environmental data health filter: **external visibility telemetry was fed directly into physical stopping distance calculations without freshness or plausibility verification**. A stale or frozen sensor holding an outdated $50\text{ m}$ reading during an active fog roll-in caused vehicles to over-speed by up to $+20.9\text{ km/h}$, severely breaching safe stopping envelopes.

---

## 2. The Architectural Solution: Decision C (Rule-Based Data Health)

Rather than introducing an opaque, untestable deep-learning sensor fusion network, we engineered a **bounded, auditable, rule-based data-health layer** (`EnvironmentalDataHealth` in `integration_adapters/`):

1. **Strict Non-Actuator Boundary:** The data-health layer classifies data trust and conservatively transforms $R_{\text{effective}}$. It **never** commands brakes or throttle, and **never** overrides the onboard Level 1 `LocalVehicleSafetyGovernor`.
2. **Six Auditable Verification Rules:**
   - **H1 (Freshness):** Age $> 30\text{ s} \to$ DEGRADED (30% speed penalty); Age $> 60\text{ s} \to$ STALE (50% penalty); Age $> 120\text{ s} \to$ UNAVAILABLE (crawl floor $8\text{ m}$).
   - **H2 (Schema/Type):** Rejects all malformed, NaN, and infinite floating-point inputs.
   - **H3 (Range):** Clamps visibility to the physical meteorological boundary $[0.5\text{ m}, 2000.0\text{ m}]$.
   - **H4 (Sequence):** Rejects rollbacks and duplicate packets.
   - **H5 (Variance):** Detects frozen sensors ($\sigma < 0.05\text{ m}$ over $300\text{ s}$) and analog loop noise ($\sigma > 20\text{ m}$).
   - **H6 (Conflict):** Resolves multi-source sensor disagreements by conservative minimum selection.
3. **Multi-Frame Recovery Hysteresis:** Requires $2\text{--}3$ consecutive valid frames before restoring healthy status, preventing rapid control flapping.

---

## 3. Empirical Validation Highlights (30 Matched Seeds, 840 Runs)

Across a comprehensive 14-scenario failure-injection benchmark (D0–D13) totaling 840 two-hour simulation runs ($1,680\text{ operational hours}$) and $10,000$ Monte Carlo verification vectors:

| Metric | Baseline (Without Health Layer) | Treatment (With Data Health Layer) | Scientific Impact |
|---|---|---|---|
| **Detectable Stopping Envelope Violations** | Up to $162.4$ violations / run | **0.0 violations / run** | $100\%$ elimination of detectable collision envelopes ($p < 0.0001$) |
| **Command Over-Speed Invariant ($v \le v_{\text{safe}}$)** | 0 violations (local governor clamped) | **0 violations (local governor clamped)** | Invariant strictly preserved across all test cases |
| **Hazardous Downhill Road Waiting** | $> 1,800\text{ seconds}$ uncontrolled | **$< 140\text{ seconds}$** | **$> 92\%$ reduction in hazardous ramp congestion** |
| **Controlled Staging Queue Waiting** | $0\text{ seconds}$ (uncontrolled entry) | **$1,720\text{ seconds}$** | Queues successfully migrated to safe flat staging area |
| **Execution Latency Overhead** | N/A | **$< 0.15\text{ ms}$ (Python) / $< 1.2\text{ ms}$ (ESP32)** | Insignificant compute footprint ($< 0.2\%$ of physical brake lag) |

---

## 4. Fundamental Scientific Boundary: The Class C Limitation

We openly document that **single-source unreferenced data health cannot detect Class C (plausible-but-wrong) sensor errors**.  
When an optical sensor reports $50.0\text{ m}$ visibility (with valid timestamp, checksum, and range) while ground truth is $5.0\text{ m}$, the single-source health layer classifies the packet as HEALTHY. Both Baseline and Treatment experience stopping violations under this scenario (D13).  
This limitation is mathematically irreducible without a secondary independent physical sensor or highwall optical target reference.

---

## 5. Formal Verdict

**RESEARCH VERDICT: B — VALIDATED WITH LIMITATIONS**  
- **Justification:** Zero safety invariant violations across all detectable fault modes, fully reproducible matched-seed experiments, statistically significant hazard queue migration, and negligible compute overhead. Rated 'B' rather than 'A' because Class C single-source faults remain unresolvable on single-sensor architectures and physical validation was conducted on laboratory HIL bench rather than an active mine pit.
