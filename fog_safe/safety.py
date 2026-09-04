"""
Model 6 & Model 8 — Safety Constraint & Multi-Constraint Safe Speed Solver.
Solves for v_safe = min(v_stop, v_retarder, v_traction, v_curve, v_mine).
"""

from dataclasses import dataclass
import numpy as np
from fog_safe.vehicle import MiningVehicle
from fog_safe.road import RoadSegment
from fog_safe.environment import EnvironmentState
from fog_safe.braking import calculate_effective_deceleration
from fog_safe.retarder import calculate_retarder_speed_limit
from fog_safe.communication import CommunicationModel

@dataclass
class SafeSpeedResult:
    """Dataclass holding safe speed solution and full constraint traceability."""
    v_safe_ms: float
    v_safe_kmh: float
    primary_constraint: str
    secondary_constraint: str
    candidate_limits_ms: dict[str, float]
    candidate_limits_kmh: dict[str, float]
    a_dec: float
    s_stop: float
    s_margin: float
    r_effective: float
    is_safe: bool

def calculate_v_stop(
    a_dec: float,
    tau_total: float,
    r_effective: float,
    s_base: float = 5.0,
    k_comm: float = 0.0,
    c_comm: float = 1.0
) -> float:
    """
    Model 6: Analytical solver for stopping-limited speed v_stop with adaptive safety margin.
    Constraint: S_stop(v) + S_margin(v) <= R_effective
    where S_stop(v) = v * tau_total + v^2 / (2 * a_dec)
    and   S_margin(v) = S_base + k_comm * (1 - C_comm) * v
    
    Quadratic equation:
      (1 / (2*a_dec)) * v^2 + [tau_total + k_comm*(1 - C_comm)] * v + (S_base - R_effective) = 0
    
    Let tau_eff_margin = tau_total + k_comm*(1 - C_comm).
    Formula:
      v_stop = -a_dec * tau_eff_margin + sqrt( a_dec^2 * tau_eff_margin^2 + 2 * a_dec * (R_effective - S_base) )
    """
    if r_effective <= s_base or a_dec <= 0:
        return 0.0

    tau_eff_margin = tau_total + k_comm * (1.0 - c_comm)
    delta = (a_dec**2) * (tau_eff_margin**2) + 2.0 * a_dec * (r_effective - s_base)
    if delta < 0:
        return 0.0

    v_stop = -a_dec * tau_eff_margin + np.sqrt(delta)
    return max(0.0, float(v_stop))

def solve_safe_speed(
    vehicle: MiningVehicle,
    road: RoadSegment,
    env: EnvironmentState,
    comm: CommunicationModel,
    mu_effective: float,
    r_effective: float = None
) -> SafeSpeedResult:
    """
    Model 8: Multi-Constraint Safe Speed Solver.
    Computes v_safe = min(v_stop, v_retarder, v_traction, v_curve, v_mine)
    """
    if r_effective is None:
        r_effective = env.r_effective

    tau_total = comm.tau_total

    # 1. Effective Deceleration
    a_dec = calculate_effective_deceleration(vehicle, road, env, mu=mu_effective)

    # 2. v_stop with exact dynamic safety margin formulation
    s_base = comm.margin_params.s_base
    k_comm = comm.margin_params.k_comm
    c_comm = comm.c_comm

    v_stop = calculate_v_stop(
        a_dec=a_dec,
        tau_total=tau_total,
        r_effective=r_effective,
        s_base=s_base,
        k_comm=k_comm,
        c_comm=c_comm
    )

    s_margin_exact = comm.calculate_safety_margin(v=v_stop)

    # 3. v_retarder
    v_retarder = calculate_retarder_speed_limit(vehicle, road, env, mu=mu_effective)

    # 4. v_curve (lateral skid limit)
    if np.isfinite(road.curve_radius) and road.curve_radius > 0:
        v_curve = np.sqrt(max(0.0, mu_effective * env.g * road.curve_radius))
    else:
        v_curve = np.inf

    # 5. v_traction (longitudinal acceleration slip limit over perception distance R_effective)
    a_tr_max = env.g * (mu_effective * np.cos(road.theta) + np.sin(road.theta) - road.c_rr * np.cos(road.theta))
    v_traction = np.sqrt(max(0.0, 2.0 * max(0.1, a_tr_max) * r_effective))

    # 6. v_mine (site speed limit)
    v_mine = road.speed_limit_ms

    candidates_ms = {
        "v_stop": float(v_stop),
        "v_retarder": float(v_retarder),
        "v_traction": float(v_traction),
        "v_curve": float(v_curve),
        "v_mine": float(v_mine)
    }

    candidates_kmh = {k: v * 3.6 for k, v in candidates_ms.items()}

    # Sort constraints by speed limit value
    sorted_constraints = sorted(candidates_ms.items(), key=lambda item: item[1])
    primary_name, v_safe = sorted_constraints[0]
    secondary_name, _ = sorted_constraints[1]

    # Actual stopping distance at v_safe
    s_stop_act = v_safe * tau_total + ((v_safe**2) / (2.0 * a_dec) if a_dec > 0 else np.inf)
    is_safe = (s_stop_act + s_margin_exact <= r_effective + 1e-5) if v_safe > 0 else (r_effective > s_margin_exact)

    return SafeSpeedResult(
        v_safe_ms=v_safe,
        v_safe_kmh=v_safe * 3.6,
        primary_constraint=primary_name,
        secondary_constraint=secondary_name,
        candidate_limits_ms=candidates_ms,
        candidate_limits_kmh=candidates_kmh,
        a_dec=a_dec,
        s_stop=s_stop_act,
        s_margin=s_margin_exact,
        r_effective=r_effective,
        is_safe=is_safe
    )
