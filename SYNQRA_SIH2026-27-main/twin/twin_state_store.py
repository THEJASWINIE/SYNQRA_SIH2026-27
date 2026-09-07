"""
FOG-ORCHESTRATOR 2.0 — Canonical Digital Twin State Store (P1).

THIN state-management layer over the EXISTING Digital Twin.

    twin/network.py       MineNetwork / RoadEdge / Node  -> topology and domain behaviour
    models/vehicle.py     Vehicle                        -> vehicle domain model
    weather/fog_model.py  FogModel                       -> environment domain model
    models/*              physics                        -> safety/physics behaviour

This module owns NONE of that. It owns the canonical *current synchronized state*:
per-field values with provenance, per-field timestamps, quality, and source mode.

It is deliberately NOT:
  - a second Digital Twin,
  - a second physics engine,
  - a simulation stepper.

It never computes a physical quantity and never invents one. A field that nothing has
supplied reads back as UNAVAILABLE, not as a plausible-looking number.

Related but different: `twin/state.py` (TwinState.compile_state) is a stateless one-shot
serializer for reports and the HMI contract. It holds nothing between calls and carries
no provenance. This module is the thing that holds state.

Design note: this module imports nothing from `twin`, `models` or `weather` at runtime.
It reads domain objects structurally (duck-typed). That is what makes it impossible for
it to change the behaviour of `twin/simulator.py`, `main.py`, `game_ui.py` or the
existing tests.

FIELD-LEVEL HARDWARE PRECEDENCE (P4)
------------------------------------
One store holds simulated and physical vehicles at once. When both sources can supply the
SAME field of the SAME vehicle:

    a valid & current HARDWARE-backed observation outranks a SIMULATION value.

Decided PER FIELD, never per vehicle. A physical truck keeps its measured `rpm` and IMU
while simultaneously carrying simulated `position_s`, `road_id` and environment - each
with its own provenance. Hardware never takes over the whole entity.

  valid & current := available, quality not INVALID, and not aged past `stale_after_s`
                     (see `Sourced.is_current`). With no threshold configured, freshness
                     is not evaluated rather than assumed.

  hardware-backed := `Sourced.origin` (or `source`) is HARDWARE. `origin` exists so a
                     speed DERIVED from a measured RPM is still recognised as standing on
                     a real sensor.

Precedence deliberately does NOT compare sequence numbers: those counters are
transport-specific and mean nothing across sources.

Fallback: when a hardware-backed field goes STALE or INVALID, simulation may take it over
ONLY if the field is listed in `SIMULATION_FALLBACK_FIELDS`. The value is then stored with
source=SIMULATION, so the takeover is visible in the snapshot and no false HARDWARE label
survives. Measured quantities are deliberately absent from that list - a stale RPM reads
as STALE rather than being quietly replaced by a simulated one.
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, Iterable, Optional


# =====================================================================
# PROVENANCE PRIMITIVES
# =====================================================================

class Source(str, Enum):
    """Where a value came from. Never guessed - always set by whoever supplied it."""

    SIMULATION = "SIMULATION"   # produced by the simulation / domain models
    HARDWARE = "HARDWARE"       # measured on a physical vehicle or sensor
    DERIVED = "DERIVED"         # computed from other state (e.g. physics solver output)
    CONFIGURED = "CONFIGURED"   # static reference/config value; not a measurement
    UNKNOWN = "UNKNOWN"         # nothing has supplied this field yet


class Quality(str, Enum):
    GOOD = "GOOD"
    DEGRADED = "DEGRADED"
    STALE = "STALE"
    INVALID = "INVALID"
    UNKNOWN = "UNKNOWN"


class ClockDomain(str, Enum):
    """
    Which clock a timestamp belongs to.

    The simulator runs on deterministic simulation seconds (`sim.current_time`, starting
    near 0); telemetry carries wall-clock epoch seconds. Those are different number lines.
    Comparing one against the other produces a meaningless age, which is why every
    timestamped field records the domain it was measured in.

    NEVER inferred from a value's magnitude - always declared by whoever supplied it.
    """

    SIMULATION = "SIMULATION"    # deterministic simulation seconds
    WALL_CLOCK = "WALL_CLOCK"    # epoch seconds
    UNKNOWN = "UNKNOWN"          # not declared


class TwinMode(str, Enum):
    SIMULATION = "SIMULATION"
    HARDWARE = "HARDWARE"
    HYBRID = "HYBRID"


@dataclass(frozen=True)
class Sourced:
    """
    One dynamic field: its value plus how much that value can be trusted.

    `value is None` together with `source == UNKNOWN` is the explicit "not available"
    state. It is a first-class answer, not a failure.
    """

    value: Any = None
    timestamp: Optional[float] = None
    source: Source = Source.UNKNOWN
    quality: Quality = Quality.UNKNOWN
    # Where the value ULTIMATELY came from, when that differs from `source`.
    #
    # A speed computed from a measured wheel RPM has source=DERIVED (it went through a
    # calculation) but origin=HARDWARE (a real sensor stands behind it). P4 precedence
    # needs that distinction: such a value must not be silently replaced by a simulated
    # one. Left None when origin and source are the same thing.
    #
    # Deliberately NOT part of `as_dict()` - it is internal arbitration metadata, and the
    # snapshot contract stays exactly as P1 defined it.
    origin: Optional[Source] = None
    # The clock `timestamp` is expressed in. Freshness is only ever evaluated against a
    # reference time from the SAME domain.
    clock_domain: ClockDomain = ClockDomain.UNKNOWN

    @property
    def is_available(self) -> bool:
        return self.value is not None and self.source is not Source.UNKNOWN

    def domain_matches(self, now_domain: Optional["ClockDomain"]) -> bool:
        """True when a reference time in `now_domain` may be compared to this timestamp."""
        if now_domain is None:
            return True                                  # caller declared no domain (legacy path)
        if self.clock_domain is ClockDomain.UNKNOWN or now_domain is ClockDomain.UNKNOWN:
            return False                                 # no compatible clock -> do not compare
        return self.clock_domain is now_domain

    def age_in(self, now: Optional[float], now_domain: Optional["ClockDomain"]) -> Optional[float]:
        """
        Age against a reference time of a stated domain.

        Returns None when no compatible clock exists. An age is never manufactured across
        domains: a simulation timestamp of 120.0 is not 1.7 billion seconds old.
        """
        if now is None or self.timestamp is None:
            return None
        if not self.domain_matches(now_domain):
            return None
        return max(0.0, now - self.timestamp)

    def freshness(self, now: Optional[float], stale_after_s: Optional[float],
                  now_domain: Optional["ClockDomain"] = None) -> str:
        """CURRENT / STALE / NOT_EVALUATED. Never STALE merely because clocks differ."""
        if not self.is_available:
            return "NOT_EVALUATED"
        if stale_after_s is None:
            return "NOT_EVALUATED"                       # threshold unconfigured (P1 rule)
        age = self.age_in(now, now_domain)
        if age is None:
            return "NOT_EVALUATED"                       # no compatible clock
        return "STALE" if age > stale_after_s else "CURRENT"

    @property
    def effective_origin(self) -> Source:
        """`origin` when set, otherwise `source`."""
        return self.origin if self.origin is not None else self.source

    def is_hardware_backed(self) -> bool:
        """True when a physical sensor ultimately stands behind this value."""
        return self.effective_origin is Source.HARDWARE

    def is_current(self, now: float, stale_after_s: Optional[float],
                   now_domain: Optional["ClockDomain"] = None) -> bool:
        """
        Valid AND current: available, not INVALID, and not aged past the threshold.

        With no configured staleness threshold, freshness is NOT evaluated (P1 rule: a
        missing threshold is never silently replaced by an assumed one), so an available
        non-INVALID value counts as current.
        """
        if not self.is_available:
            return False
        return self.effective_quality(now, stale_after_s, now_domain) not in (
            Quality.STALE,
            Quality.INVALID,
            Quality.UNKNOWN,
        )

    def age_s(self, now: float) -> Optional[float]:
        return None if self.timestamp is None else max(0.0, now - self.timestamp)

    def effective_quality(self, now: float, stale_after_s: Optional[float],
                          now_domain: Optional["ClockDomain"] = None) -> Quality:
        """
        Quality as it stands *right now*. A value that was GOOD when written becomes
        STALE once it ages past the threshold. Stored quality is never mutated -
        staleness is a function of the read time (CLAUDE.md Rule 9).

        Staleness is only applied when the reference time is in a compatible clock domain.
        When it is not, the stored quality is returned unchanged: a field is never called
        STALE just because it was measured on a different clock.
        """
        if not self.is_available:
            return Quality.UNKNOWN
        if self.quality is Quality.INVALID:
            return Quality.INVALID
        if stale_after_s is None or self.timestamp is None:
            return self.quality
        age = self.age_in(now, now_domain)
        if age is None:
            return self.quality                          # no compatible clock -> not evaluated
        if age > stale_after_s:
            return Quality.STALE
        return self.quality

    def as_dict(self, now: float, stale_after_s: Optional[float] = None,
                now_domain: Optional["ClockDomain"] = None) -> Dict[str, Any]:
        return {
            "value": self.value,
            "timestamp": self.timestamp,
            "source": self.source.value,
            "quality": self.effective_quality(now, stale_after_s, now_domain).value,
            "age_s": self.age_in(now, now_domain),
            "available": self.is_available,
            # P4.1: the distinction is exposed, not hidden.
            "clock_domain": self.clock_domain.value,
            "freshness": self.freshness(now, stale_after_s, now_domain),
        }


UNAVAILABLE = Sourced()


# =====================================================================
# ENTITY STATE CONTAINERS
# =====================================================================

# Dynamic vehicle fields the store tracks. Anything not listed is either static
# (see `static`) or simply not modelled yet.
VEHICLE_DYNAMIC_FIELDS = (
    "position_s",             # m along current road edge
    "road_id",                # current road edge id
    "node_id",                # current node id when parked/queued
    "speed_mps",
    "acceleration_mps2",
    "heading_rad",
    "rpm",
    "mass_kg",
    "payload_kg",
    "is_loaded",
    "state",                  # idle / traveling / queued / loading / dumping
    "v_safe_mps",
    "v_dispatch_mps",
    "v_command_mps",
    "safe_headway_m",
    "stop_envelope_m",
    "warning_fault",
    "communication_state",
)

ROAD_DYNAMIC_FIELDS = (
    "visibility_m",
    "friction_mu",
    "c_rr",
    "surface_state",
    "v_safe_mps",
    "safe_headway_m",
    "capacity_vph",
    "vehicle_count",
)

# Fields the architecture explicitly permits simulation to take over when the
# hardware-backed value has gone STALE or INVALID.
#
# Deliberately tiny. `speed_mps` is the ONLY field both sources currently produce under
# the same name (the simulator writes it; telemetry derives it from measured RPM), so it
# is the only genuine conflict. Everything else is disjoint by name - measured `rpm` /
# `ax_mps2` on one side, simulated `position_s` / `state` on the other - and therefore
# coexists without arbitration.
#
# Measured quantities are NOT listed: a stale RPM must not be quietly replaced by a
# simulated one. It simply reads as STALE, which is the honest answer.
SIMULATION_FALLBACK_FIELDS = frozenset({"speed_mps"})

ENVIRONMENT_DYNAMIC_FIELDS = (
    "visibility_m",
    "friction_mu",
    "c_rr",
    "surface_state",
    "scenario",
)


@dataclass
class EntityState:
    """Common shape: an id, immutable configured properties, and sourced dynamic fields."""

    entity_id: str
    static: Dict[str, Any] = field(default_factory=dict)
    dynamic: Dict[str, Sourced] = field(default_factory=dict)

    def get(self, name: str) -> Sourced:
        return self.dynamic.get(name, UNAVAILABLE)

    def set(
        self,
        name: str,
        value: Any,
        source: Source,
        timestamp: float,
        quality: Quality = Quality.GOOD,
        origin: Optional[Source] = None,
        clock_domain: ClockDomain = ClockDomain.UNKNOWN,
    ) -> None:
        self.dynamic[name] = Sourced(
            value=value,
            timestamp=timestamp,
            source=Source(source),
            quality=Quality(quality),
            origin=Source(origin) if origin is not None else None,
            clock_domain=ClockDomain(clock_domain),
        )

    def as_dict(self, now: float, stale_after_s: Optional[float] = None,
                now_by_domain: Optional[Dict["ClockDomain", Optional[float]]] = None) -> Dict[str, Any]:
        """
        `now_by_domain` supplies a reference time per clock domain. Each field is aged
        against its OWN domain's reference; a field whose domain has no reference time is
        reported NOT_EVALUATED rather than stale.
        """
        def render(sourced: "Sourced") -> Dict[str, Any]:
            if now_by_domain is None:
                return sourced.as_dict(now, stale_after_s)
            domain = sourced.clock_domain
            return sourced.as_dict(now_by_domain.get(domain), stale_after_s, domain)

        return {
            "id": self.entity_id,
            "static": dict(self.static),
            "dynamic": {k: render(v) for k, v in sorted(self.dynamic.items())},
        }


@dataclass
class VehicleState(EntityState):
    """Canonical vehicle state. `domain_vehicle` is the EXISTING models.vehicle.Vehicle."""

    domain_vehicle: Any = None


@dataclass
class RoadState(EntityState):
    domain_edge: Any = None


# =====================================================================
# THE STORE
# =====================================================================

class TwinStateStore:
    """
    Canonical runtime location for current synchronized Digital Twin state.

    Typical wiring:

        store = TwinStateStore(network=network, mode=TwinMode.SIMULATION)
        for v in simulator.vehicles:
            store.register_vehicle(v)
        ...
        store.sync_from_simulation(simulator)     # after each simulator.run_step()

    Hardware telemetry (P3) writes individual fields instead:

        store.update_vehicle_field("TRUCK_02", "rpm", 240.0, Source.HARDWARE)

    A field update touches that field only. Nothing else in the Twin is disturbed.
    """

    def __init__(
        self,
        network: Any = None,
        mode: TwinMode = TwinMode.SIMULATION,
        clock: Callable[[], float] = time.time,
        stale_after_s: Optional[float] = None,
    ):
        self._clock = clock
        self._mode = TwinMode(mode)
        self.stale_after_s = stale_after_s

        # P3: server-side ingestion made this store multi-writer. One reentrant lock around
        # canonical state mutation and snapshot reads is the smallest correct model - a
        # packet can never leave the Twin partially updated, and a snapshot can never
        # observe a half-applied update. Reentrant because public methods call each other
        # (e.g. sync_from_simulation -> bind_network -> register_vehicle).
        # ponytail: single store-wide lock; per-vehicle locks only if ingest throughput
        # ever measurably contends.
        self._lock = threading.RLock()

        self._vehicles: Dict[str, VehicleState] = {}
        self._roads: Dict[str, RoadState] = {}
        self._mine: Dict[str, Any] = {"nodes": {}, "adjacency": {}}
        self._environment = EntityState(entity_id="ENVIRONMENT")
        self._network: Any = None
        self._last_sync_ts: Optional[float] = None
        # Latest SIMULATION-domain reference time, taken from the simulator's own clock
        # (sim.current_time). Never converted to epoch time.
        self._sim_now: Optional[float] = None

        if network is not None:
            self.bind_network(network)

    # -- mode ---------------------------------------------------------

    @property
    def mode(self) -> TwinMode:
        return self._mode

    def set_mode(self, mode: TwinMode) -> None:
        self._mode = TwinMode(mode)

    @property
    def last_sync_timestamp(self) -> Optional[float]:
        return self._last_sync_ts

    def now(self) -> float:
        """Wall-clock now."""
        return self._clock()

    @property
    def simulation_now(self) -> Optional[float]:
        """Latest simulation-clock reference, or None before any simulation sync."""
        return self._sim_now

    def now_by_domain(self) -> Dict[ClockDomain, Optional[float]]:
        """
        Reference time per clock domain.

        WALL_CLOCK always has one. SIMULATION has one only after a simulation sync has
        told us what the simulator's clock reads. UNKNOWN never does - a field with an
        undeclared domain is simply not aged.
        """
        return {
            ClockDomain.WALL_CLOCK: self._clock(),
            ClockDomain.SIMULATION: self._sim_now,
            ClockDomain.UNKNOWN: None,
        }

    # -- binding existing domain objects ------------------------------

    def bind_network(self, network: Any) -> None:
        """
        Adopt an EXISTING MineNetwork. Topology and geometry are CONFIGURED reference
        data - they are not measurements and are not given physical provenance.
        """
        with self._lock:
            self._bind_network_locked(network)

    def _bind_network_locked(self, network: Any) -> None:
        self._network = network

        for road_id, edge in getattr(network, "edges", {}).items():
            existing = self._roads.get(road_id)
            self._roads[road_id] = RoadState(
                entity_id=road_id,
                domain_edge=edge,
                static={
                    "start_node": getattr(edge, "start_node", None),
                    "end_node": getattr(edge, "end_node", None),
                    "length_m": _as_float(getattr(edge, "length_m", None)),
                    "grade_percent": _as_float(getattr(edge, "grade_percent", None)),
                    "curve_radius_m": _as_float(getattr(edge, "curve_radius_m", None)),
                    "speed_limit_mps": _as_float(getattr(edge, "speed_limit_mps", None)),
                    "width_m": _as_float(getattr(edge, "width_m", None)),
                },
                # Re-binding must not discard state already observed for this road.
                dynamic=dict(existing.dynamic) if existing is not None else {},
            )

        self._mine = {
            "nodes": {
                node_id: {
                    "id": node_id,
                    "type": getattr(node, "type", None),
                    "service_rate_vph": _as_float(getattr(node, "service_rate_vph", None)),
                    "criticality": _as_float(getattr(node, "criticality", None)),
                    "has_queue": getattr(node, "queue", None) is not None,
                }
                for node_id, node in getattr(network, "nodes", {}).items()
            },
            "adjacency": {
                start: [getattr(e, "id", None) for e in edges]
                for start, edges in getattr(network, "adjacency", {}).items()
            },
        }

    def register_vehicle(self, vehicle: Any, vehicle_id: Optional[str] = None) -> VehicleState:
        """
        Register an EXISTING vehicle object (models.vehicle.Vehicle) or, when only an id
        is known (a physical truck reporting telemetry), a bare id string.

        Registration records static/configured properties only. No dynamic field is
        populated here - nothing has been observed yet, so everything reads UNAVAILABLE.
        """
        if isinstance(vehicle, str):
            vehicle_id, vehicle = vehicle, None
        if vehicle_id is None:
            vehicle_id = getattr(vehicle, "id", None)
        if not vehicle_id:
            raise ValueError("register_vehicle requires a vehicle id")

        static: Dict[str, Any] = {}
        if vehicle is not None:
            for src_attr, key in (
                ("tare_mass", "tare_mass_kg"),
                ("payload_capacity", "payload_capacity_kg"),
                ("length", "length_m"),
                ("width", "width_m"),
                ("wheelbase", "wheelbase_m"),
            ):
                if hasattr(vehicle, src_attr):
                    static[key] = _as_float(getattr(vehicle, src_attr))

        with self._lock:
            existing = self._vehicles.get(vehicle_id)
            state = VehicleState(
                entity_id=vehicle_id,
                domain_vehicle=vehicle,
                static=static,
                # Re-registering must NEVER discard state a real source already reported
                # (e.g. a physical truck that reported telemetry before its simulation
                # Vehicle object was attached).
                dynamic=dict(existing.dynamic) if existing is not None else {},
            )
            self._vehicles[vehicle_id] = state
            return state

    # -- per-field updates --------------------------------------------

    def update_vehicle_field(
        self,
        vehicle_id: str,
        name: str,
        value: Any,
        source: Source,
        timestamp: Optional[float] = None,
        quality: Quality = Quality.GOOD,
        origin: Optional[Source] = None,
        clock_domain: ClockDomain = ClockDomain.UNKNOWN,
    ) -> None:
        """Update exactly one vehicle field. Unrelated fields are untouched."""
        with self._lock:
            state = self._vehicles.get(vehicle_id)
            if state is None:
                raise KeyError(f"unknown vehicle '{vehicle_id}' - register it before updating state")
            state.set(name, value, source, timestamp if timestamp is not None else self.now(),
                      quality, origin=origin, clock_domain=clock_domain)

    def update_vehicle_fields(self, vehicle_id: str, updates: Dict[str, "Sourced"]) -> None:
        """
        Apply several vehicle fields ATOMICALLY.

        Either every field in `updates` lands or none does. This is the entry point for
        telemetry ingestion (P3): one packet must never leave the Twin half-updated, and a
        concurrent snapshot must never observe a partially applied packet.

        Values are pre-built `Sourced` instances so the caller owns provenance decisions;
        the store does not guess a source or a quality.
        """
        if not updates:
            return
        with self._lock:
            state = self._vehicles.get(vehicle_id)
            if state is None:
                raise KeyError(f"unknown vehicle '{vehicle_id}' - register it before updating state")
            # Validate the whole batch before mutating anything.
            for name, sourced in updates.items():
                if not isinstance(sourced, Sourced):
                    raise TypeError(f"field '{name}' must be a Sourced, got {type(sourced).__name__}")
            state.dynamic.update(updates)

    def update_road_field(
        self,
        road_id: str,
        name: str,
        value: Any,
        source: Source,
        timestamp: Optional[float] = None,
        quality: Quality = Quality.GOOD,
        origin: Optional[Source] = None,
        clock_domain: ClockDomain = ClockDomain.UNKNOWN,
    ) -> None:
        with self._lock:
            state = self._roads.get(road_id)
            if state is None:
                raise KeyError(f"unknown road '{road_id}'")
            state.set(name, value, source, timestamp if timestamp is not None else self.now(),
                      quality, origin=origin, clock_domain=clock_domain)

    def update_environment_field(
        self,
        name: str,
        value: Any,
        source: Source,
        timestamp: Optional[float] = None,
        quality: Quality = Quality.GOOD,
        origin: Optional[Source] = None,
        clock_domain: ClockDomain = ClockDomain.UNKNOWN,
    ) -> None:
        with self._lock:
            self._environment.set(
                name, value, source, timestamp if timestamp is not None else self.now(),
                quality, origin=origin, clock_domain=clock_domain
            )

    # -- synchronization from the existing simulation -----------------

    def sync_from_simulation(
        self,
        simulator: Any = None,
        network: Any = None,
        vehicles: Optional[Iterable[Any]] = None,
        fog_model: Any = None,
        timestamp: Optional[float] = None,
    ) -> float:
        """
        Pull current values out of the existing domain objects and stamp them SIMULATION
        (physics/solver outputs are stamped DERIVED).

        Reads only. The simulator is never stepped from here - stepping stays in
        `twin/simulator.py`, which remains the owner of domain behaviour.
        """
        if simulator is not None:
            network = network if network is not None else getattr(simulator, "network", None)
            vehicles = vehicles if vehicles is not None else getattr(simulator, "vehicles", None)
            fog_model = fog_model if fog_model is not None else getattr(simulator, "fog_model", None)
            if timestamp is None:
                timestamp = _as_float(getattr(simulator, "current_time", None))

        ts = timestamp if timestamp is not None else self.now()

        if network is not None and network is not self._network:
            self.bind_network(network)
        if network is None:
            network = self._network

        with self._lock:
            if fog_model is not None:
                self._sync_environment(fog_model, ts)
            if network is not None:
                self._sync_roads(network, ts)
            if vehicles is not None:
                self._sync_vehicles(vehicles, ts)
            self._last_sync_ts = ts
            self._sim_now = ts          # the simulator's own clock, kept in its own domain
        return ts

    def _sync_environment(self, fog_model: Any, ts: float) -> None:
        for attr, name in (
            ("current_visibility", "visibility_m"),
            ("current_friction", "friction_mu"),
            ("current_rr", "c_rr"),
            ("current_state", "surface_state"),
            ("scenario_name", "scenario"),
        ):
            if hasattr(fog_model, attr):
                self._environment.set(name, getattr(fog_model, attr), Source.SIMULATION, ts,
                                     origin=Source.SIMULATION, clock_domain=ClockDomain.SIMULATION)

    def _sync_roads(self, network: Any, ts: float) -> None:
        for road_id, edge in getattr(network, "edges", {}).items():
            state = self._roads.get(road_id)
            if state is None:
                self._bind_network_locked(network)
                state = self._roads[road_id]

            # Environment on the segment: supplied by the simulation's fog model.
            for attr, name in (
                ("visibility_m", "visibility_m"),
                ("friction_mu", "friction_mu"),
                ("c_rr", "c_rr"),
                ("surface_state", "surface_state"),
            ):
                if hasattr(edge, attr):
                    state.set(name, getattr(edge, attr), Source.SIMULATION, ts,
                              origin=Source.SIMULATION, clock_domain=ClockDomain.SIMULATION)

            # Physics/safety solver outputs: DERIVED, not measured.
            for attr, name in (
                ("v_safe_mps", "v_safe_mps"),
                ("safe_headway_m", "safe_headway_m"),
                ("capacity_vph", "capacity_vph"),
            ):
                if hasattr(edge, attr):
                    state.set(name, getattr(edge, attr), Source.DERIVED, ts,
                              origin=Source.SIMULATION, clock_domain=ClockDomain.SIMULATION)

            state.set("vehicle_count", len(getattr(edge, "vehicles", []) or []), Source.SIMULATION, ts,
                      origin=Source.SIMULATION, clock_domain=ClockDomain.SIMULATION)

    def _simulation_may_write(self, state: "EntityState", name: str, now: float) -> bool:
        """
        FIELD-LEVEL HARDWARE PRECEDENCE (P4).

            For the SAME vehicle and the SAME field:
                a valid, current HARDWARE-backed observation outranks a SIMULATION value.

        This is decided per field, never per vehicle: a hardware truck keeps simulated
        position and simulated environment alongside its measured RPM and IMU. Only a
        field that a real sensor currently stands behind is protected.

        Precedence is provenance + freshness. It deliberately does NOT compare sequence
        numbers: those are transport-specific counters and mean nothing across sources.

        Fallback: when a hardware-backed field goes STALE or INVALID, simulation may take
        it over ONLY if the field appears in SIMULATION_FALLBACK_FIELDS. The value is then
        written with source=SIMULATION, so the takeover is visible in the snapshot and no
        false HARDWARE label survives.
        """
        existing = state.dynamic.get(name)
        if existing is None or not existing.is_hardware_backed():
            return True                       # nothing hardware-backed here to protect

        reference = self.now_by_domain().get(existing.clock_domain)
        if existing.is_current(reference, self.stale_after_s, existing.clock_domain):
            return False                      # valid + current hardware wins

        # Hardware present but stale/invalid.
        return name in SIMULATION_FALLBACK_FIELDS

    def _sync_vehicles(self, vehicles: Iterable[Any], ts: float) -> None:
        # Simulation-owned kinematic / operational state.
        simulated = (
            ("position_s", "position_s"),
            ("current_edge", "road_id"),
            ("current_node", "node_id"),
            ("speed_mps", "speed_mps"),
            ("acceleration_mps2", "acceleration_mps2"),
            ("mass_kg", "mass_kg"),
            ("payload_kg", "payload_kg"),
            ("is_loaded", "is_loaded"),
            ("state", "state"),
        )
        # Physics / safety solver outputs.
        derived = (
            ("v_safe_mps", "v_safe_mps"),
            ("v_dispatch_mps", "v_dispatch_mps"),
            ("v_command_mps", "v_command_mps"),
            ("safe_headway_m", "safe_headway_m"),
            ("stop_envelope_m", "stop_envelope_m"),
            ("warning_fault", "warning_fault"),
        )

        for vehicle in vehicles:
            vid = getattr(vehicle, "id", None)
            if not vid:
                continue
            state = self._vehicles.get(vid)
            if state is None:
                state = self.register_vehicle(vehicle, vid)

            for attr, name in simulated:
                if hasattr(vehicle, attr) and self._simulation_may_write(state, name, ts):
                    state.set(name, getattr(vehicle, attr), Source.SIMULATION, ts,
                              origin=Source.SIMULATION, clock_domain=ClockDomain.SIMULATION)
            for attr, name in derived:
                if hasattr(vehicle, attr) and self._simulation_may_write(state, name, ts):
                    # A solver result stays DERIVED even for a simulated vehicle: it is a
                    # physics output, not an observation of the simulation.
                    state.set(name, getattr(vehicle, attr), Source.DERIVED, ts,
                              origin=Source.SIMULATION, clock_domain=ClockDomain.SIMULATION)

            # NOTE: rpm, heading_rad and communication_state are deliberately NOT filled
            # here. The simulation does not produce them. They stay UNAVAILABLE until a
            # real source supplies them (P3 telemetry ingestion).

    # -- query API ----------------------------------------------------

    def get_vehicle(self, vehicle_id: str) -> Optional[VehicleState]:
        """Canonical vehicle state, or None when the vehicle is unknown."""
        return self._vehicles.get(vehicle_id)

    def get_all_vehicles(self) -> Dict[str, VehicleState]:
        return dict(self._vehicles)

    def get_road(self, road_id: str) -> Optional[RoadState]:
        return self._roads.get(road_id)

    def get_all_roads(self) -> Dict[str, RoadState]:
        return dict(self._roads)

    def get_environment(self) -> EntityState:
        return self._environment

    def get_mine(self) -> Dict[str, Any]:
        return {
            "nodes": dict(self._mine.get("nodes", {})),
            "adjacency": dict(self._mine.get("adjacency", {})),
        }

    def get_vehicle_field(self, vehicle_id: str, name: str) -> Sourced:
        """Field lookup that answers UNAVAILABLE for unknown vehicles and unset fields."""
        state = self._vehicles.get(vehicle_id)
        return UNAVAILABLE if state is None else state.get(name)

    def get_state_snapshot(self, now: Optional[float] = None) -> Dict[str, Any]:
        """Full canonical snapshot. Every dynamic field carries its own provenance."""
        t = now if now is not None else self.now()
        with self._lock:
            domains = self.now_by_domain()
            if now is not None:
                # An explicit `now` overrides the wall-clock reference only.
                domains[ClockDomain.WALL_CLOCK] = now
            return {
                "schema": "twin_state_snapshot/1",
                "snapshot_timestamp": t,
                "mode": self._mode.value,
                "last_sync_timestamp": self._last_sync_ts,
                "stale_after_s": self.stale_after_s,
                "simulation_time": self._sim_now,
                "environment": self._environment.as_dict(t, self.stale_after_s, domains),
                "mine": self.get_mine(),
                "roads": {rid: r.as_dict(t, self.stale_after_s, domains) for rid, r in sorted(self._roads.items())},
                "vehicles": {vid: v.as_dict(t, self.stale_after_s, domains) for vid, v in sorted(self._vehicles.items())},
            }


def _as_float(value: Any) -> Any:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return value
