"""
FOG-ORCHESTRATOR 2.0 — Command Gateway (P5).

    HMI / orchestration
            |
            v
    CommandGateway.submit()      <- validation, dedup, ordering, safety-state dependency
            |
            v
    integration_adapters/*       <- EXISTING transport + scaling + ACK correlation
            |
            v
    vehicle (ESP32 / hardware_emulator)
            |
            v
    local Tier-1 governor clamps, then ACKs

AUTHORITY HIERARCHY (unchanged by this module)
  1. Local Tier-1 vehicle safety governor      <- final authority, always
  2. fog_safe safety calculations              <- the only safe-speed solver
  3. This gateway                              <- validation / transport protection ONLY
  4. Operator / HMI                            <- advisory

This gateway NEVER computes a safe speed and NEVER overrides a local safety stop. It
reads the authoritative `v_safe_mps` already in the Twin and refuses anything that
contradicts it. When safety state is unusable it FAILS CLOSED.

TWO DISTINCT TIMEOUTS - deliberately not merged
  gateway validity window   `max_recommendation_age_seconds` = 5.0 s
                            (config/integration_config.json)
                            How long a command may sit before the gateway refuses it.

  ACK timeout               `command_ack_timeout_seconds` = 3.0 s
                            (config/integration_config.json)
                            How long the gateway waits for a vehicle ACK before recording
                            TIMEOUT.

  firmware watchdog         `COMMAND_TIMEOUT_MS` = 15000 ms
                            (esp32_code/VEHICLE_B_TRUCK_02_V2V_DIGITAL_TWIN_MOTOR/...ino:155
                             "Stop if twin disappears.")
                            The PHYSICAL fail-safe: no valid command within that window and
                            the vehicle stops itself. Untouched by this module and never
                            reinterpreted here.

COMMAND LIFECYCLE
    submit()            -> ACCEPTED       gateway validated it; nothing has moved yet
    mark_transmitted()  -> TRANSMITTED    handed to a transport
    record_ack()        -> ACKNOWLEDGED / EXECUTED / REJECTED
    expire_pending()    -> TIMEOUT        no ACK within command_ack_timeout_seconds

  ACCEPTED is never reported as EXECUTED. Acceptance of an HTTP request is not evidence
  that a vehicle did anything.

CLOCK DOMAIN
  Command freshness is a WALL_CLOCK concern (P4.1). A command timestamp is never compared
  against simulation time.
"""

from __future__ import annotations

import json
import logging
import math
import os
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

logger = logging.getLogger("CommandGateway")

# P9: one loader for the project's timing thresholds. This module used to carry its own
# copy of the path and the defaults; both now live in `integration_adapters.config_paths`
# so a tuned threshold cannot apply to the gateway but not to the backend.
from integration_adapters.config_paths import load_timeouts as _load_timeouts


class CommandStatus:
    """Explicit result states. Only states supported by evidence are ever reported."""

    ACCEPTED = "ACCEPTED"              # gateway validated it; NOT yet sent, NOT executed
    TRANSMITTED = "TRANSMITTED"        # handed to a transport
    ACKNOWLEDGED = "ACKNOWLEDGED"      # vehicle replied
    EXECUTED = "EXECUTED"              # vehicle confirmed it applied the requested target
    REJECTED = "REJECTED"
    DUPLICATE = "DUPLICATE"
    STALE = "STALE"
    UNKNOWN_VEHICLE = "UNKNOWN_VEHICLE"
    INVALID = "INVALID"
    TIMEOUT = "TIMEOUT"
    SUPERSEDED = "SUPERSEDED"          # an older command arrived after a newer one


class CommandSource:
    OPERATOR = "OPERATOR"
    DISPATCH = "DISPATCH"
    SAFETY = "SAFETY"
    SIMULATION = "SIMULATION"
    TEST = "TEST"

    ALL = frozenset({OPERATOR, DISPATCH, SAFETY, SIMULATION, TEST})


