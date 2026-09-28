# 15_FINAL_PROBLEM_AUDIT.md (FINAL_PROBLEM_AUDIT.md)
## FOG-ORCHESTRATOR 2.0 — Comprehensive Problem & Defect Forensic Register
**Date / Timestamp:** 2026-09-27T09:48:00+05:30  
**Evaluator Role:** Principal Software Architect, Senior Safety-Critical Systems Engineer, Embedded Systems Lead  
**Absolute Principle:** NO FABRICATION — Full Defect Disclosures & Verification Requirements

---

### PROBLEM P-001
- **TITLE:** Permanent Odometry Latch-up on Disconnect Gap ($dt > 10.0\text{ s}$)
- **LAYER:** Telemetry Ingestion / Backend Odometry Integration
- **SYMPTOM:** When telemetry packets resume after a $>10\text{ s}$ pause, odometry calculations permanently fail with repeating warnings and remain locked in `STALE` status forever.
- **REPRODUCTION STEPS:**
  1. Boot backend and connect Vehicle A over Wi-Fi (`192.168.137.43`).
  2. Transmit 10 packets, then pause or disconnect for 15 seconds.
  3. Resume transmission at 2 Hz.
- **EXPECTED:** The first packet after resumption is flagged as a time gap; reference timestamp is updated; subsequent packets resume valid differential odometry.
- **ACTUAL:** Every subsequent packet is rejected with `Invalid dt=110.615... dt=112.616...` and odometry never recovers.
- **RAW EVIDENCE:** Log lines 216–225 in `task-5016.log` / `results/02_backend_startup.log`:
  ```text
  Invalid dt=110.615 for odometry update on TRUCK_01
  Invalid dt=112.616 for odometry update on TRUCK_01
  Invalid dt=114.620 for odometry update on TRUCK_01
  Invalid dt=116.620 for odometry update on TRUCK_01
  Invalid dt=118.668 for odometry update on TRUCK_01
  ```
- **ROOT CAUSE:** In `integration_adapters/wheel_imu_odometry.py:92-95`, the function returns `self.snapshot(status="STALE")` when $dt > 10.0$ **without** setting `self.last_timestamp = timestamp`. Because `self.last_timestamp` is never advanced, all future packets calculate $dt$ against the ancient pre-disconnect timestamp.
- **SEVERITY:** **P1**
- **SAFETY IMPACT:** Vehicle localization and dead-reckoning permanently fail after any wireless hiccup or tunnel transit.
- **AFFECTED COMPONENTS:** `integration_adapters/wheel_imu_odometry.py`, `app.routers.hardware`
- **PROPOSED FIX:** Advance `self.last_timestamp = timestamp` and reset `self.last_pulse_count` on gap detection before returning snapshot.
- **FIX IMPLEMENTED:** Pending implementation in next sprint.
- **RETEST RESULT:** OPEN

---

### PROBLEM P-002
- **TITLE:** Operator HMI 401 Unauthorized Polling Loop on Cold Page Mount
- **LAYER:** Frontend / Backend Authentication Handshake
- **SYMPTOM:** Backend logs are flooded with repeating `401 Unauthorized` responses at ~2 Hz when `/truck01.html` is open.
- **REPRODUCTION STEPS:**
  1. Open browser to `http://localhost:5173/truck01.html`.
  2. Observe uvicorn console output.
- **EXPECTED:** Frontend acquires or presents an active session token before querying `/api/operator/context`.
- **ACTUAL:** Frontend queries `/api/operator/context` unconditionally without an `Authorization` header, generating hundreds of 401 errors.
- **RAW EVIDENCE:** Backend logs lines 16–123 in `task-5016.log`:
  ```text
  INFO: 127.0.0.1:53809 - "GET /api/operator/context HTTP/1.1" 401 Unauthorized
  ```
- **ROOT CAUSE:** `useVehicleStore.ts` does not check for an existing session token in `localStorage` or execute an initial anonymous login handshake (`POST /api/operator/session`) before launching its polling interval.
- **SEVERITY:** **P2**
- **SAFETY IMPACT:** Operator context (current shift, assigned haul route, driver ID) remains unpopulated in the UI.
- **AFFECTED COMPONENTS:** `SYNQRA_SIH2026-27-HMI/frontend/src/hooks/useVehicleStore.ts`
- **PROPOSED FIX:** Wrap the polling interval in a session token check, initiating `/api/operator/session` on mount.
- **FIX IMPLEMENTED:** Pending implementation.
- **RETEST RESULT:** OPEN

---

