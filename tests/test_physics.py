import pytest
import numpy as np
from fog_safe.safety import calculate_v_stop, solve_safe_speed
from fog_safe.vehicle import MiningVehicle
from fog_safe.road import RoadSegment
from fog_safe.environment import EnvironmentState
from fog_safe.communication import CommunicationModel
from fog_safe.braking import calculate_effective_deceleration


def test_stopping_distance_formula():
    v = 10.0  # m/s
    tau = 0.25  # s
    a_dec = 2.0  # m/s^2
    d_stop = v * tau + (v ** 2) / (2.0 * a_dec)
    assert np.isclose(d_stop, 2.5 + 25.0)


def test_v_stop_analytical_solver():
    a_dec = 2.5
    tau = 0.25
    r_eff = 30.0
    s_base = 5.0
    v_stop = calculate_v_stop(a_dec=a_dec, tau_total=tau, r_effective=r_eff, s_base=s_base)
    
    # Check constraint: S_stop(v) + S_margin <= R_effective
    s_stop = v_stop * tau + (v_stop ** 2) / (2.0 * a_dec)
    assert s_stop + s_base <= r_eff + 1e-4


def test_reduced_friction_physics():
    veh = MiningVehicle()
    road = RoadSegment(percent_grade=0.0)
    env_dry = EnvironmentState(r_effective=50.0, mu_true=0.60)
    env_wet = EnvironmentState(r_effective=50.0, mu_true=0.25)

    a_dry = calculate_effective_deceleration(veh, road, env_dry, mu=0.60)
    a_wet = calculate_effective_deceleration(veh, road, env_wet, mu=0.25)

    assert a_dry > a_wet


def test_downhill_grade_deceleration():
    veh = MiningVehicle()
    road_flat = RoadSegment(percent_grade=0.0)
    road_down = RoadSegment(percent_grade=8.0)
    env = EnvironmentState(r_effective=50.0, mu_true=0.40)

    a_flat = calculate_effective_deceleration(veh, road_flat, env, mu=0.40)
    a_down = calculate_effective_deceleration(veh, road_down, env, mu=0.40)

    assert a_flat > a_down
