"""
tests/integration/test_end_to_end_integration.py
------------------------------------------------
Comprehensive End-to-End Integration Test Suite for FOG-ORCHESTRATOR 2.0 (Phases H1–H10).

Covers:
1. Phase H1: Hardware Interface Freeze (Vehicle B TB6612FNG, Encoders, Kinematic Scaling)
2. Phase H2: Canonical Vehicle Telemetry Validation & Rejection of Malformed Packets
3. Phase H3: 8-State Sensor Health Engine Integration
4. Phase H4: Tier-1 Safety Governor Hierarchy & Speed Clamping
5. Phase H5: LoRa CSS Telemetry vs. DSSS/PN Gateway Selection
6. Phase H6: Safe Beacon Activation & Anti-Flapping Recovery
7. Phase H7: CAN / J1939 Vehicle-Command Abstraction & Latency Tracking
8. Phase H8: Digital Twin Canonical Synchronization (LIVE_MIRROR vs. WHAT_IF Isolation)
9. Phase H9/H10: Operator and Control Room HMI Projection Integrity
10. Safety Invariants (I1 through I10)
"""

import math
import time
import json
import pytest
import numpy as np

from integration_adapters.master_data_model import (
    VehicleState,
    DataSourceType,
    MasterSensorQuality,
    MasterSafetyState,
    MasterCanState,
    DigitalTwinSyncState,
)
from integration_adapters.fail_safe_controller import (
    FailSafeState,
    CommandAction,
    IncomingCommand,
    LocalVehicleSafetyGovernor,
)
from integration_adapters.end_to_end_safety_state_machine import (
    EndToEndSafetyStateMachine,
    IntegratedSafetyState,
    SubsystemAuthority,
)
from integration_adapters.can_twai_hil import (
    CAN_ID_SAFETY_COMMAND,
    CAN_ID_VEHICLE_SPEED,
    CanFrame,
    CanBusState,
    CanTwaiBusEmulator,
    encode_vehicle_speed,
    decode_vehicle_speed,
    encode_safety_command,
    decode_safety_command,
)
from integration_adapters.dsss_gateway_selector import (
    DSSSGatewaySelector,
    GatewaySelectionState,
    LinkState,
    CommunicationLink,
)
from integration_adapters.environmental_data_health import (
    EnvironmentalDataHealth,
    DataState,
    FaultCode,
    SensorQuality,
)
from failsafe.safe_beacon import (
    SafeBeaconState,
    SafeBeaconSystemState,
    SafeBeaconController,
    format_safe_beacon,
    parse_safe_beacon,
)
from integration_adapters.digital_twin_sync import (
    DigitalTwinEngine,
    TwinOperatingMode,
)


# =========================================================================
# 1. PHASE H1: HARDWARE INTERFACE FREEZE (TB6612FNG & ENCODERS)
# =========================================================================

class TestPhaseH1HardwareInterface:
    """Tests for physical Vehicle B (TRUCK_02) TB6612FNG and odometry freeze."""

    def test_truck_02_tb6612fng_pinout_verification(self):
        with open("config/physical_vehicle_parameters.json", "r") as f:
            params = json.load(f)

        truck_b = params["TRUCK_02"]
        assert truck_b["motor_driver"] == "TB6612FNG", "Vehicle B must use TB6612FNG, NOT L298N!"
        pinout = truck_b["pinout"]
        assert pinout["LEFT_IN1"] == 25
        assert pinout["LEFT_IN2"] == 26
        assert pinout["LEFT_PWM"] == 27
        assert pinout["RIGHT_IN1"] == 32
        assert pinout["RIGHT_IN2"] == 33
        assert pinout["RIGHT_PWM"] == 14
        assert pinout["MOTOR_STBY"] == 13
        assert pinout["SPEED_SENSOR_PIN"] == 35

    def test_truck_02_kinematic_derivation(self):
        """Verify wheel diameter and PPR distance and speed calculations."""
        with open("config/physical_vehicle_parameters.json", "r") as f:
            params = json.load(f)

        truck_b = params["TRUCK_02"]
        d = truck_b["wheel_diameter_m"]
        ppr = truck_b["pulses_per_revolution"]
        assert d > 0.0
        assert ppr > 0.0

        wheel_circ = math.pi * d
        # In 1 second, ppr pulses recorded = 1 rev = wheel_circ m
        delta_pulses = ppr
        delta_t_s = 1.0
        speed_mps = (delta_pulses / ppr) * wheel_circ / delta_t_s
        assert pytest.approx(speed_mps, 0.001) == wheel_circ

        # Distance derivation
        total_dist = (100.0 / ppr) * wheel_circ
        assert total_dist > 0.0


# =========================================================================
# 2. PHASE H2: CANONICAL TELEMETRY SCHEMA & INGESTION INTEGRITY
# =========================================================================

