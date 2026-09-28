"""
integration_adapters/fail_safe_controller.py
--------------------------------------------
FOG-ORCHESTRATOR 2.0 — Local Vehicle Safety Governor & Fail-Safe Controller.

AUTHORITY HIERARCHY (PART 19):
  LEVEL 0: Emergency / Local Physical Safety (Firmware Watchdog & E-Stop)
  LEVEL 1: Local HEMM Safety Governor (THIS MODULE — Ultimate Operational Authority)
  LEVEL 2: Vehicle Command Validation & Ingestion
  LEVEL 3: Central FOG-Orchestrator Intelligence Engine
  LEVEL 4: Fleet Optimization & Slot Reservation
  LEVEL 5: Predictive 3D Digital Twin

CORE SAFETY INVARIANT (I1 / I6):
  v_applied <= v_safe
  Higher levels may only RECOMMEND. The Local Vehicle Safety Governor can CLAMP or REJECT.
  Nothing above Level 1 may directly force a vehicle actuator state.
"""

from __future__ import annotations

import logging
import math
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, Optional, Tuple

logger = logging.getLogger("FailSafeController")


class FailSafeState(str, Enum):
    NORMAL = "NORMAL"
    DEGRADED_COMMUNICATION = "DEGRADED_COMMUNICATION"
    STALE_COMMAND = "STALE_COMMAND"
    NO_GATEWAY = "NO_GATEWAY"
    INVALID_COMMAND = "INVALID_COMMAND"
    UNSAFE_COMMAND = "UNSAFE_COMMAND"
    STOP = "STOP"
    EMERGENCY_STOP = "EMERGENCY_STOP"
    RECOVERY = "RECOVERY"


class CommandAction(str, Enum):
    ACCEPT = "ACCEPT"
    CLAMP = "CLAMP"
    REJECT = "REJECT"


@dataclass
class IncomingCommand:
    """Standard incoming vehicle dispatch / guidance command."""
    vehicle_id: str
    sequence: int
    timestamp: float                       # Wall clock epoch seconds
    requested_speed_mps: float
    action: str = "TARGET_SPEED"           # TARGET_SPEED, HOLD, STOP, EMERGENCY_STOP
    command_source: str = "CENTRAL"        # CENTRAL, DISPATCH, OPERATOR, LOCAL
    reason: str = ""


@dataclass
class GovernorDecision:
    """Result of command processing through the local safety governor."""
    vehicle_id: str
    applied_speed: float
    action: CommandAction
    state: FailSafeState
    v_safe: float
    requested_speed: float
    sequence: int
    reason: str
    timestamp: float


