"""
integration_adapters/safe_beacon_adapter.py
--------------------------------------------
FOG-ORCHESTRATOR 2.0 — Safe Beacon Protocol Adapter & State Machine.

FROZEN PROTOCOL PAYLOAD:
    BEACON,<vehicle_id>,<sequence>,<state>,<timestamp>,<zone_id>

Allowed States:
    NORMAL, DEGRADED, STOP, EMERGENCY

Candidate State Machine States:
    NORMAL, DEGRADED, STOP, EMERGENCY, COMM_LOSS

BOUNDARY ARCHITECTURE:
    Beacon Received
          ↓
    Local Safety Awareness
          ↓
    Local Safety Governor
          ↓
        v_safe
          ↓
      v_command
          ↓
       Actuator

CRITICAL INVARIANTS:
    1. Beacon does NOT directly command actuators.
    2. "No beacon" ≠ "vehicle disappeared" (timeout degrades confidence, never accelerates).
    3. Replay of old NORMAL packet cannot overwrite STOP/EMERGENCY.
    4. Deterministic Schmitt-trigger debounce around 5.0 m dense-fog boundary.
"""

from __future__ import annotations

import logging
import math
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

logger = logging.getLogger("SafeBeaconAdapter")


class BeaconState(str, Enum):
    NORMAL = "NORMAL"
    DEGRADED = "DEGRADED"
    STOP = "STOP"
    EMERGENCY = "EMERGENCY"


class BeaconSystemState(str, Enum):
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
    state: BeaconState
    timestamp: float
    zone_id: str
    raw_packet: str = ""
    received_at: float = field(default_factory=time.time)


@dataclass
class BeaconParseResult:
    """Result of raw beacon packet ingestion."""
    accepted: bool
    beacon: Optional[SafeBeaconMessage] = None
    rejection_reason: str = ""
    error_code: str = "OK"  # OK, MALFORMED, UNKNOWN_VEHICLE, UNKNOWN_STATE, OUT_OF_ORDER, DUPLICATE, STALE, FUTURE_TIMESTAMP


@dataclass
class PeerVehicleTracking:
    """Tracks state and communication confidence of a peer vehicle."""
    vehicle_id: str
    last_sequence: int = 0
    last_timestamp: float = 0.0
    last_state: BeaconState = BeaconState.NORMAL
    last_zone_id: str = ""
    last_received_at: float = 0.0
    packets_received: int = 0
    is_stale: bool = False
    in_comm_loss: bool = False


class DenseFogDebounceFilter:
    """
    Deterministic Schmitt-trigger persistence filter for visibility around the 5.0 m blindout boundary.
    Prevents command chattering (0 <-> 0.21 m/s) when visibility fluctuates between 4.9 m and 5.1 m.

    Rule:
      - Enter STAGED (halt, v_safe = 0) immediately if R <= S_base (5.0 m).
      - Exit STAGED to MOVING only if R >= S_base + delta_R (5.2 m) AND visibility
        remains above threshold for N_consecutive observations (debounce count = 2).
    """

    def __init__(
        self,
        s_base: float = 5.0,
        hysteresis_margin_m: float = 0.20,
        persistence_count: int = 2
    ):
        self.s_base = s_base
        self.exit_threshold = s_base + hysteresis_margin_m  # e.g. 5.20 m
        self.persistence_count = persistence_count
        self.is_staged: bool = False
        self.clear_counter: int = 0
        self.last_raw_r: float = 100.0
        self.transitions_count: int = 0

    def update(self, r_effective: float) -> Tuple[bool, float]:
        """
        Updates filter with new visibility reading.
        Returns:
            (is_staged, filtered_effective_r)
        """
        self.last_raw_r = r_effective

        if r_effective <= self.s_base:
            # Immediate safety halt (fail-closed, 0 ms delay)
            if not self.is_staged:
                self.is_staged = True
                self.transitions_count += 1
            self.clear_counter = 0
            return True, min(r_effective, self.s_base)

        if self.is_staged:
            # Vehicle is staged; require sustained clearing above exit threshold
            if r_effective >= self.exit_threshold:
                self.clear_counter += 1
                if self.clear_counter >= self.persistence_count:
                    self.is_staged = False
                    self.transitions_count += 1
                    self.clear_counter = 0
                    return False, r_effective
                else:
                    # Still debouncing recovery; remain staged
                    return True, self.s_base
            else:
                # Visibility is between s_base and exit_threshold (deadband 5.0 - 5.2 m)
                self.clear_counter = 0
                return True, self.s_base
        else:
            # Vehicle is already moving
            self.clear_counter = 0
            return False, r_effective


