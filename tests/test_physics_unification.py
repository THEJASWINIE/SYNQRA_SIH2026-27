"""
P2 — physics/safety unification tests.

Proves that `models.vehicle_physics` is a compatibility adapter over `fog_safe`, that the
legacy caller contract survives, and that no duplicate safety formula remains behind.
"""

import inspect
import math
from unittest import mock

import numpy as np
import pytest

from models import vehicle_physics
from models.vehicle_physics import (
    calculate_curve_speed_limit,
    calculate_retarder_speed_limit,
    calculate_traction_speed_limit,
    resolve_v_safe,
)

LEGACY_KEYS = ("v_safe", "v_stop", "v_retarder", "v_curve", "v_traction", "v_mine", "a_dec")

BASE = dict(
    mass_kg=165000.0,
    grade_percent=0.0,
    friction_mu=0.60,
    c_rr=0.02,
    hardware_max_brake_n=600000.0,
    max_retarder_power_w=1200000.0,
    curve_radius_m=0.0,
    traction_speed_factor_mps=30.0,
    speed_limit_mps=13.89,
    visibility_m=50.0,
    tau_total=0.25,
    s_margin=5.0,
)


def call(**over):
    kw = dict(BASE)
    kw.update(over)
    return resolve_v_safe(**kw)


# ---------------------------------------------------------------------
# 1. resolve_v_safe still exists with the legacy signature
# ---------------------------------------------------------------------

def test_resolve_v_safe_still_exists_with_legacy_signature():
    assert callable(resolve_v_safe)

    params = list(inspect.signature(resolve_v_safe).parameters)
    legacy_positional = [
        "mass_kg", "grade_percent", "friction_mu", "c_rr", "hardware_max_brake_n",
        "max_retarder_power_w", "curve_radius_m", "traction_speed_factor_mps",
        "speed_limit_mps", "visibility_m", "tau_total", "s_margin",
    ]
    # Legacy positional order preserved exactly; new args may only be appended.
    assert params[: len(legacy_positional)] == legacy_positional

    # Positional call (as twin/simulator.py and verify_task2.py do) still works.
    res = resolve_v_safe(165000.0, -8.0, 0.60, 0.02, 600000.0, 1200000.0, 50.0, 30.0, 11.11, 30.0, 0.25, 5.0)
    assert set(LEGACY_KEYS).issubset(res)


def test_legacy_return_shape_preserved():
    res = call()
    for key in LEGACY_KEYS:
        assert key in res, f"legacy key {key} disappeared"
        assert isinstance(res[key], float)


# ---------------------------------------------------------------------
# 2. existing Twin callers still work
# ---------------------------------------------------------------------

def test_twin_simulator_still_runs_end_to_end():
    from run_baseline_vs_orchestrator import build_graph, load_configs
    from twin.simulator import Simulator

    vehicle_cfg, roads_cfg, nodes_cfg, weather_cfg, scenario_cfg = load_configs()
    network = build_graph(nodes_cfg, roads_cfg)
    sim = Simulator(network, vehicle_cfg, weather_cfg, dict(scenario_cfg))

    for _ in range(30):
        sim.run_step()

    assert sim.current_time > 0
    for edge in sim.network.edges.values():
        assert edge.v_safe_mps >= 0.0
        assert np.isfinite(edge.v_safe_mps)
        assert edge.v_safe_mps <= edge.speed_limit_mps + 1e-9   # site limit is never exceeded
    for v in sim.vehicles:
        assert v.v_command_mps <= v.v_safe_mps + 1e-9           # governor still clamps


def test_optimizer_callers_still_work():
    from optimizer.milp_dispatch import DeterministicMPC

    mpc = DeterministicMPC(
        horizon_s=600.0, step_s=10.0, crusher_service_rate_vph=10.0,
        shovel_service_rate_vph=15.0,
        vehicle_config={
            "gross_mass_kg": 165000.0, "tare_mass_kg": 74000.0, "payload_mass_kg": 91000.0,
            "hardware_max_brake_force_n": 600000.0, "max_retarder_power_w": 1200000.0,
            "traction_speed_factor_mps": 30.0, "ecu_hydraulic_latency_s": 0.25,
            "safety_stop_margin_m": 5.0, "safety_headway_margin_m": 5.0,
            "min_static_headway_m": 15.5,
        },
        road_config={
            "grade_percent": -8.0, "friction_mu": 0.35, "c_rr": 0.02,
            "curve_radius_m": 50.0, "speed_limit_mps": 11.11,
        },
    )
    delay = mpc.optimize_release_rate(3, np.full(60, 30.0))
    assert delay >= 0.0


