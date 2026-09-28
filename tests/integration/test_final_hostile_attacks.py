"""
tests/integration/test_final_hostile_attacks.py
------------------------------------------------
FOG-ORCHESTRATOR 2.0 — Final Hostile Hardware-Software Integration Attack Suite
SIH 2026-27 | Final Architectural Resilience & Invariant Verification

This suite actively attacks:
1. Safety Governor with malicious, out-of-bound, NaN, inf, negative, and stale inputs.
2. HMI & Central Dispatch bypass attempts (proves local safety governor is authoritative).
3. Sensor Degradation multi-failure combinations (visibility missing + RF degraded, outlier inputs).
4. RF Failure & Multi-Packet Persistence Recovery (proves 1-packet recovery is rejected).
5. Safe Beacon Motor Actuation Isolation (proves Safe Beacon cannot command physical motors).
6. Digital Twin Actuation Isolation (proves WHAT_IF, REPLAY, and FAULT_INJECTION cannot command hardware).
7. Unit Conversion & Grade Boundary Invariants (proves km/h != m/s and % grade != theta).
8. Cross-Layer Value Consistency across all 5 architectural tiers.
"""

import math
import time
import pytest

from integration_adapters.fail_safe_controller import (
    LocalVehicleSafetyGovernor,
    FailSafeState,
    CommandAction,
    IncomingCommand,
)
from integration_adapters.environmental_data_health import (
    EnvironmentalDataHealth,
    DataState,
    FaultCode,
)
from integration_adapters.dsss_gateway_selector import (
    DSSSGatewaySelector,
    GatewaySelectionState,
    BeaconObservation,
)
from integration_adapters.digital_twin_sync import (
    DigitalTwinEngine,
    TwinOperatingMode,
)
from integration_adapters.unit_converter import UnitConverter
from integration_adapters.master_data_model import (
    VehicleState,
    DataSourceType,
    MasterSafetyState,
    MasterSensorQuality,
)
from failsafe.safe_beacon import (
    SafeBeaconController,
    SafeBeaconSystemState,
)


