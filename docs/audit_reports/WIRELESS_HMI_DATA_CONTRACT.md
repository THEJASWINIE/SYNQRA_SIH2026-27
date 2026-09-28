# FOG-ORCHESTRATOR 2.0 — WIRELESS HMI DATA CONTRACT SPECIFICATION

**Date**: 2026-08-29  
**Author**: Backend Engineer, Industrial HMI Integration Engineer  
**Scope**: REST API Specification for `POST /api/hardware/telemetry`

---

## 1. Ingestion Endpoint Specification

- **Endpoint**: `POST /api/hardware/telemetry`
- **Content-Type**: `application/json`

### Request JSON Schema:

```json
{
  "vehicle_id": "TRUCK_01",
  "sequence": 28,
  "rpm": 240.0,
  "speed": null,
  "ax": -496,
  "ay": 132,
  "az": 16696,
  "gx": 703,
  "gy": 342,
  "gz": 191,
  "rssi": -78,
  "snr": 9.75,
  "source": "DIRECT_WIFI",
  "timestamp": 1787935000.125
}
```

---

## 2. Source Values & Priority Rules

- **`DIRECT_WIFI`**: Direct Wi-Fi telemetry packet sent straight to HMI backend.
- **`V2V_VIA_TRUCK_02`**: Relayed V2V packet received by `TRUCK_02` and forwarded to HMI backend.

---

## 3. Response JSON Schema (200 OK)

```json
{
  "status": "ACCEPTED",
  "vehicle_id": "TRUCK_01",
  "sequence": 28,
  "source": "DIRECT_WIFI",
  "is_duplicate": false,
  "communication_status": "ONLINE"
}
```
