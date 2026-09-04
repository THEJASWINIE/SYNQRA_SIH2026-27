# FOG-SAFE: Physics-Constrained Safe-Speed & Headway Optimization Engine

**Application Context**: Open-Cast Mine Haulage in Low-Visibility and Fog Conditions  
**Reference Operations**: NMDC Limited (BIOM-Kirandul, BIOM-Bacheli, Donimalai)  
**Reference Heavy Haulage Dumper**: BEML BH100-Class (74t Empty / 165t Loaded)  

---

## Overview

FOG-SAFE is a mathematical modeling, simulation, and real-time safe-speed optimization architecture designed to determine the highest physically defensible operating speed $v_{\text{safe}}$ and safe longitudinal headway separation $H_{\text{safe}}$ for heavy mine dumpers operating on haul roads under degraded visibility and wet/slippery surface conditions.

Rather than relying on static speed limits or heuristic fog rules, FOG-SAFE enforces strict physics constraints:
$$S_{\text{stop}} + S_{\text{margin}} \le R_{\text{effective}}$$

and optimizes across five simultaneous physical candidate speed limits:
$$v_{\text{safe}} = \min(v_{\text{stop}}, v_{\text{retarder}}, v_{\text{traction}}, v_{\text{curve}}, v_{\text{mine}})$$

---

## Quick Start

### 1. Installation

Install required Python dependencies:
```bash
pip install -r requirements.txt
```

### 2. Execution

To run the complete validation suite, scenario tests 1–12, Monte Carlo uncertainty analysis, generate all 14 visual charts, and export CSV/JSON results:

```bash
python -m fog_safe.main
```

---

## Codebase Architecture

- `fog_safe/config.py`: Reference vehicle, road, environment, reaction latency, and safety margin parameters.
- `fog_safe/vehicle.py`: BEML BH100 physical mass and drag state model.
- `fog_safe/road.py`: Haul road geometry ($\theta$, $C_{\text{rr}}$, $R_{\text{curve}}$, $v_{\text{mine}}$).
- `fog_safe/environment.py`: Awareness range $R_{\text{effective}}$ and friction priors.
- `fog_safe/dynamics.py`: Longitudinal vehicle force balance equations ($F_{\text{drive}}, F_{\text{grade}}, F_{\text{roll}}, F_{\text{aero}}$).
- `fog_safe/braking.py`: Tire-road longitudinal friction limits ($\mu m g \cos\theta$) and emergency stopping distance.
- `fog_safe/retarder.py`: Continuous downhill retarding power limit ($P_{\text{retarder\_max}}$).
- `fog_safe/friction.py`: Friction prior management and surface classification labels.
- `fog_safe/headway.py`: Conservative dynamic longitudinal headway $H_{\text{safe}}$ and time headway $T_{\text{headway}}$.
- `fog_safe/communication.py`: V2X latency decomposition and dynamic safety margin expansion $S_{\text{margin}}$.
- `fog_safe/safety.py`: Multi-constraint safe speed optimization engine and constraint traceability solver.
- `fog_safe/rls.py`: Recursive Least Squares (RLS) estimator and mathematical identifiability failure analysis.
- `fog_safe/simulator.py`: Dynamic time-stepping physics simulation engine.
- `fog_safe/scenarios.py`: Implementation of Tests 1 through 12.
- `fog_safe/metrics.py`: Summary statistics and safety violation counters.
- `fog_safe/validation.py`: Automated dimensional, boundary, monotonicity, and physical sanity tests.
- `fog_safe/plots.py`: High-resolution Matplotlib generator for all 14 required figures.
- `fog_safe/main.py`: Main CLI execution orchestrator.

---

## Verification & Outputs

Executing `python -m fog_safe.main` produces:
1. `results/`: CSV output files for all scenario sweeps and Monte Carlo runs.
2. `plots/`: 14 high-resolution visual plots.
3. `summary_results.json`: Machine-readable summary data.
4. Terminal output confirming formal validation status.
