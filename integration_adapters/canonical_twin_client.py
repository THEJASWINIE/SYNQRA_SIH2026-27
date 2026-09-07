"""
Canonical Twin read-only client — P9.

==============================================================================
 READ-ONLY. THIS ADAPTER NEVER WRITES ANYTHING.

 It performs exactly one HTTP verb, GET, against the HMI backend's Twin
 snapshot. It issues no command, publishes no telemetry and mutates no Twin.
 The command path is unchanged and remains:

     HMI -> POST /api/commands -> CommandGateway

 game_ui is a VISUALISATION CLIENT, not a command client (root CLAUDE.md §13).
==============================================================================

WHY THIS EXISTS

`game_ui.py` runs its own `Simulator` and its own in-process `TwinStateStore`
(TwinMode.SIMULATION) holding the SIMULATED fleet. The HMI backend runs a
separate `TwinStateStore` holding whatever telemetry actually arrived. Those are
two different modelled systems that happen to share vehicle ids.

Before P9 the simulator could not see the backend's Twin at all. This adapter
lets it DISPLAY that canonical state beside its own, clearly labelled, without
merging the two. It deliberately does NOT:

  - write canonical values into the simulator or its Twin
  - let a canonical value stand in for a simulated one, or the reverse
  - synthesise any field the snapshot does not carry

WHAT THE LIVE SNAPSHOT ACTUALLY CARRIES (measured, not assumed)

  AVAILABLE    speed_mps, speed_mps_reported, rpm, communication_state,
               sequence, received_at, telemetry_transport, each with
               source / origin / quality / freshness / age_s
  UNAVAILABLE  visibility, friction, surface, fog state, road_id, position,
               heading, grade, curvature, v_safe, v_command, safety state,
               stopping distance, individual limiters

Nothing here invents a member of the second list. A field the snapshot omits is
reported as absent, and the caller renders UNAVAILABLE.

The parsing half is PURE and needs no network, so the contract is testable
without a running backend.
"""

from __future__ import annotations

import json
import threading
import urllib.error
import urllib.request
from dataclasses import dataclass, field as dataclass_field
from typing import Any, Dict, Optional

# The marker the whole project uses for "not supplied". Never 0, never a fallback.
UNAVAILABLE_TEXT = "--"

DEFAULT_SNAPSHOT_URL = "http://127.0.0.1:8000/api/twin/snapshot"

# Short by design: this runs beside a render loop. A slow backend must degrade to
# UNAVAILABLE rather than stall the visualiser.
DEFAULT_TIMEOUT_S = 1.0

# How often the poller asks. The backend is authoritative for freshness; polling
# faster than telemetry arrives would not make anything fresher.
DEFAULT_POLL_INTERVAL_S = 1.0


@dataclass(frozen=True)
class CanonicalField:
    """One canonical Twin field, exactly as the snapshot reported it."""

    value: Any
    source: Optional[str]
    origin: Optional[str]
    quality: Optional[str]
    freshness: Optional[str]
    age_s: Optional[float]
    available: bool

    def provenance_label(self) -> str:
        """
        SIMULATION vs PHYSICAL, in the SAME vocabulary the HMI uses.

        Deliberately identical wording to the frontend's `dataStatus.provenanceLabel`
        (P8), so one fact does not acquire a second name just because it is being
        shown by pygame instead of React.

        `origin` is what the value ultimately rests on; `source` is how it was
        obtained. A speed DERIVED from a measured RPM has origin HARDWARE and is
        physical, and says that it was derived.

        NEVER inferred from connectivity: reaching the backend says nothing about
        whether a truck's wheel was actually turning a real encoder.
        """
        if self.origin == "HARDWARE":
            return "PHYSICAL (derived)" if self.source == "DERIVED" else "PHYSICAL"
        if self.origin == "SIMULATION":
            return "SIMULATION"
        if self.source is None and self.origin is None:
            return UNAVAILABLE_TEXT
        return "%s · %s" % (self.source, self.origin)

    def freshness_label(self) -> str:
        """CURRENT / STALE / UNKNOWN / UNAVAILABLE — the P8 data-state vocabulary."""
        if not self.available:
            return "UNAVAILABLE"
        if self.freshness in ("CURRENT", "STALE"):
            return self.freshness
        if self.freshness == "MISSING":
            return "UNAVAILABLE"
        return "UNKNOWN"


