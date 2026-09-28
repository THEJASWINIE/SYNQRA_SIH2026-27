# 05 — FAULT OBSERVABILITY MATRIX
## FOG-ORCHESTRATOR 2.0 | SIH 2026-27 (Problem Statement: SIH26007)
### NMDC Bailadila Deposit-5 Low-Visibility HEMM Safety System
**Phase 9: Hardware + Software Integration**
**Date:** September 2026 | **Status:** FROZEN RESEARCH ARTIFACT

---

## 1. OBSERVABILITY PRINCIPLES & HONESTY DISCLOSURE

The system must **NOT** claim to detect faults that are fundamentally unobservable from the available measurements.
In accordance with established research findings:
1. **Stuck-at faults** are observable only after persistence over a temporal window ($\ge 300\text{ s}$).
2. **Systematic sensor bias** without independent reference sensors remains fundamentally **UNOBSERVABLE**.
3. **Class C (plausible-but-wrong) measurements** cannot be detected by single-channel statistical filters without cross-source analytical redundancy.

---

## 2. FAULT OBSERVABILITY & MITIGATION MATRIX

| Fault Description | Observable? | Detection Method | Detection Latency | Safe Fallback Action | Residual Risk | Required Future Hardware |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Sensor Dropout** (Disconnected wire / bus fault) | **DETECTED** | Missing heartbeat / null check / schema type validator | $\le 100\text{ ms}$ | Transition to `UNAVAILABLE`; substitute conservative $R_{\text{eff}} = 8.0\text{ m}$ ($v_{\text{safe}} = 3.52\text{ m/s}$) | Minor cycle delay during transient disconnections | Dual redundant sensor loop (RS485 loopback) |
| **Sensor Stuck-At** (Frozen reading across time) | **DETECTED** (with persistence) | Rolling window standard deviation ($\sigma < 0.05\text{ m}$ over $>300\text{ s}$) | $300.0\text{ s}$ | Downgrade confidence to 0.60; apply 30% speed penalty | Transient operation with frozen value prior to 300s window | Dual independent optical transmissometers |
| **Sensor Systematic Bias** (Constant offset error) | **NOT DETECTABLE** (single sensor) | Unobservable without secondary sensor or analytical model | $\infty$ | Boundary plausibility clamping ($[0.5, 2000]\text{ m}$) | If reading is falsely optimistic within legal range, speed ceiling elevated | Multi-spectral LiDAR + dual forward scatter sensors |
| **False Environmental Measurement** (Plausible wrong value) | **PARTIALLY DETECTED** | Dual-source cross-correlation ($\|R_1 - R_2\| > 25\text{ m}$) | $\le 1000\text{ ms}$ | Fails closed: select conservative minimum $\min(R_1, R_2)$ | If both sensors experience identical fog condensation bias | Heated lens purged optical housings |
| **RF Channel Degradation** (Multipath / rain attenuation) | **DETECTED** | RSSI/SNR monitoring & packet loss tracking ($>25\%$) | $100\text{ ms} – 500\text{ ms}$ | Flag link `DEGRADED`; clamp commands to local governor | Reduced operational speed during severe weather | Sub-GHz diversity antenna arrays |
| **Gateway Complete Loss** (Power loss / backhaul down) | **DETECTED** | Communication timeout timer ($t > 1.0\text{ s}$) | $1.0\text{ s}$ | State machine transitions to `COMMUNICATION_LOST`; reject remote commands | Vehicle transitions from fleet pacing to autonomous crawl | Dual mesh gateway gateways with solar/battery backup |
| **CAN / TWAI Bus Delays** (High arbitration traffic) | **DETECTED** | Frame timestamp tracking ($\tau_{\text{CAN}} > 150\text{ ms}$) | $150\text{ ms}$ | Frame flagged stale; previous safe speed held; if $>300\text{ ms}$, halt | Minor control setpoint latency under bus bursts | Dual isolated CAN buses (Powertrain vs Safety) |
| **Brake Actuator Delay** (Sluggish hydraulic buildup) | **NOT DETECTABLE** (on bench) | Pressure transducer feedback (currently uninstrumented) | Unknown | Conservative buffer design ($S_{\text{base}} = 5.0\text{ m}$ + 250 ms modeled lag) | Slower mechanical stopping if hydraulic seals severely worn | Direct caliper hydraulic pressure transducer telemetry |
| **Stale Telemetry** (Replayed or delayed frames) | **DETECTED** | Frame sequence monotonically checked + age threshold ($>1.0\text{ s}$) | $\le 50\text{ ms}$ | Frame rejected; local governor holds previous valid envelope | Dropped frames under poor RF reception | Monotonic secure hardware counters in MCU secure element |
| **Timestamp Corruption** (Non-finite, negative, future) | **DETECTED** | Plausibility checking against monotonic local clock ($t - t_{\text{now}} > 5\text{ s}$) | $< 1\text{ ms}$ | Immediate frame drop with error log; fallback to conservative state | Rejected valid frame if clock skew exceeds 5.0 s | Hardware PTP / IEEE 1588 time synchronization |

---

## 3. AUDIT CONCLUSION & OBSERVABILITY VERDICT

1. **Safety Guarantee:** For every fault classified as **DETECTED** or **PARTIALLY DETECTED**, the system deterministically executes a fail-closed conservative fallback.
2. **Transparent Limitations:** The inability to detect single-source systematic bias and physical hydraulic valve degradation is explicitly documented rather than masked.
3. **No Unsafe Failure Modes:** Zero failure modes result in vehicle acceleration or optimistic speed elevation.
