# FOG-ORCHESTRATOR 2.0 — DIGITAL TWIN VELOCITY TRACE

**Date**: 2026-08-29  
**Author**: Systems Architecture & Safety Engineering Team  
**Scope**: Traceability Audit of Digital Twin Visibility $\rightarrow$ Physics Engine Safe Velocity $\rightarrow$ Vehicle Command Interface

---

## 1. Traceability Matrix & Closed-Loop Pipeline

```text
Visibility Input (e.g. 50m, 30m, 15m)
      ↓
Visibility State (EnvironmentState.r_effective / RoadStateMessage.visibility_m)
      ↓
Fog/Environment Model (fog_safe.environment / fog_orchestrator.core.config)
      ↓
Existing Physics Calculation (fog_safe.safety.solve_safe_speed / calculate_v_stop)
      ↓
Safe Velocity (SafeSpeedResult.v_safe_ms / SafetyStateMessage.v_safe)
      ↓
Command Interface (TwinVelocityAdapter -> DispatchCommandMessage)
      ↓
Physical Vehicle (Local Safety Governor Clamping -> Motor Controller)
```

---

## 2. Detailed Component Traceability

### A. Digital Twin Visibility Representation
- **Primary Source Class**: `EnvironmentState` in [`fog_safe/environment.py`](file:///c:/Users/JAGADEESH%20M/OneDrive/Documents/SIH-2026-27/fog_safe/environment.py) and `EnvironmentalParameters` in [`fog_orchestrator/core/config.py`](file:///c:/Users/JAGADEESH%20M/OneDrive/Documents/SIH-2026-27/fog_orchestrator/core/config.py).
- **Interface Field**: `r_effective` (Meters) / `visibility_m` (Meters) in `RoadStateMessage` ([`contracts.py`](file:///c:/Users/JAGADEESH%20M/OneDrive/Documents/SIH-2026-27/contracts.py)).

### B. Visibility State Mutation
- **Function/Method**: `VehicleHardwareEmulator.update_environment(visibility_m, friction_mu, grade_pct)` in [`hardware_emulator.py`](file:///c:/Users/JAGADEESH%20M/OneDrive/Documents/SIH-2026-27/hardware_emulator.py) updating `self.env.r_effective = max(0.1, visibility_m)`.

### C. Existing Physics Component Consuming Visibility
- **Module**: `fog_safe.safety` ([`fog_safe/safety.py`](file:///c:/Users/JAGADEESH%20M/OneDrive/Documents/SIH-2026-27/fog_safe/safety.py)) and `fog_orchestrator.tier1_governor.safety_governor` ([`fog_orchestrator/tier1_governor/safety_governor.py`](file:///c:/Users/JAGADEESH%20M/OneDrive/Documents/SIH-2026-27/fog_orchestrator/tier1_governor/safety_governor.py)).

### D. Function Calculating Safe Velocity
- **Function**: `solve_safe_speed(vehicle, road, env, comm, mu_effective, r_effective)` in [`fog_safe/safety.py`](file:///c:/Users/JAGADEESH%20M/OneDrive/Documents/SIH-2026-27/fog_safe/safety.py) calling `calculate_v_stop()`:
  $$\frac{1}{2 a_{\text{dec}}} v^2 + \tau_{\text{eff}} v + (S_{\text{base}} - R_{\text{effective}}) = 0 \implies v_{\text{stop}} = -a_{\text{dec}} \tau_{\text{eff}} + \sqrt{a_{\text{dec}}^2 \tau_{\text{eff}}^2 + 2 a_{\text{dec}} (R_{\text{effective}} - S_{\text{base}})}$$
- **Multi-Constraint Resolution**:
  $$v_{\text{safe}} = \min(v_{\text{stop}}, v_{\text{retarder}}, v_{\text{traction}}, v_{\text{curve}}, v_{\text{mine}})$$

### E. Pipeline Location of Final Velocity
- **Object/Field**: `SafeSpeedResult.v_safe_ms` in `fog_safe.safety` and `SafetyStateMessage.v_safe` in [`contracts.py`](file:///c:/Users/JAGADEESH%20M/OneDrive/Documents/SIH-2026-27/contracts.py).

### F. Vehicle Command Representation
- **Command Schema**: `DispatchCommandMessage` in [`contracts.py`](file:///c:/Users/JAGADEESH%20M/OneDrive/Documents/SIH-2026-27/contracts.py) and `TwinVelocityAdapter` in [`integration_adapters/twin_velocity_adapter.py`](file:///c:/Users/JAGADEESH%20M/OneDrive/Documents/SIH-2026-27/integration_adapters/twin_velocity_adapter.py).
- **Vehicle Response**: `CommandAckMessage` (`status="ACCEPTED" | "CLAMPED" | "REJECTED"`).