# ---------------------------------------------------------------------
# 3. resolve_v_safe actually delegates to fog_safe
# ---------------------------------------------------------------------

def test_resolve_v_safe_delegates_to_fog_safe():
    """If fog_safe is not consulted, this test fails. No silent local fallback."""
    with mock.patch("models.vehicle_physics._fog_safe_solve", wraps=vehicle_physics._fog_safe_solve) as spy:
        res = call(visibility_m=30.0)
    assert spy.call_count == 1, "resolve_v_safe did not call fog_safe.safety.solve_safe_speed"
    assert res["engine"] == "fog_safe"


def test_delegation_passes_translated_inputs():
    """The adapter must hand fog_safe the canonical objects, with the grade sign flipped."""
    with mock.patch("models.vehicle_physics._fog_safe_solve", wraps=vehicle_physics._fog_safe_solve) as spy:
        call(grade_percent=-8.0, friction_mu=0.35, visibility_m=25.0, speed_limit_mps=11.11)

    kwargs = spy.call_args.kwargs
    road, env = kwargs["road"], kwargs["env"]

    # SIGN FLIP: twin negative-downhill becomes fog_safe positive-downhill.
    assert road.percent_grade == pytest.approx(8.0)
    assert road.theta > 0.0, "downhill must be theta > 0 in fog_safe convention"
    assert road.speed_limit_ms == pytest.approx(11.11)
    assert env.r_effective == pytest.approx(25.0)
    assert kwargs["mu_effective"] == pytest.approx(0.35)


def test_adapter_result_equals_direct_fog_safe_call():
    """The adapter adds no arithmetic of its own on top of the canonical result."""
    from fog_safe.communication import CommunicationModel
    from fog_safe.config import (
        EnvironmentParameters, ReactionTimeParameters, SafetyMarginParameters, VehicleParameters,
    )
    from fog_safe.environment import EnvironmentState
    from fog_safe.road import RoadSegment
    from fog_safe.safety import solve_safe_speed
    from fog_safe.vehicle import MiningVehicle

    veh = MiningVehicle(
        params=VehicleParameters(
            mass_empty=165000.0, mass_loaded=165000.0,
            frontal_area=VehicleParameters().frontal_area,
            drag_coefficient=VehicleParameters().drag_coefficient,
            retarder_power_max=1200000.0, hardware_brake_max_force=600000.0,
        ),
        is_loaded=True,
    )
    road = RoadSegment(percent_grade=8.0, c_rr=0.02, curve_radius=50.0, speed_limit_kmh=11.11 * 3.6)
    env = EnvironmentState(r_effective=25.0, mu_true=0.35, env_params=EnvironmentParameters())
    comm = CommunicationModel(
        c_comm=1.0,
        rx_params=ReactionTimeParameters(tau_sensor=0.25, tau_comm_base=0.0, tau_decision=0.0, tau_human=0.0),
        margin_params=SafetyMarginParameters(s_base=5.0, k_comm=0.0),
    )
    # Like-for-like: the adapter forwards the configured traction ceiling, so the direct
    # call must supply it too.
    direct = solve_safe_speed(
        veh, road, env, comm, mu_effective=0.35, r_effective=25.0,
        traction_ceiling_factor_mps=30.0,
    )

    via_adapter = call(
        grade_percent=-8.0, friction_mu=0.35, curve_radius_m=50.0,
        speed_limit_mps=11.11, visibility_m=25.0, traction_speed_factor_mps=30.0,
    )

    assert via_adapter["v_safe"] == pytest.approx(direct.v_safe_ms)
    assert via_adapter["a_dec"] == pytest.approx(direct.a_dec)
    for key in ("v_stop", "v_retarder", "v_curve", "v_mine"):
        assert via_adapter[key] == pytest.approx(direct.candidate_limits_ms[key])
    assert via_adapter["v_traction_physical"] == pytest.approx(direct.candidate_limits_ms["v_traction"])
    assert via_adapter["v_traction_ceiling"] == pytest.approx(direct.candidate_limits_ms["v_traction_ceiling"])


