# MASTER CONTRADICTION REGISTER & AUDIT RESOLUTION
## FOG-ORCHESTRATOR 2.0 — SIH 2026-27
**Target Mine Reference:** NMDC Bailadila Deposit 5, Bacheli Complex, Chhattisgarh  
**Status:** CANONICAL FORENSIC AUDIT RECORD (All 15 Contradictions Formally Resolved)  
**Date:** 2026-09-18  

---

## 1. Grade Sign Convention Conflict

- **CLAIM:**  
  "Ramp grade is $+8\%$ downhill on Ramp R1, but GIS maps and civil standards designate it as $-8\%$."
- **EVIDENCE:**  
  Civil engineering / GIS standard elevation gradient: $\Delta h / \Delta s < 0$ for descending ramps ($-8\%$). Internal physics in `fog_safe/road.py` and `fog_safe/braking.py` defined forward downhill slopes as positive angles ($\theta > 0$, positive grade force $F_{\text{grade}} = m g \sin\theta$).
- **CONFLICT:**  
  If $-8\%$ were passed directly into physics formulas without adaptation, the solver would interpret it as an uphill climb ($\theta < 0$), calculating that gravity assists braking. Stopping distance would be underestimated by up to $34\%$.
- **CANONICAL INTERPRETATION:**  
  External systems (GIS, HMI, Operator HUD) strictly follow civil standards: $+G = \text{Uphill}$, $-G = \text{Downhill}$. Internal resistance solvers use $G_{\text{physics}} = -G_{\text{civil}}$.
- **FIX:**  
  All external grades must pass through `GradeAdapter` (`integration_adapters/grade_adapter.py`). Verified that downhill ($-8\%$) increases stopping distance and decreases safe speed.
- **STATUS:**  
  **RESOLVED & VERIFIED** (Documented in `docs/GRADE_CONVENTION_FINAL.md`, regression tested in `tests/test_grade_adapter.py`).

---

## 2. Old vs Canonical Safe-Speed Values ($4.382\text{ m/s}$ vs $4.109\text{ m/s}$ vs $4.22\text{ m/s}$)

- **CLAIM:**  
  "Safe speed under dense fog is variously stated as $4.382\text{ m/s}$, $4.109\text{ m/s}$, or $4.22\text{ m/s}$."
- **EVIDENCE:**  
  Historical draft logs and uncoordinated test harnesses used divergent mass ($165\text{ t}$ vs $165.5\text{ t}$) and latency values ($\tau = 0.40\text{ s}, 0.45\text{ s}, 0.80\text{ s}$).
- **CONFLICT:**  
  Hardcoded values in presentation slides created conflicting targets for test assertion and HMI display.
- **CANONICAL INTERPRETATION:**  
  $v_{\text{safe}}$ is not an arbitrary constant; it is the instantaneous analytical root of the quadratic stopping constraint:
  $$\frac{1}{2 a_{\text{dec}}} v^2 + \tau_{\text{total}} v + (S_{\text{base}} - R_{\text{effective}}) = 0$$
  Under canonical Bailadila parameters ($m = 165.5\text{ t}, \mu = 0.35, G_{\text{civil}} = -8.0\%, R = 12.0\text{ m}, \tau = 0.450\text{ s}$), $a_{\text{dec}} = 2.7485\text{ m/s}^2$ and the exact root is $v_{\text{safe}} = 4.3815\dots\text{ m/s}$ ($15.77\text{ km/h}$).
- **FIX:**  
  Parameters centralized in `config/bailadila_hemm_canonical.yaml`. The solver computes exact double-precision floating-point roots, formatted to 2 decimals on HMI displays.
- **STATUS:**  
  **RESOLVED & VERIFIED** (Tested in `tests/test_hemm_canonical_regression.py`).

---

## 3. Theoretical Kinematic Saturation vs Practical Road Capacity ($700.5\text{ vph}$ vs $600\text{ vph}$)

- **CLAIM:**  
  "Haul road capacity under fog is $700.5\text{ vph}$ (or $600\text{ vph}$ nominal)."
- **EVIDENCE:**  
  Kinematic hydrodynamic traffic equation $C_{\text{kin}} = 3600 \cdot \frac{v}{H}$. At $v = 4.38\text{ m/s}, H = 22.5\text{ m}$, $C = 700.5\text{ vph}$.
- **CONFLICT:**  
  $700.5\text{ vph}$ assumes continuous, bumper-to-bumper vehicle packing on an infinite open road. Presenting this as "mine production capacity" implies moving $>64{,}000\text{ TPH}$, whereas the single crusher ceiling is $18\text{ vph}$ ($1{,}647\text{ TPH}$).
