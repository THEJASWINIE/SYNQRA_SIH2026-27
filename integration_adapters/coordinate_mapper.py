"""
FOG-ORCHESTRATOR 2.0 — Coordinate Mapper & Position Estimator Adapter (Blocker 4 Resolution)

Performs dead-reckoning trajectory estimation (x, y, heading) for physical prototypes
without GPS. Explicitly flags all output poses as "ESTIMATED" and maps prototype-relative
coordinates onto logical Digital Twin mine grid coordinates.
"""

import os
import json
import math
import time
import logging
from typing import Dict, Any, Optional, Tuple

logger = logging.getLogger("CoordinateMapper")

class CoordinateMapper:
    """Estimates physical prototype relative position and maps to logical mine grid."""

    def __init__(self, config_path: Optional[str] = None):
        if config_path is None:
            config_path = os.path.join("config", "physical_vehicle_parameters.json")

        self.vehicle_poses: Dict[str, Dict[str, float]] = {}
        self.last_update_times: Dict[str, float] = {}

        if os.path.exists(config_path):
            with open(config_path, "r") as f:
                params = json.load(f)
                for vid, data in params.items():
                    pose = data.get("initial_pose", {"x": 0.0, "y": 0.0, "heading_rad": 0.0})
                    self.vehicle_poses[vid] = {
                        "x_p": float(pose.get("x", 0.0)),
                        "y_p": float(pose.get("y", 0.0)),
                        "heading_rad": float(pose.get("heading_rad", 0.0))
                    }
                    self.last_update_times[vid] = time.time()

    def update_pose(self, vehicle_id: str, speed_mps: float, yaw_rate_rads: float, dt_s: float, is_stale: bool = False) -> Dict[str, Any]:
        """
        Updates kinematic dead reckoning state:
        x_{k+1} = x_k + v * cos(heading) * dt
        y_{k+1} = y_k + v * sin(heading) * dt
        heading_{k+1} = heading_k + yaw_rate * dt
        """
        if is_stale or speed_mps is None or dt_s <= 0 or dt_s > 2.0:
            # Rejects update from stale or invalid data
            current_pose = self.vehicle_poses.get(vehicle_id, {"x_p": 0.0, "y_p": 0.0, "heading_rad": 0.0})
            return {
                "vehicle_id": vehicle_id,
                "x_p": current_pose["x_p"],
                "y_p": current_pose["y_p"],
                "heading_rad": current_pose["heading_rad"],
                "x_twin": current_pose["x_p"] + 100.0,  # Offset to logical mine grid node
                "y_twin": current_pose["y_p"] + 50.0,
                "position_quality": "ESTIMATED_STALE"
            }

        pose = self.vehicle_poses.setdefault(vehicle_id, {"x_p": 0.0, "y_p": 0.0, "heading_rad": 0.0})

        speed = max(0.0, speed_mps)
        yaw_rate = yaw_rate_rads if yaw_rate_rads is not None else 0.0

        # Update heading
        new_heading = pose["heading_rad"] + yaw_rate * dt_s
        new_heading = (new_heading + math.pi) % (2 * math.pi) - math.pi

        # Update planar coordinates
        dx = speed * math.cos(new_heading) * dt_s
        dy = speed * math.sin(new_heading) * dt_s

        new_x = pose["x_p"] + dx
        new_y = pose["y_p"] + dy

        self.vehicle_poses[vehicle_id] = {
            "x_p": new_x,
            "y_p": new_y,
            "heading_rad": new_heading
        }

        # Logical mine coordinate mapping (Map prototype origin to Mine Node N01 grid: X_offset=100.0m, Y_offset=50.0m)
        mine_x_offset = 100.0
        mine_y_offset = 50.0
        x_twin = new_x + mine_x_offset
        y_twin = new_y + mine_y_offset

        return {
            "vehicle_id": vehicle_id,
            "x_p": round(new_x, 3),
            "y_p": round(new_y, 3),
            "heading_rad": round(new_heading, 3),
            "x_twin": round(x_twin, 3),
            "y_twin": round(y_twin, 3),
            "position_quality": "ESTIMATED"
        }
