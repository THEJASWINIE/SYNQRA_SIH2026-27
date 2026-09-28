# FOG-ORCHESTRATOR 2.0 — HMI V2V PACKET LOSS TEST REPORT

**Date**: 2026-08-29  
**Author**: Distributed Systems Test Engineer, Industrial HMI Validation Engineer  
**Scope**: Controlled Software Packet Loss Sweeps (0%, 10%, 25%, 50%) and Health State Degradation Testing

---

## 1. Packet Loss Sweep Results

| Packet Loss Rate | Total Transmitted | Received | Dropped | State Stability | Freshness Timer | Health Status | Vehicle Isolation |
|------------------|-------------------|----------|---------|-----------------|-----------------|---------------|-------------------|
| **0% Loss** | 200 | 200 | 0 | **STABLE** | Active | `ONLINE` | **ISOLATED** |
| **10% Loss** | 200 | 180 | 20 | **STABLE** | Active | `ONLINE` | **ISOLATED** |
| **25% Loss** | 200 | 150 | 50 | **STABLE** | Active | `ONLINE` | **ISOLATED** |
| **50% Loss** | 200 | 100 | 100 | **STABLE** | Active ($>3.0\text{s}$) | `STALE` | **ISOLATED** |

---

## 2. Key Robustness Findings

1. **State Preservation**: When packet loss reaches 50%, last valid vehicle state is retained without garbage data corruption.
2. **Health Degradation**: Timeout logic correctly transitions health state from `ONLINE` to `STALE` ($>3.0\text{s}$) and `OFFLINE` ($>10.0\text{s}$).
3. **Vehicle Isolation**: Simulated packet loss on `TRUCK_01` has zero impact on `TRUCK_02` communication health.
