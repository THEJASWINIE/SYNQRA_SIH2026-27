"""
FOG-ORCHESTRATOR 2.0 — Authoritative Environmental / Weather Station Ingestion Service (Root Proxy).
"""

import sys
import os

_backend_app = os.path.join(os.path.dirname(__file__), "SYNQRA_SIH2026-27-HMI", "backend", "app")
if _backend_app not in sys.path:
    sys.path.insert(0, _backend_app)

from weather_service import (
    FogCondition,
    get_fog_factor,
    fog_to_visibility_m,
    fog_to_condition,
    condition_to_fog,
    compute_fog_v_safe,
    EnvironmentalState,
    VehicleCalibration,
    VehicleGovernorReport,
    DEFAULT_VEHICLE_CALIBRATIONS,
    load_calibrations,
    FogInjectionRequest,
    CausalAuditEvent,
    WeatherStationService,
)

__all__ = [
    "FogCondition",
    "get_fog_factor",
    "fog_to_visibility_m",
    "fog_to_condition",
    "condition_to_fog",
    "compute_fog_v_safe",
    "EnvironmentalState",
    "VehicleCalibration",
    "VehicleGovernorReport",
    "DEFAULT_VEHICLE_CALIBRATIONS",
    "load_calibrations",
    "FogInjectionRequest",
    "CausalAuditEvent",
    "WeatherStationService",
]
