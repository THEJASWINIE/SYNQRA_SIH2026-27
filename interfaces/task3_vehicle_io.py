"""
interfaces/task3_vehicle_io.py
------------------------------
Task-3 Vehicle Telemetry Ingestion & Supervisory Command Output Interface.
Provides bidirectional data serialization, validation, stale timestamp detection,
communication confidence monitoring, and fail-safe command synthesis.

Safety Invariants:
- High-level supervisory setpoints only: NO direct control of raw motor PWM / low-level actuators.
- Inviolable Tier-1 Governor: v_command <= v_safe
- Communication loss or stale telemetry triggers autonomous fail-safe fallback.

Evidence Tags:
- Interface Protocol: [MODEL CONFIG / TELEMETRY] Task-3 vehicle I/O specification.
- Validation: [VERIFIED / PRIMARY] Pydantic/Dataclass type & range validation.
"""

from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field, asdict
import math
import time

try:
    from pydantic import BaseModel, Field, field_validator
    PYDANTIC_AVAILABLE = True
except ImportError:
    PYDANTIC_AVAILABLE = False

try:
    from fastapi import FastAPI, HTTPException
    FASTAPI_AVAILABLE = True
except ImportError:
    FASTAPI_AVAILABLE = False



@dataclass
class IMUData:
    """3-axis accelerometer (m/s^2) and gyroscope (rad/s) readings."""
    accel_x: float = 0.0
    accel_y: float = 0.0
    accel_z: float = 9.81
    gyro_x: float = 0.0
    gyro_y: float = 0.0
    gyro_z: float = 0.0


@dataclass
class WheelSpeedData:
    """Individual wheel rotational velocities in rad/s or m/s equivalent."""
    front_left: float = 0.0
    front_right: float = 0.0
    rear_left: float = 0.0
    rear_right: float = 0.0


@dataclass
class BrakeTelemetry:
    """Service brake hydraulic pressure and engagement state."""
    pressure_bar: float = 0.0
    is_engaged: bool = False
    pedal_pct: float = 0.0


@dataclass
class RetarderTelemetry:
    """Hydrodynamic retarder absorption power and status."""
    power_kw: float = 0.0
    level_pct: float = 0.0
    temperature_c: float = 65.0


@dataclass
class VehicleTelemetryPacket:
    """
    Complete Task-3 Ingestion Telemetry Schema.
    """
    vehicle_id: str
    timestamp: float
    speed_mps: float
    acceleration_mps2: float
    position_xyz: List[float]  # [x, y, z] in local mine coordinate frame
    heading_rad: float
    grade_pct: float
    wheel_speeds: WheelSpeedData
    imu: IMUData
    brake: BrakeTelemetry
    retarder: RetarderTelemetry
    obstacle_range_m: float
    communication_confidence: float  # [0.0, 1.0]

    # Optional metadata
    road_edge_id: Optional[str] = None
    station_s: Optional[float] = None
    payload_tonnes: float = 91.5


@dataclass
class VehicleCommandPacket:
    """
    Supervisory Command-Output Schema for Task-3 Onboard Autonomy.
    Outputs high-level speed envelopes and spatial targets, NEVER raw PWM.
    """
    vehicle_id: str
    timestamp: float
    command_speed_mps: float
    safe_speed_ceiling_mps: float
    target_headway_m: float
    target_route: List[str]
    retarder_limit_kw: float
    control_mode: str  # "AUTONOMOUS_GOVERNED", "FAILSAFE_STOP", "DEGRADED_CRAWL"
    warning_alert: Optional[str] = None
    is_emergency_stop: bool = False


class TelemetryValidationError(Exception):
    """Raised when incoming telemetry violates schema bounds or data types."""
    pass


