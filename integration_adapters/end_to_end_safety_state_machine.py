"""
integration_adapters/end_to_end_safety_state_machine.py
-------------------------------------------------------
FOG-ORCHESTRATOR 2.0 — End-to-End Safety State Machine & Authority Arbitrator.
SIH 2026-27 | Problem Statement: SIH26007

AUTHORITY HIERARCHY (SECTION 10 & 11):
  PRIORITY 1: Emergency physical safety (Firmware watchdog, E-Stop latch)
  PRIORITY 2: Local safety governor (Level 1 vehicle ECU authority)
  PRIORITY 3: Valid local sensor information (IMU, Wheel speed, Local Transmissometer)
  PRIORITY 4: Communication-derived information (V2V, Gateway RF telemetry)
  PRIORITY 5: Fleet optimization (Orchestrator dispatch, Headway regulation)
  PRIORITY 6: Production optimization (Throughput maximization, Cycle targets)

CORE INVARIANT:
  Production optimization must NEVER override a safety invariant.
  v_applied <= v_safe strictly holds in all states.
  During COMMUNICATION_LOST, NO REMOTE COMMAND IS ACCEPTED.
"""

from __future__ import annotations

import logging
import math
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple

from integration_adapters.environmental_data_health import SensorQuality
from integration_adapters.dsss_gateway_selector import GatewaySelectionState, LinkState
from integration_adapters.fail_safe_controller import CommandAction

logger = logging.getLogger("EndToEndSafetyStateMachine")


class IntegratedSafetyState(str, Enum):
    NORMAL = "NORMAL"
    DEGRADED_VISIBILITY = "DEGRADED_VISIBILITY"
    SENSOR_DEGRADED = "SENSOR_DEGRADED"
    COMMUNICATION_DEGRADED = "COMMUNICATION_DEGRADED"
    HANDOVER = "HANDOVER"
    COMMUNICATION_LOST = "COMMUNICATION_LOST"
    SAFE_BEACON = "SAFE_BEACON"
    LOCAL_SAFE_GOVERNOR = "LOCAL_SAFE_GOVERNOR"
    RECOVERY = "RECOVERY"
    EMERGENCY_STOP = "EMERGENCY_STOP"


class SubsystemAuthority(str, Enum):
    EMERGENCY_PHYSICAL_SAFETY = "EMERGENCY_PHYSICAL_SAFETY"   # Priority 1
    LOCAL_SAFETY_GOVERNOR = "LOCAL_SAFETY_GOVERNOR"           # Priority 2
    VALID_LOCAL_SENSOR_INFO = "VALID_LOCAL_SENSOR_INFO"       # Priority 3
    COMMUNICATION_DERIVED_INFO = "COMMUNICATION_DERIVED_INFO" # Priority 4
    FLEET_OPTIMIZATION = "FLEET_OPTIMIZATION"                 # Priority 5
    PRODUCTION_OPTIMIZATION = "PRODUCTION_OPTIMIZATION"       # Priority 6


# Map state to authoritative subsystem and authority priority rank (lower is higher priority)
STATE_AUTHORITY_MAP: Dict[IntegratedSafetyState, Tuple[SubsystemAuthority, int]] = {
    IntegratedSafetyState.EMERGENCY_STOP: (SubsystemAuthority.EMERGENCY_PHYSICAL_SAFETY, 1),
    IntegratedSafetyState.LOCAL_SAFE_GOVERNOR: (SubsystemAuthority.LOCAL_SAFETY_GOVERNOR, 2),
    IntegratedSafetyState.SAFE_BEACON: (SubsystemAuthority.LOCAL_SAFETY_GOVERNOR, 2),
    IntegratedSafetyState.COMMUNICATION_LOST: (SubsystemAuthority.LOCAL_SAFETY_GOVERNOR, 2),
    IntegratedSafetyState.RECOVERY: (SubsystemAuthority.LOCAL_SAFETY_GOVERNOR, 2),
    IntegratedSafetyState.SENSOR_DEGRADED: (SubsystemAuthority.VALID_LOCAL_SENSOR_INFO, 3),
    IntegratedSafetyState.HANDOVER: (SubsystemAuthority.LOCAL_SAFETY_GOVERNOR, 2),
    IntegratedSafetyState.COMMUNICATION_DEGRADED: (SubsystemAuthority.LOCAL_SAFETY_GOVERNOR, 2),
    IntegratedSafetyState.DEGRADED_VISIBILITY: (SubsystemAuthority.LOCAL_SAFETY_GOVERNOR, 2),
    IntegratedSafetyState.NORMAL: (SubsystemAuthority.FLEET_OPTIMIZATION, 5),
}


@dataclass
class SafetyStateEvaluation:
    """Evaluation result of the end-to-end safety state machine."""
    state: IntegratedSafetyState
    authority: SubsystemAuthority
    priority_level: int
    v_safe_mps: float
    command_action: CommandAction
    applied_speed_mps: float
    remote_command_allowed: bool
    safe_beacon_required: bool
    reason: str
    timestamp: float


