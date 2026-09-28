# 08 — DSSS & LORA GATEWAY INTEGRATION REPORT
## FOG-ORCHESTRATOR 2.0 | SIH 2026-27 (Problem Statement: SIH26007)
### NMDC Bailadila Deposit-5 Low-Visibility HEMM Safety System
**Phase 9: Hardware + Software Integration**
**Date:** September 2026 | **Classification:** LEVEL 3 / LEVEL 4 (Hybrid Architecture)

---

## 1. ARCHITECTURAL HONESTY & CARRIER ABSTRACTION

```
[CRITICAL ARCHITECTURAL DISTINCTION]
- Physical Bench Hardware: Semtech SX1278 (Ra-02) 433 MHz LoRa transceiver.
  * Physical Modulation: Chirp Spread Spectrum (CSS).
  * Bandwidth: 125 kHz | Spreading Factor: SF7 | Coding Rate: 4/5.
- Research / Future Mining Production Architecture: Direct-Sequence Spread Spectrum (DSSS).
  * Direct pseudo-noise (PN) sequence chipping for high-density multi-gateway spatial reuse.
- Software Integration Abstraction:
  * Both physical LoRa CSS packets and simulated DSSS PN chipping frames map to a unified `CommunicationLink` object.
  * Neither the central orchestrator nor the local safety governor depends on proprietary PHY registers.
```

---

## 2. 5-LAYER GATEWAY SELECTION ARCHITECTURE

```
  ┌────────────────────────────────────────────────────────┐
  │                 1. RFHardwareAdapter                   │
  │  (Bridges SX1278 LoRa SPI packets & DSSS frame models) │
  └───────────────────────────┬────────────────────────────┘
                              │
                              ▼
  ┌────────────────────────────────────────────────────────┐
  │                 2. CommunicationLink                   │
  │     (Standardized carrier metrics: RSSI, SNR, Loss)    │
  └───────────────────────────┬────────────────────────────┘
                              │
                              ▼
  ┌────────────────────────────────────────────────────────┐
  │              3. GatewayCorrelationEngine               │
  │    (Computes normalized PN / link correlation score)   │
  └───────────────────────────┬────────────────────────────┘
                              │
                              ▼
  ┌────────────────────────────────────────────────────────┐
  │           4. GatewaySelectionStateMachine              │
  │    (Anti-flapping hysteresis, persistence counter,      │
  │     handover arbitrations, transition audit logging)   │
  └───────────────────────────┬────────────────────────────┘
                              │
                              ▼
  ┌────────────────────────────────────────────────────────┐
  │               5. SafetyOrchestratorLink                │
  │     (Presents chosen gateway & degradation state)      │
  └────────────────────────────────────────────────────────┘
```

---

## 3. SELECTION STATE MACHINE & TRANSITION RULES

### Primary States:
1. `NO_GATEWAY`: No gateway meets minimum signal/correlation threshold ($\text{corr} < 0.40$ or $\text{RSSI} < -115\text{ dBm}$), or all have timed out.
2. `CONNECTED`: Operating reliably with primary gateway ($\text{corr} \ge 0.60$ and $\text{loss} < 25\%$).
3. `DEGRADED`: Connected to gateway, but signal correlation degraded ($0.40 \le \text{corr} < 0.60$) or packet loss $\ge 25\%$.
4. `HANDOVER_PENDING`: Candidate gateway exceeds current by switch margin ($+0.15$), accumulating persistence count ($N < 3$).
5. `DISCONNECTED`: All links severed; triggers standalone vehicle safe beacon failsafe.

---

## 4. BENCHMARK & HIL VERIFICATION RESULTS

| Test Vector | Evaluated Scenario | System Response | Handover Result | Status |
| :--- | :--- | :--- | :--- | :--- |
| **Cold Start** | Boot with GW-01 emitting valid correlation ($0.85$) | Instantly selects GW-01 as primary gateway | Initialized to `CONNECTED` | **PASS** |
| **Weak Rejection** | Injected observation with correlation $0.32 < 0.40$ | Frame rejected; gateway state remains `NO_GATEWAY` | Rejected defensively | **PASS** |
| **Switch Margin** | Candidate gateway exceeds current by only $+0.08 < 0.15$ | Handover rejected; stays on current gateway | Suppressed jitter | **PASS** |
| **Persistence** | Candidate gateway exceeds current by $+0.20$ for 3 frames | `HANDOVER_PENDING` for 2 frames $\to$ switches on 3rd | Handover executed cleanly | **PASS** |
| **Anti-Flapping**| Two gateways alternating higher scores frame-by-frame | Switch counter resets each alternate frame; no flap | 0 false handovers | **PASS** |
| **Timeout Failover**| Current gateway goes silent for $1.5\text{ s}$ | Fails over immediately to alternate candidate | Seamless failover | **PASS** |

---

## 5. AUDIT TRAIL LOGGING VERIFICATION

Every gateway state transition is logged with complete audit fields:
```json
{
  "timestamp": 1727134500.32,
  "old_gateway": "GW_RAMP_01",
  "candidate_gateway": "GW_RAMP_02",
  "correlation_current": 0.68,
  "correlation_candidate": 0.89,
  "RSSI": -68.5,
  "SNR": 8.2,
  "packet_loss": 0.05,
  "reason": "Transition from HANDOVER_PENDING to CONNECTED",
  "new_state": "CONNECTED"
}
```

---

## 6. AUDIT CONCLUSION

The DSSS/LoRa gateway abstraction layer (`integration_adapters/dsss_gateway_selector.py`) successfully bridges physical bench LoRa hardware with research DSSS models, providing zero command discontinuity, robust anti-flapping protection, and fully auditable state transitions.
