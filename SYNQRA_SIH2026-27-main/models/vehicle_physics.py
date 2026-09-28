"""
Compatibility adapter: existing Twin physics API -> authoritative fog_safe solver.

P2 ARCHITECTURAL RULING
-----------------------
`fog_safe` is the SINGLE authoritative runtime physics/safety engine. This module is no
longer a solver. It is a translation layer that:

    existing caller (twin/simulator.py, game_ui.py, optimizer/*)
        -> models.vehicle_physics.resolve_v_safe(...)      <- unchanged public API
        -> fog_safe.safety.solve_safe_speed(...)           <- the authority
        -> SafeSpeedResult
        -> legacy return dict

No safe-speed formula is computed here. Every constraint value returned by this module
comes out of fog_safe.

The authoritative rule is unchanged and enforced inside fog_safe:

    v_safe = min(v_stop, v_retarder, v_traction, v_curve, v_mine)

Command generation (v_command = min(v_dispatch, v_safe)) is NOT done here. It stays with
the callers that already own it.

`calculate_acceleration` below is vehicle *dynamics* used by the simulator's motion
integration, not a safety constraint. It is deliberately left as-is in P2.

COMPATIBILITY MAPPING (every one traceable, no magic constants)
---------------------------------------------------------------
| legacy argument              | fog_safe destination                                   |
|------------------------------|--------------------------------------------------------|
| mass_kg                      | VehicleParameters.mass_loaded == mass_empty (exact)    |
| grade_percent                | RoadSegment.percent_grade = -grade_percent  [SIGN FLIP]|
| friction_mu                  | mu_effective and EnvironmentState.mu_true              |
| c_rr                         | RoadSegment.c_rr                                       |
| hardware_max_brake_n         | VehicleParameters.hardware_brake_max_force             |
| max_retarder_power_w         | VehicleParameters.retarder_power_max                   |
| curve_radius_m (<=0 => none) | RoadSegment.curve_radius (inf when no curve)           |
| speed_limit_mps              | RoadSegment.speed_limit_kmh = speed_limit_mps * 3.6    |
| visibility_m                 | EnvironmentState.r_effective                           |
| tau_total                    | ReactionTimeParameters.tau_sensor, others zeroed       |
| s_margin                     | SafetyMarginParameters.s_base (k_comm = 0)             |
| traction_speed_factor_mps    | solve_safe_speed(traction_ceiling_factor_mps=...)      |

SIGN CONVENTION (the load-bearing detail)
    twin/models: negative grade_percent = downhill  (models/braking.py: a_dec includes
                 + g*sin(arctan(grade/100)), so downhill must be negative to reduce it)
    fog_safe:    positive percent_grade = downhill  (fog_safe/road.py docstring, and
                 tests/test_physics.py::test_downhill_grade_deceleration)
    The adapter therefore negates the grade. This is a convention translation, not a
    physics change: with the flip, fog_safe's a_dec is algebraically identical to the
    previous models/braking.calculate_deceleration.

LATENCY MAPPING
    Legacy callers supply one aggregate `tau_total`. fog_safe decomposes latency into
    sensor + comm + decision + human. The aggregate is placed in the sensor slot and the
    other three are set to zero, so fog_safe's `tau_total` equals the caller's value
    exactly. No latency is invented and none is dropped.

COMMUNICATION DEGRADATION
    The legacy API has no communication-quality input, so the adapter pins C_comm = 1.0
    and k_comm = 0.0. The fog_safe adaptive margin term k_comm*(1-C_comm)*v is therefore
    identically zero and the legacy margin semantics are preserved exactly. Callers that
    want comm-degraded margins should use fog_safe directly (or a future explicit
    argument) rather than having a penalty applied behind their back.

AERODYNAMIC PARAMETERS
    The legacy signature carries no Cd / frontal area / air density. They do not affect
    a_dec or v_stop (fog_safe evaluates emergency deceleration at v = 0, so aero is zero,
    matching the previous "drag is not credited" behaviour). They DO affect v_retarder,
    which fog_safe solves including drag. The optional keyword arguments below default to
    fog_safe's own documented reference values rather than to a made-up number; a caller
    with better data can pass its own.

    LIMITATION: `config/vehicle.yaml` carries drag_coefficient_cd = 0.8 and
    cross_sectional_area_a_m2 = 30.0, which differ from fog_safe's reference 0.7 / 20.0.
    The simulator does not currently pass them to this function. Wiring that through is
    left to a later phase; it is recorded here rather than silently reconciled.

TRACTION CONSTRAINT (both limits apply)
    fog_safe evaluates two traction constraints and takes whichever binds:

      1. physical limit : v_traction = sqrt(2 * a_tr_max * R_effective), with
                          a_tr_max = g*(mu*cos(theta) + sin(theta) - c_rr*cos(theta))
      2. safety ceiling : v_traction_ceiling = traction_speed_factor_mps * mu

    The ceiling is the project's EXISTING `traction_speed_factor_mps` parameter from
    `config/vehicle.yaml`, forwarded unchanged to fog_safe as
    `traction_ceiling_factor_mps`. It is computed inside fog_safe, never here, and it is
    documented there as a safety constraint (fog_safe.config.TractionCeilingParameters).

    The returned legacy key `v_traction` is the binding (tighter) of the two; the
    components are also reported separately as `v_traction_physical` and
    `v_traction_ceiling`.

FRICTION VALIDITY
    Not checked in this adapter. fog_safe fails closed on mu <= 0 or non-finite mu,
    returning v_safe = 0.0 and primary_constraint "INVALID_FRICTION", so every caller of
    the authoritative solver gets that protection - not only callers routed through here.
"""