# Actions that reduce speed. Always permissible, even when safety state is unusable:
# refusing a STOP because the Twin is stale would be the dangerous failure.
DEFENSIVE_ACTIONS = frozenset({"STOP", "HOLD"})
VALID_ACTIONS = frozenset({"TARGET_SPEED", "HOLD", "STOP", "RELEASE"})


@dataclass
class VehicleCommand:
    """Canonical normalized command. SI units throughout (m/s, seconds)."""

    vehicle_id: str
    command_id: str
    created_at: float                       # WALL_CLOCK epoch seconds
    action: str = "TARGET_SPEED"
    target_speed_mps: float = 0.0
    source: str = CommandSource.OPERATOR
    reason: str = ""
    expires_at: Optional[float] = None      # None => gateway validity window applies
    mode: str = "SIMULATION"                # SIMULATION | HARDWARE - provenance of the command
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def is_defensive(self) -> bool:
        return str(self.action).upper() in DEFENSIVE_ACTIONS

    def identity(self) -> tuple:
        """What makes two submissions 'the same command' for conflict detection."""
        return (self.vehicle_id, str(self.action).upper(), round(float(self.target_speed_mps), 6))


@dataclass
class CommandResult:
    status: str
    command_id: Optional[str] = None
    vehicle_id: Optional[str] = None
    reason: str = ""
    v_safe_mps: Optional[float] = None
    accepted_at: Optional[float] = None

    @property
    def accepted(self) -> bool:
        return self.status == CommandStatus.ACCEPTED

    def __bool__(self) -> bool:
        return self.accepted


