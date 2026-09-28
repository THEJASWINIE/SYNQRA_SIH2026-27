# FOG-ORCHESTRATOR 2.0 — PHYSICAL VS TWIN SEMANTICS SPECIFICATION

**Date**: 2026-08-28  
**Author**: Principal Systems Architect, Safety-Critical Integration Engineer  
**Scope**: Semantic Boundaries & Comparison Guidelines between Physical Prototype and Mining Digital Twin

---

## 1. Core Semantic Definitions

- **WHAT THE PROTOTYPE REPRESENTS**: A real-time **Hardware-in-the-Loop (HIL) Validation Agent** proving wireless telemetry transport, LoRa gateway throughput, backend parsing, WebSocket streaming, operator command dispatch, local safety governor clamping, and ACK correlation.
- **WHAT THE DIGITAL TWIN REPRESENTS**: A full-scale **Mining Operational Simulator** modeling 165-tonne BEML BH100 heavy dumpers, spatio-temporal fog propagation ($50\text{m} \rightarrow 15\text{m}$), road surface friction ($\mu=0.60 \rightarrow 0.25$), queue accumulation ($\rho = \lambda/\mu$), and CC-MPC fleet optimization.

---

## 2. Comparison Matrix

| Dimension | Permitted Comparison? | Engineering Justification |
|-----------|------------------------|---------------------------|
| **Command Latency & RTT** | **YES** | Real-world network & serial latency valid across physical & HIL domains |
| **ACK Correlation** | **YES** | `command_id` tracking behavior identical across domains |
| **Communication Health** | **YES** | `ONLINE`, `STALE`, `OFFLINE` status valid for both physical & simulated agents |
| **Speed Reduction Ratio** | **YES** | Relative speed clamping ratio ($\frac{v_{\text{applied}}}{v_{\text{req}}}$) directly comparable |
| **Raw Mass / Momentum** | **NO (STRICT)** | $2.2\text{kg}$ prototype inertia cannot be compared to $165\text{t}$ dumper momentum |
| **Braking Distance (m)** | **NO (STRICT)** | Prototype stopping distance ($<0.5\text{m}$) differs from 165t dumper stopping distance ($>20\text{m}$) |
| **Retarder Temperature** | **NO (STRICT)** | Physical prototype uses electric DC motors, not hydraulic retarders |

---

## 3. Explicit Architecture Disclaimer

> [!IMPORTANT]
> The final architecture does **NEVER** claim:  
> *"2 kg prototype dynamics prove 165-ton dumper physics."*  
> The prototype proves **hardware execution integrity, communication health, and safety governor clamping**, while the Digital Twin computes **heavy equipment physics and fleet optimization**.
