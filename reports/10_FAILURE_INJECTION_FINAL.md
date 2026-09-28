# 10 — FAILURE INJECTION & FAIL-SAFE TRANSITION AUDIT REPORT

**Project:** FOG-ORCHESTRATOR 2.0 (SIH 2026-27 — SIH26007)  
**Classification:** Fault Injection & Autonomous Governor Resilience Audit  
**Dataset Reference:** [`data/failure_injection_matrix.csv`](file:///c:/Users/JAGADEESH%20M/OneDrive/Documents/SIH-2026-27/data/failure_injection_matrix.csv)  
**Date of Audit:** 2026-09-18  

---

## 1. Critical Distinction: What "<100 ms Fail-Safe" Actually Measures

> [!WARNING]
> **AUDIT CLARIFICATION ON FAIL-SAFE LATENCY**  
> Previous project statements claiming that the system "fails safe in $< 100\text{ ms}$" must be mathematically and operationally qualified:
> 
> - **WHAT IT ACTUALLY MEASURES:**  
>   The time required for the **onboard firmware / governor to detect a corrupted, stale, or severed packet and transition its internal speed command clamp to a safe target ($v_{\text{applied}} \le v_{\text{safe}}$)**. Because the governor evaluates incoming commands on a 20 Hz periodic task cycle ($50\text{ ms}$) with a sub-millisecond parsing and validation check ($< 2\text{ ms}$), command rejection and state transition occur within **$52\text{ ms}$ (well under $100\text{ ms}$)**.
> 
> - **WHAT IT DOES NOT MEASURE:**  
>   It does **NOT** mean the 165.5-tonne physical truck comes to a complete physical standstill in $< 100\text{ ms}$! Physical braking requires mechanical pressure buildup ($\sim 200\text{ ms}$) plus kinetic energy dissipation ($1.5\text{--}4.0\text{ seconds}$). Nor does it include queue clearance or traffic recovery.

---

## 2. Failure Injection Matrix (13 Modes Audited)

| Fault ID | Injected Failure Mode | Injection Method | Detection Time (s) | Firmware Fallback State | Enforced Speed Target | Invariant Preserved? |
|:---|:---|:---|:---:|:---|:---:|:---:|
| **FI-01** | **Gateway Wireless Loss** | Central LoRa beacon severed | 1.050 s | `NO_GATEWAY` | $0.00\text{ m/s}$ (Watchdog) | **PASS (I5)** |
| **FI-02** | **Wi-Fi Socket Drop** | ESP32-to-FastAPI TCP severed | 1.050 s | `NO_GATEWAY` | $0.00\text{ m/s}$ (Watchdog) | **PASS (I5)** |
| **FI-03** | **Direct V2V Link Severed** | Peer dumper beacon dropped | 0.350 s | `DEGRADED_COMMUNICATION` | Headway doubled to 100 m | **PASS (I6)** |
| **FI-04** | **Severe RF Packet Loss (90%)** | 9 out of 10 packets dropped | 0.050 s | `DEGRADED_COMMUNICATION` | $v_{\text{safe}}$ clamped locally | **PASS (I7)** |
| **FI-05** | **Stale Command Injection** | Command timestamp $\Delta t = 1.5\text{ s}$ | 0.050 s | `STALE_COMMAND` | Reject; apply local $v_{\text{safe}}$ | **PASS (I2)** |
| **FI-06** | **Duplicate Command Replay** | Rolling back command sequence | 0.050 s | `INVALID_COMMAND` | Reject; apply local $v_{\text{safe}}$ | **PASS (I3)** |
| **FI-07** | **Out-of-Order Command** | Sequence number $seq < last\_seq$ | 0.050 s | `INVALID_COMMAND` | Reject; apply local $v_{\text{safe}}$ | **PASS (I4)** |
| **FI-08** | **Malformed CRC / Bit Flip** | Injected single-bit payload error | 0.020 s | `INVALID_COMMAND` | Reject; maintain safe envelope | **PASS (I10)** |
| **FI-09** | **Excessive Speed Request** | Dispatch requests $15\text{ m/s} > 5.56\text{ m/s}$ | 0.050 s | `UNSAFE_COMMAND` (Clamped)| Clamped to $v_{\text{safe}}$ ($4.50\text{ m/s}$) | **PASS (I1)** |
| **FI-10** | **Negative / NaN Speed Float** | Injected `NaN` / `-5.0` float value | 0.050 s | `INVALID_COMMAND` | Forced to $0.00\text{ m/s}$ | **PASS (I10/I11)** |
| **FI-11** | **Optimizer Timeout / Crash** | LP solver process terminated | 1.050 s | `NO_GATEWAY` | Autonomous local governance | **PASS (I5)** |
| **FI-12** | **Backend Server Disconnect** | FastAPI server process killed | 1.050 s | `NO_GATEWAY` | Autonomous local governance | **PASS (I5)** |
| **FI-13** | **Sensor Dropout / Blackout** | Fog sensor disconnected / NaN | 0.100 s | `EMERGENCY_STOP` | Forced to $0.00\text{ m/s}$ | **PASS (I8)** |

---

## 3. Verified System Invariants

Across all 13 injected failure modes:
1. **Invariant I1 ($v_{\text{command}} \le v_{\text{safe}}$):** Never violated.
2. **Invariant I2 (Stale Invariance):** Stale or delayed packets never caused vehicle acceleration.
3. **Invariant I5 (Gateway Independence):** Total loss of gateway or cloud backend preserves vehicle local braking capability.
4. **Invariant I8 (Fail-Closed Visibility):** Loss of visibility estimation triggers immediate staging/halt.
