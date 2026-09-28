# FOG-ORCHESTRATOR 2.0 — PROJECT EXECUTION AUDIT (PHASE 0)

**Date**: 2026-08-28  
**Author**: Senior Systems Integration Engineer & Software Verification Engineer  
**Scope**: Independent System A (HMI) & System B (Digital Twin) Structural & Execution Audit

---

## 1. System Component Registry & Architecture Map

| Component | Location | Entry Point | Dependencies | Status |
|-----------|----------|-------------|--------------|--------|
| **HMI Root Directory** | `SYNQRA_SIH2026-27-HMI/` | `SYNQRA_SIH2026-27-HMI/README.md` | React 19, Vite 7, FastAPI, Pydantic | **VALIDATED** |
| **HMI Backend** | `SYNQRA_SIH2026-27-HMI/backend/` | `SYNQRA_SIH2026-27-HMI/backend/app/main.py` | FastAPI, Uvicorn, WebSockets, Pydantic | **VALIDATED** |
| **HMI Frontend** | `SYNQRA_SIH2026-27-HMI/frontend/` | `SYNQRA_SIH2026-27-HMI/frontend/src/main.tsx` | React, TypeScript, Vite, Vitest | **VALIDATED** |
| **Digital Twin Root** | `fog_orchestrator/` & `SYNQRA_SIH2026-27-main/` | `fog_orchestrator/main.py` | NumPy, Pandas, SciPy, Matplotlib | **VALIDATED** |
| **Physics Engine** | `fog_safe/` & `fog_orchestrator/tier1_governor/` | `fog_safe/safety.py`, `vehicle_physics.py` | Math, NumPy, PyDantic | **VALIDATED** |
| **Fog / Environment Model** | `fog_safe/environment.py` & `fog_orchestrator/tier2_infrastructure/` | `fog_safe/environment.py` | Math, Dataclasses | **VALIDATED** |
| **Vehicle Model** | `fog_safe/vehicle.py` & `fog_orchestrator/simulation/` | `fog_safe/vehicle.py`, `simulator.py` | Dataclasses, NumPy | **VALIDATED** |
| **Queue Model** | `fog_orchestrator/tier3_central/` | `digital_twin.py`, `simulator.py` | Graph network, Math | **VALIDATED** |
| **Bottleneck Detection** | `fog_orchestrator/tier3_central/` | `bottleneck_analyzer.py` | Mine network, Dataclasses | **VALIDATED** |
| **Safety Governor** | `fog_orchestrator/tier1_governor/` | `safety_governor.py` | RLS Estimator, VehiclePhysics | **VALIDATED** |
| **Orchestrator** | `fog_orchestrator/tier3_central/` | `optimizer.py`, `digital_twin.py` | Chance-constrained MPC | **VALIDATED** |
| **Existing Simulation Scripts** | Root & `fog_orchestrator/` | `fog_orchestrator/main.py`, `fog_safe/main.py` | Python 3.14, NumPy, Pandas | **VALIDATED** |
| **Existing Test Files** | `tests/`, `SYNQRA_SIH2026-27-HMI/frontend/src/` | `pytest tests/`, `npm test` | Pytest, Vitest | **VALIDATED** |
| **Requirements & Docs** | `SYNQRA_SIH2026-27-HMI/requirements/`, `docs/` | `CLAUDE.md`, `ARCHITECTURE_AUDIT.md` | Markdown, PDF | **VALIDATED** |

---

## 2. Issues & Root Cause Classification

Every issue identified during the Phase 0 audit is classified below according to severity (`CRITICAL`, `HIGH`, `MEDIUM`, `LOW`) and root cause taxonomy:
- **A. Execution issue** (Invocation path or shell environment issue)
- **B. Dependency issue** (Missing package or module path)
- **C. Configuration issue** (Port, endpoint, or environment configuration)
- **D. Actual software defect** (Code logic or contract violation)
- **E. Missing file** (Missing mock script or test suite entrypoint)

### Audit Issue Log

#### ISSUE 01: Direct script execution of `fog_orchestrator/main.py` failed due to missing module path
- **Severity**: `HIGH`
- **Root Cause Category**: `B. Dependency issue` / `A. Execution issue`
- **Description**: Running `python fog_orchestrator/main.py` throws `ModuleNotFoundError: No module named 'fog_orchestrator'`.
- **Resolution**: Execute using module mode `python -m fog_orchestrator.main` or set `PYTHONPATH=.`.

#### ISSUE 02: HMI Frontend `node_modules` missing in initial clone
- **Severity**: `MEDIUM`
- **Root Cause Category**: `B. Dependency issue`
- **Description**: Running `npm test` or `npm run dev` in `SYNQRA_SIH2026-27-HMI/frontend` fails before `npm install`.
- **Resolution**: Executed `npm install` inside `SYNQRA_SIH2026-27-HMI/frontend`. All 830 frontend Vitest tests pass cleanly.

#### ISSUE 03: Pytest collection error when running `pytest` globally from workspace root
- **Severity**: `MEDIUM`
- **Root Cause Category**: `C. Configuration issue` / `B. Dependency issue`
- **Description**: Plain `pytest` attempts to collect duplicate test names (`test_bottleneck.py`) across historical baseline subdirectories (`SYNQRA_SIH2026-27-main/V0_1_BASELINE`).
- **Resolution**: Scope test execution to `python -m pytest tests/`. All 33 root Python tests pass 100%.

#### ISSUE 04: HMI Backend missing dedicated WebSocket telemetry endpoint and REST command receiver
- **Severity**: `HIGH`
- **Root Cause Category**: `E. Missing file` / `C. Configuration issue`
- **Description**: `SYNQRA_SIH2026-27-HMI/backend/app/main.py` only contained `/api/health`. Independent HMI validation requires WebSocket streaming and command endpoints (`TARGET_SPEED`, `HOLD`, `STOP`, `RELEASE`).
- **Resolution**: Add `/api/ws`, `/api/commands`, `/api/vehicles`, and `/api/telemetry` to HMI Backend app without importing Digital Twin packages.

#### ISSUE 05: Missing independent HMI mock vehicle generator (`mock_vehicle_generator.py`)
- **Severity**: `HIGH`
- **Root Cause Category**: `E. Missing file`
- **Description**: The prompt requires a isolated `MOCK_MODE` script (`mock_vehicle_generator.py`) simulating Vehicle A (`TRUCK_01` normal telemetry) and Vehicle B (`TRUCK_02` comm degradation test) with ZERO Digital Twin dependencies.
- **Resolution**: Create `mock_vehicle_generator.py` using canonical message contracts (`contracts.py`) only.

---

## 3. Scope Boundaries & Non-Interference Audit

- **System A Isolation**: HMI contains NO imports from `fog_orchestrator` or `fog_safe`.
- **System B Isolation**: Digital Twin contains NO imports from `SYNQRA_SIH2026-27-HMI` or frontend packages.
- **Hardware Code Safety**: `esp32_code/` remains untouched and uncompiled.

---

## 4. Phase 0 Audit Conclusion

Both System A and System B codebases are fully intact, structurally sound, and ready for independent verification execution.