- **CANONICAL INTERPRETATION:**  
  The system strictly distinguishes:
  1. `THEORETICAL_KINEMATIC`: Theoretical pipe flux ($700.5\text{ vph}$, never the active bottleneck).
  2. `PRACTICAL_ROAD`: Convoy spacing with platoon turbulence ($180\text{--}600\text{ vph}$).
  3. `SERVICE_RESOURCE`: Facility bottleneck ($18\text{ vph} = 1{,}647\text{ TPH}$).
- **FIX:**  
  Every capacity output must carry an explicit type tag (`THEORETICAL_KINEMATIC`, `PRACTICAL_ROAD`, `SERVICE_RESOURCE`).
- **STATUS:**  
  **RESOLVED & ENFORCED** (Documented in `docs/STAGE5_2_CAPACITY_HIERARCHY.md`).

---

## 4. Retarder Speed vs Capacity Conflation ($92.4\text{ vph}$ vs $92.41\text{ km/h}$)

- **CLAIM:**  
  "Under severe fog, road carrying capacity drops down to $92.4\text{ vph}$."
- **EVIDENCE:**  
  `results/monte_carlo_results.csv`, Row 330, Column 10: Multi-constraint solver output $v_{\text{retarder}} = 25.669\text{ m/s} = 92.410876\text{ km/h}$.
- **CONFLICT:**  
  A drafting error transcribed the velocity column $92.41\text{ km/h}$ as a flow capacity $92.4\text{ vph}$.
- **CANONICAL INTERPRETATION:**  
  $92.41\text{ km/h}$ is a vehicle retarding velocity limit under shallow grade, NOT a fleet capacity.
- **FIX:**  
  Expunged all citations of $92.4\text{ vph}$. Clarified its true origin as a velocity limit.
- **STATUS:**  
  **RESOLVED & DOCUMENTED** (Cataloged in `docs/STAGE3_SCIENTIFIC_AUDIT.md`).

---

## 5. Transient Queue Flush vs Sustainable Throughput ($3{,}294\text{ TPH}$ vs $1{,}647\text{ TPH}$)

- **CLAIM:**  
  "Mine dispatch optimization achieved $3{,}294\text{ TPH}$ throughput."
- **EVIDENCE:**  
  Initial simulation conditions where 6 loaded trucks were initialized directly at the crusher dump hopper, dumping in the first 5 minutes.
- **CONFLICT:**  
  Dumping 6 trucks in 6 minutes yields an instantaneous rate of $36\text{ trucks/hr} \times 91.5\text{ t} = 3{,}294\text{ TPH}$. However, the physical crusher cycle is $200\text{ s}$ ($18\text{ trucks/hr} = 1{,}647\text{ TPH}$). Claiming $3{,}294\text{ TPH}$ violates mass conservation.
- **CANONICAL INTERPRETATION:**  
  Mine throughput must be measured over a steady-state horizon ($T \ge 3600\text{ s}$) excluding the transient flush. Absolute sustainable ceiling is $1{,}647.0\text{ TPH}$.
- **FIX:**  
  Enforce steady-state time averaging and clamp reported facility throughput to $1{,}647\text{ TPH}$.
- **STATUS:**  
  **RESOLVED & ENFORCED** (Enforced in `experiments/run_stage5_1_forensic_benchmark.py`).

---

## 6. HOLD Road Waiting vs Total Waiting Delay (Little's Law)

- **CLAIM:**  
  "Upstream HOLD policy eliminated $73.8\%$ of haulage waiting delay."
- **EVIDENCE:**  
  Waiting time measured specifically on the hazardous $8\%$ downhill fog ramp (Ramp R1).
- **CONFLICT:**  
  By Little's Law ($\bar{L} = \lambda \bar{W}$), holding trucks on flat shovel benches does NOT destroy round-trip delay if the downstream crusher is congested; total delay is conserved ($\approx 125\text{ s}$). Claiming delay elimination misrepresents queue relocation as delay destruction.
- **CANONICAL INTERPRETATION:**  
  HOLD does not eliminate waiting delay; it **relocates** delay spatially from high-risk $8\%$ downhill fog ramps to safe shovel benches, preventing ramp rear-end collisions.
- **FIX:**  
  Ramp waiting time and total system waiting time are reported as separate metrics.
- **STATUS:**  
  **RESOLVED & DOCUMENTED** (Analyzed in `docs/STAGE5_1_HOLD_COUNTERFACTUAL.md`).

---

## 7. Low Visibility ($\le 5\text{ m}$) Operating Regime vs Productive Haulage

