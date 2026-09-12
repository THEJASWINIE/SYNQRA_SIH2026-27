# FOG-ORCHESTRATOR 2.0 — Task 2: Digital Twin Engine

Predictive operational digital twin connecting mine-road conditions, vehicle physics, spatio-temporal fog fields, dynamic road capacity, queue dynamics, bottleneck migration, and chance-constrained fleet dispatch.

---

## 1. Project Purpose

FOG-ORCHESTRATOR 2.0 addresses the **Safe and Efficient Operation of Mine Haul Vehicles in Fog and Low-Visibility Conditions in Open-Cast Iron Ore Mines** (Ministry of Steel / NMDC Reference Contexts: Kirandul, Bacheli, Donimalai).

During winter and monsoon months, heavy valley and advection fog severely degrades optical line-of-sight visibility (dropping below $15\,\text{m}$), while precipitation reduces tire-road surface friction ($\mu \le 0.35$). Conventional mining fleets either halt operations entirely (causing massive production losses) or operate blindly at high collision risk.

FOG-ORCHESTRATOR 2.0 solves this by coupling:
- **Tier-1 Local Safety Governors**: Inviolable physical braking and headway envelope enforcement guaranteeing $v_{\text{command}} = \min(v_{\text{dispatch}}, v_{\text{safe}})$.
- **Tier-2 Infrastructure Coordination**: Mutual exclusion slot reservations for single-lane hairpin switchbacks and blind intersections.
- **Tier-3 Predictive Dispatch**: Receding-horizon chance-constrained model predictive control (RH-MPC) shaping vehicle arrival rates to prevent downstream queue overflow and bottleneck congestion.

---

## 2. System Architecture

```
+-----------------------------------------------------------------------------------+
|               TIER 3: CENTRAL / CLOUD OPTIMIZATION & FLEET DISPATCH               |
|  - Receding-Horizon Chance-Constrained MPC (optimizer/chance_mpc.py)              |
|  - Dynamic Bottleneck Ranking & Migration Tracking (models/bottleneck.py)         |
|  - Arrival-Rate Shaping & Finite Buffer Management (models/queue_model.py)        |
+-----------------------------------------------------------------------------------+
                                         │
                   Dispatch Targets (v_dispatch, route)
                                         ▼
+-----------------------------------------------------------------------------------+
|             TIER 2: INFRASTRUCTURE COORDINATION & RESERVATIONS                   |
|  - Switchback Single-Lane Slot Coordinator (models/switchback.py)                 |
|  - Intersection Conflict Exclusion                                                |
|  - Spatio-Temporal Fog & Friction Field (weather/fog_model.py)                    |
+-----------------------------------------------------------------------------------+
                                         │
                   Reservation Approvals & Environmental State
                                         ▼
+-----------------------------------------------------------------------------------+
|               TIER 1: ONBOARD VEHICLE SAFETY & LOCAL GOVERNOR                     |
|  - Longitudinal Grade Physics & Retarder Energy Balance (models/braking.py)       |
|  - Conservative Stopping Distance & Headway (models/braking.py)                   |
|  - INVIOLABLE GOVERNOR: v_command = min(v_dispatch, v_safe)                       |
+-----------------------------------------------------------------------------------+
```

---

## 3. Folder Structure

