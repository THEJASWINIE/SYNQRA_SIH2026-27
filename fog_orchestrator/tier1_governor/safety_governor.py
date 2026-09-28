"""
Tier 1: Autonomous Vehicle Safety Governor for FOG-ORCHESTRATOR 2.0
Enforces core safety constraint: S_stop + S_margin <= R_effective
Calculates v_safe, H_safe, active limiting constraints, and RLS friction estimation.
"""

import math
from dataclasses import dataclass
from typing import Dict, Tuple, Optional
from fog_orchestrator.core.config import (
    VehicleParameters, EnvironmentalParameters, PerceptionCommParameters,
    DEFAULT_VEHICLE, DEFAULT_ENV, DEFAULT_COMM
)
from fog_orchestrator.tier1_governor.vehicle_physics import VehiclePhysics


@dataclass
class SafetyState:
    """Output container for Tier 1 Safety Governor state."""
    v_safe_mps: float
    v_safe_kmh: float
    v_stop_kmh: float
    v_retarder_kmh: float
    v_curve_kmh: float
    v_mine_kmh: float
    h_safe_m: float
    s_stop_m: float
    active_constraint: str  # 'STOPPING_DISTANCE', 'RETARDER_THERMAL', 'CURVE_LATERAL', 'SITE_SPEED_LIMIT', 'UNSAFE_RUNAWAY'
    is_safe: bool
    risk_score: float  # 0.0 (low risk) to 1.0 (high/imminent collision risk)


class RLSFrictionEstimator:
    """
    Recursive Least Squares (RLS) tire-road friction estimator with conservative safety bound.
    mu_meas = [ m*g*sin(theta) - F_roll - F_retarder - F_aero - m*a_x ] / [ m*g*cos(theta) ]
    mu_safe = max(mu_floor, hat_mu - k * sigma_mu)
    """
    def __init__(
        self,
        mu_prior: float = 0.35,
        p_prior: float = 0.04,
        r_noise: float = 0.005,
        q_process: float = 0.0001,
        mu_floor: float = 0.05,
        k_sigma: float = 2.0
    ):
        self.hat_mu = mu_prior
        self.p_var = p_prior
        self.r_noise = r_noise
        self.q_process = q_process
        self.mu_floor = mu_floor
        self.k_sigma = k_sigma

    def update(
        self,
        a_meas_mps2: float,
        grade_rad: float,
        is_loaded: bool,
        f_retarder_n: float,
        speed_mps: float,
        veh_params: VehicleParameters = DEFAULT_VEHICLE,
        env_params: EnvironmentalParameters = DEFAULT_ENV
    ) -> Tuple[float, float, float]:
        """
        Updates RLS estimator with new deceleration measurement.
        Returns: (hat_mu, sigma_mu, mu_safe)
        """
        mass_kg = veh_params.mass_loaded_kg if is_loaded else veh_params.mass_empty_kg
        g = env_params.gravity_mps2

        f_grade = mass_kg * g * math.sin(grade_rad)
        f_roll = env_params.c_rr_default * mass_kg * g * math.cos(grade_rad)
        f_aero = 0.5 * env_params.air_density_kgm3 * veh_params.drag_coeff * veh_params.frontal_area_m2 * (speed_mps ** 2)

        normal_force = mass_kg * g * math.cos(grade_rad)
        if normal_force <= 1.0:
            return self.hat_mu, math.sqrt(self.p_var), self.get_mu_safe()

        # Compute raw measured friction from longitudinal dynamic balance
        net_known_force = f_grade - f_roll - f_aero - f_retarder_n
        # m * a_x = net_known_force - F_brake
        # F_brake = net_known_force - m * a_x
        f_brake_meas = net_known_force - mass_kg * a_meas_mps2
        mu_meas = f_brake_meas / normal_force
        mu_meas = max(0.05, min(0.85, mu_meas))

        # Time update (Predict)
        self.p_var += self.q_process

        # Measurement update (Correct)
        k_gain = self.p_var / (self.p_var + self.r_noise)
        self.hat_mu += k_gain * (mu_meas - self.hat_mu)
        self.p_var = (1.0 - k_gain) * self.p_var

        sigma_mu = math.sqrt(max(1e-6, self.p_var))
        mu_safe = max(self.mu_floor, self.hat_mu - self.k_sigma * sigma_mu)

        return self.hat_mu, sigma_mu, mu_safe

    def get_mu_safe(self) -> float:
        sigma_mu = math.sqrt(max(1e-6, self.p_var))
        return max(self.mu_floor, self.hat_mu - self.k_sigma * sigma_mu)