- **CLAIM:**  
  "System maintains productive haulage even in $3\text{--}5\text{ m}$ zero-visibility fog."
- **EVIDENCE:**  
  Early presentation marketing slides.
- **CONFLICT:**  
  At $V \le 5\text{ m}$, the available sight stopping distance budget is $S_{\text{stop}} \le R_{\text{sensor}} - S_{\text{base}} = 5.0\text{ m} - 5.0\text{ m} = 0.0\text{ m}$. Because physical braking distance cannot be zero at positive velocity, the Tier-1 governor enforces $v_{\text{safe}} = 0.0\text{ m/s}$. Physical haulage cannot operate; trucks must halt.
- **CANONICAL INTERPRETATION:**  
  For $V \le 5.0\text{ m}$, the system enters `TIER_1_SAFETY_ZERO_SPEED_HALT`. Production is $0\text{ TPH}$.
- **FIX:**  
  Classify $V \le 5\text{ m}$ as emergency halt regime. Production retention is $0\%$, not positive.
- **STATUS:**  
  **RESOLVED & ENFORCED** (Verified in `docs/STAGE5_2_1_PR_AUDIT.md`).

---

## 8. CAN Latency Assumption vs Future Measured CAN Delay

- **CLAIM:**  
  "CAN bus delay was measured as $50\text{ ms}$ (or $100\text{ ms}$)."
- **EVIDENCE:**  
  Hardcoded values in early simulation test harnesses.
- **CONFLICT:**  
  No physical oscilloscope or J1939 CAN bus analyzer measurements were ever performed on a full-scale BEML BH100 in this project. Labeling an assumption as "measured" violates Rule 3 of `AGENTS.md`.
- **CANONICAL INTERPRETATION:**  
  $\tau_{\text{can}} = 50\text{ ms}$ is an **EXPLICIT CONSERVATIVE ASSUMPTION** (5-10x higher than SAE J1939 literature $<10\text{ ms}$). TWAI bench benchmark characterized P95 latency at $19.17\text{ ms}$.
- **FIX:**  
  Tagged strictly as `ASSUMED` in `config/bailadila_hemm_canonical.yaml`. True vehicle validation remains an open field gap.
- **STATUS:**  
  **RESOLVED & DOCUMENTED** (Cataloged in `reports/phase6_can_latency_validation.md`).

---

## 9. Packet-Loss Robustness vs Wireless Communication Reliability

- **CLAIM:**  
  "The system survives $75\%$ packet loss; the wireless communication link is reliable at $25\%$ delivery."
- **EVIDENCE:**  
  Automated test matrix where vehicle safely navigated while $75\%$ of dispatch command packets were dropped.
- **CONFLICT:**  
  An RF link dropping $75\%$ of packets is severely degraded. Confusing safety governor robustness with communication link reliability misrepresents the physical channel.
- **CANONICAL INTERPRETATION:**  
  Communication delivery degrades under packet loss. What survives $75\%$ packet loss is **LOCAL TIER-1 SAFETY GOVERNOR ROBUSTNESS**: valid packets are clamped to $v_{\text{safe}}$, stale packets time out, and the vehicle halts safely if silence persists.
- **FIX:**  
  Always state: "Local safety invariants remained enforced under the tested packet-loss condition; wireless link reliability degrades."
- **STATUS:**  
  **RESOLVED & FORMALIZED** (Enforced in `reports/phase6_rf_validation.md` and `docs/FAILSAFE_ARCHITECTURE.md`).

---

## 10. Test Count vs Software / Physical Correctness

- **CLAIM:**  
  "All 810 passed unit tests prove 100% software and physical correctness."
- **EVIDENCE:**  
  Pytest output summaries.
- **CONFLICT:**  
  Software unit tests verify internal assertion consistency against coded mathematical formulas. They do NOT prove that mathematical equations match Bailadila iron ore wet clay or full-scale haul road dynamics.
- **CANONICAL INTERPRETATION:**  
  Automated regression tests verify algorithmic consistency against specified models; field physical validity remains subject to in-pit calibration.
- **FIX:**  
  Disclaim physical validation in test reporting; qualify test counts as software regression proofs only.
- **STATUS:**  
  **RESOLVED & DOCUMENTED**.

---

## 11. Modeled Non-Collision vs Real-World Collision Avoidance

- **CLAIM:**  
  "Zero collisions in simulation proves 100% real-world collision avoidance."
- **EVIDENCE:**  
  Discrete-time collision detector in `twin/simulator.py`.
- **CONFLICT:**  
  Simulations assume ideal vehicle perception up to sight distance and deterministic braking. Real mines suffer from spilled rock boulders, lens occlusion, and brake fade.