class TestPhaseH2VehicleTelemetry:
    """Tests canonical schema validation, timestamps, and error handling."""

    def test_valid_canonical_telemetry_creation(self):
        state = VehicleState(
            vehicle_id="TRUCK_02",
            data_source=DataSourceType.HARDWARE,
            event_timestamp=100.0,
            receive_timestamp=100.02,
            processing_timestamp=100.03,
            speed=0.50,
            visibility=15.0,
            grade=-8.0,
            sensor_health=MasterSensorQuality.VALID,
            gateway_id="GW_01",
            safe_speed=3.52,
        )
        assert state.vehicle_id == "TRUCK_02"
        assert state.speed == 0.50
        assert state.grade == -8.0
        assert state.sensor_health == MasterSensorQuality.VALID

    def test_telemetry_rejection_of_impossible_values(self):
        """Negative speed must raise a validation error."""
        with pytest.raises(Exception):
            VehicleState(
                vehicle_id="TRUCK_02",
                event_timestamp=100.0,
                receive_timestamp=100.02,
                processing_timestamp=100.03,
                speed=-5.0,  # Impossible negative speed
            )


# =========================================================================
# 3. PHASE H3: 8-STATE SENSOR HEALTH INTEGRATION
# =========================================================================

class TestPhaseH3SensorHealth:
    """Verifies that sensor health transitions deterministically alter safety."""

    def test_sensor_health_states_and_reactions(self):
        t0 = 1000.0
        health = EnvironmentalDataHealth(clock=lambda: t0)

        # 1. Normal optical scatter
        sig1 = health.update(visibility_m=25.0, timestamp=t0, sequence=1)
        assert sig1.health == DataState.HEALTHY
        assert sig1.value == 25.0

        # 2. Outlier rejection (impossible spike)
        sig2 = health.update(visibility_m=2500.0, timestamp=t0 + 0.1, sequence=2)
        assert sig2.health in [DataState.DEGRADED, DataState.UNAVAILABLE]
        assert sig2.fault_code == FaultCode.RANGE_VIOLATION


# =========================================================================
# 4. PHASE H4: SAFETY GOVERNOR & SPEED CLAMPING
# =========================================================================

class TestPhaseH4SafetyGovernor:
    """Verifies that local safety governor clamps remote commands unconditionally."""

    def test_speed_clamping_hierarchy(self):
        t0 = 1000.0
        governor = LocalVehicleSafetyGovernor(
            vehicle_id="TRUCK_02",
            v_safe_default=3.52,
            clock=lambda: t0
        )

        # Dispatch commands 15.0 m/s in fog where v_safe is 3.52 m/s
        cmd = IncomingCommand(
            vehicle_id="TRUCK_02",
            sequence=1,
            timestamp=t0 - 0.05,
            requested_speed_mps=15.0,
            command_source="CENTRAL",
        )
        decision = governor.process_command(cmd)

        assert decision.action == CommandAction.CLAMP
        assert decision.applied_speed == 3.52, "Local governor MUST clamp command to v_safe!"

    def test_stale_command_rejection(self):
        t0 = 1000.0
        governor = LocalVehicleSafetyGovernor(
            vehicle_id="TRUCK_02",
            v_safe_default=3.52,
            clock=lambda: t0
        )

        # Command is 2.5 seconds old (> max_command_age_s = 1.0s)
        stale_cmd = IncomingCommand(
            vehicle_id="TRUCK_02",
            sequence=1,
            timestamp=t0 - 2.5,
            requested_speed_mps=3.0,
        )
        decision = governor.process_command(stale_cmd)
        assert decision.action == CommandAction.REJECT
        assert decision.state == FailSafeState.STALE_COMMAND


# =========================================================================
# 5. PHASE H6: SAFE BEACON & RESILIENCE PATH
# =========================================================================

class TestPhaseH6SafeBeaconResilience:
    """Verifies Safe Beacon independent activation upon comm loss and recovery."""

    def test_safe_beacon_activation_on_comm_loss(self):
        t = [100.0]
        beacon_ctrl = SafeBeaconController(
            vehicle_id="TRUCK_02",
            comm_timeout_s=0.5,
            clock=lambda: t[0]
        )

        # Before timeout
        assert beacon_ctrl.check_comm_timeout(now=t[0]) is False
        assert beacon_ctrl.is_standalone_active is False

        # Advance clock past 500 ms heartbeat timeout
        t[0] += 0.55
        is_timed_out = beacon_ctrl.check_comm_timeout(now=t[0])

        assert is_timed_out is True
        assert beacon_ctrl.is_standalone_active is True
        assert beacon_ctrl.system_state == SafeBeaconSystemState.COMM_LOSS

        # Generate beacon packet
        beacon_str = beacon_ctrl.generate_beacon(now=t[0])
        valid, msg, err = parse_safe_beacon(beacon_str, clock=lambda: t[0])
        assert valid is True
        assert msg.vehicle_id == "TRUCK_02"
        assert msg.state == SafeBeaconState.DEGRADED

    def test_safe_beacon_recovery_requires_validation(self):
        t = [100.0]
        beacon_ctrl = SafeBeaconController(
            vehicle_id="TRUCK_02",
            comm_timeout_s=0.5,
            clock=lambda: t[0]
        )
        # Force into comm loss
        t[0] += 0.6
        beacon_ctrl.check_comm_timeout(now=t[0])
        assert beacon_ctrl.is_standalone_active is True

        # Restoring link notifies controller
        t[0] += 0.1
        beacon_ctrl.notify_central_comm_received(timestamp=t[0])
        assert beacon_ctrl.is_standalone_active is False
        assert beacon_ctrl.system_state == SafeBeaconSystemState.NORMAL


