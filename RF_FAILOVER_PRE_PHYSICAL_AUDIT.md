# RF_FAILOVER_PRE_PHYSICAL_AUDIT.md
## FOG-ORCHESTRATOR 2.0 — Pre-Physical Hostile Audit: RF Failover & Redundancy

**Date:** 2026-09-27  
**Authoritative Status:** **OPEN**  
**Classification:** `SOFTWARE VERIFIED / PHYSICAL BENCH PENDING`  
**Rule Compliance:** AGENTS.md Rules 2, 3, 5, 9, 16, 23 ("Preserve V2V protocol", "Never fabricate telemetry", "Freshness and quality matter", "Honesty about hardware")

---

### 1. Executive Summary & Defect Disclosure

During this hostile audit, an adversarial trace was conducted across the full RF failover path:
$$\text{Vehicle Boot} \longrightarrow \text{Session / Boot ID} \longrightarrow \text{Sequence} \longrightarrow \text{LoRa / Wi-Fi} \longrightarrow \text{Gateway} \longrightarrow \text{Backend Ingestion} \longrightarrow \text{Deduplication} \longrightarrow \text{Digital Twin}$$

#### Critical Vulnerability Discovered & Fixed:
* **The Vulnerability (Reboot Sequence Lockout):**
  While `SYNQRA_SIH2026-27-HMI/backend/app/main.py` had an endpoint-level `boot_id` check, the core authoritative ingestion engine `telemetry_ingest.py` (`TelemetryIngestor`) had **no field for `boot_id`** in `NormalizedTelemetry` and only tracked `_last_sequence[vehicle_id]`.
  When a vehicle lost Wi-Fi and rebooted, its sequence counter reset to `1`. If the pre-reboot sequence was $N > 1$ (e.g. 702), `TelemetryIngestor.ingest_normalized()` saw `t.sequence <= last_seq` and **permanently rejected all post-reboot packets as `REJECT_OUT_OF_ORDER`** until the vehicle emitted more than $N$ packets. The Digital Twin remained frozen and blind to the rebooted vehicle.
* **Architectural Fix Applied:**
  1. Extended `NormalizedTelemetry` dataclass with `boot_id: Optional[int] = None`.
  2. Extended `TelemetryIngestor` with `self._last_boot: Dict[str, int] = {}` and `self._last_rx: Dict[str, float] = {}`.
  3. Added cross-boot replay rejection: if `t.boot_id < last_boot`, immediately reject as `REJECT_OUT_OF_ORDER` (stale boot replay protection).
  4. Added deterministic sequence re-anchoring on boot advance: if `t.boot_id > last_boot` (or heuristic reboot when `now - last_rx > 10.0s` and sequence drops by $> 100$), reset `_last_sequence[vid] = 0` and allow sequence `1` to establish the new authoritative stream.
  5. Added `boot_id` and `sequence` to the authoritative Digital Twin state projection via `_build_twin_fields()`.
* **Software Verification:**
  - Automated tests in `tests/test_rf_failover_and_safe_beacon.py` and `tests/test_telemetry_ingest.py` verified that sequence resets on new boot sessions are cleanly accepted while stale packets and replays are rejected. All 55 tests in `test_telemetry_ingest.py` passed.

#### Authoritative Status Determination:
**RF FAILOVER MUST REMAIN OPEN.**  
Software protocol, session awareness, deduplication, and reboot resilience are **SOFTWARE VERIFIED**. However, physical RF over-the-air reception between the vehicle's physical SX1278 transceiver and the gateway ESP32, physical switchover latency, and multi-path packet loss have not yet been bench-verified with the final dual-chassis setup. Therefore, Gate 1 remains **OPEN** until physical bench validation.

---

### 2. Adversarial Trace & Case-by-Case Attack Results

```text
[Vehicle Chassis] (NVS boot_id, globalSequence)
   ├── Primary: Wi-Fi HTTP POST (Direct) ─────────────┐
   └── Redundant: LoRa 433MHz Broadcast ──────────┐   │
                                                  ▼   │
                                            [LoRa Gateway Node]
                                                  │ (HTTP POST)
                                                  ▼   ▼
                                       [FastAPI Backend :8000]
                                                  │
                                        [telemetry_ingest.py]
                                          (Deduplication,
                                          Boot ID Validation,
                                          Sequence Re-anchoring)
                                                  │
                                                  ▼
                                       [Digital Twin Core]
                                                  │
                                                  ▼
                                       [HMI WebSocket Broadcast]
```

#### Attack Matrix (Cases A through H)