import numpy as np

from fog_safe.communication import CommunicationModel
from fog_safe.config import (
    EnvironmentParameters,
    ReactionTimeParameters,
    SafetyMarginParameters,
    VehicleParameters,
)
from fog_safe.environment import EnvironmentState
from fog_safe.road import RoadSegment
from fog_safe.safety import solve_safe_speed as _fog_safe_solve
from fog_safe.vehicle import MiningVehicle

# fog_safe reference aerodynamic values (fog_safe/config.py VehicleParameters /
# EnvironmentParameters). Used only when a caller supplies nothing better.
_DEFAULT_CD = VehicleParameters().drag_coefficient
_DEFAULT_AREA_M2 = VehicleParameters().frontal_area
_DEFAULT_AIR_DENSITY = EnvironmentParameters().air_density


def calculate_acceleration(mass_kg: float, grade_percent: float, speed_mps: float,
                              F_drive: float, F_brake: float, F_retarder: float,
                              c_rr: float, friction_mu: float, drag_cd: float,
                              area_m2: float, rho: float) -> float:
    """
    Longitudinal acceleration from the force balance:
      m * a_x = F_drive + F_grade - F_roll - F_aero - F_retarder - F_brake

    This is motion integration used by twin/simulator.py, NOT a safety constraint, and is
    intentionally unchanged in P2. Its grade convention is the twin one (negative =
    downhill), matching every existing caller.
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


def _build_fog_safe_inputs(
    mass_kg, grade_percent, friction_mu, c_rr, hardware_max_brake_n,
    max_retarder_power_w, curve_radius_m, speed_limit_mps, visibility_m,
    tau_total, s_margin, drag_coefficient_cd, cross_sectional_area_a_m2,
    air_density_rho_kg_m3,
):
    """Translate the legacy argument list into canonical fog_safe objects. See module docstring."""
    veh_params = VehicleParameters(
        mass_empty=mass_kg,
        mass_loaded=mass_kg,          # legacy callers pass an explicit mass; no load lookup
        frontal_area=cross_sectional_area_a_m2,
        drag_coefficient=drag_coefficient_cd,
        retarder_power_max=max_retarder_power_w,
        hardware_brake_max_force=hardware_max_brake_n,
    )
    vehicle = MiningVehicle(params=veh_params, is_loaded=True)

    road = RoadSegment(
        percent_grade=-grade_percent,   # SIGN FLIP: twin negative-downhill -> fog_safe positive-downhill
        c_rr=c_rr,
        curve_radius=float(curve_radius_m) if curve_radius_m and curve_radius_m > 0 else np.inf,
        speed_limit_kmh=speed_limit_mps * 3.6,
    )

    env = EnvironmentState(
        r_effective=visibility_m,
        mu_true=friction_mu,
        env_params=EnvironmentParameters(air_density=air_density_rho_kg_m3),
    )

    comm = CommunicationModel(
        c_comm=1.0,                     # legacy API has no comm-quality input
        rx_params=ReactionTimeParameters(
            tau_sensor=tau_total,       # aggregate latency preserved exactly
            tau_comm_base=0.0,
            tau_decision=0.0,
            tau_human=0.0,
        ),
        margin_params=SafetyMarginParameters(s_base=s_margin, k_comm=0.0),
    )
    return vehicle, road, env, comm


def resolve_v_safe(mass_kg: float, grade_percent: float, friction_mu: float,
                   c_rr: float, hardware_max_brake_n: float, max_retarder_power_w: float,
                   curve_radius_m: float, traction_speed_factor_mps: float, speed_limit_mps: float,
                   visibility_m: float, tau_total: float, s_margin: float,
                   drag_coefficient_cd: float = _DEFAULT_CD,
                   cross_sectional_area_a_m2: float = _DEFAULT_AREA_M2,
                   air_density_rho_kg_m3: float = _DEFAULT_AIR_DENSITY) -> dict:
    """
    Resolve the overall safe speed limit. COMPATIBILITY ADAPTER - the calculation itself
    is performed by fog_safe.safety.solve_safe_speed.

    v_safe = min(v_stop, v_retarder, v_curve, v_traction, v_mine), all in m/s.

    `traction_speed_factor_mps` is accepted for API compatibility and ignored; fog_safe
    derives the traction limit from physics (see module docstring).

    Returns the legacy dict shape, plus additive diagnostic keys that existing callers
    are free to ignore.
    """
    # Input validation at the trust boundary. Unusable safety inputs must never produce an
    # optimistic speed.
    #
    # Visibility validity is checked here (it is an adapter input-domain concern).
    # FRICTION validity is NOT checked here - fog_safe owns it, so that every caller of the
    # authoritative solver inherits the same fail-closed behaviour rather than only the
    # ones that come through this adapter. An unusable mu returns v_safe = 0.0 with
    # primary_constraint "INVALID_FRICTION".
    if np.isnan(visibility_m) or visibility_m < 0.0:
        return {
            "v_safe": 0.0,
            "v_stop": 0.0,
            "v_retarder": 0.0,
            "v_curve": 0.0,
            "v_traction": 0.0,
            "v_mine": speed_limit_mps,
            "a_dec": 0.1,
            "primary_constraint": "INVALID_INPUT",
            "secondary_constraint": "INVALID_INPUT",
            "is_safe": False,
            "s_stop": 0.0,
            "s_margin": s_margin,
            "r_effective": visibility_m,
            "v_safe_kmh": 0.0,
            "engine": "fog_safe",
            "units": "m/s",
        }

    vehicle, road, env, comm = _build_fog_safe_inputs(
        mass_kg, grade_percent, friction_mu, c_rr, hardware_max_brake_n,
        max_retarder_power_w, curve_radius_m, speed_limit_mps, visibility_m,
        tau_total, s_margin, drag_coefficient_cd, cross_sectional_area_a_m2,
        air_density_rho_kg_m3,
    )

    result = _fog_safe_solve(
        vehicle=vehicle,
        road=road,
        env=env,
        comm=comm,
        mu_effective=friction_mu,
        r_effective=visibility_m,
        # Forwarded, not computed here: fog_safe owns the ceiling constraint.
        traction_ceiling_factor_mps=traction_speed_factor_mps,
    )

    limits = result.candidate_limits_ms
    return {
        # -- legacy keys (unchanged names, unchanged units: m/s, m/s^2) --
        "v_safe": float(result.v_safe_ms),
        "v_stop": float(limits["v_stop"]),
        "v_retarder": float(limits["v_retarder"]),
        "v_curve": float(limits["v_curve"]),
        # Legacy `v_traction` reports the BINDING traction constraint, i.e. the tighter of
        # the physical limit and the configured conservative ceiling. The two are also
        # exposed separately below for diagnostics.
        "v_traction": float(min(limits["v_traction"], limits.get("v_traction_ceiling", float("inf")))),
        "v_traction_physical": float(limits["v_traction"]),
        "v_traction_ceiling": float(limits.get("v_traction_ceiling", float("inf"))),
        "v_mine": float(limits["v_mine"]),
        "a_dec": float(result.a_dec),
        # -- additive diagnostics from the canonical result --
        "primary_constraint": result.primary_constraint,
        "secondary_constraint": result.secondary_constraint,
        "is_safe": bool(result.is_safe),
        "s_stop": float(result.s_stop),
        "s_margin": float(result.s_margin),
        "r_effective": float(result.r_effective),
        "v_safe_kmh": float(result.v_safe_kmh),
        "engine": "fog_safe",
        "units": "m/s",
    }


# ---------------------------------------------------------------------------
# Legacy single-constraint helpers.
#
# Kept for API compatibility (models/tests import them). Each one now reads its
# constraint out of the authoritative solver instead of recomputing it, so no duplicate
# safety formula survives in this module.
# ---------------------------------------------------------------------------

# Placeholder inputs for helpers that expose a constraint depending on only a subset of
# the state. They are chosen to leave the requested constraint untouched, and each helper
# documents which inputs actually matter.
_HELPER_PLACEHOLDER = dict(
    mass_kg=165000.0,
    hardware_max_brake_n=600000.0,
    max_retarder_power_w=1200000.0,
    traction_speed_factor_mps=30.0,
    speed_limit_mps=1e9,
    visibility_m=1e9,
    tau_total=0.25,
    s_margin=5.0,
)


def calculate_retarder_speed_limit(mass_kg: float, grade_percent: float, c_rr: float,
                                   max_retarder_power_w: float, friction_mu: float = 0.35) -> float:
    """
    Continuous downhill retarder speed limit (m/s), delegated to fog_safe.

    Depends on mass, grade, rolling resistance and retarder power. `friction_mu` defaults
    to fog_safe's own reference prior (0.35) and is used only for fog_safe's runaway-skid
    check, which the previous local implementation did not perform.
    """
    kwargs = dict(_HELPER_PLACEHOLDER)
    kwargs.update(
        mass_kg=mass_kg,
        grade_percent=grade_percent,
        c_rr=c_rr,
        max_retarder_power_w=max_retarder_power_w,
        friction_mu=friction_mu,
        curve_radius_m=0.0,
    )
    return float(resolve_v_safe(**kwargs)["v_retarder"])


def calculate_curve_speed_limit(friction_mu: float, curve_radius_m: float) -> float:
    """
    Lateral (skid) curve speed limit (m/s), delegated to fog_safe.

    Depends only on friction and curve radius: v_curve = sqrt(mu * g * R).
    """
    kwargs = dict(_HELPER_PLACEHOLDER)
    kwargs.update(
        grade_percent=0.0,
        friction_mu=friction_mu,
        c_rr=0.02,
        curve_radius_m=curve_radius_m,
    )
    return float(resolve_v_safe(**kwargs)["v_curve"])


def calculate_traction_speed_limit(friction_mu: float, traction_speed_factor_mps: float,
                                   c_rr: float = 0.02, grade_percent: float = 0.0,
                                   visibility_m: float = 50.0) -> float:
    """
    Longitudinal traction speed limit (m/s), delegated to fog_safe.

    NOTE: fog_safe derives this from physics over the effective perception range rather
    than from `traction_speed_factor_mps`, which is ignored (kept for API compatibility).
    Because the fog_safe model depends on grade, rolling resistance and perception range,
    those are exposed as explicit arguments instead of being assumed.
    """
    kwargs = dict(_HELPER_PLACEHOLDER)
    kwargs.update(
        grade_percent=grade_percent,
        friction_mu=friction_mu,
        c_rr=c_rr,
        curve_radius_m=0.0,
        traction_speed_factor_mps=traction_speed_factor_mps,
        visibility_m=visibility_m,
    )
    return float(resolve_v_safe(**kwargs)["v_traction"])
