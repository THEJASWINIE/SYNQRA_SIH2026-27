# FOG-ORCHESTRATOR 2.0 — DIGITAL TWIN INDEPENDENT RUN GUIDE (SYSTEM B)

This guide provides exact step-by-step commands to run and operate System B (**Digital Twin** / Mine Simulation / Fog Physics / Physics Engine / Safety Governor / Orchestrator) located in [`SYNQRA_SIH2026-27-main`](file:///c:/Users/JAGADEESH%20M/OneDrive/Documents/SIH-2026-27/SYNQRA_SIH2026-27-main) and [`fog_orchestrator`](file:///c:/Users/JAGADEESH%20M/OneDrive/Documents/SIH-2026-27/fog_orchestrator) in complete isolation without HMI, WebSocket, or physical hardware dependencies.

---

## Digital Twin Root Directory: `SYNQRA_SIH2026-27-main/`

The Digital Twin codebase is structured in [`SYNQRA_SIH2026-27-main/`](file:///c:/Users/JAGADEESH%20M/OneDrive/Documents/SIH-2026-27/SYNQRA_SIH2026-27-main):

| Module | Location | Purpose |
|--------|----------|---------|
| **Digital Twin Simulator** | [`SYNQRA_SIH2026-27-main/twin/simulator.py`](file:///c:/Users/JAGADEESH%20M/OneDrive/Documents/SIH-2026-27/SYNQRA_SIH2026-27-main/twin/simulator.py) | Mine simulation engine & state stepper |
| **Digital Twin State** | [`SYNQRA_SIH2026-27-main/twin/state.py`](file:///c:/Users/JAGADEESH%20M/OneDrive/Documents/SIH-2026-27/SYNQRA_SIH2026-27-main/twin/state.py) | Global mine state & vehicle tracker |
| **Mine Network Graph** | [`SYNQRA_SIH2026-27-main/twin/network.py`](file:///c:/Users/JAGADEESH%20M/OneDrive/Documents/SIH-2026-27/SYNQRA_SIH2026-27-main/twin/network.py) | Mine topology graph $G=(V,E)$ |
| **Vehicle Physics** | [`SYNQRA_SIH2026-27-main/models/vehicle_physics.py`](file:///c:/Users/JAGADEESH%20M/OneDrive/Documents/SIH-2026-27/SYNQRA_SIH2026-27-main/models/vehicle_physics.py) | Longitudinal vehicle dynamic equations |
| **Braking Engine** | [`SYNQRA_SIH2026-27-main/models/braking.py`](file:///c:/Users/JAGADEESH%20M/OneDrive/Documents/SIH-2026-27/SYNQRA_SIH2026-27-main/models/braking.py) | Service brake & retarder thermal limits |
| **Queue Model** | [`SYNQRA_SIH2026-27-main/models/queue_model.py`](file:///c:/Users/JAGADEESH%20M/OneDrive/Documents/SIH-2026-27/SYNQRA_SIH2026-27-main/models/queue_model.py) | Node queue accumulation dynamics |
| **Bottleneck Scoring** | [`SYNQRA_SIH2026-27-main/models/bottleneck.py`](file:///c:/Users/JAGADEESH%20M/OneDrive/Documents/SIH-2026-27/SYNQRA_SIH2026-27-main/models/bottleneck.py) | Utilization $\rho = \lambda/\mu$ & severity score |
| **Digital Twin Main Runner** | [`SYNQRA_SIH2026-27-main/main.py`](file:///c:/Users/JAGADEESH%20M/OneDrive/Documents/SIH-2026-27/SYNQRA_SIH2026-27-main/main.py) | Primary Task 2 Digital Twin execution script |
| **Digital Twin Verification** | [`SYNQRA_SIH2026-27-main/verify_task2_final.py`](file:///c:/Users/JAGADEESH%20M/OneDrive/Documents/SIH-2026-27/SYNQRA_SIH2026-27-main/verify_task2_final.py) | Full Task 2 verification & audit suite |

---

## Target Architecture

```
                    MINE MODEL
                        │
                        ▼
                 ENVIRONMENT MODEL
                        │
                ┌───────┴────────┐
                │                │
                ▼                ▼
             FOG MODEL       ROAD MODEL
                │                │
                └───────┬────────┘
                        │
                        ▼
                  PHYSICS ENGINE
                        │
                        ▼
                 VEHICLE SIMULATION
                        │
                        ▼
                   SAFETY ENGINE
                        │
                        ▼
                    QUEUE MODEL
                        │
                        ▼
               BOTTLENECK DETECTION
                        │
                        ▼
                   ORCHESTRATOR
                        │
                        ▼
                 DISPATCH DECISION
```

---

## Execution Commands

### 1. Run Task 2 Digital Twin Execution & Verification Suite

To execute the Task 2 Digital Twin validation suite inside `SYNQRA_SIH2026-27-main`:

```powershell
cd "c:\Users\JAGADEESH M\OneDrive\Documents\SIH-2026-27\SYNQRA_SIH2026-27-main"
python verify_task2_final.py
```

Outputs generated:
- `TASK2_REQUIREMENT_TRACEABILITY.md`
- `NFR_TRACEABILITY.md`
- `TASK2_POST_IMPLEMENTATION_VERIFICATION_REPORT.md`

---

### 2. Run Task 2 Digital Twin Simulation (`SYNQRA_SIH2026-27-main/main.py`)

```powershell
cd "c:\Users\JAGADEESH M\OneDrive\Documents\SIH-2026-27\SYNQRA_SIH2026-27-main"
python main.py
```

---

### 3. Run Fog Physics & 5-Constraint Safety Engine (`fog_safe`)

Executes physical constraint validation, 12 safety scenarios, and generates 14 visual plot figures:

```powershell
cd "c:\Users\JAGADEESH M\OneDrive\Documents\SIH-2026-27"
python -m fog_safe.main
```

---

### 4. Run 3-Tier Orchestrator Benchmark (`fog_orchestrator`)

Executes 22 killer scenarios, 1,000 Monte Carlo trials, ablation study, and adversarial audit:

```powershell
cd "c:\Users\JAGADEESH M\OneDrive\Documents\SIH-2026-27"
python -m fog_orchestrator.main
```

---

### 5. Execute Independent System B Acceptance Test

To run the automated 12-check verification suite:

```powershell
cd "c:\Users\JAGADEESH M\OneDrive\Documents\SIH-2026-27"
python verify_digital_twin_independent.py
```

Expected Output:

```
==================================================
DIGITAL TWIN INDEPENDENT VERIFICATION
==================================================
CHECK 1 ........ PASS
CHECK 2 ........ PASS
CHECK 3 ........ PASS
CHECK 4 ........ PASS
CHECK 5 ........ PASS
CHECK 6 ........ PASS
CHECK 7 ........ PASS
CHECK 8 ........ PASS
CHECK 9 ........ PASS
CHECK 10 ........ PASS
CHECK 11 ........ PASS
CHECK 12 ........ PASS

FINAL RESULT:

DIGITAL TWIN INDEPENDENT SYSTEM: PASS
```
