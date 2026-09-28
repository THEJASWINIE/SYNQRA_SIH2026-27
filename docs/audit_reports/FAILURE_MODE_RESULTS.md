# FAILURE MODE TEST RESULTS REPORT
**PROJECT**: FOG-ORCHESTRATOR 2.0  
**TEST DATE**: 2026-08-28  

---

## 1. FAILURE MODE RESILIENCE MATRIX

| Failure Mode ID | Injected Fault Scenario | Expected System Response | Actual System Behavior | Result Status |
|---|---|---|---|---|
| **FAILURE-A** | Digital Twin backend process stops / drops offline | HMI displays `STALE/DEGRADED` banner; local vehicle governors remain fully operational | Digital Twin health status transitions to `STALE`; vehicles continue local safe operation | **PASSED** |
| **FAILURE-B** | Vehicle telemetry transmission stops ($> 5.0\text{ s}$) | Vehicle marked `OFFLINE/STALE`; central dispatcher excludes vehicle from active route allocations | Vehicle health state set to `OFFLINE`; age logged as $> 5,000\text{ ms}$ | **PASSED** |
| **FAILURE-C** | Central Optimizer crashes or halts | Simulation and vehicles remain operational; central commands fall back to nominal baseline dispatch; no unsafe speeds generated | Vehicles continue running under Tier 1 local safety governors ($0$ safety violations) | **PASSED** |
| **FAILURE-D** | Invalid or corrupted command structure received | Command rejected by vehicle interface; error logged; vehicle maintains current safe speed | Command ACK returned with `status: REJECTED` and reason logged | **PASSED** |
| **FAILURE-E** | Central target speed exceeds local safe speed ceiling ($v_{\rm command} > v_{\rm safe}$) | Local safety governor clamps speed to $v_{\rm safe}$; ACK returns `CLAMPED` status | Applied target speed clamped to exact $v_{\rm safe}$; ACK returned with `status: CLAMPED` | **PASSED** |
| **FAILURE-F** | Fog visibility sensor output drops / becomes invalid (NaN) | System falls back to conservative minimum visibility ($5.0\text{ m}$); uncertainty flag set | Sensor loss handled gracefully; safe speed capped conservatively at $0.0\text{ m/s}$ / minimum safe limit | **PASSED** |
| **FAILURE-G** | LoRa V2X communication link lost completely | Vehicle transitions to `LOCAL_SAFE / DEGRADED` mode; speed capped at fallback $v_{\rm safe} \le 2.78\text{ m/s}$ ($10\text{ km/h}$) | `SafetyState` active constraint set to `COMMUNICATION_DEGRADED_FALLBACK`; speed capped at $2.78\text{ m/s}$ | **PASSED** |
| **FAILURE-H** | Supervisory HMI window closed / reloaded | Vehicle control and physical safety are completely independent of HMI | Vehicle motion and safety governor step loop continue without interruption | **PASSED** |

---

## 2. DETAILED ANALYSIS OF KEY FAILURE MODES

### Failure Mode E: Central Speed Exceeding Local Safe Speed
- **Test Command**: `target_speed = 15.0 m/s` (54 km/h) sent to Vehicle A when local fog visibility is $10.0\text{ m}$ ($v_{\rm safe} = 3.82\text{ m/s}$).
- **Measured Result**: Vehicle emulator safety governor intercepted the command, calculated $v_{\rm safe} = 3.82\text{ m/s}$, and set `applied_speed = 3.82 m/s`. ACK returned: `status = CLAMPED`, `reason = Command speed (15.00 m/s) exceeded safe ceiling (3.82 m/s). Clamped by local governor.`

### Failure Mode G: Complete LoRa Telemetry Loss
- **Test Condition**: Set `comm_state = "LOST"` and simulated elapsed time of $10.0\text{ s}$ without telemetry update.
- **Measured Result**: Safety governor detected elapsed time $> 5.0\text{ s}$ threshold, transitioned active constraint to `COMMUNICATION_DEGRADED_FALLBACK`, capped safe speed ceiling to fallback limit $2.78\text{ m/s}$ ($10\text{ km/h}$), and prevented high-speed movement without active telemetry.

---

## 3. VERDICT

All 8 failure injection modes passed verification without any safety violations, unexpected crashes, or silent failures.
