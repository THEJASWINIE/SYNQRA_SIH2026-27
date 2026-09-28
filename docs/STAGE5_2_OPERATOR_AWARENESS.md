# STAGE 5.2: OPERATOR SITUATIONAL AWARENESS & GUIDANCE EVIDENCE
**Authoritative Operational State, Data Provenance, and Decision Logic**  
**Project:** FOG-ORCHESTRATOR 2.0 (SIH 2026-27 — NMDC Bailadila Iron Ore Haulage)  
**Status:** VALIDATED EVIDENCE — ZERO SENSOR FABRICATION  

---

## 1. NMDC Problem Statement Alignment

This document validates NMDC Problem Statement Requirements:
- **Requirement 7:** *Improve operator situational awareness during low-visibility and monsoon fog operations.*
- **Requirement 6:** *Provide real-time monitoring and actionable operational decision support without cognitive overload.*

In large open-cast mines (such as NMDC Bailadila Deposit 5 / Deposit 14), heavy Caterpillar 777G dumpers (165.5-tonne gross mass) operate on steep 6% to 8% grades adjacent to steep drop-offs. Under monsoon fog, optical sight distance collapses from $>100\text{ m}$ down to $<12\text{ m}$. Operators cannot see preceding vehicles, road crests, or switchback queue tailbacks.

The Operator HMI provides **authoritative, real-time situational awareness** derived strictly from physical telemetry and Tier-1 safety calculations.

---

## 2. Telemetry Provenance & Data Contract

To comply with **Non-Negotiable Rule 4 (Never hard-code live hardware values)** and **Rule 6 (Frontend must not invent vehicle state)**, every field presented on the Operator HMI traces directly to an authoritative source:

| Displayed Metric | Engineering Unit | Authoritative Source | Mathematical Derivation / Hardware Provenance |
| :--- | :---: | :--- | :--- |
| **Current Speed ($v$)** | $\text{m/s}$ ($\text{km/h}$) | Onboard Odometry & ESP32 Telemetry | Pulse counter / CAN-bus wheel speed via `telemetry_ingest.py` |
| **Safe Speed ($v_{\text{safe}}$)** | $\text{m/s}$ | Tier-1 Local Safety Governor | $v_{\text{safe}} = \min(v_{\text{stop}}, v_{\text{retarder}}, v_{\text{traction}}, v_{\text{curve}}, v_{\text{mine}})$ |
| **Command Speed ($v_{\text{cmd}}$)** | $\text{m/s}$ | Tier-1 Mandatory Clamp | $v_{\text{command}} = \min(v_{\text{dispatch}}, v_{\text{safe}})$ (Immutable Safety Invariant) |
| **Visibility ($V$)** | $\text{m}$ | Roadside Optical Sensor / Twin State | Transmissometer / LiDAR optical backscatter reading |
| **Road Surface State** | Categorical | Roadside Friction Model | `"dry"` ($\mu = 0.65$) vs. `"wet"` ($\mu = 0.35$), safe bound $\mu_{\text{safe}} = 0.282$ |
| **Road Gradient ($\theta$)** | $\%$ (grade) | Topological Twin Map (`roads.yaml`) | Fixed surveyed road segment grade ($+6.25\%$ uphill, $-8.0\%$ switchback) |
| **Stopping Distance ($S_{\text{stop}}$)** | $\text{m}$ | Local Kinematics Engine | $S_{\text{stop}} = v \tau_{\text{total}} + \frac{v^2}{2 a_{\text{dec}}}$, where $a_{\text{dec}}$ accounts for grade & friction |
| **Safe Headway ($H_{\text{safe}}$)** | $\text{m}$ | Tier-1 Car-Following Model | $H_{\text{safe}} = L_{\text{veh}} + d_{\text{standstill}} + S_{\text{stop}} = 10.52\text{ m} + 5.0\text{ m} + S_{\text{stop}}$ |
| **Actual Headway ($H_{\text{act}}$)** | $\text{m}$ | Direct LoRa V2V Telemetry | $s_{\text{leader}} - s_{\text{follower}} - 10.52\text{ m}$ (monotonic odometry delta) |
| **Vehicle Ahead** | ID string | V2V Broadcast Frame | Leader vehicle identifier from direct ESP32 LoRa beacon |
| **Communication State** | Categorical | V2V Heartbeat Monitor | `V2V_ONLINE` ($\text{age} < 0.5\text{ s}$), `DEGRADED` (drop $>25\%$), `OFFLINE` ($\text{age} > 2.0\text{ s}$) |
| **Safety State** | Categorical | Tier-1 Safety State Machine | `SAFE`, `WARNING`, `RESTRICTED`, `EMERGENCY_HALT` |
| **Recommended Action** | Categorical | Advisory Decision Logic | `NORMAL`, `CAUTION`, `REDUCE SPEED`, `HOLD`, `STOP`, `RESUME` |

