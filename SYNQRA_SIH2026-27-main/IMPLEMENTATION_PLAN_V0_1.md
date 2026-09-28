# IMPLEMENTATION_PLAN_V0_1 (CORRECTED)

## 1. Introduction & Scope Statement
This implementation plan defines the layout and math for **Demo V0.1 — Minimum Working Vertical Slice**. 
This is the **first validated vertical slice** of the FOG-ORCHESTRATOR 2.0 Task 2 Digital Twin. It does **NOT** complete Task 2. It demonstrates the fundamental physics-to-queue causal loop, leaving advanced scheduling, real telemetry hooks, and full MPC optimizers for subsequent iterations.

---

## 2. Parameter Evidence Classification

Every numerical parameter in this simulation is explicitly categorized to prevent the misrepresentation of simulation baselines as verified field data:

*   **REFERENCE**: Representative OEM specifications for mining dumpers (BEML BH100-class).
    *   Tare mass: $74,000$ kg (~74 t)
    *   Payload capacity: $91,000$ kg (~91 t)
    *   Gross mass: $165,000$ kg (~165 t)
    *   Vehicle length: $10.52$ m
    *   Vehicle width: $5.52$ m
*   **SIMULATION BASELINE**: Representative baseline values chosen for testing; not measured mine values.
    *   Crusher service capacity: $18$ vehicles/hour (vph)
    *   Shovel service capacity: $15$ vehicles/hour (vph)
*   **MODEL CONFIG**: Chosen tuning or structural parameters for the physics engine and safety margins.
    *   Safety stop margin ($S_{\text{margin}}$): $5.0$ m
    *   Safety headway margin ($S_{\text{margin\_headway}}$): $5.0$ m
    *   ECU/Hydraulic braking latency ($\tau_{\text{total}}$): $0.25$ s
    *   Minimum static headway ($H_{\text{min\_static}}$): $15.5$ m (vehicle length + $5.0$ m margin)
*   **SIMULATION SCENARIO**: Parameters varied dynamically across scenarios to test environmental stress.
    *   Visibility range ($V$): Clear baseline ($50$ m), Moderate ($30$ m), Dense Fog ($15$ m), Extreme ($5$ m).
    *   Friction ($\mu$): $0.15$ (very wet/muddy) to $0.65$ (dry).
    *   Road grade ($\theta$): $0\%$ (flat), $4\%$ (modest), $6.25\%$, $8\%$, and $10\%$ (steep).
    *   Fleet size ($N$): $2$ to $5$ trucks (for Demo V0.1).
*   **ASSUMPTION**: Temporary assumptions made to proceed in the absence of telemetry.
    *   Rolling resistance coefficient ($C_{\text{rr}}$): $0.02$ (dry) to $0.04$ (saturated).
    *   Air density ($\rho$): $1.225$ kg/m³
    *   BH100 drag coefficient ($C_D$): $0.8$
    *   BH100 cross-sectional area ($A$): $30.0$ m²
*   **UNKNOWN**: Direct field telemetry that is publicly unavailable and must be measured in Task 3.
    *   *Real-world road-specific friction logs, site-specific visibility maps, exact communication packet-loss profiles.*

---

## 3. Project Architecture & Modular Structure

We preserve a strict modular separation of concerns.

```
digitalTwin_FOG/
│
├── config/
│   ├── vehicle.yaml        # REFERENCE / MODEL CONFIG vehicle parameters
│   ├── roads.yaml          # SIMULATION SCENARIO road parameters
│   ├── nodes.yaml          # SIMULATION BASELINE node parameters
│   ├── weather.yaml        # SIMULATION SCENARIO environment parameters
│   └── scenarios.yaml      # Simulation loop configuration (seeds, timesteps)
│
├── models/
│   ├── vehicle.py          # State representation and load-handling
│   ├── vehicle_physics.py  # Force-balance governor, safe-speed math
│   ├── braking.py          # Stopping-distance math
│   ├── road_capacity.py    # Capacity Cr math
│   ├── queue_model.py      # Discrete-time queue logic
│   └── bottleneck.py       # Bottleneck score calculation
│
├── weather/
│   └── fog_model.py        # Environmental updates
│
├── twin/
│   ├── network.py          # Custom graph structures
│   ├── state.py            # HMI-facing serialization
│   └── simulator.py        # Core loop and safety constraint enforcement
│
├── control/
│   └── arrival_shaping.py  # Shovel dispatch controller
│
├── interfaces/
│   └── task2_state_schema.py # APIs for HMI/Task 3
│
├── scenarios/
│   └── demo_v01.py         # 6 scenario implementations
│
├── tests/                  # Unified verification framework
│   ├── test_physics.py
│   ├── test_capacity.py
│   ├── test_queue.py
│   ├── test_bottleneck.py
│   └── test_demo.py
│
├── results/                # CSV and JSON logs
├── plots/                  # Generated PNG figures
│
├── main.py                 # Simulation runner CLI
├── requirements.txt        # Package configuration
├── README.md               # User guide
└── DEMO_V0_1_REPORT.md     # Final validation document
```

### Extensible Parameter Sweeps
Configurations will support single runs for Demo V0.1 but are designed to handle full-scale parameter sweeps in the future. YAML configurations will explicitly list ranges for visibility ($50/30/20/15/10/5$ m), grades ($0/4/6.25/8/10\%$), friction ($0.15$ to $0.65$), and fleet sizes up to the $50$-vehicle benchmark.

---

## 4. Fundamental Physics Equations (Intact)

We do not simplify the physics. The governor uses the exact longitudinal model:

