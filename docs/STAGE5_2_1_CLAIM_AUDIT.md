# STAGE 5.2.1: CRITICAL WORDING & CLAIM INTEGRITY AUDIT
**Forensic Audit of Repository Claims, Language Precision, and Overstatement Removal**  
**Project:** FOG-ORCHESTRATOR 2.0 (SIH 2026-27 — NMDC Bailadila Iron Ore Complex)  
**Status:** EVIDENCE INTEGRITY GATE — ZERO MARKETING LANGUAGE  

---

## 1. Executive Objective

The purpose of this audit is to conduct a forensic text and evidence search across the entire repository to identify any claim that exceeds its empirical basis. In competitive evaluations and industrial peer reviews (such as NMDC / SIH 2026-27), unearned claims (e.g. "eliminates collision risk", "increases production", "real-time deployable") destroy credibility.

This audit establishes a strict, non-negotiable standard:
- **No claim may exceed the exact experimental condition under which it was demonstrated.**
- **Simulation proofs must never be labeled as real-world or field validations.**
- **Kinematic boundary clamping must not be conflated with total operational risk elimination.**

---

## 2. Line-by-Line Claim Audit Table

The table below catalogs every occurrence of key audited phrases across the documentation and codebase, evaluates the evidence, and defines the mandatory safe scientific wording:

| File & Line | Quoted Claim / Text | Empirical Evidence Available | Scientific Status | Invalid / Overstated Element | Mandatory Safe Scientific Wording |
| :--- | :--- | :--- | :---: | :--- | :--- |
| `STAGE5_2_SCIENTIFIC_CONCLUSION.md:36` | *"demonstrably eliminates collision risk"* | Exp B simulated 9 two-vehicle car-following scenarios with $H_{\text{min}} = 6.49\text{ m} > 5.0\text{ m}$. | **OVERSTATED** | "eliminates collision risk" implies 100% operational guarantee across all real-world mine conditions. | *"demonstrated non-colliding vehicle trajectories across the 9 tested kinematic stress scenarios"* |
| `STAGE5_2_EXECUTIVE_SUMMARY.md:83` | *"Completely prevents rear-end collisions in zero-visibility fog"* | Exp B simulated lead braking at $-3.0\text{ m/s}^2$; vehicle halted with $1.49\text{ m}$ margin above buffer. | **OVERSTATED** | "Completely prevents rear-end collisions" is an unprovable universal negative in a stochastic open pit. | *"prevents simulated rear-end collisions under modeled car-following and emergency deceleration scenarios"* |
| `STAGE5_2_EXECUTIVE_SUMMARY.md:86` | *"Instantaneous Recovery: Eliminates 15–30 minutes of human dispatch radio confusion"* | Exp F showed control-command resumption at $t = 1001.0\text{ s}$ ($1.0\text{ s}$ after visibility $V > 5\text{ m}$). | **OVERSTATED** | "Instantaneous recovery" conflates control-command updating with physical traffic flow and cycle completion. | *"Automated control-command resumption within <1.0 s after the simulated safety envelope recovers"* |
| `STAGE5_2_COLLISION_AVOIDANCE.md:4` | *"100% COLLISION-FREE TRAJECTORIES"* | 9 kinematic scenarios with modeled reaction latency ($\tau=0.400\text{ s}$) showed zero bumper violations. | **QUALIFIED PASS** | Valid for the 9 scenarios, but must not be generalized to unmodeled multi-vehicle pileups or mechanical brake fade. | *"Maintained non-colliding trajectories across all 9 evaluated stress scenarios ($H_{\text{min}} \ge 6.49\text{ m}$)"* |
| `STAGE5_2_TRUTH_TABLE.md:17` | *"System reduces total waiting"* | Exp E measured $W_{\text{total}} = 125.8\text{ s}$ (`FOG_ORCHESTRATOR`) vs $122.9\text{ s}$ (`SAFETY_ONLY`). | **REFUTED** | Total waiting is conserved per Little's Law; claiming waiting reduction is factually false. | *"Total waiting time is conserved under saturated bottlenecks ($125.8\text{ s}$ vs $122.9\text{ s}$); delay is relocated spatially to safe staging benches."* |
| `STAGE5_2_TRUTH_TABLE.md:20` | *"System increases production"* | Exp D/E measured $274.5\text{ t}$ at $10\text{ m}$ fog for both `SAFETY_ONLY` and `FOG_ORCHESTRATOR`. | **REFUTED** | Production is bounded by physical speed $v_{\text{safe}}$ and crusher capacity ($18\text{ VPH}$). | *"FOG-Orchestrator does not increase physical mine production beyond the limits of braking physics and crusher service rates."* |
| `STAGE5_2_VISIBILITY_PRODUCTION.md:40` | *"Actual Haulage: 3,294.0 TPH"* | 18 loads completed in initial $1{,}800\text{ s}$ window ($18 \times 91.5\text{ t} / 0.5\text{ h}$). | **QUALIFIED PASS** | Labeling $3{,}294\text{ TPH}$ as "mine production capacity" is false; crusher max is $1{,}647\text{ TPH}$. | *"Simulated delivered throughput during the initial 1,800s window ($3{,}294\text{ TPH}$), driven by pre-staged shovel queue flush; steady-state ceiling is $1{,}647\text{ TPH}$."* |
| `STAGE5_2_NMDC_REQUIREMENT_MATRIX.md:23` | *"Digital Twin Software Authority: PROVEN"* | `TwinStateStore` and FastAPI serve as single state projection for physics, optimizer, Pygame, and HMI. | **PROVEN** | Accurately describes software architecture within the project scope. | *"Single authoritative Digital Twin software architecture verified across simulation, HMI, and telemetry pipelines."* |
| `STAGE5_2_NMDC_REQUIREMENT_MATRIX.md:25` | *"Scalability for Large Open-Cast Mines: PROVEN"* | Capacity hierarchy evaluated for 5 to 50 trucks; runtime is linear; state handling verified. | **PARTIALLY PROVEN** | "Proven" overclaims hardware network scalability (LoRa RF channel contention was not tested at 50 nodes). | *"Software architecture and queue algorithms scale consistently up to 50 simulated trucks; multi-node RF channel capacity remains to be field-validated."* |
| `STAGE5_2_TRUTH_TABLE.md:23` | *"System is deployable to NMDC: PARTIALLY PROVEN"* | Caterpillar 777G parameters, Bailadila road grades, and ESP32 telemetry contracts implemented. | **PARTIALLY PROVEN** | "Deployable" risks implying immediate operational readiness without on-site hardware trials. | *"Architecture is designed for NMDC Bailadila operating specifications; in-pit RF propagation and vehicle CAN-bus trials remain required."* |
| `STAGE4_FINAL_EVALUATOR_DEFENSE.md:29` | *"backed by autonomous radar/LiDAR obstacle detection"* | Simulated obstacle and leader headway detection; no physical LiDAR sensor was integrated. | **OVERSTATED** | Mentions radar/LiDAR as if present on the prototype vehicle. | *"Prototype utilizes LoRa V2V peer telemetry; industrial deployment targets J1939 CAN bus and commercial radar/LiDAR integration."* |
| `STAGE2_ABLATION_RESULTS.csv:7` | *"Level 4 FOG_ORCHESTRATOR ... 30 safety violations"* | Stage 2 ablation script had transient initialization speed mismatch before governor engagement. | **HISTORICAL ARTIFACT** | In Stage 5.2, governor clamping is verified with 0 safety violations. | *"Stage 2 transient artifact preserved for historical traceability; Stage 5.2 verifies 0 safety violations."* |

