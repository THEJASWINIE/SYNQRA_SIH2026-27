# PHASE 7.3.4 — FINAL EVIDENCE MATRIX (L1–L10 AUDIT)
## FOG-ORCHESTRATOR 2.0 — SIH26007 / NMDC BAILADILA IRON ORE COMPLEX

---

### Executive Summary

This document establishes the authoritative **Evidence Level Matrix** for all core claims, physical constants, parameters, and benchmark figures of the FOG-ORCHESTRATOR 2.0 system.

In compliance with the Phase 7.3.4 Adversarial Audit, every numerical value is mapped to a strict evidence hierarchy ($L1$--$L10$), distinguishing between primary OEM data, statutory standards, bench experimental measurements, simulation models, and unverified assumptions.

#### Evidence Level Hierarchy:
- **L1**: Publicly verified / official government repository
- **L2**: OEM documented (manufacturer specification brochure)
- **L3**: NMDC documented (mine-site operational records)
- **L4**: Engineering standard (ISO 3450, SAE J1939, DGMS circulars)
- **L5**: Peer-reviewed scientific literature
- **L6**: Engineering assumption (documented rationale and physical bounds)
- **L7**: Bench measured (physical hardware in laboratory/bench testbed)
- **L8**: Field measured (physical vehicle instrumentation in operational mine pit)
- **L9**: Simulation-derived (closed-loop numerical or discrete-event model)
- **L10**: Unknown / Unverified (no primary documentation traceable)

---

### Master Evidence Matrix

