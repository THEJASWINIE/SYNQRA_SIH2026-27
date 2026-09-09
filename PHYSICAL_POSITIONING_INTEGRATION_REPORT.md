# PHYSICAL POSITIONING INTEGRATION REPORT

---

## 1. HARDWARE CAPABILITY DISCOVERY ASSESSMENT

A full codebase and hardware integration audit was performed prior to implementation:

1. **TRUCK_01 Physical Hardware**:
   - MCU: ESP32 Dual-Core MCU (Wi-Fi 802.11 b/g/n)
   - Sensors Installed: LM393 Speed/Slot Sensor (wheel RPM via ISR), MPU6050 6-DOF IMU ($a_x, a_y, a_z$ accel & $g_x, g_y, g_z$ gyro), Wi-Fi RSSI.
   - **GNSS/GPS Receiver**: **NOT PRESENT / NOT VERIFIED**.
2. **TRUCK_02 Physical Hardware**:
   - MCU: ESP32 Dual-Core MCU
   - Sensors Installed: MPU6050 6-DOF IMU, Wi-Fi RSSI, PWM motor feedback.
   - **GNSS/GPS Receiver**: **NOT PRESENT / NOT VERIFIED**.
3. **Repository Truth & Constraints**:
   - `telemetry_ingest.py` lists `position_s` under `NEVER_FROM_HARDWARE`.
   - `hardwareTelemetry.ts` and `vehiclePosition.ts` document that prototype hardware carries no GNSS receiver.
   - `PhysicalVehiclePositionProvider` returns `position: null` with `NO_PHYSICAL_POSITION_REASON`.

### Assessment Status Summary
- **PHYSICAL POSITIONING HARDWARE**: **NOT PRESENT / NOT VERIFIED**
- **SOFTWARE POSITIONING SUPPORT**: **IMPLEMENTED / READY**
- **S1 LIVE MARKER**: **UNAVAILABLE UNTIL REAL POSITION SOURCE IS CONNECTED**

---

## 2. FINAL POSITION PROVENANCE RULES COMPLIANCE

1. **Coordinates vs Provenance**: Coordinates (`latitude`, `longitude`, `status`, `timestamp`) and Provenance metadata (`transport`, `origin`, `received_at`, `quality`, `is_simulated`) are strictly separate structures.
2. **Physical Provenance Chain**: A position is classified as `PHYSICAL` **only** when its provenance chain traces to a verified physical hardware sensor.
3. **`position_source="GNSS"` is Not Proof**: `position_source="GNSS"` alone does NOT imply physical hardware origin (e.g. simulated or emulated GNSS payloads remain `SIMULATION` / `EMULATED`).
4. **Trusted Transport + Provenance**: Physical classification requires trusted hardware transport (`DIRECT_WIFI`, `V2V`, `SERIAL_GATEWAY`) AND `is_simulated == False` AND `origin == Source.HARDWARE`.
5. **V2V Relay Provenance Preservation**: V2V-relayed coordinates preserve the original remote vehicle's `origin` and `source` metadata.
6. **Synthetic Test Payload Labeling**: All synthetic/manual test payloads remain explicitly labeled `SOFTWARE-ONLY / SYNTHETIC INPUT`.
7. **VALID**: Current valid fix.
8. **STALE**: Previously valid fix retained with explicit `STALE` visual indication.
9. **INVALID**: Newly received malformed/out-of-bound coordinate rejected without overwriting a previously valid coordinate.
10. **UNAVAILABLE**: No usable position fix exists (`position = null`).
11. **Dual Timestamps**: Preserves both `position_timestamp` (GNSS fix timestamp) and `received_at` (backend arrival epoch).
12. **Zero Fabricated Coordinates**: Absolute prohibition on generating coordinates from wheel RPM, map center, OSM centroid, synthetic mine geometry, hard-coded truck locations, or simulation state in LIVE mode.

---

## 3. FIRST-CLASS SOFTWARE CONTRACT ARCHITECTURE

### Ingestion Contract (`telemetry_ingest.py`)
```json
"position_gnss": {
  "latitude": 18.6812,
  "longitude": 81.1855,
  "source": "GNSS",
  "status": "VALID",
  "timestamp": 1770000000.0,
  "received_at": 1770000001.2,
  "origin": "HARDWARE",
  "transport": "DIRECT_WIFI"
}
```

### Digital Twin State Projection (`twin_projection.py`)
`position_gnss` is included in `VEHICLE_PROJECTION_FIELDS` and projected under the `dynamic` vehicle envelope.

### Frontend Provider (`vehiclePosition.ts`)
`PhysicalVehiclePositionProvider` checks `vehicle.positionGnss`. When valid WGS84 coordinates exist:
- `position = { lat, lon }`
- `provenance = "PHYSICAL"`
- `reason = "Physical GNSS fix"`

When `positionGnss` is absent or invalid:
- `position = null`
- `provenance = "UNAVAILABLE"`
- `reason = "No positioning hardware on this vehicle. Position is never derived from wheel RPM."`

---

## 4. VERIFICATION EVIDENCE

- **Frontend Unit Tests (`vitest`)**: Passed 47 test files (1,270 tests).
- **TypeScript Check (`tsc`)**: Passed clean (`npx tsc --noEmit` exited 0).
- **Backend Tests (`pytest`)**: Passed 651 tests (1 skipped).

---

## 5. PHYSICAL E2E POSITIONING RESULT

**PHYSICAL E2E POSITIONING**: **NOT VERIFIED — HARDWARE UNAVAILABLE**
(No physical GNSS hardware module was connected during this test run. All software contracts for ingestion, twin state, and frontend positioning are fully implemented and verified with software unit tests.)
