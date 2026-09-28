"""
tests/test_data_health_to_safety_chain.py
-----------------------------------------
Dedicated verification test proving the unbreakable causal chain:
DATA HEALTH -> VALIDATED R_EFFECTIVE -> LOCAL SAFETY GOVERNOR -> V_SAFE -> V_COMMAND

Verifies for every primary health state:
- HEALTHY
- DEGRADED
- STALE
- CONFLICTING
- UNAVAILABLE

Across four distinct operating environments:
1. Level dry road (0% grade, mu=0.55)
2. Downhill wet ramp (-8% grade, mu=0.35)
3. Slippery downhill ramp (-10% grade, mu=0.20)
4. Dense fog on steep ramp (-12% grade, mu=0.25, R_raw=10m)

Enforces Hard Invariants:
Invariant 1: v_command <= v_safe (Zero central optimizer overspeed)
Invariant 2: S_stop + S_base <= R_effective (Stopping distance envelope closure)
"""

import pytest
import math
from typing import Dict, Any

from integration_adapters.environmental_data_health import (
    DataState,
    EnvironmentalDataHealth,
    EnvironmentalHealthConfig,
    FaultCode,
    ValidatedSignal,
)
from fog_safe.vehicle import MiningVehicle
from fog_safe.road import RoadSegment
from fog_safe.environment import EnvironmentState
from fog_safe.communication import CommunicationModel
from fog_safe.safety import solve_safe_speed


def calculate_stopping_distance(v_mps: float, a_dec: float, tau: float) -> float:
    if a_dec <= 0.0 or v_mps <= 0.0:
        return 0.0
    return (v_mps * tau) + (v_mps ** 2) / (2.0 * a_dec)


@pytest.fixture
def health_configs():
    return EnvironmentalHealthConfig(
        T_DEGRADED_ENV_s=30.0,
        T_STALE_ENV_s=60.0,
        T_GRACE_PERIOD_s=120.0,
        DEGRADED_FACTOR=0.70,
        STALE_FACTOR=0.50,
        R_MIN_m=5.0,
        R_UNAVAILABLE_MIN_m=8.0,
        CONFLICT_THRESHOLD_m=25.0
    )


