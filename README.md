# FOG-ORCHESTRATOR 2.0 — Task 2 Digital Twin
## Demo V0.1: Minimum Working Vertical Slice

This repository contains the **Demo V0.1 Minimum Working Vertical Slice** of the Task 2 Digital Twin for **FOG-ORCHESTRATOR 2.0**.
It models a synthetic open-cast iron ore haul network and simulates the causal chain of visibility degradation, safe speed reduction, capacity loss, queue formation, bottleneck identification, and arrival-rate shaping.

---

## 1. Project Orientation & Evidence Classifications

In compliance with the project build specification, all numerical parameters and simulation inputs are tagged with their authoritative evidence classification:

*   **`[REFERENCE]`**: Representative OEM specifications for BEML BH100 dumpers (tare/payload/mass/dimensions). Not direct mine telemetry.
*   **`[SIMULATION BASELINE]`**: Chosen baseline parameters for the synthetic network simulation (e.g. Shovel 15 vph, Crusher 18 vph). Not verified site statistics.
*   **`[MODEL CONFIG]`**: System calibration parameters and safety margins (latency $\tau = 0.25$ s, headway margins, standstill offsets).
*   **`[SIMULATION SCENARIO]`**: Values varied dynamically in stress-tests (visibility, road grade, fleet size, surface friction).
*   **`[ASSUMPTION]`**: Engineering constants used to model resistance (air density, dumper drag coefficients, rolling resistance coefficients).
*   **`[UNKNOWN]`**: Field values that cannot be simulated (site-specific friction logs, actual visibility maps, communication packet loss). Must be replaced with real telemetry in Task 3.

---

## 2. Project Layout

```
digitalTwin_FOG/
│
├── config/
│   ├── vehicle.yaml        # BH100 tare, payload, dimensions, retardation limits
│   ├── roads.yaml          # Mine network road segments and grades
│   ├── nodes.yaml          # Mine network service nodes (Shovel, Crusher)
│   ├── weather.yaml        # Fog and wetness friction properties
│   └── scenarios.yaml      # Simulation loop configuration (seeds, timesteps)
│
├── models/
│   ├── vehicle.py          # State tracking and empty-to-loaded transitions
│   ├── vehicle_physics.py  # Force-balance governor and safe-speed calculations
│   ├── braking.py          # Stopping distance quadratic solver
│   ├── road_capacity.py    # Analytical capacity Cr calculations
│   ├── queue_model.py      # Discrete-time queue logic: Q(t+dt)
│   ├── bottleneck.py       # Bottleneck score calculation
│   └── switchback.py       # Tier-2 switchback slots stub interface
│
├── weather/
│   └── fog_model.py        # Environmental visibility updates and wetness transitions
│
├── twin/
│   ├── network.py          # Custom graph G=(V,E) representation
│   ├── state.py            # HMI-facing state serialization
│   └── simulator.py        # Core loop and safety constraint enforcement
│
├── control/
│   └── arrival_shaping.py  # Shovel dispatch controller (Tier-3 arrival rate shaper)
│
├── interfaces/
│   └── task2_state_schema.py # API schemas for Task 1 HMI and Task 3 telemetry
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
├── results/                # CSV and JSON summary outputs
├── plots/                  # Generated PNG charts
│
├── main.py                 # Simulation runner CLI
├── requirements.txt        # Package configuration
└── README.md               # This file
```

---

## 3. Installation & Setup

Before running the simulation, activate the existing virtual environment and install the minimal dependencies.

### Step 3.1: Activate Virtual Environment
Open PowerShell and run:
```powershell
.venv\Scripts\Activate.ps1
```

### Step 3.2: Install Dependencies
```powershell
pip install -r requirements.txt
```

---

## 4. Reproducible Run Command

To run the entire set of scenarios (Clear, Dense Fog, Fog Recovery, Crusher Bottleneck, Shaping Comparison, Full Vertical Slice) and generate all validation logs/plots:
```powershell
python main.py
```

To run a single specific scenario (e.g. the full vertical slice):
```powershell
python main.py --scenario DEMO_06_FULL_VERTICAL_SLICE
```

Supported scenario flags:
*   `DEMO_01_CLEAR`
*   `DEMO_02_DENSE_FOG`
*   `DEMO_03_FOG_RECOVERY`
*   `DEMO_04_CRUSHER_BOTTLENECK`
*   `DEMO_05_ARRIVAL_SHAPING_OFF`
*   `DEMO_05_ARRIVAL_SHAPING_ON`
*   `DEMO_06_FULL_VERTICAL_SLICE`

---

## 5. Verification & Testing

Demo V0.1 contains a test suite of **17 unit and system tests** covering forces, safety constraints, capacity calculations, queue conservation, and bottleneck identification.

To execute all tests, run:
```powershell
python -m unittest discover -s tests -p "test_*.py"
```

### Core Tests Executed:
*   **`TEST 01`**: Graph validity and connectivity.
*   **`TEST 02`**: Vehicle mass transitions (Empty $\leftrightarrow$ Loaded).
*   **`TEST 03–04`**: Physics equations, stopping envelope, and safe-speed calculations.
*   **`TEST 05–08`**: Monotonicity checks for Visibility, Grade, Friction, and Latency.
*   **`TEST 09`**: Headway spacing validity ($H \ge 15.5$ m).
*   **`TEST 10`**: Analytical capacity checks.
*   **`TEST 11–13`**: Queue conservation, growth, and dissipation.
*   **`TEST 14`**: Crusher bottleneck score priority.
*   **`TEST 15`**: Arrival shaping queue stabilization.
*   **`TEST 16`**: Fog clearing recovery transitions.
*   **`TEST 17`**: Safety Override verification ($v_{\rm command} \le v_{\rm safe}$ at every step).
