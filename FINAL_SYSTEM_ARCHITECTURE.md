# FINAL SYSTEM ARCHITECTURE SPECIFICATION
**PROJECT**: FOG-ORCHESTRATOR 2.0  
**VERSION**: 2.0-INTEGRATED  
**DATE**: 2026-08-28  

---

## 1. ARCHITECTURE OVERVIEW

The **FOG-ORCHESTRATOR 2.0** architecture provides dynamic, real-time fleet orchestration, bottleneck mitigation, and physical safety enforcement for autonomous mining haulage during low-visibility fog events.

```
                    ┌──────────────────────────────┐
                    │       ENVIRONMENT MODEL      │
                    │ Fog / Visibility             │
                    │ Road Condition & Friction    │
                    │ Grade & Weather Forecast     │
                    └──────────────┬───────────────┘
                                   │
                                   ▼
                    ┌──────────────────────────────┐
                    │       DIGITAL MINE TWIN       │
                    │ Mine Road Graph & Queues     │
                    │ Fleet Kinematics Simulation  │
                    │ Crusher / Shovel Nodes       │
                    └──────────────┬───────────────┘
                                   │
                                   ▼
                    ┌──────────────────────────────┐
                    │    PREDICTION & BOTTLENECK    │
                    │          ENGINE               │
                    │ Capacity Reduction           │
                    │ Queue Evolution (lambda/mu)  │
                    │ Bottleneck Score Engine      │
                    └──────────────┬───────────────┘
                                   │
                                   ▼
                    ┌──────────────────────────────┐
                    │       OPTIMIZATION ENGINE     │
                    │ Receding-Horizon Dispatch    │
                    │ Arrival Rate Shaping         │
                    │ Hold / Release / Target Speed│
                    └──────────────┬───────────────┘
                                   │
                                   ▼
                    ┌──────────────────────────────┐
                    │      SUPERVISORY HMI          │
                    │ Operations Overview Dashboard│
                    │ Live Fog & Queue Telemetry   │
                    │ Reason Codes & Alerts        │
                    └──────────────┬───────────────┘
                                   │
                                   ▼
                    ┌──────────────────────────────┐
                    │   VEHICLE COMMUNICATION API   │
                    │ VehicleState / SafetyState   │
                    │ DispatchCommand / Ack        │
                    │ Hardware Interface Emulator  │
                    └──────────────┬───────────────┘
                                   │
                                   ▼
                    ┌──────────────────────────────┐
                    │ PHYSICAL HARDWARE (NEXT STEP) │
                    │ ESP32 Microcontrollers       │
                    │ LoRa Transceivers & IMUs     │
                    │ Wheel Speed & Motor Driver   │
                    └──────────────────────────────┘
```

---

## 2. LAYER DESCRIPTIONS & INTERFACES

### Layer 1: Environment Model
- **Role**: Simulates dynamic weather events, fog visibility decay ($50\text{ m} \to 10\text{ m}$), ground-truth tire-road friction ($\mu = 0.60 \to 0.25$), road grade ($\theta$), and perception range ($R_{\rm effective}$).
- **Interface Output**: `RoadStateMessage` containing `visibility_m`, `friction`, `grade`, `capacity_vph`, and `safe_speed_mps`.

### Layer 2: Digital Mine Twin
- **Role**: Maintains mine road network graph, discrete-time fleet kinematics, node queues (`ServiceQueue`), and vehicle payload states (BEML BH100 class: 74 t empty, 165 t gross).
- **Interface Output**: `VehicleStateMessage` streaming positions, speeds, segment locations, and load status.

### Layer 3: Prediction & Bottleneck Engine
- **Role**: Evaluates arrival rate ($\lambda$), service rate ($\mu$), queue accumulation ($Q(t+dt) = \max(0, Q(t) + (\lambda - \mu)dt)$), and computes node bottleneck scores:
  $$\text{Score} = \left(\frac{\lambda}{\mu}\right) \cdot \left(1 + \frac{Q}{Q_{\rm max}}\right) \cdot \text{Criticality}$$
- **Interface Output**: `BottleneckStateMessage` identifying primary bottleneck nodes (e.g. Crusher).

### Layer 4: Central Optimization Engine
- **Role**: Generates receding-horizon dispatch commands and arrival-rate shaping releases at upstream loading points (Shovel) to match downstream constrained capacity.
- **Interface Output**: `DispatchCommandMessage` carrying `target_speed`, `action` (`HOLD`/`RELEASE`/`TARGET_SPEED`), `departure_time`, `slot_id`, and `reason_code`.

### Layer 5: Supervisory HMI
- **Role**: Exposes live web dashboard (React / Vite frontend + FastAPI WebSocket backend `/ws/live`). Visualizes mine map, fog boundaries, safe speeds, queue evolution, bottleneck alerts, and optimizer decisions. Advises operators; performs no vehicle safety overrides.

### Layer 6: Vehicle Communication API & Hardware Interface Emulator
- **Role**: Acts as the software-HIL bridge for Vehicle A and Vehicle B. Ingests `DispatchCommandMessage` packets and runs the **Non-Negotiable Local Safety Governor**:
  $$\text{applied\_speed} = \min(v_{\rm command}, v_{\rm safe})$$
  Evaluates multi-constraint safe speed ($v_{\rm safe} = \min(v_{\rm stop}, v_{\rm retarder}, v_{\rm curve}, v_{\rm mine})$) and returns `CommandAckMessage` and `SafetyStateMessage`.
- **Fault Injection**: Simulates packet loss, latency, communication loss, and stale telemetry (triggering fallback to $v_{\rm safe} = 2.78\text{ m/s}$ / $10\text{ km/h}$).

### Layer 7: Physical Hardware (Next Step Boundary)
- **Role**: ESP32 microcontroller firmwares (`sketch_aug26a.ino`, `vehicle_B.ino`), LoRa transceivers, wheel speed sensors, IMUs, and motor controllers.
- **Integration Boundary**: The hardware emulator abstraction allows physical ESP32/LoRa hardware to replace Layer 6 transport without requiring central architecture changes.

---

## 3. NON-NEGOTIABLE SAFETY COMMAND HIERARCHY

```
Central Optimizer (Advisory / Supervisory)
        │
        │ Proposes target_speed / HOLD / RELEASE / route / slot
        ▼
Vehicle Interface / Hardware Emulator
        │
        │ Passes command to local vehicle controller
        ▼
Local Safety Governor (Non-Negotiable)
        │
        ├─ Computes v_safe = min(v_stop, v_retarder, v_curve, v_mine)
        ├─ Enforces applied_speed = min(v_command, v_safe)
        └─ If Comm Loss or Stale Data -> Fallback to v_safe <= 2.78 m/s (10 km/h)
```

1. **Central Command Clamp**: If central command requests $v_{\rm command} > v_{\rm safe}$, local governor clamps speed to $v_{\rm safe}$ and returns `status = CLAMPED` in ACK.
2. **Communication Failure Safety**: If communication is interrupted for $> 5.0\text{ s}$, vehicle drops out of central control into `LOCAL_SAFE` mode with speed capped at $2.78\text{ m/s}$ ($10\text{ km/h}$).
3. **HMI Independence**: Vehicle safety logic runs locally on vehicle hardware/emulator and does not depend on HMI connectivity.
