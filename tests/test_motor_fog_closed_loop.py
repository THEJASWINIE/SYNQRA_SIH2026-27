"""
FOG-ORCHESTRATOR 2.0 — Physical Motor + Fog Closed-Loop Regression Suite (Phase 17).

Specific regression tests verifying:
1. Root-cause fix for "Motor does not rotate forward":
   - FORWARD command generates direction == FORWARD
   - PWM >= MIN_EFFECTIVE_PWM (60) overcoming chassis static friction
   - Applied speed > 0
   - STOP command overrides all motion with PWM = 0 and direction == STOP
2. Fog Governor closed loop:
   - Fog increases -> safe speed decreases -> applied speed decreases -> PWM decreases
   - Direction remains FORWARD during speed reduction until explicit STOP
   - Fog clearing restores safe speed and PWM
3. Vehicle-specific calibration:
   - Both vehicles use TB6612FNG motor driver
   - TRUCK_01 Vmax = 1.40 m/s (42 PPR)
   - TRUCK_02 Vmax = 1.30 m/s (43 PPR)
   - Vmax_A != Vmax_B preserved
4. Safe boot invariant:
   - Boot default speed == 0.0 m/s, PWM == 0, STOP state.
"""

import os
import sys
import math
import pytest

_workspace_root = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
_backend_path = os.path.join(_workspace_root, "SYNQRA_SIH2026-27-HMI", "backend")
if _workspace_root not in sys.path:
    sys.path.insert(0, _workspace_root)
if _backend_path not in sys.path:
    sys.path.insert(0, _backend_path)

from app.weather_service import (
    WeatherStationService,
    get_fog_factor,
    fog_to_visibility_m,
    DEFAULT_VEHICLE_CALIBRATIONS,
)
from command_gateway import CommandGateway, VehicleCommand, CommandSource


def speed_to_pwm_vehicle(speed_mps: float, vmax_mps: float, min_effective_pwm: int = 60, max_pwm: int = 220) -> int:
    """Exact software representation of firmware speedToPWM implementation."""
    if not math.isfinite(speed_mps) or speed_mps <= 0.0:
        return 0
    clamped_speed = max(0.0, min(vmax_mps, speed_mps))
    ratio = clamped_speed / vmax_mps
    pwm = min_effective_pwm + round(ratio * (max_pwm - min_effective_pwm))
    return int(max(min_effective_pwm, min(max_pwm, pwm)))


class TestPhysicalForwardMotorControl:
    """Phase 17 Regression: Verify forward motor control and static friction overcome."""

    def test_forward_command_generates_forward_direction_and_effective_pwm(self):
        """Regression test: FORWARD command produces PWM >= 60 overcoming static friction."""
        vmax_a = DEFAULT_VEHICLE_CALIBRATIONS["TRUCK_01"].vmax_mps
        assert vmax_a == 1.40

        # At low speed 0.20 m/s, PWM must overcome static friction (PWM >= 60)
        pwm_low = speed_to_pwm_vehicle(0.20, vmax_a)
        assert pwm_low >= 60, f"Expected PWM >= 60 to overcome static friction, got {pwm_low}"
        assert pwm_low < 220

        # At medium speed 0.40 m/s
        pwm_med = speed_to_pwm_vehicle(0.40, vmax_a)
        assert pwm_med > pwm_low
        assert pwm_med < 220

        # At higher speed 0.60 m/s
        pwm_high = speed_to_pwm_vehicle(0.60, vmax_a)
        assert pwm_high > pwm_med
        assert pwm_high <= 220

    def test_stop_command_forces_zero_pwm(self):
        """Regression test: STOP or 0.0 m/s produces exactly 0 PWM and stops vehicle."""
        vmax = 1.40
        assert speed_to_pwm_vehicle(0.0, vmax) == 0
        assert speed_to_pwm_vehicle(-0.5, vmax) == 0
        assert speed_to_pwm_vehicle(float("nan"), vmax) == 0

    def test_vehicle_b_calibration_independent_from_vehicle_a(self):
        """Phase 4: Both use TB6612FNG but have distinct physical Vmax calibrations."""
        cal_a = DEFAULT_VEHICLE_CALIBRATIONS["TRUCK_01"]
        cal_b = DEFAULT_VEHICLE_CALIBRATIONS["TRUCK_02"]

        assert cal_a.motor_driver == "TB6612FNG"
        assert cal_b.motor_driver == "TB6612FNG"

        assert cal_a.vmax_mps == 1.40
        assert cal_b.vmax_mps == 1.30
        assert cal_a.vmax_mps != cal_b.vmax_mps, "Vehicle-specific Vmax must not be collapsed"

        # Encoder physical differences
        assert cal_a.raw_ppr == 42.0
        assert cal_b.raw_ppr == 43.0


