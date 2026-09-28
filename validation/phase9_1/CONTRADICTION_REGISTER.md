# CONTRADICTION REGISTER & RESOLUTION LOG
**FOG-ORCHESTRATOR 2.0 — SIH 2026-27 | Phase 9.1 Hostile Integration Validation**  
**Role:** Lead Safety-Critical Systems Red-Team Engineer / Principal Systems Architect  
**Date:** 2026-09-24  
**Audit Status:** AUDITED — 10 MAJOR REPOSITORY CONTRADICTIONS CATALOGED & RESOLVED

---

## 1. Executive Summary

A rigorous audit of all project documents, configurations, source code, and validation summaries revealed 10 major technical contradictions where different numbers, architectural claims, or operational assumptions clashed.

In accordance with Section 0 and Section 13 of the Red-Team mandate, **none of these contradictions have been concealed or softened**. Each is cataloged with its exact conflicting values, physical interpretation, coexistence verdict, and mandatory engineering resolution.

---

## 2. Master Contradiction Register

### Contradiction 1: 450 ms Target vs. 437.1 ms Analytical vs. 557.3 ms P99 vs. 935.0 ms Cascade
- **Conflicting Values:**
  - Value A: $450.0\text{ ms}$ (Nominal engineering target in presentation decks and `01_CANONICAL_PARAMETERS.md`).
  - Value B: $437.1\text{ ms}$ (Analytical config sum in `config/integration_canonical.yaml`).
  - Value C: $557.3\text{ ms}$ (Measured empirical full-loop P99 in Phase 9.1 benchmarks).
  - Value D: $935.0\text{ ms}$ (Cascade communication loss worst-case in Phase 9.1 cascade test).
  - Value E: $800.0\text{ ms}$ (DGMS standard ceiling).
- **Physical Meaning:**
  - $437.1\text{ ms}$ is a theoretical zero-contention calculation.
  - $450.0\text{ ms}$ is a coarse marketing/presentation target.
  - $557.3\text{ ms}$ is the real measured P99 roundtrip under active LoRa and CAN jitter.
  - $935.0\text{ ms}$ includes the $500\text{ ms}$ remote heartbeat loss timeout before local fail-safe takes over.
- **Can They Coexist?** **NO** as a single interchangeable "latency". They describe completely different operational regimes.
- **Resolution:** Formally separate into:
  1. `T_LOCAL_LOOP_NOMINAL = 243.8 ms`
  2. `T_FULL_LOOP_P99 = 557.3 ms`
  3. `T_CASCADE_WORST_CASE = 935.0 ms`
  4. `T_DGMS_LIMIT = 800.0 ms`.

---

### Contradiction 2: 50 ms CAN Latency Budget vs. 54.8 ms Measured at 99% Load
- **Conflicting Values:**
  - Value A: $T_{\text{CAN}} \le 50.0\text{ ms}$ (Canonical maximum CAN latency budget in `config/integration_canonical.yaml`).
  - Value B: $T_{\text{CAN\_max}} = 54.8\text{ ms}$ (Measured worst-case delivery delay under $99\%$ synthetic bus load).
- **Physical Meaning:** When the TWAI controller transmit buffer is saturated with low-priority telemetry frames, transmission queue delays push delivery past the 50 ms budget by $4.8\text{ ms}$.
- **Can They Coexist?** **NO**. 54.8 ms violates the 50 ms hard budget.
- **Resolution:** Implement strict hardware-level message abort and preemption for Priority 0 emergency frames (`can_emergency_priority = 0x0`). Under preemption, maximum delay is capped at $4.32\text{ ms}$ even at $99\%$ load.

---

### Contradiction 3: 250 ms Actuator Delay Assumption vs. Zero Physical Validation
- **Conflicting Values:**
  - Value A: $T_{\text{actuator}} = 250.0\text{ ms}$ claimed as a verified constant in safety proofs.
  - Value B: Repository contains zero physical measurement of hydraulic caliper lag on a 100-tonne haul truck.
- **Physical Meaning:** Literature on Caterpillar 777D and BEML BH85 trucks indicates hydraulic pressure buildup takes between **$200\text{ ms}$ and $350\text{ ms}$** depending on fluid viscosity, oil temperature, and valve degradation.
- **Can They Coexist?** **NO**. An unverified assumption cannot be claimed as a measured constant.
- **Resolution:** Reclassify $T_{\text{actuator}}$ strictly as **Level F (Engineering Assumption)** / **Level E (Literature Derived)**. Conduct physical testing with pressure transducers during Phase 10 field trials.

---

### Contradiction 4: 433 MHz Telemetry vs. 433 MHz Safe Beacon on Single SX1278
- **Conflicting Values:**
  - Value A: Primary telemetry operates over 433.0 MHz LoRa.
  - Value B: Safe Beacon operates over 433.0 MHz LoRa on the *same physical SX1278 module*.
- **Physical Meaning:** The SX1278 is a **half-duplex transceiver**. Transmitting a Safe Beacon switches the radio into TX mode, completely blinding the receiver to incoming gateway aborts and dispatch packets for **$38.5\text{ ms}$**.
- **Can They Coexist?** **NO**. Single-transceiver shared operation creates co-channel blocking and packet loss.
- **Resolution:** Tagged as an **OPEN SAFETY DEPENDENCY**. Mandate dual-radio architecture (Radio 1 for Gateway, Radio 2 for Beacon) in commercial deployment.

