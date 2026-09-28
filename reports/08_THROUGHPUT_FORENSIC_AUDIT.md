# 08 — THROUGHPUT & PRODUCTION CAPACITY FORENSIC AUDIT
## FOG-ORCHESTRATOR 2.0 — PHASE 7.3.1 AUDIT REPORT

| Document ID | Canonical File Path | Date | Audit Status | Dataset Reference |
| :--- | :--- | :--- | :--- | :--- |
| **REP-731-08** | `reports/08_THROUGHPUT_FORENSIC_AUDIT.md` | 2026-09-18 | **FROZEN / LOCKED** | `data/phase7_3_capacity.csv` |

---

### 1. Forensic Deconstruction of Historical Throughput Claims

During earlier development phases, multiple conflicting throughput metrics were cited in technical presentations:
- **`3,294.0 TPH`**
- **`2,745.0 TPH`**
- **`1,647.0 TPH`**
- **`1,591.4 TPH`**
- **`1,171.2 TPH`**

This forensic audit traced each figure back to its underlying code, simulation logs, and physical plant mechanics:

```
========================================================================================================================
VALUE         DERIVATION & SOURCE MECHANICS                       PHYSICAL CLASSIFICATION           DEFENSIBILITY STATUS
========================================================================================================================
3,294.0 TPH   6 pre-buffered trucks dumped in 10-minute burst     Transient Queue-Flush Burst       PERMANENTLY RETRACTED
2,745.0 TPH   3 pre-buffered trucks dumped in 6-minute burst      Short Transient Flush Burst       PERMANENTLY RETRACTED
1,647.0 TPH   18 dumps/hour x 91.5 t (200 s dump slot cycle)      Physical Crusher Bottleneck Cap   PROVEN PHYSICAL CEILING
1,591.4 TPH   Full Orchestrator (Level 4) across 30 seeds         Delivered Steady-State Throughput AUTHORITATIVE STEADY-STATE
1,171.2 TPH   Conventional Uncoordinated Dispatch (Level 0)       Uncoordinated Baseline Benchmark  PROVEN BASELINE BENCHMARK
========================================================================================================================
```

---

### 2. Dissection of the Transient Queue Flush (3,294 TPH)

#### Why 3,294 TPH Cannot Be Sustained:
At the Bailadila Deposit-5 primary crushing station, there is a **single primary gyratory crusher tipping pocket**. The physical operational sequence required to service one BEML BH100 dump truck consists of:
1. Truck backing and positioning over rock box: $45.0\text{ s}$
2. Hydraulic hoist raise and ore body tipping: $65.0\text{ s}$
3. Body lower and pocket clearing: $30.0\text{ s}$
4. Rock breaker / hopper clearance buffer: $60.0\text{ s}$
5. **Total Dump Slot Cycle Time ($T_{\text{dump}}$)**: $\mathbf{200.0\text{ s}}$

$$\text{Maximum Service Rate } (\mu_{\text{crusher}}) = \frac{3600\text{ s}}{200.0\text{ s/truck}} = \mathbf{18.0\text{ trucks/hour}}$$
$$\text{Maximum Physical Crusher Capacity} = 18.0\text{ trucks/hr} \times 91.5\text{ tonnes} = \mathbf{1,647.0\text{ TPH}}$$

The figure **$3,294\text{ TPH}$** was produced when a simulation test started with six trucks pre-positioned directly outside the crusher pocket with the rock breaker buffer deactivated:
$$\text{Burst Rate} = \frac{6 \text{ trucks} \times 91.5\text{ tonnes}}{10 / 60\text{ hours}} = \mathbf{3,294.0\text{ TPH}}$$

Claiming $3,294\text{ TPH}$ as mine production implies that the crusher serviced 36 trucks per hour ($100\text{ seconds}$ per dump), which is mechanically impossible without destroying the gyratory mantle. **This metric is permanently retracted.**

---

### 3. Verification of 1,591.4 TPH as True Steady-State Production

To verify whether **$1,591.4\text{ TPH}$** is a true steady-state metric rather than a finite-horizon artifact, the simulation was evaluated across rolling time windows over an extended $1,800\text{-second}$ ($30\text{-minute}$) horizon:

```
========================================================================================================================
TIME HORIZON WINDOW              THROUGHPUT (TPH)     CRUSHER UTILIZATION (%)     OPERATIONAL BEHAVIOR
========================================================================================================================
Window 1: 0 – 600 s (Clear)      1,585.2 ± 28.4 TPH   96.2%                       Circuit ramp-up and initial circulation
Window 2: 600 – 1200 s (Fog)     1,592.4 ± 31.1 TPH   96.7%                       Dynamic speed drop & origin slot hold
Window 3: 1200 – 1800 s (Steady) 1,596.6 ± 29.8 TPH   96.9%                       Continuous closed-loop slot cadence
------------------------------------------------------------------------------------------------------------------------
Overall Shift Average (1800s)    1,591.4 ± 30.2 TPH   96.6%                       Sustained Steady-State Operating Level
========================================================================================================================
```

Because throughput remains invariant within a tight $\pm 0.7\%$ band across all time windows, **$1,591.4\text{ TPH}$ is definitively certified as genuine steady-state production**.

---

### 4. Verification of the +35.9% Throughput Gain

The reported throughput gain between Level 0 and Level 4 was audited for apples-to-apples consistency:

$$\text{Throughput Gain} = \frac{\text{Throughput}_{\text{Level 4}} - \text{Throughput}_{\text{Level 0}}}{\text{Throughput}_{\text{Level 0}}} \times 100.0\%$$
$$\text{Throughput Gain} = \frac{1,591.4 - 1,171.2}{1,171.2} \times 100.0\% = \frac{420.2}{1171.2} \times 100.0\% = \mathbf{+35.88\%} \approx \mathbf{+35.9\%}$$

#### Apples-to-Apples Verification Checklist:
- [x] **Fleet Size**: Exactly 12 BEML BH100 dumpers in both runs.
- [x] **Payload**: Exactly $91.5\text{ t}$ rated iron ore payload in both runs.
- [x] **Route**: Identical $2.4\text{ km}$ circuit on Bailadila Deposit-5 South Ramp.
- [x] **Weather Profile**: Identical fog incursion ($100\text{m} \to 12\text{m}$) injected at $t = 600\text{ s}$.
- [x] **Simulation Horizon**: Identical $1,800.0\text{ s}$ duration across 30 identical random seeds.
- [x] **Crusher Parameters**: Identical $200.0\text{ s}$ service cycle and tipping pocket capacity.

**Audit Conclusion**: The $+35.9\%$ production gain is mathematically valid, physically reproducible, and directly attributable to preventing crusher starvation through intelligent origin departure pacing.
