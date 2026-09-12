"""
models/friction.py
------------------
Manages tire-road friction estimation, road surface state mapping,
and conservative lower confidence bound calculation under uncertainty.

Equations:
- mu_safe = max(mu_floor, mu_hat - k_sigma * sigma_mu)

Evidence Tags:
- Formulation: [MODEL CONFIG] Conservative lower confidence bound (95% one-sided).
- Reference Parameters: mu_floor = 0.18, k_sigma = 1.645 [MODEL CONFIG].
- Surface Priors: [ASSUMPTION] Dry (0.65), Damp (0.50), Wet (0.35), Saturated (0.20).
"""

from typing import Dict, Any, Tuple, Optional
import math


class FrictionModel:
    """
    Tire-road adhesion estimator providing conservative safety bounds
    based on surface wetness, past measurements, and uncertainty variance.
    """
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        cfg = config or {}
        weather_cfg = cfg.get("weather", cfg)
        safety_floors = weather_cfg.get("safety_floors", {})
        
        self.mu_floor = float(safety_floors.get("mu_floor", 0.18))
        self.k_sigma = float(safety_floors.get("k_sigma", 1.645))
        
        self.surface_map = {
            "dry": (0.65, 0.05, 0.020),
            "damp": (0.50, 0.06, 0.025),
            "wet": (0.35, 0.08, 0.035),
            "saturated": (0.20, 0.05, 0.050),
            "saturated_slurry": (0.20, 0.05, 0.050)
        }

        # Override defaults if configured
        mapping_cfg = weather_cfg.get("surface_friction_mapping", {})
        for surf, params in mapping_cfg.items():
            if isinstance(params, dict):
                mu_m = float(params.get("mu_mean", 0.65))
                mu_s = float(params.get("mu_sigma", 0.05))
                c_rr = float(params.get("rolling_resistance", 0.025))
                self.surface_map[surf.lower()] = (mu_m, mu_s, c_rr)

    def calculate_safe_friction(
        self,
        mu_hat: float,
        sigma_mu: float,
        mu_floor: Optional[float] = None,
        k_sigma: Optional[float] = None
    ) -> float:
        """
        Calculate conservative tire-road friction mu_safe enforcing lower confidence bound
        and absolute physical floor:
        mu_safe = max(mu_floor, mu_hat - k_sigma * sigma_mu)
        """
        if math.isnan(mu_hat) or math.isnan(sigma_mu):
            raise ValueError("Friction inputs cannot be NaN")
        if math.isinf(mu_hat) or math.isinf(sigma_mu):
            raise ValueError("Friction inputs cannot be infinite")
        if mu_hat < 0.0 or sigma_mu < 0.0:
            raise ValueError("Friction values must be non-negative")

        floor = self.mu_floor if mu_floor is None else mu_floor
        k = self.k_sigma if k_sigma is None else k_sigma

        lower_bound = mu_hat - (k * sigma_mu)
        return max(floor, lower_bound)

    def get_surface_prior(self, surface_state: str) -> Tuple[float, float, float]:
        """
        Returns (mu_mean, mu_sigma, rolling_resistance) for a specified surface condition.
        """
        surf = surface_state.lower()
        if surf not in self.surface_map:
            raise ValueError(f"Unknown surface state '{surface_state}'. Expected one of {list(self.surface_map.keys())}")
        return self.surface_map[surf]
