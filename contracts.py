"""
FOG-ORCHESTRATOR 2.0 — Canonical Message Architecture & Data Contracts
Source of Truth for logical messages across Digital Twin, HMI, and Hardware Interface Emulator.
"""

from typing import Dict, List, Optional, Any, Union
from pydantic import BaseModel, Field
import time
import json


class VehicleStateMessage(BaseModel):
    vehicle_id: str = Field(..., description="Unique vehicle identifier, e.g., 'TRUCK_A'")
    timestamp: float = Field(..., description="UNIX or simulation timestamp in seconds")
    position: float = Field(..., description="Position along segment in meters")
    segment_id: str = Field(..., description="Current road segment ID")
    speed_mps: float = Field(..., description="Vehicle current speed in meters per second")
    acceleration_mps2: float = Field(0.0, description="Vehicle acceleration in m/s^2")
    heading: float = Field(0.0, description="Vehicle heading angle in radians")
    mode: str = Field("traveling", description="Mode: idle, traveling, queued, loading, dumping")
    communication_state: str = Field("HEALTHY", description="Communication status: HEALTHY, DEGRADED, STALE, LOST")
    is_loaded: bool = Field(False, description="Payload status")
    total_tonnes_hauled: float = Field(0.0, description="Total tonnes hauled")


class SafetyStateMessage(BaseModel):
    vehicle_id: str = Field(..., description="Unique vehicle identifier")
    timestamp: float = Field(..., description="Simulation timestamp in seconds")
    actual_speed: float = Field(..., description="Actual applied vehicle speed (m/s)")
    v_safe: float = Field(..., description="Computed maximum safe speed ceiling (m/s)")
    h_safe: float = Field(..., description="Safe headway distance (meters)")
    risk_level: float = Field(..., description="Risk score between 0.0 (low) and 1.0 (imminent collision)")
    active_constraint: str = Field(..., description="Limiting factor: Visibility, Friction, Grade, Braking, Curve, Site speed limit")
    v_stop: float = Field(0.0, description="Stopping-limited speed (m/s)")
    v_retarder: float = Field(0.0, description="Retarder thermal speed limit (m/s)")
    v_curve: float = Field(0.0, description="Curve lateral friction speed limit (m/s)")
    v_mine: float = Field(0.0, description="Site speed limit (m/s)")
    a_dec: float = Field(0.0, description="Effective deceleration capability (m/s^2)")
    s_stop: float = Field(0.0, description="Stopping distance (m)")
    s_margin: float = Field(5.0, description="Safety stop margin (m)")
    is_safe: bool = Field(True, description="Safety condition satisfied: d_stop + s_margin <= R_effective")


class RoadStateMessage(BaseModel):
    segment_id: str = Field(..., description="Road segment identifier")
    timestamp: float = Field(..., description="Simulation timestamp in seconds")
    visibility_m: float = Field(..., description="Effective visibility in meters")
    visibility_sigma: float = Field(0.0, description="Visibility uncertainty std dev")
    friction: float = Field(..., description="Estimated surface friction coefficient mu")
    grade: float = Field(0.0, description="Road grade percentage (%)")
    capacity_vph: float = Field(..., description="Calculated road capacity in vehicles per hour")
    queue: int = Field(0, description="Number of vehicles currently on/queued on segment")
    utilization: float = Field(0.0, description="Segment utilization ratio (0.0 to 1.0)")
    safe_speed_mps: float = Field(..., description="Road segment safe speed limit (m/s)")


class BottleneckStateMessage(BaseModel):
    node_id: str = Field(..., description="Node/Intersection identifier")
    timestamp: float = Field(..., description="Simulation timestamp in seconds")
    lambda_vph: float = Field(..., description="Arrival rate in vehicles per hour")
    mu_vph: float = Field(..., description="Service rate in vehicles per hour")
    queue: int = Field(..., description="Current queue length in vehicles")
    queue_max: int = Field(10, description="Maximum queue capacity")
    utilization: float = Field(..., description="Node utilization ratio lambda / mu")
    criticality: float = Field(1.0, description="Node operational criticality factor")
    bottleneck_score: float = Field(..., description="Calculated bottleneck severity score")


class DispatchCommandMessage(BaseModel):
    command_id: str = Field(..., description="Unique command ID")
    vehicle_id: str = Field(..., description="Target vehicle ID")
    timestamp: float = Field(..., description="Issue timestamp in seconds")
    target_speed: float = Field(..., description="Target speed recommended by optimizer (m/s)")
    route_id: str = Field("", description="Assigned route ID")
    departure_time: float = Field(0.0, description="Commanded departure timestamp")
    slot_id: str = Field("", description="Reserved switchback/intersection slot ID")
    action: str = Field("TARGET_SPEED", description="Action type: TARGET_SPEED, HOLD, RELEASE, STOP, ROUTE")
    reason_code: str = Field("NOMINAL_DISPATCH", description="Optimizer decision reason code")


class HealthMessage(BaseModel):
    component_id: str = Field(..., description="Component identifier, e.g., 'VEHICLE_EMULATOR_A'")
    timestamp: float = Field(..., description="Current timestamp in seconds")
    state: str = Field("HEALTHY", description="State: HEALTHY, DEGRADED, STALE, OFFLINE, ERROR")
    latency_ms: float = Field(0.0, description="Message/processing latency in milliseconds")
    age_ms: float = Field(0.0, description="Data age in milliseconds")
    error_code: int = Field(0, description="Active error code (0 = NONE)")


class CommandAckMessage(BaseModel):
    command_id: str = Field(..., description="Acknowledged command ID")
    vehicle_id: str = Field(..., description="Vehicle ID sending ACK")
    timestamp: float = Field(..., description="ACK timestamp in seconds")
    status: str = Field("ACCEPTED", description="Status: ACCEPTED, CLAMPED, REJECTED")
    applied_speed: float = Field(..., description="Actual speed applied by local governor (m/s)")
    reason: str = Field("", description="Explanation if clamped or rejected")
