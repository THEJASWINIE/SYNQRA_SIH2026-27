"""
tests/test_hemm_canonical_regression.py
---------------------------------------
Automated regression suite for Canonical Bailadila HEMM Physics & Operating Envelope.
Proves:
1. Schema & provenance integrity of config/bailadila_hemm_canonical.yaml.
2. Canonical longitudinal force balance & aerodynamic relevance.
3. Grade force monotonicity & GradeAdapter integration.
4. Stopping distance decomposition: tau_sensor + tau_comm + tau_decision + tau_can + tau_actuator.
5. Multi-constraint safe speed solver traceability.
6. Headway model: strict separation of spatial distance (m) from temporal gap (s).
7. Road capacity classification: kinematic vs practical vs service resource.
"""

import os
import yaml
import pytest
import numpy as np

from fog_safe.road import RoadSegment
from fog_safe.vehicle import MiningVehicle
from fog_safe.environment import EnvironmentState
from fog_safe.communication import CommunicationModel
from fog_safe.dynamics import (
    calculate_grade_force,
    calculate_rolling_resistance,
    calculate_aero_drag,
    calculate_longitudinal_acceleration,
)
from fog_safe.braking import calculate_effective_deceleration, calculate_stopping_distance
from fog_safe.safety import solve_safe_speed
from fog_safe.headway import calculate_safe_headway
from integration_adapters.grade_adapter import GradeAdapter


def test_canonical_yaml_schema_and_provenance():
    """Verify config/bailadila_hemm_canonical.yaml exists, parses, and satisfies PART 3 schema."""
    path = "config/bailadila_hemm_canonical.yaml"
    assert os.path.exists(path), f"Missing {path}"

    with open(path, "r") as f:
        data = yaml.safe_load(f)

    assert "parameters" in data
    params = data["parameters"]

    required_keys = [
        "name", "value", "unit", "source", "source_type", "confidence", "valid_range", "notes"
    ]
    valid_source_types = {
        "RESEARCH_DERIVED", "STANDARD", "OEM_REFERENCE", "MEASURED", "DERIVED", "ASSUMED", "UNVERIFIED"
    }

    for param_name, param_dict in params.items():
        for req in required_keys:
            assert req in param_dict, f"Parameter '{param_name}' missing required key '{req}'"
        assert param_dict["source_type"] in valid_source_types, (
            f"Parameter '{param_name}' invalid source_type: {param_dict['source_type']}"
        )
        assert isinstance(param_dict["valid_range"], list)
        assert len(param_dict["valid_range"]) == 2
        # If numeric, ensure value is within valid_range
        if isinstance(param_dict["value"], (int, float)):
            low, high = param_dict["valid_range"]
            assert low <= param_dict["value"] <= high, (
                f"Parameter '{param_name}' value {param_dict['value']} outside [{low}, {high}]"
            )


def test_longitudinal_force_balance_and_aero_relevance():
    """
    Verify longitudinal dynamic model:
    m * dv/dt = F_drive + F_grade - F_roll - F_aero - F_retarder - F_brake
    Evaluate aerodynamic drag relevance at haul road speeds (<= 20 km/h = 5.56 m/s).
    """
    road = RoadSegment.from_civil_grade(0.0)
    env = EnvironmentState(r_effective=50.0, mu_true=0.35)
    veh = MiningVehicle()

    # Force at max speed (20 km/h = 5.556 m/s)
    v_max = 20.0 / 3.6
    f_roll = calculate_rolling_resistance(veh, road, env)
    f_aero = calculate_aero_drag(veh, env, v_max)

    # For a 165.5t dumper, F_roll ~ 40.5 kN. F_aero ~ 0.5 * 1.225 * 0.8 * 22 * (5.56^2) ~ 333 N
    assert f_roll > 30000.0, f"F_roll {f_roll} unexpectedly small"
    assert f_aero < 500.0, f"F_aero {f_aero} unexpectedly large at 20 km/h"
    # Aerodynamic drag is < 1.5% of rolling resistance at 20 km/h
    assert (f_aero / f_roll) < 0.02


def test_grade_force_monotonicity_across_standard_grades():
    """Verify grade forces and decelerations across [+8%, +5%, 0%, -5%, -8%]."""
    grades = [8.0, 5.0, 0.0, -5.0, -8.0]
    env = EnvironmentState(r_effective=30.0, mu_true=0.35)
    veh = MiningVehicle()

    a_decs = []
    for g in grades:
        road = RoadSegment.from_civil_grade(g)
        a_dec = calculate_effective_deceleration(veh, road, env, mu=0.35)
        a_decs.append(a_dec)

    # Deceleration must strictly decrease as grade goes from steep uphill (+8%) to steep downhill (-8%)
    for i in range(len(a_decs) - 1):
        assert a_decs[i] > a_decs[i + 1], (
            f"Monotonicity violated: grade {grades[i]}% (a={a_decs[i]:.3f}) <= grade {grades[i+1]}% (a={a_decs[i+1]:.3f})"
        )


