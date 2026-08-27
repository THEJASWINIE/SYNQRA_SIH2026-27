# DEMO V0.1 — MINIMUM WORKING VERTICAL SLICE VALIDATION REPORT

## 1. Objective & Scope
The purpose of Demo V0.1 is to demonstrate and validate the fundamental physical-to-operational causal chain of the **FOG-ORCHESTRATOR 2.0 Task 2 Digital Twin**.
This is the **first validated vertical slice** representing the core numerical dynamics. It is **not** the complete Task-2 system.

Scope boundary:
*   **Tier 1 Physics Safety Governor**: Fully implemented (force balance, reaction stopping distance, retarder and curve speed constraints).
*   **Tier 2 Switchback Slot Reservations**: Stub interface provided for scheduling expansion.
*   **Tier 3 Fleet Layer**: Simulated via arrival shaping and dispatch releases.
*   **HMI / Hardware Telemetry**: State schema contracts fully documented.
*   **Network Layout**: Synthetic road graph: Shovel $\rightarrow$ Road 1 $\rightarrow$ Intersection $\rightarrow$ Road 2 $\rightarrow$ Crusher $\rightarrow$ Road Return $\rightarrow$ Shovel.

---

## 2. Parameter & Result Classification Register

Every parameter and metric is labeled according to the Task-2 build specifications:

### 2.1 Inputs & Initializations
*   **BEML BH100 tare weight ($74\text{ t}$), payload ($91\text{ t}$), gross ($165\text{ t}$), dimensions ($10.52\text{ m} \times 5.52\text{ m}$)**: `[REFERENCE]`
*   **Shovel service rate ($15\text{ vph}$), Crusher service rate ($18\text{ vph}$)**: `[SIMULATION BASELINE]` (not NMDC mine facts)
*   **Safety margin ($5.0\text{ m}$), minimum headway ($15.5\text{ m}$), hydraulic latency ($\tau = 0.25\text{ s}$)**: `[MODEL CONFIG]`
*   **Air density ($1.225\text{ kg/m}^3$), drag coefficient ($C_D = 0.8$), cross-section ($A = 30.0\text{ m}^2$)**: `[ASSUMPTION]`
*   **Visibility levels ($50/15/5\text{ m}$), slopes ($0\%$, $-8\%$, $+4\%$)**: `[SIMULATION SCENARIO]`
*   **Site-specific friction logs, site visibility distributions, packet drop rates**: `[UNKNOWN]` (must be measured in Task 3)

### 2.2 Generated Outputs
*   **All CSV logs, JSON files, plotted graphs, tonnes hauled, and queue sizes**: `[SIMULATION RESULT]`

---

## 3. Implemented Mathematical Model

### 3.1 Longitudinal Force Balance
$$m \frac{dv}{dt} = F_{\rm drive} - F_{\rm roll} - F_{\rm aero} - F_{\rm retarder} - F_{\rm brake} - m g \sin(\theta)$$
*   Rolling Resistance: $F_{\rm roll} = C_{\rm rr} m g \cos(\theta)$
*   Aero Drag: $F_{\rm aero} = 0.5 \rho C_D A v^2$ (neglected conservatively for stopping distance calculations)
*   Emergency Deceleration ceiling: $a_{\rm dec} = \frac{\min(F_{\rm hardware\_max}, \mu m g \cos(\theta)) + F_{\rm roll}}{m} + g \sin(\theta)$

### 3.2 Safety Governor Quadratic Speed Limit
Solving $v \tau + \frac{v^2}{2 a_{\rm dec}} + S_{\rm margin} \le Visibility$:
$$v_{\rm stop} = a_{\rm dec} \left( -\tau + \sqrt{\tau^2 + \frac{2}{a_{\rm dec}}(Visibility - S_{\rm margin})} \right)$$

### 3.3 Downhill Retarder Speed Limit
For downhill slope ($\theta < 0$), retarder force must prevent continuous speed accumulation:
$$v_{\rm retarder} = \frac{P_{\rm ret\_max}}{-m g \sin(\theta) - F_{\rm roll}}$$

---

## 4. Scenario Replay & Causal Chain Verification

