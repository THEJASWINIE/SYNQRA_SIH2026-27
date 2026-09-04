def calculate_road_capacity(v_safe_mps: float, safe_headway_m: float, min_headway_m: float = 15.5) -> float:
    """
    Calculate the first-order road capacity.
    Formula:
      C_r = 3600 * v_safe / H_safe  [vehicles/hour]
      
    Where:
      H_safe = max(safe_headway_m, min_headway_m)
    """
    if v_safe_mps <= 0.0:
        return 0.0
        
    h_eff = max(safe_headway_m, min_headway_m)
    c_r = 3600.0 * v_safe_mps / h_eff
    return float(c_r)
