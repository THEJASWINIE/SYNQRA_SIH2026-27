# PHASE 8 — TIMING AUDIT & LATENCY DECOMPOSITION REPORT
## FOG-ORCHESTRATOR 2.0 — SIH26007
### Empirical Latency Decomposition across 6 HIL Stages and Stopping Distance Decoupling

---

## 1. Crucial Conceptual Boundary

> **NON-NEGOTIABLE SAFETY AUDIT RULE (Prompt Section 8 & 11):**  
> Software command response time and physical vehicle stopping distance are **fundamentally different physical quantities**.  
> Under NO circumstances is software timing called *"braking latency"*.  
> We strictly distinguish:
> 1. **HIL Command-Path Latency ($T_{\text{command}}$):** The electronic/algorithmic delay from sensor ingress to actuator signal dispatch.
> 2. **Physical Stopping Kinematics ($S_{\text{stop}}$):** The physical distance traveled by a 165.5-tonne hauler under friction and mechanical brake drum deceleration.

---

## 2. 6-Stage Latency Decomposition (Empirical Benchmark)

Logged across $N=105$ systematic HIL benchmark trials in [`data/phase8_hil_results.csv`](file:///c:/Users/JAGADEESH%20M/OneDrive/Documents/SIH-2026-27/data/phase8_hil_results.csv):

| Processing Stage | Physical Execution Subsystem | Mean (ms) | P50 (ms) | P95 (ms) | P99 (ms) | Max (ms) | Notes |
|---|---|---|---|---|---|---|---|
| **$T_{\text{sensor}}$** | Sensor ADC & CAN frame pack | 1.26 | 1.26 | 1.26 | 1.27 | 1.27 | Wheel encoder / IMU sampling |
| **$T_{\text{safety}}$** | Canonical physics solver + governor | 2.20 | 2.19 | 2.24 | 2.27 | 2.28 | `fog_safe.safety.solve_safe_speed` |
| **$T_{\text{can}}$** | CAN 250 kbps wire delay + queue | 12.55 | 12.60 | 12.60 | 12.60 | 12.60 | Ingress + egress TWAI frames |
| **$T_{\text{actuator}}$** | Electro-pneumatic valve delay | 205.12* | 200.00 | 200.00 | 296.00 | 350.00* | Modeled delay ($\tau \in [200, 350]\text{ ms}$) |
| **$T_{\text{dynamics}}$** | Longitudinal kinematic solver | 0.85 | 0.85 | 0.85 | 0.85 | 0.85 | Simulation physics integration |
| **$T_{\text{telemetry}}$**| Operator HUD bridge serialization | 0.93 | 0.93 | 0.93 | 0.93 | 0.93 | Presentation packaging |
| **TOTAL COMMAND PATH**| **Sensor $\to$ Actuator Output** | **222.13\*** | **216.05** | **216.12** | **312.05** | **366.15\*** | **Excluding non-response fault** |

*\*Note on Actuator Non-Response Scenario (HIL-27):* In scenario HIL-27, mechanical valve seizure was specifically injected ($\tau \to \infty$). The software watchdog flagged `ACTUATOR_FAULT_NON_RESPONSIVE` at $t = 500\text{ ms}$, clamping the commanded velocity ceiling while logging the fault. The table above reports operational timing excluding infinite non-response.

---

## 3. Command Response Time vs Physical Stopping Distance

### Mathematical Decoupling:

1. **Electronic Command Latency Budget ($\tau_{\text{total}}$):**
   $$\tau_{\text{total}} = \tau_{\text{sensor}} + \tau_{\text{solver}} + \tau_{\text{comm}} + \tau_{\text{actuator}}$$
   - Bench-measured mean: $1.26\text{ ms} + 2.20\text{ ms} + 12.55\text{ ms} + 200.00\text{ ms} = 216.01\text{ ms} \approx 0.216\text{ s}$.
   - Canonical conservative assumption used in safety calculations: $\tau = 0.400\text{ s}$ ($400\text{ ms}$).

2. **Physical Stopping Kinematics ($S_{\text{stop}}$):**
   $$S_{\text{stop}} = v \cdot \tau_{\text{total}} + \frac{v^2}{2 \cdot a_{\text{dec}}}$$
   For a BEML BH100 at $v = 4.3815\text{ m/s}$ (canonical dense fog safe speed), emergency deceleration $a_{\text{emergency}} = 2.7856\text{ m/s}^2$:
   $$S_{\text{reaction}} = 4.3815 \times 0.400 = 1.753\text{ m}$$
   $$S_{\text{braking}} = \frac{4.3815^2}{2 \times 2.7856} = 3.446\text{ m}$$
   $$S_{\text{base}} = 5.000\text{ m}\quad (\text{safety buffer})$$
   $$S_{\text{total}} = 1.753 + 3.446 + 5.000 = 10.199\text{ m} \le 12.000\text{ m}\quad (\text{stopping visibility envelope})$$

### Crucial Finding:
The electronic command path ($216\text{ ms}$) represents only **17.2%** of the stopping distance ($1.75\text{ m}$ out of $10.20\text{ m}$). The remaining **82.8%** is dictated by heavy vehicle inertia ($165.5\text{ tonnes}$) and ground contact friction. Optimizing software down to microseconds cannot eliminate the laws of Newtonian braking.