class EndToEndSafetyStateMachine:
    """
    Arbitrates subsystem authority and manages deterministic safety state transitions.
    """

    def __init__(
        self,
        vehicle_id: str = "TRUCK_01",
        clock: Callable[[], float] = time.time
    ):
        self.vehicle_id = vehicle_id
        self.clock = clock

        self.current_state: IntegratedSafetyState = IntegratedSafetyState.NORMAL
        self.emergency_stop_latched: bool = False
        self.in_recovery: bool = False
        self.recovery_frames: int = 0
        self.history: List[Dict[str, Any]] = []

    def trigger_emergency_stop(self, reason: str = "ESTOP_TRIGGERED"):
        """Latches emergency stop with highest priority (Priority 1)."""
        self.emergency_stop_latched = True
        self.current_state = IntegratedSafetyState.EMERGENCY_STOP
        logger.critical(f"{self.vehicle_id}: EMERGENCY STOP LATCHED ({reason})")

    def reset_emergency_stop(self):
        """Clears emergency stop and transitions to RECOVERY."""
        self.emergency_stop_latched = False
        self.in_recovery = True
        self.recovery_frames = 0
        self.current_state = IntegratedSafetyState.RECOVERY

    def evaluate_state(
        self,
        visibility_m: float,
        sensor_quality: SensorQuality,
        gateway_state: GatewaySelectionState,
        comm_lost: bool,
        requested_speed_mps: float = 0.0,
        now: Optional[float] = None
    ) -> SafetyStateEvaluation:
        """
        Determines the authoritative safety state and applied speed setpoint.
        """
        t_now = now if now is not None else self.clock()

        # Compute kinematic safe speed floor
        v_safe = self._compute_kinematic_safe_speed(visibility_m)

        # ----------------------------------------------------------------------
        # Priority 1: Emergency Stop
        # ----------------------------------------------------------------------
        if self.emergency_stop_latched:
            self.current_state = IntegratedSafetyState.EMERGENCY_STOP
            return self._build_evaluation(
                state=IntegratedSafetyState.EMERGENCY_STOP,
                v_safe=0.0,
                applied_speed=0.0,
                action=CommandAction.REJECT,
                remote_allowed=False,
                beacon_required=True,
                reason="EMERGENCY_STOP: Priority 1 physical safety active",
                timestamp=t_now
            )

        # ----------------------------------------------------------------------
        # Priority 2: Communication Loss / Standalone Mode
        # ----------------------------------------------------------------------
        if comm_lost or gateway_state == GatewaySelectionState.NO_GATEWAY:
            self.current_state = IntegratedSafetyState.COMMUNICATION_LOST
            applied = min(v_safe, requested_speed_mps) if requested_speed_mps <= v_safe else v_safe
            return self._build_evaluation(
                state=IntegratedSafetyState.COMMUNICATION_LOST,
                v_safe=v_safe,
                applied_speed=v_safe,
                action=CommandAction.REJECT,
                remote_allowed=False,
                beacon_required=True,
                reason="COMMUNICATION_LOST: Remote command rejected, Local Safety Governor authoritative",
                timestamp=t_now
            )

        # ----------------------------------------------------------------------
        # Priority 2: Recovery Re-synchronization
        # ----------------------------------------------------------------------
        if self.in_recovery:
            self.recovery_frames += 1
            if self.recovery_frames >= 2:
                self.in_recovery = False
            else:
                self.current_state = IntegratedSafetyState.RECOVERY
                return self._build_evaluation(
                    state=IntegratedSafetyState.RECOVERY,
                    v_safe=v_safe,
                    applied_speed=min(v_safe, requested_speed_mps),
                    action=CommandAction.REJECT,
                    remote_allowed=False,
                    beacon_required=False,
                    reason="RECOVERY: Sequence stream re-synchronizing",
                    timestamp=t_now
                )

        # ----------------------------------------------------------------------
        # Priority 2: Gateway Handover in Progress
        # ----------------------------------------------------------------------
        if gateway_state == GatewaySelectionState.HANDOVER_PENDING:
            self.current_state = IntegratedSafetyState.HANDOVER
            applied = min(v_safe, requested_speed_mps)
            action = CommandAction.CLAMP if requested_speed_mps > v_safe else CommandAction.ACCEPT
            return self._build_evaluation(
                state=IntegratedSafetyState.HANDOVER,
                v_safe=v_safe,
                applied_speed=applied,
                action=action,
                remote_allowed=True,
                beacon_required=False,
                reason="HANDOVER: Gateway transition pending, speed clamped to local safe envelope",
                timestamp=t_now
            )

        # ----------------------------------------------------------------------
        # Priority 2: Communication Degraded
        # ----------------------------------------------------------------------
        if gateway_state == GatewaySelectionState.DEGRADED:
            self.current_state = IntegratedSafetyState.COMMUNICATION_DEGRADED
            applied = min(v_safe, requested_speed_mps)
            action = CommandAction.CLAMP if requested_speed_mps > v_safe else CommandAction.ACCEPT
            return self._build_evaluation(
                state=IntegratedSafetyState.COMMUNICATION_DEGRADED,
                v_safe=v_safe,
                applied_speed=applied,
                action=action,
                remote_allowed=True,
                beacon_required=True,
                reason="COMMUNICATION_DEGRADED: High packet loss or weak signal",
                timestamp=t_now
            )

        # ----------------------------------------------------------------------
        # Priority 3: Sensor Degraded / Fault
        # ----------------------------------------------------------------------
        if sensor_quality != SensorQuality.VALID:
            self.current_state = IntegratedSafetyState.SENSOR_DEGRADED
            # Conservative penalty for sensor degradation
            if sensor_quality in [SensorQuality.STUCK, SensorQuality.OUTLIER, SensorQuality.MISSING]:
                effective_v_safe = 0.0 if visibility_m <= 8.0 else min(v_safe, 3.52)
            else:
                effective_v_safe = min(v_safe, 4.45)
            applied = min(effective_v_safe, requested_speed_mps)
            action = CommandAction.CLAMP if requested_speed_mps > effective_v_safe else CommandAction.ACCEPT
            return self._build_evaluation(
                state=IntegratedSafetyState.SENSOR_DEGRADED,
                v_safe=effective_v_safe,
                applied_speed=applied,
                action=action,
                remote_allowed=True,
                beacon_required=True,
                reason=f"SENSOR_DEGRADED: Sensor quality is {sensor_quality.value}",
                timestamp=t_now
            )

        # ----------------------------------------------------------------------
        # Priority 2: Fog / Visibility Degraded
        # ----------------------------------------------------------------------
        if visibility_m < 25.0:
            self.current_state = IntegratedSafetyState.DEGRADED_VISIBILITY
            applied = min(v_safe, requested_speed_mps)
            action = CommandAction.CLAMP if requested_speed_mps > v_safe else CommandAction.ACCEPT
            return self._build_evaluation(
                state=IntegratedSafetyState.DEGRADED_VISIBILITY,
                v_safe=v_safe,
                applied_speed=applied,
                action=action,
                remote_allowed=True,
                beacon_required=(visibility_m <= 10.0),
                reason=f"DEGRADED_VISIBILITY: Fog sightline {visibility_m:.1f}m restricts safe speed",
                timestamp=t_now
            )

        # ----------------------------------------------------------------------
        # Priority 5/6: Normal Operation
        # ----------------------------------------------------------------------
        self.current_state = IntegratedSafetyState.NORMAL
        applied = min(v_safe, requested_speed_mps)
        action = CommandAction.CLAMP if requested_speed_mps > v_safe else CommandAction.ACCEPT
        return self._build_evaluation(
            state=IntegratedSafetyState.NORMAL,
            v_safe=v_safe,
            applied_speed=applied,
            action=action,
            remote_allowed=True,
            beacon_required=False,
            reason="NORMAL: All subsystems nominal, fleet optimization active",
            timestamp=t_now
        )

    def _compute_kinematic_safe_speed(
        self,
        visibility_m: float,
        tau_s: float = 0.80,
        a_dec: float = 2.7856,
        s_base: float = 5.0
    ) -> float:
        if visibility_m <= s_base:
            return 0.0
        available_dist = visibility_m - s_base
        discriminant = (tau_s ** 2) + 2.0 * available_dist / a_dec
        if discriminant <= 0:
            return 0.0
        v_root = (-tau_s + math.sqrt(discriminant)) * a_dec
        return max(0.0, min(11.11, float(v_root)))

    def _build_evaluation(
        self,
        state: IntegratedSafetyState,
        v_safe: float,
        applied_speed: float,
        action: CommandAction,
        remote_allowed: bool,
        beacon_required: bool,
        reason: str,
        timestamp: float
    ) -> SafetyStateEvaluation:
        authority, priority = STATE_AUTHORITY_MAP[state]
        ev = SafetyStateEvaluation(
            state=state,
            authority=authority,
            priority_level=priority,
            v_safe_mps=round(v_safe, 4),
            command_action=action,
            applied_speed_mps=round(applied_speed, 4),
            remote_command_allowed=remote_allowed,
            safe_beacon_required=beacon_required,
            reason=reason,
            timestamp=timestamp
        )
        self.history.append({
            "timestamp": timestamp,
            "state": state.value,
            "authority": authority.value,
            "priority": priority,
            "applied_speed": ev.applied_speed_mps,
            "v_safe": ev.v_safe_mps,
            "reason": reason
        })
        return ev
