# FINAL EVIDENCE BOUNDARY & PROVENANCE SPECIFICATION
## FOG-ORCHESTRATOR 2.0 — SIH 2026-27 (Problem Statement SIH26007)
### Authoritative Evidence Taxonomy, Classification Boundaries & Hardware Reality

---

## 1. Absolute Evidence Demarcation

In strict adherence to the project governance charter, scientific integrity principles, and forensic reproducibility guidelines, all evidence generated, referenced, or claimed by **FOG-ORCHESTRATOR 2.0** is mapped into exactly four mutually exclusive evidence classes:

$$\mathbf{CLASS\ A:\ PHYSICAL\ BENCH}\quad\vert\quad \mathbf{CLASS\ B:\ HIL}\quad\vert\quad \mathbf{CLASS\ C:\ SIMULATION}\quad\vert\quad \mathbf{CLASS\ D:\ ANALYTICAL}$$

> [!CAUTION]
> ### MANDATORY OVERARCHING EVIDENCE BOUNDARY
> **NO CLASS A, CLASS B, CLASS C, OR CLASS D EVIDENCE CONSTITUTES FIELD VALIDATION OF A REAL BEML BH100 MINING HAUL TRUCK.**  
> The project did NOT physically instrument or brake an actual 165.5-tonne BH100 hauler on an active mine ramp, did NOT access OEM factory engine/transmission ECU command gates, and did NOT conduct pit-wide wireless surveys in active open-pit dust conditions. All claims are bounded strictly to their classified evidence level.

---

## 2. The Four Authoritative Evidence Classes

```
+───────────────────────────────────────────────────────────────────────────────────────────────────+
│                                  FOUR AUTHORITATIVE EVIDENCE CLASSES                              │
+───────────────────────────────────────────────────────────────────────────────────────────────────+
│ CLASS A: PHYSICAL BENCH                                                                           │
│ Definition: Real embedded hardware, transceivers, and buses physically executing on testbenches.  │
│ Scope: Electronic processing time, RF packet delivery, physical bus arbitration.                 │
├───────────────────────────────────────────────────────────────────────────────────────────────────┤
│ CLASS B: HARDWARE-IN-THE-LOOP (HIL)                                                              │
│ Definition: Embedded microcontroller hardware interacting with mathematical dynamic surrogates.   │
│ Scope: Safety governor command enforcement, J1939-style framing, fault injection watchdogs.      │
├───────────────────────────────────────────────────────────────────────────────────────────────────┤
│ CLASS C: SIMULATION                                                                               │
│ Definition: Timestep-based, closed-loop software simulations across discrete seeds.              │
│ Scope: Fleet-scale throughput, queue redistribution, bottleneck mitigation, Monte Carlo trials.   │
├───────────────────────────────────────────────────────────────────────────────────────────────────┤
│ CLASS D: ANALYTICAL                                                                               │
│ Definition: Closed-form mathematical derivations and first-principles kinematic envelopes.        │
│ Scope: Stopping distance quadratic roots, space headway formulation, crusher service ceilings.   │
+───────────────────────────────────────────────────────────────────────────────────────────────────+
```

---

## 3. Detailed Evidence Inventory by Class

### CLASS A — PHYSICAL BENCH EVIDENCE
*Real electronic hardware, microcontrollers, RF transceivers, and serial buses physically measured on laboratory and outdoor line-of-sight (LOS) testbenches.*

- **ESP32 Dual-Core Firmware Execution:**
  - Microcontroller: ESP32-WROOM-32D (240 MHz dual-core Tensilica LX6).
  - Measurement: Deterministic task tick time ($T_{\text{governor}} = 2.20\text{ ms}$, $T_{\text{sensor}} = 1.26\text{ ms}$).
  - Boundary: Benchtop operating conditions; high-vibration mining chassis mounting unverified.
- **SX1278 LoRa RF Link Performance:**
  - Hardware: Ai-Thinker Ra-02 (Semtech SX1278, 433 MHz, Chirp Spread Spectrum).
  - Measurement: **99.1% Packet Delivery Ratio (PDR)** over $150\text{ m}$ outdoor line-of-sight (LOS) open ground; **41.2 ms** roundtrip ping-pong over-the-air latency.
  - Boundary: Valid strictly in open LOS terrain; open-pit hematite dust attenuation, highwall shadowing, and pit multipath reflections were NOT physically measured.
- **TWAI / CAN 2.0B Physical Bus Timing:**
  - Hardware: ESP32 Two-Wire Automotive Interface (TWAI) with SN65HVD230 transceiver at 250 kbps.
  - Measurement: **0.512 ms** physical wire transmission time per 29-bit extended frame; $13.81\text{ ms}$ total electronic command pipeline.
  - Boundary: Bench wiring harness; not connected to live OEM Cummins QST30 or Allison 8610 transmission CAN backbone.

---

### CLASS B — HARDWARE-IN-THE-LOOP (HIL) EVIDENCE
*Physical microcontroller running real embedded safety firmware connected in real-time to simulated vehicle dynamics and actuator models.*