- **CANONICAL INTERPRETATION:**  
  Simulated collision-freedom proves non-colliding trajectories *under modeled kinematics and operational assumptions*.
- **FIX:**  
  Document external physical failure modes as out of scope for kinematic simulation.
- **STATUS:**  
  **RESOLVED & DOCUMENTED** (Detailed in `docs/STAGE5_2_COLLISION_AVOIDANCE.md`).

---

## 12. Software Scalability vs Physical RF Channel Scalability

- **CLAIM:**  
  "System scales linearly to 50 vehicles."
- **EVIDENCE:**  
  Software simulation runs with `num_vehicles = 50`.
- **CONFLICT:**  
  Scaling an array in Python is trivial. 50 physical vehicles broadcasting V2V packets at $10\text{ Hz}$ on a single 433 MHz LoRa channel cause severe packet collisions, duty cycle exhaustion, and $>60\%$ loss.
- **CANONICAL INTERPRETATION:**  
  Software scalability ($100+$ nodes) $\ne$ Physical RF scalability ($12\text{--}16$ nodes per carrier).
- **FIX:**  
  Document RF scalability limits; multi-channel DSSS / TDMA modeling is required for large fleets.
- **STATUS:**  
  **RESOLVED & DOCUMENTED** (Noted in `reports/phase6_contradiction_audit.md`).

---

## 13. Field Validation vs Simulation / Bench Validation

- **CLAIM:**  
  "System is field-validated for NMDC Bailadila Deposit 5 operations."
- **EVIDENCE:**  
  Desktop prototype HIL tests using ESP32 microcontrollers.
- **CONFLICT:**  
  No hardware was ever deployed onto a physical 165-tonne haul truck inside NMDC Bailadila Deposit 5. Calling desktop testing "field validation" breaches Rules 3 and 23 of `AGENTS.md`.
- **CANONICAL INTERPRETATION:**  
  The system is validated via **Simulation and Laboratory Bench Hardware Emulation**. In-pit mine validation is **NOT TESTED / UNVERIFIED (Class C)**.
- **FIX:**  
  Strictly label all physical claims as `SIMULATION` or `BENCH_PROTOTYPE`. Prohibit the phrase "field-validated".
- **STATUS:**  
  **RESOLVED & ENFORCED**.

---

## 14. DSSS Research Model vs Physical LoRa PHY Hardware

- **CLAIM:**  
  "The vehicle communication subsystem operates on DSSS (Direct-Sequence Spread-Spectrum)."
- **EVIDENCE:**  
  Conceptual gateway specifications and PN correlation state machine diagrams.
- **CONFLICT:**  
  The physical bench hardware uses Semtech SX1278 (AI-Thinker Ra-02) transceivers operating on Chirp Spread Spectrum (CSS) LoRa at $433\text{ MHz}$. The SX1278 is a proprietary CSS modem, not a DSSS chip.
- **CANONICAL INTERPRETATION:**  
  The DSSS/PN multi-gateway correlation architecture is an **ARCHITECTURAL RESEARCH & SIMULATION MODEL**. The physical prototype operates on CSS-LoRa.
- **FIX:**  
  Strictly separate the physical CSS-LoRa prototype from the research DSSS model in code and documentation.
- **STATUS:**  
  **RESOLVED & FORMALIZED** (Documented in `docs/DSSS_GATEWAY_ARCHITECTURE.md` and `integration_adapters/dsss_gateway_selector.py`).

---

## 15. Gateway Availability vs Vehicle Safety Authority

- **CLAIM:**  
  "The central gateway controls vehicle stopping distance and ensures safety."
- **EVIDENCE:**  
  Centralized dispatch architecture diagrams.
- **CONFLICT:**  
  If the gateway were the safety authority, loss of the wireless link would leave the vehicle without safety governance, risking runaway collisions.
- **CANONICAL INTERPRETATION:**  
  The gateway is a communication transport only. **The onboard Local Vehicle Safety Governor is the ultimate authority.** When the gateway is lost (`NO_GATEWAY`), the vehicle retains total local safety authority, rejects central commands, and falls back to a safe stop.
- **FIX:**  
  Enforce monotonic authority hierarchy: Level 0 (Physical) $\to$ Level 1 (Local Governor) $\to$ Level 2 (Gateway Validation) $\to$ Level 3 (Central Intelligence).
- **STATUS:**  
  **RESOLVED & VERIFIED** (Enforced in `integration_adapters/fail_safe_controller.py`, verified in `tests/test_failsafe_execution.py`).
