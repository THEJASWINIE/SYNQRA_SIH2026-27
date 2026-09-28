# FOG-ORCHESTRATOR 2.0 — TELEMETRY QUALITY & DATA TRUST SPECIFICATION

**Date**: 2026-08-28  
**Author**: Principal Systems Architect, Safety-Critical Integration Engineer  
**Scope**: Data Quality Classification, Trust Hierarchy, and Digital Twin State Protection

---

## 1. Quality State Definitions

- **`LIVE`**: Telemetry frame received within $< 1.0\text{s}$ age with valid sequence order (`should_update_twin: True`).
- **`DELAYED`**: Telemetry frame received between $1.0\text{s}$ and $3.0\text{s}$ age (`should_update_twin: True`).
- **`STALE`**: Telemetry age between $3.0\text{s}$ and $10.0\text{s}$ (`should_update_twin: False`).
- **`OFFLINE`**: No telemetry received for $> 10.0\text{s}$ (`should_update_twin: False`).
- **`RECOVERING`**: First telemetry packet after `STALE` or `OFFLINE` state (`should_update_twin: True`, requires 2-packet confirmation to transition to `LIVE`).
- **`INVALID`**: Malformed ASCII parsing or missing vehicle ID (`should_update_twin: False`).

---

## 2. Digital Twin Update Rule

```text
Incoming Telemetry ➔ TelemetryQualityFilter ➔ should_update_twin == True ? ➔ Update Digital Twin
                                             ➔ should_update_twin == False ? ➔ Reject Update (Maintain Last Valid State)
```
