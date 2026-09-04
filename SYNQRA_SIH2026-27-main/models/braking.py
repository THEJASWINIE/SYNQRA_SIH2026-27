import numpy as np

def calculate_deceleration(mass_kg: float, grade_percent: float, friction_mu: float, 
                          c_rr: float, hardware_max_brake_n: float) -> float:
    """
    Calculate deceleration rate under emergency braking.
    Assumes conservative emergency stopping: aerodynamic drag is not credited.
    
    Formula:
      theta = arctan(grade_percent / 100)  (positive for uphill, negative for downhill)
      F_roll = c_rr * mass * g * cos(theta)
      F_brake_max = friction_mu * mass * g * cos(theta)
      F_brake = min(hardware_max_brake_n, F_brake_max)
      a_dec = (F_brake + F_roll) / mass + g * sin(theta)
      
    Returns:
      Deceleration rate (m/s^2)
    """
    g = 9.81  # m/s^2
    theta = np.arctan(grade_percent / 100.0)
    
    # Force components
    cos_theta = np.cos(theta)
    sin_theta = np.sin(theta)
    
    F_roll = c_rr * mass_kg * g * cos_theta
    F_brake_max = friction_mu * mass_kg * g * cos_theta
    F_brake = min(hardware_max_brake_n, F_brake_max)
    
    # Emergency braking deceleration
    a_dec = (F_brake + F_roll) / mass_kg + g * sin_theta
    return a_dec

def calculate_stopping_distance(v: float, a_dec: float, tau_total: float) -> float:
    """
    Calculate stopping distance based on reaction time and braking deceleration.
    
    Formula:
      S_stop = d_reaction + d_brake
             = v * tau_total + v^2 / (2 * a_dec)
    """
    if a_dec <= 0:
        return float('inf')
    
    d_reaction = v * tau_total
    d_brake = (v ** 2) / (2.0 * a_dec)
    return d_reaction + d_brake

def solve_safe_speed(visibility_m: float, a_dec: float, tau_total: float, s_margin: float) -> float:
    """
    Solve the quadratic inequality for safe speed:
      S_stop + S_margin <= Visibility
      v * tau_total + v^2 / (2 * a_dec) + S_margin <= Visibility
      
    If Visibility <= s_margin, return 0.0.
    If a_dec <= 0.0, return 0.0 (unsafe braking capability).
    """
    if visibility_m <= s_margin or a_dec <= 0.0:
        return 0.0
    
    # Quadratic equation coefficients: A*v^2 + B*v + C = 0
    # A = 1 / (2 * a_dec)
    # B = tau_total
    # C = -(visibility_m - s_margin)
    
    effective_dist = visibility_m - s_margin
    term = (tau_total ** 2) + (2.0 / a_dec) * effective_dist
    
    if term < 0.0:
        return 0.0
        
    v_stop = a_dec * (-tau_total + np.sqrt(term))
    return max(0.0, float(v_stop))