class Task3VehicleIOInterface:
    """
    Task-3 Telemetry Ingestion and Command Synthesis Engine.
    """
    def __init__(
        self,
        max_stale_age_s: float = 2.0,
        comm_loss_threshold: float = 0.20,
        failsafe_crawl_speed_mps: float = 1.50
    ):
        self.max_stale_age_s = float(max_stale_age_s)
        self.comm_loss_threshold = float(comm_loss_threshold)
        self.failsafe_crawl_speed_mps = float(failsafe_crawl_speed_mps)

        # Vehicle last known telemetry store
        self.last_telemetry: Dict[str, VehicleTelemetryPacket] = {}
        self.last_ingest_time: Dict[str, float] = {}

    def parse_and_validate_telemetry(
        self,
        raw_data: Dict[str, Any],
        current_time_s: Optional[float] = None
    ) -> Tuple[bool, Optional[VehicleTelemetryPacket], str]:
        """
        Validates incoming telemetry payload against schema, value bounds, and freshness.
        Returns: (is_valid, parsed_packet, error_or_status_message)
        """
        # 1. Mandatory field existence check
        required_fields = [
            "vehicle_id", "timestamp", "speed_mps", "acceleration_mps2",
            "position_xyz", "heading_rad", "grade_pct", "obstacle_range_m",
            "communication_confidence"
        ]
        for field_name in required_fields:
            if field_name not in raw_data:
                return False, None, f"Missing required telemetry field: '{field_name}'"

        vid = str(raw_data["vehicle_id"]).strip()
        if not vid:
            return False, None, "vehicle_id cannot be empty"

        ts = float(raw_data["timestamp"])
        spd = float(raw_data["speed_mps"])
        acc = float(raw_data["acceleration_mps2"])
        pos = raw_data["position_xyz"]
        heading = float(raw_data["heading_rad"])
        grade = float(raw_data["grade_pct"])
        obs_range = float(raw_data["obstacle_range_m"])
        comm_conf = float(raw_data["communication_confidence"])

        # 2. Value Bounds Validation
        if math.isnan(spd) or math.isinf(spd) or spd < 0.0 or spd > 25.0:
            return False, None, f"Invalid speed_mps: {spd} (must be in [0, 25] m/s)"

        if math.isnan(acc) or math.isinf(acc) or abs(acc) > 15.0:
            return False, None, f"Invalid acceleration_mps2: {acc} (must be in [-15, +15] m/s^2)"

        if not isinstance(pos, (list, tuple)) or len(pos) < 3:
            return False, None, f"position_xyz must be 3-element list [x, y, z], got: {pos}"

        for p_val in pos[:3]:
            if math.isnan(p_val) or math.isinf(p_val):
                return False, None, f"position_xyz contains NaN or Inf: {pos}"

        if math.isnan(obs_range) or math.isinf(obs_range) or obs_range < 0.0:
            return False, None, f"Invalid obstacle_range_m: {obs_range} (must be >= 0)"

        if math.isnan(comm_conf) or math.isinf(comm_conf) or comm_conf < 0.0 or comm_conf > 1.0:
            return False, None, f"Invalid communication_confidence: {comm_conf} (must be in [0.0, 1.0])"

        # 3. Freshness / Stale Timestamp Validation
        if current_time_s is not None:
            age = current_time_s - ts
            if age > self.max_stale_age_s:
                return False, None, f"Stale telemetry timestamp: age {age:.2f}s exceeds threshold {self.max_stale_age_s}s"
            if age < -10.0:
                return False, None, f"Future telemetry timestamp detected: dt = {age:.2f}s"

        # 4. Nested sub-structures parsing
        imu_dict = raw_data.get("imu", {})
        imu = IMUData(
            accel_x=float(imu_dict.get("accel_x", 0.0)),
            accel_y=float(imu_dict.get("accel_y", 0.0)),
            accel_z=float(imu_dict.get("accel_z", 9.81)),
            gyro_x=float(imu_dict.get("gyro_x", 0.0)),
            gyro_y=float(imu_dict.get("gyro_y", 0.0)),
            gyro_z=float(imu_dict.get("gyro_z", 0.0))
        )

        wheel_dict = raw_data.get("wheel_speeds", {})
        wheel = WheelSpeedData(
            front_left=float(wheel_dict.get("front_left", spd)),
            front_right=float(wheel_dict.get("front_right", spd)),
            rear_left=float(wheel_dict.get("rear_left", spd)),
            rear_right=float(wheel_dict.get("rear_right", spd))
        )

        brake_dict = raw_data.get("brake", {})
        brake = BrakeTelemetry(
            pressure_bar=float(brake_dict.get("pressure_bar", 0.0)),
            is_engaged=bool(brake_dict.get("is_engaged", False)),
            pedal_pct=float(brake_dict.get("pedal_pct", 0.0))
        )

        retarder_dict = raw_data.get("retarder", {})
        retarder = RetarderTelemetry(
            power_kw=float(retarder_dict.get("power_kw", 0.0)),
            level_pct=float(retarder_dict.get("level_pct", 0.0)),
            temperature_c=float(retarder_dict.get("temperature_c", 65.0))
        )

        packet = VehicleTelemetryPacket(
            vehicle_id=vid,
            timestamp=ts,
            speed_mps=spd,
            acceleration_mps2=acc,
            position_xyz=[float(pos[0]), float(pos[1]), float(pos[2])],
            heading_rad=heading,
            grade_pct=grade,
            wheel_speeds=wheel,
            imu=imu,
            brake=brake,
            retarder=retarder,
            obstacle_range_m=obs_range,
            communication_confidence=comm_conf,
            road_edge_id=raw_data.get("road_edge_id"),
            station_s=raw_data.get("station_s"),
            payload_tonnes=float(raw_data.get("payload_tonnes", 91.5))
        )

        # Store in cache
        self.last_telemetry[vid] = packet
        self.last_ingest_time[vid] = ts if current_time_s is None else current_time_s

        return True, packet, "VALID_TELEMETRY_INGESTED"

    def synthesize_command_output(
        self,
        vehicle_id: str,
        desired_dispatch_speed_mps: float,
        safe_speed_ceiling_mps: float,
        current_time_s: float,
        assigned_route: Optional[List[str]] = None
    ) -> VehicleCommandPacket:
        """
        Synthesize governed supervisory command output for a vehicle.
        Enforces:
        - Inviolable Tier-1 Governor: v_command = min(v_dispatch, v_safe)
        - Communication loss / stale telemetry fail-safe stop or crawl.
        """
        route = assigned_route or ["SHOVEL_01", "CRUSHER_01"]

        # Check telemetry availability and freshness
        telemetry = self.last_telemetry.get(vehicle_id)
        last_time = self.last_ingest_time.get(vehicle_id, 0.0)

        # Fail-Safe Mode 1: No Telemetry Ever Received
        if telemetry is None:
            return VehicleCommandPacket(
                vehicle_id=vehicle_id,
                timestamp=current_time_s,
                command_speed_mps=0.0,
                safe_speed_ceiling_mps=0.0,
                target_headway_m=25.0,
                target_route=route,
                retarder_limit_kw=700.0,
                control_mode="FAILSAFE_STOP",
                warning_alert="NO_TELEMETRY_DATA_AVAILABLE",
                is_emergency_stop=True
            )

        # Fail-Safe Mode 2: Stale Telemetry (Communication Lost)
        age = current_time_s - last_time
        if age > self.max_stale_age_s:
            return VehicleCommandPacket(
                vehicle_id=vehicle_id,
                timestamp=current_time_s,
                command_speed_mps=0.0,
                safe_speed_ceiling_mps=0.0,
                target_headway_m=30.0,
                target_route=route,
                retarder_limit_kw=700.0,
                control_mode="FAILSAFE_STOP",
                warning_alert=f"COMMUNICATION_LOSS_STALE_TELEMETRY (age: {age:.2f}s)",
                is_emergency_stop=True
            )

        # Fail-Safe Mode 3: Low Communication Confidence
        if telemetry.communication_confidence < self.comm_loss_threshold:
            return VehicleCommandPacket(
                vehicle_id=vehicle_id,
                timestamp=current_time_s,
                command_speed_mps=min(self.failsafe_crawl_speed_mps, safe_speed_ceiling_mps),
                safe_speed_ceiling_mps=safe_speed_ceiling_mps,
                target_headway_m=35.0,
                target_route=route,
                retarder_limit_kw=700.0,
                control_mode="DEGRADED_CRAWL",
                warning_alert=f"LOW_COMMUNICATION_CONFIDENCE ({telemetry.communication_confidence:.2f})",
                is_emergency_stop=False
            )

        # Nominal Governed Command Mode
        v_governed = min(desired_dispatch_speed_mps, safe_speed_ceiling_mps)

        # Headway based on safe stopping envelope
        h_target = max(15.52, (v_governed * 2.0) + 10.52 + 5.0)

        return VehicleCommandPacket(
            vehicle_id=vehicle_id,
            timestamp=current_time_s,
            command_speed_mps=v_governed,
            safe_speed_ceiling_mps=safe_speed_ceiling_mps,
            target_headway_m=h_target,
            target_route=route,
            retarder_limit_kw=700.0,
            control_mode="AUTONOMOUS_GOVERNED",
            warning_alert=None,
            is_emergency_stop=False
        )


