"""
models/road_capacity.py
-----------------------
Calculates dynamic road segment carrying capacity C_r (vehicles/hour)
from microscopic vehicle physics (safe speed v_safe, safe headway H_safe),
enforcing the physical vehicle spacing lower bound for the BH100 class.

Equations:
- C_r = v_safe / H_safe  [vehicles / second]
- C_r_h = 3600 * v_safe / H_safe  [vehicles / hour]
- H_safe = v_safe * tau_total + v_safe^2 / (2 * a_dec) + L_vehicle + S_standstill
- Physical Bound: H_safe >= L_vehicle + S_standstill = 15.52 m for BH100-class

Evidence Tags:
- Flow Relation: [VERIFIED / PRIMARY] Hydrodynamic traffic flow capacity equation.
- Physical Bound: [MODEL CONFIG] 15.52 m minimum center-to-center headway.
"""

from typing import Dict, Any, Optional
import math


class RoadCapacityModel:
    """
    Evaluates dynamic safe following headway H_safe and continuous hourly carrying
    capacity C_r for road segments under degraded environmental conditions.
    """
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        cfg = config or {}
        v_cfg = cfg.get("vehicle", cfg)
        geometry = v_cfg.get("geometry", {})
        latency = v_cfg.get("latency", {})

        self.length_vehicle_m = float(geometry.get("length_m", 10.52))
        self.standstill_margin_m = float(geometry.get("standstill_margin_m", 5.0))
        self.min_headway_bound_m = self.length_vehicle_m + self.standstill_margin_m  # 15.52 m

        # Default reaction latency
        self.tau_total_default = float(latency.get("tau_total_autonomous_s", 0.40))

    def calculate_safe_headway(
        self,
        v_safe_mps: float,
        a_dec_mps2: float,
        tau_total_s: Optional[float] = None,
        length_vehicle_m: Optional[float] = None,
        standstill_margin_m: Optional[float] = None
    ) -> float:
        """
        Calculate dynamic safe center-to-center following distance H_safe (m).
        
        H_safe = max(H_min, v_safe * tau + (v_safe^2 / (2 * a_dec)) + L_v + S_margin)
        """
        if math.isnan(v_safe_mps) or math.isnan(a_dec_mps2):
            raise ValueError("Kinematic inputs cannot be NaN")
        if math.isinf(v_safe_mps) or math.isinf(a_dec_mps2):
            raise ValueError("Kinematic inputs cannot be infinite")
        if v_safe_mps < 0.0:
            raise ValueError(f"v_safe must be non-negative, got {v_safe_mps}")
        if a_dec_mps2 <= 0.0:
            raise ValueError(f"a_dec must be strictly positive, got {a_dec_mps2}")

        tau = self.tau_total_default if tau_total_s is None else tau_total_s
        l_v = self.length_vehicle_m if length_vehicle_m is None else length_vehicle_m
        s_m = self.standstill_margin_m if standstill_margin_m is None else standstill_margin_m
        
        h_min = l_v + s_m  # Physical standstill lower bound (e.g. 15.52m)

        d_reaction = v_safe_mps * tau
        d_brake = (v_safe_mps ** 2) / (2.0 * a_dec_mps2)
        
        calculated_headway = d_reaction + d_brake + l_v + s_m

        # Strictly enforce physical spacing lower bound
        return max(h_min, calculated_headway)

    def calculate_road_capacity(
        self,
        v_safe_mps: float,
        h_safe_m: float
    ) -> Dict[str, float]:
        """
        Compute road segment carrying capacity from safe speed and safe headway:
        C_r_vps = v_safe / H_safe  [vehicles/second]
        C_r_vph = 3600 * v_safe / H_safe  [vehicles/hour]
        """
        if math.isnan(v_safe_mps) or math.isnan(h_safe_m):
            raise ValueError("Inputs cannot be NaN")
        if math.isinf(v_safe_mps) or math.isinf(h_safe_m):
            raise ValueError("Inputs cannot be infinite")
        if v_safe_mps < 0.0:
            raise ValueError(f"v_safe must be non-negative, got {v_safe_mps}")
        if h_safe_m <= 0.0:
            raise ValueError(f"h_safe must be strictly positive, got {h_safe_m}")

        # Enforce physical headway constraint on input
        effective_h_safe = max(self.min_headway_bound_m, h_safe_m)

        if v_safe_mps <= 1e-4:
            return {
                "capacity_vps": 0.0,
                "capacity_vph": 0.0,
                "v_safe_mps": 0.0,
                "h_safe_m": effective_h_safe
            }

        c_r_vps = v_safe_mps / effective_h_safe
        c_r_vph = 3600.0 * c_r_vps

        return {
            "capacity_vps": c_r_vps,
            "capacity_vph": c_r_vph,
            "v_safe_mps": v_safe_mps,
            "h_safe_m": effective_h_safe
        }

    def calculate_capacity_from_conditions(
        self,
        v_safe_mps: float,
        a_dec_mps2: float,
        tau_total_s: Optional[float] = None
    ) -> Dict[str, float]:
        """
        Convenience method to compute safe headway and hourly road capacity in a single step.
        """
        h_safe = self.calculate_safe_headway(v_safe_mps, a_dec_mps2, tau_total_s)
        return self.calculate_road_capacity(v_safe_mps, h_safe)
