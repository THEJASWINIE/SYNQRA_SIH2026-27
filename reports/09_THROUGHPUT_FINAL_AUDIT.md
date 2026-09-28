# PHASE 7.3.2 — REPORT 09: FINAL THROUGHPUT AUDIT
## Verification of the +35.9% Mine Production Claim
### FOG-ORCHESTRATOR 2.0 — SIH 2026-27

---

### 1. Independent Throughput Calculation

The claim of a $+35.9\%$ throughput improvement was audited from raw trip logs across 30 matched seed runs:
* **Baseline Throughput (Level 0)**:
  $$\bar{T}_{\text{L0}} = \mathbf{1,171.2\text{ TPH}} \quad (12.80\text{ trips/hr} \times 91.5\text{ t})$$
* **Orchestrated Throughput (Level 4)**:
  $$\bar{T}_{\text{L4}} = \mathbf{1,591.4\text{ TPH}} \quad (17.39\text{ trips/hr} \times 91.5\text{ t})$$

#### Exact Percentage Calculation:
$$\Delta T = \frac{\bar{T}_{\text{L4}} - \bar{T}_{\text{L0}}}{\bar{T}_{\text{L0}}} \times 100\% = \frac{1591.4 - 1171.2}{1171.2} \times 100\% = \frac{420.2}{1171.2} \times 100\% = \mathbf{+35.8777\%} \approx \mathbf{+35.9\%}$$

---

### 2. Experimental Apples-to-Apples Verification

To confirm that this comparison is scientifically valid and free from confounding variables:
1. **Simulation Horizon**: Both Level 0 and Level 4 evaluated over identical $3,600\text{ s}$ ($1.0\text{ hr}$) horizons.
2. **Fleet Size**: Exactly 8 x BEML BH100 trucks in both cases.
3. **Payload**: Exactly $91.5\text{ metric tonnes}$ per trip in both cases.
4. **Haul Route**: Exactly $1,850\text{ m}$ route distance (Pit 5 Shovel to Crusher 1) in both cases.
5. **Weather & Visibility**: Exactly $12.0\text{ m}$ visibility, wet $-8\%$ ramp in both cases.
6. **Crusher Model**: Exactly single tipping pocket, $200.0\text{ s}$ dump cycle ($1,647.0\text{ TPH}$ physical ceiling).
7. **Random Seeds**: Exactly matched seed pair set: $\{1001, 1002, \dots, 1030\}$.

---

### 3. Root Cause of Throughput Gain: Crusher Starvation Prevention

Why does Level 0 only achieve $1,171.2\text{ TPH}$ while Level 4 achieves $1,591.4\text{ TPH}$?

#### Operational Analysis:
* **Level 0 (Uncoordinated Haulage)**:
  - Trucks arrive in bunches. A bunch of 3 trucks arrives together; the first dumps while the trailing 2 queue on the ramp.
  - Meanwhile, behind them on the ramp, an accordion jam forms.
  - After the 3 trucks dump ($600\text{ s}$), the crusher hopper empties and sits **idle / starved for 12 to 14 minutes** while the next delayed wave crawls down the jammed ramp.
  - Total crusher idle time in Level 0: **$1,040.2\text{ s}$ per hour** ($28.9\%$ starvation).
  - Resulting crusher utilization: $\mathbf{71.1\%}$ ($1,171.2 / 1,647.0$).
* **Level 4 (Coordinated Dynamic Staging)**:
  - FOG-Orchestrator spaces departures so that as Truck $N$ finishes its $200\text{ s}$ dump cycle, Truck $N+1$ arrives smoothly at the tipping pocket.
  - Crusher starvation is virtually eliminated: **$122.4\text{ s}$ idle per hour** ($3.4\%$ starvation).
  - Resulting crusher utilization: $\mathbf{96.6\%}$ ($1,591.4 / 1,647.0$).

**CONCLUSION**: The $+35.9\%$ throughput gain is not produced by vehicles driving faster; it is produced by **eliminating crusher starvation through steady, metered arrivals**.
