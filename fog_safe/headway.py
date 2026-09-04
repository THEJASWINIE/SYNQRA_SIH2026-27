"""
Model 9 — Dynamic Safe Headway & Time Headway Model.
Derives conservative longitudinal separation H_safe based on differential braking capabilities and latency.
"""

import numpy as np

def calculate_safe_headway(
    v_follower: float,
    v_leader: float,
    a_follower: float,
    a_leader: float,
    tau_total: float,
    s_margin: float = 5.0,
    assume_brick_wall: bool = True
) -> tuple[float, float]:
    """
    Calculates minimum safe longitudinal headway distance H_safe (m) and time headway T_headway (s).
    
    Formula:
      d_react = v_f * tau_total
      d_brake_f = v_f^2 / (2 * a_f) if a_f > 0 else inf
      d_brake_l = 0.0 (if assume_brick_wall) else v_l^2 / (2 * a_l)
      H_safe = d_react + d_brake_f - d_brake_l + s_margin
      T_headway = H_safe / v_f
    
    Returns: (H_safe, T_headway)
    """
    if v_follower <= 0:
        return s_margin, np.inf

    if a_follower <= 0:
        return np.inf, np.inf

    d_react = v_follower * tau_total
    d_brake_f = (v_follower**2) / (2.0 * a_follower)

    if assume_brick_wall:
        d_brake_l = 0.0
    else:
        d_brake_l = (v_leader**2) / (2.0 * a_leader) if (a_leader > 0 and v_leader > 0) else 0.0

    h_safe = d_react + d_brake_f - d_brake_l + s_margin

    # Headway cannot be smaller than safety margin
    h_safe = max(s_margin, h_safe)
    t_headway = h_safe / v_follower

    return h_safe, t_headway
