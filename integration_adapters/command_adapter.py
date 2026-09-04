"""
FOG-ORCHESTRATOR 2.0 — Command Adapter (Blocker 8 Resolution)

Bridges Digital Twin advisory recommendations to physical commands while strictly
enforcing LOCAL SAFETY AUTHORITY > CENTRAL OPTIMIZATION. Distinguishes RECOMMENDED,
REQUESTED, and APPLIED speed values and correlates vehicle ACKs (ACCEPTED, CLAMPED, REJECTED, FAILED, TIMEOUT).
"""

import time
import logging
from typing import Dict, Any, Optional

from integration_adapters.kinematic_scale import KinematicScaleAdapter
from integration_adapters.vehicle_id_mapper import VehicleIDMapper
from integration_adapters.time_adapter import TimeAdapter

logger = logging.getLogger("CommandAdapter")

class CommandAdapter:
    """Manages command flow and ACK correlation between Digital Twin and Physical Vehicles."""

    def __init__(self, id_mapper: Optional[VehicleIDMapper] = None, scale_adapter: Optional[KinematicScaleAdapter] = None, time_adapter: Optional[TimeAdapter] = None):
        self.id_mapper = id_mapper or VehicleIDMapper()
        self.scale_adapter = scale_adapter or KinematicScaleAdapter()
        self.time_adapter = time_adapter or TimeAdapter()
        self.issued_commands: Dict[str, Dict[str, Any]] = {}

    def translate_twin_advisory_to_command(self, twin_advisory: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Translates Digital Twin advisory target speed to canonical physical HMI command.
        Distinguishes RECOMMENDED_VALUE vs REQUESTED_VALUE.
        """
        return self.translate_twin_advisory(twin_advisory)

    def translate_twin_advisory(self, twin_advisory: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Translates Digital Twin advisory target speed to canonical physical HMI command.
        Distinguishes RECOMMENDED_VALUE vs REQUESTED_VALUE.
        """
        if not twin_advisory or not isinstance(twin_advisory, dict):
            logger.error("[CommandAdapter] Invalid twin_advisory payload")
            return None

        # Check recommendation expiration
        adv_ts = twin_advisory.get("timestamp", time.time())
        if self.time_adapter.is_recommendation_expired(adv_ts):
            logger.warning(f"[CommandAdapter] Twin advisory recommendation expired (ts: {adv_ts})")
            return None

        twin_vid = twin_advisory.get("vehicle_id")
        physical_vid = self.id_mapper.to_physical_id(twin_vid) if twin_vid else None
        if not physical_vid:
            # Try direct lookup if already physical ID
            if self.id_mapper.is_mapped_physical(twin_vid):
                physical_vid = twin_vid
            else:
                logger.error(f"[CommandAdapter] Unknown vehicle ID for twin advisory: '{twin_vid}'")
                return None

        rec_speed = float(twin_advisory.get("recommended_speed", 0.0))
        # Scale 165t dumper advisory speed to physical prototype bounds
        req_speed = self.scale_adapter.twin_advisory_to_physical_speed(rec_speed)

        cmd_id = f"CMD_{int(time.time() * 1000)}_{physical_vid}"
        action = twin_advisory.get("action", "TARGET_SPEED").upper()

        command_record = {
            "command_id": cmd_id,
            "vehicle_id": physical_vid,
            "action": action,
            "recommended_value": rec_speed,
            "requested_value": req_speed,
            "timestamp": time.time(),
            "status": "ISSUED",
            "reason": twin_advisory.get("reason", "TWIN_ADVISORY_DISPATCH")
        }
        self.issued_commands[cmd_id] = command_record
        return command_record

    def process_vehicle_ack(self, ack_payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Processes physical vehicle command ACK (ACCEPTED, CLAMPED, REJECTED, FAILED, TIMEOUT).
        Records APPLIED_VALUE and returns updated ACK state to Digital Twin.
        """
        now = time.time()
        cmd_id = ack_payload.get("command_id")
        if not cmd_id or cmd_id not in self.issued_commands:
            logger.warning(f"[CommandAdapter] Received ACK for unrecorded/expired command_id: '{cmd_id}'")
            return {
                "command_id": cmd_id or "UNKNOWN",
                "vehicle_id": ack_payload.get("vehicle_id", "UNKNOWN"),
                "status": "REJECTED",
                "applied_value": 0.0,
                "timestamp": now,
                "message": "Unrecorded command ID"
            }

        cmd_record = self.issued_commands[cmd_id]
        status = ack_payload.get("status", "ACCEPTED").upper()
        applied_speed = float(ack_payload.get("applied_speed", ack_payload.get("applied_value", cmd_record["requested_value"])))

        cmd_record["status"] = status
        cmd_record["applied_value"] = applied_speed
        cmd_record["ack_timestamp"] = now
        cmd_record["round_trip_ms"] = round((now - cmd_record["timestamp"]) * 1000.0, 2)

        twin_vid = self.id_mapper.to_twin_id(cmd_record["vehicle_id"]) or cmd_record["vehicle_id"]

        return {
            "command_id": cmd_id,
            "vehicle_id": cmd_record["vehicle_id"],
            "twin_vehicle_id": twin_vid,
            "action": cmd_record["action"],
            "recommended_value": cmd_record["recommended_value"],
            "requested_value": cmd_record["requested_value"],
            "applied_value": applied_speed,
            "ack_status": status,
            "round_trip_ms": cmd_record["round_trip_ms"],
            "timestamp": now
        }