### PROBLEM P-003
- **TITLE:** Auxiliary ESP32 (COM14) Flash Partition Hash Failure & Infinite Bootloop
- **LAYER:** Embedded Hardware / Firmware Bootloader
- **SYMPTOM:** Auxiliary node connected to workstation via CH9102 USB-to-UART bridge fails to boot into application code.
- **REPRODUCTION STEPS:**
  1. Connect to COM14 at 115200 baud.
  2. Observe bootloader console output.
- **EXPECTED:** ESP32 boots into flashed application firmware and begins initialization.
- **ACTUAL:** Bootloader reports invalid image hash and restarts in a continuous crash loop.
- **RAW EVIDENCE:** Captured COM14 serial trace:
  ```text
  E (338) esp_image: Image hash failed - image is corrupt
  E (338) boot: OTA app partition slot 0 is not bootable
  E (338) esp_image: image at 0x150000 has invalid magic byte (nothing flashed here?)
  E (344) boot: OTA app partition slot 1 is not bootable
  E (349) boot: No bootable app partitions in the partition table
  rst:0x3 (SW_RESET),boot:0x13 (SPI_FAST_FLASH_BOOT)
  ```
- **ROOT CAUSE:** Previous flash operation was truncated or written to an incompatible partition offset.
- **SEVERITY:** **P1**
- **SAFETY IMPACT:** Node is completely unusable for physical HIL or vehicle emulation until reflashed.
- **AFFECTED COMPONENTS:** Hardware Node COM14 (`USB\VID_1A86&PID_55D4\5B53023552`)
- **PROPOSED FIX:** Perform full chip erase and reflash clean binary via `arduino-cli` or `esptool.py`.
- **FIX IMPLEMENTED:** Pending bench flash operation.
- **RETEST RESULT:** OPEN

---

### PROBLEM P-004
- **TITLE:** Standalone Speed Calibration Sketches Omit Effective Calibration $K=34.58$
- **LAYER:** Firmware / Calibration Harness
- **SYMPTOM:** Tachometer speed measured with standalone calibration sketch differs by $17.67\%$ (Vehicle A) and $19.58\%$ (Vehicle B) from speed reported by production firmware.
- **REPRODUCTION STEPS:**
  1. Inspect `esp32_code/VEHICLE_SPEED_CALIBRATION/VEHICLE A/.../VEHICLE_SPEED_CALIBRATION.ino`.
  2. Compare formula with `esp32_code/sketch_aug26a/sketch_aug26a.ino`.
- **EXPECTED:** Both sketches utilize the same canonical calibration constant ($K=34.58$).
- **ACTUAL:** Calibration sketch calculates RPM using raw `PPR = 42.0` (Vehicle A) and `43.0` (Vehicle B), omitting $K=34.58$.
- **RAW EVIDENCE:** Line 24 in `VEHICLE_SPEED_CALIBRATION.ino`:
  ```cpp
  #define PULSES_PER_REV 42.0f
  ```
- **ROOT CAUSE:** Calibration sketch was authored before empirical $K=34.58$ reconciliation was established and was not updated.
- **SEVERITY:** **P2**
- **SAFETY IMPACT:** Confusion during physical tachometer verification; bench tests report inconsistent speed measurements.
- **AFFECTED COMPONENTS:** `esp32_code/VEHICLE_SPEED_CALIBRATION/`
- **PROPOSED FIX:** Update `#define PULSES_PER_REV ENCODER_EFFECTIVE_PPR` with `ENCODER_EFFECTIVE_PPR 34.58f`.
- **FIX IMPLEMENTED:** Pending firmware file update.
- **RETEST RESULT:** OPEN

---

### PROBLEM P-005
- **TITLE:** Vehicle B Hardcoded Uncontrolled Forward Motion at Startup
- **LAYER:** Vehicle Firmware (Vehicle B)
- **SYMPTOM:** Vehicle B immediately drives forward at PWM 80 upon boot without waiting for dispatch command.
- **REPRODUCTION STEPS:**
  1. Power on Vehicle B with wheels resting on ground.
- **EXPECTED:** Vehicle boots into stationary standby (`speed = 0.0 m/s`, `PWM = 0`) until authorized by orchestrator.
- **ACTUAL:** Motor driver activates forward motion at PWM 80 immediately after setup.
- **RAW EVIDENCE:** Lines 45–47 in `VEHICLE_B_TRUCK_02_V2V_DIGITAL_TWIN_MOTOR.ino`:
  ```cpp
  #define CONTINUOUS_FORWARD_TEST true
  const int CONTINUOUS_TEST_PWM = 80;
  ```
