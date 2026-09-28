# FOG-ORCHESTRATOR 2.0 — ADAPTER INTERFACE SPECIFICATION

**Date**: 2026-08-28  
**Author**: Principal Systems Architect, Software Verification Engineer  
**Scope**: Public Python API Signatures for the 8 Integration Adapters

---

## 1. Adapter Class Signatures

### 1. `VehicleIDMapper`
- `to_twin_id(physical_id: str) -> Optional[str]`
- `to_physical_id(twin_id: str) -> Optional[str]`

### 2. `UnitConverter`
- `rpm_to_speed_mps(vehicle_id: str, rpm: float) -> Optional[float]`
- `mps_to_kmh(speed_mps: float) -> float`

### 3. `KinematicScaleAdapter`
- `physical_to_twin_speed(physical_speed_mps: float) -> Dict[str, float]`
- `twin_advisory_to_physical_speed(twin_advisory_speed_mps: float) -> float`

### 4. `IMUProcessor`
- `process(raw_imu_dict: Dict[str, Any]) -> Dict[str, Any]`

### 5. `TimeAdapter`
- `process_telemetry(raw_telemetry: Dict[str, Any]) -> Dict[str, Any]`
- `is_recommendation_expired(recommendation_timestamp: float) -> bool`

### 6. `CoordinateMapper`
- `update_pose(vehicle_id: str, speed_mps: float, yaw_rate_rads: float, dt_s: float, is_stale: bool) -> Dict[str, Any]`

### 7. `TelemetryQualityFilter`
- `filter_telemetry(telemetry: Dict[str, Any]) -> Dict[str, Any]`

### 8. `CommandAdapter`
- `translate_twin_advisory(twin_advisory: Dict[str, Any]) -> Optional[Dict[str, Any]]`
- `process_vehicle_ack(ack_payload: Dict[str, Any]) -> Dict[str, Any]`
