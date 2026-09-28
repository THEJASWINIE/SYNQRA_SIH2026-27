# Task 1 / Task 2 Integration — Transport Decision (TECH-001)

**Specification Citation:** `docs/FOG_ORCHESTRATOR_Task1_HMI_Requirements.pdf` §10  
**Baseline Status:** Planning Baseline v1.9 (frozen). Governed by `requirements/DECISIONS.md`.  
**Status:** **PROVISIONAL EVALUATION — PENDING AUTHORITATIVE CONFIRMATION**

---

> [!IMPORTANT]
> **TECH-001 STATUS: PENDING FINAL TASK 2 CONFIRMATION**  
> This document records the candidate evaluation and architectural recommendation for the Task 1 / Task 2 integration transport. **The final choice is NOT finalized.**  
> - **Recommended Candidate:** WebSocket (based on current Task 1 HMI browser requirements).  
> - **Final Transport Selection:** Pending integration-team and Task 2 team confirmation.  
> - **Endpoint URI:** Pending.  
> - **Wire Framing Protocol:** Pending.  
> - **Do not treat this recommendation as a finalized decision.**

---

## 1. Transport Candidates Enumerated in the Specification

`docs/FOG_ORCHESTRATOR_Task1_HMI_Requirements.pdf` §10 enumerates three candidate transport categories for Task 1 / Task 2 boundary integration:

1. **WebSocket** (`ws://` / `wss://`)
2. **MQTT** (over WebSocket for browser clients)
3. **Local Message Bus / IPC**

---

## 2. Comparative Evaluation Matrix

| Criterion | WebSocket | MQTT over WebSocket | Local Message Bus / IPC |
|---|---|---|---|
| **Browser Native Client** | **Native** (`WebSocket` API, 0 runtime dependencies) | Requires client library (`mqtt.js` / `paho-mqtt`) | **Not accessible** from web browser runtime |
| **Push Cadence (1 Hz Telemetry)** | High efficiency, low framing overhead per frame | High efficiency, topic routing overhead | High efficiency (local memory/sockets) |
| **Bi-directional Capability** | **Full duplex** (inbound telemetry + advisory acknowledgement) | Pub/sub (publish to ack topic) | Full duplex |
| **Infrastructure Footprint** | Direct connection to backend / Task 2 endpoint | Requires MQTT broker (Mosquitto/EMQX/HiveMQ) | Requires co-located process |
| **Ordering Guarantees** | Strict TCP in-order message delivery | QoS dependent (QoS 0/1/2) | Buffer/transport dependent |
| **Payload Format** | JSON / Protobuf / Binary | JSON / Protobuf / Binary | Structured structs / Protobuf |

---

## 3. Evaluation & Current Recommendation

### Recommended Candidate: **WebSocket**

Based on repository evidence and architectural constraints:

1. **Zero Client Dependencies:** The browser HMI consumes WebSocket natively without bundling external broker client libraries.
2. **Push Stream Alignment:** 1 Hz periodic batch updates (vehicles, safety, alerts, bottlenecks) map cleanly to WebSocket frames.
3. **Advisory Acknowledgement Channel:** Bidirectional channel accommodates advisory acknowledgement messages (`ALERT_ACKNOWLEDGED`) over the established connection.
4. **Transport Isolation:** `LiveDataProvider` isolates the transport behind the `LiveTransport` interface (`connect()`, `disconnect()`, `onMessage()`, `onStatus()`, `send()`). Swapping to an alternative transport (e.g. MQTT or SSE) requires changing only the transport adapter, with zero impact on screens or data normalization.

---

## 4. Reconnect & Backoff Policy (Provisional)

For live network resilience (HMI-NFR-004, HMI-NFR-012), `LiveDataProvider` implements provider-level exponential backoff with configurable parameters:

- **Initial Delay:** 1 000 ms
- **Max Delay:** 30 000 ms
- **Backoff Multiplier:** 1.5×
- **Random Jitter:** 0.8× – 1.2× (prevents synchronized reconnect stampedes)
- **Max Retries:** Configurable (defaults to unlimited in production; configurable in tests)
- **Degraded Presentation:** On transport drop, `ConnectionStatus` transitions to `RECONNECTING`, previously received data ages into `STALE`, and the status bar displays `DEGRADED` (NFR-012).

---

## 5. Architectural Boundary & Encapsulation

```
┌─────────────────────────────────────────────────────────────┐
│ Task 2 Endpoint (Pending confirmation)                      │
└──────────────────────────────┬──────────────────────────────┘
                               │ (WebSocket / Transport Wire)
┌──────────────────────────────▼──────────────────────────────┐
│ LiveTransport (Isolated Interface)                          │
│   ├── StubLiveTransport (M12-A Foundation)                  │
│   └── WebSocketLiveTransport (M12-B Planned)                │
└──────────────────────────────┬──────────────────────────────┘
                               │ (Raw Inbound Payloads)
┌──────────────────────────────▼──────────────────────────────┐
│ LiveDataProvider (implements DataProvider)                  │
│   ├── Shared Validation (data/validate.ts)                  │
│   ├── Shared Normalization (data/normalize.ts)              │
│   └── Patch Assembly (data/patch.ts)                        │
└──────────────────────────────┬──────────────────────────────┘
                               │ (ProviderPatch)
┌──────────────────────────────▼──────────────────────────────┐
│ AppStateStore                                               │
└──────────────────────────────┬──────────────────────────────┘
                               │ (Normalized AppState)
┌──────────────────────────────▼──────────────────────────────┐
│ HMI Screens (S1–S6) — ZERO TRANSPORT AWARENESS             │
└─────────────────────────────────────────────────────────────┘
```

---

## 6. Open Items Pending Task 2 Agreement

1. **Formal Transport Confirmation:** Task 2 team sign-off on WebSocket vs MQTT.
2. **Endpoint URI Definition:** Production and staging URLs (e.g. `wss://<host>:<port>/ws/live`).
3. **Transport Wire Format:** Single envelope vs batch dictionary (see `docs/integration/data-contract.md`).
4. **Authentication / Handshake:** Handshake protocol (TLS/WSS certificates, token exchange) pending security architecture decisions.