---

## 3. Mandatory Terminology Standards

To prevent scientific overreach in all project presentations, reports, and documentation, the following terminology substitutions are mandatory:

1. **Collision Avoidance:**
   - ❌ *Forbidden:* "Eliminates collision risk", "Guarantees zero collisions", "Prevents all accidents".
   - ✔️ *Mandatory:* "Maintains non-colliding vehicle trajectories in modeled car-following and emergency braking scenarios ($H_{\text{min}} > 5.0\text{ m}$)."

2. **Fog Recovery:**
   - ❌ *Forbidden:* "Instantaneous recovery", "Zero-delay mine resumption".
   - ✔️ *Mandatory:* "Sub-second control-command resumption ($<1.0\text{ s}$) upon safety envelope expansion, eliminating manual radio roll-call delays."

3. **Production & Throughput:**
   - ❌ *Forbidden:* "Increases mine production in severe fog", "Eliminates fog production loss".
   - ✔️ *Mandatory:* "Does not increase physical bottleneck capacity; captures feasible operational envelopes in moderate fog ($10\text{--}25\text{ m}$) while safely halting at $\le 5\text{ m}$."

4. **Queue Management (HOLD Policy):**
   - ❌ *Forbidden:* "Eliminates waiting time", "Reduces total mine delay".
   - ✔️ *Mandatory:* "Relocates queuing delay spatially from hazardous single-lane mountain slopes to flat shovel benches; total network delay is conserved."

5. **Deployment & Maturity:**
   - ❌ *Forbidden:* "Deployable to NMDC", "Field-validated", "Production-ready mining system".
   - ✔️ *Mandatory:* "Architecture calibrated to NMDC Bailadila specifications; prototype verified on bench hardware; deep-pit field validation remains outstanding."