- **Tier-1 Local Safety Governor Execution:**
  - Real firmware on ESP32 running FreeRTOS clamps incoming speed requests against the local quadratic stopping envelope.
  - Demonstrated: Clamping adversarial $30.0\text{ m/s}$ requests down to $5.12\text{ m/s}$ ($18.4\text{ km/h}$) in dense fog without communication disruption.
- **Project-Defined J1939-Style Framing:**
  - Protocol: 6 project-defined J1939-compatible PGNs (61444, 65265, 61441, 65281, 65282, 65280) encoding electronic speed, engine RPM, retarder status, and beacon alarms.
  - Boundary: Framing and decoding validated over TWAI; OEM factory proprietary security certificates and unlock seed-keys unvalidated.
- **End-to-End Command-Path Latency Characterization:**
  - Measurement: **216.05 ms median** command-path latency under the configured actuator model.
  - Explicit Decomposition: $13.81\text{ ms}$ physical bench electronics ($1.26\text{ ms}$ sensor + $2.20\text{ ms}$ governor + $12.55\text{ ms}$ CAN queue) + $202.24\text{ ms}$ modeled electro-pneumatic actuator build-up lag.
  - Boundary: Does NOT represent physical brake pad contact on real steel drums.
- **Actuator Surrogate & Fault Injection:**
  - Software watchdog detects actuator non-response ($500\text{ ms}$ threshold) and transitions to fail-closed state (`ACTUATOR_FAULT_NON_RESPONSIVE`).
  - Boundary: Software-level detection demonstrated; physical mechanical brake seizure containment unvalidated.
- **Frozen Sensor Handling (HIL-23):**
  - Stale frame timeout ($150\text{ ms}$) verified. Single-channel static float freeze classified as **PARTIAL**; redundant physical sensing required for full containment.

---

### CLASS C — SIMULATION EVIDENCE
*Timestep-based, closed-loop multi-vehicle fleet orchestration simulations and stochastic Monte Carlo evaluations.*

- **20-Seed Master Haulage Benchmark:**
  - Configuration: 20 matched seeds (101 to 197), 7,200 s (2-hour shift) horizon, 6 x BEML BH100 dumpers, sustained $12.0\text{ m}$ fog, -8% downhill ramp.
  - Results:
    - Hazardous ramp waiting reduced from $625.4\text{ s}$ (L1) to $141.6\text{ s}$ (L4) (**77.36% reduction**, $t=58.02$, $p=1.50\times 10^{-31}$).
    - Modeled delivered throughput increased from $1171.2\text{ TPH}$ (L0) to $1591.4\text{ TPH}$ (L4) (**+35.88% relative to L0**; **+27.46% relative to L1**).
    - Net total trip delay reduced from $713.6\text{ s}$ to $630.8\text{ s}$ (**11.60% net reduction**).
    - Peak ramp queue reduced from $7.8\text{ trucks}$ (L0) to $1.2\text{ trucks}$ (L4).
    - Post-fog recovery accelerated from $950\text{ s}$ (L1) to $180\text{ s}$ (L4).
  - Boundary: Valid strictly for the modeled haul-road and crusher configuration; does NOT imply measured production from an actual NMDC pit.
- **10,000-Trial Monte Carlo Safety Stress Testing:**
  - Sampling: Randomized parameter vectors across mass ($74.0\text{ to }165.5\text{ t}$), grade ($-8\%\text{ to }+8\%$), friction ($\mu \in [0.20, 0.45]$), visibility ($3.0\text{ to }100.0\text{ m}$), and lag ($\tau \in [0.20, 0.475]\text{ s}$).
  - Results: **Zero defined safety-invariant violations** ($v_{\text{command}} \le v_{\text{safe}}$ and $S_{\text{stop}} + S_{\text{base}} \le R_{\text{effective}}$ across all moving trials).
  - Boundary: Bounded by 1D longitudinal assumptions; lateral tire slip and multi-body dynamics unmodeled.
- **Predictive Queue & Bottleneck Propagation:**
  - What-if Digital Twin engine evaluates queue growth on ramp and issues proactive staging holds at flat shovel bays before ramp gridlock forms.

---

### CLASS D — ANALYTICAL EVIDENCE
*First-principles mathematical derivations, kinematic closed-form roots, and physical conservation laws.*

- **Master Longitudinal Force Balance:**
  - Equations: $m \frac{dv}{dt} = F_{\text{drive}} + m g \sin(\theta) - F_{\text{roll}} - F_{\text{aero}} - F_{\text{retarder}} - F_{\text{brake}}$.
  - Canonical emergency net deceleration derived: $a_{\text{emergency\_canonical}} = 2.7856\text{ m/s}^2$ on -8% grade ($165,500\text{ kg}$, $C_{\text{rr}}=0.025$, $F_{\text{brake}}=550\text{ kN}$).
  - Legacy baseline deceleration preserved: $a_{\text{emergency\_legacy}} = 2.7466\text{ m/s}^2$.
  - Service deceleration ceiling: $a_{\text{service}} = 1.2000\text{ m/s}^2$.
