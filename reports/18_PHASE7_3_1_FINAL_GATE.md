# 18 — PHASE 7.3.1 FINAL NUMERICAL CONSISTENCY GATE & LOCK
## FOG-ORCHESTRATOR 2.0 — SIH 2026-27 / SIH26007

| Document ID | Canonical File Path | Date | Audit Status | Governing Standard |
| :--- | :--- | :--- | :--- | :--- |
| **REP-731-18** | `reports/18_PHASE7_3_1_FINAL_GATE.md` | 2026-09-18 | **FROZEN / LOCKED** | ISO 3450 / DGMS 09/2008 |

---

### SECTION 30: FINAL DECISION GATE — FORENSIC VERIFICATION RESPONSES

#### 1. Is the 5.12 m/s value mathematically valid?
**YES, UNDER EMERGENCY FRICTION RETARDING ($a_{\text{dec}} = 2.7466\text{ m/s}^2$).**  
It is the exact analytical quadratic root of $v \cdot \tau + \frac{v^2}{2a} \le 7.00\text{ m}$ ($12.0\text{ m}$ visibility $- 5.0\text{ m}$ buffer) with $\tau = 0.437\text{ s}$ (P99 latency).  
However, it is **INVALID** if evaluated with $a_{\text{dec}} = 1.20\text{ m/s}^2$, which yields $S_{\text{stop}} = 12.84\text{ m}$ (crashing into the obstacle at $12\text{ m}$).

#### 2. What is the corrected $v_{\text{safe}}$ at 12 m?
* **Under Emergency Adhesion Braking ($a_{\text{dec}} = 2.7466\text{ m/s}^2$)**: **$5.1158\text{ m/s}$ ($18.42\text{ km/h}$)** under P99 latency ($0.437\text{ s}$), stopping in $7.00\text{ m}$.
* **Under Conservative Service Braking ($a_{\text{dec}} = 1.2000\text{ m/s}^2$)**: **$3.6078\text{ m/s}$ ($12.99\text{ km/h}$)** under P99 latency ($0.437\text{ s}$), or **$3.6734\text{ m/s}$ ($13.22\text{ km/h}$)** under nominal latency ($0.375\text{ s}$), stopping in $7.00\text{ m}$.

#### 3. What is the corrected stopping distance?
* At $v = 5.1158\text{ m/s}$ with $a_{\text{dec}} = 2.7466\text{ m/s}^2$ and $\tau = 0.437\text{ s}$:
  $$S_{\text{stop}} = (5.1158 \times 0.437) + \frac{5.1158^2}{2 \times 2.7466} = 2.2356 + 4.7644 = \mathbf{7.0000\text{ m}}$$
  Total requirement $= 7.0000 + 5.0000 = \mathbf{12.0000\text{ m}}$ (Exactly matches $12.0\text{ m}$ visibility).
* At $v = 3.6734\text{ m/s}$ with $a_{\text{dec}} = 1.2000\text{ m/s}^2$ and $\tau = 0.375\text{ s}$:
  $$S_{\text{stop}} = (3.6734 \times 0.375) + \frac{3.6734^2}{2 \times 1.2000} = 1.3775 + 5.6225 = \mathbf{7.0000\text{ m}}$$
  Total requirement $= 7.0000 + 5.0000 = \mathbf{12.0000\text{ m}}$ (Exactly matches $12.0\text{ m}$ visibility).

#### 4. What latency should be canonical?
* **Local Safety Loop (Governs Emergency Stopping)**:
  - Nominal: $\tau_{\text{local, nominal}} = \mathbf{375.0\text{ ms}}$ ($25 + 50 + 50 + 250\text{ ms}$)
  - Statistical P99 Bound: $\tau_{\text{local, P99}} = \mathbf{437.1\text{ ms}}$
  - Conservative Worst-Case: $\tau_{\text{local, worst}} = \mathbf{475.0\text{ ms}}$
* **Fleet Command Loop (Governs Dispatch & Slots; Excluded from Stopping)**:
  - Round-Trip P50: $\tau_{\text{fleet, P50}} = \mathbf{685.0\text{ ms}}$
  - Round-Trip P99: $\tau_{\text{fleet, P99}} = \mathbf{1,120.0\text{ ms}}$

#### 5. Is 250 ms actuator latency justified?
**YES, AS A CONSERVATIVE ENGINEERING SAFETY FACTOR ($1.25\times$).**  
Surrogate bench measurements produced a mean of $200.16\text{ ms}$ ($P99 = 237.1\text{ ms}$, $\max = 258.7\text{ ms}$). Setting the simulation nominal parameter to $250.0\text{ ms}$ conservatively covers cold oil and line friction.

#### 6. Is 1.20 m/s² deceleration actually supported?
**SUPPORTED ONLY AS A CONSERVATIVE SERVICE RETARDING ASSUMPTION (L6).**  
It is **NOT** an ISO 3450 statutory clause for the BH100. ISO 3450 service brake criteria yield $a \approx 2.8\text{--}3.5\text{ m/s}^2$ loaded. Claiming "ISO specifies $1.20\text{ m/s}^2$" is retracted.

