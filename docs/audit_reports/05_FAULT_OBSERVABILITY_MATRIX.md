# 05 — FAULT OBSERVABILITY MATRIX
## FOG-ORCHESTRATOR 2.0 | SIH 2026-27 (Problem Statement: SIH26007)
### NMDC Bailadila Deposit-5 Low-Visibility HEMM Safety System
**Phase 9: Hardware + Software Integration**

*(See comprehensive detailed report in [docs/FAULT_OBSERVABILITY_MATRIX.md](file:///c:/Users/JAGADEESH%20M/OneDrive/Documents/SIH-2026-27/docs/FAULT_OBSERVABILITY_MATRIX.md))*

### Summary Observability Matrix
| Fault Description | Observable? | Detection Method | Detection Latency | Safe Fallback Action | Residual Risk |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Sensor Dropout** | **DETECTED** | Missing heartbeat / null check | $\le 100\text{ ms}$ | $R_{\text{eff}} = 8.0\text{ m}$ fallback ($3.52\text{ m/s}$) | Minor transient slowdown |
| **Sensor Stuck-At** | **DETECTED** (with persistence) | Window std dev ($\sigma < 0.05\text{ m}$) | $300.0\text{ s}$ | Confidence 0.60; 30% speed penalty | Unobserved during initial 300s |
| **Sensor Systematic Bias** | **NOT DETECTABLE** | Unobservable (single sensor) | $\infty$ | Clamped to $[0.5, 2000]\text{ m}$ | Plausible offset within range |
| **False Environmental Measurement** | **PARTIALLY DETECTED** | Dual-source discrepancy $>25\text{ m}$ | $\le 1000\text{ ms}$ | Fails closed: select conservative min | Identical dual condensation bias |
| **RF Channel Degradation** | **DETECTED** | RSSI/SNR & loss tracking $>25\%$ | $100\text{ ms} – 500\text{ ms}$ | State `DEGRADED`; local governor clamp | Reduced operational speed |
| **Gateway Complete Loss** | **DETECTED** | Comm timeout ($t > 1.0\text{ s}$) | $1.0\text{ s}$ | `COMMUNICATION_LOST`; reject remote | Autonomous crawl |
| **CAN / TWAI Bus Delays** | **DETECTED** | Frame age $\tau_{\text{CAN}} > 150\text{ ms}$ | $150\text{ ms}$ | Hold previous safe speed; halt if $>300\text{ ms}$| Minor transient setpoint lag |
| **Brake Actuator Delay** | **NOT DETECTABLE** | Hydraulic pressure unmeasured | Unknown | Conservative $S_{\text{base}} = 5.0\text{ m}$ buffer | Worn hydraulic seals |
| **Stale Telemetry** | **DETECTED** | Monotonic sequence & age $>1.0\text{ s}$| $\le 50\text{ ms}$ | Immediate packet rejection | Dropped packet under noise |
| **Timestamp Corruption** | **DETECTED** | Plausibility skew check $>5\text{ s}$ | $< 1\text{ ms}$ | Packet drop with error logging | Rejection if skew $>5\text{ s}$ |