# A field nothing supplied. Distinct from a field supplied as 0.
ABSENT_FIELD = CanonicalField(
    value=None, source=None, origin=None, quality=None,
    freshness=None, age_s=None, available=False,
)


@dataclass(frozen=True)
class CanonicalVehicle:
    """The canonical Twin's view of one vehicle. Only what the snapshot carried."""

    vehicle_id: str
    fields: Dict[str, CanonicalField] = dataclass_field(default_factory=dict)

    def get(self, name: str) -> CanonicalField:
        """A field, or the explicit absent field. Never a fabricated default."""
        return self.fields.get(name, ABSENT_FIELD)

    @property
    def speed_mps(self) -> Optional[float]:
        """Canonical speed, or None. None means UNAVAILABLE and never means 0."""
        value = self.get("speed_mps").value
        return float(value) if isinstance(value, (int, float)) else None

    @property
    def rpm(self) -> Optional[float]:
        value = self.get("rpm").value
        return float(value) if isinstance(value, (int, float)) else None

    @property
    def communication_state(self) -> Optional[str]:
        """SUPPLIED link state. Not derived from the vehicle merely existing."""
        value = self.get("communication_state").value
        return None if value is None else str(value)

    def provenance_label(self) -> str:
        """Provenance of this vehicle's speed — the field every view shows."""
        return self.get("speed_mps").provenance_label()

    def freshness_label(self) -> str:
        return self.get("speed_mps").freshness_label()


def _parse_field(raw: Any) -> CanonicalField:
    if not isinstance(raw, dict):
        return ABSENT_FIELD
    age = raw.get("age_s")
    return CanonicalField(
        value=raw.get("value"),
        source=raw.get("source"),
        origin=raw.get("origin"),
        quality=raw.get("quality"),
        freshness=raw.get("freshness"),
        age_s=float(age) if isinstance(age, (int, float)) else None,
        available=bool(raw.get("available", raw.get("value") is not None)),
    )


def parse_snapshot(payload: Any) -> Dict[str, CanonicalVehicle]:
    """
    PURE. Turn a Twin snapshot payload into canonical vehicles.

    Tolerates a malformed or partial payload by returning fewer vehicles rather
    than raising: a visualiser must not crash because one packet was bad (root
    CLAUDE.md §16). What it must never do is invent a vehicle or a field.
    """
    if not isinstance(payload, dict):
        return {}
    vehicles = payload.get("vehicles")
    if not isinstance(vehicles, dict):
        return {}

    parsed: Dict[str, CanonicalVehicle] = {}
    for vehicle_id, body in vehicles.items():
        if not isinstance(body, dict):
            continue
        dynamic = body.get("dynamic")
        fields: Dict[str, CanonicalField] = {}
        if isinstance(dynamic, dict):
            for name, raw in dynamic.items():
                fields[name] = _parse_field(raw)
        parsed[str(vehicle_id)] = CanonicalVehicle(vehicle_id=str(vehicle_id), fields=fields)
    return parsed


def snapshot_is_empty(payload: Any, block: str) -> bool:
    """
    Whether a top-level snapshot block carries nothing.

    Used to report LIVE limitations honestly: `environment`, `roads` and `mine`
    come back empty from the live backend, and the caller must say UNAVAILABLE
    rather than draw an empty mine that reads like a mine with no hazards.
    """
    if not isinstance(payload, dict):
        return True
    value = payload.get(block)
    if isinstance(value, dict):
        if block == "mine":
            return not any(bool(value.get(key)) for key in ("nodes", "adjacency"))
        return len(value) == 0
    return True


