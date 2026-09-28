# PHASE 7.4 — FAILURE INJECTION TEST MATRIX (SAFE-01 to SAFE-25)
## FOG-ORCHESTRATOR 2.0 — SIH26007
**Classification:** Experimental Failure Injection & Invariant Validation Matrix  
**Dataset Source:** `data/phase7_4_failure_injection.csv`  
**Test Suite:** `tests/test_phase7_4_safe_beacon.py` (43 passed tests)  

---

## 1. Overview & Evaluation Protocol

This matrix records the systematic injection of 25 communication, environmental, telemetry, and adversarial failure modes into the FOG-ORCHESTRATOR 2.0 system.

For every failure scenario, the test verifies:
1. **Detection Latency:** Time elapsed between failure occurrence and state transition.
2. **Fallback State:** Deterministic state machine entry (`NORMAL`, `DEGRADED`, `STOP`, `EMERGENCY`, `COMM_LOSS`).
3. **Speed Enforcement:** Clamped speed $v_{\text{applied}} \le v_{\text{safe}}$.
4. **Safety Invariant Preserved:** Monotonic safety holds without runaway or permissive bypass.

---

## 2. Complete Failure Injection Matrix

| Test ID | Scenario Name | Test Setup & Fault Injection | Input Condition | Expected Behavior | Observed Behavior | Verdict | Evidence Level |
|---|---|---|---|---|---|---|---|
| **SAFE-01** | NORMAL_OPERATION | All radios healthy (Gateway + V2V + Beacon) | Central requests 4.0 m/s ($v_{\text{safe}}=5.0$) | Command accepted, NORMAL state | Speed = 4.0 m/s, ACCEPT | **PASS** | L7 Bench Measured |
| **SAFE-02** | GATEWAY_FAILURE | Gateway radio link severed | Central commands severed | Reject central cmd, maintain local safety | State = NO_GATEWAY, REJECT, speed $\le 4.0$ | **PASS** | L7 Bench Measured |
| **SAFE-03** | V2V_FAILURE | Direct V2V peer beacon severed | Central requests 3.5 m/s | Degraded communication, local governor active | State = DEGRADED_COMMUNICATION, speed $\le 4.0$ | **PASS** | L7 Bench Measured |
| **SAFE-04** | GATEWAY_PLUS_V2V_FAILURE | Both Gateway and V2V severed simultaneously | Central requests 5.0 m/s | Total RF loss: local governor authoritative | State = NO_GATEWAY, REJECT, speed $\le 3.5$ | **PASS** | L7 Bench Measured |
| **SAFE-05** | BEACON_LOSS_TIMEOUT | Peer beacon ceases transmission | $\Delta t > 1.0\text{ s}$ silence | Peer marked COMM_LOSS; headway doubled ($50\text{m} \to 100\text{m}$); free-flow speed ceiling unchanged ($4.00\text{ m/s}$) | Peer retained in memory, headway 100m, speed ceiling 4.00 m/s | **PASS** | L1 Deterministic |
| **SAFE-06** | TOTAL_RF_LOSS | Gateway + V2V + Beacon offline | Local sensors active | Local governor enforces safe envelope | Speed clamped $\le 3.0$ m/s, no acceleration | **PASS** | L1 Deterministic |
| **SAFE-07** | REPLAY_ATTACK | Attacker replays old NORMAL after STOP | Seq 1 (NORMAL) sent after Seq 2 (STOP) | Replay packet rejected, STOP persists | State = STOP, speed = 0.0 m/s, DUPLICATE/OUT_OF_ORDER | **PASS** | L1 Deterministic |
| **SAFE-08** | DUPLICATE_PACKET | Repeated transmission of identical sequence | Same sequence $N=5$ times | Duplicate rejected on sequence check | First accepted, 4 rejected as DUPLICATE | **PASS** | L1 Deterministic |
| **SAFE-09** | OUT_OF_ORDER_PACKET | Sequences arrive 100, 101, then 99, 98 | Decreasing sequence numbers | Stale sequence rejected | 100, 101 accepted; 99, 98 OUT_OF_ORDER | **PASS** | L1 Deterministic |
| **SAFE-10** | MALFORMED_PACKET | Corrupted string, truncated fields, bad types | Non-CSV, missing fields, NaN | Packet rejected without backend crash | Rejected as MALFORMED, state unchanged | **PASS** | L1 Deterministic |
| **SAFE-11** | SPOOFED_VEHICLE_ID | Unauthorized vehicle ID injected | `TRUCK_99` injected | Rejected at validation boundary | Rejected as UNKNOWN_VEHICLE | **PASS** | L1 Deterministic |
| **SAFE-12** | INVALID_STATE_PAYLOAD | Unrecognized state string | State = `ACCELERATE` | Rejected at state enum check | Rejected as UNKNOWN_STATE | **PASS** | L1 Deterministic |
| **SAFE-13** | TIMESTAMP_FAILURE | Future, ancient, zero, negative timestamps | $t > t_{\text{clock}} + 0.1\text{s}$ or age $> 1.0\text{s}$ | Stale or future packet rejected | Rejected as FUTURE_TIMESTAMP / STALE | **PASS** | L1 Deterministic |
| **SAFE-14** | BURST_LOSS_100_PKTS | 100 consecutive dropped packets | RF fade for 5.0 s | Watchdog trips, fallback activated | State = COMM_LOSS, defensive headway | **PASS** | L7 Bench Measured |
| **SAFE-15** | RECOVERY_PROGRESSION | Recovery after channel restoration | Clear frames re-introduced | Re-synchronization required | State transitions safely: FAIL $\to$ RECOVERY $\to$ NORMAL | **PASS** | L1 Deterministic |
| **SAFE-16** | EMERGENCY_BEACON | Peer vehicle transmits EMERGENCY | Peer enters emergency state | Local vehicle halts immediately | State = EMERGENCY_STOP, speed = 0.0 m/s | **PASS** | L7 Bench Measured |
| **SAFE-17** | STOP_BEACON | Peer vehicle transmits STOP | Preceding truck stopped at crossing | Local safety state enters STOP, commanded speed 0.0 m/s; old replay rejected; requires valid clear beacon + $N=2$ frames in RECOVERY to exit | State = STOP, speed = 0.0 m/s, CLAMP | **PASS** | L7 Bench Measured |
| **SAFE-18** | RACE_CONDITION | Simultaneous STOP, NORMAL, EMERGENCY | Conflicting frames arrive at $t=100.0$ | Precedence holds: EMERGENCY > STOP > NORMAL | Final state = EMERGENCY, speed = 0.0 m/s | **PASS** | L1 Deterministic |
| **SAFE-19** | GATEWAY_POWER_RESTORE | Gateway power loss then restoration | Gateway powers up, requests 15 m/s | Restoration mandates RECOVERY state; frame 1 rejected; frame 2 exits recovery and clamps excessive speed | Frame 1: RECOVERY, Frame 2: UNSAFE_COMMAND clamped $\le 4.0\text{ m/s}$ | **PASS** | L7 Bench Measured |
| **SAFE-20** | DENSE_FOG_TRANSITION | Visibility drops from 50m to 3m | $R = 3.0\text{ m} \le S_{\text{base}}$ ($5.0\text{ m}$) | Immediate zero-speed safe limit (STAGED) | $v_{\text{safe}} = 0.0\text{ m/s}$, vehicle staged | **PASS** | L6 Model |
| **SAFE-21** | VISIBILITY_NOISE | Visibility noise $\pm 15\%$ above 5.0m | $R \in [6.0, 50.0]\text{ m}$ noisy | Permissible speed adapts within envelope | $S_{\text{stop}} + S_{\text{base}} \le R$ at all ticks | **PASS** | L6 Model |
| **SAFE-22** | CHATTERING_ELIMINATION | Visibility fluctuating $4.9\text{ m} \leftrightarrow 5.1\text{ m}$ | Oscillating dense fog reading | Schmitt debounce prevents $0 \leftrightarrow 0.21$ m/s chatter | Remains STAGED without command chatter | **PASS** | L1 Deterministic |
| **SAFE-23** | CENTRAL_OVERRIDE_ATTEMPT | Central optimizer requests 25 m/s | Over-speed command injection | Governor clamps command to local $v_{\text{safe}}$ | Speed clamped to 4.38 m/s, UNSAFE_COMMAND | **PASS** | L1 Deterministic |
| **SAFE-24** | STALE_COMMAND_TIMEOUT | Command age > 1.0s | Issue timestamp $t=95.0$, recv $t=100.0$ | Stale command rejected by governor | State = STALE_COMMAND, REJECT | **PASS** | L1 Deterministic |
| **SAFE-25** | COMMAND_RECOVERY_RESYNC | Resync after E-Stop reset | Commands arrive post-reset | First command rejected, second accepted | State transitions: RECOVERY $\to$ NORMAL | **PASS** | L1 Deterministic |

---

## 3. Matrix Statistical Summary

- **Total Injected Failure Scenarios:** 25
- **Passed Scenarios:** 25 (100.0%)
- **Failed Scenarios:** 0 (0.0%)
- **Safety Invariant Violations:** 0
- **Maximum Detection Latency:** $1.050\text{ s}$ (Gateway watchdog expiry)
- **Minimum Detection Latency:** $0.005\text{ s}$ (Local sensor / math fault clamp)
- **Zero-Speed Command Enforcement on E-Stop / STOP:** Verified in 100% of tested scenarios.
