"""
Model 2, Model 3 & Model 5 — Tire-Road Friction Limit, Effective Deceleration, and Stopping Distance.
"""

import numpy as np
from fog_safe.vehicle import MiningVehicle
from fog_safe.road import RoadSegment
from fog_safe.environment import EnvironmentState
from fog_safe.dynamics import calculate_grade_force, calculate_rolling_resistance, calculate_aero_drag

def calculate_max_traction_brake_force(vehicle: MiningVehicle, road: RoadSegment, env: EnvironmentState, mu: float) -> float:
    """
    Model 2: Tire-road longitudinal friction limit F_mu = mu * m * g * cos(theta).
    Available braking force cannot exceed this friction limit or hardware max.
    F_available = min(F_hardware_max, mu * m * g * cos(theta))
    """
    f_friction_limit = mu * vehicle.mass * env.g * np.cos(road.theta)
    return min(vehicle.hardware_brake_max, f_friction_limit)

def calculate_effective_deceleration(
    vehicle: MiningVehicle,
    road: RoadSegment,
    env: EnvironmentState,
    mu: float,
    v: float = 0.0,
    include_retarder: bool = True
) -> float:
    """
    Model 3: Effective braking deceleration a_dec (m/s^2) during emergency stopping (F_drive = 0).
    a_dec = [ F_brake_effective + F_roll + F_aero - F_grade ] / m
    where F_brake_effective <= min(F_hardware_max, mu * m * g * cos(theta)).
    
    Returns a_dec (m/s^2). If downhill gravity overcomes friction + drag + roll, a_dec <= 0.
    """
    f_brake_max = calculate_max_traction_brake_force(vehicle, road, env, mu)
    f_roll = calculate_rolling_resistance(vehicle, road, env)
    f_aero = calculate_aero_drag(vehicle, env, v)
    f_grade = calculate_grade_force(vehicle, road, env)

    f_net_retarding = f_brake_max + f_roll + f_aero - f_grade
    a_dec = f_net_retarding / vehicle.mass
    return a_dec

def calculate_stopping_distance(
    vehicle: MiningVehicle,
    road: RoadSegment,
    env: EnvironmentState,
    mu: float,
    v: float,
    tau_total: float
) -> tuple[float, float, float]:
    """
    Model 4 & Model 5: Calculates reaction distance, braking distance, and total stopping distance.
    Returns: (d_reaction, d_brake, S_stop)
    """
    d_reaction = v * tau_total
    a_dec = calculate_effective_deceleration(vehicle, road, env, mu, v=v)

    if a_dec <= 0:
        # Runaway condition: infinite braking distance
        return d_reaction, np.inf, np.inf

    d_brake = (v**2) / (2.0 * a_dec)
    s_stop = d_reaction + d_brake
    return d_reaction, d_brake, s_stop