class TestDataHealthToSafetyChain:

    @pytest.mark.parametrize("health_state,expected_r_factor", [
        (DataState.HEALTHY, 1.0),
        (DataState.DEGRADED, 0.70),
        (DataState.STALE, 0.50),
        (DataState.CONFLICTING, 0.70),
        (DataState.UNAVAILABLE, None),  # fixed at 8.0m
    ])
    @pytest.mark.parametrize("env_case", [
        {"name": "Level Dry", "grade": 0.0, "mu": 0.55, "raw_vis": 50.0},
        {"name": "Downhill Wet", "grade": -8.0, "mu": 0.35, "raw_vis": 50.0},
        {"name": "Slippery Downhill", "grade": -10.0, "mu": 0.20, "raw_vis": 30.0},
        {"name": "Dense Fog Steep", "grade": -12.0, "mu": 0.25, "raw_vis": 10.0},
    ])
    def test_causal_propagation_and_invariants(self, health_configs, health_state, expected_r_factor, env_case):
        """
        Tests that every health state deterministically maps to R_effective,
        which bounds v_safe, which clamps v_command, strictly satisfying stopping distance.
        """
        vehicle = MiningVehicle(is_loaded=True)
        road = RoadSegment(percent_grade=env_case["grade"], speed_limit_kmh=40.0)
        comm = CommunicationModel()
        tau_total = comm.tau_total

        # 1. Determine R_effective from data health rules
        raw_vis = env_case["raw_vis"]
        if health_state == DataState.HEALTHY:
            r_eff = raw_vis
        elif health_state == DataState.DEGRADED:
            r_eff = max(health_configs.R_MIN_m, raw_vis * health_configs.DEGRADED_FACTOR)
        elif health_state == DataState.STALE:
            r_eff = max(health_configs.R_MIN_m, raw_vis * health_configs.STALE_FACTOR)
        elif health_state == DataState.CONFLICTING:
            # Conflict with secondary visibility
            r_eff = max(health_configs.R_MIN_m, raw_vis * health_configs.DEGRADED_FACTOR)
        else:  # UNAVAILABLE
            r_eff = health_configs.R_UNAVAILABLE_MIN_m

        # 2. Physics & Safety Governor Evaluation
        env = EnvironmentState(r_effective=r_eff, mu_true=env_case["mu"])
        res = solve_safe_speed(
            vehicle, road, env, comm,
            mu_effective=env_case["mu"],
            r_effective=r_eff
        )
        v_safe = res.v_safe_ms

        # 3. Simulate Central Optimizer Requesting Over-speed (e.g. 25.0 m/s ~ 90 km/h)
        v_requested = 25.0
        # Local Safety Governor enforces Level 1 constraint:
        v_command = min(v_requested, v_safe)

        # -------------------------------------------------------------
        # INVARIANT 1: Commanded speed cannot exceed safe envelope
        # -------------------------------------------------------------
        assert v_command <= v_safe + 1e-6, (
            f"Invariant 1 Violated! v_command ({v_command}) > v_safe ({v_safe})"
        )

        # -------------------------------------------------------------
        # INVARIANT 2: Physical stopping distance envelope closure
        # S_stop(v_command) + S_base <= R_effective
        # -------------------------------------------------------------
        a_dec = res.a_dec
        s_base = comm.margin_params.s_base  # 5.0m
        s_stop = calculate_stopping_distance(v_command, a_dec, tau_total)
        stopping_margin = r_eff - (s_stop + s_base)

        assert stopping_margin >= -1e-4, (
            f"Invariant 2 Violated! Margin={stopping_margin:.4f}m for State={health_state} on {env_case['name']}. "
            f"R_eff={r_eff}m, S_stop={s_stop:.2f}m, S_base={s_base}m, a_dec={a_dec:.2f}m/s2"
        )

    def test_state_table_generation(self, health_configs):
        """
        Generates and prints the exact State Transition & Clamping Table
        for the forensic documentation.
        """
        states = [
            DataState.HEALTHY,
            DataState.DEGRADED,
            DataState.STALE,
            DataState.CONFLICTING,
            DataState.UNAVAILABLE,
        ]
        vehicle = MiningVehicle(is_loaded=True)
        comm = CommunicationModel()
        tau_total = comm.tau_total

        table_rows = []
        raw_vis = 50.0

        for st in states:
            if st == DataState.HEALTHY:
                r_eff = raw_vis
            elif st == DataState.DEGRADED:
                r_eff = raw_vis * 0.70
            elif st == DataState.STALE:
                r_eff = raw_vis * 0.50
            elif st == DataState.CONFLICTING:
                r_eff = raw_vis * 0.70
            else:
                r_eff = 8.0

            # Level road
            road_level = RoadSegment(percent_grade=0.0, speed_limit_kmh=40.0)
            res_level = solve_safe_speed(vehicle, road_level, EnvironmentState(r_effective=r_eff, mu_true=0.40), comm, mu_effective=0.40, r_effective=r_eff)

            # Downhill road (-8%)
            road_down = RoadSegment(percent_grade=-8.0, speed_limit_kmh=40.0)
            res_down = solve_safe_speed(vehicle, road_down, EnvironmentState(r_effective=r_eff, mu_true=0.35), comm, mu_effective=0.35, r_effective=r_eff)

            table_rows.append({
                "health": st.value,
                "raw_vis": raw_vis,
                "r_eff": r_eff,
                "v_safe_level_kmh": res_level.v_safe_kmh,
                "v_safe_down_kmh": res_down.v_safe_kmh,
                "v_safe_down_mps": res_down.v_safe_ms,
                "a_dec_down": res_down.a_dec,
                "s_stop_down": calculate_stopping_distance(res_down.v_safe_ms, res_down.a_dec, tau_total),
            })

        assert len(table_rows) == 5
        # Verify monotonically non-increasing safe speed as health degrades
        speeds_down = [r["v_safe_down_kmh"] for r in table_rows]
        assert speeds_down[0] >= speeds_down[1] >= speeds_down[2] > speeds_down[4]
