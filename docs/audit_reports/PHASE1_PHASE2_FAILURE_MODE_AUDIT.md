# FOG-ORCHESTRATOR 2.0 — FAILURE PROPAGATION AUDIT (AUDIT PART 9)

**Date**: 2026-08-28  
**Author**: Principal Systems Architect, Safety-Critical Systems Verification Engineer  
**Scope**: Failure Mode & Effects Analysis (FMEA) for Future Integrated System

---

## Failure Mode & Propagation Matrix

### Scenario 1: Digital Twin Process Crashes
- **Failure**: Digital Twin Python process terminates or encounters uncaught exception.
- **Detection**: HMI Backend heartbeats to Digital Twin fail (HTTP/WebSocket timeout).
- **Isolation**: High-level advisory layer is completely isolated from physical hardware control.
- **Fallback**: Physical vehicles continue operating normally under Phase 1 supervisory control and local ESP32 safety governor.
- **Recovery**: Automatic process restart of Digital Twin; state re-synchronized upon boot.
- **Severity**: **LOW** (Non-Critical Advisory System)

---

### Scenario 2: Phase 1 Hardware Loses LoRa Communication
- **Failure**: RF interference or vehicle power off interrupts telemetry stream.
- **Detection**: Gateway serial reader heartbeat timer exceeds $3.0\text{s}$ (`STALE`) / $10.0\text{s}$ (`OFFLINE`).
- **Isolation**: Hardware quality filter marks vehicle `OFFLINE`.
- **Fallback**: Digital Twin marks vehicle state as `COMMUNICATION_DEGRADED` and stops updating simulation position. Digital Twin **NEVER** invents physical telemetry.
- **Recovery**: Upon RF reconnection, status transits `OFFLINE` $\rightarrow$ `RECOVERING` $\rightarrow$ `ONLINE`.
- **Severity**: **MEDIUM** (Operational Outage)

---

### Scenario 3: Digital Twin Produces Unsafe / Invalid Speed Target
- **Failure**: Digital Twin calculates $v_{\text{rec}} = 25.0\text{ m/s}$ ($90\text{ km/h}$) due to sensor noise or optimization artifact.
- **Detection**: Local physical safety governor on ESP32 evaluates requested speed against local stopping distance.
- **Isolation**: Physical vehicle clamps speed strictly to local safe limit ($10.87\text{ m/s}$).
- **Fallback**: Vehicle executes $v_{\text{applied}} = 10.87\text{ m/s}$ and returns ACK `CLAMPED`.
- **Recovery**: Digital Twin recalibrates next optimization cycle based on returned ACK.
- **Severity**: **HIGH** (Prevented by Local Safety Authority)

---

### Scenario 4: Time Synchronization Fails
- **Failure**: Host clock drift or NTP loss causes time offset discrepancy $> 3.0\text{s}$.
- **Detection**: Time Adapter detects timestamp lag relative to host NTP timekeeper.
- **Isolation**: Stale simulation recommendations are discarded immediately.
- **Fallback**: Vehicle ignores expired advisories and maintains current safe operating velocity.
- **Recovery**: NTP clock resynchronization.
- **Severity**: **MEDIUM** (Advisory Expiration)

---

### Scenario 5: Vehicle ID Mismatch
- **Failure**: Dispatched command contains unmapped or invalid vehicle ID (`TRUCK_99`).
- **Detection**: Vehicle ID Mapper Adapter fails lookup dictionary.
- **Isolation**: Command is rejected at HMI Backend boundary with HTTP 400.
- **Fallback**: Vehicle maintains current state; no command sent over LoRa RF.
- **Recovery**: Re-issue command with valid vehicle ID.
- **Severity**: **LOW** (Rejected Command)

---

### Scenario 6: Duplicate Command Issued
- **Failure**: Network retry re-issues existing `command_id` (`CMD_102`).
- **Detection**: HMI Backend checks `command_history` registry for duplicate `command_id`.
- **Isolation**: Duplicate command returns immediate `REJECTED` response.
- **Fallback**: Vehicle ignores duplicate transmission; no repeated motor actuation.
- **Recovery**: None required (Idempotent protection active).
- **Severity**: **LOW** (Idempotent Handling)

---

### Scenario 7: Conflicting Digital Twin Recommendations
- **Failure**: Fog model recommends slowing down ($4.0\text{ m/s}$), while Queue optimizer recommends accelerating ($8.0\text{ m/s}$).
- **Detection**: 5-Constraint Safety Governor evaluates minimum boundary.
- **Isolation**: Minimum speed constraint wins: $v_{\text{advisory}} = \min(4.0, 8.0) = 4.0\text{ m/s}$.
- **Fallback**: Vehicle executes conservative lower speed.
- **Recovery**: Next optimization loop resolves conflict.
- **Severity**: **LOW** (Fail-Safe Hierarchy)

---

### Scenario 8: Digital Twin Optimization Delays ($> 5.0\text{s}$)
- **Failure**: Heavy CC-MPC matrix calculation delays advisory output.
- **Detection**: Command Adapter freshness check detects expired recommendation.
- **Isolation**: Recommendation expires silently.
- **Fallback**: HMI Backend falls back to default manual supervisory speed limits.
- **Recovery**: Subsequent optimization cycle completes.
- **Severity**: **LOW** (Performance Degradation)