class SafeBeaconAdapter:
    """
    Authoritative parser, state machine, and situational awareness adapter for Safe Beacons.
    """

    ALLOWED_VEHICLES: Set[str] = {"TRUCK_01", "TRUCK_02", "TRUCK_03", "TRUCK_04", "TRUCK_05", "EXCAVATOR_01"}

    # Severity ordering for deterministic precedence
    STATE_SEVERITY: Dict[BeaconState, int] = {
        BeaconState.NORMAL: 1,
        BeaconState.DEGRADED: 2,
        BeaconState.STOP: 3,
        BeaconState.EMERGENCY: 4,
    }

    def __init__(
        self,
        local_vehicle_id: str = "TRUCK_01",
        max_beacon_age_s: float = 1.0,
        future_tolerance_s: float = 0.10,
        peer_timeout_s: float = 1.0,
        allowed_vehicles: Optional[Set[str]] = None,
        clock: Callable[[], float] = time.time
    ):
        self.local_vehicle_id = local_vehicle_id
        self.max_beacon_age_s = max_beacon_age_s
        self.future_tolerance_s = future_tolerance_s
        self.peer_timeout_s = peer_timeout_s
        self.allowed_vehicles = allowed_vehicles or set(self.ALLOWED_VEHICLES)
        self.clock = clock

        # State tracking per peer vehicle
        self.peers: Dict[str, PeerVehicleTracking] = {}

        # Local combined situational awareness state
        self.current_system_state: BeaconSystemState = BeaconSystemState.NORMAL
        self.active_emergency_peers: Set[str] = set()
        self.active_stop_peers: Set[str] = set()

        # Dense fog debounce filter
        self.fog_filter = DenseFogDebounceFilter(s_base=5.0, hysteresis_margin_m=0.20, persistence_count=2)

        # Statistics
        self.total_received: int = 0
        self.total_accepted: int = 0
        self.total_rejected: int = 0
        self.rejection_counts: Dict[str, int] = {
            "MALFORMED": 0,
            "UNKNOWN_VEHICLE": 0,
            "UNKNOWN_STATE": 0,
            "OUT_OF_ORDER": 0,
            "DUPLICATE": 0,
            "STALE": 0,
            "FUTURE_TIMESTAMP": 0,
        }

    def format_beacon(
        self,
        sequence: int,
        state: BeaconState,
        zone_id: str,
        timestamp: Optional[float] = None
    ) -> str:
        """Serializes canonical BEACON packet."""
        t = timestamp if timestamp is not None else self.clock()
        st = state.value if isinstance(state, BeaconState) else str(state)
        return f"BEACON,{self.local_vehicle_id},{sequence},{st},{t:.4f},{zone_id}"

    def parse_beacon_packet(
        self,
        raw_packet: str,
        now: Optional[float] = None
    ) -> BeaconParseResult:
        """
        Parses and validates incoming raw BEACON packet string.
        Enforces malformed packet safety, vehicle identity, state enums,
        timestamp sanity, and strict sequence progression.
        """
        self.total_received += 1
        curr_time = now if now is not None else self.clock()

        if not raw_packet or not isinstance(raw_packet, str):
            self.total_rejected += 1
            self.rejection_counts["MALFORMED"] += 1
            return BeaconParseResult(False, None, "Packet is empty or not a string", "MALFORMED")

        line = raw_packet.strip()
        tokens = [t.strip() for t in line.split(",")]

        # Expected format: BEACON,vehicle_id,sequence,state,timestamp,zone_id (6 tokens)
        if len(tokens) < 6:
            self.total_rejected += 1
            self.rejection_counts["MALFORMED"] += 1
            return BeaconParseResult(
                False, None,
                f"Insufficient tokens in beacon packet: got {len(tokens)}, expected 6",
                "MALFORMED"
            )

        header = tokens[0].upper()
        if header != "BEACON":
            self.total_rejected += 1
            self.rejection_counts["MALFORMED"] += 1
            return BeaconParseResult(
                False, None,
                f"Invalid header '{tokens[0]}', expected 'BEACON'",
                "MALFORMED"
            )

        vid = tokens[1].strip()
        if not vid or (self.allowed_vehicles and vid not in self.allowed_vehicles):
            self.total_rejected += 1
            self.rejection_counts["UNKNOWN_VEHICLE"] += 1
            return BeaconParseResult(
                False, None,
                f"Unknown or unauthorized vehicle ID: '{vid}'",
                "UNKNOWN_VEHICLE"
            )

        # Sequence validation
        try:
            seq = int(tokens[2])
            if seq < 0:
                raise ValueError("Negative sequence")
        except (ValueError, TypeError):
            self.total_rejected += 1
            self.rejection_counts["MALFORMED"] += 1
            return BeaconParseResult(
                False, None,
                f"Invalid sequence number: '{tokens[2]}'",
                "MALFORMED"
            )

        # State validation
        state_str = tokens[3].strip().upper()
        try:
            beacon_state = BeaconState(state_str)
        except ValueError:
            self.total_rejected += 1
            self.rejection_counts["UNKNOWN_STATE"] += 1
            return BeaconParseResult(
                False, None,
                f"Unknown beacon state: '{tokens[3]}'. Allowed: {[s.value for s in BeaconState]}",
                "UNKNOWN_STATE"
            )

        # Timestamp validation
        try:
            ts = float(tokens[4])
            if math.isnan(ts) or math.isinf(ts) or ts <= 0.0:
                raise ValueError("Invalid float timestamp")
        except (ValueError, TypeError):
            self.total_rejected += 1
            self.rejection_counts["MALFORMED"] += 1
            return BeaconParseResult(
                False, None,
                f"Invalid timestamp value: '{tokens[4]}'",
                "MALFORMED"
            )

        # Check future timestamp
        if ts > (curr_time + self.future_tolerance_s):
            self.total_rejected += 1
            self.rejection_counts["FUTURE_TIMESTAMP"] += 1
            return BeaconParseResult(
                False, None,
                f"Future timestamp rejected: ts={ts:.4f} > curr_time={curr_time:.4f} + {self.future_tolerance_s}s",
                "FUTURE_TIMESTAMP"
            )

        # Check stale timestamp
        age = curr_time - ts
        if age > self.max_beacon_age_s:
            self.total_rejected += 1
            self.rejection_counts["STALE"] += 1
            return BeaconParseResult(
                False, None,
                f"Stale beacon packet rejected: age={age:.4f}s > max_age={self.max_beacon_age_s}s",
                "STALE"
            )

        zone_id = tokens[5].strip()
        if not zone_id:
            self.total_rejected += 1
            self.rejection_counts["MALFORMED"] += 1
            return BeaconParseResult(
                False, None,
                "Zone ID cannot be empty",
                "MALFORMED"
            )

        # Per-vehicle sequence tracking & Replay / Out-of-order rejection
        if vid in self.peers:
            peer = self.peers[vid]
            if seq == peer.last_sequence:
                self.total_rejected += 1
                self.rejection_counts["DUPLICATE"] += 1
                return BeaconParseResult(
                    False, None,
                    f"Duplicate sequence {seq} rejected for vehicle {vid}",
                    "DUPLICATE"
                )
            elif seq < peer.last_sequence:
                self.total_rejected += 1
                self.rejection_counts["OUT_OF_ORDER"] += 1
                return BeaconParseResult(
                    False, None,
                    f"Out-of-order sequence {seq} < latest {peer.last_sequence} rejected for {vid}",
                    "OUT_OF_ORDER"
                )

        # Valid beacon accepted!
        msg = SafeBeaconMessage(
            vehicle_id=vid,
            sequence=seq,
            state=beacon_state,
            timestamp=ts,
            zone_id=zone_id,
            raw_packet=line,
            received_at=curr_time
        )
        self.total_accepted += 1
        return BeaconParseResult(True, msg, "Accepted", "OK")

    def ingest_beacon(
        self,
        raw_packet: str,
        now: Optional[float] = None
    ) -> BeaconParseResult:
        """
        Ingests and updates local peer tracking and safety awareness state.
        """
        curr_time = now if now is not None else self.clock()
        res = self.parse_beacon_packet(raw_packet, now=curr_time)

        if not res.accepted or not res.beacon:
            return res

        b = res.beacon
        vid = b.vehicle_id

        # Update or create peer tracking record
        if vid not in self.peers:
            self.peers[vid] = PeerVehicleTracking(vehicle_id=vid)

        peer = self.peers[vid]
        peer.last_sequence = b.sequence
        peer.last_timestamp = b.timestamp
        peer.last_state = b.state
        peer.last_zone_id = b.zone_id
        peer.last_received_at = curr_time
        peer.packets_received += 1
        peer.is_stale = False
        peer.in_comm_loss = False

        # Update active emergency / stop peer sets
        if b.state == BeaconState.EMERGENCY:
            self.active_emergency_peers.add(vid)
        else:
            self.active_emergency_peers.discard(vid)

        if b.state == BeaconState.STOP:
            self.active_stop_peers.add(vid)
        else:
            self.active_stop_peers.discard(vid)

        self._recompute_system_state(curr_time)
        return res

    def check_timeouts(self, now: Optional[float] = None) -> List[str]:
        """
        Evaluates peer heartbeat freshness.
        Enforces "No beacon" ≠ "vehicle disappeared":
        When timeout expires, the vehicle is marked as COMM_LOSS / STALE,
        maintaining presence and triggering defensive posture.
        """
        curr_time = now if now is not None else self.clock()
        timed_out_peers = []

        for vid, peer in self.peers.items():
            if peer.last_received_at > 0:
                elapsed = curr_time - peer.last_received_at
                if elapsed > self.peer_timeout_s:
                    if not peer.in_comm_loss:
                        peer.in_comm_loss = True
                        peer.is_stale = True
                        timed_out_peers.append(vid)
                        logger.warning(
                            f"Peer {vid} beacon timed out ({elapsed:.3f}s > {self.peer_timeout_s}s). "
                            "Retaining vehicle presence under COMM_LOSS."
                        )

        self._recompute_system_state(curr_time)
        return timed_out_peers

    def _recompute_system_state(self, now: float):
        """
        Determines local system safety state using strict precedence:
        EMERGENCY > STOP > COMM_LOSS > DEGRADED > NORMAL.
        """
        if self.active_emergency_peers:
            self.current_system_state = BeaconSystemState.EMERGENCY
            return

        if self.active_stop_peers:
            self.current_system_state = BeaconSystemState.STOP
            return

        any_comm_loss = any(p.in_comm_loss for p in self.peers.values())
        if any_comm_loss:
            self.current_system_state = BeaconSystemState.COMM_LOSS
            return

        any_degraded = any(p.last_state == BeaconState.DEGRADED for p in self.peers.values())
        if any_degraded:
            self.current_system_state = BeaconSystemState.DEGRADED
            return

        self.current_system_state = BeaconSystemState.NORMAL

    def get_local_safe_headway_multiplier(self) -> float:
        """
        Returns headway scaling factor based on beacon situational awareness.
        If a peer is in COMM_LOSS / DEGRADED, following headway doubles (e.g. 50m -> 100m).
        """
        if self.current_system_state in (BeaconSystemState.COMM_LOSS, BeaconSystemState.DEGRADED):
            return 2.0
        return 1.0

    def evaluate_dense_fog_visibility(self, r_effective: float) -> Tuple[bool, float]:
        """
        Applies Schmitt-trigger debounce around the 5.0 m boundary.
        Returns: (is_staged, filtered_visibility)
        """
        return self.fog_filter.update(r_effective)

    def reset_recovery(self):
        """Resets emergency/stop tracking after clear conditions verified."""
        self.active_emergency_peers.clear()
        self.active_stop_peers.clear()
        for p in self.peers.values():
            p.in_comm_loss = False
            p.is_stale = False
            p.last_state = BeaconState.NORMAL
        self.current_system_state = BeaconSystemState.NORMAL