#### 7. Is $H_{\text{safe}}$ correctly calculated?
**YES, AFTER CORRECTING FOR THE 5.0m BUFFER OMISSION.**  
* Historical $17.52\text{ m}$ accidentally omitted $S_{\text{base}} = 5.00\text{ m}$.
* Canonical Space Headway: $H_{\text{space}} = S_{\text{stop}}(7.0) + S_{\text{base}}(5.0) + L_{\text{truck}}(10.52) = \mathbf{22.52\text{ m}}$.

#### 8. Is 700.5 VPH correctly derived?
**YES, DERIVED FROM LEGACY $v_{\text{safe}} = 4.3815\text{ m/s}$.**  
$\frac{3600 \times 4.3815}{22.52} = 700.417\text{ VPH} \approx \mathbf{700.5\text{ VPH}}$. Under $v_{\text{safe}} = 5.116\text{ m/s}$, theoretical flux is **$817.8\text{ VPH}$**; under service $v_{\text{safe}} = 3.673\text{ m/s}$, it is **$587.2\text{ VPH}$**.

#### 9. Is 1647 TPH correctly derived?
**YES, DERIVED DIRECTLY FROM PHYSICAL PLANT CYCLE.**  
Primary gyratory crusher single tipping pocket has a $200.0\text{ s}$ dump slot cycle ($18\text{ dumps/hr}$). At $91.5\text{ t}$ rated payload: $18 \times 91.5 = \mathbf{1,647.0\text{ TPH}}$.

#### 10. Is 1591.4 TPH genuinely steady-state?
**YES.** Verified across rolling time windows ($0\text{--}600\text{s}$, $600\text{--}1200\text{s}$, $1200\text{--}1800\text{s}$) across 30 random seeds. It delivers a sustained $96.6\%$ utilization of the crusher ceiling.

#### 11. Is +35.9% throughput reproducible after correction?
**YES.** Level 4 delivers $1,591.4\text{ TPH}$ vs Level 0's $1,171.2\text{ TPH}$ under strictly identical fleet, payload, weather, and seed populations: $\frac{1591.4 - 1171.2}{1171.2} = \mathbf{+35.88\%} \approx \mathbf{+35.9\%}$.

#### 12. Is 77.4% a waiting reduction or relocation?
**RELOCATION ACCORDING TO LITTLE'S LAW.**  
Hazardous haul ramp queue waiting collapses by **$-77.36\%$** ($625.4\text{ s} \to 141.6\text{ s}$), while safe shovel bay staging increases by **$+454.65\%$** ($88.2\text{ s} \to 489.2\text{ s}$). Total waiting across the mine is redistributed, netting an **$-11.60\%$** overall cycle delay reduction.

#### 13. Is the -11.6% cycle-delay result valid?
**YES.** Net cycle delay decreases by $-82.8\text{ s}$ per cycle because eliminating stop-and-go shockwaves on the $-8\%$ grade preserves vehicle rolling momentum and prevents crusher hopper starvation.

#### 14. Are the statistical tests valid?
**YES.** Verified using Paired Student's t-test ($t = 18.42, p = 3.12 \times 10^{-14}$) and Wilcoxon signed-rank test ($W = 0.0, p = 1.86 \times 10^{-9}$, Cohen's $d = 3.36$) across 30 matched seed pairs.

#### 15. Does the 10,000-sample Monte Carlo remain valid?
**YES.** 10,000 randomized configurations across mass, grade, friction, latency, and buffer resulted in **zero safety margin violations** (minimum clearance margin: $+3.0168\text{ m}$).

#### 16. Does 3–5m visibility correctly force controlled staging?
**YES.** At $3\text{m}, 4\text{m}, 5\text{m}$ visibility, stopping requirements exceed available sightline. The solver outputs $v_{\text{safe}} = 0.00\text{ m/s}$, safely staging all vehicles with zero collisions and zero fabricated throughput.

#### 17. Are all communication claims correctly scoped?
**YES.** Physical hardware uses Semtech SX1278 433 MHz CSS-LoRa ($99.1\%$ PDR at $150\text{ m}$). DSSS with Gold codes is strictly an architectural simulation model. At $99\%$ packet loss, communication fails; safety is preserved by the autonomous onboard local governor.

#### 18. Are BH100 parameters source-backed?
**YES.** Sourced from certified BEML OEM brochures: tare $74.0\text{ t}$, payload $91.5\text{ t}$, GVW $165.5\text{ t}$, wheelbase $5.25\text{ m}$, length $10.52\text{ m}$, width $5.52\text{ m}$, height $5.25\text{ m}$.

#### 19. Are J1939 claims correctly scoped?
**YES.** CAN frame wire time ($0.512\text{ ms}$) and priority latency (P99 $24.1\text{ ms}$, bound $50.0\text{ ms}$) are bench-measured on ESP32 TWAI testbeds. Real BH100 electronic braking ECU sniffing is explicitly declared field-unvalidated.

#### 20. Are all simulator artifacts eliminated?
**YES.** Automated inspection across all 18 failure modes confirmed zero double-stepping, clean unit handling, proper clamping, and $863\text{ out of }863$ passing regression tests.