def test_legacy_helpers_delegate_too():
    for fn, args in (
        (calculate_retarder_speed_limit, (165000.0, -8.0, 0.02, 1200000.0)),
        (calculate_curve_speed_limit, (0.35, 50.0)),
        (calculate_traction_speed_limit, (0.35, 30.0)),
    ):
        with mock.patch("models.vehicle_physics._fog_safe_solve", wraps=vehicle_physics._fog_safe_solve) as spy:
            fn(*args)
        assert spy.call_count >= 1, f"{fn.__name__} did not delegate to fog_safe"


# ---------------------------------------------------------------------
# 4. no duplicate local safety formula remains in the adapter
# ---------------------------------------------------------------------

def test_no_duplicate_safety_formula_in_adapter():
    """
    Guards against a local solver creeping back in. The adapter must not contain the
    stopping-distance quadratic, the curve formula or a retarder power division.
    """
    src = inspect.getsource(vehicle_physics)
    segments = src.split('"""')
    executable = "".join(segments[::2])  # drop docstring segments
    executable = "\n".join(
        line for line in executable.splitlines() if not line.strip().startswith("#")
    )

    banned = [
        "np.sqrt",          # curve / traction / quadratic solutions
        "math.sqrt",
        "root_scalar",
        "retarder_power_max /",
        "max_retarder_power_w /",
    ]
    for token in banned:
        assert token not in executable, f"adapter appears to recompute safety physics: {token!r}"

    # It must, however, import the authority.
    assert "from fog_safe.safety import solve_safe_speed" in src


def test_braking_module_is_no_longer_the_safety_authority():
    """models/braking.py must not be reachable from the adapter's safe-speed path."""
    src = inspect.getsource(vehicle_physics)
    assert "from models.braking import" not in src
    assert "import models.braking" not in src


# ---------------------------------------------------------------------
# 5. units remain explicit and correct
# ---------------------------------------------------------------------

def test_units_are_explicit_and_consistent():
    res = call(visibility_m=30.0)
    assert res["units"] == "m/s"
    # km/h diagnostic is exactly 3.6x the m/s value — no unit drift.
    assert res["v_safe_kmh"] == pytest.approx(res["v_safe"] * 3.6)
    # Site limit round-trips through fog_safe's km/h storage without loss.
    assert res["v_mine"] == pytest.approx(BASE["speed_limit_mps"])


def test_speed_limit_round_trip_is_exact():
    for limit in (5.56, 11.11, 13.89, 20.0):
        assert call(speed_limit_mps=limit)["v_mine"] == pytest.approx(limit)


# ---------------------------------------------------------------------
# 6. deterministic outputs
# ---------------------------------------------------------------------

def test_outputs_are_deterministic():
    cases = [
        dict(visibility_m=50.0),
        dict(visibility_m=15.0, friction_mu=0.25, grade_percent=-8.0),
        dict(visibility_m=10.0, friction_mu=0.15, grade_percent=-10.0, curve_radius_m=40.0),
    ]
    for kw in cases:
        runs = [call(**kw) for _ in range(5)]
        for other in runs[1:]:
            for key in LEGACY_KEYS:
                assert other[key] == runs[0][key], f"non-deterministic {key} for {kw}"


# ---------------------------------------------------------------------
# 7. constraint attribution remains available
# ---------------------------------------------------------------------

def test_primary_constraint_is_reported_and_correct():
    res = call(speed_limit_mps=5.56, visibility_m=50.0)
    assert res["primary_constraint"] == "v_mine"
    assert res["v_safe"] == pytest.approx(res["v_mine"])

    res = call(visibility_m=15.0)
    assert res["primary_constraint"] == "v_stop"
    assert res["v_safe"] == pytest.approx(res["v_stop"])

    res = call(curve_radius_m=20.0, visibility_m=50.0)
    assert res["primary_constraint"] == "v_curve"

    res = call(grade_percent=-8.0, max_retarder_power_w=300000.0, visibility_m=50.0)
    assert res["primary_constraint"] == "v_retarder"

    assert "secondary_constraint" in res


