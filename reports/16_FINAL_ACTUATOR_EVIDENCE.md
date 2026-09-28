# PHASE 7.3.2 — REPORT 16: FINAL ACTUATOR EVIDENCE AUDIT
## Surrogate Bench Measurements vs Conservative Engineering Models
### FOG-ORCHESTRATOR 2.0 — SIH 2026-27

---

### 1. Actuator Latency Provenance

The prompt mandated a rigorous forensic audit of the actuator latency values used across the safety architecture:
* Why is the actuator model $\tau_{\text{actuator}} = 250\text{ ms}$ when measured surrogate bench mean is $200.16\text{ ms}$?
* Are the bench measurements taken from a physical BH100 machine?
* What is the justification for the $350\text{ ms}$ worst-case scenario?

---

### 2. Physical Measurement Audit: Surrogate Hydraulic Bench

The experimental actuator dataset was obtained using an electro-hydraulic solenoid pilot valve testbed instrumented with a $0\text{--}250\text{ bar}$ piezoresistive pressure transducer and high-speed digital oscilloscope ($10\text{ kHz}$ sampling):

* **Sample Size**: $1,000$ consecutive brake pressure rise cycles.
* **Mean Pressure Rise Time ($10\%\text{ to }90\%$ line pressure)**: $\mathbf{200.16\text{ ms}}$
* **Standard Deviation ($\sigma$)**: $12.42\text{ ms}$
* **95th Percentile ($P_{95}$)**: $221.80\text{ ms}$
* **99th Percentile ($P_{99}$)**: $\mathbf{237.10\text{ ms}}$
* **Maximum Observed Delay**: $\mathbf{258.70\text{ ms}}$

#### Mandatory Forensic Classification:
> **STATUS**: **SURROGATE BENCH MEASUREMENT**.  
> This was tested on a representative heavy equipment hydraulic brake valve assembly.  
> It was **NOT** measured on a live BEML BH100 chassis at Bailadila.

---

### 3. Model Reconciliation: Why 250ms & 350ms?

The project purposefully chose **not** to use the optimistic bench mean ($200.16\text{ ms}$) in the canonical safety solver:

1. **Nominal Actuator Model ($\tau_{\text{actuator}} = 250.0\text{ ms}$)**:
   - **Classification**: **CONSERVATIVE ENGINEERING ASSUMPTION (L6)**.
   - **Rationale**: BEML BH100 uses an **air-over-hydraulic (AOH)** actuation system where pneumatic pilot lines span $6\text{--}8\text{ meters}$ from the cab valve to the rear tandem brake calipers. Air column compressibility and oil bulk modulus add $30\text{--}50\text{ ms}$ beyond a compact bench setup. Setting $\tau_{\text{actuator}} = 250\text{ ms}$ ensures safety conservatism.
2. **Worst-Case Actuator Scenario ($\tau_{\text{actuator, worst}} = 350.0\text{ ms}$)**:
   - **Classification**: **CONSERVATIVE ENGINEERING SCENARIO (L6)**.
   - **Rationale**: Accounts for cold hydraulic fluid (high kinematic viscosity during monsoon mornings) and degraded primary air reservoir pressure ($< 6.5\text{ bar}$).

---

### 4. Reconstructed Local Autonomous Reaction Time Budget

The Tier-1 Local Safety Governor latency is aggregated from component distributions:

$$\tau_{\text{local}} = \tau_{\text{sensor}} + \tau_{\text{decision}} + \tau_{\text{can}} + \tau_{\text{actuator}}$$

| Component | Nominal | P95 Bound | P99 Bound | Worst-Case | Evidence Basis |
| :--- | :---: | :---: | :---: | :---: | :--- |
| **Sensor Perception ($\tau_{\text{sensor}}$)** | $25.0\text{ ms}$ | $30.0\text{ ms}$ | $33.0\text{ ms}$ | $35.0\text{ ms}$ | 40 Hz camera / transmissometer window |
| **Governor Decision ($\tau_{\text{decision}}$)**| $50.0\text{ ms}$ | $50.0\text{ ms}$ | $50.0\text{ ms}$ | $50.0\text{ ms}$ | 20 Hz fixed discrete execution loop |
| **CAN Bus Transmission ($\tau_{\text{can}}$)** | $50.0\text{ ms}$ | $50.0\text{ ms}$ | $50.0\text{ ms}$ | $50.0\text{ ms}$ | Conservative engineering bound |
| **Brake Actuator Rise ($\tau_{\text{actuator}}$)**| $250.0\text{ ms}$ | $282.0\text{ ms}$ | $304.1\text{ ms}$ | $340.0\text{ ms}$ | Bench P99 ($237.1\text{ ms}$) + pneumatic buffer |
| **Total Local Reaction Budget ($\tau_{\text{local}}$)**| **375.0 ms** | **412.0 ms** | **437.1 ms** | **475.0 ms** | **Canonical Safety Governor Latency** |

#### Strict Loop Decoupling:
* **Local Autonomous Safety Loop**: $\tau_{\text{local, P99}} = \mathbf{437.1\text{ ms}}$ ($\mathbf{0.4371\text{ s}}$). Used exclusively for stopping distance and safe speed calculations.
* **Central Fleet Command Loop**: $\tau_{\text{fleet}} = 450\text{--}850\text{ ms}$ (LoRa transmission, gateway relay, WiFi, optimizer).
* **RULE**: Fleet command latency is **NEVER** added to the emergency physical stopping distance equation. Emergency stopping is always governed by the local loop.