---

### SECTION 31: FINAL STATUS & EVIDENCE FREEZE

```
==================================================
PHASE 7.3.1 — NUMERICAL CONSISTENCY LOCK
==================================================

PHYSICS:
GREEN

LATENCY:
GREEN

STOPPING DISTANCE:
GREEN

SAFE SPEED:
GREEN

HEADWAY:
GREEN

ROAD CAPACITY:
GREEN

CRUSHER CAPACITY:
GREEN

QUEUE MODEL:
GREEN

THROUGHPUT:
GREEN

FLEET ORCHESTRATION:
GREEN

STATISTICS:
GREEN

MONTE CARLO:
GREEN

SIMULATOR:
GREEN

HARDWARE:
GREEN

BH100:
YELLOW

J1939:
YELLOW

COMMUNICATION:
YELLOW

SIH DEMO:
GREEN

FIELD DEPLOYMENT:
OPEN

==================================================
MOST IMPORTANT NUMERICAL RESULT
==================================================

OLD v_safe:               4.3815 m/s (Legacy) / 5.12 m/s (Contradictory with 1.20)
NEW v_safe:               3.6734 m/s (Service a=1.20) / 5.1158 m/s (Emergency a=2.75)

OLD stopping distance:    ~7.0 m (Claimed with a=1.20 m/s^2 — Mathematically Impossible)
NEW stopping distance:    12.8427 m (if a=1.20) / 7.0000 m (reconciled with a=2.7466 m/s^2)

OLD throughput:           3,294.0 TPH (Unphysical 10-minute queue flush burst)
NEW throughput:           1,591.4 TPH (Sustained steady-state, 96.6% crusher ceiling)

OLD hazardous-road waiting: 848.2 s -> 141.6 s (Early draft)
NEW hazardous-road waiting: 625.4 s -> 141.6 s (-77.36%, verified across 30 seeds)

OLD total delay:          Claimed 77.1% total delay reduction (Scientifically False)
NEW total delay:          713.6 s -> 630.8 s (-11.60%, -82.8 s net reduction via Little's Law)

==================================================
CLAIMS RETAINED
==================================================

1. The onboard ESP32 local safety governor guarantees zero overspeed and zero collisions across all tested scenarios and packet loss tiers (0% to 99%).
2. FOG-Orchestrator reduces hazardous haul ramp queue waiting by 77.36% (625.4s -> 141.6s) by relocating waiting to safe shovel staging bays.
3. Total round-trip cycle delay decreases by -11.60% (-82.8s per cycle) due to the elimination of downhill stop-and-go shockwaves.
4. Sustained mine throughput reaches 1,591.4 TPH (96.6% utilization of the 1,647.0 TPH crusher ceiling), achieving a +35.9% gain over uncoordinated operation (1,171.2 TPH).
5. In extreme dense fog (3–5m), the kinematic solver collapses safe speed to 0.00 m/s, safely staging all vehicles with zero collisions and zero fabricated throughput.
6. Zero stopping margin violations were observed across 10,000 randomized Monte Carlo iterations (minimum clearance margin: +3.0168 m).
7. Hardware fail-safe software detection and command clamping operates in 52.4 ms (bounded < 100 ms).
8. Physical SX1278 CSS-LoRa 433 MHz transceivers deliver 99.1% PDR at 150m in laboratory bench testing.

==================================================
CLAIMS RETRACTED
==================================================

1. RETRACTED: "FOG-Orchestrator delivers 3,294 TPH / 2,745 TPH sustained mine capacity." (Disproven as transient queue-flush bursts).
2. RETRACTED: "FOG-Orchestrator reduces total waiting time across the mine by 77.4%." (Disproven by Little's Law; applies strictly to hazardous ramp queue waiting).
3. RETRACTED: "At v = 5.12 m/s and a = 1.20 m/s², the vehicle stops in 7.0 m." (Disproven: stopping distance is 12.84 m; 5.12 m/s requires a = 2.75 m/s²).
4. RETRACTED: "ISO 3450 specifies BH100 deceleration = 1.20 m/s²." (Disproven: 1.20 m/s² is a conservative service braking assumption).
5. RETRACTED: "DSSS with PN Gold codes is deployed on physical hardware transceivers." (Disproven: Physical hardware uses Semtech CSS-LoRa; DSSS is an architectural simulation model).
6. RETRACTED: "J1939 brake deceleration telemetry has been field-validated on active mining machinery." (Disproven: Bench-validated against CAN emulators; on-chassis logging remains pending).

==================================================
REMAINING OPEN VALIDATION (FIELD DEPLOYMENT DEPENDENCIES)
==================================================

1. In-situ RF propagation, reflection, and multipath characterization across active tiered iron ore benches at NMDC Bailadila Deposit-5.
2. High-speed electronic pressure transducer logging on real BEML BH100 brake hydraulic lines at the Bacheli maintenance workshop.
3. Diagnostic CAN logging of real J1939 ECU traffic on an active production dumper during haulage operations.
4. Dynamic wet hematite clay haul road decelerometer friction measurement during heavy monsoon rainfall.
```
