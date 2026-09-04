# FOG-ORCHESTRATOR 2.0 — TIME SYNCHRONIZATION SPECIFICATION

**Date**: 2026-08-28  
**Author**: Principal Systems Architect, Distributed Systems Engineer  
**Scope**: Host Timekeeper Authority, Timestamp Formatting, and Expiration Policy

---

## 1. Integration Timestamp Payload Schema

Every telemetry frame processed by `TimeAdapter` includes:

```json
{
  "vehicle_id": "TRUCK_01",
  "sequence_number": 104,
  "source_timestamp": 1787935000.125,
  "gateway_timestamp": 1787935000.128,
  "integration_timestamp": 1787935000.130,
  "telemetry_age_seconds": 0.005,
  "is_duplicate": false,
  "is_out_of_order": false,
  "is_stale": false
}
```

---

## 2. Expiration & Timeout Policies

- **`MAX_TELEMETRY_AGE` ($3.0\text{s}$)**: Telemetry frames older than $3.0\text{ seconds}$ are flagged `is_stale: true` and rejected from updating Digital Twin state.
- **`MAX_RECOMMENDATION_AGE` ($5.0\text{s}$)**: Digital Twin advisory recommendations older than $5.0\text{ seconds}$ expire and are rejected by `CommandAdapter`.
