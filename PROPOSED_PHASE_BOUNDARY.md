# FOG-ORCHESTRATOR 2.0 — PROPOSED PHASE BOUNDARY SPECIFICATION (AUDIT PART 7)

**Date**: 2026-08-28  
**Author**: Principal Systems Architect, Distributed Systems Engineer  
**Scope**: Interface Boundary Rules and Data Flow Boundaries between Phase 1 and Phase 2

---

## 1. Upstream Data Boundary (Phase 1 Hardware $\rightarrow$ Phase 2 Digital Twin)

```text
PHYSICAL HARDWARE                 UPSTREAM ADAPTER                 DIGITAL TWIN
┌─────────────────┐             ┌──────────────────┐             ┌─────────────────┐
│ Vehicle State   │────────────>│ Telemetry Filter │────────────>│ Vehicle Twin    │
└─────────────────┘             └──────────────────┘             └─────────────────┘
```

| Field Name | Category | Rationale |
|------------|----------|-----------|
| `vehicle_id` | **MUST SEND** | Essential for fleet identification & state binding |
| `timestamp` | **MUST SEND** | Required for time synchronization & age tracking |
| `sequence_number` | **MUST SEND** | Needed for packet loss detection & out-of-order filter |
| `speed_mps` | **MUST SEND** | Primary physical telemetry for dumper state estimation |
| `rpm` | **MUST SEND** | Direct physical sensor measurement from LM393 |
| `acceleration` ($AX, AY$) | **SHOULD SEND** | Enables slope & dynamic deceleration validation |
| `gyroscope` ($GZ$) | **SHOULD SEND** | Enables yaw rate & curve detection |
| `communication_status` | **MUST SEND** | Essential to inform Digital Twin of `ONLINE`/`STALE`/`OFFLINE` state |
| `raw_imu_lsb` | **DO NOT SEND** | Keep raw sensor details isolated within Phase 1 |
| `debug_serial_text` | **DO NOT SEND** | Keep debug logs completely off the network boundary |

---

## 2. Downstream Data Boundary (Phase 2 Digital Twin $\rightarrow$ Phase 1 HMI / Hardware)

```text
DIGITAL TWIN                   DOWNSTREAM ADAPTER                 PHYSICAL HARDWARE
┌─────────────────┐             ┌──────────────────┐             ┌─────────────────┐
│ Advisory State  │────────────>│ Command Adapter  │────────────>│ ESP32 Governor  │
└─────────────────┘             └──────────────────┘             └─────────────────┘
```

| Field Name | Category | Rationale |
|------------|----------|-----------|
| `vehicle_id` | **MUST SEND** | Target vehicle identifier for command routing |
| `recommended_speed` | **MUST SEND** | Advisory speed target calculated by 5-constraint solver |
| `predicted_visibility` | **SHOULD SEND** | Informs operator of dynamic fog conditions ahead |
| `surface_friction_mu` | **SHOULD SEND** | Informs operator of low-traction road conditions |
| `hold_recommendation` | **SHOULD SEND** | Fleet arrival shaping hold recommendation |
| `dispatch_delay_s` | **OPTIONAL** | Queue optimization delay |
| `raw_cc_mpc_matrix` | **DO NOT SEND** | Keep complex optimization matrices inside Phase 2 |
| `direct_pwm_values` | **DO NOT SEND (CRITICAL)** | **NEVER** allow Digital Twin to issue raw PWM motor commands |