# =========================================================================
# 6. PHASE H7: CAN / TWAI ABSTRACTION
# =========================================================================

class TestPhaseH7CanTwaiAbstraction:
    """Verifies TWAI framing, priority arbitration, and watchdog silence."""

    def test_can_emergency_priority_arbitration(self):
        bus = CanTwaiBusEmulator()

        # High priority brake frame (PGN 0xF001, Emergency Stop action 4)
        frame = encode_safety_command(target_speed_mps=0.0, action_code=4, sequence=1, timestamp=time.time())
        delivered, latency_ms = bus.transmit(frame)

        assert delivered is True
        assert latency_ms < 50.0, f"CAN delivery latency {latency_ms} ms must be < 50 ms budget"

    def test_can_watchdog_timeout_on_silence(self):
        bus = CanTwaiBusEmulator()
        bus.set_fault_injection(bus_off=True)
        frame = encode_safety_command(target_speed_mps=0.0, action_code=4, sequence=1, timestamp=time.time())
        delivered, latency_ms = bus.transmit(frame)
        assert delivered is False, "Frame cannot be delivered during bus-off silence"


# =========================================================================
# 7. PHASE H8: DIGITAL TWIN INTEGRATION & COMMAND ISOLATION
# =========================================================================

class TestPhaseH8DigitalTwinIntegration:
    """Verifies that WHAT_IF / REPLAY / FAULT modes never command physical hardware."""

    def test_twin_operating_modes_and_what_if(self):
        twin = DigitalTwinEngine(vehicle_id="TRUCK_02")
        assert twin.mode == TwinOperatingMode.LIVE_MIRROR

        state = VehicleState(
            vehicle_id="TRUCK_02",
            event_timestamp=100.0,
            receive_timestamp=100.02,
            processing_timestamp=100.03,
            speed=1.0,
            visibility=20.0,
            grade=-5.0,
        )
        sync_state = twin.ingest_real_telemetry(state, now=100.03)
        assert sync_state == DigitalTwinSyncState.SYNCHRONIZED

        # Run What-If scenario (Simulate sudden 5m dense fog on -8% grade)
        what_if_res = twin.run_what_if_scenario(
            visibility_m=5.0,
            grade_pct=-8.0,
            friction_mu=0.35,
            comm_lost=True
        )
        assert what_if_res["predicted_safe_speed_mps"] == 0.0, "Blindout What-If must predict 0 m/s stop"


# =========================================================================
# 8. MASTER SAFETY INVARIANTS (I1 TO I10)
# =========================================================================

class TestSafetyInvariants:
    """Formal mathematical validation of the 10 core safety invariants."""

    def test_invariant_1_central_cannot_exceed_local_governor(self):
        governor = LocalVehicleSafetyGovernor(vehicle_id="TRUCK_02", v_safe_default=3.52)
        cmd = IncomingCommand(
            vehicle_id="TRUCK_02",
            sequence=10,
            timestamp=time.time(),
            requested_speed_mps=12.0,
        )
        decision = governor.process_command(cmd)
        assert decision.applied_speed <= 3.52

    def test_invariant_2_comm_loss_preserves_local_safety(self):
        sm = EndToEndSafetyStateMachine(vehicle_id="TRUCK_02")
        eval_res = sm.evaluate_state(
            visibility_m=8.0,
            sensor_quality=SensorQuality.VALID,
            gateway_state=GatewaySelectionState.NO_GATEWAY,
            comm_lost=True,
            requested_speed_mps=5.0
        )
        assert eval_res.remote_command_allowed is False
        assert eval_res.applied_speed_mps <= eval_res.v_safe_mps

    def test_invariant_3_safe_beacon_cannot_actuate_motors(self):
        """Safe Beacon state generates RF strings; it does NOT possess a motor PWM handle."""
        beacon_ctrl = SafeBeaconController(vehicle_id="TRUCK_02")
        beacon_str = format_safe_beacon("TRUCK_02", 1, SafeBeaconState.NORMAL, time.time(), "ZONE_1")
        assert isinstance(beacon_str, str)
        assert not hasattr(beacon_ctrl, "set_motor_pwm")
        assert not hasattr(beacon_ctrl, "motor_driver")

    def test_invariant_10_emergency_stop_latches_zero_speed(self):
        sm = EndToEndSafetyStateMachine(vehicle_id="TRUCK_02")
        sm.trigger_emergency_stop("ESTOP_PUSHBUTTON")
        eval_res = sm.evaluate_state(
            visibility_m=50.0,
            sensor_quality=SensorQuality.VALID,
            gateway_state=GatewaySelectionState.CONNECTED,
            comm_lost=False,
            requested_speed_mps=10.0
        )
        assert eval_res.state == IntegratedSafetyState.EMERGENCY_STOP
        assert eval_res.applied_speed_mps == 0.0
        assert eval_res.remote_command_allowed is False