def test_v_safe_is_the_minimum_of_all_constraints():
    """The authoritative rule: v_safe = min(v_stop, v_retarder, v_traction, v_curve, v_mine)."""
    for kw in (
        dict(visibility_m=50.0),
        dict(visibility_m=15.0, friction_mu=0.25),
        dict(grade_percent=-12.0, visibility_m=40.0),
        dict(curve_radius_m=20.0),
        dict(speed_limit_mps=5.56),
        dict(grade_percent=-10.0, friction_mu=0.15, curve_radius_m=40.0, visibility_m=10.0),
    ):
        res = call(**kw)
        # v_traction already reports the binding of (physical, ceiling).
        expected = min(
            res["v_stop"], res["v_retarder"], res["v_traction"],
            res["v_traction_ceiling"], res["v_curve"], res["v_mine"],
        )
        assert res["v_safe"] == pytest.approx(expected), f"v_safe is not the binding minimum for {kw}"


# ---------------------------------------------------------------------
# 8. invalid / unknown inputs never produce an optimistic safe speed
# ---------------------------------------------------------------------

@pytest.mark.parametrize(
    "bad,reason",
    [
        # Visibility validity is an adapter input-domain concern.
        (dict(visibility_m=float("nan")), "INVALID_INPUT"),
        (dict(visibility_m=-10.0), "INVALID_INPUT"),
        # Friction validity is owned by the authoritative solver (D2).
        (dict(friction_mu=float("nan")), "INVALID_FRICTION"),
        (dict(friction_mu=-0.5), "INVALID_FRICTION"),
        (dict(friction_mu=0.0), "INVALID_FRICTION"),
        (dict(friction_mu=float("inf")), "INVALID_FRICTION"),
        (dict(friction_mu=float("-inf")), "INVALID_FRICTION"),
    ],
)
def test_invalid_inputs_fail_closed(bad, reason):
    res = call(**bad)
    assert res["v_safe"] == 0.0
    assert res["v_stop"] == 0.0
    assert res["v_traction"] == 0.0
    assert res["is_safe"] is False
    assert res["primary_constraint"] == reason


def test_visibility_below_margin_gives_zero_speed():
    res = call(visibility_m=4.0, s_margin=5.0)
    assert res["v_stop"] == 0.0
    assert res["v_safe"] == 0.0


# ---------------------------------------------------------------------
# D2 — zero / invalid friction must fail closed
# ---------------------------------------------------------------------

def test_d2_zero_friction_fails_closed():
    """
    mu = 0 must never yield a positive permitted speed.

    Interim P2 behaviour (before this correction) let fog_safe's internal
    max(0.1, a_tr_max) floor turn mu = 0 into v_safe = 3.1623 m/s. That is now rejected
    at the top of the authoritative solver.
    """
    res = call(friction_mu=0.0, visibility_m=50.0)
    assert res["v_safe"] == 0.0
    assert res["is_safe"] is False
    assert res["primary_constraint"] == "INVALID_FRICTION"
    for key in ("v_stop", "v_retarder", "v_traction", "v_curve"):
        assert res[key] == 0.0


@pytest.mark.parametrize("mu", [0.0, -0.001, -0.5, float("nan"), float("inf"), float("-inf")])
def test_d2_unusable_friction_never_permits_motion(mu):
    for vis in (5.0, 15.0, 50.0, 200.0):
        res = call(friction_mu=mu, visibility_m=vis)
        assert res["v_safe"] == 0.0, f"mu={mu} vis={vis} permitted {res['v_safe']} m/s"
        assert res["is_safe"] is False