class Task3VehicleIORESTApp:
    """
    Lightweight, standalone REST application fallback for Task-3 Vehicle I/O.
    """
    def __init__(self, interface: Optional[Task3VehicleIOInterface] = None):
        self.interface = interface or Task3VehicleIOInterface()
        self.title = "FOG-ORCHESTRATOR 2.0 - Task-3 Vehicle I/O API"
        self.routes: Dict[str, Any] = {
            "/health": lambda: {"status": "ok"},
            "/api/v1/telemetry/buffer": self.get_telemetry_buffer
        }

    def get_telemetry_buffer(self) -> Dict[str, Any]:
        return {
            "buffered_vehicles_count": len(self.interface.telemetry_buffer),
            "vehicle_ids": list(self.interface.telemetry_buffer.keys())
        }

    def handle_request(self, path: str, method: str = "GET", **kwargs) -> Dict[str, Any]:
        """Dispatch direct programmatic REST requests."""
        handler = self.routes.get(path)
        if not handler:
            raise KeyError(f"Endpoint '{path}' not found in Vehicle I/O API.")
        return handler(**kwargs) if kwargs else handler()


def create_task3_fastapi_app(interface: Optional[Task3VehicleIOInterface] = None) -> Any:
    """
    Factory creating the FastAPI application for Task-3 Vehicle I/O.
    """
    target_interface = interface or Task3VehicleIOInterface()
    if FASTAPI_AVAILABLE:
        app = FastAPI(
            title="FOG-ORCHESTRATOR 2.0 - Task-3 Vehicle I/O API",
            description="Vehicle Telemetry Ingestion & Supervisory Command Output Interface",
            version="2.0.0",
            docs_url="/docs",
            openapi_url="/openapi.json"
        )

        @app.get("/health")
        def health_check():
            return {"status": "ok"}

        @app.get("/api/v1/telemetry/buffer")
        def get_buffer():
            return {
                "buffered_vehicles_count": len(target_interface.telemetry_buffer),
                "vehicle_ids": list(target_interface.telemetry_buffer.keys())
            }

        return app

    return Task3VehicleIORESTApp(target_interface)


# Default application instance for direct import
default_interface = Task3VehicleIOInterface()
app = create_task3_fastapi_app(default_interface)

