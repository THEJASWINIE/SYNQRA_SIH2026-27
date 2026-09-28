# PHASE 7.3.2 — REPORT 18: FINAL CLAIM CLASSIFICATION & FREEZE
## Rigorous Boundary Enforcement & Retraction Register
### FOG-ORCHESTRATOR 2.0 — SIH 2026-27

---

### 1. Classification Methodology

Every claim made across the FOG-ORCHESTRATOR 2.0 system is classified into one of four scientific tiers:
* **GREEN**: Fully demonstrated and reproducible within the verified prototype and simulation scope.
* **YELLOW**: Supported under explicitly documented engineering assumptions, surrogate hardware, or bounded models.
* **RED**: Contradicted, mathematically invalid, or transient artifact (**RETRACTED AND PROHIBITED**).
* **OPEN**: Unvalidated pending physical field trials at NMDC Bailadila.

---

### 2. Five Strongest Defensible Claims (GREEN)

1. **Zero Safety Invariant Violations in Tested Scenarios**:
   - The Tier-1 Local Safety Governor enforces $v_{\text{command}} \le v_{\text{safe}}$ across normal, adversarial, and communication-loss conditions, maintaining zero stopping-margin violations across 10,000 Monte Carlo iterations (minimum margin $+3.0018\text{ m}$).
2. **Sustained Steady-State Production (+35.9% Throughput)**:
   - Level 4 delivers $1,591.4\text{ TPH}$ sustained over extended 2-hour multi-cycle horizons ($96.6\%$ crusher bottleneck utilization), compared to $1,171.2\text{ TPH}$ under conventional uncoordinated fog operation ($p = 5.41 \times 10^{-15}$).
3. **Hazardous Ramp Queue Relocation (-77.4% Ramp Waiting)**:
   - Dynamic shovel slot metering reduces hazardous stationary queue waiting on the steep $-8\%$ haul ramp from $625.4\text{ s} \to 141.6\text{ s}$ ($p = 3.12 \times 10^{-14}$), transferring waiting time to flat, safe shovel staging bays.
4. **Autonomous Communication-Loss Resilience**:
   - Direct peer-to-peer V2V and onboard speed governing ensure that even at $99\%$ packet loss or central backend disconnection, local vehicle safety remains $100\%$ preserved.
5. **Physical Hardware Bench Transceiver Verification**:
   - Physical ESP32 + Semtech SX1278 transceivers achieve $99.1\%$ packet delivery ratio with $41.2\text{ ms}$ round-trip latency at $150\text{ m}$ line-of-sight bench testing.

---

### 3. Five Qualified Claims (YELLOW)

1. **Dual-Regime Speed Governance**:
   - The $18.42\text{ km/h}$ ($5.1158\text{ m/s}$) safe speed at $12\text{ m}$ visibility is qualified as an **emergency adhesion-limited ceiling** ($a_{\text{dec}} = 2.7466\text{ m/s}^2$). Normal service haulage operates at **$13.0\text{--}13.2\text{ km/h}$** ($3.61\text{--}3.67\text{ m/s}$) to prevent rock spillage.
2. **Surrogate Hydraulic Actuator Timing**:
   - Actuator latency measurements (mean $200.16\text{ ms}$, P99 $237.1\text{ ms}$) were obtained on a surrogate hydraulic pilot testbed, not an operational BEML BH100 dumper.
3. **CAN Delay Modeling**:
   - CAN transmission latency is modeled with a conservative $50.0\text{ ms}$ bound pending physical J1939 bus sniffing on the chassis.
4. **DSSS RF Processing Gain**:
   - Direct Sequence Spread Spectrum with Gold codes is implemented as an architectural simulation model; physical transceivers use native Chirp Spread Spectrum (LoRa).
5. **Net Cycle Delay Reduction (-11.6%)**:
   - The $82.8\text{ s}$ net delay savings ($713.6\text{ s} \to 630.8\text{ s}$) is qualified as momentum conservation resulting from the elimination of ramp stop-start accordion shockwaves.

---

### 4. Five Permanently Prohibited Claims (RED / RETRACTED)

1. **PROHIBITED: Claiming 3,294 TPH or 2,745 TPH as Mine Production**:
   - *Reason*: These rates were 6-minute and 10-minute queue-flush transient bursts that exceed the primary gyratory crusher bottleneck ($1,647.0\text{ TPH}$).
2. **PROHIBITED: Claiming 77.4% Total Waiting Reduction**:
   - *Reason*: $401.0\text{ s}$ of the $483.8\text{ s}$ ramp queue wait was relocated to the shovel staging bay. Total trip delay only decreased by $-11.60\%$ ($-82.8\text{ s}$).
3. **PROHIBITED: Pairing 5.12 m/s with a = 1.20 m/s² and Claiming 7m Stopping Distance**:
   - *Reason*: $v = 5.12\text{ m/s}$ with $a = 1.20\text{ m/s}^2$ requires $12.84\text{ m}$ to stop, causing an overrun and crash. Stopping in $7.0\text{ m}$ strictly requires $a = 2.7466\text{ m/s}^2$.
4. **PROHIBITED: Claiming Physical DSSS Modulation on SX1278 Hardware**:
   - *Reason*: Physical transceivers run Chirp Spread Spectrum (CSS). DSSS is simulation-only.
5. **PROHIBITED: Claiming 100% Real-World Safety or Zero-Accident Guarantee**:
   - *Reason*: Simulation and bench tests cannot account for physical mechanical blowouts, uncalibrated sensor blinding, or structural failures.

---

### 5. Remaining Open Field Validations (OPEN)

1. **BEML BH100 J1939 Chassis Bus Logging**: Direct tapping of PGN 61441 and PGN 61444 on live machine.
2. **Bailadila Pit-5 RF Propagation Survey**: 433 MHz and 868 MHz path loss and shadow fading across deep iron ore benches.
3. **Wet Hematite Friction Coefficient Measurement**: In-situ British Pendulum / decelerometer skid tests on wet Bailadila haul ramps.
4. **Air-Over-Hydraulic Caliper Rise Time on BH100**: In-chassis pressure transducer logging during emergency brake application.
