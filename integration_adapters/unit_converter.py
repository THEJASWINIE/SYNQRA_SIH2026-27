"""
FOG-ORCHESTRATOR 2.0 — Unit Converter Adapter (Blocker 2 Resolution)

Converts physical wheel RPM measurements into physical linear velocity (m/s)
using explicit, measured wheel radius values from configuration files.
Never invents or hardcodes uncalibrated parameters.
"""

import os
import json
import math
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger("UnitConverter")

class UnitConverter:
    """Converts wheel RPM to physical linear speed in m/s and km/h."""

    def __init__(self, config_path: Optional[str] = None):
        if config_path is None:
            config_path = os.path.join("config", "physical_vehicle_parameters.json")
        
        self.vehicle_params: Dict[str, Dict[str, Any]] = {}
        if os.path.exists(config_path):
            with open(config_path, "r") as f:
                self.vehicle_params = json.load(f)
        else:
            logger.warning(f"Config path '{config_path}' not found. UnitConverter initialized uncalibrated.")

    def rpm_to_speed_mps(self, vehicle_id: str, rpm: float) -> Optional[float]:
        """Calculates physical linear speed (m/s) from wheel RPM."""
        if rpm is None or not isinstance(rpm, (int, float)) or rpm < 0:
            logger.error(f"[UnitConverter] Invalid RPM input '{rpm}' for vehicle '{vehicle_id}'")
            return None

        params = self.vehicle_params.get(vehicle_id)
        if not params or "wheel_radius_m" not in params:
            logger.error(f"[UnitConverter] Missing calibrated wheel_radius_m for vehicle '{vehicle_id}'")
            return None

        r_m = params["wheel_radius_m"]
        if r_m <= 0:
            logger.error(f"[UnitConverter] Invalid wheel radius {r_m} for vehicle '{vehicle_id}'")
            return None

        # v = RPM * 2 * pi * r / 60
        v_mps = (rpm * 2.0 * math.pi * r_m) / 60.0
        return round(v_mps, 4)

    def mps_to_kmh(self, speed_mps: float) -> float:
        if speed_mps is None or speed_mps < 0:
            return 0.0
        return round(speed_mps * 3.6, 2)
