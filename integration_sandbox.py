"""
FOG-ORCHESTRATOR 2.0 — Integration Sandbox Runner

Non-invasive controlled integration runner bridging Phase 1 (Physical Hardware ↔ HMI)
and Phase 2 (Digital Twin ↔ Central Orchestrator) through the Integration Adapter Layer.
DO NOT modify production runtimes. Operates as an independent sandbox process.
"""

import sys
import os
import time
import json
import logging
from typing import Dict, Any, Optional

# Ensure project root is in sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from integration_adapters.vehicle_id_mapper import VehicleIDMapper
from integration_adapters.unit_converter import UnitConverter
from integration_adapters.kinematic_scale import KinematicScaleAdapter
from integration_adapters.imu_processor import IMUProcessor
from integration_adapters.time_adapter import TimeAdapter
from integration_adapters.coordinate_mapper import CoordinateMapper
from integration_adapters.telemetry_quality_filter import TelemetryQualityFilter
from integration_adapters.command_adapter import CommandAdapter

logger = logging.getLogger("IntegrationSandbox")

class IntegrationSandbox:
    """Sandbox runtime bridging Phase 1 telemetry to Phase 2 Digital Twin advisory loop."""

    def __init__(self):
        self.id_mapper = VehicleIDMapper()
        self.unit_converter = UnitConverter()
        self.scale_adapter = KinematicScaleAdapter()
        self.imu_processor = IMUProcessor(is_calibrated=True)
        self.time_adapter = TimeAdapter()
        self.coordinate_mapper = CoordinateMapper()
        self.quality_filter = TelemetryQualityFilter()
        self.command_adapter = CommandAdapter(
            id_mapper=self.id_mapper,
            scale_adapter=self.scale_adapter,
            time_adapter=self.time_adapter
        )

    def process_physical_telemetry_frame(self, raw_telemetry: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Passes physical telemetry frame through adapter pipeline:
        Physical Telemetry -> Time Adapter -> Quality Filter -> ID Mapper -> Unit Converter -> IMU Processor -> Coordinate Mapper -> Adapted Digital Twin Payload
        """
        # Step 1: Time synchronization & sequence tracking
        timed = self.time_adapter.process_telemetry(raw_telemetry)

        # Step 2: Quality filter & trust evaluation
        filtered = self.quality_filter.filter_telemetry(timed)
        if not filtered.get("should_update_twin", False):
            logger.warning(f"Telemetry rejected by Quality Filter (Quality: {filtered.get('data_quality')})")
            return None

        # Step 3: Vehicle ID mapping
        physical_vid = filtered.get("vehicle_id")
        twin_vid = self.id_mapper.to_twin_id(physical_vid)
        if not twin_vid:
            logger.error(f"Unmapped physical vehicle ID: {physical_vid}")
            return None

        # Step 4: Unit conversion & kinematic scaling
        rpm = filtered.get("rpm", 0.0)
        speed_mps = self.unit_converter.rpm_to_speed_mps(physical_vid, rpm) or filtered.get("speed_mps", 0.0)
        scale_info = self.scale_adapter.physical_to_twin_speed(speed_mps)

        # Step 5: IMU processing
        imu_state = self.imu_processor.process(filtered)

        # Step 6: Coordinate mapping / dead reckoning
        pose_info = self.coordinate_mapper.update_pose(
            physical_vid,
            speed_mps,
            imu_state["angular_velocity_rads"]["z"],
            dt_s=0.5,
            is_stale=filtered.get("is_stale", False)
        )

        # Step 7: Assemble Adapted Digital Twin Payload matching contracts.py schema
        adapted_payload = {
            "vehicle_id": twin_vid,
            "physical_vehicle_id": physical_vid,
            "sequence_number": filtered["sequence_number"],
            "source_timestamp": filtered["source_timestamp"],
            "integration_timestamp": filtered["integration_timestamp"],
            "speed": scale_info["twin_equivalent_speed_mps"],
            "physical_speed_mps": scale_info["physical_speed_mps"],
            "normalized_speed": scale_info["normalized_speed"],
            "acceleration_x": imu_state["acceleration_mps2"]["x"],
            "acceleration_y": imu_state["acceleration_mps2"]["y"],
            "gyroscope_z": imu_state["angular_velocity_rads"]["z"],
            "position_x": pose_info["x_twin"],
            "position_y": pose_info["y_twin"],
            "position_quality": pose_info["position_quality"],
            "communication_status": filtered["data_quality"],
            "safety_state": filtered.get("safety_state", "NORMAL")
        }
        return adapted_payload

    def process_twin_advisory_recommendation(self, twin_advisory: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Passes Digital Twin advisory recommendation through Command Adapter to physical command."""
        return self.command_adapter.translate_twin_advisory(twin_advisory)

    def process_physical_vehicle_ack(self, ack_payload: Dict[str, Any]) -> Dict[str, Any]:
        """Passes physical vehicle ACK through Command Adapter to Digital Twin."""
        return self.command_adapter.process_vehicle_ack(ack_payload)


if __name__ == "__main__":
    sandbox = IntegrationSandbox()
    test_pkt = {
        "vehicle_id": "TRUCK_01",
        "sequence_number": 1,
        "timestamp": time.time(),
        "rpm": 240.0,
        "speed_mps": 2.51,
        "acceleration": {"x": 0.12, "y": -0.05, "z": 9.81},
        "gyroscope": {"x": 0.02, "y": 0.01, "z": -0.03}
    }
    res = sandbox.process_physical_telemetry_frame(test_pkt)
    print("Adapted Digital Twin Payload:", json.dumps(res, indent=2))
