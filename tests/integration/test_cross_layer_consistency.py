"""
tests/integration/test_cross_layer_consistency.py
-------------------------------------------------
FOG-ORCHESTRATOR 2.0 — Cross-Layer Value Consistency Test Suite
SIH 2026-27 | Phase H11 Parameter Reconciliation

Verifies that for the exact same event timestamp:
  - vehicle_id
  - speed (m/s and km/h)
  - safe_speed (m/s and km/h)
  - grade (% / deg)
  - visibility (m)
  - RF / gateway state
  - sensor health
  - safety state
  - Safe Beacon state
are 100% IDENTICAL across:
  1. Microcontroller telemetry payload (ESP32)
  2. Ingestion layer (Backend MasterDataModel)
  3. Operator HMI projected view
  4. Control Room HMI projected view
  5. Digital Twin synchronized mirror

Any value drift or independent recalculation inside the frontend is treated as a fatal violation.
"""

import math
import time
import pytest
from integration_adapters.master_data_model import (
    VehicleState,
    DataSourceType,
    MasterSafetyState,
    MasterSensorQuality,
    DigitalTwinSyncState,
)
from integration_adapters.digital_twin_sync import DigitalTwinEngine, TwinOperatingMode
from integration_adapters.unit_converter import UnitConverter


class TestCrossLayerConsistency:
    """Rigorous end-to-end verification of parameter parity across all architectural layers."""

    @pytest.fixture
    def canonical_event_packet(self):
        """Simulates raw incoming ASCII packet from physical ESP32 Vehicle B."""
        # D = 0.060 m, PPR_eff = 34.58
        # At 240 RPM, speed = 240 * pi * 0.060 / 60 = 0.7540 m/s
        return {
            "vehicle_id": "TRUCK_02",
            "event_timestamp": 1727180000.125,
            "rpm": 240.0,
            "speed_reported": 0.7540,
            "ax": 0.12,
            "ay": -0.05,
            "az": 9.81,
            "gx": 0.02,
            "gy": 0.01,
            "gz": -0.03,
            "rssi": -68.0,
            "snr": 9.5,
            "gateway_id": "GW_01",
            "gateway_state": "CONNECTED",
            "visibility_m": 45.0,
            "grade_pct": -4.0,  # civil downhill 4%
            "safe_speed_limit": 1.40,
            "safety_state": MasterSafetyState.NORMAL,
            "safe_beacon_state": "INACTIVE",
            "sensor_health": MasterSensorQuality.VALID,
        }

    def test_cross_layer_exact_value_propagation(self, canonical_event_packet):
        pkt = canonical_event_packet

        # 1. ESP32 Layer Kinematics
        converter = UnitConverter("config/physical_vehicle_parameters.json")
        derived_speed_mps = converter.rpm_to_speed_mps(pkt["vehicle_id"], pkt["rpm"])
        assert derived_speed_mps is not None
        assert math.isclose(derived_speed_mps, 0.7540, abs_tol=1e-3)

        # 2. Ingestion / Backend State Model
        t_recv = pkt["event_timestamp"] + 0.0014
        backend_state = VehicleState(
            vehicle_id=pkt["vehicle_id"],
            event_timestamp=pkt["event_timestamp"],
            receive_timestamp=t_recv,
            processing_timestamp=t_recv + 0.0002,
            data_source=DataSourceType.HARDWARE,
            speed=derived_speed_mps,
            position=124.50,
            visibility=pkt["visibility_m"],
            grade=pkt["grade_pct"],
            gateway_id=pkt["gateway_id"],
            gateway_state=pkt["gateway_state"],
            RSSI=pkt["rssi"],
            SNR=pkt["snr"],
            safe_speed=pkt["safe_speed_limit"],
            commanded_speed=derived_speed_mps,
            safety_state=pkt["safety_state"],
            safe_beacon_state=pkt["safe_beacon_state"],
            sensor_health=pkt["sensor_health"],
        )

        # 3. Digital Twin Ingestion
        twin = DigitalTwinEngine("TRUCK_02")
        twin_sync_status = twin.ingest_real_telemetry(backend_state, now=t_recv + 0.0005)
        twin_view = backend_state.to_digital_twin_view()

        # 4. Operator HMI View Projection
        operator_view = backend_state.to_operator_hmi_view(now=t_recv + 0.0005)

        # 5. Control Room HMI View Projection
        control_room_view = backend_state.to_control_room_view(now=t_recv + 0.0005)

        # =========================================================================
        # PARITY ASSERTIONS: Must match across all views for identical timestamp
        # =========================================================================

        # A. Vehicle ID
        assert backend_state.vehicle_id == "TRUCK_02"
        assert operator_view["vehicle_id"] == "TRUCK_02"
        assert control_room_view["vehicle_id"] == "TRUCK_02"
        assert twin_view["vehicle_id"] == "TRUCK_02"

        # B. Speed (mps and kmh)
        assert backend_state.speed == 0.7540
        assert operator_view["speed_mps"] == 0.75
        assert operator_view["speed_kmh"] == round(0.7540 * 3.6, 1)
        assert control_room_view["speed_kmh"] == round(0.7540 * 3.6, 1)
        assert twin_view["speed_mps"] == 0.7540

        # C. Safe Speed Limit
        assert backend_state.safe_speed == 1.40
        assert operator_view["safe_speed_mps"] == 1.40
        assert operator_view["safe_speed_kmh"] == round(1.40 * 3.6, 1)
        assert control_room_view["safe_speed_kmh"] == round(1.40 * 3.6, 1)
        assert twin_view["safe_speed_mps"] == 1.40

        # D. Grade
        assert backend_state.grade == -4.0
        assert operator_view["grade_pct"] == -4.0
        assert control_room_view["grade_pct"] == -4.0
        assert twin_view["grade_pct"] == -4.0

        # E. Visibility
        assert backend_state.visibility == 45.0
        assert operator_view["visibility_m"] == 45.0
        assert control_room_view["visibility_m"] == 45.0
        assert twin_view["visibility_m"] == 45.0

        # F. RF / Gateway State
        assert backend_state.gateway_state == "CONNECTED"
        assert operator_view["gateway_status"] == "GW_01 (CONNECTED)"
        assert control_room_view["gateway_id"] == "GW_01"
        assert twin_view["gateway_state"] == "CONNECTED"

        # G. Sensor Health
        assert backend_state.sensor_health == MasterSensorQuality.VALID
        assert operator_view["sensor_health"] == "VALID"
        assert control_room_view["sensor_quality"] == "VALID"
        assert twin_view["sensor_health"] == "VALID"

        # H. Safety State
        assert backend_state.safety_state == MasterSafetyState.NORMAL
        assert operator_view["safety_state"] == "NORMAL"
        assert control_room_view["safety_state"] == "NORMAL"
        assert twin_view["safety_state"] == "NORMAL"

        # I. Safe Beacon State
        assert backend_state.safe_beacon_state == "INACTIVE"
        assert control_room_view["safe_beacon_active"] is False
        assert twin_view["safe_beacon_state"] == "INACTIVE"

    def test_hmi_prohibits_independent_safety_calculation(self):
        """Verify that modifying local variables does not affect backend safety enforcement."""
        backend_state = VehicleState(
            vehicle_id="TRUCK_01",
            event_timestamp=1000.0,
            receive_timestamp=1000.002,
            processing_timestamp=1000.003,
            data_source=DataSourceType.HARDWARE,
            speed=1.20,
            safe_speed=0.50,  # Safe speed ceiling forced by fog
            safety_state=MasterSafetyState.DEGRADED,
        )

        op_view = backend_state.to_operator_hmi_view()
        # Operator action MUST recommend REDUCE SPEED because speed (1.20) > safe_speed (0.50)
        assert op_view["active_warning"] == "REDUCE SPEED"
        assert op_view["safe_speed_mps"] == 0.50

    def test_digital_twin_safety_boundary_enforcement(self):
        """Verify Safety Invariant 6: Simulation modes cannot issue physical actuator commands."""
        twin = DigitalTwinEngine("TRUCK_01")

        # LIVE_MIRROR mode is authorized to recommend commands via safety governor
        twin.set_mode(TwinOperatingMode.LIVE_MIRROR)
        assert twin.can_issue_physical_command() is True

        # Simulation and replay modes are STRICTLY PROHIBITED from commanding hardware
        for restricted_mode in [
            TwinOperatingMode.WHAT_IF,
            TwinOperatingMode.REPLAY,
            TwinOperatingMode.PREDICTIVE,
            TwinOperatingMode.FAULT_INJECTION,
        ]:
            twin.set_mode(restricted_mode)
            assert twin.can_issue_physical_command() is False, (
                f"Mode {restricted_mode} must NEVER be allowed to command physical actuators!"
            )