---

### Contradiction 5: DSSS / PN Correlation vs. SX1278 Chirp Spread Spectrum (CSS)
- **Conflicting Values:**
  - Value A: Architectural papers claim "DSSS / PN Code Gateway Correlation and Handover".
  - Value B: Physical prototype uses Semtech SX1278 transceivers which utilize proprietary Chirp Spread Spectrum (CSS), not DSSS Gold codes.
- **Physical Meaning:** The DSSS/PN algorithm is implemented purely as a Python/C++ simulation and research model in software, while physical RF communication utilizes LoRa CSS packets.
- **Can They Coexist?** **YES, IF PROPERLY DEMARCATED**.
- **Resolution:** Explicitly document: LoRa CSS is the physical layer (Level A); DSSS PN sequence correlation is a simulation research layer (Level C/D).

---

### Contradiction 6: "Validated at Bailadila" vs. Benchtop / Simulation Validation
- **Conflicting Values:**
  - Value A: Presentation slides state *"Validated at NMDC Bailadila Iron Ore Mine"*.
  - Value B: Repository evidence shows all experiments were run on an ESP32-S3 benchtop rig with synthetic noise models and digital twin simulations.
- **Physical Meaning:** No physical 100-tonne haul truck was autonomous-braked inside the Bailadila pit during Phase 9.
- **Can They Coexist?** **NO**. Claiming field validation without field trials is a disqualifying integrity violation.
- **Resolution:** Downgrade all references to: *"Validated in hardware-in-the-loop and software simulation using Bailadila terrain models; physical mine deployment pending."*

---

### Contradiction 7: Downhill Crawl Speed (3.52 m/s) vs. 5.0-Meter Buffer Invariant
- **Conflicting Values:**
  - Value A: $v_{\text{crawl}} = 3.52\text{ m/s}$ ($12.67\text{ km/h}$) asserted as safe for $8.0\text{ m}$ visibility with $5.0\text{ m}$ buffer.
  - Value B: On a $-8\%$ downhill ramp with $\mu=0.35$ and $T_{\text{actuator}}=250\text{ ms}$, total stopping distance is $3.885\text{ m}$, leaving only a $4.115\text{ m}$ buffer (eroding buffer by $88.5\text{ cm}$).
- **Physical Meaning:** The $3.52\text{ m/s}$ speed was calculated for flat ground ($\mu=0.7$) and fails to preserve the full $5.0\text{ m}$ buffer on steep wet downhill ramps.
- **Can They Coexist?** **NO**. The safety invariant $S_{\text{stop}} \le R_{\text{eff}} - S_{\text{base}}$ is violated.
- **Resolution:** Revise crawl speed on $-8\%$ ramps down to **$v_{\text{safe}} = 2.99\text{ m/s}$ ($10.76\text{ km/h}$)** (`CONFIG_REV_9_1_02`).

---

### Contradiction 8: Safe Beacon Alerts Control Room vs. Dead Gateway Reality
- **Conflicting Values:**
  - Value A: Safe Beacon specification claims it alerts the Control Room when communication is lost.
  - Value B: If the gateway is dead, RF packets cannot reach the Control Room.
- **Physical Meaning:** A vehicle cannot transmit through a severed link. The Control Room detects the outage via passive heartbeat loss timeout (500 ms).
- **Can They Coexist?** **NO**. Circular dependency.
- **Resolution:** Clarify that Safe Beacon is strictly a peer-to-peer V2V broadcast for adjacent trucks (0-300 m); Control Room alerts are triggered by server-side silence.

---

### Contradiction 9: Friction Coefficient Models ($\mu = 0.70$ vs. $\mu = 0.35$)
- **Conflicting Values:**
  - Value A: Dry road friction $\mu = 0.70$ used in standard kinematic tests.
  - Value B: Monsoon crushed iron ore wet friction $\mu = 0.35$ measured in Bailadila geotechnical surveys.
- **Physical Meaning:** Stopping distance nearly doubles on wet crushed iron ore fines compared to dry hardpack.
- **Can They Coexist?** **YES, AS DYNAMIC MODES**.
- **Resolution:** The GradeAdapter and Tier-1 governor must dynamically inject $\mu=0.35$ whenever the environmental rain/fog sensor indicates water saturation.

---

### Contradiction 10: Watchdog Timeouts (500 ms Comm Loss vs. 150 ms CAN Loss)
- **Conflicting Values:**
  - Value A: `COMM_LOSS_TIMEOUT_MS = 500.0\text{ ms}`.
  - Value B: `CAN_WATCHDOG_TIMEOUT_MS = 150.0\text{ ms}`.
- **Physical Meaning:** CAN bus is local and high-rate (10-50 Hz), so 150 ms is 3-15 missed frames. LoRa is long-range and lower-rate (2-5 Hz), so 500 ms is 1-2 missed frames.
- **Can They Coexist?** **YES**, but under dense fog, 500 ms comm loss is too slow and causes the cascade reaction time to reach $935.0\text{ ms}$.
- **Resolution:** Dynamically reduce `COMM_LOSS_TIMEOUT_MS` to **$200.0\text{ ms}$** in dense fog conditions.
