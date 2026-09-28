# END-TO-END DATA FLOW DIAGRAM SPECIFICATION
**PROJECT**: FOG-ORCHESTRATOR 2.0  
**DATE**: 2026-08-28  

---

## 1. END-TO-END SYSTEM DATA FLOW DIAGRAM

```mermaid
sequenceDiagram
    autonumber
    participant Env as Environment Model
    participant Twin as Digital Mine Twin
    participant Pred as Bottleneck Engine
    participant Opt as Central Optimizer
    participant HMI as Supervisory HMI (FastAPI/React)
    participant HIL as Hardware Emulator (Vehicle A & B)

    loop 1.0 Hz Simulation Tick Loop
        Env->>Twin: RoadStateMessage (visibility_m, friction_mu, grade)
        Twin->>Pred: Fleet positions, segment queues, service rates
        Pred->>Pred: Compute lambda, mu, queue dynamics & Bottleneck Scores
        Pred->>Opt: BottleneckStateMessage (critical node identified)
        
        alt Congestion Predicted (lambda > mu)
            Opt->>Opt: Calculate arrival shaping release delay
            Opt->>HIL: DispatchCommandMessage (HOLD / TARGET_SPEED, reason_code)
            HIL->>HIL: Run Local Safety Governor: applied = min(target, v_safe)
            HIL->>Opt: CommandAckMessage (status=ACCEPTED/CLAMPED, applied_speed)
        end

        HIL->>Twin: VehicleStateMessage & SafetyStateMessage
        Twin->>HMI: Broadcast full HMI_STATE_SCHEMA via WebSocket (/ws/live)
        HMI->>HMI: Render live Mine Map, Fog profile, Bottleneck alerts, & KPIs
    end
```

---

## 2. DETAILED MESSAGE DATA FLOW STEPS

### Step 1: Environmental Sensing & Perception Update
- **Data Product**: `RoadStateMessage`
- **Fields**: `segment_id`, `timestamp`, `visibility_m`, `friction`, `grade`, `capacity_vph`, `safe_speed_mps`.
- **Frequency**: 1.0 Hz.
- **Direction**: Environment Model $\rightarrow$ Digital Twin & Hardware Emulators.

### Step 2: Twin Kinematics & Queue State Assembly
- **Data Product**: Internal Twin State
- **Fields**: Vehicle positions ($s$), velocities ($v$), payload weights, road segment occupancy, node queue lengths.
- **Frequency**: 1.0 Hz.
- **Direction**: Digital Twin $\rightarrow$ Bottleneck Engine.

### Step 3: Bottleneck Detection & Queue Prediction
- **Data Product**: `BottleneckStateMessage`
- **Fields**: `node_id`, `timestamp`, `lambda_vph`, `mu_vph`, `queue`, `queue_max`, `utilization`, `criticality`, `bottleneck_score`.
- **Logic**: Evaluates $\lambda > \mu$ condition. If crusher queue $\ge 2$, computes elevated bottleneck score.
- **Direction**: Bottleneck Engine $\rightarrow$ Central Optimizer.

### Step 4: Dispatch Decision & Reason Code Packaging
- **Data Product**: `DispatchCommandMessage`
- **Fields**: `command_id`, `vehicle_id`, `timestamp`, `target_speed`, `route_id`, `departure_time`, `slot_id`, `action`, `reason_code`.
- **Example Reason Code**: `ARRIVAL_RATE_EXCEEDS_CAPACITY`.
- **Direction**: Central Optimizer $\rightarrow$ Hardware Interface Emulator.

### Step 5: Local Safety Clamping & ACK Generation
- **Data Product**: `CommandAckMessage` & `SafetyStateMessage`
- **Fields**: `command_id`, `vehicle_id`, `timestamp`, `status` (`ACCEPTED`/`CLAMPED`), `applied_speed`, `reason`, `v_safe`, `active_constraint`.
- **Logic**: Local governor evaluates $v_{\rm safe} = \min(v_{\rm stop}, v_{\rm retarder}, v_{\rm curve}, v_{\rm mine})$. Applies $\min(v_{\rm command}, v_{\rm safe})$.
- **Direction**: Hardware Interface Emulator $\rightarrow$ Central Twin & Optimizer.

### Step 6: Live WebSocket HMI Streaming
- **Data Product**: Full `HMI_STATE_SCHEMA` JSON State Vector
- **Transport**: FastAPI WebSocket Endpoint (`ws://127.0.0.1:8000/ws/live`).
- **Target**: Supervisory Web HMI (React / Vite Frontend).
- **Update Frequency**: 1.0 Hz real-time broadcast.
