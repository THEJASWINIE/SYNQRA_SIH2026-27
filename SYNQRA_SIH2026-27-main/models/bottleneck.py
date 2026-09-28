def calculate_bottleneck_score(arrival_rate_vph: float, service_rate_vph: float, 
                               queue_length: float, criticality: float, 
                               w1: float = 1.0, w2: float = 0.5, w3: float = 1.0) -> float:
    """
    Calculate the bottleneck score for a service node.
    Formula:
      rho = arrival_rate / service_rate (utilization ratio)
      B_j = (w1 * rho) * (1 + w2 * queue_length) * (w3 * criticality)
    """
    if service_rate_vph <= 0.0:
        rho = 999.0  # infinite utilization if service is blocked
    else:
        rho = arrival_rate_vph / service_rate_vph
        
    score = (w1 * rho) * (1.0 + w2 * queue_length) * (w3 * criticality)
    return float(score)
