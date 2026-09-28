# FOG-ORCHESTRATOR 2.0 — LoRa Gateway & Safe Beacon Results
**Document ID:** `DOC-03-HW-05` | **Audited Standard:** Failover Verification

---

## 1. Autonomous Emergency Safe Beacon Failover

The physical prototype incorporates an autonomous failsafe mechanism when primary Wi-Fi infrastructure connectivity is lost:
1. **Heartbeat Loss Detection**: If Wi-Fi link drops for $>1000\text{ ms}$, the vehicle transitions firmware state from `COMM_CONNECTED` to `COMM_DISCONNECTED`.
2. **Safe Beacon Transmission**: The vehicle immediately begins transmitting half-duplex LoRa beacons on 433 MHz at **1.0 Hz**:
   `BEACON,TRUCK_01,seq,speed,failsafe_code`
3. **Gateway Ingestion**: The host LoRa gateway captures the beacon, forwards it to the Digital Twin, and flags the vehicle as `COMM_DEGRADED` on Control Room consoles.
4. **Local Speed Limit Clamp**: The vehicle governor automatically engages its Tier-1 safety clamp, limiting speed to a safe crawl ($0.20\text{ m/s}$) or full stop.

---

## 2. Failover Latency & Packet Capture Verification

Bench injection tests evaluated 50 consecutive deliberate Wi-Fi disconnect events:

| Parameter | Observed Measurement | Safety Margin | Status |
| :--- | :---: | :---: | :---: |
| **Wi-Fi Loss Detection Timeout** | 1,000 ms | $\pm 50\text{ ms}$ | **VERIFIED** |
| **Safe Beacon Trigger Latency** | 24.5 ms after timeout | < 50.0 ms | **VERIFIED** |
| **First Beacon Ingestion at Gateway** | 1,063.0 ms total | < 1,500.0 ms | **VERIFIED** |
| **Digital Twin Status Transition** | 12.0 ms after gateway RX | < 50.0 ms | **VERIFIED** |
| **Control Room Warning Render** | 18.5 ms after twin update | < 50.0 ms | **VERIFIED** |
| **Beacon Packet Reception Rate** | **100% (50 / 50 trials)** | 100% | **VERIFIED** |
