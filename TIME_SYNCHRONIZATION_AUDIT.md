# FOG-ORCHESTRATOR 2.0 — TIME SYNCHRONIZATION AUDIT (AUDIT PART 5)

**Date**: 2026-08-28  
**Author**: Principal Systems Architect, Distributed Systems Engineer  
**Scope**: Clock Alignment, Timestamp Authority, and Time Synchronization Strategy between Phase 1 Hardware and Phase 2 Digital Twin

---

## 1. Existing Timestamp Audit

| Layer | Timestamp Format | Clock Source | Resolution | Drift Profile |
|-------|------------------|--------------|------------|---------------|
| **ESP32 Firmware** | Relative `millis()` | Internal hardware timer | $1.0\text{ ms}$ | Crystal drift ($\approx \pm 20\text{ ppm}$) |
| **LoRa Gateway** | Relative `millis()` + Arrival | Internal gateway clock | $1.0\text{ ms}$ | Independent crystal oscillator |
| **HMI Backend** | POSIX Epoch (float seconds) | Host system NTP clock | $< 0.1\text{ ms}$ | NTP synchronized |
| **Digital Twin Simulator** | Simulation time $t_{\text{sim}}$ (float seconds from $0.0$) | Discrete timestep loop ($\Delta t = 0.1\text{s}$) | $100\text{ ms}$ | Deterministic simulation clock |

---

## 2. Synchronization Strategy Options Evaluation

- **Option A: Pure Real-Time Clock**: Force Digital Twin to run locked to wall-clock NTP time. Difficult if optimization cycles require variable computation time.
- **Option B: Simulation Timestep Driven**: Force physical hardware to pause for simulation steps. Impossible with physical vehicles.
- **Option E: Hybrid Time Synchronization (RECOMMENDED)**:
  - **Timestamp Authority**: HMI Backend Host System NTP clock (`now = time.time()`).
  - **Hardware Telemetry**: Gateway serial reader attaches host POSIX timestamp upon packet arrival.
  - **Digital Twin Sync**: Digital Twin maintains a monotonic wall-clock offset ($\Delta T_{\text{offset}} = T_{\text{host}} - t_{\text{sim}}$) allowing real-time telemetry matching while retaining discrete physics step evaluation.

---

## 3. Synchronization Thresholds & Authority Rules

1. **Timestamp Authority**: HMI Backend host clock is the authoritative timekeeper for physical telemetry.
2. **Sequence Numbers**: Sequence numbers (`SEQ=1, 2, 3...`) are tracked per vehicle to detect out-of-order or duplicate packets regardless of clock jitter.
3. **Stale Data Threshold**: Telemetry older than $3.0\text{ seconds}$ is flagged `STALE`. Telemetry older than $10.0\text{ seconds}$ is flagged `OFFLINE`.
4. **Max Acceptable Integration Latency**: End-to-end integration latency budget $T_{E2E} \le 50.0\text{ ms}$.
