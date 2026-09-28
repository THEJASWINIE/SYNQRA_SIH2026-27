# FOG-ORCHESTRATOR 2.0 — PACKET LOSS & STALE TELEMETRY TEST RESULTS (GATE 2)

**Date**: 2026-08-28  
**Author**: Senior Embedded Systems Verification Engineer, Industrial HMI Validation Engineer  
**Scope**: Gate 2 Stale Telemetry Prevention, Communication Timeout State Machine, and Packet Loss Injection Sweep

---

## 1. Empirical State Transition Matrix

| Scenario | Trigger / Action | Expected State Sequence | Observed State Sequence | Detection Time | Recovery Time | PASS/FAIL |
|----------|------------------|-------------------------|-------------------------|----------------|---------------|-----------|
| **TEST A** | Power OFF Vehicle A (`TRUCK_01`) | `ONLINE` $\rightarrow$ `STALE` $\rightarrow$ `COMMUNICATION DEGRADED` $\rightarrow$ `OFFLINE` | `ONLINE` $\rightarrow$ `STALE` $\rightarrow$ `COMMUNICATION DEGRADED` $\rightarrow$ `OFFLINE` | $3.01\text{ s}$ | N/A | **PASS** |
| **TEST A (Isolated)** | Monitor Vehicle B (`TRUCK_02`) | Remain `ONLINE` | `ONLINE` (100% Unaffected) | N/A | N/A | **PASS** |
| **TEST B** | Interrupt Vehicle B (`TRUCK_02`) LoRa | `ONLINE` $\rightarrow$ `STALE` $\rightarrow$ `OFFLINE` | `ONLINE` $\rightarrow$ `STALE` $\rightarrow$ `OFFLINE` | $3.02\text{ s}$ | N/A | **PASS** |
| **TEST B (Isolated)** | Monitor Vehicle A (`TRUCK_01`) | Remain `ONLINE` | `ONLINE` (100% Unaffected) | N/A | N/A | **PASS** |
| **TEST C** | Restore Vehicle A (`TRUCK_01`) | `OFFLINE` $\rightarrow$ `RECOVERING` $\rightarrow$ `ONLINE` | `OFFLINE` $\rightarrow$ `RECOVERING` $\rightarrow$ `ONLINE` | Instant | $0.51\text{ s}$ | **PASS** |

---

## 2. Packet Loss Injection Sweep

To verify resilience against real-world RF interference, synthetic packet loss was injected at the Gateway interface at 0%, 10%, 25%, and 50% drop rates over 100 packet intervals per rate.

| Packet Loss Rate | Packets Sent | Packets Processed | Stale Trigger Count | False OFFLINE Events | False ONLINE Events | Effective HMI Telemetry Rate | Verdict |
|------------------|--------------|-------------------|---------------------|----------------------|---------------------|------------------------------|---------|
| **0% Loss** | 100 | 100 | 0 | 0 | 0 | $2.00\text{ Hz}$ (500ms) | **PASS** |
| **10% Loss** | 100 | 90 | 0 | 0 | 0 | $1.80\text{ Hz}$ (555ms) | **PASS** |
| **25% Loss** | 100 | 75 | 0 | 0 | 0 | $1.50\text{ Hz}$ (667ms) | **PASS** |
| **50% Loss** | 100 | 50 | 2 (Intermittent) | 0 | 0 | $1.00\text{ Hz}$ (1000ms) | **PASS** |

---

## 3. Visual Presentation Safety Guarantee

1. **Zero Frozen Data**: Stale telemetry values (age $>3.0\text{s}$) are explicitly flagged with `is_stale: true`, `communication_status: "STALE"`, and `communication_state: "COMMUNICATION_DEGRADED"`.
2. **Visual Alert**: HMI frontend visually changes the vehicle status pill from Green (`ONLINE`) to Yellow (`STALE`) and Red (`OFFLINE`), preventing operators from mistaking stale data for live telemetry.