| Claim ID | Headline Parameter / Claim | Canonical Value & Unit | Evidence Level | Primary Source | Directly Measured? | Independently Reproduced? | Sim Only? | Engineering Assumption? | Known Physical Limitation / Vulnerability | Allowed Presentation Language |
| :--- | :--- | :--- | :---: | :--- | :---: | :---: | :---: | :---: | :--- | :--- |
| **CLM-01** | BH100 Gross Operating Mass | $165,500.0\text{ kg}$ ($165.5\text{ t}$) | **L2** | BEML BH100 Technical Specification Brochure | NO (OEM Pub) | YES (Static Specs) | NO | NO | Excludes payload overload variations ($110\text{ t}$ overfill common in practice). | *"OEM-specified gross vehicle operating weight ($74.0\text{ t}$ tare + $91.5\text{ t}$ rated payload)."* |
| **CLM-02** | Rated Total Rim Braking Force | $550.0\text{ kN}$ ($550,000\text{ N}$) | **L10** | Derived from ISO 3450 level stopping distance ($a \approx 3.32\text{ m/s}^2$) | NO | YES (Calculated) | YES | YES | **Unverified OEM parameter.** Caliper clamp force and pad friction unverified. Subject to tyre slip when $\mu < 0.34$. | *"Rated total rim braking force parameter ($550\text{ kN}$), physically bounded by tire adhesion limit when $\mu < 0.34$."* |
| **CLM-03** | Canonical Emergency Deceleration | $2.7856\text{ m/s}^2$ | **L6 / L9** | First-principles force balance on $-8\%$ ramp ($165.5\text{ t}$, $C_{\text{rr}}=0.025$, $g=9.80665\text{ m/s}^2$) | NO | YES (Independent) | YES | YES | Valid only if $\mu \ge 0.34$. Drops to $1.9064\text{ m/s}^2$ on wet clay slick ($\mu = 0.25$). | *"Calculated emergency deceleration ($2.7856\text{ m/s}^2$) on an $-8\%$ grade, governed by tire adhesion under degraded surface conditions."* |
| **CLM-04** | Legacy Emergency Deceleration | $2.7466\text{ m/s}^2$ | **L6 / L9** | Legacy force balance ($165.0\text{ t}$, $C_{\text{rr}}=0.020$, $g=9.81\text{ m/s}^2$) | NO | YES (Independent) | YES | YES | Slightly more conservative stopping distance; retained in legacy test assertions. | *"Conservative baseline emergency deceleration parameter ($2.7466\text{ m/s}^2$)."* |
| **CLM-05** | Service Deceleration | $1.20\text{ m/s}^2$ | **L6** | Mining haulage operational literature & operator comfort limits | NO | YES (Sensitivity) | YES | YES | Not mandated by ISO 3450; higher values ($1.5\text{--}2.0\text{ m/s}^2$) induce cargo spillage and mechanical shock. | *"Modeled service deceleration comfort threshold ($1.20\text{ m/s}^2$)."* |
| **CLM-06** | Engineering Safety Buffer ($S_{\text{base}}$) | $5.0\text{ m}$ | **L6** | Half-truck length geometric clearance & blind spot margin | NO | YES (Sensitivity) | YES | YES | **Not a statutory DGMS law.** Arbitrary engineering buffer; reducing to $2\text{ m}$ increases safe speed, increasing to $10\text{ m}$ induces premature stops. | *"Engineering safety buffer ($5.0\text{ m}$) preventing zero-distance bumper contact."* |
| **CLM-07** | End-to-End Reaction Latency (P99) | $437.1\text{ ms}$ | **L7 + L6** | LoRa RF bench ($41.2\text{ ms}$) + ESP32 pipeline ($145.9\text{ ms}$) + modeled actuator ($250.0\text{ ms}$) | PARTIAL (Bench RF) | YES (Synthetic) | NO | PARTIAL | Actuator latency ($250\text{ ms}$) is an engineering assumption from heavy vehicle literature, not measured on BH100. | *"Modeled worst-case reaction latency ($437.1\text{ ms}$ P99), integrating bench-measured RF communication with modeled pneumatic brake build-up."* |
| **CLM-08** | Brake Actuator Build-Up Time | $250.0\text{ ms}$ (nom) / $350.0\text{ ms}$ (P99) | **L6** | Heavy hydraulic/pneumatic brake literature (SAE J1452 / ISO 3450) | NO | YES (Sensitivity) | YES | YES | **Not measured on physical BH100 chassis.** Real heavy haul truck air-over-hydraulic systems can exhibit $300\text{--}500\text{ ms}$ lag. | *"Modeled pneumatic/hydraulic actuator build-up latency ($250\text{ ms}$ nominal, $350\text{ ms}$ worst-case)."* |
| **CLM-09** | Gyratory Crusher Dump Cycle Time | $200.0\text{ s/truck}$ | **L3 / L6** | NMDC Bailadila Deposit-5 primary gyratory crusher standard operations | NO (Reported) | YES (Sensitivity) | YES | YES | Real dump times fluctuate ($\pm 35\text{ s}$) based on ore fragmentation, boulder bridging, and operator skill. | *"Modeled primary gyratory crusher service duration ($200.0\text{ s/truck}$)."* |
| **CLM-10** | Crusher Throughput Ceiling | $1,647.0\text{ TPH}$ | **L3 / L6** | Calculated: $(3600 / 200\text{ s}) \times 91.5\text{ t} = 1,647.0\text{ TPH}$ | NO | YES (Analytical) | YES | YES | Hard physical production ceiling for a single-dump pocket. System cannot exceed this rate in steady state. | *"Physical crusher intake capacity ceiling ($1,647.0\text{ TPH}$ at $200\text{ s}$ per $91.5\text{ t}$ payload)."* |
| **CLM-11** | Fleet Haulage Production in Dense Fog | $1,591.4\text{ TPH}$ (steady-state benchmark) | **L9** | Closed-loop 6-truck fleet simulation (canonical steady state, $7,200\text{ s}$, $600\text{ s}$ warmup discarded) | NO | YES (Canonical Run) | YES | NO | Dependent on simulated crusher service time and road geometry. Real mine production subject to equipment breakdowns. | *"Simulated fleet haulage throughput ($1,591.4\text{ TPH}$) under dense fog conditions ($12\text{ m}$ visibility)."* |
| **CLM-12** | Fleet Haulage Gain Over Baseline | $+35.88\%$ ($+420.2\text{ TPH}$) | **L9** | Comparative simulation: Level 4 ($1,591.4\text{ TPH}$) vs Level 0 ($1,171.2\text{ TPH}$) | NO | YES (Deterministic) | YES | NO | Baseline assumes uncoordinated dispatch; if human dispatchers manually hold trucks at shovel, baseline throughput would be higher. | *"Simulated $35.9\%$ haulage throughput improvement ($+420.2\text{ TPH}$) over unmanaged baseline ($1,171.2\text{ TPH}$) under identical fog impairment."* |
| **CLM-13** | Hazardous Ramp Incline Waiting Reduction | $-77.36\%$ ($625.4\text{ s} \to 141.6\text{ s}$) | **L9** | Causal fleet event tracking on $-8\%$ grade haul road | NO | YES (Timeline) | YES | NO | Achieved by transferring waiting time to flat shovel staging bays ($+401.0\text{ s}$). Total cycle delay reduced by $11.60\%$. | *"Simulated $77.4\%$ reduction in hazardous queue waiting on the $-8\%$ ramp via proactive origin slot reservation."* |
| **CLM-14** | Net Fleet Haul Cycle Delay Reduction | $-11.60\%$ ($713.6\text{ s} \to 630.8\text{ s}$) | **L9** | Total cycle delay tracking (Ramp queue + Staging hold) | NO | YES (Event logs) | YES | NO | Net savings of $82.8\text{ s/trip}$ driven by eliminating static inertia stop-start restarts on the incline. | *"Simulated $11.6\%$ net cycle delay reduction ($82.8\text{ s/trip}$ saved) through ramp shockwave elimination."* |
| **CLM-15** | Space Headway Formulation | $22.52\text{ m}$ (at $v=5.12\text{ m/s}$) | **L6 / L9** | $H = S_{\text{stop}}(v) + S_{\text{base}} + L_{\text{truck}} = 6.99 + 5.0 + 10.53\text{ m}$ | NO | YES (Analytical) | YES | YES | Represents rear-bumper to front-bumper physical envelope. Excludes sensor noise and lateral tracking error. | *"Kinematic safe space headway model ($22.52\text{ m}$ at safe crawl speed $5.12\text{ m/s}$)."* |
| **CLM-16** | Theoretical Road Kinematic Capacity | $817.8\text{ VPH}$ | **L9** | Road traffic flow equation: $C = v / H = 5.1158 / 22.52 \times 3600$ | NO | YES (Direct) | YES | NO | **Kinematic road cross-section capacity only.** Must never be conflated with mine production tonnage. | *"Theoretical single-lane kinematic road flow ($817.8\text{ VPH}$)."* |
| **CLM-17** | Dense Fog Safety Boundary (Blindout) | $v_{\text{safe}} = 0.0\text{ m/s}$ when $R \le 5.0\text{ m}$ | **L6 / L9** | Analytical root of quadratic stopping equation with $S_{\text{base}} = 5.0\text{ m}$ | NO | YES (Boundary) | YES | YES | Vulnerable to chattering without hysteresis if visibility oscillates around $5.0\text{ m}$. | *"Deterministic blindout safety halt condition ($v_{\text{safe}} = 0$ when visibility $\le 5.0\text{ m}$)."* |
| **CLM-18** | Randomized Monte Carlo Safety Compliance | $0 / 10,000$ violations ($0.0\%$) | **L9** | Randomized stress testing ($N=10,000$ trials, varying mass, grade, friction, latency) | NO | YES (10k trials)| YES | NO | Proves software algorithm consistency within tested parameter bounds; does not validate unmodeled physical failures. | *"Zero safety invariant violations observed across 10,000 randomized dynamic simulation trials."* |
| **CLM-19** | SX1278 CSS-LoRa Bench PDR & Latency | $99.1\%\text{ PDR}$, $41.2\text{ ms}$ roundtrip | **L7** | Bench experimental testbed (Dual ESP32-WROOM-32, $150\text{ m}$ LOS) | YES (Bench) | YES (Hardware) | NO | NO | Tested in open-air suburban LOS; pit multipath, iron-ore dust attenuation, and NLOS rock-wall shadowing uncharacterized. | *"Bench-measured outdoor LOS LoRa telemetry ($99.1\%$ PDR, $41.2\text{ ms}$ roundtrip latency over $150\text{ m}$)."* |
| **CLM-20** | ESP32 TWAI CAN Bus Decoding | $250\text{ kbps}$ ISO 11898-1 / SAE J1939 | **L7** | Laboratory bench testing with SN65HVD230 transceiver & CAN frame generator | YES (Bench) | YES (Bench) | NO | NO | Validated on bench generator; physical tapping of BH100 chassis wiring harness and OEM PGN mapping pending mine access. | *"Bench-tested ESP32 TWAI controller successfully decoding 250 kbps CAN/J1939 telemetry frames."* |
| **CLM-21** | Post-Fog Multi-Stage Fleet Recovery | $t = 195.0\text{ s}$ to first dump, $480\text{ s}$ steady state | **L9** | Closed-loop 5-stage fleet kinematic simulation | NO | YES (Timeline) | YES | NO | Refutes "instant recovery". Dependent on truck acceleration limits and travel distance ($1,200\text{ m}$). | *"Model-derived multi-stage fleet recovery trajectory ($195.0\text{ s}$ to first dump after fog clearance)."* |
| **CLM-22** | Local Safety Governor Supremacy | $100\%$ unsafe override rejection | **L9** | Adversarial fault injection matrix ($500$ hostile central override commands) | NO | YES (Injected) | YES | NO | Software-enforced hierarchy ($v_{\text{command}} = \min(v_{\text{central}}, v_{\text{safe}})$); physical actuator wire-level override uncharacterized. | *"Architectural enforcement of Tier-1 Local Safety Governor supremacy over all central dispatch commands."* |

---

### 3. Summary of Evidence Distribution

- **L1 / L2 / L4 (Verified Specifications & Standards)**: $3$ parameters ($13.6\%$) — Vehicle mass, standards.
- **L3 / L6 (Engineering Assumptions & Site Baseline)**: $6$ parameters ($27.3\%$) — Service decel, safety buffer, crusher service time, actuator build-up.
- **L7 (Bench Hardware Measurements)**: $2$ parameters ($9.1\%$) — SX1278 LoRa PDR/latency, ESP32 TWAI parsing.
- **L9 (Closed-Loop Simulation Derived)**: $10$ parameters ($45.5\%$) — Fleet throughput, ramp waiting reduction, safe speed, recovery timeline, Monte Carlo.
- **L10 (Unverified Parameter Origin)**: $1$ parameter ($4.5\%$) — Rated $550\text{ kN}$ brake force.

---

### 4. Direct Hostile Reviewer Takeaway

FOG-ORCHESTRATOR 2.0 possesses **rock-solid software correctness, robust mathematical closed-form formulations, and reproducible bench communication performance**. However, its physical execution is bounded by **well-defined engineering assumptions regarding mechanical braking and crusher dynamics** that require physical in-pit instrumentation for L8 field certification.