def test_d2_enforced_in_fog_safe_not_only_in_the_adapter():
    """Every caller of the authoritative solver inherits the fail-closed behaviour."""
    from fog_safe.communication import CommunicationModel
    from fog_safe.environment import EnvironmentState
    from fog_safe.road import RoadSegment
    from fog_safe.safety import solve_safe_speed
    from fog_safe.vehicle import MiningVehicle

    veh, road = MiningVehicle(), RoadSegment(percent_grade=0.0)
    env, comm = EnvironmentState(r_effective=50.0, mu_true=0.0), CommunicationModel()

    for mu in (0.0, -0.2, float("nan"), float("inf")):
        res = solve_safe_speed(veh, road, env, comm, mu_effective=mu, r_effective=50.0)
        assert res.v_safe_ms == 0.0
        assert res.is_safe is False
        assert res.primary_constraint == "INVALID_FRICTION"


def test_d2_very_small_positive_friction_is_effectively_zero():
    """
    mu just above zero is NOT treated as invalid (it is a real, if useless, estimate).
    The ceiling makes the permitted speed vanish with mu, which is the intended response.

    Note the residual reported in P2: `is_safe` stays True here because the stopping
    constraint is trivially satisfiable at ~0 m/s. The permitted speed is what matters,
    and it is ~0.
    """
    res = call(friction_mu=1e-9, visibility_m=50.0)
    assert res["v_safe"] < 1e-6
    assert res["primary_constraint"] == "v_traction_ceiling"


# ---------------------------------------------------------------------
# D1 — explicit, named, configurable conservative traction ceiling
# ---------------------------------------------------------------------

def test_d1_low_friction_relaxation_is_rejected():
    """The 94% low-friction relaxation is gone; pre-P2 conservatism is restored exactly."""
    res = call(friction_mu=0.15, visibility_m=30.0)
    assert res["v_safe"] == pytest.approx(4.5, abs=1e-9)          # pre-P2 value
    assert res["primary_constraint"] == "v_traction_ceiling"      # and it is attributed


def test_d1_ceiling_is_named_and_attributed():
    res = call(friction_mu=0.15, visibility_m=30.0)
    assert "v_traction_ceiling" in res
    assert res["v_traction_ceiling"] == pytest.approx(30.0 * 0.15)
    # Both traction components remain separately visible for diagnostics.
    assert res["v_traction_physical"] > res["v_traction_ceiling"]
    assert res["v_traction"] == pytest.approx(res["v_traction_ceiling"])


def test_d1_ceiling_is_configurable_and_participates_in_the_minimum():
    """A tighter configured factor must bind; a looser one must not invent restriction."""
    tight = call(friction_mu=0.60, visibility_m=50.0, traction_speed_factor_mps=5.0)
    assert tight["v_safe"] == pytest.approx(3.0, abs=1e-9)        # 5.0 * 0.60
    assert tight["primary_constraint"] == "v_traction_ceiling"

    loose = call(friction_mu=0.60, visibility_m=50.0, traction_speed_factor_mps=1000.0)
    assert loose["primary_constraint"] != "v_traction_ceiling"


def test_d1_ceiling_is_not_applied_when_unconfigured():
    """fog_safe must not assume a ceiling the caller never supplied."""
    from fog_safe.communication import CommunicationModel
    from fog_safe.environment import EnvironmentState
    from fog_safe.road import RoadSegment
    from fog_safe.safety import solve_safe_speed
    from fog_safe.vehicle import MiningVehicle

    veh, road = MiningVehicle(), RoadSegment(percent_grade=0.0)
    env, comm = EnvironmentState(r_effective=50.0, mu_true=0.35), CommunicationModel()

    without = solve_safe_speed(veh, road, env, comm, mu_effective=0.35, r_effective=50.0)
    assert "v_traction_ceiling" not in without.candidate_limits_ms

    with_ceiling = solve_safe_speed(
        veh, road, env, comm, mu_effective=0.35, r_effective=50.0,
        traction_ceiling_factor_mps=30.0,
    )
    assert with_ceiling.candidate_limits_ms["v_traction_ceiling"] == pytest.approx(10.5)


def test_d1_ceiling_is_computed_in_fog_safe_not_in_the_adapter():
    """The adapter forwards the factor; it must not multiply it out locally."""
    src = inspect.getsource(vehicle_physics)
    executable = "".join(src.split('"""')[::2])
    executable = "\n".join(l for l in executable.splitlines() if not l.strip().startswith("#"))
    assert "traction_speed_factor_mps *" not in executable
    assert "* friction_mu" not in executable
    assert "traction_ceiling_factor_mps=traction_speed_factor_mps" in executable