- **ROOT CAUSE:** Diagnostic bench test flag was left permanently enabled in production firmware.
- **SEVERITY:** **P0 / P1 Safety Hazard**
- **SAFETY IMPACT:** Potential runaway vehicle hazard during power-up or reboot in field/pit operations.
- **AFFECTED COMPONENTS:** `esp32_code/VEHICLE_B_TRUCK_02_V2V_DIGITAL_TWIN_MOTOR/...ino`
- **PROPOSED FIX:** Set `#define CONTINUOUS_FORWARD_TEST false` by default; require explicit command downlink to initiate motion.
- **FIX IMPLEMENTED:** Pending firmware file edit.
- **RETEST RESULT:** OPEN

---

### PROBLEM P-006
- **TITLE:** Starlette TestClient Socketpair PermissionError on Windows Python 3.14
- **LAYER:** Developer Test Infrastructure / DevOps
- **SYMPTOM:** Bulk execution of `python -m pytest` fails 4 tests due to Windows socket permissions.
- **REPRODUCTION STEPS:**
  1. Run `python -m pytest` on Windows with Python 3.14.
- **EXPECTED:** All unit tests complete cleanly.
- **ACTUAL:** 4 tests fail with `PermissionError: [WinError 10013]` inside `anyio` loopback socketpair.
- **RAW EVIDENCE:** Task-5212 pytest output:
  ```text
  E PermissionError: [WinError 10013] An attempt was made to access a socket in a way forbidden by its access permissions
  4 failed, 1185 passed, 1 skipped in 19.81s
  ```
- **ROOT CAUSE:** Python 3.14 on Windows proactor event loop requires elevated privileges or dedicated port range for rapid socketpair creation when Starlette TestClient spins up multiple threads.
- **SEVERITY:** **P2**
- **SAFETY IMPACT:** CI/CD test automation failure; individual tests pass when run in isolation.
- **AFFECTED COMPONENTS:** `tests/test_master_failure_injection.py`, `tests/test_master_data_consistency.py`
- **PROPOSED FIX:** Use AsyncClient with `ASGITransport` instead of synchronous `TestClient` for FastAPI endpoint testing.
- **FIX IMPLEMENTED:** Pending test harness refactoring.
- **RETEST RESULT:** OPEN

---

### PROBLEM P-007
- **TITLE:** Pydantic V2 Deprecation Warnings on NumPy Boolean Scalar Indexing
- **LAYER:** Backend Data Models
- **SYMPTOM:** Pytest emits 29 deprecation warnings during model validation.
- **RAW EVIDENCE:** `DeprecationWarning: In future, it will be an error for 'np.bool' scalars to be interpreted as an index`.
- **ROOT CAUSE:** NumPy 2.x boolean scalar passed into Pydantic validators.
- **SEVERITY:** **P3**
- **PROPOSED FIX:** Explicitly cast boolean values using `bool(...)` in telemetry model validators.
- **STATUS:** OPEN

---

### PROBLEM P-008
- **TITLE:** Frontend Production Chunk Size Exceeding 500 kB Warning
- **LAYER:** Frontend Build Bundle
- **SYMPTOM:** `npm run build` outputs warning regarding large chunks (`MineCanvas-DFSMRKJ5.js` = 940 kB).
- **ROOT CAUSE:** Three.js and `@react-three/drei` bundled into a single synchronous chunk.
- **SEVERITY:** **P3**
- **PROPOSED FIX:** Configure `build.rollupOptions.output.manualChunks` in `vite.config.ts`.
- **STATUS:** OPEN

---

### PROBLEM P-009
- **TITLE:** LoRa Gateway Receives 0 RF Packets During Normal Direct Wi-Fi Operation
- **LAYER:** RF / Gateway Subsystem
- **SYMPTOM:** Gateway on COM11 logs `RX packets: 0 | Forwarded: 0` during active vehicle operation.
- **ROOT CAUSE:** Vehicle A firmware defaults to direct HTTP POST over Wi-Fi (`HMI_SERVER`), so it does not trigger LoRa transmissions if V2V interval is paused or Vehicle B is silent.
- **SEVERITY:** **P2**
- **SAFETY IMPACT:** Redundant RF failover channel remains idle and unverified during Wi-Fi primary operation.
- **STATUS:** OPEN

---

### PROBLEM P-010
- **TITLE:** Misrepresentation of 38.5 ms RF Airtime Component as Total System Latency
- **LAYER:** Documentation & Reporting
- **SYMPTOM:** Historical reports claimed "38.5 ms End-to-End Latency".
- **ROOT CAUSE:** 38.5 ms is strictly the LoRa PHY packet airtime for 32 bytes at SF7/125kHz, ignoring sensor sampling, MCU execution, backend solver, and mechanical motor response. Total closed-loop reaction time is ~124 ms.
- **SEVERITY:** **P2**
- **SAFETY IMPACT:** Potential underestimation of safe stopping distance if 38.5 ms was used instead of 124 ms in safety derivations.
- **STATUS:** OPEN
