# 02_BUILD_AUDIT.md (results/01_build_audit.md)
## FOG-ORCHESTRATOR 2.0 — Build Health, Compilation & Static Verification Audit
**Date / Timestamp:** 2026-09-27T09:39:00+05:30  
**Evaluator Role:** DevOps Engineer, Embedded Systems Engineer, Backend Integration Engineer  
**Absolute Principle:** NO FABRICATION — Full Build and Compiler Findings

---

### 1. BUILD STATUS SUMMARY MATRIX

| Component | Target / Environment | Build Command | Exit Code | Result | Severity | Key Observations / Output |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **HMI Frontend** | Node.js v20+, Vite v7.3.6, TypeScript | `npm run build` (`tsc --noEmit && vite build`) | 0 | **PASS** | P3 (Info) | Clean compilation. 801 modules transformed. Chunks generated for `index.html`, `truck01.html`, `truck02.html`, `mine-cast.html`, `MineCanvas-DFSMRKJ5.js`. Large chunk warning (>500 kB) on Three.js bundles. |
| **Frontend Tests** | Vitest v2.1.9, JSDOM | `npm test` (`vitest run`) | 0 | **PASS** | None | 71/71 test files passed, 1,860/1,860 tests passed. |
| **HMI Backend** | Python 3.14, FastAPI, Uvicorn | `uvicorn app.main:app` | 0 | **PASS** | None | Server initializes cleanly on `0.0.0.0:8000`. WebSocket handler accepted, CORS configured. |
| **Backend Test Suite** | Python 3.14, Pytest 9.1.1 | `python -m pytest` | 1 | **PARTIAL** | **P2** | 1,185 passed, 4 failed, 1 skipped, 29 warnings in 19.81s. 4 failures caused by Windows `PermissionError: [WinError 10013]` in `socket.socketpair()` fallback during Starlette `TestClient` AnyIO proactor teardown on Windows Python 3.14. Tests pass when executed individually. |
| **3D Digital Twin** | Python 3.14, FastAPI | `python main.py --serve-hmi --port 8080` | 0 | **PASS** | None | Process running on PID 23832, bound to port 8080. |
| **ESP32 Firmware A** | Arduino Core for ESP32 v3.3.11 | `arduino-cli compile --fqbn esp32:esp32:esp32` | 0 | **PASS** | **P2** | Compiles with warnings. Uses deprecated `ledcAttachPin` / LEDC macros depending on Core 2.x vs 3.x. Includes `secrets.h` with hotspot configuration. |
| **ESP32 Firmware B** | Arduino Core for ESP32 v3.3.11 | `arduino-cli compile --fqbn esp32:esp32:esp32` | 0 | **PASS** | **P2** | Compiles with `CONTINUOUS_FORWARD_TEST true` hardcoded. `ENABLE_DIRECT_WIFI_TELEMETRY` disabled. |
| **LoRa Gateway** | Arduino Core for ESP32 v3.3.11 | `arduino-cli compile --fqbn esp32:esp32:esp32` | 0 | **PASS** | None | Verified compiled and flashed on physical ESP32 on COM11. |
| **Aux ESP32 (COM14)** | ESP32-WROOM-32E (CH9102) | Bootloader execution | N/A | **FAIL** | **P1** | Flash corrupted. `E (338) esp_image: Image hash failed - image is corrupt / No bootable app partitions`. Board stuck in reboot loop until reflashed. |

---

### 2. DETAILED DEFECT & WARNING LOG

#### [DEFECT B-001] Starlette TestClient Socketpair PermissionError on Windows Python 3.14
- **Layer:** Backend Unit Testing
- **Severity:** P2 (Test Harness Environmental Flaw)
- **Symptom:** `PermissionError: [WinError 10013] An attempt was made to access a socket in a way forbidden by its access permissions` in `anyio/from_thread.py` during bulk test execution.
- **Affected Tests:**
  1. `tests/test_master_data_consistency.py::TestMasterDataConsistencyPipeline::test_complete_data_chain_consistency`
  2. `tests/test_master_failure_injection.py::test_failure_01_malformed_json`
  3. `tests/test_master_failure_injection.py::test_failure_02_missing_required_field`
  4. `tests/test_master_failure_injection.py::test_failure_03_wrong_data_type`
- **Root Cause:** In Python 3.14 on Windows, `socket.socketpair()` falls back to a loopback TCP socket pair. When multiple Starlette `TestClient` instances are spawned rapidly without closing the blocking portal, ephemeral ports are exhausted or blocked by Windows Defender Firewall / Network access filtering.
- **Verification:** When tests are executed individually or with a persistent event loop fixture, all assertions pass.

#### [DEFECT B-002] Deprecation Warnings in Pydantic V2 Models
- **Layer:** Backend Data Models
- **Severity:** P3 (Deprecation / Maintenance)
- **Warning Log:** `DeprecationWarning: In future, it will be an error for 'np.bool' scalars to be interpreted as an index` across 29 test files.
- **Root Cause:** NumPy 2.x boolean scalars passed into Pydantic validators during telemetry quality checking.

#### [DEFECT B-003] Frontend Production Bundle Chunk Size Exceeded
- **Layer:** Frontend / HMI
- **Severity:** P3 (Performance Optimization)
- **Warning Log:** `dist/assets/MineCanvas-DFSMRKJ5.js (940.57 kB)` and `dist/assets/hmi-BEKPTHrF.js (499.07 kB)` exceed standard 500 kB chunk threshold.
- **Mitigation:** Dynamic imports (`import()`) for Three.js and heavy charting modules to reduce initial page load latency.

#### [DEFECT B-004] COM14 Physical Node Flash Corruption
- **Layer:** Embedded Hardware / Firmware
- **Severity:** P1 (Hardware Blocked)
- **Symptom:** ESP32 connected on COM14 outputs `E (338) esp_image: Image hash failed - image is corrupt / No bootable app partitions in the partition table` and enters infinite restart.
- **Root Cause:** Interrupted flash write or incorrect partition offset flashed previously.
- **Mitigation:** Requires full chip erase (`esptool.py erase_flash`) and complete binary re-flash before this node can participate in physical testing.

---

### 3. CLASSIFICATION BREAKDOWN

- **P0 (Blocker):** 0
- **P1 (Critical):** 1 (COM14 flash corruption)
- **P2 (Major):** 2 (Windows socketpair test suite issue, LEDC Core 3.x macro deprecations)
- **P3 (Minor/Warning):** 2 (Pydantic NumPy boolean scalar deprecation, frontend chunk sizes)
