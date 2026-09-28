"""
failsafe/safe_beacon.py
-----------------------
FOG-ORCHESTRATOR 2.0 — Canonical Safe Beacon Failsafe Architecture.
SIH 2026-27 | Problem Statement: SIH26007

FROZEN PROTOCOL PAYLOAD:
    BEACON,<vehicle_id>,<sequence>,<state>,<timestamp>,<zone_id>

PURPOSE & ARCHITECTURAL SCOPE:
    1. Autonomous announcement of vehicle safety state when central comms fail.
    2. Over-the-air peer vehicle situational awareness in dense fog.
    3. Standalone failsafe authority: During communication loss, NO REMOTE
       COMMAND IS ACCEPTED.
    4. Deterministic local safety governor retains ultimate operational authority.
    5. Safe Beacon is NOT a replacement for physical braking; it provides
       peer awareness and deterministic recovery coordination.
"""

from __future__ import annotations

import logging
import math
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple

from integration_adapters.safe_beacon_adapter import (
    BeaconState,
    BeaconSystemState,
    SafeBeaconMessage as AdapterSafeBeaconMessage,
    SafeBeaconAdapter,
    DenseFogDebounceFilter,
    PeerVehicleTracking,
)
from integration_adapters.fail_safe_controller import (
    LocalVehicleSafetyGovernor,
    FailSafeState,
    CommandAction,
    IncomingCommand,
)

logger = logging.getLogger("SafeBeaconFailsafe")


class SafeBeaconState(str, Enum):
    NORMAL = "NORMAL"
    DEGRADED = "DEGRADED"
    STOP = "STOP"
    EMERGENCY = "EMERGENCY"


class SafeBeaconSystemState(str, Enum):
    NORMAL = "NORMAL"
    DEGRADED = "DEGRADED"
    STOP = "STOP"
    EMERGENCY = "EMERGENCY"
    COMM_LOSS = "COMM_LOSS"


@dataclass
class SafeBeaconMessage:
    """Parsed and validated Safe Beacon frame."""
    vehicle_id: str
    sequence: int
    state: SafeBeaconState
    timestamp: float
    zone_id: str
    raw_packet: str = ""
    received_at: float = field(default_factory=time.time)


def format_safe_beacon(
    vehicle_id: str,
    sequence: int,
    state: SafeBeaconState,
    timestamp: float,
    zone_id: str
) -> str:
    """Formats canonical Safe Beacon ASCII packet."""
    state_str = state.value if isinstance(state, SafeBeaconState) else str(state)
    return f"BEACON,{vehicle_id},{sequence},{state_str},{timestamp:.3f},{zone_id}"


def parse_safe_beacon(raw_packet: str, max_age_s: float = 2.0, clock: Callable[[], float] = time.time) -> Tuple[bool, Optional[SafeBeaconMessage], str]:
    """
    Parses and validates incoming Safe Beacon ASCII packet.
    Returns (valid: bool, message: Optional[SafeBeaconMessage], error_code: str).
    """
    if not raw_packet or not isinstance(raw_packet, str):
        return False, None, "EMPTY_PACKET"

    parts = raw_packet.strip().split(",")
    if len(parts) != 6 or parts[0] != "BEACON":
        return False, None, "MALFORMED_HEADER"

    vehicle_id = parts[1].strip()
    if not vehicle_id:
        return False, None, "MISSING_VEHICLE_ID"

    try:
        sequence = int(parts[2].strip())
    except ValueError:
        return False, None, "INVALID_SEQUENCE"

    state_token = parts[3].strip().upper()
    try:
        state = SafeBeaconState(state_token)
    except ValueError:
        return False, None, "UNKNOWN_STATE"

    try:
        ts = float(parts[4].strip())
    except ValueError:
        return False, None, "INVALID_TIMESTAMP"

    zone_id = parts[5].strip()
    if not zone_id:
        return False, None, "MISSING_ZONE_ID"

    now = clock()
    if math.isnan(ts) or math.isinf(ts):
        return False, None, "NON_FINITE_TIMESTAMP"

    if (now - ts) > max_age_s:
        return False, None, "STALE_TIMESTAMP"

    if (ts - now) > 5.0:  # More than 5s in future
        return False, None, "FUTURE_TIMESTAMP"

    msg = SafeBeaconMessage(
        vehicle_id=vehicle_id,
        sequence=sequence,
        state=state,
        timestamp=ts,
        zone_id=zone_id,
        raw_packet=raw_packet,
        received_at=now
    )
    return True, msg, "OK"


