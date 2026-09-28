# RF_FAILOVER_CLOSURE.md
## FOG-ORCHESTRATOR 2.0 — RF Failover Sequence Continuity Closure Report
**Authoritative Status:** P1 G1 CLOSED  
**Date / Timestamp:** 2026-09-27T12:51:00+05:30  
**Evaluator:** Principal Software Architect & Lead Embedded Engineer  
**Classification:** HARDWARE / PHYSICAL VERIFIED  

---

### 1. FAILURE SUMMARY
- **Observed Defect:** When a physical vehicle (TRUCK_01 or TRUCK_02) experienced Wi-Fi disruption or power cycling while operating at high sequence numbers (e.g., sequence 702), upon rebooting the ESP32 sequence counter restarted from 1. When the vehicle transmitted telemetry packets via the SX1278 LoRa 433 MHz link to the LoRa Gateway, the gateway faithfully forwarded them to the backend API (`POST /api/hardware/telemetry`).
- **Backend Rejection:** The backend rejected all forwarded packets with:
  ```http
  HTTP 409 Conflict
  {"status": "REJECTED_OUT_OF_ORDER", "sequence": 1, "last_sequence": 702, "message": "Sequence 1 is older than last seen 702"}
  ```
- **Operational Impact:** The vehicle entered an unrecoverable telemetry deadlock over LoRa RF failover until the backend process was manually restarted.

---

### 2. ROOT CAUSE FORENSICS
1. **Volatile Sequence Counters:** The ESP32 firmware maintained `txSequence` (LoRa V2V) and `telemetrySequence` (Wi-Fi HMI) as non-persistent C++ variables (`uint32_t`) initialized to 0 on boot.
2. **Transport Disparity:** LoRa and Wi-Fi transmissions maintained separate counters, meaning a switch from Wi-Fi to LoRa caused immediate sequence jumps or rollbacks even without a reboot.
3. **Session Agnostic Backend:** The FastAPI backend maintained a single monotonic sequence tracker (`last_sequence_by_vehicle[vid]`). It lacked the concept of a boot session epoch, preventing it from distinguishing between:
   - A legitimate reboot of the physical vehicle, vs.
   - An adversary replaying old out-of-order packets from an earlier session.

---

### 3. ARCHITECTURAL DESIGN DECISION
To comply with **Non-Negotiable Rule 2** (Preserve V2V protocol), **Rule 3** (Never fabricate telemetry), and the strict requirement that a reboot must NOT allow stale/duplicate packets to be accepted, we evaluated the candidate architectures:

- **Option A (Persistent Vehicle Sequence Counter in Flash):** Flash wear on ESP32 EEPROM/NVS on every 100 ms packet write degrades endurance. Rejected.
- **Option B (NVS Monotonic Boot/Session ID + Sequence Number):** **SELECTED AS PRIMARY.** The ESP32 increments a persistent `boot_id` in NVS flash once per boot cycle (endurance $>100,000$ reboots). The backend validates `(boot_id, sequence)` pairs.
- **Option C (Gateway Sequence Normalization):** Violates Rule 1 and Rule 5. The gateway is dumb transport infrastructure, not authoritative state manager.
- **Option D (Backend Deterministic Reboot & Session Detection):** **SELECTED AS COMPATIBILITY LAYER.** In addition to explicit `boot_id`, backend detects session resets when sequence drops to $\le 10$ after a communication silence gap of $\ge 1.5\text{ s}$ and previous sequence was $\ge 30$.

---

### 4. IMPLEMENTATION DETAILS

#### 4.1. ESP32 Firmware (`esp32_code/sketch_aug26a/sketch_aug26a.ino`)
- **NVS Persistence:** Integrated ESP32 `Preferences.h` (`synqra` namespace). Reads `boot_id`, increments by 1, and saves back to NVS on hardware initialization.
- **Unified Monotonic Sequence:** Replaced split `txSequence` and `telemetrySequence` with a unified `globalSequence`. Every packet emitted across either Wi-Fi or LoRa advances the same monotonic counter.
- **Telemetry Contract:** Added `"boot_id": <bootId>` to the JSON payload emitted by `sendLocalToHMI()`.

#### 4.2. FastAPI Backend (`SYNQRA_SIH2026-27-HMI/backend/app/main.py`)
- **Model Extension:** Added `boot_id: Optional[int] = Field(None)` to `HardwareTelemetryPayload`.
- **Session Tracking:** Added `last_boot_by_vehicle: Dict[str, int] = {}`.
- **Stale Session Protection:**
  ```python
  if payload.boot_id is not None and last_boot is not None and payload.boot_id < last_boot:
      return JSONResponse(status_code=409, content={
          "status": "REJECTED_STALE_SESSION",
          "vehicle_id": vid,
          "boot_id": payload.boot_id,
          "current_boot_id": last_boot,
          "message": f"Packet from stale session boot_id={payload.boot_id} rejected"
      })
  ```
- **Reboot Re-anchoring:** Upon detecting a higher `boot_id` or heuristic reboot pattern:
  - Clears `deduplication_store` for that vehicle.
  - Resets `last_sequence_by_vehicle[vid] = 0`.
  - Updates `last_boot_by_vehicle[vid] = payload.boot_id`.
  - Re-anchors canonical Digital Twin sequence tracking.

---

### 5. SECURITY & REPLAY IMPLICATIONS
1. **Replay Protection:** Replaying packets from earlier boot sessions (e.g. injecting `boot_id=1, sequence=702` while vehicle is on `boot_id=2`) is strictly rejected with `HTTP 409 REJECTED_STALE_SESSION`.
2. **In-Session Protection:** Within an active session, any duplicate packet is rejected with `HTTP 409 ACCEPTED_DUPLICATE` (dedup store), and any backward sequence is rejected with `HTTP 409 REJECTED_OUT_OF_ORDER`.
3. **Dual Path Protection:** Simultaneous delivery via Wi-Fi and LoRa Gateway is deduplicated using the bounded `deduplication_store`.

---

### 6. VERIFICATION EVIDENCE

#### 6.1. Automated Pytest Verification (`tests/test_rf_failover_and_safe_beacon.py`)
```bash
python -m pytest tests/test_rf_failover_and_safe_beacon.py -v
```
**Results:**
- `test_rf_failover_reboot_continuity`: **PASS** (Normal seq 702 accepted $\to$ seq 700 rejected out of order $\to$ seq 702 rejected duplicate $\to$ reboot boot_id=2 seq 1 accepted $\to$ seq 2 accepted $\to$ old session replay boot_id=1 rejected 409).
- `test_heuristic_reboot_without_explicit_boot_id`: **PASS** (Heuristic reboot re-anchoring verified).
- `test_safe_beacon_endpoint_and_recovery`: **PASS** (Full safe beacon ingestion and recovery verified).

#### 6.2. Physical Hardware Execution (`COM14` & Backend)
1. **Flash Verification:** `sketch_aug26a.ino` compiled cleanly (1,079,887 bytes) and flashed to `COM14` via `arduino-cli`.
2. **Serial Output on Reboot:**
   ```text
   ======================================
          FOG-ORCHESTRATOR 2.0
          VEHICLE A / TRUCK_01
   ======================================
   [BOOT SESSION] Persistent Boot ID: 2
   MPU6050 Initialized
   Initializing LoRa...
   LoRa SUCCESS
   ```
3. **Backend Acceptance:** Verified live hardware streaming at `http://127.0.0.1:8000/api/vehicles` re-anchored sequence numbers cleanly without 409 rejections.

**GATE 1 STATUS: CLOSED (PASS)**