# ---------------------------------------------------------------------
# 9/10. fog response stays monotonic and meaningful (demo acceptance)
# ---------------------------------------------------------------------

def test_visibility_monotonicity_after_unification():
    """More fog must never raise the safe speed."""
    prev = float("inf")
    for vis in (50.0, 40.0, 30.0, 25.0, 20.0, 15.0, 10.0, 8.0, 6.0):
        v_safe = call(visibility_m=vis, speed_limit_mps=25.0)["v_safe"]
        assert v_safe <= prev + 1e-9, f"visibility {vis} m raised v_safe: {v_safe} > {prev}"
        prev = v_safe


def test_fog_clearing_recovers_safe_speed():
    dense = call(visibility_m=15.0, speed_limit_mps=25.0)["v_safe"]
    clear = call(visibility_m=50.0, speed_limit_mps=25.0)["v_safe"]
    assert clear > dense, "safe speed must recover when fog clears"


def test_friction_monotonicity_after_unification():
    prev = 0.0
    for mu in (0.15, 0.25, 0.35, 0.45, 0.55, 0.65):
        v_safe = call(friction_mu=mu, visibility_m=25.0, grade_percent=-8.0,
                      c_rr=0.03, curve_radius_m=50.0, speed_limit_mps=25.0)["v_safe"]
        assert v_safe >= prev - 1e-9, f"more friction lowered v_safe at mu={mu}"
        prev = v_safe


def test_downhill_grade_monotonicity_after_unification():
    prev = float("inf")
    for grade in (0.0, -4.0, -6.25, -8.0, -10.0, -12.0):
        v_safe = call(grade_percent=grade, friction_mu=0.25, c_rr=0.03,
                      visibility_m=20.0, speed_limit_mps=25.0)["v_safe"]
        assert v_safe <= prev + 1e-9, f"steeper downhill raised v_safe at {grade}%"
        prev = v_safe


def test_latency_monotonicity_after_unification():
    prev = float("inf")
    for tau in (0.0, 0.1, 0.25, 0.5, 1.0, 2.0):
        v_safe = call(tau_total=tau, visibility_m=30.0, speed_limit_mps=25.0)["v_safe"]
        assert v_safe <= prev + 1e-9, f"more latency raised v_safe at tau={tau}"
        prev = v_safe


# ---------------------------------------------------------------------
# Numeric compatibility: the mappings that must remain EXACT
# ---------------------------------------------------------------------

@pytest.mark.parametrize(
    "kw,expected_a_dec,expected_v_stop",
    [
        (dict(visibility_m=50.0), 3.8325636363636364, 17.638868562176263),
        (dict(visibility_m=15.0), 3.8325636363636364, 7.849202999769826),
        (dict(grade_percent=-8.0, visibility_m=50.0), 3.0496381634172733, 15.82218279708213),
        (dict(mass_kg=74000.0, visibility_m=30.0), 6.0822, 15.984365661107883),
    ],
)
def test_a_dec_and_v_stop_unchanged_from_pre_p2_baseline(kw, expected_a_dec, expected_v_stop):
    """
    Captured from the pre-P2 solver. The sign-flip and latency mappings are correct only
    if these still match to 1e-6, so this is the regression guard for the translation.
    """
    res = call(**kw)
    assert res["a_dec"] == pytest.approx(expected_a_dec, abs=1e-6)
    assert res["v_stop"] == pytest.approx(expected_v_stop, abs=1e-6)


def test_curve_limit_unchanged_from_pre_p2():
    # Bit-identical to the pre-P2 engine: both compute v_curve = sqrt(mu * g * R).
    assert calculate_curve_speed_limit(0.60, 20.0) == pytest.approx(10.849884792015075, abs=1e-9)
    assert calculate_curve_speed_limit(0.60, 50.0) == pytest.approx(17.155174146594955, abs=1e-9)


def test_uphill_still_needs_no_retarder():
    assert math.isinf(call(grade_percent=4.0)["v_retarder"])
    assert math.isinf(call(grade_percent=0.0)["v_retarder"])
