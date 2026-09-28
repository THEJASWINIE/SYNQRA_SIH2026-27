# SOFTWARE-ONLY POSITIONING TEST REPORT

---

## 1. EXECUTIVE SUMMARY & STATEMENT OF TRUTH

> "Successful synthetic GNSS injection proves the software telemetry-to-S1 positioning pipeline only. It does not prove physical GNSS hardware operation or physical vehicle location."

- **SOFTWARE POSITIONING PIPELINE**: **VERIFIED**
- **SYNTHETIC GNSS $\to$ S1**: **VERIFIED**
- **PHYSICAL GNSS HARDWARE**: **NOT PRESENT / NOT VERIFIED**
- **PHYSICAL GNSS $\to$ S1**: **NOT VERIFIED**
- **Current LIVE Vehicle Map Markers**: **UNAVAILABLE UNTIL REAL POSITION SOURCE EXISTS**

---

## 2. HARDWARE LIMITATION & SYNTHETIC TEST DESIGN

Audit of prototype vehicles TRUCK_01 and TRUCK_02 confirmed:
- No GPS/GNSS module is physically wired to either vehicle's ESP32 MCU.
- Normal hardware telemetry includes Wheel RPM (TRUCK_01), MPU6050 6-DOF IMU, and Wi-Fi RSSI.
- In normal LIVE mode with physical hardware, both vehicles strictly evaluate to `position = null` and display `POSITION UNAVAILABLE`.

To validate the backend-to-frontend positioning architecture, a deterministic software test harness (`tests/fixtures/synthetic_gnss.py`) was implemented to inject synthetic GNSS-shaped telemetry.

---

## 3. DATA PATH & PROVENANCE ISOLATION (RULES 1–10)

$$\text{Synthetic Payload} \longrightarrow \text{telemetry\_ingest.py} \longrightarrow \text{TwinStateStore} \longrightarrow \text{twin\_projection.py} \longrightarrow \text{HMI Normalize} \longrightarrow \text{PhysicalVehiclePositionProvider} \longrightarrow \text{S1 Map Marker}$$

### Strict Provenance Rules Enforced
1. **No `Source.HARDWARE`**: Synthetic input uses `is_simulated = True` and `origin = "SOFTWARE_ONLY"`.
2. **No Promotion**: Synthetic coordinates are never promoted to `Source.HARDWARE` or `provenance = "PHYSICAL"`.
3. **Frontend Resolution**: `PhysicalVehiclePositionProvider` resolves test inputs with `provenance = "SOFTWARE_ONLY_SYNTHETIC"`.
4. **S1 Visual Label**: S1 renders markers with the explicit visual label:
   $$\text{TRUCK\_01} \cdot \text{SOFTWARE TEST} \cdot \text{SYNTHETIC GNSS}$$
5. **No LIVE Fallback**: Normal LIVE mode hardware telemetry without GNSS continues to produce `position = null` (`POSITION UNAVAILABLE`).

---

## 4. TEST SUITE RESULTS (TEST CASES 1–10)

| Test Case | Description | Result | Provenance |
| :--- | :--- | :--- | :--- |
| **Test Case 1** | Valid synthetic GNSS injection (`TRUCK_01`, `TRUCK_02`) | **PASS** | `SOFTWARE_ONLY_SYNTHETIC` |
| **Test Case 2** | No-position telemetry | **PASS** | `UNAVAILABLE` |
| **Test Case 3** | Invalid latitude (`91.0`) rejected without fallback | **PASS** | `UNAVAILABLE` |
| **Test Case 4** | Invalid longitude (`181.0`) rejected without fallback | **PASS** | `UNAVAILABLE` |
| **Test Case 5** | No GNSS fix (`NO_FIX`) rejected without fallback | **PASS** | `UNAVAILABLE` |
| **Test Case 6** | Stale timestamp tracking | **PASS** | `STALE` |
| **Test Case 7** | Mode isolation (LIVE default remains `UNAVAILABLE`) | **PASS** | `UNAVAILABLE` |
| **Test Case 8** | Vehicle identity preservation (`TRUCK_01`, `TRUCK_02`) | **PASS** | Preserved |
| **Test Case 9** | Position movement ($A \to B$) | **PASS** | `SOFTWARE_ONLY_SYNTHETIC` |
| **Test Case 10** | End-to-end full pipeline assertion | **PASS** | `SOFTWARE_ONLY` |

---

## 5. AUTOMATED & MANUAL VERIFICATION EVIDENCE

- **Frontend Vitest Suite**: Passed 47 test files (1,270 tests).
- **TypeScript Check (`tsc`)**: Passed clean (`npx tsc --noEmit` exited code 0).
- **Backend Pytest Suite**: Passed 661 tests (1 skipped).
- **Manual Harness Verification (`python verify_synthetic_gnss_harness.py`)**: Passed with verdict `SOFTWARE POSITIONING PIPELINE: VERIFIED`.
