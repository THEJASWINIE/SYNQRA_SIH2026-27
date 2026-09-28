# PHASE 7.3.4 — CLAIM LANGUAGE & OVERCLAIM AUDIT
## FOG-ORCHESTRATOR 2.0 — SIH26007 / NMDC BAILADILA IRON ORE COMPLEX

---

### Executive Summary

In compliance with **Phase 7.3.4 Attack #30**, a comprehensive static scan was executed across all markdown reports, source documentation, configuration comments, and presentation-facing materials.

A hostile evaluation by external mining-systems safety certifiers (DGMS/ISO auditors) will immediately reject any presentation that uses unsubstantiated, absolutist, or marketing-style language. This audit classifies all scanned keywords into four strict categories:
1. **SUPPORTED**: Claims with direct, reproducible numerical, physical, or bench experimental evidence.
2. **OVERSTATED**: Claims containing real engineering substance but stated with unscientific universal scope (e.g., claiming "zero collision risk" without qualifying the operational design domain).
3. **UNVERIFIED**: Parameters or capabilities treated as established facts without primary OEM, statutory, or physical telemetry backing (e.g., 550 kN brake force origin, BH100 J1939 chassis frames).
4. **FALSE / RETRACTED**: Disproven claims, mathematical impossibilities, or conflated physical concepts (e.g., converting road kinematic VPH into mine production TPH, claiming Bailadila field testing).

---

### 1. Keyword Scan Results & Forensic Classification

The static scanner analyzed 18 target terms across all project files. Below is the systematic breakdown of audited usages:

| Target Keyword | Occurrences Scanned | Forensic Classification | Audit Disposition & Mandatory Language Correction |
| :--- | :---: | :--- | :--- |
| **`field validated`** | 9 | **OVERSTATED / RETRACTED** | **Prohibited.** Hardware testing was performed exclusively on an outdoor suburban bench with dual ESP32-WROOM-32 transceivers. No transceivers were installed in Bailadila Deposit-5 pits. Replaced with: *"Site-calibrated simulation and outdoor bench LoRa telemetry."* |
| **`guaranteed`** | 6 | **OVERSTATED** | **Prohibited in absolute terms.** Safety cannot be universally "guaranteed" against physical brake actuator failure, tyre blowout, or extreme sub-0.10 mud slick conditions. Replaced with: *"Mathematically provable within modeled kinematic constraints."* |
| **`collision-free`** | 3 | **OVERSTATED** | **Prohibited as a blanket claim.** Replaced with: *"Maintained non-colliding trajectories across N=10,000 randomized Monte Carlo dynamic trials ($0.0\%$ violations observed)."* |
| **`eliminates`** | 8 | **OVERSTATED (Conditional)** | Allowed only when referring specifically to the removal of stop-start ramp shockwaves at $-8\%$ grade: *"Eliminates stop-start shockwaves on the haulage incline by relocating waiting to shovel staging."* **Prohibited** when claiming to eliminate all collision risk or total mine delay. |
| **`certified`** | 18 | **SUPPORTED (Conditional)** | Valid when referencing OEM-published payload/tare mass ($74.0\text{ t}$ empty, $91.5\text{ t}$ payload) or DGMS statutory guidelines. **Prohibited** when applied to unverified brake actuator pressure or uncertified software models. |
| **`first`** | 22 | **SUPPORTED** | Used primarily in technical contexts such as *"first-principles derivation"*, *"first packet after stale"*, and *"first wave arrival at crusher"*. Defensible when describing mathematical modeling from first principles. |
| **`instant recovery`** | 3 | **FALSE / RETRACTED** | **Prohibited.** Recovery after fog dissipation is physically constrained by truck acceleration ($a \le 0.5\text{ m/s}^2$), haul distance ($1,200\text{ m}$), and crusher queue emptying. Full fleet cycle recovery requires $195.0\text{ s}$ to first dump and $\sim 480\text{ s}$ to steady state. |
| **`production increase`** | 3 | **SUPPORTED (Qualified)** | Supported as: *"+35.9% fleet haulage throughput improvement over Level 0 unmanaged baseline under dense fog ($15\text{ m}$ visibility) in a 7,200 s closed-loop simulation."* **Prohibited** as a general mine production guarantee. |
| **`zero risk`** | 1 | **FALSE / RETRACTED** | Found in an internal architectural comment. **Prohibited in all external and presentation contexts.** Zero operational risk does not exist in open-cast mining. |
| **`100% reliable` / `100% safe`** | 1 | **OVERSTATED** | Replaced with exact statistical bounds: *"PDR = 99.1% across 1,000 packets at 150m LOS bench; zero safety violations across 10,000 simulation trials."* |
| **`survives packet loss`** | 0 | **SUPPORTED** | Tested up to 100% communication loss and 30 s burst dropouts; vehicle safely defaults to autonomous Tier-1 local governor. |
| **`DGMS compliant`** | 0 | **UNVERIFIED / CONDITIONAL**| The system is designed to adhere to DGMS circulars on haul road safety, but has not received formal DGMS certification. Must be labeled *"Designed in alignment with DGMS haul road safety guidelines."* |
| **`ISO compliant`** | 0 | **UNVERIFIED / CONDITIONAL**| Emergency stopping distances satisfy ISO 3450 criteria, but the vehicle has not undergone certified ISO 3450 physical track testing. |
| **`novel` / `AI prediction`** | 0 | **SUPPORTED (Scrutinized)**| Orchestration uses kinematic virtual slot reservation; prediction uses physics-informed bottleneck forecasting, not black-box deep learning. |

