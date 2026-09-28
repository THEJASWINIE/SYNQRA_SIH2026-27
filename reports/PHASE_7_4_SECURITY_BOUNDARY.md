# PHASE 7.4 — SECURITY BOUNDARY & ADVERSARIAL RESILIENCE AUDIT
## FOG-ORCHESTRATOR 2.0 — SIH26007
**Classification:** Threat Modeling, Sequence Verification & Security Boundary Definition  
**Mandatory Declarative Standard:** Complete Honesty Regarding Cryptographic Limitations  

---

## 1. Mandatory Declarative Security Disclaimer

> [!WARNING]
> **CRYPTOGRAPHIC INTEGRITY DISCLAIMER**
> - **Message authenticity is NOT cryptographically validated.**
> - Neither the V2V telemetry protocol (`STATE,TRUCK_01,...`) nor the Safe Beacon protocol (`BEACON,vehicle_id,...`) currently incorporates cryptographic signatures (e.g. Ed25519, ECDSA) or Hash-based Message Authentication Codes (HMAC).
> - Under NO circumstances should this system be described as *"secure"*, *"tamper-proof"*, *"spoof-proof"*, or *"cryptographically authenticated"*.

---

## 2. Implemented Protocol-Level Safeguards

While unauthenticated, the system implements rigorous structural, temporal, and sequence-based verification that prevents casual protocol manipulation, network replay, and state corruption:

| Security Mechanism | Implementation File | Threat Mitigated | Defensive Behavior |
|---|---|---|---|
| **Monotonic Sequence Enforcement** | `SafeBeaconAdapter.parse_beacon_packet()` | Replay attacks, duplicate packets, packet re-ordering | Rejects any packet where sequence $\le$ latest seen sequence. |
| **Strict Precedence Latching** | `SafeBeaconAdapter._recompute_system_state()` | Replay of `NORMAL` after `STOP` or `EMERGENCY` | Once `STOP` or `EMERGENCY` is active, replaying earlier `NORMAL` frames cannot cancel safety state. |
| **Timestamp Window Verification** | `SafeBeaconAdapter.parse_beacon_packet()` | Stale packet injection, future timestamp replay | Rejects packets with age $> 1.0\text{ s}$ or timestamp $> \text{clock} + 0.10\text{ s}$. |
| **Fleet Identity Whitelist** | `SafeBeaconAdapter.ALLOWED_VEHICLES` | Casual device spoofing (e.g. `TRUCK_99`) | Discards packets from unauthorized vehicle identifiers. |
| **State Enum Whitelist** | `SafeBeaconAdapter.parse_beacon_packet()` | Permissive state injection (e.g. `ACCELERATE`) | Rejects any state not strictly in `[NORMAL, DEGRADED, STOP, EMERGENCY]`. |
| **Local Governor Speed Clamp** | `LocalVehicleSafetyGovernor.process_command()` | Malicious central over-speed dispatch | Clamps incoming commands to local physical safe speed envelope ($v_{\text{applied}} \le v_{\text{safe}}$). |
| **Firmware Watchdog Timeout** | `LocalVehicleSafetyGovernor` ($1.0\text{ s}$) | Denial of Service (DoS) / RF Jamming | Halts vehicle ($v_{\text{command}} = 0.0\text{ m/s}$) if RF link is suppressed. |

---

## 3. Explicit Vulnerability & Attack Surface Register

The following vulnerabilities exist in the current prototype and represent the honest security boundary:

1. **Monotonic Sequence Spoofing:**
   - A malicious actor transmitting an unencrypted 433 MHz RF packet with the correct vehicle ID (`TRUCK_02`) and a sequence number *greater* than the latest observed sequence could spoof a `STOP` or `EMERGENCY` state (causing a nuisance halt) or attempt to report `NORMAL`.
   - **Mitigation by Physics Governor:** Even if a spoofed packet claims `NORMAL`, the local vehicle safety governor independently computes $v_{\text{safe}}$ from onboard sensors and clamps the actuator. An attacker **cannot force an over-speed collision** via RF injection.
2. **Denial-of-Service / RF Jamming:**
   - High-power continuous carrier jamming at 433 MHz will suppress LoRa packet reception.
   - **System Response:** Safe fallback. Loss of beacons triggers `COMM_LOSS` (headway expansion), and command loss triggers watchdog expiry (`EMERGENCY_STOP`). The vehicle halts rather than running away.
3. **Eavesdropping:**
   - All telemetry and beacon packets are transmitted in plaintext ASCII over LoRa and Wi-Fi.

---

## 4. Evaluator Evidence Summary

- **Can an RF attacker inject a high-speed command to cause a runaway crash?**
  **NO.** Central commands must pass the `LocalVehicleSafetyGovernor`. The governor enforces $v_{\text{applied}} \le v_{\text{safe}}$ derived from local sensors. Physics constraints cannot be overridden by external RF messages.
- **Can an attacker replay an old `NORMAL` packet to cancel an emergency halt?**
  **NO.** Monotonic sequence validation rejects old sequence numbers, and state precedence maintains `EMERGENCY` / `STOP`.
- **Is the link cryptographically authenticated?**
  **NO.** Authenticity relies on sequence and protocol validation, not cryptographic keys.
- **Can an unauthenticated attacker cause nuisance STOP / EMERGENCY or Denial of Service?**
  **YES / POSSIBLE / NOT FULLY PROTECTED.** An attacker transmitting syntactically valid BEACON frames with valid fresh sequences can induce false halts.

### Definitive Security Boundary Conclusion
> "The local governor prevents tested forged speed commands from exceeding the physics-based safe-speed ceiling, but RF message authenticity is not cryptographically protected and nuisance/availability attacks remain possible."
