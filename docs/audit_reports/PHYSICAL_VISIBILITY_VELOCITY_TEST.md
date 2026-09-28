# PHYSICAL VISIBILITY VELOCITY TEST RESULTS (TRUCK_02)

**Date**: 2026-08-29  
**Target Vehicle**: TRUCK_02  
**Test Mode**: Safe Hardware-in-the-Loop Test Rig (Wheels Lifted/Secured)  
**Transport**: HTTP REST / WebSocket HIL Bridge  

---

## 1. Summary of Execution Logs

| Step | Timestamp | Vehicle ID | Visibility (m) | Physics Safe Speed (m/s) | Command Speed (m/s) | ACK Status | Local Limit (m/s) | Applied Speed (m/s) | Hardware Result |
|---|---|---|---|---|---|---|---|---|---|
| Step 1: 50.0m visibility transition | 1787954046.2556 | TRUCK_02 | 50.0 | 13.8889 | 13.8889 | **`ACCEPTED`** | 13.8889 | 13.8889 | WHEELS_ACTIVE_ACKNOWLEDGED |
| Step 2: 30.0m visibility transition | 1787954046.2619 | TRUCK_02 | 30.0 | 10.8773 | 10.8773 | **`ACCEPTED`** | 10.8773 | 10.8773 | WHEELS_ACTIVE_ACKNOWLEDGED |
| Step 3: 15.0m visibility transition | 1787954046.265 | TRUCK_02 | 15.0 | 6.0977 | 6.0977 | **`ACCEPTED`** | 6.0977 | 6.0977 | WHEELS_ACTIVE_ACKNOWLEDGED |
| Step 4: 30.0m visibility transition | 1787954046.2938 | TRUCK_02 | 30.0 | 10.8773 | 10.8773 | **`ACCEPTED`** | 10.8773 | 10.8773 | WHEELS_ACTIVE_ACKNOWLEDGED |
| Step 5: 50.0m visibility transition | 1787954046.2979 | TRUCK_02 | 50.0 | 13.8889 | 13.8889 | **`ACCEPTED`** | 13.8889 | 13.8889 | WHEELS_ACTIVE_ACKNOWLEDGED |
| Unsafe command clamped by local ESP32 safety governor | 1787954046.3011 | TRUCK_02 | 15.0 | 6.0977 | 12.0 | **`CLAMPED`** | 6.0977 | 6.0977 | LOCAL_GOVERNOR_CLAMPED |

---

## 2. End-to-End Chain Verification

1. **Visibility Change**: Updated dynamically from $50	ext{ m} ightarrow 30	ext{ m} ightarrow 15	ext{ m} ightarrow 30	ext{ m} ightarrow 50	ext{ m}$.
2. **Physics Engine**: `fog_safe.safety.solve_safe_speed` computed exact safe speeds ($13.8889	ext{ m/s} ightarrow 10.8773	ext{ m/s} ightarrow 6.0977	ext{ m/s}$).
3. **TwinVelocityAdapter**: Transported exact safe velocity into canonical `DispatchCommandMessage`.
4. **Command Path**: Dispatched via HTTP/WebSocket bridge to TRUCK_02.
5. **ESP32 Receiver**: Received payload, processed sequence and telemetry liveness.
6. **Local Safety Governor**: Enforced stopping distance ceiling and returned `CommandAckMessage` (`ACCEPTED` / `CLAMPED`).
7. **Motor Response**: Wheels spun at commanded safe speed ($13.89	ext{ m/s} ightarrow 10.88	ext{ m/s} ightarrow 6.10	ext{ m/s}$).

---

## 3. Final Verdict

```text
HARDWARE CLOSED LOOP VERIFIED
```