---

### 2. Mandatory Language Dictionary for Presentation & Publications

To eliminate all hostile evaluator attack vectors, the following substitution table is **frozen and enforced**:

| Forbidden Term / Overclaim | Mandatory Defensible Phrasing | Physical & Experimental Justification |
| :--- | :--- | :--- |
| *"Eliminates all collision risk in fog."* | *"Enforces a mathematically non-colliding operational envelope across all tested simulation conditions ($N=10,000$, zero violations). Real-world safety remains contingent upon mechanical brake health and tyre-road friction."* | Tier-1 local governor enforces $S_{\text{stop}}(v) + S_{\text{base}} \le R$; however, physical hardware failure or tyre blowout cannot be eliminated by software. |
| *"100% collision-free guaranteed."* | *"Zero overspeed or stopping-distance violations observed across 10,000 randomized Monte Carlo dynamic trials."* | Absolute guarantees violate basic system safety engineering principles (IEC 61508 / ISO 26262). |
| *"Field validated at NMDC Bailadila Deposit-5."* | *"Calibrated using NMDC Bailadila Deposit-5 geospatial geometry and validated via hardware-in-the-loop LoRa RF bench testing and closed-loop fleet dynamics simulation."* | Hardware transceivers were tested on a suburban test bench; physical access to Bailadila mine pits has not occurred. |
| *"FOG-Orchestrator delivers instant recovery after fog clears."* | *"The fleet transitions through a five-stage physical recovery trajectory, achieving first post-fog crusher dump at $t = 195.0\text{ s}$ and complete queue steady-state recovery at $t \approx 480\text{ s}$."* | Vehicles have inertia; acceleration is governed by engine traction on an $-8\%$ ramp. Recovery cannot be instantaneous. |
| *"Achieves 74,828 TPH mine production."* | *"The haul road possesses a theoretical kinematic vehicle flow of $817.8\text{ VPH}$. Actual mine fleet production is strictly capped by the gyratory crusher dump pocket at $1,647.0\text{ TPH}$."* | Conflating road cross-section vehicle capacity with mine dumping throughput is a physical category error. |
| *"Eliminates 77.4% of total mine waiting delay."* | *"Reduces hazardous queue waiting on the $-8\%$ haulage ramp by $77.36\%$ ($625.4\text{ s} \to 141.6\text{ s}$) by relocating trucks to safe, flat shovel staging bays ($+401.0\text{ s}$). Net cycle delay decreases by $11.60\%$ ($82.8\text{ s/trip}$ saved)."* | Delays are relocated from high-risk inclines to low-risk flat loading benches, with modest net time savings from eliminating restart inertia. |
| *"J1939 CAN bus fully integrated on BH100."* | *"ESP32 TWAI controller verified for ISO 11898 CAN 2.0B / SAE J1939 frame decoding at 250 kbps on a bench simulator; live tapping of physical BH100 chassis wiring harness is pending mine deployment."* | TWAI driver compatibility does not constitute vehicle chassis integration. |
| *"OEM certified 550 kN brake force."* | *"Rated brake force of $550\text{ kN}$ is an unverified engineering parameter derived from ISO 3450 minimum level-ground stopping criteria ($a \approx 3.32\text{ m/s}^2$). Critical adhesion crossover occurs at $\mu = 0.34$, below which tyre traction strictly limits braking."* | Primary BEML OEM documentation for the caliper normal clamp force is absent from the repository. |

---

### 3. Conclusion & Audit Disposition

The FOG-ORCHESTRATOR 2.0 codebase and reports have been purged of unsupported marketing language. Every remaining claim is directly tied to an explicit evidence tier ($L1$--$L10$), ensuring full technical defensibility during hostile evaluation.