class CanonicalTwinClient:
    """
    Polls the backend Twin snapshot on a daemon thread.

    Threaded so a slow or absent backend never blocks the render loop. The render
    loop reads the last parsed result under a lock; when nothing has ever been
    fetched it reads an empty mapping, which the caller renders as UNAVAILABLE.

    NOT A TWIN. It holds a decoded copy of someone else's Twin for display, is
    never written to by the simulator, and is never consulted for a safety
    decision.
    """

    def __init__(
        self,
        url: str = DEFAULT_SNAPSHOT_URL,
        timeout_s: float = DEFAULT_TIMEOUT_S,
        poll_interval_s: float = DEFAULT_POLL_INTERVAL_S,
        opener=None,
    ):
        self.url = url
        self.timeout_s = float(timeout_s)
        self.poll_interval_s = float(poll_interval_s)
        # Injectable so the contract is testable without a socket.
        self._opener = opener or self._urlopen
        self._lock = threading.Lock()
        self._vehicles: Dict[str, CanonicalVehicle] = {}
        self._payload: Optional[dict] = None
        self._connected = False
        self._error: Optional[str] = None
        self._stop = threading.Event()
        self._thread: Optional[threading.Thread] = None

    # -- transport ---------------------------------------------------------

    def _urlopen(self, url: str, timeout: float) -> bytes:
        with urllib.request.urlopen(url, timeout=timeout) as response:  # noqa: S310
            return response.read()

    def fetch_once(self) -> bool:
        """
        One GET. Returns whether it succeeded. NEVER raises, and never clears the
        last good data on failure — a stale canonical reading, honestly labelled,
        is more useful than a blank panel, and the freshness comes from the Twin.
        """
        try:
            raw = self._opener(self.url, self.timeout_s)
            payload = json.loads(raw)
            vehicles = parse_snapshot(payload)
        except (urllib.error.URLError, OSError, ValueError, TypeError) as exc:
            with self._lock:
                self._connected = False
                self._error = str(exc)[:120]
            return False

        with self._lock:
            self._vehicles = vehicles
            self._payload = payload if isinstance(payload, dict) else None
            self._connected = True
            self._error = None
        return True

    # -- lifecycle ---------------------------------------------------------

    def start(self) -> None:
        """Begin polling. Idempotent."""
        if self._thread is not None:
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._loop, name="canonical-twin", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        thread = self._thread
        self._thread = None
        if thread is not None:
            thread.join(timeout=2.0)

    def _loop(self) -> None:
        while not self._stop.is_set():
            self.fetch_once()
            self._stop.wait(self.poll_interval_s)

    # -- read model --------------------------------------------------------

    @property
    def connected(self) -> bool:
        """Whether the LAST fetch succeeded. A transport fact, not a data fact."""
        with self._lock:
            return self._connected

    @property
    def error(self) -> Optional[str]:
        with self._lock:
            return self._error

    def vehicles(self) -> Dict[str, CanonicalVehicle]:
        with self._lock:
            return dict(self._vehicles)

    def vehicle(self, vehicle_id: str) -> Optional[CanonicalVehicle]:
        """The canonical vehicle, or None when the Twin does not carry it."""
        with self._lock:
            return self._vehicles.get(vehicle_id)

    def block_is_empty(self, block: str) -> bool:
        """Whether `environment` / `roads` / `mine` came back empty."""
        with self._lock:
            payload = self._payload
        return snapshot_is_empty(payload, block)

    def status_text(self) -> str:
        """One line for the panel header. Says what is true, including 'no backend'."""
        with self._lock:
            connected, count = self._connected, len(self._vehicles)
        if not connected:
            return "CANONICAL TWIN UNAVAILABLE — no backend snapshot"
        return "CANONICAL TWIN — %d vehicle(s)" % count
