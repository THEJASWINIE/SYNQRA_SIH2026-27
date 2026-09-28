# PHASE 7.3.4 — ATTACK #7 & #8: LATENCY DECOMPOSITION & ACTUATOR PROVENANCE
**Module:** System Timing & Actuator Boundary  
**Datasets:** `data/phase7_3_4_latency_provenance.csv`, `data/phase7_3_4_actuator_sensitivity.csv`  
**Classification:** **HYBRID BENCH-MEASURED & MODELLED (YELLOW)**  

---

## 1. Forensic Decomposition of the 437.1 ms P99 Reaction Latency

The project cites a local reaction latency of $\tau_{\text{local}} = 375.0\text{ ms}$ nominal and $\mathbf{437.1\text{ ms}}$ P99.  
The hostile audit decomposes this parameter into its constituent delays to expose which portions are physically measured and which are modeled assumptions:

$$\tau_{\text{local}} = \tau_{\text{sensor}} + \tau_{\text{decision}} + \tau_{\text{comm}} + \tau_{\text{can}} + \tau_{\text{actuator}}$$

| Component | Nominal (ms) | P99 (ms) | Evidence Level | Physical Origin | Truthful Audit Description |
|:---|:---:|:---:|:---:|:---|:---|
| **$\tau_{\text{sensor}}$ (Perception)** | $100.0$ | $100.0$ | **ASSUMED** | Model | Camera/LiDAR sliding filter and state estimation update window |
| **$\tau_{\text{decision}}$ (Governor)** | $25.0$ | $50.0$ | **BENCH_MEASURED** | Bench | Python safety solver loop (execution $< 5\text{ ms}$, $20\text{ Hz}$ loop period) |
| **$\tau_{\text{comm}}$ (Direct V2V)** | $41.2$ | $50.0$ | **BENCH_MEASURED** | Bench | Dual-ESP32 SX1278 physical LoRa RF bench ($150\text{ m}$ LOS) |
| **$\tau_{\text{can}}$ (Chassis CAN)** | $2.0$ | $5.0$ | **BENCH_MEASURED** | Bench | ESP32 TWAI transceiver hardware bench at $250\text{ kbps}$ ($< 2\text{ ms}$) |
| **$\tau_{\text{actuator}}$ (Brake Valve)** | $200.16$ | $237.1$ | **SURROGATE_BENCH**| Bench | Automotive electro-hydraulic surrogate rig (**NOT A BEML BH100**) |
| **$\tau_{\text{actuator\_canonical}}$** | $250.0$ | $250.0$ | **MODELLED** | Literature | Heavy HEMM air-over-hydraulic pneumatic fill time model |
| **$\tau_{\text{actuator\_worst}}$** | $350.0$ | $350.0$ | **MODELLED** | Literature | Low reservoir air pressure pneumatic lag upper bound |

### Audit Finding:
The sum ($\mathbf{437.1\text{ ms}}$) must **NEVER** be presented as a "measured reaction time of the BEML BH100."  
It is a **HYBRID COMPOSITE LATENCY BUDGET**, combining laboratory bench hardware measurements (dual-ESP32 V2V, TWAI CAN, surrogate hydraulic actuator) with heavy-equipment literature models for sensor perception ($100\text{ ms}$) and pneumatic valve build-up ($250\text{ ms}$).

---

## 2. Sensitivity of Safe Speed to Actuator Latency

To test whether the safety governor breaks under longer pneumatic valve delays, safe speed was recalculated across $\tau_{\text{actuator}} \in [200, 500]\text{ ms}$ at $12\text{ m}$ visibility ($S_{\text{base}} = 5.0\text{ m}$, $a = 2.7466\text{ m/s}^2$):

| Actuator Delay ($\tau_{\text{actuator}}$) | Total Latency ($\tau_{\text{total}}$) | Safe Speed ($v_{\text{safe}}$) | Reaction Dist ($d_{\text{react}}$) | Braking Dist ($d_{\text{brake}}$) | Stopping Dist ($S_{\text{stop}}$) | Total Envelope ($S_{\text{stop}} + 5\text{m}$) |
|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **200.16 ms** (Surrogate Bench) | $387.3\text{ ms}$ | **5.27 m/s (19.0 km/h)** | $2.04\text{ m}$ | $4.96\text{ m}$ | **7.00 m** | $12.00\text{ m}$ (Safe) |
| **250.00 ms** (Canonical Model) | $437.1\text{ ms}$ | **5.12 m/s (18.4 km/h)** | $2.24\text{ m}$ | $4.76\text{ m}$ | **7.00 m** | $12.00\text{ m}$ (Safe) |
| **300.00 ms** (Moderate Fill Lag) | $487.1\text{ ms}$ | **4.97 m/s (17.9 km/h)** | $2.42\text{ m}$ | $4.58\text{ m}$ | **7.00 m** | $12.00\text{ m}$ (Safe) |
| **350.00 ms** (Worst-Case Spec) | $537.1\text{ ms}$ | **4.83 m/s (17.4 km/h)** | $2.59\text{ m}$ | $4.41\text{ m}$ | **7.00 m** | $12.00\text{ m}$ (Safe) |
| **400.00 ms** (Aged Valve Lag) | $587.1\text{ ms}$ | **4.70 m/s (16.9 km/h)** | $2.76\text{ m}$ | $4.24\text{ m}$ | **7.00 m** | $12.00\text{ m}$ (Safe) |
| **500.00 ms** (Severely Degraded) | $687.1\text{ ms}$ | **4.46 m/s (16.0 km/h)** | $3.06\text{ m}$ | $3.94\text{ m}$ | **7.00 m** | $12.00\text{ m}$ (Safe) |

### Audit Insight:
The safety quadratic solver dynamically scales speed downward as actuation delay increases:
- At $\tau_{\text{actuator}} = 200\text{ ms}$, permitted speed is $19.0\text{ km/h}$.
- At $\tau_{\text{actuator}} = 500\text{ ms}$, permitted speed safely throttles to $16.0\text{ km/h}$.
- In **every scenario**, stopping distance is maintained at exactly $7.00\text{ m}$, guaranteeing that the total spatial footprint fits the $12.0\text{ m}$ visibility horizon.
- The control law is physically stable and fail-safe against actuator timing drift.

---

## 3. Brake Hydraulic Pressure Audit: The 12.5 MPa Target

The proposed field target of achieving $90\%$ of $12.5\text{ MPa}$ line pressure was audited:
- **OEM Documentation Status:** Public BEML BH100 manuals do not publish the exact secondary brake line relief pressure.
- **Classification:** **UNVERIFIED AS OEM DOCUMENTED (UNKNOWN)**.
- **Auditor Instruction:** $12.5\text{ MPa}$ must be described as an **arbitrary engineering test target** for future field telemetry, not a verified factory specification of the BH100.
