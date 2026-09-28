"""
Model 7 — Retarder Continuous Downhill Speed Constraint.
Distinguishes continuous downhill speed sustainability from emergency stopping distance.
"""

import numpy as np
from scipy.optimize import root_scalar
from fog_safe.vehicle import MiningVehicle
from fog_safe.road import RoadSegment
from fog_safe.environment import EnvironmentState

def calculate_retarder_force_required(vehicle: MiningVehicle, road: RoadSegment, env: EnvironmentState, v: float) -> float:
    """
    F_retarder_required = m*g*sin(theta) - C_rr*m*g*cos(theta) - 0.5*rho*Cd*A*v^2
    Positive if downhill grade force exceeds rolling resistance + drag.
    """
    f_grade = vehicle.mass * env.g * np.sin(road.theta)
    f_roll = road.c_rr * vehicle.mass * env.g * np.cos(road.theta)
    f_aero = 0.5 * env.rho * vehicle.Cd * vehicle.frontal_area * (v**2)
    return f_grade - f_roll - f_aero

def calculate_retarder_power_required(vehicle: MiningVehicle, road: RoadSegment, env: EnvironmentState, v: float) -> float:
    """
    P_retarder = F_retarder_required * v (Watts).
    """
    f_ret = calculate_retarder_force_required(vehicle, road, env, v)
    return max(0.0, f_ret * v)

def calculate_retarder_speed_limit(
    vehicle: MiningVehicle,
    road: RoadSegment,
    env: EnvironmentState,
    mu: float = 0.35
) -> float:
    """
    Solves for maximum sustainable downhill speed v_retarder where P_retarder(v) <= P_retarder_max.
    Also verifies that net downhill gravity force does not exceed available tire friction.
    Returns v_retarder in m/s (or 0.0 if traction is exceeded, np.inf if retarder not needed).
    """
    f_friction_limit = mu * vehicle.mass * env.g * np.cos(road.theta)
    f_net_gravity = vehicle.mass * env.g * np.sin(road.theta) - road.c_rr * vehicle.mass * env.g * np.cos(road.theta)

    if f_net_gravity > f_friction_limit:
        # Downhill gravity force exceeds available tire friction -> Runaway / Skid risk!
        return 0.0

    if f_net_gravity <= 0:
        # Flat, uphill, or shallow grade where rolling resistance overcomes downhill gravity
        return np.inf

    # Analytical upper bound neglecting aero drag (conservative): v_approx = P_max / f_net_gravity
    v_approx = vehicle.retarder_power_max / f_net_gravity

    # Exact cubic root solver including aero drag: (f_net_gravity - 0.5*rho*Cd*A*v^2)*v = P_max
    c_aero = 0.5 * env.rho * vehicle.Cd * vehicle.frontal_area

    def f_obj(v_val):
        return (f_net_gravity - c_aero * (v_val**2)) * v_val - vehicle.retarder_power_max

    try:
        sol = root_scalar(f_obj, bracket=[0.01, v_approx * 1.5], method='brentq')
        if sol.converged and sol.root > 0:
            return sol.root
    except Exception:
        pass

    return v_approx