class SafeBeaconController:
    """
    Standalone Vehicle Failsafe & Safe Beacon Manager.
    Ties together local safety state, peer beacon awareness, and autonomous governing.
    """

    def __init__(
        self,
        vehicle_id: str = "TRUCK_01",
        default_zone_id: str = "ZONE_RAMP_D5",
        comm_timeout_s: float = 1.0,
        clock: Callable[[], float] = time.time,
        governor: Optional[LocalVehicleSafetyGovernor] = None
    ):
        self.vehicle_id = vehicle_id
        self.default_zone_id = default_zone_id
        self.comm_timeout_s = comm_timeout_s
        self.clock = clock

        # Underlying adapter and governor
        self.adapter = SafeBeaconAdapter(local_vehicle_id=vehicle_id, clock=clock)
        self.governor = governor or LocalVehicleSafetyGovernor(
            vehicle_id=vehicle_id,
            clock=clock
        )
        self.debounce = DenseFogDebounceFilter()

        # State tracking
        self.sequence: int = 0
        self.system_state: SafeBeaconSystemState = SafeBeaconSystemState.NORMAL
        self.last_central_comm_time: float = clock()
        self.is_standalone_active: bool = False

    def notify_central_comm_received(self, timestamp: Optional[float] = None):
        """Notifies the controller that a valid central orchestrator packet was received."""
        self.last_central_comm_time = timestamp if timestamp is not None else self.clock()
        if self.is_standalone_active:
            logger.info(f"{self.vehicle_id}: Central communication restored. Recovering from Standalone Failsafe.")
            self.is_standalone_active = False
            self.system_state = SafeBeaconSystemState.NORMAL

    def check_comm_timeout(self, now: Optional[float] = None) -> bool:
        """Evaluates whether central communication has timed out."""
        t_now = now if now is not None else self.clock()
        elapsed = t_now - self.last_central_comm_time
        if elapsed > self.comm_timeout_s:
            if not self.is_standalone_active:
                logger.warning(
                    f"{self.vehicle_id}: Central comm timeout ({elapsed:.2f}s > {self.comm_timeout_s}s). "
                    f"ACTIVATING STANDALONE SAFE BEACON FAILSAFE."
                )
            self.is_standalone_active = True
            self.system_state = SafeBeaconSystemState.COMM_LOSS
            return True
        return False

    def generate_beacon(self, now: Optional[float] = None) -> str:
        """Generates outgoing Safe Beacon packet."""
        t_now = now if now is not None else self.clock()
        self.sequence += 1

        # Map internal system state to 4-state over-the-air BeaconState
        if self.system_state == SafeBeaconSystemState.EMERGENCY:
            beacon_state = SafeBeaconState.EMERGENCY
        elif self.system_state in [SafeBeaconSystemState.COMM_LOSS, SafeBeaconSystemState.DEGRADED]:
            beacon_state = SafeBeaconState.DEGRADED
        elif self.system_state == SafeBeaconSystemState.STOP:
            beacon_state = SafeBeaconState.STOP
        else:
            beacon_state = SafeBeaconState.NORMAL

        return format_safe_beacon(
            vehicle_id=self.vehicle_id,
            sequence=self.sequence,
            state=beacon_state,
            timestamp=t_now,
            zone_id=self.default_zone_id
        )

    def compute_local_safe_speed(
        self,
        visibility_m: float,
        grade_pct: float = -8.0,
        tau_s: float = 0.80,
        a_dec: float = 2.7856,
        s_base: float = 5.0
    ) -> float:
        """
        Computes local kinematic safe stopping speed:
        v_safe = (-tau + sqrt(tau^2 + 2 * (R_vis - S_base) / a_dec)) * a_dec
        Clamped to 0.0 at R_vis <= S_base (5.0m).
        """
        is_staged, filtered_r = self.debounce.update(visibility_m)
        if is_staged or filtered_r <= s_base:
            return 0.0

        available_dist = filtered_r - s_base
        # Solving v * tau + v^2 / (2 * a_dec) = available_dist
        # Quadratic formula: (1/(2*a_dec)) * v^2 + tau * v - available_dist = 0
        discriminant = (tau_s ** 2) + 2.0 * available_dist / a_dec
        if discriminant <= 0:
            return 0.0
        v_root = (-tau_s + math.sqrt(discriminant)) * a_dec
        return max(0.0, min(11.11, float(v_root)))

    def evaluate_command_authority(
        self,
        command: Optional[IncomingCommand],
        local_visibility_m: float = 12.0,
        local_grade_pct: float = -8.0,
        now: Optional[float] = None
    ) -> Tuple[float, CommandAction, str]:
        """
        Enforces command authority invariants (I1, I2, I4).
        If central comms are lost or standalone mode is active, REMOTE COMMANDS ARE REJECTED.
        The Local Safety Governor computes local safe speed.
        """
        t_now = now if now is not None else self.clock()
        self.check_comm_timeout(now=t_now)

        local_v_safe = self.compute_local_safe_speed(
            visibility_m=local_visibility_m,
            grade_pct=local_grade_pct
        )

        # Update underlying governor with local physics state
        self.governor.update_local_safety_state(
            v_safe=local_v_safe,
            has_gateway=(not self.is_standalone_active),
            has_v2v=True
        )

        # Invariant I2: During communication loss, NO REMOTE COMMAND IS ACCEPTED
        if self.is_standalone_active or self.system_state == SafeBeaconSystemState.COMM_LOSS:
            reason = "COMM_LOSS_STANDALONE_LOCAL_GOVERNOR_AUTHORITY"
            if command is not None:
                reason += f" (REJECTED_REMOTE_CMD_SEQ_{command.sequence})"
            return local_v_safe, CommandAction.REJECT, reason

        # Normal operation: process through local governor
        if command is None:
            return local_v_safe, CommandAction.ACCEPT, "NOMINAL_NO_REMOTE_COMMAND"

        decision = self.governor.process_command(
            cmd=command,
            now=t_now
        )
        return decision.applied_speed, decision.action, decision.reason
