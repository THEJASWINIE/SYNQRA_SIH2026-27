# 16 — RESEARCH CONTRIBUTION STATEMENT
## FOG-ORCHESTRATOR 2.0 — Sensor & Data Degradation Research
**Project:** SIH26007 — Fog / Low-Visibility Mine Fleet Safety & Orchestration  
**Date:** 2026-09-21  
**Lead Researcher:** Systems Architect & Safety Systems Research Lead  

---

## 1. Primary Research Framing

> We investigate a bounded, auditable, rule-based data-health layer for low-visibility open-cast mine haulage that propagates environmental telemetry validity and confidence directly into a physics-constrained local safety governor and central fleet orchestration layer. Rather than introducing an opaque, learned sensor-fusion model, our approach explicitly separates detectable telemetry degradations (freshness, sequence, range, variance) from the harder problem of plausible-but-wrong measurements, preserving local onboard vehicle safety authority as inviolable while enabling fleet-level dispatch to account for degraded operational confidence.

---

## 2. The Core Problem & Research Gap

In low-visibility open-cast mining operations (dense advection fog, mining dust storms, monsoonal precipitation), haul trucks operating at gross vehicle weights exceeding $165\text{ tonnes}$ on steep haul road ramps ($-8\%\text{ to }-12\%$ downhill grades) depend critically on environmental visibility ($R_{\text{effective}}$) to compute safe stopping envelopes ($v_{\text{stop}}$).

### The Demonstrated Safety Vulnerability
In standard connected fleet management architectures:
1. Vehicle telemetry (wheel speed, engine RPM, IMU) passes through quality and freshness filters.
2. **Environmental telemetry (visibility, surface friction, road grade) bypasses telemetry trust filters**, entering directly as trusted parameters into stopping distance calculations.
3. If an optical visibility sensor drops out, freezes, or becomes stale during a sudden fog bank, the vehicle safety solver continues permitting high speeds based on outdated visibility (e.g., holding $50\text{ m}$ visibility when true visibility has dropped to $12\text{ m}$).
4. On a $-8\%$ grade with a $165.5\text{-tonne}$ loaded truck, this failure allows an over-speed allowance of $+5.82\text{ m/s}$ ($+20.9\text{ km/h}$), leading to fatal stopping-distance violations:
   $$S_{\text{stop}}(v_{\text{applied}}) + S_{\text{base}} > R_{\text{effective\_true}}$$

### The Research Gap
Prior research in heavy vehicle safety typically falls into two extremes:
- **Academic Complex Perception:** Heavy deep-learning multimodal sensor fusion (LiDAR-camera-radar fusion) that is computationally prohibitive on low-power embedded vehicle ECUs, opaque under safety certification audits (ISO 19014 / IEC 61508), and vulnerable to out-of-distribution optical scattering in mine fog.
- **Commercial FMS Oversimplification:** Macro-dispatch fleet management systems that treat visibility as an unverified scalar or binary stop/go flag, resulting in either unmitigated collision risk or severe mine-wide operational paralysis.

There has been an absence of a **lightweight, auditable, rule-based data-health layer** that:
1. Quantifies environmental telemetry confidence mathematically without machine learning.
2. Directly tightens the closed-form physical stopping distance envelope.
3. Decouples local vehicle safety authority from central fleet optimization.

---

## 3. Concrete Engineering & Scientific Contributions

### Contribution 1: Authoritative Architectural Decoupling (Hierarchy Preserved)
We formalized and implemented an inviolable safety authority hierarchy where the data-health layer acts strictly as a **conservative environmental filter**, not an actuator authority:
$$\text{Telemetry Ingest} \to \text{EnvironmentalDataHealth} \to R_{\text{effective\_conservative}} \to \text{solve\_safe\_speed} \to \text{LocalVehicleSafetyGovernor} \to v_{\text{applied}}$$
- The health layer can never command brakes or throttle directly.
- The central fleet orchestrator can never override the local vehicle governor ($v_{\text{applied}} \le v_{\text{safe}}$).
- If the health module encounters an unhandled exception, it fails closed to $R_{\text{UNAVAILABLE\_MIN}} = 8.0\text{ m}$.

### Contribution 2: Multi-Check Rule-Based Health Engine with Hysteresis
We engineered a clean, deterministic module implementing six auditable checks:
- **H1 (Freshness):** Tiered degradation at $30\text{ s}$ (30% penalty) and $60\text{ s}$ (50% penalty), dropping to crawl floor ($8\text{ m}$) after grace period ($120\text{ s}$).
- **H2 (Schema/Type):** Strict rejection of NaN, Inf, non-numeric, or malformed payloads.
- **H3 (Range):** Physical plausibility clamping to $[0.5\text{ m}, 2000\text{ m}]$.
- **H4 (Sequence):** Detection of duplicate packets and backward sequence rollbacks.
- **H5 (Variance):** Stuck-at detection ($\sigma < 0.05\text{ m}$ over $300\text{ s}$) and excessive noise detection ($\sigma > 20\text{ m}$).
- **H6 (Conflict):** Disagreement detection when dual independent sources exist.
- **Recovery Hysteresis:** Mandatory multi-frame confirmation ($2\text{ frames}$ from STALE, $3\text{ frames}$ from UNAVAILABLE) preventing state flapping.

### Contribution 3: Hazard Migration Proof (Hazardous Ramp vs. Controlled Staging)
We proved both analytically and experimentally that health-aware orchestration does not merely reduce waiting time—it **migrates waiting from high-hazard active ramps to flat, controlled staging zones**.
- Uncontrolled baseline B0 results in trucks idling on active $-8\%$ slopes under zero visibility.
- Health-aware treatment B1 holds vehicles in the designated staging area before ramp entry, reducing hazardous road waiting by $> 90\%$.

### Contribution 4: Mathematical Exposure of the Class C Boundary
We refused to fabricate a claim of "complete sensor fault elimination."
We proved that **plausible-but-wrong single-source telemetry (True=5m, Reported=50m) is mathematically undetectable** without an independent physical reference. By formalizing this boundary, we established clear architectural specifications for future dual-sensor mine deployments.

---

## 4. Summary Table of Contributions

| Area | Prior State in Repo | Contribution of This Work |
|---|---|---|
| **Environmental Telemetry** | Unguarded pass-through of visibility into physics solver | Full rule-based health pipeline (H1–H6) with conservative scaling |
| **Safety Invariant Closure** | Stale visibility caused stopping envelope violations | Stopping violations reduced to zero for all detectable failure modes |
| **Failure Recovery** | Potential rapid flapping between offline and live | Multi-frame recovery hysteresis (2–3 consecutive clean observations) |
| **Traffic Accounting** | Generic total waiting time | Explicit separation: Hazardous Downhill Waiting vs. Staging Waiting |
| **Scientific Integrity** | Undocumented single-source limitations | Formal identification and verification of Class C failure boundary |
