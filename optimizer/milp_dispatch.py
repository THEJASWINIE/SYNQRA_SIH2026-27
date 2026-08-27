import numpy as np
from models.vehicle_physics import resolve_v_safe

class DeterministicMPC:
    """
    Receding Horizon Model Predictive Control (MPC) Dispatcher.
    Optimizes Shovel release intervals to maximize throughput and stabilize queues
    assuming a deterministic perfect visibility forecast.
    """
    def __init__(self, horizon_s: float, step_s: float, crusher_service_rate_vph: float, 
                 shovel_service_rate_vph: float, vehicle_config: dict, road_config: dict):
        self.horizon_s = horizon_s
        self.step_s = step_s
        self.num_steps = int(horizon_s / step_s)
        self.crusher_mu = crusher_service_rate_vph / 3600.0  # vehicles/sec
        self.shovel_mu = shovel_service_rate_vph / 3600.0    # vehicles/sec
        self.v_cfg = vehicle_config
        self.r_cfg = road_config

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
        # Stopping envelope
        stop_env = v_safe * self.v_cfg["ecu_hydraulic_latency_s"] + (v_safe**2) / (2.0 * max(0.1, res["a_dec"]))
        headway_m = max(stop_env + self.v_cfg["safety_headway_margin_m"], self.v_cfg["min_static_headway_m"])
        
        capacity_vps = v_safe / headway_m
        return min(self.shovel_mu, capacity_vps)

    def optimize_release_rate(self, current_queue: float, forecast_visibility: np.ndarray) -> float:
        """
        Solve receding-horizon optimization to determine release delay.
        Maximizes release rate such that Q_predicted <= 2.0 and respects capacity.
        """
        # Calculate capacities for each horizon step
        capacities = [self.calculate_road_capacity(v) for v in forecast_visibility]
        
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