- **Closed-Form Quadratic Stopping Envelope:**
  - Derivation: $v_{\text{stop}} = -a_{\text{dec}} \tau_{\text{total}} + \sqrt{(a_{\text{dec}} \tau_{\text{total}})^2 + 2 a_{\text{dec}} (R_{\text{effective}} - S_{\text{base}})}$.
  - Canonical dense-fog safe speed at $R_v = 12.0\text{ m}$: $v_{\text{safe}} = 5.12\text{ m/s}$ ($18.4\text{ km/h}$).
  - Blindout threshold: At $R_v \le 5.0\text{ m}$, $R_{\text{effective}} \le S_{\text{base}}$, yielding $v_{\text{safe}} = 0.00\text{ m/s}$ (mandatory controlled halt).
- **Defensive Space Headway Formulation:**
  - Formula: $H_{\text{space}} = S_{\text{stop}}(v) + S_{\text{base}} + L_{\text{truck}}$.
  - Canonical dense-fog space headway: $H_{\text{space}} = 6.94\text{ m} + 5.00\text{ m} + 10.53\text{ m} = 22.52\text{ m}$.
- **Theoretical Kinematic Road Capacity Flux:**
  - Formula: $C_{\text{road}} = 3600 \cdot v_{\text{safe}} / H_{\text{space}}$.
  - Emergency kinematic road flow: **817.8 VPH** (at $5.12\text{ m/s}$, $22.52\text{ m}$ headway).
  - Service kinematic road flow: **587.2 VPH** (at $3.61\text{ m/s}$, $22.13\text{ m}$ headway, $a_{\text{service}} = 1.2\text{ m/s}^2$).
  - *Crucial Classification:* These values represent theoretical pipe flow. They are NOT mine ore throughput.
- **Crusher Modeled Service Ceiling:**
  - Derivation: $(3600\text{ s} / 200\text{ s/truck}) \times 91.5\text{ t} = 18\text{ dumps/hr} \times 91.5\text{ t} = \mathbf{1647.0\text{ TPH}}$.
  - Physical boundary: Any sustained production claim exceeding $1647\text{ TPH}$ on a single tipping pocket is physically impossible.

---

## 4. Summary Traceability Cross-Reference

| Claim / Metric | Value | Evidence Class | Primary Grounding Artifact |
|---|---|---|---|
| ESP32 Governor Task Execution | 2.20 ms | **CLASS A** (Physical Bench) | `esp32_code/` bench oscilloscope / FreeRTOS timer |
| SX1278 LoRa PDR (150m LOS) | 99.1% | **CLASS A** (Physical Bench) | `FINAL_COMMUNICATION_VALIDATION.csv` |
| TWAI / CAN Wire Delay | 0.512 ms | **CLASS A** (Physical Bench) | Logic analyzer capture on SN65HVD230 |
| Electronic Command Latency (HIL) | 216.05 ms | **CLASS B** (HIL) | `FINAL_HIL_VALIDATION.csv` (13.8ms bench + 202.2ms model) |
| J1939-Style Frame Protocol | 6 PGNs decoded | **CLASS B** (HIL) | `integration_adapters/can_twai_hil.py` |
| Actuator Non-Response Watchdog | 500 ms timeout | **CLASS B** (HIL) | `FINAL_SCENARIO_MATRIX.csv` (Scenario S20) |
| Ramp Waiting Time Reduction | -77.36% | **CLASS C** (Simulation) | `FINAL_BENCHMARK.csv` across 20 matched seeds |
| Modeled Throughput Gain | +35.88% (vs L0) | **CLASS C** (Simulation) | `FINAL_BENCHMARK.csv` (1171.2 to 1591.4 TPH) |
| Monte Carlo Safety Adherence | 0 violations / 10,000 | **CLASS C** (Simulation) | `FINAL_SAFETY_VALIDATION.csv` |
| Emergency Net Deceleration | 2.7856 m/s² | **CLASS D** (Analytical) | Force balance on -8% grade (`FINAL_CANONICAL_MODEL.md`) |
| Canonical Fog Safe Speed | 5.12 m/s | **CLASS D** (Analytical) | Closed-form quadratic root at 12m visibility |
| Canonical Fog Space Headway | 22.52 m | **CLASS D** (Analytical) | $S_{\text{stop}} + S_{\text{base}} + L_{\text{truck}}$ formulation |
| Emergency Road Flow Flux | 817.8 VPH | **CLASS D** (Analytical) | Kinematic pipe flow formula ($3600 \cdot v / H$) |
| Service Road Flow Flux | 587.2 VPH | **CLASS D** (Analytical) | Kinematic flow under $1.2\text{ m/s}^2$ service decel |
| Crusher Service Ceiling | 1647.0 TPH | **CLASS D** (Analytical) | 200 s tipping cycle on 91.5 t payload |
| Physical BH100 Braking in Field | **UNVALIDATED** | **NONE** | Acknowledged physical boundary (Future Work) |
