# COMPREHENSIVE SYSTEM TEST PLAN
**PROJECT**: FOG-ORCHESTRATOR 2.0  
**DATE**: 2026-08-28  

---

## 1. TEST PLAN OBJECTIVE & SCOPE

This Test Plan defines the execution framework, test categories, verification criteria, and automated test suite structure required to validate **FOG-ORCHESTRATOR 2.0** before physical hardware integration.

Scope:
- Data contract validation
- Mathematical physics and stopping distance equations
- Non-negotiable safety governor command clamping
- Fog-to-production numerical causal chain propagation
- Queue dynamics and bottleneck detection scoring
- Optimizer arrival-rate shaping decisions
- Command flow, vehicle interface emulators, and ACKs
- Stale data detection and telemetry loss fallbacks
- Deliberate failure mode injection (Scenarios A through H)
- 15-step end-to-end reproducible scenario replay

---

## 2. TEST CATEGORIES & AUTOMATED TEST SUITE STRUCTURE

All automated tests are located in `tests/` and executable via a single command: `python -m pytest -v tests/`.

| Test Module | Description / Target | Target Criteria |
|---|---|---|
| `test_data_contract.py` | Validates logical message schemas (`VehicleState`, `SafetyState`, `RoadState`, `BottleneckState`, `DispatchCommand`, `Health`) | 100% schema compliance, invalid message rejection |
| `test_physics.py` | Validates stopping distance equation $d_{\rm stop} = v \tau + v^2/(2 a_{\rm dec})$, deceleration balance, grade, and friction | Exact mathematical precision, numerical stability |
| `test_safety_governor.py` | Validates multi-constraint solver and command clamp $\text{applied\_speed} = \min(v_{\rm command}, v_{\rm safe})$ across 6 core safety scenarios | 0 safety violations, clamp active when requested speed exceeds ceiling |
| `test_fog_propagation.py` | Validates fog visibility decay $\to$ safe speed reduction $\to$ traversal time increase $\to$ capacity reduction | Monotonic physical-to-operational causal propagation |
| `test_queue_model.py` | Validates queue dynamics $Q(t+dt) = \max(0, Q(t) + (\lambda - \mu)dt)$ and mass balance conservation | Mass balance conserved across all time steps |
| `test_bottleneck_detection.py` | Validates bottleneck score calculation and dynamic node shift from Shovel $\to$ Intersection $\to$ Crusher | Correct identification of highest-risk node |
| `test_optimizer.py` | Validates arrival-rate shaper release delays and reason code generation | Throttling triggered when downstream queues accumulate |
| `test_command_flow.py` | Validates central command generation $\to$ emulator ingestion $\to$ safety clamping $\to$ ACK generation | Command ACK returned with status `ACCEPTED` or `CLAMPED` |
| `test_stale_data.py` | Validates telemetry age monitoring and stale data detection | Telemetry age $> 5.0\text{ s}$ triggers fallback $v_{\rm safe} \le 2.78\text{ m/s}$ |
| `test_failure_modes.py` | Validates system resilience across 8 deliberate failure injection modes (A through H) | Graceful degradation, 0 unsafe commands, 0 system crashes |
| `test_end_to_end.py` | Validates complete 15-step reproducible demo scenario replay | Queue reduction in Fog-Orchestrator vs Baseline |

---

## 3. EXECUTION PROCEDURE

### Single-Command Automated Verification
Run in PowerShell / Terminal:
```powershell
python -m pytest -v tests/
```

### Comparative Benchmark Execution
Run in PowerShell / Terminal:
```powershell
python run_baseline_vs_orchestrator.py
```

### Live HMI Backend Server Launch
Run in PowerShell / Terminal:
```powershell
python -m uvicorn app.main:app --reload --port 8000
```
(Executed from `SYNQRA_SIH2026-27-HMI/backend` directory).
