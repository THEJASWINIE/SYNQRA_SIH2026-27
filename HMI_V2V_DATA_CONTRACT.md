# FOG-ORCHESTRATOR 2.0 — HMI V2V CANONICAL DATA CONTRACT SPECIFICATION

**Date**: 2026-08-29  
**Author**: Industrial HMI Validation Engineer, Backend Engineer  
**Scope**: Canonical Schema Contract for V2V Telemetry Ingestion and HMI Store Representation

---

## 1. Controlled Ingestion Architecture

```text
V2V / LoRa Hardware Packet
        │
        ▼
v2v_packet_parser.py (Telemetry Ingestion Adapter)
        │
        ▼
Canonical Vehicle State (JSON Dict)
        │
        ▼
HMI Backend Store (vehicle_telemetry_store)
        │
        ├──────────────────────┐
        ▼                      ▼
WebSocket /api/ws      REST API /api/vehicles
        │                      │
        └──────────┬───────────┘
                   ▼
         Live HMI Frontend Store
```

---

## 2. Canonical Vehicle State Schema (JSON)

```json
{
  "vehicle_id": "TRUCK_01",
  "source": "V2V",
  "sequence_number": 28,
  "rpm": 240.0,
  "speed": null,
  "speed_value": 0.0,
  "speed_unit": "m/s",
  "speed_calibrated": false,
  "acceleration": {
    "x": -0.297,
    "y": 0.079,
    "z": 10.001
  },
  "gyroscope": {
    "x": 0.093,
    "y": 0.045,
    "z": 0.025
  },
  "raw_imu": {
    "ax": -496,
    "ay": 132,
    "az": 16696,
    "gx": 703,
    "gy": 342,
    "gz": 191
  },
  "communication": {
    "status": "ONLINE",
    "last_seen": 1787935000.125,
    "rssi": -78,
    "snr": 9.75,
    "latency_ms": 2.5
  },
  "communication_status": "ONLINE",
  "communication_state": "HEALTHY",
  "safety_state": "NORMAL",
  "data_quality": "LIVE",
  "stale_threshold_s": 3.0,
  "offline_threshold_s": 10.0,
  "timestamp": 1787935000.125
}
```

---

## 3. Speed Uncalibrated Semantics

Because wheel radius to linear speed calibration is intentionally postponed:
- `speed_calibrated`: Explicitly set to `false`.
- `rpm`: Primary verified physical measurement ($240.0\text{ RPM}$).
- Frontend display indicates speed measurement status as uncalibrated.