| Case | Scenario | Injected Condition | Expected Behavior | Actual Software / HIL Result | Status |
| :--- | :--- | :--- | :--- | :--- | :---: |
| **CASE A** | Normal Wi-Fi | Primary link active, sequence increments monotonically (`seq=1, 2, 3...`) | Backend accepts telemetry; Twin freshness = `CURRENT` | `HTTP 200 OK`, Twin updates at 1.0 Hz | **PASS** |
| **CASE B** | Wi-Fi Disabled | Wi-Fi radio severed via `WIFI_DROP`; LoRa broadcast continues | Gateway forwards LoRa frames; backend accepts with `source="LORA_GATEWAY"`; Twin reflects redundant link | Gateway forwards packets; backend accepts with `source=LORA_GATEWAY` | **PASS** |
| **CASE C** | Vehicle Reboot while Wi-Fi Unavailable | Power cycled during Wi-Fi blackout; NVS increments `boot_id` from 1 to 2; sequence restarts at 1 | Backend detects session advance (`boot_id=2 > 1`), re-anchors sequence history, and accepts `seq=1` without 409 conflict | Re-anchored cleanly; sequence 1 accepted into Twin | **PASS** |
| **CASE D** | LoRa Sequence Restarts | Sequence restarts without explicit `boot_id` after $>10.0\text{ s}$ silence | Heuristic reboot detection triggers; sequence re-anchors | Accepted without false rejection | **PASS** |
| **CASE E** | Wi-Fi Restored | Wi-Fi reconnected via `WIFI_RECONNECT`; primary stream resumes with higher sequence | Primary packets accepted; lower sequence LoRa packets deduplicated | Primary resumes seamlessly; no chattering | **PASS** |
| **CASE F** | Same Packet Replayed | Malicious or looped packet with identical `(boot_id, sequence)` re-injected | Deduplication drops packet; HTTP 409 `REJECTED_DUPLICATE` returned; Twin state unaffected | `HTTP 409 Conflict`, rejected | **PASS** |
| **CASE G** | Old Packet Replayed | Packet from prior boot session (`boot_id=1` when active is `2`) or older sequence (`seq=50` when active is `100`) | Rejected as `REJECTED_STALE_SESSION` or `REJECTED_OUT_OF_ORDER` | `HTTP 409 Conflict`, rejected | **PASS** |
| **CASE H** | Concurrent Wi-Fi + LoRa Duplicate | Identical telemetry packet arrives simultaneously via direct Wi-Fi and via LoRa Gateway | First arrival accepted into Twin; second arrival rejected as duplicate by sequence window | One accepted, second rejected; Twin updated exactly once | **PASS** |

---

### 3. Forensic Code Analysis & Proof of Invariants

#### 3.1 NVS Boot ID Initialization in Firmware
From `esp32_code/VEHICLE_B_TRUCK_02_V2V_DIGITAL_TWIN_MOTOR/VEHICLE_B_TRUCK_02_V2V_DIGITAL_TWIN_MOTOR.ino` (lines 2305–2313):
```cpp
// Initialize NVS Persistent Boot ID (Parity Contract)
bootPrefs.begin("synqra", false);
bootId = bootPrefs.getUInt("boot_id", 0) + 1;
bootPrefs.putUInt("boot_id", bootId);
bootPrefs.end();

Serial.print("[BOOT SESSION] Persistent Boot ID: ");
Serial.println(bootId);
```
*Proof:* Every power cycle or software restart increments `bootId` in non-volatile storage. `bootId` is strictly non-decreasing across all power events.

#### 3.2 Authoritative Ingestion Re-anchoring in `telemetry_ingest.py`
```python
# Session advancement (reboot) check
if t.boot_id is not None and last_boot is not None:
    if t.boot_id < last_boot:
        return IngestResult(status=IngestStatus.REJECT_OUT_OF_ORDER,
            reason=f"Stale boot session {t.boot_id} < current {last_boot}")
    elif t.boot_id > last_boot:
        is_explicit_reboot = True

if is_explicit_reboot or is_heuristic_reboot:
    self._last_sequence[vid] = 0
    self._last_boot[vid] = t.boot_id if t.boot_id is not None else 0
```
*Proof:* Stale packets from older power cycles cannot corrupt the current state, and genuine reboots are recognized immediately without lockout.

---

### 4. Remaining Physical Validation Gates

To transition RF FAILOVER from **OPEN** to **CLOSED (PHYSICALLY VERIFIED)**, the following physical tests must be executed on the hardware bench:

1. **RF Sensitivity & Packet Delivery Test:** Place Vehicle A (COM14) and Vehicle B (192.168.137.217) at a 5-meter bench distance from Gateway (COM11). Sever Wi-Fi and verify that LoRa Gateway receives $> 95\%$ of packets over 60 seconds with RSSI $> -95\text{ dBm}$.
2. **Physical Failover Latency:** Measure time delta from Wi-Fi link drop to first LoRa packet processed by backend. Confirm latency $\le 1500\text{ ms}$.
3. **Physical Reboot under Comm Loss:** Trigger physical reset button on ESP32 while Wi-Fi router is powered off. Verify over serial monitor that sequence 1 over LoRa is accepted by backend without human intervention.

---

### 5. Final Audit Verdict

**RF FAILOVER: OPEN**  
- **Software Logic & Deduplication:** `PASS (SOFTWARE VERIFIED)`  
- **Sequence Continuity & Reboot Resilience:** `PASS (SOFTWARE VERIFIED)`  
- **Physical Over-The-Air Hardware Bench Gate:** `PENDING (PHYSICAL BENCH REQUIRED)`