class LocalVehicleSafetyGovernor:
    """
    Onboard vehicle safety governor running on vehicle ECU / ESP32.
    Evaluates incoming central commands against local safety invariants.
    """

    def __init__(
        self,
        vehicle_id: str = "TRUCK_01",
        v_safe_default: float = 4.3815,
        max_command_age_s: float = 1.0,
        firmware_watchdog_timeout_s: float = 1.0,
        clock: Callable[[], float] = time.time,
        has_v2v: bool = True,
        beacon_adapter: Optional[Any] = None
    ):
        self.vehicle_id = vehicle_id
        self.v_safe: float = v_safe_default
        self.max_command_age_s = max_command_age_s
        self.firmware_watchdog_timeout_s = firmware_watchdog_timeout_s
        self.clock = clock

        # State tracking
        self.last_valid_command_time: float = 0.0
        self.last_valid_sequence: int = 0
        self.has_gateway: bool = True
        self.has_v2v: bool = has_v2v
        self.beacon_adapter = beacon_adapter
        self.packet_loss_rate: float = 0.0
        self.in_recovery: bool = False
        self.recovery_observations: int = 0
        self.current_state: FailSafeState = FailSafeState.NORMAL
        self.emergency_stop_latched: bool = False

    def update_local_safety_state(
        self,
        v_safe: float,
        has_gateway: bool = True,
        has_v2v: bool = True,
        packet_loss_rate: float = 0.0,
        beacon_adapter: Optional[Any] = None
    ):
        """Updates local physical safety envelope from vehicle sensors / local solver."""
        if math.isnan(v_safe) or math.isinf(v_safe) or v_safe < 0:
            # Physical safety fault -> force zero safe speed
            self.v_safe = 0.0
        else:
            self.v_safe = float(v_safe)

        # Gateway power restoration detection: mandate validated sequence resync
        if not self.has_gateway and has_gateway:
            self.in_recovery = True
            self.recovery_observations = 0
            self.current_state = FailSafeState.RECOVERY

        self.has_gateway = has_gateway
        self.has_v2v = has_v2v
        if beacon_adapter is not None:
            self.beacon_adapter = beacon_adapter
        self.packet_loss_rate = max(0.0, min(1.0, float(packet_loss_rate)))

    def trigger_emergency_stop(self, reason: str = "MANUAL_ESTOP") -> GovernorDecision:
        """Latches emergency stop condition. Forces zero speed."""
        self.emergency_stop_latched = True
        self.current_state = FailSafeState.EMERGENCY_STOP
        now = self.clock()
        return GovernorDecision(
            vehicle_id=self.vehicle_id,
            applied_speed=0.0,
            action=CommandAction.REJECT,
            state=FailSafeState.EMERGENCY_STOP,
            v_safe=0.0,
            requested_speed=0.0,
            sequence=self.last_valid_sequence,
            reason=f"Emergency stop activated: {reason}",
            timestamp=now
        )

    def reset_emergency_stop(self):
        """Resets emergency stop latch and enters RECOVERY state."""
        self.emergency_stop_latched = False
        self.in_recovery = True
        self.recovery_observations = 0
        self.current_state = FailSafeState.RECOVERY

    def process_command(
        self,
        cmd: IncomingCommand,
        now: Optional[float] = None
    ) -> GovernorDecision:
        """
        Executes strict command validation and clamps/rejects according to
        local safety invariants (I1 to I11).
        """
        if now is None:
            now = self.clock()

        # 1. Check Latched Emergency Stop (Invariant I8)
        if self.emergency_stop_latched or cmd.action == "EMERGENCY_STOP":
            self.emergency_stop_latched = True
            self.current_state = FailSafeState.EMERGENCY_STOP
            return GovernorDecision(
                vehicle_id=self.vehicle_id,
                applied_speed=0.0,
                action=CommandAction.REJECT,
                state=FailSafeState.EMERGENCY_STOP,
                v_safe=self.v_safe,
                requested_speed=cmd.requested_speed_mps,
                sequence=cmd.sequence,
                reason="EMERGENCY_STOP: actuator forced to 0.0 m/s",
                timestamp=now
            )

        # 1.5 Check Peer Safe Beacon Situational Awareness (Level 2 -> Level 1)
        if self.beacon_adapter is not None:
            sys_state = getattr(self.beacon_adapter, "current_system_state", None)
            if sys_state is not None:
                state_val = sys_state.value if hasattr(sys_state, "value") else str(sys_state)
                if state_val == "EMERGENCY":
                    self.current_state = FailSafeState.EMERGENCY_STOP
                    return GovernorDecision(
                        vehicle_id=self.vehicle_id,
                        applied_speed=0.0,
                        action=CommandAction.REJECT,
                        state=FailSafeState.EMERGENCY_STOP,
                        v_safe=0.0,
                        requested_speed=cmd.requested_speed_mps,
                        sequence=cmd.sequence,
                        reason="Peer safety beacon EMERGENCY: forced to 0.0 m/s",
                        timestamp=now
                    )
                elif state_val == "STOP":
                    self.current_state = FailSafeState.STOP
                    return GovernorDecision(
                        vehicle_id=self.vehicle_id,
                        applied_speed=0.0,
                        action=CommandAction.CLAMP,
                        state=FailSafeState.STOP,
                        v_safe=0.0,
                        requested_speed=cmd.requested_speed_mps,
                        sequence=cmd.sequence,
                        reason="Peer safety beacon STOP: holding at 0.0 m/s",
                        timestamp=now
                    )

        # Transition out of STOP state (peer beacon STOP cleared and command is not STOP)
        if self.current_state == FailSafeState.STOP and not self.emergency_stop_latched and cmd.action != "STOP":
            self.in_recovery = True
            self.recovery_observations = 0
            self.current_state = FailSafeState.RECOVERY

        # 2. Check Vehicle Identity (FS-10)
        if cmd.vehicle_id != self.vehicle_id:
            return GovernorDecision(
                vehicle_id=self.vehicle_id,
                applied_speed=min(0.0, self.v_safe),
                action=CommandAction.REJECT,
                state=FailSafeState.INVALID_COMMAND,
                v_safe=self.v_safe,
                requested_speed=cmd.requested_speed_mps,
                sequence=cmd.sequence,
                reason=f"Vehicle ID mismatch: target {cmd.vehicle_id} != local {self.vehicle_id}",
                timestamp=now
            )

        # 3. Check Physical Numerical Validity (Invariant I10, I11, FS-11)
        if (
            math.isnan(cmd.requested_speed_mps)
            or math.isinf(cmd.requested_speed_mps)
            or cmd.requested_speed_mps < 0.0
        ):
            return GovernorDecision(
                vehicle_id=self.vehicle_id,
                applied_speed=0.0,
                action=CommandAction.REJECT,
                state=FailSafeState.INVALID_COMMAND,
                v_safe=self.v_safe,
                requested_speed=cmd.requested_speed_mps,
                sequence=cmd.sequence,
                reason="Corrupted speed value: negative, NaN, or Inf",
                timestamp=now
            )

        # 4. Check Sequence Order & Duplication (Invariant I3, I4, FS-04, FS-05)
        if self.last_valid_command_time > 0:
            if cmd.sequence == self.last_valid_sequence:
                if self.in_recovery:
                    self.recovery_observations = 0
                return GovernorDecision(
                    vehicle_id=self.vehicle_id,
                    applied_speed=min(self.v_safe, cmd.requested_speed_mps),
                    action=CommandAction.REJECT,
                    state=FailSafeState.INVALID_COMMAND,
                    v_safe=self.v_safe,
                    requested_speed=cmd.requested_speed_mps,
                    sequence=cmd.sequence,
                    reason=f"Duplicate command sequence: {cmd.sequence}",
                    timestamp=now
                )
            elif cmd.sequence < self.last_valid_sequence:
                if self.in_recovery:
                    self.recovery_observations = 0
                return GovernorDecision(
                    vehicle_id=self.vehicle_id,
                    applied_speed=min(self.v_safe, cmd.requested_speed_mps),
                    action=CommandAction.REJECT,
                    state=FailSafeState.INVALID_COMMAND,
                    v_safe=self.v_safe,
                    requested_speed=cmd.requested_speed_mps,
                    sequence=cmd.sequence,
                    reason=f"Out-of-order sequence: {cmd.sequence} < latest {self.last_valid_sequence}",
                    timestamp=now
                )

        # 5. Check Command Age / Stale Command (Invariant I2, FS-03)
        command_age = now - cmd.timestamp
        if command_age > self.max_command_age_s:
            return GovernorDecision(
                vehicle_id=self.vehicle_id,
                applied_speed=min(self.v_safe, cmd.requested_speed_mps),
                action=CommandAction.REJECT,
                state=FailSafeState.STALE_COMMAND,
                v_safe=self.v_safe,
                requested_speed=cmd.requested_speed_mps,
                sequence=cmd.sequence,
                reason=f"Stale command: age {command_age:.3f}s exceeds threshold {self.max_command_age_s}s",
                timestamp=now
            )

        # 6. Check Firmware Watchdog Timeout (FS-08, FS-09)
        if self.last_valid_command_time > 0:
            time_since_last = now - self.last_valid_command_time
            if time_since_last > self.firmware_watchdog_timeout_s:
                self.current_state = FailSafeState.EMERGENCY_STOP
                return GovernorDecision(
                    vehicle_id=self.vehicle_id,
                    applied_speed=0.0,
                    action=CommandAction.REJECT,
                    state=FailSafeState.EMERGENCY_STOP,
                    v_safe=self.v_safe,
                    requested_speed=cmd.requested_speed_mps,
                    sequence=cmd.sequence,
                    reason=f"Firmware watchdog expired: {time_since_last:.3f}s without valid command",
                    timestamp=now
                )

        # 7. Check Gateway and V2V Availability (Invariant I5, I10, I11, I12, FS-06)
        if not self.has_gateway:
            self.current_state = FailSafeState.NO_GATEWAY
            # Central commands rejected; maintain safe local speed limit
            applied = min(self.v_safe, cmd.requested_speed_mps)
            return GovernorDecision(
                vehicle_id=self.vehicle_id,
                applied_speed=applied,
                action=CommandAction.REJECT,
                state=FailSafeState.NO_GATEWAY,
                v_safe=self.v_safe,
                requested_speed=cmd.requested_speed_mps,
                sequence=cmd.sequence,
                reason="No active gateway connection: central command rejected, local safety preserved",
                timestamp=now
            )
        elif not self.has_v2v:
            self.current_state = FailSafeState.DEGRADED_COMMUNICATION
            # V2V peer loss: central command clamped to local safety envelope
            applied = min(self.v_safe, cmd.requested_speed_mps)
            return GovernorDecision(
                vehicle_id=self.vehicle_id,
                applied_speed=applied,
                action=CommandAction.CLAMP if cmd.requested_speed_mps > self.v_safe else CommandAction.ACCEPT,
                state=FailSafeState.DEGRADED_COMMUNICATION,
                v_safe=self.v_safe,
                requested_speed=cmd.requested_speed_mps,
                sequence=cmd.sequence,
                reason="V2V communication lost: operating in degraded mode, local safety governor authoritative",
                timestamp=now
            )

        # 8. Check Recovery State (Invariant I9, FS-13)
        if self.in_recovery:
            self.recovery_observations += 1
            if self.recovery_observations < 2:
                # Require at least 2 valid consecutive command frames to exit recovery
                self.last_valid_command_time = now
                self.last_valid_sequence = cmd.sequence
                applied = min(self.v_safe, cmd.requested_speed_mps)
                return GovernorDecision(
                    vehicle_id=self.vehicle_id,
                    applied_speed=applied,
                    action=CommandAction.REJECT,
                    state=FailSafeState.RECOVERY,
                    v_safe=self.v_safe,
                    requested_speed=cmd.requested_speed_mps,
                    sequence=cmd.sequence,
                    reason="Recovery state: re-synchronizing sequence stream before actuation resume",
                    timestamp=now
                )
            else:
                self.in_recovery = False

        # 9. Evaluate Speed against Local Safe Envelope (Invariant I1, I7, FS-01, FS-02, FS-14, FS-15, FS-16)
        self.last_valid_command_time = now
        self.last_valid_sequence = cmd.sequence

        if cmd.action == "STOP":
            self.current_state = FailSafeState.STOP
            return GovernorDecision(
                vehicle_id=self.vehicle_id,
                applied_speed=0.0,
                action=CommandAction.ACCEPT,
                state=FailSafeState.STOP,
                v_safe=self.v_safe,
                requested_speed=cmd.requested_speed_mps,
                sequence=cmd.sequence,
                reason="Defensive action applied: STOP",
                timestamp=now
            )
        elif cmd.action == "HOLD":
            self.current_state = FailSafeState.NORMAL
            return GovernorDecision(
                vehicle_id=self.vehicle_id,
                applied_speed=0.0,
                action=CommandAction.ACCEPT,
                state=FailSafeState.NORMAL,
                v_safe=self.v_safe,
                requested_speed=cmd.requested_speed_mps,
                sequence=cmd.sequence,
                reason="Defensive action applied: HOLD",
                timestamp=now
            )

        # Determine if communication is degraded (e.g. high packet loss >= 25%)
        is_degraded = self.packet_loss_rate >= 0.25

        if cmd.requested_speed_mps > self.v_safe:
            # Over-speed command -> CLAMP to local v_safe (Invariant I1, I7)
            applied = self.v_safe
            action = CommandAction.CLAMP
            state = FailSafeState.DEGRADED_COMMUNICATION if is_degraded else FailSafeState.UNSAFE_COMMAND
            reason = f"Command {cmd.requested_speed_mps:.2f} m/s clamped to safe limit {self.v_safe:.2f} m/s"
        else:
            # Safe speed command -> ACCEPT
            applied = cmd.requested_speed_mps
            action = CommandAction.ACCEPT
            state = FailSafeState.DEGRADED_COMMUNICATION if is_degraded else FailSafeState.NORMAL
            reason = "Command within local safe envelope"

        self.current_state = state
        return GovernorDecision(
            vehicle_id=self.vehicle_id,
            applied_speed=applied,
            action=action,
            state=state,
            v_safe=self.v_safe,
            requested_speed=cmd.requested_speed_mps,
            sequence=cmd.sequence,
            reason=reason,
            timestamp=now
        )