### 4.1 Force Balance
$$m \frac{dv}{dt} = F_{\text{drive}} + m g \sin(\theta) - F_{\text{roll}} - F_{\text{aero}} - F_{\text{retarder}} - F_{\text{brake}}$$
*   Uphill/downhill grade angle: $\theta$ (radians). Uphill: $\theta > 0$, Downhill: $\theta < 0$.
*   Rolling resistance: $F_{\text{roll}} = C_{\text{rr}} m g \cos(\theta)$
*   Aero drag: $F_{\text{aero}} = 0.5 \rho C_D A v^2$ (used in simulation force updates; neglected conservatively in stopping calculations).
*   Maximum braking force (friction limited): $F_{\text{brake\_max}} = \mu m g \cos(\theta)$.
*   Emergency stopping force: $F_{\text{brake}} = \min(F_{\text{hardware\_max\_brake}}, F_{\text{brake\_max}})$.

### 4.2 Deceleration under Emergency Braking (Conservative)
$$a_{\text{dec}} = \frac{F_{\text{brake}} + F_{\text{roll}}}{m} - g \sin(\theta)$$
*   If $a_{\text{dec}} \le 0$, the truck cannot decelerate (unsafe slope/friction). The governor halts the truck ($v_{\text{safe}} = 0$).

### 4.3 Safe Stopping Speed ($v_{\text{stop}}$)
Solving $S_{\text{stop}} + S_{\text{margin}} \le V$:
$$v \cdot \tau_{\text{total}} + \frac{v^2}{2 a_{\text{dec}}} + S_{\text{margin}} \le V$$
$$v_{\text{stop}} = a_{\text{dec}} \left( -\tau_{\text{total}} + \sqrt{\tau_{\text{total}}^2 + \frac{2}{a_{\text{dec}}} (V - S_{\text{margin}})} \right) \quad \text{if } V > S_{\text{margin}} \text{ else } 0.0$$

### 4.4 Downhill Retarder Speed ($v_{\text{retarder}}$)
To prevent runaway speed downhill ($\theta < 0$), retarder force must counter gravity:
$$F_{\text{ret\_required}} = -m g \sin(\theta) - F_{\text{roll}}$$
If $F_{\text{ret\_required}} > 0$:
$$v_{\text{retarder}} = \frac{P_{\text{ret\_max}}}{F_{\text{ret\_required}}}$$
Else, $v_{\text{retarder}} = \infty$.

### 4.5 Safety Override Principle
The vehicle controller calculates the final commanded speed:
$$v_{\text{command}} = \min(v_{\text{dispatch}}, v_{\text{safe}})$$
where $v_{\text{safe}} = \min(v_{\text{stop}}, v_{\text{retarder}}, v_{\text{traction}}, v_{\text{curve}}, v_{\text{mine}})$.
This is enforced at **every single simulation timestep** in the simulator loop, ensuring the optimizer can never command an unsafe speed.

---

## 5. Switchback Slot Interfaces
In Demo V0.1, we do not implement active slot-based scheduling algorithms inside `arrival_shaping.py`. We follow the strict implementation order. However, we define a modular class stub in a new file `models/switchback.py`:
```python
class SwitchbackCoordinator:
    """
    Interface stub for Tier 2 switchback/intersection slot reservation.
    To be expanded in Task-2 full system with scheduling algorithms.
    """
    def __init__(self):
        self.reservations = {}  # {node_id: [(t_start, t_end, vehicle_id)]}

    def request_slot(self, node_id: str, t_start: float, t_end: float, vehicle_id: str) -> bool:
        # For V0.1, simply returns True to permit travel, acting as a pass-through
        return True
```

---

## 6. Verification and Validation Checks
`tests/test_physics.py` is configured with strict assertions for:
1.  **Dimensional Analysis**: Checks that forces, accelerations, and speeds are dimensionally consistent.
2.  **Sign Checks**: Confirms gravity is positive uphill, negative downhill; rolling resistance and braking always oppose motion.
3.  **Boundary Conditions**: Checks extreme limits (e.g. $V \le S_{\text{margin}}$ yields $v_{\text{safe}} = 0$; $\mu = 0$ yields $v_{\text{safe}} = 0$).
4.  **Monotonicity**:
    *   Grade monotonicity: increasing downhill steepness decreases $v_{\text{safe}}$.
    *   Friction monotonicity: decreasing friction decreases $v_{\text{safe}}$.
    *   Visibility monotonicity: decreasing visibility decreases $v_{\text{safe}}$.
    *   Latency monotonicity: increasing latency decreases $v_{\text{safe}}$ / increases $S_{\text{stop}}$.

---

## 7. Roadmap of Remaining Task-2 Requirements
Upon completion of Demo V0.1, the following requirements remain for the full Task-2 digital twin:
*   Deterministic receding-horizon optimizer (MILP / dispatch).
*   Robust/Scenario MPC and Chance-Constrained RH-MPC optimizer.
*   Probabilistic constraint checks (e.g. $P(v \le v_{\text{safe}}) \ge 0.99$).
*   Switchback slot scheduling algorithms (Tier-2 reservation coordination).
*   LoRa communication delay, packet loss, and stale telemetry emulators.
*   Monte Carlo uncertainty sweeps ($1,000+$ run validation).
*   Integration testing with Task-1 HMI Web Sockets.
*   Integration testing with Task-3 hardware-in-the-loop telemetry input.

---

## 8. Dependencies & Environment
*   **Python version**: 3.13.5
*   **Minimum Dependencies**:
    *   `pyyaml>=6.0`: For parsing configuration documents.
    *   `numpy>=2.0.0`: For numerical array handling and calculations.
    *   `matplotlib>=3.9.0`: For generating output validation charts.
