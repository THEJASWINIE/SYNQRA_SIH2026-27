"""
FOG-ORCHESTRATOR 2.0 — Kinematic Scale Adapter (Blocker 2 Resolution)

Distinguishes raw physical speed (physical_speed_mps), normalized ratio (normalized_speed),
and Digital Twin equivalent speed (twin_equivalent_speed_mps).
Ensures physical vehicle data is never overwritten or miscalibrated.
"""

import os

from integration_adapters.config_paths import config_path as _project_config_path
import json
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger("KinematicScaleAdapter")

class KinematicScaleAdapter:
    """Manages explicit scale conversions between Physical Prototype and Mining Digital Twin."""

    def __init__(self, config_path: Optional[str] = None):
        if config_path is None:
            config_path = _project_config_path("integration_config.json")

        self.proto_max_mps = 3.0
        self.twin_max_mps = 11.11
        self.lambda_scale = 0.27
        self.enable_scaling = True

        if os.path.exists(config_path):
            with open(config_path, "r") as f:
                cfg = json.load(f).get("kinematic_scale", {})
                self.proto_max_mps = cfg.get("prototype_max_speed_mps", 3.0)
                self.twin_max_mps = cfg.get("twin_dumper_max_speed_mps", 11.11)
                self.lambda_scale = cfg.get("scale_factor_lambda", 0.27)
                self.enable_scaling = cfg.get("enable_scaling", True)

    def physical_to_twin_speed(self, physical_speed_mps: float) -> Dict[str, float]:
        """
        Maps physical prototype speed (m/s) to twin-equivalent speed (m/s).
        Returns dict containing physical_speed_mps, normalized_speed, and twin_equivalent_speed_mps.
        """
        if physical_speed_mps is None or physical_speed_mps < 0:
            physical_speed_mps = 0.0

        normalized = min(1.0, physical_speed_mps / self.proto_max_mps) if self.proto_max_mps > 0 else 0.0
        twin_equiv = round(normalized * self.twin_max_mps, 2)

        return {
            "physical_speed_mps": round(physical_speed_mps, 4),
            "normalized_speed": round(normalized, 4),
            "twin_equivalent_speed_mps": twin_equiv
        }

    def twin_advisory_to_physical_speed(self, twin_advisory_speed_mps: float) -> float:
        """
        Scales Digital Twin advisory speed target (for 165t dumper) to physical prototype speed (m/s).
        """
        if twin_advisory_speed_mps is None or twin_advisory_speed_mps < 0:
            return 0.0

        normalized = min(1.0, twin_advisory_speed_mps / self.twin_max_mps) if self.twin_max_mps > 0 else 0.0
        proto_speed = round(normalized * self.proto_max_mps, 2)
        return min(proto_speed, self.proto_max_mps)