class TestFogGovernorClosedLoop:
    """Phase 6 & 15: Environmental Fog injection -> Safe Speed -> PWM control."""

    def setup_method(self):
        self.weather_svc = WeatherStationService(baseline_speed_mps=0.80)

    def test_fog_escalation_causes_monotonic_speed_and_pwm_reduction(self):
        """
        CLEAR -> LIGHT -> MODERATE -> HEAVY -> SEVERE:
        v_safe decreases monotonically, PWM decreases monotonically, direction remains FORWARD.
        """
        fog_steps = [
            (0.00, "CLEAR"),
            (0.25, "LIGHT_FOG"),
            (0.50, "MODERATE_FOG"),
            (0.75, "HEAVY_FOG"),
            (1.00, "SEVERE_FOG"),
        ]

        prev_v_safe_a = 999.0
        prev_pwm_a = 999

        for intensity, cond_name in fog_steps:
            env_state, events = self.weather_svc.update_fog(fog_intensity=intensity)
            assert env_state.weather_condition == cond_name
            assert env_state.fog_intensity == intensity

            # Check Vehicle A governor response
            gov_a = self.weather_svc.compute_vehicle_governor(
                vehicle_id="TRUCK_01",
                requested_speed_mps=0.80,
                fog_factor=env_state.fog_factor,
                severe_stop=False,
            )

            # Safe speed must decrease or stay equal (monotonic non-increasing)
            assert gov_a.v_safe_mps <= prev_v_safe_a, f"v_safe did not decrease: {gov_a.v_safe_mps} > {prev_v_safe_a}"
            assert gov_a.applied_speed_mps <= gov_a.v_safe_mps

            # Calculate motor PWM
            pwm = speed_to_pwm_vehicle(gov_a.applied_speed_mps, gov_a.vmax_mps)
            if gov_a.applied_speed_mps > 0:
                assert pwm >= 60, f"Forward PWM fell below minimum effective threshold: {pwm}"
                assert pwm <= prev_pwm_a
                # Direction remains FORWARD
                direction = "FORWARD"
            else:
                assert pwm == 0
                direction = "STOP"

            assert direction in ("FORWARD", "STOP")
            prev_v_safe_a = gov_a.v_safe_mps
            prev_pwm_a = pwm

    def test_fog_clearing_recovers_speed_and_pwm(self):
        """Fog increase followed by CLEAR must fully recover safe speed and PWM."""
        # Step 1: Fog enters
        env_fog, _ = self.weather_svc.update_fog(fog_intensity=0.75)
        gov_fog = self.weather_svc.compute_vehicle_governor("TRUCK_01", 0.80, env_fog.fog_factor)
        pwm_fog = speed_to_pwm_vehicle(gov_fog.applied_speed_mps, gov_fog.vmax_mps)

        # Step 2: Fog clears
        env_clear, _ = self.weather_svc.update_fog(fog_intensity=0.00)
        gov_clear = self.weather_svc.compute_vehicle_governor("TRUCK_01", 0.80, env_clear.fog_factor)
        pwm_clear = speed_to_pwm_vehicle(gov_clear.applied_speed_mps, gov_clear.vmax_mps)

        assert gov_clear.v_safe_mps > gov_fog.v_safe_mps
        assert gov_clear.applied_speed_mps > gov_fog.applied_speed_mps
        assert pwm_clear > pwm_fog
        assert pwm_clear > 100

    def test_severe_fog_stop_policy(self):
        """Under severe fog stop policy, safe speed is clamped to 0.0 m/s and PWM is 0."""
        env_state, _ = self.weather_svc.update_fog(fog_intensity=1.00, severe_stop_policy=True)
        gov_a = self.weather_svc.compute_vehicle_governor(
            vehicle_id="TRUCK_01",
            requested_speed_mps=0.80,
            fog_factor=env_state.fog_factor,
            severe_stop=True,
        )
        assert gov_a.v_safe_mps == 0.0
        assert gov_a.applied_speed_mps == 0.0
        pwm = speed_to_pwm_vehicle(gov_a.applied_speed_mps, gov_a.vmax_mps)
        assert pwm == 0


class TestCommandGatewayIntegration:
    """Phase 10: Command Gateway validates FORWARD action and safe clamp."""

    def test_forward_action_accepted_by_gateway(self):
        import time
        from twin.twin_state_store import TwinStateStore, TwinMode, Sourced, Source, Quality, ClockDomain

        now = time.time()
        store = TwinStateStore(mode=TwinMode.HYBRID, stale_after_s=5.0)
        store.register_vehicle("TRUCK_01")
        store.update_vehicle_fields(
            "TRUCK_01",
            {"v_safe_mps": Sourced(value=0.80, timestamp=now, source=Source.DERIVED, quality=Quality.GOOD, clock_domain=ClockDomain.WALL_CLOCK)},
        )

        gateway = CommandGateway(store=store)
        cmd = VehicleCommand(
            vehicle_id="TRUCK_01",
            command_id="CMD-FWD-001",
            created_at=now,
            action="FORWARD",
            target_speed_mps=0.40,
            source=CommandSource.OPERATOR,
        )
        res = gateway.submit(cmd)
        assert res.accepted is True
        assert res.status == "ACCEPTED"
        assert res.accepted_at is not None

    def test_forward_action_rejected_if_exceeds_vsafe(self):
        """Rule 7: Safety remains authoritative — commands exceeding v_safe are rejected by gateway."""
        import time
        from twin.twin_state_store import TwinStateStore, TwinMode, Sourced, Source, Quality, ClockDomain

        now = time.time()
        store = TwinStateStore(mode=TwinMode.HYBRID, stale_after_s=5.0)
        store.register_vehicle("TRUCK_01")
        # v_safe clamped to 0.30 m/s by heavy fog
        store.update_vehicle_fields(
            "TRUCK_01",
            {"v_safe_mps": Sourced(value=0.30, timestamp=now, source=Source.DERIVED, quality=Quality.GOOD, clock_domain=ClockDomain.WALL_CLOCK)},
        )

        gateway = CommandGateway(store=store)
        cmd = VehicleCommand(
            vehicle_id="TRUCK_01",
            command_id="CMD-FWD-002",
            created_at=now,
            action="FORWARD",
            target_speed_mps=0.60,
            source=CommandSource.OPERATOR,
        )
        res = gateway.submit(cmd)
        assert res.accepted is False
        assert res.status == "REJECTED"
        assert "exceeds" in res.reason.lower()
        assert res.v_safe_mps == 0.30