---

## 3. Advisory Decision Logic & Recommended Actions

The system exposes six discrete, unambiguous operational action recommendations:

```
                                  [LIVE SENSOR STATE]
                                           │
                     ┌─────────────────────┴─────────────────────┐
                     │ v_safe == 0 or Severe Fog (V <= 5m)?       │
                     └─────────────────────┬─────────────────────┘
                                           │
                           YES ────────────┴──────────── NO
                            │                            │
                     ┌──────────────┐         ┌───────────────────────────┐
                     │ ACTION: STOP │         │ Queue Ahead >= 2 Trucks?  │
                     └──────────────┘         └─────────────┬─────────────┘
                                                            │
                                            YES ────────────┴──────────── NO
                                             │                            │
                                      ┌──────────────┐         ┌───────────────────────────┐
                                      │ ACTION: HOLD │         │ Actual Headway < H_safe?  │
                                      └──────────────┘         │ OR Current Speed > v_safe?│
                                                               └────────────┬──────────────┘
                                                                            │
                                                            YES ────────────┴──────────── NO
                                                             │                            │
                                                   ┌─────────────────────┐     ┌──────────────────────┐
                                                   │ACTION: REDUCE SPEED │     │ Visibility <= 25m?   │
                                                   └─────────────────────┘     └──────────┬───────────┘
                                                                                          │
                                                                          YES ────────────┴──────────── NO
                                                                           │                            │
                                                                   ┌────────────────┐           ┌────────────────┐
                                                                   │ACTION: CAUTION │           │ ACTION: NORMAL │
                                                                   └────────────────┘           └────────────────┘
```

### Action Definitions
1. **`NORMAL`:** Operating within clear safety margins ($v \le v_{\text{safe}}$, $H_{\text{act}} \ge H_{\text{safe}}$, visibility $> 25\text{ m}$). Standard haulage operation.
2. **`CAUTION`:** Operating in reduced visibility ($V \le 25\text{ m}$) or traversing hazardous infrastructure (switchback/intersection). Full attention required; speed clamped to safe wet limit.
3. **`REDUCE SPEED`:** Active collision hazard or local governor clamping detected ($H_{\text{act}} < H_{\text{safe}}$ or requested speed $> v_{\text{safe}}$). Vehicle is automatically commanded to decelerate.
4. **`HOLD`:** Downstream bottleneck (switchback or crusher) is saturated ($\ge 2$ trucks queued). Origin staging active; vehicle holds at flat shovel apron to avoid hazardous ramp stacking.
5. **`STOP`:** Critical safety halt ($V \le 5\text{ m}$ where stopping sight distance is zero, or switchback occupied by oncoming haulage). Full service brake application.
6. **`RESUME`:** Downstream bottleneck has cleared; staged vehicle is authorized to release and proceed into the haul network.

---

## 4. Empirical Test Scenarios & State Matrix

Derived from `docs/STAGE5_2_OPERATOR_AWARENESS.csv`:

| Scenario | Vis (m) | Surface | Grade | $v$ (m/s) | $v_{\text{safe}}$ | $v_{\text{cmd}}$ | $S_{\text{stop}}$ (m) | $H_{\text{safe}}$ (m) | $H_{\text{act}}$ (m) | Leader | Comm State | Action | Safety State |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **CLEAR_NOMINAL** | $100$ | Dry | $0.0\%$ | $8.0$ | $11.11$ | $11.11$ | $10.42$ | $25.94$ | $100.0$ | None | `V2V_ONLINE` | **NORMAL** | `SAFE` |
| **MODERATE_FOG_RAMP**| $25$ | Wet | $+6.25\%$| $7.5$ | $8.33$ | $8.33$ | $11.89$ | $27.41$ | $45.0$ | TRUCK_02 | `V2V_ONLINE` | **CAUTION** | `SAFE` |
| **DENSE_FOG_FLAT** | $12$ | Wet | $0.0\%$ | $5.0$ | $6.52$ | $6.52$ | $6.08$ | $21.60$ | $30.0$ | TRUCK_02 | `V2V_ONLINE` | **CAUTION** | `SAFE` |
| **DENSE_FOG_CLOSE** | $12$ | Wet | $+6.25\%$| $4.5$ | $4.79$ | $3.00$ | $5.74$ | $21.26$ | $16.0$ | TRUCK_02 | `V2V_ONLINE` | **REDUCE SPEED**| `WARNING` |
| **ORIGIN_HOLD** | $12$ | Wet | $0.0\%$ | $0.0$ | $6.52$ | $0.00$ | $0.00$ | $15.52$ | $200.0$ | None | `V2V_ONLINE` | **HOLD** | `RESTRICTED` |
| **SEVERE_FOG_STOP** | $5$ | Wet | $+6.25\%$| $0.0$ | $0.00$ | $0.00$ | $0.00$ | $15.52$ | $50.0$ | None | `V2V_ONLINE` | **STOP** | `EMERGENCY_HALT` |
| **COMM_DEGRADED** | $12$ | Wet | $0.0\%$ | $4.0$ | $6.52$ | $4.00$ | $4.62$ | $20.14$ | $25.0$ | TRUCK_02 | `DEGRADED` | **CAUTION** | `SAFE` |
| **COMM_OFFLINE** | $12$ | Wet | $+6.25\%$| $0.0$ | $4.79$ | $0.00$ | $0.00$ | $15.52$ | $0.0$ | Unknown | `OFFLINE` | **CAUTION** | `RESTRICTED` |

---

## 5. Failure & Communication Loss Behavior

### 5.1 Local Fallback Invariant
The central architecture guarantees that **loss of central communications never imperils vehicle safety**:
1. **Heartbeat Timeout ($> 2.0\text{ s}$):** If V2V or central telemetry stops arriving, `comm_state` shifts to `OFFLINE`.
2. **Autonomous Local Governor:** The Tier-1 governor onboard the truck continues calculating $v_{\text{safe}}$ using onboard sensors (wheel odometry, IMU, local sight sensor).
3. **Conservative Standalone Envelope:** In `OFFLINE` mode, the truck assumes worst-case headway and limits speed strictly to its local visual stopping distance:
   $$v_{\text{cmd}} = \min\left(v_{\text{requested}}, v_{\text{safe}}(\text{local\_sight})\right)$$
4. **Zero Central Dependence:** A failure of the central FastAPI backend, Wi-Fi gateway, or Digital Twin leaves the vehicle fully protected against overspeeding.

---

## 6. Local vs Central Authority Architecture

| Authority Layer | Component | Function | Can It Override Local Safety? |
| :--- | :--- | :--- | :---: |
| **Tier 1 (Highest)** | Local Vehicle Governor | Stopping distance, friction limits, brake thermal limits | **AUTHORITATIVE (CANNOT BE OVERRIDDEN)** |
| **Tier 2** | Infrastructure / Switchback Coordinator | Single-lane directional locking, conflict slots | No ($v_{\text{cmd}} \le v_{\text{safe}}$) |
| **Tier 3** | Central Fleet Orchestrator / Digital Twin | Global dispatching, departure metering, route optimization | **NEVER** ($v_{\text{cmd}} = \min(v_{\text{dispatch}}, v_{\text{safe}})$) |

**Conclusion:** The Operator HMI provides complete, live situational awareness grounded in physical telemetry, preventing accidents without cognitive overload.