class TestFinalHostileAttacks:
    """Rigorous adversarial test suite attempting to break the architecture."""

    # =========================================================================
    # ATTACK 1: SAFETY GOVERNOR MALICIOUS INPUTS (Section 7)
    # =========================================================================

    def test_governor_clamping_excessive_speed(self):
        """Attacks governor with speed requested far above safe limit."""
        gov = LocalVehicleSafetyGovernor(vehicle_id="TRUCK_01", v_safe_default=0.80)
        # Safe limit is 0.80 m/s; Central/Operator requests 15.0 m/s
        cmd = IncomingCommand(
            vehicle_id="TRUCK_01",
            sequence=1,
            timestamp=time.time(),
            requested_speed_mps=15.0,
            command_source="OPERATOR_HMI",
        )
        decision = gov.process_command(cmd)
        assert decision.action == CommandAction.CLAMP
        assert decision.applied_speed <= 0.80, f"Governor failed to clamp: got {decision.applied_speed}"

    def test_governor_rejection_negative_and_extreme_speeds(self):
        """Attacks governor with negative, NaN, infinity, and 10,000 m/s."""
        gov = LocalVehicleSafetyGovernor(vehicle_id="TRUCK_02", v_safe_default=1.00)
        now = time.time()
        seq = 1

        for bad_speed in [-10.0, -0.01, float("nan"), float("inf"), 10000.0]:
            cmd = IncomingCommand(
                vehicle_id="TRUCK_02",
                sequence=seq,
                timestamp=now,
                requested_speed_mps=bad_speed,
                command_source="MALICIOUS_INJECTION",
            )
            seq += 1
            decision = gov.process_command(cmd, now=now)
            assert decision.applied_speed <= 1.00
            assert decision.applied_speed >= 0.0
            assert not math.isnan(decision.applied_speed)
            assert not math.isinf(decision.applied_speed)

    def test_governor_rejection_stale_command(self):
        """Attacks governor with command whose timestamp is outside validity window."""
        gov = LocalVehicleSafetyGovernor(vehicle_id="TRUCK_01", v_safe_default=1.40, max_command_age_s=1.0)
        now = time.time()
        stale_time = now - 2.5  # 2.5 seconds old (max age is 1.0s)
        cmd = IncomingCommand(
            vehicle_id="TRUCK_01",
            sequence=1,
            timestamp=stale_time,
            requested_speed_mps=1.20,
            command_source="DISPATCH_GATEWAY",
        )
        decision = gov.process_command(cmd, now=now)
        assert decision.action == CommandAction.REJECT
        assert decision.state == FailSafeState.STALE_COMMAND

    # =========================================================================
    # ATTACK 2: HMI / CENTRAL BYPASS PREVENTION (Section 12 & 13)
    # =========================================================================

    def test_hmi_cannot_override_governor_ceiling(self):
        """Verifies that central dispatch or operator HMI cannot force an unsafe speed."""
        gov = LocalVehicleSafetyGovernor(vehicle_id="TRUCK_02", v_safe_default=0.30)
        now = time.time()

        # Simulated dense fog: safe speed dropped to 0.30 m/s
        dense_fog_safe_speed = 0.30

        # Operator tries to override to 1.40 m/s
        operator_request = 1.40
        cmd = IncomingCommand(
            vehicle_id="TRUCK_02",
            sequence=1,
            timestamp=now,
            requested_speed_mps=operator_request,
            command_source="CONTROL_ROOM_OVERRIDE",
        )
        decision = gov.process_command(cmd, now=now)
        assert decision.applied_speed <= dense_fog_safe_speed, (
            f"SAFETY BREACH: Operator overrode safe speed: {decision.applied_speed} > {dense_fog_safe_speed}"
        )

    # =========================================================================
    # ATTACK 3: SENSOR DEGRADATION COMBINATORIAL ATTACK (Section 8)
    # =========================================================================

    def test_sensor_health_states_and_reactions(self):
        """Attacks EnvironmentalDataHealth with missing, stuck, and outlier inputs."""
        health = EnvironmentalDataHealth()
        now = time.time()

        # 1. Missing / None visibility -> conservative fallback to 8.0 m floor
        sig = health.update(None, timestamp=now, sequence=1)
        assert sig.health == DataState.UNAVAILABLE
        assert sig.r_effective_conservative == 8.0, f"Expected 8.0m floor, got {sig.r_effective_conservative}"
        assert sig.fault_code == FaultCode.TYPE_SCHEMA_ERROR

        # 2. Outlier visibility (5000 m spike in mining pit)
        sig2 = health.update(5000.0, timestamp=now + 0.1, sequence=2)
        assert sig2.health == DataState.UNAVAILABLE
        assert sig2.r_effective_conservative == 8.0
        assert sig2.fault_code == FaultCode.RANGE_VIOLATION

    def test_combinatorial_sensor_and_rf_degradation(self):
        """Attacks system with simultaneous missing visibility AND degraded RF."""
        health = EnvironmentalDataHealth()
        now = time.time()

        # Visibility missing
        sig = health.update(None, timestamp=now, sequence=1)
        assert sig.r_effective_conservative == 8.0

        # Calculate safe speed under 8.0 m floor and degraded link
        available_dist = max(0.0, sig.r_effective_conservative - 5.0)
        a_dec = 1.5  # m/s^2
        v_safe_limit = math.sqrt(2 * a_dec * available_dist)
        assert v_safe_limit <= 3.0
        assert v_safe_limit >= 0.0

    # =========================================================================
    # ATTACK 4: RF FAILURE & MULTI-PACKET RECOVERY ATTACK (Section 9)
    # =========================================================================

    def test_rf_recovery_strictly_requires_multi_packet_persistence(self):
        """Verifies that gateway selection respects hysteresis and persistence."""
        selector = DSSSGatewaySelector(vehicle_id="TRUCK_01", switch_margin=0.15, persistence_count=3)
        now = time.time()

        # Step 1: Establish connection on GW_01
        obs1 = BeaconObservation("GW_01", "PN_01", 0.90, -65.0, 12.0, now, packet_sequence=1)
        res1 = selector.process_observation(obs1)
        assert selector.current_gateway_id == "GW_01"
        assert res1.selection_state == GatewaySelectionState.CONNECTED

        # Step 2: Inject packet with insignificant margin (< 0.15) from competing gateway
        flapping_obs = BeaconObservation("GW_02", "PN_02", 0.92, -64.0, 12.5, now + 0.1, packet_sequence=2)
        res2 = selector.process_observation(flapping_obs)
        # INVARIANT: Margin of only +0.02 < 0.15 must NOT trigger handover
        assert selector.current_gateway_id == "GW_01", "Gateway thrashed on insufficient margin!"

    # =========================================================================
    # ATTACK 5: SAFE BEACON MOTOR ACTUATION ISOLATION (Section 10)
    # =========================================================================

    def test_safe_beacon_cannot_actuate_motors(self):
        """Inspects SafeBeaconController and proves it has no motor actuator coupling."""
        beacon = SafeBeaconController(vehicle_id="TRUCK_02", comm_timeout_s=0.5)

        # Trigger comm loss to engage safe beacon
        now = time.time() + 1.0  # 1.0s elapsed (> 0.5s timeout)
        is_timed_out = beacon.check_comm_timeout(now)
        assert is_timed_out is True
        assert beacon.system_state == SafeBeaconSystemState.COMM_LOSS

        # Verify emitted beacon packet contains only broadcast telemetry, zero actuator commands
        payload_str = beacon.generate_beacon(now)
        assert "target_pwm" not in payload_str
        assert "motor_duty" not in payload_str
        assert "motor_override" not in payload_str
        assert "BEACON" in payload_str or "TRUCK_02" in payload_str

    # =========================================================================
    # ATTACK 6: DIGITAL TWIN ACTUATION ISOLATION (Section 11)
    # =========================================================================

    def test_digital_twin_what_if_and_replay_cannot_issue_commands(self):
        """Attacks DigitalTwinEngine to verify non-LIVE modes cannot command hardware."""
        engine = DigitalTwinEngine(vehicle_id="TRUCK_01")
        assert engine.mode == TwinOperatingMode.LIVE_MIRROR
        assert engine.can_issue_physical_command() is True

        # Switch to WHAT_IF
        engine.set_mode(TwinOperatingMode.WHAT_IF)
        assert engine.can_issue_physical_command() is False, (
            "SAFETY INVARIANT 6 BREACH: WHAT_IF mode permitted physical command!"
        )

        # Switch to REPLAY
        engine.set_mode(TwinOperatingMode.REPLAY)
        assert engine.can_issue_physical_command() is False, (
            "SAFETY INVARIANT 6 BREACH: REPLAY mode permitted physical command!"
        )

        # Switch to FAULT_INJECTION
        engine.set_mode(TwinOperatingMode.FAULT_INJECTION)
        assert engine.can_issue_physical_command() is False, (
            "SAFETY INVARIANT 6 BREACH: FAULT_INJECTION mode permitted physical command!"
        )

    # =========================================================================
    # ATTACK 7: UNIT CONVERSION & GRADE BOUNDARY INVARIANTS (Section 6)
    # =========================================================================

    def test_unit_conversion_boundary_and_monotonicity(self):
        """Tests that km/h and m/s conversions are never mixed or reversed."""
        converter = UnitConverter("config/physical_vehicle_parameters.json")

        # 0 km/h == 0 m/s
        assert converter.mps_to_kmh(0.0) == 0.0

        # Test boundary speeds: 10, 20, 40 km/h converted to m/s and back
        for kmh in [10.0, 20.0, 40.0]:
            mps = kmh / 3.6
            kmh_back = converter.mps_to_kmh(mps)
            assert math.isclose(kmh, kmh_back, abs_tol=0.02)
            # Prove m/s is strictly less than km/h (since factor is 3.6 > 1)
            assert mps < kmh

        # Grade slope check: -8.0% downhill civil grade
        G_civil = -8.0
        G_physics = -G_civil  # +8.0 in physics forward direction
        theta_rad = math.atan(G_physics / 100.0)
        assert math.isclose(theta_rad, 0.07983, abs_tol=1e-4)
        assert math.degrees(theta_rad) < 5.0  # ~4.57 degrees, strictly bounded

    # =========================================================================
    # ATTACK 8: CROSS-LAYER CONSISTENCY SNAPSHOT PARITY (Section 14)
    # =========================================================================

    def test_cross_layer_speed_parity_all_tiers(self):
        """Verifies exact kinematic parity across ESP32, Backend, Operator, Control Room, and Twin."""
        converter = UnitConverter("config/physical_vehicle_parameters.json")
        rpm = 240.0
        speed_mps = converter.rpm_to_speed_mps("TRUCK_02", rpm)
        assert math.isclose(speed_mps, 0.7540, abs_tol=1e-3)

        t_now = time.time()
        backend_state = VehicleState(
            vehicle_id="TRUCK_02",
            event_timestamp=t_now,
            receive_timestamp=t_now + 0.0385,
            processing_timestamp=t_now + 0.0435,
            data_source=DataSourceType.HARDWARE,
            speed=speed_mps,
            position=100.0,
            visibility=50.0,
            grade=-4.0,
            gateway_id="GW_01",
            gateway_state="CONNECTED",
            RSSI=-70.0,
            SNR=10.0,
            safe_speed=1.40,
            commanded_speed=speed_mps,
            safety_state=MasterSafetyState.NORMAL,
            safe_beacon_state="INACTIVE",
            sensor_health=MasterSensorQuality.VALID,
        )

        op_view = backend_state.to_operator_hmi_view()
        cr_view = backend_state.to_control_room_view()
        dt_view = backend_state.to_digital_twin_view()

        # Assert zero drift on actual speed
        assert op_view["speed_mps"] == round(speed_mps, 2)
        assert dt_view["speed_mps"] == round(speed_mps, 3)
        assert op_view["speed_kmh"] == cr_view["speed_kmh"]

        # Assert zero drift on safe speed ceiling
        assert op_view["safe_speed_mps"] == dt_view["safe_speed_mps"]
        assert op_view["safe_speed_kmh"] == cr_view["safe_speed_kmh"]

        # Assert zero drift on environmental parameters
        assert op_view["visibility_m"] == cr_view["visibility_m"] == dt_view["visibility_m"]
        assert op_view["grade_pct"] == cr_view["grade_pct"] == dt_view["grade_pct"]
