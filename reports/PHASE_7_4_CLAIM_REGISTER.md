# PHASE 7.4 — SYSTEM CLAIM REGISTER & EVIDENCE BOUNDARIES
## FOG-ORCHESTRATOR 2.0 — SIH26007
**Purpose:** Formal Evaluator Claim Boundary Register  
**Authoritative Classification:** Demonstrated, Conditionally Supported, Not Validated  

---

## 1. Category A: DEMONSTRATED (Empirically & Programmatically Verified)

The following claims are rigorously demonstrated by automated tests, bench data logging, and formal code execution:

1. **Local Governor Supremacy:** The onboard `LocalVehicleSafetyGovernor` unconditionally enforces $v_{\text{command}} \le v_{\text{safe}}$ across all tested operating modes, central commands, and communication failure states.
2. **Total RF Independence:** When Gateway, V2V, and Safe Beacons are completely severed, the local vehicle governor remains fully operational and clamps the vehicle to local sensor-derived safe speed envelopes.
3. **Replay & Out-of-Order Rejection:** The `SafeBeaconAdapter` and `LocalVehicleSafetyGovernor` reject replayed, duplicated, and out-of-order sequence packets via monotonic sequence tracking. An old `NORMAL` packet cannot cancel an active `STOP` or `EMERGENCY` state.
4. **Stale Command Expiry:** Commands with age $> 1.0\text{ s}$ are deterministically rejected (`STALE_COMMAND`), preventing delayed commands from actuating following communication freezes.
5. **Safe Beacon Protocol Validation:** The canonical payload format `BEACON,vehicle_id,sequence,state,timestamp,zone_id` is parsed and validated against strict schema, enum, and timestamp bounds without crashing.
6. **Dense Fog Chattering Elimination:** The Schmitt-trigger debounce filter eliminates command oscillation ($0 \leftrightarrow 0.21\text{ m/s}$) when visibility fluctuates around the $5.0\text{ m}$ boundary ($4.9\text{ m} \leftrightarrow 5.1\text{ m}$).
7. **CSS-LoRa SX1278 Bench Performance:** Under line-of-sight bench conditions, Semtech SX1278 transceivers achieve $100\%$ PDR (V2V) and $98.1\%$ PDR (Gateway) with a P95 round-trip latency of $27.3\text{ ms}$.
8. **Automated Test Coverage:** 949 automated tests pass across the codebase (including all 18 invariants I1–I18, all 25 failure scenarios SAFE-01–SAFE-25, and dedicated Phase 7.4.1 consistency verification) with zero failures.
9. **Monte Carlo Safety Envelope Conformance:** Across $N = 10{,}000$ randomized Monte Carlo trials under joint environmental (visibility, friction, grade), communication (loss rate, link availability), and reaction latency variations, zero safety invariant violations were observed ($v_{\text{applied}} \le v_{\text{safe}}$ held in 100% of trials). Minimum margin is identically $0.0000\text{ m}$ because the governor clamps overspeed commands down to the exact analytical stopping boundary $v_{\text{stop}}$ where $S_{\text{stop}} + S_{\text{base}} = R_{\text{effective}}$.

---

## 2. Category B: CONDITIONALLY SUPPORTED (Model-Derived & Simulation Evidence)

The following claims are mathematically sound and verified in simulation, but rely on adopted engineering assumptions or surrogate models:

1. **Model-Derived Emergency Deceleration ($a_{\text{emergency}} \approx 2.7856\text{ m/s}^2$):** Analytically derived from vehicle mass ($165.5\text{ t}$), $-8\%$ downgrade, wheel brake force capacity ($550\text{ kN}$), and wet ore surface adhesion ($\mu = 0.35$).
2. **Service Deceleration ($a_{\text{service}} = 1.2000\text{ m/s}^2$):** Adopted engineering operational and component comfort assumption for haul road operations.
3. **Actuator Latency Model ($\tau_{\text{actuator}} = 200\text{ ms}$):** Adopted from air-over-hydraulic heavy vehicle engineering literature; bench verified only on surrogate actuator hardware.
4. **Simulated DSSS Multi-Gateway Performance:** Multi-gateway Gold code pseudo-noise correlation, handover hysteresis, and persistence logic are verified in Python simulation (L9), not on physical DSSS PHY silicon.
5. **Fleet Throughput Improvement ($+35.88\%$, $+420.2\text{ TPH}$):** Steady-state queuing and headway improvement from Level 0 ($1{,}171.2\text{ TPH}$) to Level 4 ($1{,}591.4\text{ TPH}$) validated in multi-seed closed-loop simulation.

---

## 3. Category C: NOT VALIDATED (Explicitly Unverified in Field)

The following capabilities have **NOT** been verified on real mining hardware and must **NEVER** be claimed to evaluators:

1. **Production BEML BH100 Physical Braking:** Stopping distances and decelerations have **NOT** been measured on an actual 165.5-tonne dump truck at NMDC Bailadila.
2. **Production J1939 Vehicle Bus Integration:** Tested on microcontroller bench CAN/TWAI nodes; **NOT** integrated into an OEM Cummins/Allison J1939 production vehicle bus. Status: `J1939 = PARTIAL / UNVERIFIED`.
3. **Mine-Wide Open-Pit RF Propagation:** Physical RF tests were bench/indoor laboratory measurements; deep iron ore pit diffraction and multipath shadowing have not been field-tested.
4. **Field Optical Fog Sensor Response:** Visibility estimation models have not been exposed to real tropical monsoon cloud fog in Chhattisgarh.
5. **Production Autonomous Brake Actuation:** The prototype provides advisory guidance and driver-assistance warnings; it does **NOT** command electro-pneumatic brake actuators on a production haul truck.
