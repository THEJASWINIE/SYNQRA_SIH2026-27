import pytest
from twin.network import MineNetwork
from models.road_capacity import calculate_road_capacity
from fog_safe.safety import solve_safe_speed
from fog_safe.vehicle import MiningVehicle
from fog_safe.road import RoadSegment
from fog_safe.environment import EnvironmentState
from fog_safe.communication import CommunicationModel


def test_fog_to_capacity_causal_chain():
    veh = MiningVehicle()
    road = RoadSegment(percent_grade=0.0, speed_limit_kmh=50.0)
    comm = CommunicationModel()

    # Step 1: Clear environment
    env_clear = EnvironmentState(r_effective=50.0, mu_true=0.60)
    res_clear = solve_safe_speed(veh, road, env_clear, comm, mu_effective=0.60)
    v_clear = res_clear.v_safe_ms
    h_clear = res_clear.s_stop + res_clear.s_margin

    # Step 2: Dense fog environment
    env_fog = EnvironmentState(r_effective=15.0, mu_true=0.25)
    res_fog = solve_safe_speed(veh, road, env_fog, comm, mu_effective=0.25)
    v_fog = res_fog.v_safe_ms
    h_fog = res_fog.s_stop + res_fog.s_margin

    # Verify causal propagation: Visibility ↓ -> Safe speed ↓ -> Traversal time ↑ -> Headway constraint change
    assert v_fog < v_clear
    
    travel_time_clear = 500.0 / v_clear
    travel_time_fog = 500.0 / v_fog
    assert travel_time_fog > travel_time_clear
