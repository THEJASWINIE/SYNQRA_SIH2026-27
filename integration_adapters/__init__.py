"""
FOG-ORCHESTRATOR 2.0 — Integration Adapters Package

Provides non-destructive adapter modules bridging Phase 1 (Physical Hardware ↔ HMI)
and Phase 2 (Digital Twin ↔ Central Orchestrator) while strictly enforcing:
LOCAL SAFETY AUTHORITY > CENTRAL OPTIMIZATION.
"""

from integration_adapters.vehicle_id_mapper import VehicleIDMapper
from integration_adapters.unit_converter import UnitConverter
from integration_adapters.kinematic_scale import KinematicScaleAdapter
from integration_adapters.imu_processor import IMUProcessor
from integration_adapters.time_adapter import TimeAdapter
from integration_adapters.coordinate_mapper import CoordinateMapper
from integration_adapters.telemetry_quality_filter import TelemetryQualityFilter
from integration_adapters.command_adapter import CommandAdapter
from integration_adapters.twin_velocity_adapter import TwinVelocityAdapter

__all__ = [
    "VehicleIDMapper",
    "UnitConverter",
    "KinematicScaleAdapter",
    "IMUProcessor",
    "TimeAdapter",
    "CoordinateMapper",
    "TelemetryQualityFilter",
    "CommandAdapter",
    "TwinVelocityAdapter",
]
