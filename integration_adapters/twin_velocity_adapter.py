import os

from integration_adapters.config_paths import config_path as _project_config_path
import json
import time
import math
import logging
from typing import Dict, Any, Optional
from contracts import DispatchCommandMessage

logger = logging.getLogger("TwinVelocityAdapter")


class TwinVelocityAdapter:
    """
    Adapter transporting Digital Twin / Physics Engine computed safe velocity to the vehicle command interface.
    Preserves vehicle_id, velocity value, m/s unit, timestamp, and validity status.
    Supports configurable prototype scaling and motor speed ramping.
    """

    def __init__(self, config_path: Optional[str] = None, prototype_scale: float = 0.10):
        if config_path is None:
            config_path = _project_config_path("integration_config.json")

        self.prototype_scale = prototype_scale
        if os.path.exists(config_path):
            try:
                with open(config_path, "r") as f:
                    cfg = json.load(f)
                    self.prototype_scale = cfg.get("kinematic_scale", {}).get("prototype_scale", prototype_scale)
            except Exception as e:
                logger.warning(f"[TwinVelocityAdapter] Could not read config from {config_path}: {e}")

        self.last_transported_velocity: Dict[str, float] = {}
        self.current_ramped_velocity: Dict[str, float] = {}

    def scale_velocity(self, twin_v_safe_mps: float) -> float:
        """
        Scales Digital Twin dumper velocity (m/s) to physical prototype speed (m/s) using PROTOTYPE_SCALE.
        """
        if twin_v_safe_mps is None or math.isnan(twin_v_safe_mps) or math.isinf(twin_v_safe_mps) or twin_v_safe_mps < 0:
            return 0.0
        return round(float(twin_v_safe_mps) * self.prototype_scale, 4)

    def ramp_velocity(self, vehicle_id: str, target_velocity: float, max_step_mps: float = 0.5) -> float:
        """
        Applies a smooth motor acceleration/deceleration ramp from current speed to target speed.
        Does NOT bypass local safety ceilings; lower speed always takes priority.
        """
        current = self.current_ramped_velocity.get(vehicle_id, 0.0)
        if target_velocity > current:
            next_val = min(target_velocity, current + max_step_mps)
        else:
            next_val = max(target_velocity, current - max_step_mps)

        self.current_ramped_velocity[vehicle_id] = round(next_val, 4)
        return self.current_ramped_velocity[vehicle_id]

    def format_velocity_command(
        self,
        vehicle_id: str,
        computed_velocity: float,
        timestamp: Optional[float] = None,
        validity: bool = True,
        apply_scaling: bool = False,
        apply_ramping: bool = False
    ) -> Dict[str, Any]:
        """
        Formats already-computed safe velocity into standard vehicle command payload.
        Handles STOP conditions (NaN, Inf, negative, invalid state).
        """
        ts = timestamp if timestamp is not None else time.time()

        # Stop condition checks
        is_valid = (
            validity and
            (computed_velocity is not None) and
            not math.isnan(computed_velocity) and
            not math.isinf(computed_velocity) and
            (computed_velocity >= 0.0)
        )

        if not is_valid:
            logger.warning(f"[TwinVelocityAdapter] Invalid computed velocity ({computed_velocity}) for {vehicle_id}. Emitting emergency STOP command.")
            twin_v_safe = 0.0
            proto_target = 0.0
            action = "STOP"
            status = "INVALID_FALLBACK"
            self.current_ramped_velocity[vehicle_id] = 0.0
        else:
            twin_v_safe = float(computed_velocity)
            proto_target = self.scale_velocity(twin_v_safe) if apply_scaling else twin_v_safe
            if apply_ramping:
                proto_target = self.ramp_velocity(vehicle_id, proto_target)
            action = "SET_VELOCITY"
            status = "VALID"

        cmd_id = f"CMD_VEL_{int(ts * 1000)}_{vehicle_id}"

        command_payload = {
            "command_id": cmd_id,
            "vehicle_id": vehicle_id,
            "command": action,
            "action": action,
            "v_safe_ms": twin_v_safe,
            "v_safe_kmh": round(twin_v_safe * 3.6, 2),
            "prototype_scale": self.prototype_scale,
            "prototype_target_ms": proto_target,
            "target_speed": proto_target,
            "velocity": proto_target,
            "unit": "m/s",
            "timestamp": ts,
            "validity": is_valid,
            "status": status
        }

        if is_valid:
            self.last_transported_velocity[vehicle_id] = proto_target

        return command_payload

    def to_dispatch_command_message(
        self,
        vehicle_id: str,
        computed_velocity: float,
        timestamp: Optional[float] = None,
        validity: bool = True,
        apply_scaling: bool = False
    ) -> DispatchCommandMessage:
        """
        Converts transported velocity command to canonical DispatchCommandMessage.
        """
        cmd_dict = self.format_velocity_command(vehicle_id, computed_velocity, timestamp, validity, apply_scaling)
        return DispatchCommandMessage(
            command_id=cmd_dict["command_id"],
            vehicle_id=cmd_dict["vehicle_id"],
            timestamp=cmd_dict["timestamp"],
            target_speed=cmd_dict["velocity"],
            action=cmd_dict["action"],
            reason_code="PHYSICS_COMPUTED_SAFE_VELOCITY"
        )
