# 10 — CONTROL-ROOM HMI VALIDATION REPORT
## FOG-ORCHESTRATOR 2.0 | SIH 2026-27 (Problem Statement: SIH26007)
### NMDC Bailadila Low-Visibility HEMM Safety & Operational Intelligence System
**Document ID:** `10_CONTROL_ROOM_HMI_VALIDATION.md`  
**Phase:** 9 — Full Hardware + Software + HMI + Control Room + Digital Twin Integration  
**Date:** September 2026 | **Classification:** LEVEL 2 / LEVEL 3 (Software & UI Validated)  
**Status:** COMPLETE & FROZEN  

---

## 1. Purpose & Architectural Differentiation (Section 10)

The Control Room HMI (`SYNQRA_SIH2026-27-HMI/frontend/src/state/ProviderHost.tsx`) is designed for fleet superintendents, safety controllers, and dispatch engineers.

Unlike the in-cab Operator HMI (which is local and driver-centric), the Control Room HMI provides:
1. **Fleet-Level Situational Awareness:** Global mine map, vehicle spatial distribution, corridor occupancy, and staging queues.
2. **Operational Decision Support:** Visibility heatmaps, dynamic speed limits, bottleneck analysis, and production cycle tracking.
3. **Incident & Alert Management:** Real-time event triage with actionable severity levels.
4. **Digital Mine Synchronization:** Authoritative 2D/3D representation of mine assets.

---

## 2. Fleet Overview & Vehicle Card Specification (Section 11)

Every active HEMM in the fleet displays an authoritative real-time telemetry card generated directly from the canonical `VehicleState`:

```
+---------------------------------------------------------------+
| HEMM CARD: TRUCK-07                UPDATE AGE: 180 ms [LIVE]  |
+---------------------------------------------------------------+
| SPEED:             8.3 km/h       SAFE SPEED:        9.1 km/h |
| VISIBILITY:        8.0 m          GRADE:             -5.0 %   |
| GATEWAY:           GW-02          RF QUALITY:        DEGRADED |
| SENSORS:           VALID          CAN STATE:         NORMAL   |
| SAFETY STATE:      NORMAL         FAILSAFE STATE:    NOMINAL  |
| POSITION:          X: 1420.5 m, Y: 890.2 m (Ramp R1)          |
| TWIN SYNC:         SYNCHRONIZED (RMSE 0.32 m)                 |
+---------------------------------------------------------------+
```

---

## 3. Event-Driven Alert Engine Specification (Section 12)

The Control Room alert engine processes telemetry events into structured, auditable incident records across 4 severity tiers:

| Severity | Event Type | Trigger Criteria | Default Operator / System Action |
|:---|:---|:---|:---|
| **CRITICAL** | `COMMUNICATION_LOST` | Gateway heartbeat lost $>500\text{ ms}$; Safe Beacon active | Fleet safety hold; notify field marshals; verify autonomous safe crawl |
| **HIGH** | `SAFE_SPEED_VIOLATION`| Vehicle speed $> v_{\text{safe}} + 0.5\text{ m/s}$ | Vehicle local governor automatically brakes; control room logs safety excursion |
| **HIGH** | `SENSOR_DEGRADED` | Optical sensor noisy / stuck or sequence gaps $>2$ | System penalizes $R_{\text{eff}}$ by $30\%$; dispatch technician for lens cleaning |
| **MEDIUM** | `GATEWAY_HANDOVER` | Vehicle migrates from GW-01 to GW-02 cell | Verify session continuity and link correlation score |
| **MEDIUM** | `VISIBILITY_DETERIORATION`| Visibility drops below $15\text{ m}$ threshold | Update haul road capacity model; stagger truck release intervals |
| **INFO** | `COMMUNICATION_RECOVERED`| Gateway re-establishes valid link; 2 sync frames | Exit Safe Beacon mode; restore nominal fleet monitoring |

### Canonical Alert Record Schema:
```json
{
  "alert_id": "ALT_20260924_0042",
  "timestamp": 1727136000.180,
  "vehicle_id": "TRUCK_07",
  "location": "RAMP_R1_BENCH_4",
  "trigger": "VISIBILITY_DROPPED_BELOW_10M",
  "severity": "HIGH",
  "state": "ACTIVE",
  "action": "AUTOMATIC_SPEED_CLAMP_TO_4MPS",
  "resolution": "PENDING"
}
```

---

## 4. Control Room Non-Authority Rule (Section 13)

```
[MANDATORY ARCHITECTURAL BOUNDARY]
The Control Room may:
- MONITOR fleet operations
- ANALYZE safety envelopes
- WARN vehicle operators
- COORDINATE haul routes & switchbacks
- ACKNOWLEDGE alarms
- DISPATCH target speed proposals
- LOG auditable incident data

THE CONTROL ROOM MUST NEVER:
- Bypass the vehicle's Local Safety Governor.
- Directly actuate hydraulic brakes or throttles.
- Override an active local Emergency Stop or Safe Mode.
```

If a central dispatch speed is commanded:
$$\text{Central Dispatch } (v_{\text{dispatch}}) \longrightarrow \text{Local Safety Governor } \left(v_{\text{applied}} = \min(v_{\text{dispatch}}, v_{\text{safe}})\right) \longrightarrow \text{Actuator}$$

---

## 5. Control Room Failure & Disconnection Modes (Section 30)

1. **Central Server Outage:** If the central control room server crashes or network breaks down, **VEHICLES CONTINUE OPERATING SAFELY**. The onboard Local Safety Governor maintains complete independent control.
2. **Re-connection & State Recovery:** When the control room reconnects, it synchronizes with current vehicle telemetry. Remote control is **NOT** automatically restored without explicit verification.
3. **Database Disconnection:** Telemetry is buffered in local memory ring buffers without dropping CAN safety loops.
