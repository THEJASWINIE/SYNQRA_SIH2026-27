import numpy as np
from models.braking import calculate_deceleration, solve_safe_speed

def calculate_acceleration(mass_kg: float, grade_percent: float, speed_mps: float,
                              F_drive: float, F_brake: float, F_retarder: float,
                              c_rr: float, friction_mu: float, drag_cd: float,
                              area_m2: float, rho: float) -> float:
    """
    Calculate the longitudinal acceleration of the vehicle based on force balance:
      m * a_x = F_drive + F_grade - F_roll - F_aero - F_retarder - F_brake
      
    Where:
      F_grade = - m * g * sin(theta)  (opposes motion if uphill, assists if downhill)
      F_roll = c_rr * m * g * cos(theta)
      F_aero = 0.5 * rho * Cd * A * v^2
    """
    g = 9.81
    theta = np.arctan(grade_percent / 100.0)
    cos_theta = np.cos(theta)
    sin_theta = np.sin(theta)
    
    # Friction limits drive and brake forces
    F_mu = friction_mu * mass_kg * g * cos_theta
    F_drive_clamped = min(max(0.0, F_drive), F_mu)
    F_brake_clamped = min(max(0.0, F_brake), F_mu)
    
    # Resistances
    F_roll = c_rr * mass_kg * g * cos_theta
    F_aero = 0.5 * rho * drag_cd * area_m2 * (speed_mps ** 2)
    F_grade = - mass_kg * g * sin_theta
    
    net_force = F_drive_clamped + F_grade - F_roll - F_aero - F_retarder - F_brake_clamped
    a_x = net_force / mass_kg
    return a_x

def calculate_retarder_speed_limit(mass_kg: float, grade_percent: float, c_rr: float, 
                                   max_retarder_power_w: float) -> float:
    """
    Determine downhill retarder continuous speed limit.
    To maintain speed on downhill slope (grade < 0):
      F_ret_required = - m * g * sin(theta) - F_roll
    If F_ret_required > 0:
      P_ret = F_ret_required * v <= max_retarder_power
      v_retarder = max_retarder_power / F_ret_required
    """
    if grade_percent >= 0:
        return float('inf')
        
    g = 9.81
    theta = np.arctan(grade_percent / 100.0)
    cos_theta = np.cos(theta)
    sin_theta = np.sin(theta)
    
    F_roll = c_rr * mass_kg * g * cos_theta
    # Grade force is negative downhill, so -sin(theta) is positive.
    F_ret_required = - mass_kg * g * sin_theta - F_roll
    
    if F_ret_required <= 0:
        return float('inf')
        
    v_retarder = max_retarder_power_w / F_ret_required
    return float(v_retarder)

def calculate_curve_speed_limit(friction_mu: float, curve_radius_m: float) -> float:
    """
    Determine safe speed on curves to avoid lateral sliding.
    Equation:
      v_curve = sqrt(mu * g * R_curve)
    """
    if curve_radius_m <= 0:
        return float('inf')
    g = 9.81
    v_curve = np.sqrt(friction_mu * g * curve_radius_m)
    return float(v_curve)

def calculate_traction_speed_limit(friction_mu: float, traction_speed_factor_mps: float) -> float:
    """
    Determine tractive acceleration safety limit based on local friction adhesion.
    Equation:
      v_traction = factor * mu
    """
    return float(traction_speed_factor_mps * friction_mu)

def resolve_v_safe(mass_kg: float, grade_percent: float, friction_mu: float, 
                   c_rr: float, hardware_max_brake_n: float, max_retarder_power_w: float,
                   curve_radius_m: float, traction_speed_factor_mps: float, speed_limit_mps: float,
                   visibility_m: float, tau_total: float, s_margin: float) -> dict:
    """
    Solve for individual safety limits and return the overall safe speed limit.
    v_safe = min(v_stop, v_retarder, v_traction, v_curve, v_mine)
    """
    # Guard against NaN or negative critical safety values
    if np.isnan(visibility_m) or visibility_m < 0.0 or np.isnan(friction_mu) or friction_mu < 0.0:
        return {
            "v_safe": 0.0,
            "v_stop": 0.0,
            "v_retarder": 0.0,
            "v_curve": 0.0,
            "v_traction": 0.0,
            "v_mine": speed_limit_mps,
            "a_dec": 0.1
        }

    # 1. Stopping speed limit
    a_dec = calculate_deceleration(mass_kg, grade_percent, friction_mu, c_rr, hardware_max_brake_n)
    v_stop = solve_safe_speed(visibility_m, a_dec, tau_total, s_margin)
    
    # 2. Retarder speed limit
    v_retarder = calculate_retarder_speed_limit(mass_kg, grade_percent, c_rr, max_retarder_power_w)
    
    # 3. Curve sliding speed limit
    v_curve = calculate_curve_speed_limit(friction_mu, curve_radius_m)
    
    # 4. Traction speed limit
    v_traction = calculate_traction_speed_limit(friction_mu, traction_speed_factor_mps)
    
    # 5. Mine segment speed limit
    v_mine = speed_limit_mps
    
    # Solve overall minimum
    v_safe = min(v_stop, v_retarder, v_curve, v_traction, v_mine)
    
    return {
        "v_safe": float(v_safe),
        "v_stop": float(v_stop),
        "v_retarder": float(v_retarder),
        "v_curve": float(v_curve),
        "v_traction": float(v_traction),
        "v_mine": float(v_mine),
        "a_dec": float(a_dec)
    }
