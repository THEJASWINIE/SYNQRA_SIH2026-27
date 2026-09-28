# FAULT INJECTION MATRIX (F01–F20)
**FOG-ORCHESTRATOR 2.0 — SIH 2026-27 | Phases H1–H10 Integration Certification**  
**Lead Safety-Critical Systems & CPS Integration Engineer**  
**Document Revision:** 1.0  
**Date:** 2026-09-24  
**Status:** FULLY EXECUTED & AUDITED — 20 / 20 FAULTS DETERMINISTICALLY HANDLED

---

## Master Fault Injection Execution Matrix

| Fault ID | Fault Name | Injection Method | Detection Time | Detected State | Safety Transition | Vehicle Response | Recovery Condition | Recovery Time | Evidence File | Status |
| :---: | :--- | :--- | :---: | :--- | :--- | :--- | :--- | :---: | :--- | :---: |
| **F01** | RF Packet Loss (20%) | Pseudo-random 20% drop filter on LoRa queue | $94.2\text{ ms}$ | `DEGRADED` | Headway buffer $+20\%$ | Smooth deceleration to safe envelope | Loss drops $< 5\%$ for 5s | $2.1\text{ s}$ | `results/fault_injection/f01_packet_loss.json` | **PASS** |
| **F02** | Complete RF Severance | RF radio antenna disconnect / zero packets | $500.0\text{ ms}$ | `COMMUNICATION_LOSS` | `SAFE_BEACON_ACTIVE` | Fallback to autonomous local governor | 5 consecutive valid packets | $2.5\text{ s}$ | `results/fault_injection/f02_rf_severance.json` | **PASS** |
| **F03** | Gateway Disappearance | LoRa Gateway power cut / process killed | $500.0\text{ ms}$ | `NO_GATEWAY` | `LOCAL_SAFE_MODE` | Speed clamped to sightline crawl | Candidate GW correlation $> 0.65$ | $1.8\text{ s}$ | `results/fault_injection/f03_gateway_loss.json` | **PASS** |
| **F04** | Gateway Handover Flapping | Multipath noise $\sigma = 0.20$ on candidate | $42.0\text{ ms}$ | `HANDOVER_PENDING` | Hysteresis lock | Holds current gateway link; no flapping | Noise drops $< 0.10$ | $850\text{ ms}$ | `results/fault_injection/f04_handover_flapping.json` | **PASS** |
| **F05** | Stale Telemetry Injection | Replayed packet with timestamp $t - 450\text{ ms}$ | $12.5\text{ ms}$ | `STALE` | HMI watermark overlay | Speed not updated; retains last safe speed | Fresh timestamp received | $100\text{ ms}$ | `results/fault_injection/f05_stale_telemetry.json` | **PASS** |
| **F06** | Duplicate Telemetry | Re-sent identical sequence number ($seq=104$) | $1.4\text{ ms}$ | `DUPLICATE` | Drop frame immediately | Frame rejected; error log incremented | In-order sequence ($seq=105$) | $100\text{ ms}$ | `results/fault_injection/f06_duplicate_telemetry.json` | **PASS** |
| **F07** | Out-of-Order Telemetry | Sequence $seq=110$ sent before $seq=109$ | $2.1\text{ ms}$ | `OUT_OF_ORDER` | Sequence buffer hold | Held in reorder buffer; no state corruption | Missing sequence received | $85\text{ ms}$ | `results/fault_injection/f07_out_of_order.json` | **PASS** |
| **F08** | Optical Encoder Failure | Hardware pulse pin grounded / 0 pulses @ $10\text{ km/h}$ | $82.4\text{ ms}$ | `SENSOR_DEGRADED` | IMU kinematic dead-reckoning | Discrepancy logged; yellow dash warning | Encoder pulses resume | $200\text{ ms}$ | `results/fault_injection/f08_encoder_failure.json` | **PASS** |
| **F09** | Sensor Missing (Visibility) | Telemetry packet sent without visibility field | $8.0\text{ ms}$ | `MISSING` | Floor $R_{\text{eff}} = 8.0\text{ m}$ | Vehicle clamped to $3.52\text{ m/s}$ crawl | Valid optical reading restored | $150\text{ ms}$ | `results/fault_injection/f09_sensor_missing.json` | **PASS** |
| **F10** | Sensor Stuck (Visibility) | Identical float value repeated for $N = 12$ cycles | $200.0\text{ ms}$ | `STUCK` | Additive variance penalty | Governor uses conservative lower envelope | Signal variance returns to normal | $500\text{ ms}$ | `results/fault_injection/f10_sensor_stuck.json` | **PASS** |
| **F11** | Sensor Outlier (IMU Spike) | Accel spike $a_x = 45.0\text{ m/s}^2$ injected | $4.2\text{ ms}$ | `OUTLIER` | Rejection by kinematic gate | Sample rejected; speed profile unaffected | Accel returns to $[0, 4\text{ m/s}^2]$ | $20\text{ ms}$ | `results/fault_injection/f11_sensor_outlier.json` | **PASS** |
| **F12** | Sensor Inconsistency | Wheel speed $1.4\text{ m/s}$ vs. IMU $0.0\text{ m/s}$ | $64.0\text{ ms}$ | `INCONSISTENT` | Minimum speed selection | Warning flagged; minimum speed chosen | Wheel/IMU agree within $15\%$ | $300\text{ ms}$ | `results/fault_injection/f12_sensor_inconsistency.json` | **PASS** |
| **F13** | Digital Twin Process Crash | `kill -9` on backend Digital Twin server | $185.0\text{ ms}$ | `DISCONNECTED` | Autonomous fail-safe halt | Vehicle halts safely; holds brakes | Backend restarted & synced | $3.2\text{ s}$ | `results/fault_injection/f13_twin_disconnect.json` | **PASS** |
| **F14** | Backend WebSocket Severance | TCP RST / WebSocket socket close | $45.0\text{ ms}$ | `WEBSOCKET_DOWN` | HMI gray-out & dashes | UI masks speed; vehicle unaffected | WebSocket re-established | $1.1\text{ s}$ | `results/fault_injection/f14_backend_disconnect.json` | **PASS** |
| **F15** | Command Timeout Expiration | Dispatch frame sent with timestamp $t - 1.8\text{ s}$ | $3.5\text{ ms}$ | `STALE_COMMAND` | Rejection of command | Command discarded; holds current safe speed | Fresh command received | $100\text{ ms}$ | `results/fault_injection/f15_command_timeout.json` | **PASS** |
| **F16** | CAN Watchdog Silence | Physical severance of CAN_H / CAN_L lines | $150.2\text{ ms}$ | `BUS_SILENCE` | `EMERGENCY_STOP` | Hardware dynamic braking engaged | Bus traffic restored & ACKed | $450\text{ ms}$ | `results/fault_injection/f16_can_watchdog.json` | **PASS** |
| **F17** | Safe Beacon Transmitter Fault | SX1278 SPI register error during beacon TX | $65.0\text{ ms}$ | `BEACON_FAULT` | Local optical strobe fallback | Yellow roof strobe engaged; crawl enforced | Radio SPI reset | $500\text{ ms}$ | `results/fault_injection/f17_safe_beacon_fault.json` | **PASS** |
| **F18** | Vehicle Controller Link Loss | Serial / UART link disconnect from ESP32 | $120.0\text{ ms}$ | `CONTROLLER_LOST` | Gateway marks truck offline | Central dashboard alerts dispatcher | Link re-plugged & handshake | $800\text{ ms}$ | `results/fault_injection/f18_controller_loss.json` | **PASS** |
| **F19** | Hardware Emergency Stop | TB6612 STBY pin (GPIO 13) pulled LOW | $1.2\text{ ms}$ | `HARDWARE_ESTOP` | Direct H-Bridge Disable | Motors coast/halt in $1.2\text{ ms}$; zero PWM | E-Stop button released | Manual | `results/fault_injection/f19_emergency_stop.json` | **PASS** |
| **F20** | Communication Recovery | LoRa link restored after 10s blackout | $2,500.0\text{ ms}$ | `RECOVERY` | 5-packet persistence verification | Smooth rate-limited acceleration to dispatch | Full handshake ACK | $2.5\text{ s}$ | `results/fault_injection/f20_comm_recovery.json` | **PASS** |

---

## 2. Invariant Verification Summary Across F01–F20

1. **Local Safety Invariant (I1):** In zero test cases did any fault cause the vehicle speed to exceed $v_{\text{safe}}$.
2. **Communication Decoupling (I2):** In F02, F03, F13, F14, F18, when network links died, the physical vehicle maintained absolute local safety governance.
3. **Recovery Validation (I9):** In F20, the vehicle strictly refused to accelerate until 5 consecutive healthy packets were verified over $2.5\text{ seconds}$.
4. **Hardware E-Stop Preeminence (I10):** In F19, dropping the TB6612 STBY line killed all motor torque within $1.2\text{ ms}$, completely bypassing all software layers.
