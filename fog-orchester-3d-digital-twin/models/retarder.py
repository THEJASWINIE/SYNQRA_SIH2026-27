"""
models/retarder.py
------------------
Evaluates continuous downhill retarding force requirements and thermal power absorption limits.

Equations:
- For continuous downhill operation at constant speed v:
  F_ret_required = max(0, m * g * sin(theta) - C_rr * m * g * cos(theta))
  P_ret_required = F_ret_required * v
- Require: P_ret_required <= P_ret_max
- v_retarder = P_ret_max / F_ret_required  (if F_ret_required > 0, else infinity)

Evidence Tags:
- Retarder Physics: [VERIFIED / PRIMARY] Steady-state energy conservation.
- Parameters: [REFERENCE] for BH100 continuous retarding capacity (~1200 kW).
"""

from typing import Dict, Any, Optional
import math
from models.vehicle_physics import GRAVITY_G


class RetarderModel:
    """
    Continuous downhill speed control and thermal retarder capacity model.
    Differentiates continuous downhill equilibrium from emergency friction braking.
    """
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        cfg = config or {}
        v_cfg = cfg.get("vehicle", cfg)
        powertrain = v_cfg.get("powertrain", {})
        
        self.p_ret_max_w = float(powertrain.get("max_retarder_power_kw", 1200.0)) * 1000.0
        if self.p_ret_max_w <= 0.0:
            raise ValueError(f"Retarder maximum power must be positive, got {self.p_ret_max_w} W")

    def calculate_required_retarding_force(
        self,
        mass_kg: float,
        grade_rad: float,
        c_rr: float
    ) -> float:
        """
        Calculate the steady continuous retarding force required to hold speed on a slope:
        F_ret_req = max(0, m * g * sin(theta) - C_rr * m * g * cos(theta))
        """
        if math.isnan(mass_kg) or math.isnan(grade_rad) or math.isnan(c_rr):
            raise ValueError("Inputs cannot be NaN")
        if math.isinf(mass_kg) or math.isinf(grade_rad) or math.isinf(c_rr):
            raise ValueError("Inputs cannot be infinite")
        if mass_kg <= 0.0:
            raise ValueError(f"Mass must be strictly positive, got {mass_kg} kg")
        if c_rr < 0.0:
            raise ValueError(f"Rolling resistance coefficient must be non-negative, got {c_rr}")

        f_downhill_gravity = mass_kg * GRAVITY_G * math.sin(grade_rad)
        f_roll = c_rr * mass_kg * GRAVITY_G * math.cos(grade_rad)

        return max(0.0, f_downhill_gravity - f_roll)

    def calculate_required_retarding_power(
        self,
        speed_mps: float,
        mass_kg: float,
        grade_rad: float,
        c_rr: float
    ) -> float:
        """
        Calculate continuous power absorbed by retarder at speed v:
        P_ret_req = F_ret_req * v
        """
        if speed_mps < 0.0:
            raise ValueError("Speed must be non-negative")
        f_ret = self.calculate_required_retarding_force(mass_kg, grade_rad, c_rr)
        return f_ret * speed_mps

    def calculate_max_sustainable_downhill_speed(
        self,
        mass_kg: float,
        grade_rad: float,
        c_rr: float,
        p_ret_max_w: Optional[float] = None
    ) -> float:
        """
        Solve for the maximum downhill entry speed v_retarder sustainable within retarder thermal limit:
        v_retarder = P_ret_max / F_ret_required
        """
        p_max = self.p_ret_max_w if p_ret_max_w is None else p_ret_max_w
        f_ret_req = self.calculate_required_retarding_force(mass_kg, grade_rad, c_rr)

        if f_ret_req <= 1e-4:
            # Gravity does not overcome rolling resistance; retarder is not active constraint
            return float("inf")

        return p_max / f_ret_req
