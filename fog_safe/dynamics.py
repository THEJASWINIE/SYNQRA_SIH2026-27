"""
Model 1 & Model 3 — Longitudinal Vehicle Dynamics & Force Balance equations.
Coordinates:
  +x direction = downhill travel direction (v > 0)
  theta > 0 = downhill grade angle
  F_grade = m g sin(theta)
  F_roll  = C_rr m g cos(theta)
  F_aero  = 0.5 * rho * Cd * A * v^2
"""

import numpy as np
from fog_safe.vehicle import MiningVehicle
from fog_safe.road import RoadSegment
from fog_safe.environment import EnvironmentState

def calculate_grade_force(vehicle: MiningVehicle, road: RoadSegment, env: EnvironmentState) -> float:
    """
    Downhill gravity force component: F_grade = m * g * sin(theta).
    Positive for downhill (theta > 0), pulling vehicle forward.
    """
    return vehicle.mass * env.g * np.sin(road.theta)

def calculate_rolling_resistance(vehicle: MiningVehicle, road: RoadSegment, env: EnvironmentState) -> float:
    """
    Rolling resistance force opposing motion: F_roll = C_rr * m * g * cos(theta).
    Always positive magnitude opposing velocity.
    """
    return road.c_rr * vehicle.mass * env.g * np.cos(road.theta)

def calculate_aero_drag(vehicle: MiningVehicle, env: EnvironmentState, v: float) -> float:
    """
    Aerodynamic drag force: F_aero = 0.5 * rho * Cd * A * v^2.
    """
    return 0.5 * env.rho * vehicle.Cd * vehicle.frontal_area * (v**2)

def calculate_longitudinal_acceleration(
    vehicle: MiningVehicle,
    road: RoadSegment,
    env: EnvironmentState,
    v: float,
    f_drive: float = 0.0,
    f_brake: float = 0.0,
    f_retarder: float = 0.0
) -> float:
    """
    Computes dv/dt from force balance:
    m * a_x = F_drive + m*g*sin(theta) - C_rr*m*g*cos(theta) - F_aero - F_retarder - F_brake
    """
    f_grade = calculate_grade_force(vehicle, road, env)
    f_roll = calculate_rolling_resistance(vehicle, road, env)
    f_aero = calculate_aero_drag(vehicle, env, v)

    f_net = f_drive + f_grade - f_roll - f_aero - f_retarder - f_brake
    return f_net / vehicle.mass