### 4.1 Causal Chain Trace (DEMO_06 Full Vertical Slice)
The simulation successfully demonstrated the entire cause-and-effect chain:
1.  **Clear Baseline (t = 100s)**: Visibility is $50.0\text{ m}$. Safe speed on Road 2 is $11.11\text{ m/s}$ ($40.00\text{ km/h}$). Crusher queue is $0$ trucks.
2.  **Fog Onset (t = 500s)**: Visibility drops to $15.0\text{ m}$, friction drops to $0.25$. Safe speed on Road 2 decreases to $5.40\text{ m/s}$ ($19.45\text{ km/h}$). Road capacity drops from $1369.34\text{ vph}$ to $407.21\text{ vph}$. Arrival rate exceeds capacity, Crusher queue grows to $2$ trucks.
3.  **Arrival Shaping Active (t = 1100s)**: Downstream Crusher queue is $2$ trucks. Shovel release delay throttles from $240\text{ s}$ to $600.0\text{ s}$ (equivalent to $6.0\text{ vph}$ output). Crusher queue stabilizes at $1$ truck.
4.  **Fog Recovery (t = 1700s)**: Visibility recovers to $43.0\text{ m}$, friction to $0.53$. Safe speed on Road 2 recovers to $9.92\text{ m/s}$ ($35.72\text{ km/h}$). Crusher queue dissipates back to $0$.

---

## 5. Comparison: With vs Without Arrival Shaping (DEMO_05)
Under a constrained Crusher rate of $10.0\text{ vph}$:
*   **Without Arrival Shaping**: Arrivals continue at the loaded rate ($15.0\text{ vph}$). The Crusher queue grows continuously, reaching a peak of **3 trucks**, flooding the system.
*   **With Arrival Shaping**: The Tier-3 controller throttles departures at the Shovel to match the Crusher's service capacity. The Crusher queue is stabilized, peaking at only **1 truck**.

---

## 6. Verification Checklist Results

| Test ID | Verification Target | Check Type | Pass/Fail | Evidence / Output |
| :--- | :--- | :--- | :--- | :--- |
| **TEST 01** | Graph Connectivity | Boundary | **PASS** | Synthetic network parsed successfully with nodes and edges. |
| **TEST 02** | Vehicle Parameter Validity | Sign / Value | **PASS** | BEML BH100 parameters successfully instantiated empty and loaded. |
| **TEST 03** | Safe Speed Calculation | Equations | **PASS** | Validates quadratic stopping and retarder bounds. |
| **TEST 04** | Stopping Distance Validity | Dimensions | **PASS** | Checked stopping distance values against analytical bounds. |
| **TEST 05** | Visibility Monotonicity | Monotonicity | **PASS** | Verified: safe speed is non-decreasing with increasing visibility. |
| **TEST 06** | Grade Monotonicity | Monotonicity | **PASS** | Verified: safe speed is non-increasing with increasing downhill grade. |
| **TEST 07** | Friction Monotonicity | Monotonicity | **PASS** | Verified: safe speed is non-decreasing with increasing friction. |
| **TEST 08** | Latency Monotonicity | Monotonicity | **PASS** | Verified: stopping distance is non-decreasing with increasing latency. |
| **TEST 09** | Headway Validity | Boundary | **PASS** | Spacing never drops below static headway of $15.5\text{ m}$. |
| **TEST 10** | Capacity Calculation | Dimensions | **PASS** | Calculated capacity $C_r$ scales correctly with visibility and speed. |
| **TEST 11** | Queue Conservation | Mass Balance | **PASS** | Trucks in system conserved: $Q(t+dt) = Q(t) + A(t) - D(t)$. |
| **TEST 12** | Queue Growth (Arrival > Service) | Monotonicity | **PASS** | Verified queue growth when Shovel rate exceeds Crusher capacity. |
| **TEST 13** | Queue Recovery | Boundary | **PASS** | Crusher queue returns to stable state upon clearance. |
| **TEST 14** | Crusher Bottleneck Score | Monotonicity | **PASS** | Node utilization $\rho > 1.0$ triggers higher bottleneck score. |
| **TEST 15** | Arrival Shaping Control | Stability | **PASS** | Successfully throttled releases at shovel to stabilize Crusher queue. |
| **TEST 16** | Weather Event Propagation | Continuity | **PASS** | Fog visibility and friction transition smoothly over time. |
| **TEST 17** | Safety Constraint Enforcement | Safety Governor | **PASS** | Safety override verified: $v_{\rm command} \le v_{\rm safe}$ at every step. |

---

## 7. Next Development Steps (Roadmap to Full Task 2)
1.  **Switchback Slot Coordinator**: Implement Tier-2 scheduling algorithms (non-overlapping reservation slots).
2.  **Receding-Horizon Optimizer (MPC)**: Expand deterministic MILP routing and chance-constrained optimization.
3.  **Communication Loss Simulation**: Model LoRa latency profiles and telemetry packet drops.
4.  **Task 1 Integration**: Setup FastAPI websockets for the HMI dashboard.
5.  **Task 3 Hardware Ingestion**: Adapt ESP32 telemetry packet parser.
