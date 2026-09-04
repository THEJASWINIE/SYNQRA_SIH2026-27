import numpy as np
from models.vehicle_physics import resolve_v_safe

class ChanceConstrainedMPC:
    """
    Chance-Constrained Receding Horizon Dispatcher.
    Models forecast uncertainty as a distribution and enforces probabilistic safety 
    bounds (e.g. 95% confidence bounds) on Crusher queues and road capacity.
    """
    def __init__(self, horizon_s: float, step_s: float, crusher_service_rate_vph: float, 
                 shovel_service_rate_vph: float, vehicle_config: dict, road_config: dict,
                 confidence_level: float = 0.95):
        self.horizon_s = horizon_s
        self.step_s = step_s
        self.num_steps = int(horizon_s / step_s)
        self.crusher_mu = crusher_service_rate_vph / 3600.0
        self.shovel_mu = shovel_service_rate_vph / 3600.0
        self.v_cfg = vehicle_config
        self.r_cfg = road_config
        
        # Determine standard normal quantile for confidence level
        if confidence_level == 0.95:
            self.k_sigma = 1.645
        elif confidence_level == 0.99:
            self.k_sigma = 2.33
        else:
            self.k_sigma = 1.645  # Default 95%

    def calculate_road_capacity(self, visibility_m: float) -> float:
        """Calculate first-order physical road capacity for ROAD_2."""
        res = resolve_v_safe(
            mass_kg=self.v_cfg["tare_mass_kg"] + self.v_cfg["payload_mass_kg"],
            grade_percent=self.r_cfg["grade_percent"],
            friction_mu=self.r_cfg["friction_mu"],
            c_rr=self.r_cfg["c_rr"],
            hardware_max_brake_n=self.v_cfg["hardware_max_brake_force_n"],
            max_retarder_power_w=self.v_cfg["max_retarder_power_w"],
            curve_radius_m=self.r_cfg["curve_radius_m"],
            traction_speed_factor_mps=self.v_cfg["traction_speed_factor_mps"],
            speed_limit_mps=self.r_cfg["speed_limit_mps"],
            visibility_m=visibility_m,
            tau_total=self.v_cfg["ecu_hydraulic_latency_s"],
            s_margin=self.v_cfg["safety_stop_margin_m"]
        )
        v_safe = res["v_safe"]
        stop_env = v_safe * self.v_cfg["ecu_hydraulic_latency_s"] + (v_safe**2) / (2.0 * max(0.1, res["a_dec"]))
        headway_m = max(stop_env + self.v_cfg["safety_headway_margin_m"], self.v_cfg["min_static_headway_m"])
        
        capacity_vps = v_safe / headway_m
        return min(self.shovel_mu, capacity_vps)

    def optimize_release_rate(self, current_queue: float, forecast_visibility: np.ndarray, 
                              forecast_uncertainty_std: float = 5.0) -> float:
        """
        Calculates the maximum release rate such that P(Queue <= 2.0) >= confidence_level.
        We apply the normal distribution quantile (k_sigma) to get the conservative 
        lower-bound visibility forecast.
        """
        # Calculate the 5th percentile conservative visibility forecast
        # V_safe = V_pred - k_sigma * sigma_V
        lower_bound_visibility = forecast_visibility - self.k_sigma * forecast_uncertainty_std
        lower_bound_visibility = np.clip(lower_bound_visibility, 5.0, 50.0) # physical clamp
        
        # Calculate capacities based on lower bound visibility
        capacities = [self.calculate_road_capacity(v) for v in lower_bound_visibility]
        
        # Test candidate release rates using vectorized numpy checks
        candidates = np.linspace(0.0, self.shovel_mu, 50)
        q = np.full(50, current_queue)
        feasible = np.ones(50, dtype=bool)
        
        for k in range(min(len(forecast_visibility), self.num_steps)):
            cap = capacities[k]
            flows = np.minimum(candidates, cap)
            q = np.maximum(0.0, q + (flows - self.crusher_mu) * self.step_s)
            feasible = feasible & (q <= 2.0)
            
        feasible_rates = candidates[feasible]
        if len(feasible_rates) == 0:
            return 999.0
        best_release_vps = np.max(feasible_rates)
        if best_release_vps <= 1e-5:
            return 999.0
        return min(999.0, 1.0 / best_release_vps)
