"""
Model 11 — Friction Estimation, Recursive Least Squares (RLS), and Observability / Identifiability Analysis.
"""

import numpy as np
from fog_safe.vehicle import MiningVehicle
from fog_safe.road import RoadSegment
from fog_safe.environment import EnvironmentState
from fog_safe.dynamics import calculate_aero_drag

class RecursiveFrictionEstimator:
    """
    Recursive Least Squares (RLS) estimator for online tire-road friction coefficient estimation.
    Tracks estimate mu_hat, variance P_k, and lower bound mu_lower = mu_hat - 2*sigma_mu.
    """
    def __init__(self, mu_init: float = 0.50, P_init: float = 0.04, R_meas: float = 0.01, Q_proc: float = 1e-4):
        """
        :param mu_init: Initial prior estimate of friction coefficient.
        :param P_init: Initial estimation error variance.
        :param R_meas: Measurement noise variance.
        :param Q_proc: Process noise variance (accounting for surface changes).
        """
        self.mu_hat = mu_init
        self.P = P_init
        self.R = R_meas
        self.Q = Q_proc

    @property
    def sigma_mu(self) -> float:
        return np.sqrt(max(1e-8, self.P))

    @property
    def mu_lower(self) -> float:
        """Safety-critical lower bound: mu_lower = max(0.05, mu_hat - 2*sigma_mu)."""
        return max(0.05, self.mu_hat - 2.0 * self.sigma_mu)

    def calculate_inverse_mu(
        self,
        vehicle: MiningVehicle,
        road: RoadSegment,
        env: EnvironmentState,
        v: float,
        a_x: float,
        f_retarder: float = 0.0,
        c_rr_assumed: float = None
    ) -> float:
        """
        Model 11 Inverse Estimator equation:
        mu_meas = [ g*sin(theta) - C_rr*g*cos(theta) - F_retarder/m - F_aero/m - a_x ] / [ g*cos(theta) ]
        """
        if c_rr_assumed is None:
            c_rr_assumed = road.c_rr

        g = env.g
        theta = road.theta
        m = vehicle.mass
        f_aero = calculate_aero_drag(vehicle, env, v)

        numerator = g * np.sin(theta) - c_rr_assumed * g * np.cos(theta) - (f_retarder / m) - (f_aero / m) - a_x
        denominator = g * np.cos(theta)

        mu_meas = numerator / denominator
        # Physically bound measurement to [0.05, 1.0]
        return max(0.05, min(1.0, mu_meas))

    def update(self, mu_meas: float, is_excited: bool = True) -> tuple[float, float, float]:
        """
        Performs scalar RLS measurement update step.
        Updates state only if persistent excitation is present (e.g. active braking event).
        Returns: (mu_hat, sigma_mu, mu_lower)
        """
        if not is_excited:
            return self.mu_hat, self.sigma_mu, self.mu_lower

        # Time update (prediction)
        P_prior = self.P + self.Q

        # Kalman gain
        K = P_prior / (P_prior + self.R)

        # Measurement update
        self.mu_hat = self.mu_hat + K * (mu_meas - self.mu_hat)
        self.mu_hat = max(0.05, min(1.0, float(self.mu_hat)))

        self.P = (1.0 - K) * P_prior
        return self.mu_hat, self.sigma_mu, self.mu_lower

def analyze_identifiability_failure(
    vehicle: MiningVehicle,
    road: RoadSegment,
    env: EnvironmentState,
    v: float,
    a_x_true: float,
    unknown_retarder_force: float
) -> dict:
    """
    Test 9 Identifiability Analysis:
    Demonstrates mathematically and numerically that acceleration a_x alone
    is NOT sufficient to uniquely identify mu when retarder force or rolling resistance is unmeasured.
    """
    m = vehicle.mass
    g = env.g
    theta = road.theta

    # True friction assuming zero unknown retarder force
    f_aero = calculate_aero_drag(vehicle, env, v)
    mu_true_calc = (g * np.sin(theta) - road.c_rr * g * np.cos(theta) - (f_aero / m) - a_x_true) / (g * np.cos(theta))

    # Mis-estimated friction due to unmeasured retarder force
    mu_err = unknown_retarder_force / (m * g * np.cos(theta))
    mu_estimated_if_ignored = mu_true_calc - mu_err

    return {
        "a_x": a_x_true,
        "unknown_retarder_force_N": unknown_retarder_force,
        "mu_true_calc": mu_true_calc,
        "mu_estimated_if_ignored": mu_estimated_if_ignored,
        "estimation_bias_delta_mu": mu_err,
        "is_identifiable_from_ax_alone": False
    }