```
FOG_ORCHESTRATOR_Task2/
├── config/                  # Immutable system configuration & parameters (YAML)
│   ├── vehicle.yaml         # BH100-class 165.5t dumper mass, geometry, retarder specs
│   ├── roads.yaml           # Haul-road segments (grade, length, width, speed limits)
│   ├── nodes.yaml           # Shovels, crushers, dump points, switchbacks, buffers
│   ├── weather.yaml         # Visibility levels, wetness-friction couplings, forecast noise
│   └── scenarios.yaml       # Master benchmark scenario matrix (S01 through S20)
│
├── models/                  # Microscopic physics, capacity, queue, and conflict models
│   ├── vehicle.py           # Vehicle entity and kinematic state vector
│   ├── vehicle_physics.py   # Longitudinal force balance on road grade
│   ├── braking.py           # Stopping distance, perception delay, safe-speed solver
│   ├── retarder.py          # Continuous downhill retarder thermal power balance
│   ├── friction.py          # Tire-road friction estimation & conservative bounds
│   ├── road_capacity.py     # Micro-to-macro dynamic capacity C_r & safe headway
│   ├── queue_model.py       # Discrete-time queue mass conservation & buffer limits
│   ├── bottleneck.py        # Composite bottleneck score & migration detection
│   └── switchback.py        # Tier-2 non-overlapping slot reservation coordinator
│
├── weather/                 # Weather field simulation & predictive nowcasting
│   ├── fog_model.py         # Spatio-temporal visibility field V(s, t)
│   ├── forecast_model.py    # Receding-horizon predictive visibility nowcasting
│   └── uncertainty.py       # Stochastic noise, bias, and forecast error injection
│
├── optimizer/               # Fleet dispatch and arrival-rate shaping algorithms
│   ├── baseline_dispatch.py # Heuristic, fixed-speed, vehicle-only, fleet-only
│   ├── milp_dispatch.py     # Deterministic receding-horizon MILP
│   ├── robust_mpc.py        # Bounded worst-case scenario MPC
│   └── chance_mpc.py        # Chance-constrained RH-MPC (Primary Algorithm)
│
├── twin/                    # Master digital twin state and simulation loop
│   ├── state.py             # Centralized synchronized TwinState dataclasses
│   ├── network.py           # NetworkX topological mine haulage graph G=(V, E)
│   └── simulator.py         # Master discrete-time simulation orchestrator
│
├── interfaces/              # Hardware and Dashboard integration adapters
│   ├── task1_hmi.py         # REST/WebSocket publisher emitting 12-domain state schema
│   └── task3_vehicle_io.py  # Telemetry receiver and command emitter for Task 3
│
├── dashboard/               # Browser-based Digital Twin Visualization Command Center
│   ├── index.html           # Command center layout & SVG mine network viewer
│   ├── styles.css           # High-tech dark glassmorphism theme
│   └── app.js               # WebSocket stream client, telemetry charts, controls
│
├── validation/              # Verification & Validation test suites (108 unit tests)
│   ├── test_physics.py      # Tier-1 stopping distance, retarder, grade tests
│   ├── test_weather.py      # Visibility models, spatial fields, nowcasting
│   ├── test_optimizer.py    # Chance-constrained MPC, queue shaping, capacity
│   ├── scenario_tests.py    # S01-S20 scenario integration and HMI API tests
│   └── monte_carlo.py       # 1,000-run stochastic Monte Carlo validation engine
│
├── results/                 # Verified scenario execution results & summaries
│   ├── S01.json - S20.json  # Individual scenario KPI result records
│   ├── scenario_summary.json# Consolidated S01-S20 summary matrix
│   ├── monte_carlo_summary.json # 1,000-run Monte Carlo distribution moments
│   ├── monte_carlo_results.json # Detailed stochastic sample records
│   └── verification_report.md   # Comprehensive mathematical & engineering audit
│
├── main.py                  # Master CLI entrypoint
└── requirements.txt         # Python package dependencies
```

---

## 4. Installation

### Requirements
- Python 3.10, 3.11, 3.12, or 3.13
- Modern web browser (Chrome, Edge, Firefox, Safari)

### Setup
```powershell
# Clone or navigate to the repository directory
cd d:/FOG_ORCHESTRATOR_Task2

# Install required dependencies
pip install -r requirements.txt
```

---

## RUNNING THE DIGITAL TWIN

### 1. Start the FastAPI Backend & Live Dashboard Server
Launch the unified FastAPI application on port 8080 (serves REST API, WebSocket streams, and dashboard UI):
```powershell
python main.py --serve-hmi --port 8080
```
*(Or alternatively using uvicorn directly: `python -m uvicorn interfaces.task1_hmi:app --reload --port 8080`)*