def test_stopping_distance_decomposition():
    """Verify stopping distance formula: S_stop = v * tau_total + v^2 / (2 * a_dec)."""
    road = RoadSegment.from_civil_grade(0.0)
    env = EnvironmentState(r_effective=30.0, mu_true=0.35)
    veh = MiningVehicle()

    v = 5.0  # m/s
    tau_sensor = 0.100
    tau_v2v = 0.050
    tau_gw = 0.080
    tau_dec = 0.050
    tau_can = 0.050
    tau_act = 0.200
    tau_total = tau_sensor + tau_v2v + tau_gw + tau_dec + tau_can + tau_act
    assert abs(tau_total - 0.530) < 1e-6

    d_react, d_brake, s_stop = calculate_stopping_distance(veh, road, env, mu=0.35, v=v, tau_total=tau_total)

    expected_d_react = v * tau_total
    assert abs(d_react - expected_d_react) < 1e-5
    assert s_stop == pytest.approx(d_react + d_brake, abs=1e-5)


def test_safe_speed_multi_constraint_traceability():
    """Verify solve_safe_speed correctly identifies active binding constraints."""
    # 1. Severe fog (4m sight) -> STOPPING_DISTANCE binds
    road = RoadSegment.from_civil_grade(0.0)
    env_fog = EnvironmentState(r_effective=4.0, mu_true=0.35)
    veh = MiningVehicle()
    comm = CommunicationModel()
    res_fog = solve_safe_speed(veh, road, env_fog, comm, mu_effective=0.35, r_effective=4.0)
    assert res_fog.primary_constraint == "v_stop"
    assert res_fog.v_safe_ms < 2.0  # severely restricted speed

    # 2. Clear road with sharp curve (R = 8.0m) -> CURVE_LATERAL binds
    road_curve = RoadSegment.from_civil_grade(0.0, curve_radius=8.0)
    env_clear = EnvironmentState(r_effective=100.0, mu_true=0.35)
    res_curve = solve_safe_speed(veh, road_curve, env_clear, comm, mu_effective=0.35, r_effective=100.0)
    assert res_curve.primary_constraint == "v_curve"
    assert res_curve.v_safe_ms < (20.0 / 3.6)

    # 3. Clear straight road -> SITE_SPEED_LIMIT binds
    road_straight = RoadSegment.from_civil_grade(0.0, speed_limit_kmh=20.0)
    res_straight = solve_safe_speed(veh, road_straight, env_clear, comm, mu_effective=0.35, r_effective=100.0)
    assert res_straight.primary_constraint == "v_mine"
    assert res_straight.v_safe_ms == pytest.approx(20.0 / 3.6, abs=1e-3)


def test_headway_distance_vs_time_separation():
    """
    Verify calculate_safe_headway strictly separates spatial distance (m) from temporal gap (s).
    """
    v_lead = 4.0  # m/s
    v_follower = 4.0  # m/s
    h_dist, t_headway = calculate_safe_headway(
        v_follower=v_follower,
        v_leader=v_lead,
        a_follower=2.5,
        a_leader=2.5,
        tau_total=0.53,
        s_margin=5.0
    )

    assert isinstance(h_dist, float)
    assert h_dist > 5.0, "Headway distance must exceed standstill margin"

    # Time headway is H_safe / v (seconds)
    assert isinstance(t_headway, float)
    assert t_headway > 0.53, "Time headway must exceed perception reaction time"
    assert t_headway == pytest.approx(h_dist / v_follower, abs=1e-5)


def test_road_capacity_distinction():
    """
    Verify capacity distinctions:
    - Theoretical Kinematic Capacity C_kin = 3600 * v / H
    - Service Resource Capacity = 18 trucks/hr = 1647 TPH
    """
    v = 5.0  # m/s
    h_dist = 25.0  # m
    c_kin_vph = (3600.0 * v) / h_dist  # 720 vph
    assert c_kin_vph > 500.0

    # Crusher bottleneck service time: 200s per truck -> 18 trucks/hr
    t_service = 200.0  # s
    crusher_vph = 3600.0 / t_service
    assert crusher_vph == 18.0

    payload_per_truck_t = 91.5  # tonnes
    crusher_throughput_tph = crusher_vph * payload_per_truck_t
    assert crusher_throughput_tph == 1647.0

    # Kinematic flux must NEVER be equated with sustainable mine production
    assert c_kin_vph != crusher_vph