class VehicleSafetyGovernor:
    """Tier 1 Autonomous Vehicle Safety Governor Engine."""

    def __init__(
        self,
        veh_params: VehicleParameters = DEFAULT_VEHICLE,
        env_params: EnvironmentalParameters = DEFAULT_ENV,
        comm_params: PerceptionCommParameters = DEFAULT_COMM
    ):
        self.veh = veh_params
        self.env = env_params
        self.comm = comm_params

    def calculate_effective_latency(self, comm_confidence: float = 1.0) -> float:
        """Total reaction latency incorporating communication degradation penalty."""
        c_comm = max(0.0, min(1.0, comm_confidence))
        tau_base = self.comm.tau_sensor_s + self.comm.tau_comm_s + self.comm.tau_ecu_s + self.comm.tau_human_s
        tau_eff = tau_base + self.comm.k_comm_s * (1.0 - c_comm)
        return tau_eff

    def calculate_v_stop(
        self,
        r_effective_m: float,
        grade_rad: float,
        is_loaded: bool,
        friction_mu: float,
        comm_confidence: float = 1.0
    ) -> Tuple[float, float, float]:
        """
        Calculates maximum stopping speed v_stop (mps) satisfying S_stop + S_margin <= R_effective.
        Returns: (v_stop_mps, s_stop_m, a_dec_mps2)
        """
        a_dec = VehiclePhysics.calculate_effective_deceleration(
            grade_rad=grade_rad,
            is_loaded=is_loaded,
            friction_mu=friction_mu,
            veh_params=self.veh,
            env_params=self.env
        )

        tau_eff = self.calculate_effective_latency(comm_confidence)
        s_margin_base = self.comm.s_base_m

        # If effective perception range is less than standstill margin or deceleration is zero/negative
        if r_effective_m <= s_margin_base or a_dec <= 0.0:
            return 0.0, 0.0, a_dec

        # Solve quadratic equation: (1 / (2*a_dec)) * v^2 + tau_eff * v + (s_margin_base - R_effective) = 0
        a_quad = 1.0 / (2.0 * a_dec)
        b_quad = tau_eff
        c_quad = s_margin_base - r_effective_m

        discriminant = b_quad ** 2 - 4.0 * a_quad * c_quad
        if discriminant < 0:
            return 0.0, 0.0, a_dec

        v_stop = (-b_quad + math.sqrt(discriminant)) / (2.0 * a_quad)
        v_stop = max(0.0, v_stop)

        # Compute corresponding stopping distance S_stop
        s_stop = v_stop * tau_eff + (v_stop ** 2) / (2.0 * a_dec)
        return v_stop, s_stop, a_dec

    def calculate_v_curve(self, curve_radius_m: float, grade_rad: float, friction_mu: float) -> float:
        """Calculates maximum speed limit around a curve to prevent lateral skid."""
        if math.isinf(curve_radius_m) or curve_radius_m >= 1000.0:
            return float('inf')
        g = self.env.gravity_mps2
        v_curve = math.sqrt(max(0.0, friction_mu * g * curve_radius_m * math.cos(grade_rad)))
        return v_curve

    def evaluate_tier1_safety(
        self,
        r_effective_m: float,
        grade_rad: float,
        is_loaded: bool,
        friction_mu: float,
        curve_radius_m: float = float('inf'),
        comm_confidence: float = 1.0
    ) -> SafetyState:
        """
        Evaluates Tier 1 autonomous safe speed v_safe = min(v_stop, v_retarder, v_curve, v_mine).
        Determines active limiting constraint.
        """
        v_mine_mps = self.env.v_mine_limit_kmh / 3.6

        # 1. Stopping speed constraint
        v_stop_mps, s_stop_m, a_dec = self.calculate_v_stop(
            r_effective_m=r_effective_m,
            grade_rad=grade_rad,
            is_loaded=is_loaded,
            friction_mu=friction_mu,
            comm_confidence=comm_confidence
        )

        # 2. Continuous retarder speed constraint
        v_retarder_mps = VehiclePhysics.calculate_retarder_continuous_speed_limit(
            grade_rad=grade_rad,
            is_loaded=is_loaded,
            veh_params=self.veh,
            env_params=self.env
        )

        # 3. Curve lateral friction constraint
        v_curve_mps = self.calculate_v_curve(curve_radius_m, grade_rad, friction_mu)

        # Determine minimum safe speed constraint
        constraints = [
            (v_stop_mps, "STOPPING_DISTANCE"),
            (v_retarder_mps, "RETARDER_THERMAL"),
            (v_curve_mps, "CURVE_LATERAL"),
            (v_mine_mps, "SITE_SPEED_LIMIT")
        ]

        # Handle runaway condition (a_dec <= 0)
        if a_dec <= 0.0:
            return SafetyState(
                v_safe_mps=0.0, v_safe_kmh=0.0, v_stop_kmh=0.0, v_retarder_kmh=v_retarder_mps * 3.6,
                v_curve_kmh=v_curve_mps * 3.6, v_mine_kmh=self.env.v_mine_limit_kmh,
                h_safe_m=float('inf'), s_stop_m=float('inf'), active_constraint="UNSAFE_RUNAWAY",
                is_safe=False, risk_score=1.0
            )

        v_safe_mps, active_constraint = min(constraints, key=lambda x: x[0])
        v_safe_kmh = v_safe_mps * 3.6

        # Dynamic Headway H_safe
        tau_eff = self.calculate_effective_latency(comm_confidence)
        h_safe_m = s_stop_m + self.comm.s_base_m

        is_safe = v_safe_mps > 0.0 and r_effective_m > self.comm.s_base_m
        risk_score = 1.0 - min(1.0, max(0.0, r_effective_m - s_stop_m) / 50.0)

        return SafetyState(
            v_safe_mps=v_safe_mps,
            v_safe_kmh=v_safe_kmh,
            v_stop_kmh=v_stop_mps * 3.6,
            v_retarder_kmh=min(150.0, v_retarder_mps * 3.6),
            v_curve_kmh=min(150.0, v_curve_mps * 3.6),
            v_mine_kmh=self.env.v_mine_limit_kmh,
            h_safe_m=h_safe_m,
            s_stop_m=s_stop_m,
            active_constraint=active_constraint,
            is_safe=is_safe,
            risk_score=risk_score
        )

    def calculate_safe_headway(
        self,
        v_follow_mps: float,
        v_lead_mps: float,
        grade_rad: float,
        is_loaded_follow: bool,
        friction_mu: float,
        comm_confidence: float = 1.0
    ) -> float:
        """
        Calculates exact dynamic longitudinal safe headway H_safe (m):
        H_safe = v_f * tau_eff + v_f^2 / (2 * a_f) - v_l^2 / (2 * a_l) + S_margin
        Handles worst-case stationary leader obstacle (v_lead = 0, a_l -> infinity).
        """
        a_f = VehiclePhysics.calculate_effective_deceleration(grade_rad, is_loaded_follow, friction_mu, v_follow_mps, self.veh, self.env)
        tau_eff = self.calculate_effective_latency(comm_confidence)
        s_margin = self.comm.s_base_m + self.comm.k_comm_s * (1.0 - comm_confidence) * v_follow_mps

        if a_f <= 0.0:
            return float('inf')

        d_follow_stop = v_follow_mps * tau_eff + (v_follow_mps ** 2) / (2.0 * a_f)

        if v_lead_mps <= 0.0:
            # Stationary leader obstacle
            return d_follow_stop + s_margin

        # Moving leader with maximum service deceleration a_l (assume equivalent or nominal deceleration)
        a_l = a_f
        d_lead_stop = (v_lead_mps ** 2) / (2.0 * a_l)

        h_safe = d_follow_stop - d_lead_stop + s_margin
        return max(s_margin, h_safe)