### 2. Open the Digital Twin Dashboard
- **Unified Dashboard URL**: [http://127.0.0.1:8080/](http://127.0.0.1:8080/) (or `http://127.0.0.1:8080/dashboard`)
- **Interactive Swagger Docs**: [http://127.0.0.1:8080/docs](http://127.0.0.1:8080/docs)
- **OpenAPI Schema**: [http://127.0.0.1:8080/openapi.json](http://127.0.0.1:8080/openapi.json)
- **Health Check**: [http://127.0.0.1:8080/health](http://127.0.0.1:8080/health)

*(Optional: If running the frontend on a separate HTTP dev server: `python -m http.server 5500 --directory dashboard` and open `http://127.0.0.1:5500/`)*

### 3. Run Validation Test Suite
Execute the complete 108-test validation test suite:
```powershell
python -m unittest discover -s validation -p "*.py"
```

### 4. Execute Scenarios & Benchmarks
```powershell
# Run individual scenario (e.g. S01, S02, S05)
python main.py --scenario S01 --controller chance_mpc

# Run complete benchmark suite (S01 - S20)
python main.py --benchmark-all

# Run stochastic Monte Carlo uncertainty analysis (1,000 runs)
python main.py --monte-carlo --runs 1000
```

---

## 9. API Endpoints

### Task-1 HMI API (`interfaces/task1_hmi.py`)
| Method | Path | Description |
|---|---|---|
| `GET` | `/health` | Application health check (`{"status": "ok"}`) |
| `GET` | `/docs` | Interactive Swagger UI API documentation |
| `GET` | `/api/v1/state/snapshot` | Master 12-domain digital twin snapshot |
| `GET` | `/api/v1/state/time` | Current simulation time ($t$), step count, and active scenario |
| `GET` | `/api/v1/state/environment` | Visibility ($V$), friction ($\mu \pm \sigma$), weather mode, safety status |
| `GET` | `/api/v1/state/fleet` | Aggregate production and individual vehicle telemetry ($v, v_{\text{safe}}, v_{\text{cmd}}, \text{route}$) |
| `GET` | `/api/v1/state/roads` | Haul-road segments, grades, capacities, and bottleneck scores |
| `GET` | `/api/v1/state/queues` | Service node queues, buffer utilization $\rho$, and service rates |
| `GET` | `/api/v1/state/bottlenecks` | Dynamic bottleneck rankings and historical migration log |
| `GET` | `/api/v1/state/switchbacks` | Active switchback slot reservations and mutual exclusion locks |
| `GET` | `/api/v1/state/alerts` | Active system alerts, hazard warnings, and safety status |
| `GET` | `/api/v1/state/forecast` | Short-horizon lookahead weather and visibility forecast |
| `GET` | `/api/v1/state/history` | Sliding-window telemetry timeseries for live charts |
| `GET` | `/api/v1/network/topology` | Full graph topology with 3D coordinates & segment geometries |
| `GET` | `/api/v1/results/summary` | Real S01-S20 and Monte Carlo verified result datasets |
| `POST` | `/api/v1/control/step` | Advance digital twin discrete simulation by $N$ steps |
| `POST` | `/api/v1/control/environment` | Inject dynamic weather, visibility, and surface friction (what-if) |
| `POST` | `/api/v1/control/scenario` | Switch and execute scenario from S01 to S20 |
| `POST` | `/api/v1/control/reset` | Reset simulation state with custom fleet size (up to 50+ trucks) |
| `WS` | `/ws/v1/state/stream` | Real-time bi-directional WebSocket telemetry stream (0.5s cadence) |

### Task-3 Vehicle I/O API (`interfaces/task3_vehicle_io.py`)
| Method | Path | Description |
|---|---|---|
| `GET` | `/health` | Health check (`{"status": "ok"}`) |
| `GET` | `/api/v1/telemetry/buffer` | Active buffered vehicle telemetry count and IDs |

---

## 10. Scenario Execution

Execute the full master benchmark suite (S01 through S20):

```powershell
python main.py --benchmark-all
```
*(Or via scenario runner: `python -m scenarios.scenario_runner`)*

This runs all 20 operating scenarios:
- `S01`: Baseline Clear Weather (10 Trucks)
- `S02`: Full Mine Production Load (50 Trucks)
- `S03`: Moderate Valley Fog ($V=25\,\text{m}$)
- `S04`: Dense Advection Fog ($V=12\,\text{m}$)
- `S05`: Severe Fog Emergency ($V=5\,\text{m}$)
- `S06`–`S08`: Dynamic Fog Banks, Spatial Gradients & Post-Fog Clearing Recovery
- `S09`–`S12`: Switchback Chokepoints, High Fleet Density, Crusher & Shovel Queue Surges
- `S13`–`S16`: Downhill Grade Braking, Low Friction ($\mu=0.25$), Perception Latency & Packet Loss
- `S17`–`S20`: Combined Multi-Hazard Scenarios & Benchmark Matrix Comparisons

---

## 11. Monte Carlo Execution

Run large-scale stochastic Monte Carlo parameter sensitivity sweeps ($\ge 1,000$ iterations):

```powershell
python main.py --monte-carlo --runs 1000
```
*(Or via validator: `python -m validation.monte_carlo`)*

Sweeps over stochastic distributions of vehicle mass $m \sim \mathcal{N}(165.5\text{t}, 8\text{t})$, friction $\mu \sim \mathcal{N}(0.45, 0.12)$, visibility $V \sim \mathcal{U}(6\text{m}, 60\text{m})$, perception latency $\tau \sim \mathcal{U}(0.1\text{s}, 1.2\text{s})$, and packet loss $p_{\text{loss}} \sim \mathcal{U}(0, 0.25)$, mathematically auditing zero safety violations ($0.000000$ error rate).

---

## 12. Results Location

All verified simulation and validation artifacts are stored in `results/`:
- `results/S01.json` through `results/S20.json`: Detailed KPI outputs per scenario
- `results/scenario_summary.json`: Matrix comparing production, throughput, queue lengths, and bottlenecks
- `results/monte_carlo_summary.json`: Statistical distribution moments and percentiles
- `results/monte_carlo_results.json`: Iteration sample records
- `results/verification_report.md`: Formal mathematical verification report

---

## 13. Task-3 Telemetry Integration

The Task-3 interface (`interfaces/task3_vehicle_io.py`) provides:
- Telemetry ingestion schemas validating wheel speeds, 3-axis IMU, hydraulic brake pressure, hydrodynamic retarder temperature, radar obstacle range, and communication packet confidence.
- Supervisory command packet synthesis emitting $[v_{\text{command}}, a_{\text{target}}, \text{gear}, \text{retarder\_level}, \text{safe\_headway\_m}]$.
- Autonomous fail-safe fallback: if communication latency exceeds threshold ($> 1.5\,\text{s}$) or confidence drops below $0.70$, the vehicle transitions to autonomous local Tier-1 deceleration.

---

## 14. Known Assumptions

1. **Vehicle Kinematics**: Lumped-parameter 1D longitudinal point-mass approximation along road centerlines with pitch-plane grade force components.
2. **Surface Friction**: Piecewise-homogeneous tire-road friction coefficient $\mu$ per segment with Gaussian uncertainty bounds $\sigma_\mu$.
3. **Line-of-Sight Perception**: Headway safety envelopes assume onboard radar/LiDAR sensors operate up to the optical visibility boundary $V(s,t)$ with conservative stopping safety margin $S_{\text{margin}} = 5.0\,\text{m}$.
4. **Queue Dynamics**: Point-queue approximation with deterministic service rates $\mu_{\text{node}}$ and finite buffer capacities $Q_{\text{max}}$.

---

## 15. Safety Disclaimer

> [!CAUTION]
> **SIMULATION AND DIGITAL TWIN NOTICE**:
> The algorithms, models, and simulation results provided in this project are intended for digital twin research, operational analysis, and software integration testing. They do **not** constitute formal field safety certification under ISO 26262, ISO 21448 (SOTIF), or DGMS (Directorate General of Mines Safety) statutory requirements without physical track testing and hardware validation on the target mining equipment.
