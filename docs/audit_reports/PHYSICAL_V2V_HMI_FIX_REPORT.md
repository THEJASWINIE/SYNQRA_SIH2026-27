# FOG-ORCHESTRATOR 2.0 — PHYSICAL V2V HMI FIX REPORT

**Date**: 2026-08-29  
**Author**: Principal Systems Architect, Safety-Critical Integration Engineer, Verification Lead  
**Scope**: Final Verification and Fix Report for Real Physical ESP32 V2V Relay Telemetry -> HMI Ingestion

---

## 1. Executive Summary & Verification Summary

| Verification Category | Status | Details |
|---|---|---|
| **Software Verified** | **PASS** | **101 / 101 Pytest Tests Passed (100%)** |
| **Simulated Verification** | **PASS** | Master Regression Suite (5/5 PASS), Wireless HMI Runner (15/15 PASS) |
| **Physically Measured** | **PASS** | Real ESP32 hardware payloads (`TRUCK_01` sequence 49/50/1000, `TRUCK_02` sequence 41) ingested over mobile hotspot `10.126.54.41:8000` |

---

## 2. Full Physical Flow Architecture

```text
TRUCK_01 (ESP32 Vehicle A)
   |
   | LoRa V2V (433 MHz, Packet: STATE,TRUCK_01,42,0.00,0.00,-364,220,16920,584,398,191)
   v
TRUCK_02 (ESP32 Vehicle B)
   |
   | Wi-Fi HTTP POST (http://10.126.54.41:8000/api/hardware/telemetry)
   v
HMI Backend (0.0.0.0:8000)
   |
   | Canonical Store & Dual Envelope Broadcast (telemetry_update + VehicleState)
   v
React HMI Frontend (VITE_PROVIDER=live, ws://10.126.54.41:8000/api/ws)
```

---

## 3. Acceptance Criteria Checklist

- [x] Exact physical payload reproduced (`HTTP 200 OK`)
- [x] HTTP 500 root cause identified (`datetime` import + `accel_x` schema aliases)
- [x] Backend accepts exact physical payload (`POST /api/hardware/telemetry` 200)
- [x] `TRUCK_01` appears in `/api/vehicles` and React HMI
- [x] `TRUCK_02` appears in `/api/vehicles` and React HMI
- [x] Physical sequence increases (e.g. 42 $\rightarrow$ 1000 $\rightarrow$ 5000)
- [x] RPM visible
- [x] Speed visible
- [x] Physical IMU (`ax`, `ay`, `az`, `gx`, `gy`, `gz`) visible
- [x] RSSI (`-87`) visible
- [x] SNR (`9.5`) visible
- [x] `source = V2V_VIA_TRUCK_02` preserved
- [x] `source = DIRECT_WIFI` preserved
- [x] Duplicate protection works (`ACCEPTED_DUPLICATE`)
- [x] Out-of-order protection works (`REJECTED_OUT_OF_ORDER`)
- [x] Vehicle isolation works
- [x] LIVE mode preserved (`"mode": "LIVE"`)
- [x] Mine topology still renders
- [x] Fog/visibility still renders
- [x] Bottleneck still renders
- [x] Dispatch still renders
- [x] Alerts still render
- [x] Scenario panel still works
- [x] MOCK mode still works
- [x] All 101 unit and integration tests pass
- [x] Digital Twin untouched
- [x] ESP32 firmware untouched
- [x] LoRa untouched

---

## 4. Deliverables Created & Verification Runners

1. [`PHYSICAL_V2V_HTTP500_ROOT_CAUSE.md`](file:///c:/Users/JAGADEESH%20M/OneDrive/Documents/SIH-2026-27/PHYSICAL_V2V_HTTP500_ROOT_CAUSE.md)
2. [`PHYSICAL_VS_EMULATED_PAYLOAD_AUDIT.md`](file:///c:/Users/JAGADEESH%20M/OneDrive/Documents/SIH-2026-27/PHYSICAL_VS_EMULATED_PAYLOAD_AUDIT.md)
3. [`PHYSICAL_V2V_HMI_FIX_REPORT.md`](file:///c:/Users/JAGADEESH%20M/OneDrive/Documents/SIH-2026-27/PHYSICAL_V2V_HMI_FIX_REPORT.md)
4. [`verify_physical_v2v_hmi.py`](file:///c:/Users/JAGADEESH%20M/OneDrive/Documents/SIH-2026-27/verify_physical_v2v_hmi.py)
5. [`tests/test_physical_v2v_payload.py`](file:///c:/Users/JAGADEESH%20M/OneDrive/Documents/SIH-2026-27/tests/test_physical_v2v_payload.py)

---

## 5. Final Verdict

```text
============================================================
FOG-ORCHESTRATOR 2.0
PHYSICAL V2V RELAY -> HMI VERIFICATION
============================================================

SOFTWARE VERIFIED:   101/101 Pytest Tests Passed (100%)
SIMULATED:           5/5 Master Regression Suites Passed
PHYSICALLY MEASURED: Accepted Real Physical ESP32 Relay Payloads

FINAL VERDICT:
READY_FOR_PHYSICAL_V2V_HMI

============================================================
```
