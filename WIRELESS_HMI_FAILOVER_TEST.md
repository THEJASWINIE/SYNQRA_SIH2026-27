# FOG-ORCHESTRATOR 2.0 — WIRELESS HMI FAILOVER TEST REPORT

**Date**: 2026-08-29  
**Author**: Distributed Systems Test Engineer, Wireless Network Integration Engineer  
**Scope**: Software Verification of Dual Wi-Fi Direct and Redundant LoRa V2V Failover Scenarios (A..E)

---

## 1. Failover Scenario Test Matrix

| Scenario | Network State | Expected Behavior | Measured Result | Status |
|----------|---------------|-------------------|-----------------|--------|
| **Scenario A** | A Wi-Fi ON, B Wi-Fi ON, A LoRa ON | Both `ONLINE`; Duplicate `(TRUCK_01, seq)` deduplicated | Both `ONLINE`; Duplicate rejected (`is_duplicate: True`) | **PASS** |
| **Scenario B** | A Wi-Fi OFF, B Wi-Fi ON, A LoRa ON | A observable via `V2V_VIA_TRUCK_02`; B `ONLINE` | A source = `V2V_VIA_TRUCK_02`; B `ONLINE` | **PASS** |
| **Scenario C (Critical)** | **Vehicle B Completely OFF** | **A DIRECT_WIFI -> HMI; B becomes OFFLINE** | **A ONLINE; B OFFLINE (Critical Failover PASS)** | **PASS** |
| **Scenario D** | B Wi-Fi OFF, B LoRa ON | A DIRECT_WIFI -> HMI; V2V active independently | A ONLINE via DIRECT_WIFI; B Wi-Fi down | **PASS** |
| **Scenario E** | A Wi-Fi ON, B Wi-Fi ON, A LoRa OFF | Both individually `ONLINE`; V2V path unavailable | Both `ONLINE` via DIRECT_WIFI | **PASS** |

---

## 2. Failover Architecture Summary

1. **Path Independence**: Loss of Vehicle B (`TRUCK_02`) has zero adverse effect on Vehicle A (`TRUCK_01`) direct Wi-Fi ingestion.
2. **Redundant Failover**: If `TRUCK_01` direct Wi-Fi is temporarily obstructed, its telemetry seamlessly reaches the HMI via `TRUCK_02` V2V relay.
