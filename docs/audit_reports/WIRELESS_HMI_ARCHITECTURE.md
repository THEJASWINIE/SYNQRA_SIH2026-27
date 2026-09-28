# FOG-ORCHESTRATOR 2.0 — WIRELESS VEHICLE ↔ HMI ARCHITECTURE

**Date**: 2026-08-29  
**Author**: Principal Systems Architect, Wireless Network Integration Engineer  
**Scope**: Software-Only Dual Wi-Fi Direct & Redundant LoRa V2V Telemetry Ingestion Architecture

---

## 1. Network Topology & Redundancy Model

```text
NORMAL OPERATION:
┌──────────┐    LoRa V2V     ┌──────────┐    Wi-Fi Direct    ┌──────────┐
│ TRUCK_01 │ ──────────────> │ TRUCK_02 │ ─────────────────> │   HMI    │
└────┬─────┘                 └──────────┘                    └────▲─────┘
     │                                                            │
     └────────────────────── Wi-Fi Direct ────────────────────────┘

FAILOVER OPERATION (TRUCK_02 Unavailable):
┌──────────┐                 ┌──────────┐                    ┌──────────┐
│ TRUCK_01 │ ─── (UNAVAIL) ─>│ TRUCK_02 │                    │   HMI    │
└────┬─────┘                 └──────────┘                    └────▲─────┘
     │                                                            │
     └────────────────────── Wi-Fi Direct ────────────────────────┘
```

---

## 2. Ingestion & Source Priority Protocol

1. **`TRUCK_01` Primary Source**: `DIRECT_WIFI` (Direct connection from Vehicle A to HMI access point).
2. **`TRUCK_01` Redundant Source**: `V2V_VIA_TRUCK_02` (Relayed through Vehicle B LoRa receiver to HMI).
3. **`TRUCK_02` Primary Source**: `DIRECT_WIFI` (Direct connection from Vehicle B to HMI access point).

---

## 3. Frame Deduplication Rule

- **Deduplication Key**: `(vehicle_id, sequence)`
- When duplicate frames arrive over both `DIRECT_WIFI` and `V2V_VIA_TRUCK_02`, the HMI backend updates metadata (e.g. recording available paths) while preserving a single canonical vehicle state record.