class CommandGateway:
    """
    Validation and transport protection for the command path.

    Deliberately NOT a controller: it computes no speed, holds no physics, and writes no
    vehicle telemetry. It decides only whether a command may proceed.
    """

    def __init__(
        self,
        store=None,
        id_mapper=None,
        clock=time.time,
        validity_window_s: Optional[float] = None,
        ack_timeout_s: Optional[float] = None,
        safety_stale_after_s: Optional[float] = None,
    ):
        from integration_adapters.vehicle_id_mapper import VehicleIDMapper

        timeouts = _load_timeouts()
        self.store = store
        self.id_mapper = id_mapper if id_mapper is not None else VehicleIDMapper()
        self.clock = clock
        # Gateway validity window - how long a command may sit before we refuse it.
        self.validity_window_s = (
            timeouts["max_recommendation_age_seconds"] if validity_window_s is None else validity_window_s
        )
        # ACK timeout - distinct from the firmware watchdog (see module docstring).
        self.ack_timeout_s = (
            timeouts["command_ack_timeout_seconds"] if ack_timeout_s is None else ack_timeout_s
        )
        # Configured `max_telemetry_age_seconds`, not a literal: the age at which the
        # gateway stops trusting the Twin's v_safe is the same age at which the Twin
        # itself calls a field stale.
        self.safety_stale_after_s = (
            timeouts["max_telemetry_age_seconds"] if safety_stale_after_s is None
            else float(safety_stale_after_s)
        )

        # `check duplicate + register` must be atomic (P5 section 15).
        self._lock = threading.RLock()
        self._commands: Dict[str, Dict[str, Any]] = {}
        self._latest_accepted_at: Dict[str, float] = {}
        self.stats = {
            "accepted": 0, "rejected": 0, "duplicate": 0, "stale": 0,
            "unknown_vehicle": 0, "invalid": 0, "unsafe": 0, "timeout": 0,
        }

    def _reject(self, bucket: str) -> None:
        """
        Record one refusal.

        `rejected` is the TOTAL of every refusal, and each bucket says why. Before P9 the
        specific buckets were incremented but `rejected` never was, so an operator reading
        `rejected: 0` would have concluded no command had ever been refused while the
        gateway was in fact failing closed on every one of them.

        `timeout` is deliberately NOT counted here: a timed-out command was ACCEPTED and
        then went unacknowledged, which is a different failure from a refusal at the gate.
        """
        with self._lock:
            self.stats[bucket] += 1
            self.stats["rejected"] += 1

    # -- submission ----------------------------------------------------

    def submit(self, command: VehicleCommand) -> CommandResult:
        """
        Validate and register one command. Nothing is transmitted and no vehicle state is
        touched here - acceptance means only that the command may proceed.
        """
        now = float(self.clock())

        structural = self._validate_structure(command, now)
        if structural is not None:
            return structural

        with self._lock:
            # --- duplicate / conflict detection and registration, atomically ---
            existing = self._commands.get(command.command_id)
            if existing is not None:
                same = existing["identity"] == command.identity()
                self._reject("duplicate")
                logger.info(
                    "command %s duplicate (%s)", command.command_id,
                    "identical - idempotent" if same else "CONFLICTING payload",
                )
                return CommandResult(
                    CommandStatus.DUPLICATE, command.command_id, command.vehicle_id,
                    "Idempotent replay of an already-accepted command" if same
                    else "command_id reused with a different payload",
                )

            # --- ordering: an older command must not override a newer accepted one ---
            latest = self._latest_accepted_at.get(command.vehicle_id)
            if latest is not None and command.created_at < latest:
                self._reject("stale")
                return CommandResult(
                    CommandStatus.SUPERSEDED, command.command_id, command.vehicle_id,
                    f"created_at {command.created_at} precedes accepted command at {latest}",
                )

            # --- safety-state dependency (fail closed) ---
            safety = self._check_against_safety(command, now)
            if safety is not None:
                return safety

            self._commands[command.command_id] = {
                "command": command,
                "identity": command.identity(),
                "status": CommandStatus.ACCEPTED,
                "accepted_at": now,
                "transmitted_at": None,
                "acked_at": None,
                "applied_speed_mps": None,
                "ack_status": None,
            }
            self._latest_accepted_at[command.vehicle_id] = command.created_at
            self.stats["accepted"] += 1

        logger.info(
            "command accepted: id=%s vehicle=%s action=%s target=%.3f m/s source=%s mode=%s",
            command.command_id, command.vehicle_id, str(command.action).upper(),
            float(command.target_speed_mps), command.source, command.mode,
        )
        return CommandResult(
            CommandStatus.ACCEPTED, command.command_id, command.vehicle_id,
            "Validated by gateway; not yet transmitted", accepted_at=now,
        )

    def _validate_structure(self, c: VehicleCommand, now: float) -> Optional[CommandResult]:
        """Structural / value / freshness validation. Returns a result on failure."""
        if not isinstance(c.command_id, str) or not c.command_id.strip():
            self._reject("invalid")
            return CommandResult(CommandStatus.INVALID, None, c.vehicle_id, "missing or non-string command_id")

        if not isinstance(c.vehicle_id, str) or not c.vehicle_id.strip():
            self._reject("invalid")
            return CommandResult(CommandStatus.INVALID, c.command_id, None, "missing or non-string vehicle_id")

        if str(c.action).upper() not in VALID_ACTIONS:
            self._reject("invalid")
            return CommandResult(CommandStatus.INVALID, c.command_id, c.vehicle_id,
                                 f"unsupported action '{c.action}'")

        if c.source not in CommandSource.ALL:
            self._reject("invalid")
            return CommandResult(CommandStatus.INVALID, c.command_id, c.vehicle_id,
                                 f"unsupported source '{c.source}'")

        # Unknown vehicles are rejected BEFORE anything else happens. A command never
        # registers a vehicle and never mutates Twin state.
        if not self.id_mapper.is_mapped_physical(c.vehicle_id):
            self._reject("unknown_vehicle")
            logger.warning("command %s rejected: unknown vehicle %s", c.command_id, c.vehicle_id)
            return CommandResult(CommandStatus.UNKNOWN_VEHICLE, c.command_id, c.vehicle_id,
                                 "vehicle is not a known physical vehicle")

        speed = c.target_speed_mps
        if speed is None or isinstance(speed, bool) or not isinstance(speed, (int, float)):
            self._reject("invalid")
            return CommandResult(CommandStatus.INVALID, c.command_id, c.vehicle_id,
                                 "target_speed_mps is not a number")
        if not math.isfinite(float(speed)):
            self._reject("invalid")
            return CommandResult(CommandStatus.INVALID, c.command_id, c.vehicle_id,
                                 "target_speed_mps is NaN or infinite")
        if float(speed) < 0.0:
            # No existing project protocol defines reverse via a negative target speed.
            self._reject("invalid")
            return CommandResult(CommandStatus.INVALID, c.command_id, c.vehicle_id,
                                 "negative target_speed_mps is not defined by this protocol")

        # --- freshness: WALL_CLOCK only, never simulation time ---
        if (c.created_at is None or isinstance(c.created_at, bool)
                or not isinstance(c.created_at, (int, float))
                or not math.isfinite(float(c.created_at)) or float(c.created_at) < 0):
            self._reject("invalid")
            return CommandResult(CommandStatus.INVALID, c.command_id, c.vehicle_id,
                                 "malformed created_at")

        if float(c.created_at) > now + 1.0:          # same 1 s skew allowance as TimeAdapter
            self._reject("invalid")
            return CommandResult(CommandStatus.INVALID, c.command_id, c.vehicle_id,
                                 "created_at is in the future")

        deadline = c.expires_at if c.expires_at is not None else float(c.created_at) + self.validity_window_s
        if now > deadline:
            self._reject("stale")
            logger.info("command %s stale: age %.3fs", c.command_id, now - float(c.created_at))
            return CommandResult(CommandStatus.STALE, c.command_id, c.vehicle_id,
                                 f"expired at {deadline}; now {now}")
        return None

    def _check_against_safety(self, c: VehicleCommand, now: float) -> Optional[CommandResult]:
        """
        Validate the already-computed target against the authoritative safety state.

        NO safe speed is computed here. The gateway only reads `v_safe_mps` that fog_safe
        already produced and the Twin already holds.

        Fails closed: unusable safety state means a speed-increasing command is refused.
        Defensive actions (STOP / HOLD) are always permitted.
        """
        if c.is_defensive:
            return None                       # a STOP is never blocked by missing state

        if self.store is None:
            self._reject("unsafe")
            return CommandResult(CommandStatus.REJECTED, c.command_id, c.vehicle_id,
                                 "no Twin available to validate against (fail closed)")

        vehicle = self.store.get_vehicle(c.vehicle_id)
        if vehicle is None:
            self._reject("unsafe")
            return CommandResult(CommandStatus.REJECTED, c.command_id, c.vehicle_id,
                                 "vehicle not present in Twin (fail closed)")

        v_safe = vehicle.get("v_safe_mps")
        if not v_safe.is_available:
            self._reject("unsafe")
            return CommandResult(CommandStatus.REJECTED, c.command_id, c.vehicle_id,
                                 "v_safe unavailable (fail closed)")

        # Freshness in the field's OWN clock domain (P4.1). A simulation timestamp is
        # never compared to wall-clock now.
        reference = self.store.now_by_domain().get(v_safe.clock_domain)
        if not v_safe.is_current(reference, self.safety_stale_after_s, v_safe.clock_domain):
            self._reject("unsafe")
            return CommandResult(CommandStatus.REJECTED, c.command_id, c.vehicle_id,
                                 "v_safe is stale or invalid (fail closed)",
                                 v_safe_mps=float(v_safe.value))

        if float(c.target_speed_mps) > float(v_safe.value) + 1e-9:
            self._reject("unsafe")
            logger.warning(
                "command %s rejected: target %.3f exceeds v_safe %.3f",
                c.command_id, float(c.target_speed_mps), float(v_safe.value),
            )
            return CommandResult(
                CommandStatus.REJECTED, c.command_id, c.vehicle_id,
                "target_speed exceeds authoritative v_safe", v_safe_mps=float(v_safe.value),
            )
        return None

    # -- lifecycle -----------------------------------------------------

    def mark_transmitted(self, command_id: str) -> bool:
        """Record that an accepted command was handed to a transport."""
        with self._lock:
            record = self._commands.get(command_id)
            if record is None or record["status"] != CommandStatus.ACCEPTED:
                return False
            record["status"] = CommandStatus.TRANSMITTED
            record["transmitted_at"] = float(self.clock())
            return True

    def record_ack(self, command_id: str, ack_status: str,
                   applied_speed_mps: Optional[float] = None) -> CommandResult:
        """
        Record a vehicle acknowledgement.

        EXECUTED is claimed only when the vehicle reports it applied the requested target.
        A CLAMPED ACK is ACKNOWLEDGED, not EXECUTED - the vehicle's local governor chose a
        different (lower) speed, which is its right and its authority.
        """
        with self._lock:
            record = self._commands.get(command_id)
            if record is None:
                return CommandResult(CommandStatus.REJECTED, command_id, None,
                                     "ACK for an unknown command_id")

            command: VehicleCommand = record["command"]
            now = float(self.clock())
            record["acked_at"] = now
            record["ack_status"] = str(ack_status).upper()
            record["applied_speed_mps"] = applied_speed_mps

            if record["ack_status"] == "REJECTED":
                status = CommandStatus.REJECTED
            elif (
                applied_speed_mps is not None
                and abs(float(applied_speed_mps) - float(command.target_speed_mps)) <= 1e-6
            ):
                status = CommandStatus.EXECUTED
            else:
                status = CommandStatus.ACKNOWLEDGED

            record["status"] = status
            return CommandResult(status, command_id, command.vehicle_id,
                                 f"vehicle ACK: {record['ack_status']}")

    def expire_pending(self, now: Optional[float] = None) -> list:
        """
        Mark commands transmitted but never acknowledged within
        `command_ack_timeout_seconds` as TIMEOUT.

        This is the GATEWAY's ACK timeout. It is not the firmware watchdog, which remains
        the vehicle's own final fail-safe and is not reinterpreted here.
        """
        t = float(self.clock()) if now is None else float(now)
        timed_out = []
        with self._lock:
            for command_id, record in self._commands.items():
                if record["status"] != CommandStatus.TRANSMITTED:
                    continue
                sent = record["transmitted_at"]
                if sent is not None and (t - sent) > self.ack_timeout_s:
                    record["status"] = CommandStatus.TIMEOUT
                    timed_out.append(command_id)
                    self.stats["timeout"] += 1
        for command_id in timed_out:
            logger.warning("command %s timed out awaiting ACK", command_id)
        return timed_out

    # -- queries -------------------------------------------------------

    def get_status(self, command_id: str) -> Optional[str]:
        with self._lock:
            record = self._commands.get(command_id)
            return None if record is None else record["status"]

    def get_command(self, command_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            record = self._commands.get(command_id)
            return None if record is None else dict(record)

    def history(self) -> list:
        with self._lock:
            return [
                {
                    "command_id": cid,
                    "vehicle_id": r["command"].vehicle_id,
                    "action": str(r["command"].action).upper(),
                    "target_speed_mps": r["command"].target_speed_mps,
                    "source": r["command"].source,
                    "mode": r["command"].mode,
                    "status": r["status"],
                    "created_at": r["command"].created_at,
                    "accepted_at": r["accepted_at"],
                    "transmitted_at": r["transmitted_at"],
                    "acked_at": r["acked_at"],
                    "applied_speed_mps": r["applied_speed_mps"],
                }
                for cid, r in self._commands.items()
            ]
