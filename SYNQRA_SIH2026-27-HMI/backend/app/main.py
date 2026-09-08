"""FOG-ORCHESTRATOR 2.0 — Task 1 HMI backend.

Supervisory HMI Backend with independent REST and WebSocket telemetry capabilities.

Scope boundary (see `CLAUDE.md`, `requirements/DECISIONS.md` PAD-A/B/E):
This process performs NO Digital Twin computation, NO physics, NO prediction,
NO optimization, and NO simulation. It acts as an independent HMI supervisor.
"""

import time
import json
import logging
import math
import asyncio
from datetime import datetime, timezone
from collections import deque
from typing import Dict, Any, List, Optional
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from app.config import settings
from app.schemas.health import SERVICE_VERSION, HealthResponse

app = FastAPI(
    title="FOG-ORCHESTRATOR 2.0 — Task 1 HMI backend",
    version=SERVICE_VERSION,
    summary="Supervisory HMI backend. Advisory only; performs no safety computation.",
)

# P9 - SECURITY REVIEW: CORS.
#
# This was `allow_origins=["*"], allow_methods=["*"]` while `app/config.py` already
# carried a configured origin list that only the (superseded) skeleton backend used. A
# wildcard on a service that exposes POST /api/telemetry and POST /api/commands lets any
# page the operator happens to have open drive the ingress.
#
# BEHAVIOUR CHANGE, and how to undo it: the allowed origins now come from
# `HMI_CORS_ORIGINS` (default `http://localhost:5173,http://127.0.0.1:5173`). A LAN demo
# served from another host must list that origin, e.g.
#     HMI_CORS_ORIGINS=http://192.168.4.2:5173
# or set `HMI_CORS_ORIGINS=*` to restore the previous wildcard explicitly.
_cors_origins = settings.cors_origin_list
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=False,
    # Only the verbs this API actually serves. OPTIONS is handled by the middleware.
    allow_methods=["GET", "POST"] if _cors_origins != ["*"] else ["*"],
    allow_headers=["*"],
)


# In-memory storage for independent HMI vehicle states and command history
vehicle_telemetry_store: Dict[str, Dict[str, Any]] = {}
command_history: List[Dict[str, Any]] = []
active_websockets: List[WebSocket] = []


class HMICommandRequest(BaseModel):
    command_id: str = Field(..., description="Unique command ID")
    vehicle_id: str = Field(..., description="Target vehicle ID")
    action: str = Field(..., description="Action: TARGET_SPEED, HOLD, STOP, RELEASE")
    target_speed: float = Field(0.0, description="Target speed in m/s")
    reason: str = Field("HMI_OPERATOR_DISPATCH", description="Dispatch reason")


class HMICommandResponse(BaseModel):
    command_id: str
    vehicle_id: str
    action: str
    status: str
    timestamp: float
    message: str


class HardwareTelemetryPayload(BaseModel):
    vehicle_id: str = Field(..., description="Target vehicle ID (TRUCK_01 or TRUCK_02)")
    sequence: int = Field(..., description="Sequence number")
    rpm: float = Field(0.0, description="Wheel RPM")
    speed: Any = Field(None, description="Linear speed in m/s (null if uncalibrated)")
    ax: float = Field(0.0, description="Acceleration X")
    ay: float = Field(0.0, description="Acceleration Y")
    az: float = Field(0.0, description="Acceleration Z")
    gx: float = Field(0.0, description="Gyroscope X")
    gy: float = Field(0.0, description="Gyroscope Y")
    gz: float = Field(0.0, description="Gyroscope Z")
    accel_x: Any = Field(None, description="Physical relay acceleration X alias")
    accel_y: Any = Field(None, description="Physical relay acceleration Y alias")
    accel_z: Any = Field(None, description="Physical relay acceleration Z alias")
    gyro_x: Any = Field(None, description="Physical relay gyroscope X alias")
    gyro_y: Any = Field(None, description="Physical relay gyroscope Y alias")
    gyro_z: Any = Field(None, description="Physical relay gyroscope Z alias")
    rssi: int = Field(-75, description="RSSI in dBm")
    snr: float = Field(9.5, description="SNR in dB")
    source: str = Field(..., description="Source path: DIRECT_WIFI or V2V_VIA_TRUCK_02")
    timestamp: float = Field(default_factory=time.time, description="Source timestamp")

    @property
    def effective_ax(self) -> float:
        return float(self.accel_x) if self.accel_x is not None else float(self.ax)

    @property
    def effective_ay(self) -> float:
        return float(self.accel_y) if self.accel_y is not None else float(self.ay)

    @property
    def effective_az(self) -> float:
        return float(self.accel_z) if self.accel_z is not None else float(self.az)

    @property
    def effective_gx(self) -> float:
        return float(self.gyro_x) if self.gyro_x is not None else float(self.gx)

    @property
    def effective_gy(self) -> float:
        return float(self.gyro_y) if self.gyro_y is not None else float(self.gy)

    @property
    def effective_gz(self) -> float:
        return float(self.gyro_z) if self.gyro_z is not None else float(self.gz)


# =====================================================================
# P3 — CANONICAL DIGITAL TWIN INGESTION
#
# Telemetry accepted by this backend is forwarded to the canonical TwinStateStore through
# the single ingestion boundary in `telemetry_ingest.py`.
#
# TRANSITIONAL: `vehicle_telemetry_store` above remains as the backend's own cache so the
# existing REST/WebSocket API keeps behaving exactly as before. It is NOT a second Digital
# Twin and must not become one - the Twin->HMI migration is P6, not P3.
#
# The import is optional so this backend still starts when the Twin package is not on the
# path (it lives in the sibling SYNQRA_SIH2026-27-main tree).
# =====================================================================

twin_store = None
twin_ingestor = None
command_gateway = None


class _FallbackTransport:
    """Placeholder used when the ingestion package is unavailable (ingestion is refused anyway)."""

    EMULATOR = "EMULATOR"


IngestTransport = _FallbackTransport
build_twin_snapshot = None
build_vehicle_projection = None
try:  # pragma: no cover - exercised via the root test suite
    import os as _os
    import sys as _sys

    _workspace_root = _os.path.abspath(_os.path.join(_os.path.dirname(__file__), "..", "..", ".."))
    _twin_root = _os.path.join(_workspace_root, "SYNQRA_SIH2026-27-main")
    for _p in (_workspace_root, _twin_root):
        if _p not in _sys.path:
            _sys.path.insert(0, _p)

    from telemetry_ingest import TelemetryIngestor  # noqa: E402
    from telemetry_ingest import Transport as _IngestTransport  # noqa: E402
    from twin.twin_state_store import TwinMode, TwinStateStore  # noqa: E402

    from integration_adapters.config_paths import load_timeouts as _load_timeouts  # noqa: E402

    _timeouts = _load_timeouts()
    # P9: configured, not a literal. The same `max_telemetry_age_seconds` decides
    # staleness in the Twin, in the command gateway, and in this backend's own views.
    twin_store = TwinStateStore(
        mode=TwinMode.HYBRID, stale_after_s=_timeouts["max_telemetry_age_seconds"]
    )
    twin_ingestor = TelemetryIngestor(twin_store)

    from command_gateway import CommandGateway  # noqa: E402
    from twin_projection import build_twin_snapshot as _build_twin_snapshot  # noqa: E402
    from twin_projection import build_vehicle_projection as _build_vehicle_projection  # noqa: E402

    command_gateway = CommandGateway(store=twin_store)
    IngestTransport = _IngestTransport
    build_twin_snapshot = _build_twin_snapshot
    build_vehicle_projection = _build_vehicle_projection
except Exception as _exc:  # noqa: BLE001 - the HMI must start with or without the Twin
    import logging as _logging

    _logging.getLogger("hmi.backend").warning(
        "Canonical Twin ingestion unavailable (%s); backend cache only.", _exc
    )


async def broadcast_twin_update(vehicle_id: str) -> None:
    """
    Push the canonical projection of one vehicle to every connected client.

    Broadcast happens on a meaningful Twin change (an accepted telemetry packet), not on a
    polling loop. A dead or failing client is dropped, never allowed to kill the loop.
    """
    if twin_store is None or build_vehicle_projection is None or not active_websockets:
        return
    try:
        projection = build_vehicle_projection(twin_store, vehicle_id)
        if projection is None:
            return
        message = json.dumps({"type": "twin_vehicle_update", "data": projection})
    except Exception:  # noqa: BLE001 - serialization failure must not break ingestion
        logging.getLogger("hmi.backend").exception("Twin projection/serialization failed")
        return

    stale = []
    for client in list(active_websockets):
        try:
            await client.send_text(message)
        except Exception:  # noqa: BLE001
            stale.append(client)
    for client in stale:
        if client in active_websockets:
            active_websockets.remove(client)


def forward_to_twin(payload: Dict[str, Any], is_simulated: bool) -> bool:
    """
    Forward one telemetry payload into the canonical Twin.

    Returns True only when the canonical boundary ACCEPTED the packet, so callers can
    broadcast on a real Twin change rather than on every POST. A duplicate, out-of-order
    or invalid packet changes nothing, and re-broadcasting unchanged state on one would
    be noise the HMI cannot distinguish from a genuine update.

    Never raises: a Twin-side problem must not turn a working telemetry POST into a 500,
    and one malformed packet must not corrupt Twin state (the ingestor validates before
    it writes, and writes atomically).
    """
    if twin_ingestor is None:
        return False
    try:
        result = twin_ingestor.ingest_http_payload(payload, is_simulated=is_simulated)
        return bool(getattr(result, "accepted", False))
    except Exception:  # noqa: BLE001
        import logging as _logging

        _logging.getLogger("hmi.backend").exception("Twin ingestion failed; backend cache unaffected")
        return False


# Mode Configuration: 'MOCK' or 'HARDWARE'
HMI_MODE: str = "MOCK"

# Wall-clock time of the last packet accepted on the PHYSICAL ingress
# (`/api/hardware/telemetry`). `None` means this process has never seen one.
#
# P9 - HARDWARE STATUS HONESTY
#   `HMI_MODE` is sticky: one hardware packet used to flip it to "LIVE" for the whole
#   life of the process, so `/api/mode` kept reporting LIVE long after the ESP32 was
#   unplugged. Mode is now reported from EVIDENCE - a hardware packet inside
#   `HARDWARE_PRESENCE_TIMEOUT_S` - not from a latch that never clears.
last_hardware_packet_at: float | None = None

# P9 - CONFIGURED FRESHNESS, NOT LITERALS.
# These were re-typed as 3.0 / 10.0 at four points in this file. They come from
# `config/integration_config.json` via the shared loader; the fallbacks inside that
# loader are the same values the file ships with.
try:
    from integration_adapters.config_paths import load_timeouts as _cfg_timeouts

    _T = _cfg_timeouts()
except Exception:  # noqa: BLE001 - the HMI must start even without the adapter package
    _T = {"max_telemetry_age_seconds": 3.0, "offline_threshold_seconds": 10.0}

STALE_THRESHOLD_S: float = float(_T["max_telemetry_age_seconds"])
OFFLINE_THRESHOLD_S: float = float(_T["offline_threshold_seconds"])

# A hardware link is only claimed while a physical packet is this recent. Reuses the
# configured offline threshold; it is not a new invented constant.
HARDWARE_PRESENCE_TIMEOUT_S: float = OFFLINE_THRESHOLD_S

# D005: Application-level request body size boundary for /api/telemetry.
# Prevents oversized payloads from poisoning the cache or WS broadcast.
MAX_TELEMETRY_BODY_BYTES = 65536  # 64 KiB

# D005: Only these fields are extracted from POST /api/telemetry payloads.
# Unknown keys are silently discarded — they never enter the cache, Twin, or broadcast.
TELEMETRY_ALLOWLIST = frozenset({
    "vehicle_id", "sequence_number", "sequence", "rpm", "speed", "speed_mps",
    "speed_value", "acceleration", "gyroscope", "communication",
    "communication_state", "communication_status", "data_quality",
    "rssi", "snr", "timestamp", "source_timestamp",
})


async def _read_bounded_body(request: Request, max_bytes: int) -> bytes:
    """
    Read request body with a hard size boundary.

    Accumulates at most `max_bytes` of body data via the ASGI stream. Once the
    limit is exceeded, raises HTTP 413 immediately — no JSON parsing, no cache
    mutation, no Twin mutation, no broadcast of the rejected payload.

    Under a real ASGI server (uvicorn), body arrives in network-sized chunks, so
    this stops accepting data as soon as any chunk pushes the total past the
    limit. Under TestClient the body is delivered in a single chunk, but the
    invariant holds: nothing downstream executes after rejection.
    """
    chunks: list[bytes] = []
    total = 0
    async for chunk in request.stream():
        total += len(chunk)
        if total > max_bytes:
            raise HTTPException(
                status_code=413,
                detail=f"Request body exceeds {max_bytes} byte limit"
            )
        chunks.append(chunk)
    return b"".join(chunks)


def hardware_link_state(now: float) -> Dict[str, Any]:
    """
    What this process can HONESTLY say about the physical link.

    Never claims a hardware link on the strength of a client-declared field: only a packet
    that actually arrived on the physical ingress counts.
    """
    # `HMI_MODE` is the latch ("this process has seen hardware") and
    # `last_hardware_packet_at` is the freshness. BOTH must hold to claim a link, so
    # resetting either one back to MOCK honestly clears the claim.
    if last_hardware_packet_at is None or HMI_MODE != "LIVE":
        return {"hardware_seen": False, "hardware_connected": False, "age_seconds": None}
    age = now - last_hardware_packet_at
    return {
        "hardware_seen": True,
        "hardware_connected": age <= HARDWARE_PRESENCE_TIMEOUT_S,
        "age_seconds": round(age, 2),
    }

# Deduplication and sequence history tracking
# D006: per-vehicle bounded dedup. last_sequence_by_vehicle controls ordering;
# the bounded store only caps duplicate-history memory.
_MAX_DEDUP_PER_VEHICLE = 1000


class _BoundedDedupStore:
    """Per-vehicle bounded dedup store with O(1) lookup.

    Stores the last N accepted payloads per vehicle for duplicate detection
    and source-upgrade. Old entries are evicted FIFO. Ordering decisions
    use last_sequence_by_vehicle, not this store.
    """

    def __init__(self, maxlen: int = _MAX_DEDUP_PER_VEHICLE):
        self._maxlen = maxlen
        self._store: Dict[str, Dict[int, Dict[str, Any]]] = {}  # vid -> {seq -> payload}
        self._order: Dict[str, deque] = {}                       # vid -> deque of seq

    def __contains__(self, key: str) -> bool:
        """Check if a 'vid_seq' key is tracked."""
        vid, seq = self._parse_key(key)
        return seq in self._store.get(vid, {})

    def get(self, key: str, default: Any = None) -> Any:
        vid, seq = self._parse_key(key)
        return self._store.get(vid, {}).get(seq, default)

    def add(self, vid: str, seq: int, payload: Dict[str, Any]) -> None:
        if vid not in self._store:
            self._store[vid] = {}
            self._order[vid] = deque(maxlen=self._maxlen)
        order = self._order[vid]
        store = self._store[vid]
        if len(order) == self._maxlen:
            evicted = order[0]
            store.pop(evicted, None)
        order.append(seq)
        store[seq] = payload

    def __getitem__(self, key: str) -> Any:
        vid, seq = self._parse_key(key)
        val = self._store.get(vid, {}).get(seq)
        if val is None:
            raise KeyError(key)
        return val

    def __setitem__(self, key: str, payload: Dict[str, Any]) -> None:
        vid, seq = self._parse_key(key)
        self.add(vid, seq, payload)

    def __iter__(self):
        for vid, seqs in self._store.items():
            for seq in seqs:
                yield f"{vid}_{seq}"

    def keys(self):
        return [f"{vid}_{seq}" for vid, seqs in self._store.items() for seq in seqs]

    def values(self):
        return [payload for seqs in self._store.values() for payload in seqs.values()]

    def items(self):
        return [(f"{vid}_{seq}", payload) for vid, seqs in self._store.items() for seq, payload in seqs.items()]

    def update(self, other: Any) -> None:
        items = other.items() if hasattr(other, "items") else other
        for k, v in items:
            self[k] = v

    def __len__(self) -> int:
        return sum(len(seqs) for seqs in self._store.values())

    def clear(self) -> None:
        self._store.clear()
        self._order.clear()

    def clear_vehicle(self, vid: str) -> None:
        self._store.pop(vid, None)
        self._order.pop(vid, None)

    @staticmethod
    def _parse_key(key: str):
        parts = key.rsplit("_", 1)
        return parts[0], int(parts[1])


deduplication_store = _BoundedDedupStore()
last_sequence_by_vehicle: Dict[str, int] = {}


@app.get("/api/health", response_model=HealthResponse, tags=["health"])
def get_health() -> HealthResponse:
    """Liveness of this service. Used by the frontend as its connectivity proof."""
    return HealthResponse()


@app.get("/api/mode", tags=["config"])
def get_mode() -> Dict[str, Any]:
    """Returns current operating mode (MOCK or LIVE)."""
    now = time.time()
    link = hardware_link_state(now)
    # LIVE means "a physical packet arrived recently", not "a physical packet arrived once".
    active_mode = "LIVE" if link["hardware_connected"] else "MOCK"
    return {
        "mode": active_mode,
        "status": "ACTIVE",
        "hardware_seen": link["hardware_seen"],
        "hardware_connected": link["hardware_connected"],
        "hardware_age_seconds": link["age_seconds"],
    }


@app.get("/api/observability", tags=["health"])
def get_observability() -> Dict[str, Any]:
    """
    Operational counters for the canonical data paths.

    WHY THIS EXISTS (P9)
        The ingestion boundary and the command gateway have kept accept/reject counters
        since P3/P5, but nothing exposed them, so a rejection storm was invisible to
        anyone not reading the process log. This endpoint reports what those components
        already count. It computes nothing and asserts nothing about hardware it has not
        seen.

    HONESTY
        A component that is not wired reports `null`, never zero - "not measured" and
        "measured zero" are different answers, and the difference matters here.
    """
    now = time.time()
    link = hardware_link_state(now)
    return {
        "service": "hmi-backend",
        "timestamp": now,
        "twin_attached": twin_store is not None,
        "twin_vehicle_count": len(twin_store.get_state_snapshot().get("vehicles", {}))
        if twin_store is not None else None,
        "telemetry_ingest": dict(twin_ingestor.stats) if twin_ingestor is not None else None,
        "command_gateway": dict(command_gateway.stats) if command_gateway is not None else None,
        "backend_cache_vehicles": len(vehicle_telemetry_store),
        "websocket_clients": len(active_websockets),
        "command_history_length": len(command_history),
        "hardware": link,
        "mode": "LIVE" if link["hardware_connected"] else "MOCK",
    }


@app.get("/api/vehicles", tags=["telemetry"])
def get_vehicles() -> Dict[str, Any]:
    """Returns currently registered vehicle states and staleness status."""
    now = time.time()
    result = {}
    has_active_live = False

    for vid, data in vehicle_telemetry_store.items():
        ts = data.get("timestamp", now)
        age = now - ts
        
        stale_thresh = data.get("stale_threshold_s", STALE_THRESHOLD_S)
        offline_thresh = data.get("offline_threshold_s", OFFLINE_THRESHOLD_S)

        if data.get("data_quality") == "LIVE" and age <= offline_thresh:
            has_active_live = True
        
        if age <= stale_thresh:
            comm_status = "ONLINE"
            comm_state = "HEALTHY"
            safety_state = data.get("safety_state", "NORMAL")
            is_stale = False
        elif age <= offline_thresh:
            comm_status = "STALE"
            comm_state = "COMMUNICATION_DEGRADED"
            safety_state = "COMMUNICATION_DEGRADED"
            is_stale = True
        else:
            comm_status = "OFFLINE"
            comm_state = "COMMUNICATION_DEGRADED"
            safety_state = "COMMUNICATION_DEGRADED"
            is_stale = True
        
        veh_copy = dict(data)
        veh_copy["is_stale"] = is_stale
        veh_copy["communication_status"] = comm_status
        veh_copy["communication_state"] = comm_state
        veh_copy["safety_state"] = safety_state
        veh_copy["age_seconds"] = round(age, 2)

        # D007: Twin-derived state is authoritative whenever twin_store exists.
        # Cache is compatibility fallback only when Twin is genuinely unavailable (twin_store is None).
        if twin_store is not None:
            try:
                if build_vehicle_projection is not None:
                    proj = build_vehicle_projection(twin_store, vid)
                    if proj is not None and "dynamic" in proj:
                        dyn = proj["dynamic"]
                        if "communication_state" in dyn and dyn["communication_state"].get("value") is not None:
                            twin_field = dyn["communication_state"]
                            twin_val = twin_field.get("value")
                            twin_qual = twin_field.get("quality")
                            if twin_qual == "STALE" or is_stale or twin_val == "COMMUNICATION_DEGRADED":
                                veh_copy["communication_state"] = "COMMUNICATION_DEGRADED"
                                if veh_copy["communication_status"] == "ONLINE":
                                    veh_copy["communication_status"] = "STALE"
                            else:
                                veh_copy["communication_state"] = twin_val
                                veh_copy["communication_status"] = "ONLINE"
                else:
                    logging.getLogger("hmi.backend").error(
                        "Twin projection function is unavailable while twin_store is present for vehicle '%s'", vid
                    )
                    veh_copy["communication_state"] = "COMMUNICATION_DEGRADED"
                    if veh_copy.get("communication_status") == "ONLINE":
                        veh_copy["communication_status"] = "STALE"
                    veh_copy["safety_state"] = "COMMUNICATION_DEGRADED"
                    veh_copy["is_stale"] = True
            except Exception as exc:
                logging.getLogger("hmi.backend").error(
                    "Twin projection failed for vehicle '%s': %s", vid, exc, exc_info=True
                )
                # D007: Do not disguise internal Twin projection failure as valid cache state.
                # Return safe deterministic response based on canonical Twin availability contract.
                veh_copy["communication_state"] = "COMMUNICATION_DEGRADED"
                if veh_copy.get("communication_status") == "ONLINE":
                    veh_copy["communication_status"] = "STALE"
                veh_copy["safety_state"] = "COMMUNICATION_DEGRADED"
                veh_copy["is_stale"] = True

        if "communication" in veh_copy and isinstance(veh_copy["communication"], dict):
            comm_sub = dict(veh_copy["communication"])
            comm_sub["status"] = veh_copy["communication_status"]
            veh_copy["communication"] = comm_sub
        
        result[vid] = veh_copy

    # `has_active_live` above describes individual records; the PROCESS mode is decided by
    # the physical ingress alone (P9), so a stale hardware link reports MOCK again.
    active_mode = "LIVE" if hardware_link_state(now)["hardware_connected"] else "MOCK"
    return {"vehicles": result, "count": len(result), "mode": active_mode, "timestamp": now}


@app.post("/api/telemetry", tags=["telemetry"])
async def ingest_telemetry(request: Request) -> Dict[str, Any]:
    """Ingests vehicle telemetry payload from mock telemetry generator or external source."""
    # D005: bounded receive — reject oversized body BEFORE any parsing/mutation
    raw_body = await _read_bounded_body(request, MAX_TELEMETRY_BODY_BYTES)

    try:
        payload = json.loads(raw_body)
    except (json.JSONDecodeError, UnicodeDecodeError):
        raise HTTPException(status_code=400, detail="Malformed JSON body")

    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="Expected JSON object")

    vid = payload.get("vehicle_id")
    if not vid:
        raise HTTPException(status_code=400, detail="vehicle_id is required")

    # GAP 1 & GAP 2: speed type and value validation BEFORE cache/Twin/broadcast mutation
    speed_raw = None
    speed_present = False
    for k in ("speed", "speed_mps", "speed_value"):
        if k in payload:
            speed_present = True
            speed_raw = payload[k]
            break

    if speed_present and speed_raw is not None:
        if isinstance(speed_raw, bool) or not isinstance(speed_raw, (int, float)):
            raise HTTPException(status_code=400, detail="Invalid speed: must be a numeric value")
        if not math.isfinite(speed_raw):
            raise HTTPException(status_code=400, detail="Invalid speed: must be finite")
        if speed_raw < 0.0:
            raise HTTPException(status_code=400, detail="Invalid speed: negative speed is invalid")

    # Protection: Active LIVE hardware telemetry takes precedence over mock updates
    existing = vehicle_telemetry_store.get(vid)
    if existing and existing.get("data_quality") == "LIVE":
        age = time.time() - existing.get("timestamp", 0)
        if age <= 10.0:
            # D004: mock overwrite attempt → 409 Conflict
            return JSONResponse(status_code=409, content={
                "status": "IGNORED_MOCK_OVERWRITE",
                "vehicle_id": vid,
                "timestamp": time.time(),
                "message": "Active LIVE hardware telemetry stream has precedence over mock telemetry"
            })

    # D005: allowlist — only canonical telemetry fields are extracted.
    # Unknown keys are discarded. Raw payload is never stored.
    canonical = {k: v for k, v in payload.items() if k in TELEMETRY_ALLOWLIST}
    canonical["received_at"] = time.time()
    # P9 - PROVENANCE IS DECIDED BY THE TRANSPORT, NOT BY THE SENDER.
    # This endpoint is the mock/simulated ingress. A caller could previously post
    # `data_quality: "LIVE"` and have the whole backend treat its packet as physical
    # telemetry: `/api/mode` reported LIVE, `/api/vehicles` labelled it LIVE, and it
    # locked out later mock updates. That is the same hole P5.1 closed on the WebSocket.
    canonical["data_quality"] = "SIMULATED"
    vehicle_telemetry_store[vid] = canonical

    # P3: /api/telemetry carries mock/simulated telemetry, so it enters the Twin as
    # SIMULATION. It must never be recorded as a physical measurement.
    twin_accepted = forward_to_twin(canonical, is_simulated=True)

    # Broadcast the CANONICAL Twin projection, exactly as /api/hardware/telemetry does.
    #
    # Without this the simulated ingress updated the Twin but emitted no
    # `twin_vehicle_update` frame. The HMI deliberately ignores the legacy
    # `telemetry_update` below (it used to carry fabricated position/friction), so its
    # vehicle slice was filled once from `connection_established` at page load and never
    # updated again - a frozen, apparently-stale reading while the Twin was current.
    #
    # Emitted BEFORE the legacy frame so both ingresses put the authoritative projection
    # first. `broadcast_twin_update` no-ops when the Twin is unavailable and never raises.
    #
    # Only on a real Twin change: a duplicate/out-of-order/invalid packet leaves Twin
    # state untouched, and re-broadcasting it would look to the HMI like a fresh update.
    if twin_accepted:
        await broadcast_twin_update(vid)

    # Broadcast to active WebSockets
    message_json = json.dumps({"type": "telemetry_update", "data": canonical})
    disconnected = []
    for ws in active_websockets:
        try:
            await ws.send_text(message_json)
        except Exception:
            disconnected.append(ws)
    for ws in disconnected:
        if ws in active_websockets:
            active_websockets.remove(ws)
            
    return {"status": "INGESTED", "vehicle_id": vid, "timestamp": canonical["received_at"]}


@app.post("/api/hardware/telemetry", tags=["telemetry"])
async def ingest_hardware_telemetry(payload: HardwareTelemetryPayload) -> Dict[str, Any]:
    """
    Ingests canonical vehicle telemetry from physical Wi-Fi Direct or V2V relay paths.
    Enforces deduplication by (vehicle_id, sequence), source priority (DIRECT_WIFI > V2V_VIA_TRUCK_02),
    and sequence continuity.
    """
    global HMI_MODE, last_hardware_packet_at

    vid = payload.vehicle_id.upper()
    if vid not in ["TRUCK_01", "TRUCK_02"]:
        raise HTTPException(status_code=400, detail=f"Invalid vehicle_id '{vid}'. Must be TRUCK_01 or TRUCK_02")

    source_val = payload.source.upper()
    if source_val not in ["DIRECT_WIFI", "V2V_VIA_TRUCK_02"]:
        raise HTTPException(status_code=400, detail=f"Invalid source '{source_val}'. Must be DIRECT_WIFI or V2V_VIA_TRUCK_02")

    # D001: Reject invalid RPM BEFORE any clamping/canonicalization.
    # NaN, ±Inf, and negative RPM must not be laundered into 0.0.
    # Valid RPM == 0.0 (motor stopped) is permitted.
    if not math.isfinite(payload.rpm) or payload.rpm < 0:
        raise HTTPException(status_code=422, detail=f"Invalid RPM value: {payload.rpm}")

    # GAP 1 & GAP 2: speed validation on hardware telemetry
    if payload.speed is not None:
        if isinstance(payload.speed, bool) or not isinstance(payload.speed, (int, float)):
            raise HTTPException(status_code=422, detail=f"Invalid speed type: {type(payload.speed)}")
        if not math.isfinite(payload.speed):
            raise HTTPException(status_code=422, detail=f"Non-finite speed: {payload.speed}")
        if payload.speed < 0:
            raise HTTPException(status_code=422, detail=f"Negative speed: {payload.speed}")

    # Only a VALIDATED physical packet is evidence of a hardware link (P9). A rejected
    # payload must not make the process claim hardware is connected.
    HMI_MODE = "LIVE"
    last_hardware_packet_at = time.time()

    dedup_key = f"{vid}_{payload.sequence}"
    is_duplicate = dedup_key in deduplication_store

    now = time.time()
    last_seq = last_sequence_by_vehicle.get(vid, 0)
    is_out_of_order = (payload.sequence < last_seq) and not is_duplicate

    if is_out_of_order:
        # D004: out-of-order → 409 Conflict
        return JSONResponse(status_code=409, content={
            "status": "REJECTED_OUT_OF_ORDER",
            "vehicle_id": vid,
            "sequence": payload.sequence,
            "last_sequence": last_seq,
            "is_duplicate": False,
            "message": f"Sequence {payload.sequence} is older than last seen {last_seq}"
        })

    # Store deduplication record
    existing_rec = deduplication_store.get(dedup_key)
    if is_duplicate and existing_rec:
        if source_val == "DIRECT_WIFI" and existing_rec.get("source") != "DIRECT_WIFI":
            existing_rec["source"] = "DIRECT_WIFI"
            if vid in vehicle_telemetry_store:
                vehicle_telemetry_store[vid]["source"] = "DIRECT_WIFI"
                vehicle_telemetry_store[vid]["primary_source"] = "DIRECT_WIFI"

        # D004: duplicate → 409 Conflict
        return JSONResponse(status_code=409, content={
            "status": "ACCEPTED_DUPLICATE",
            "vehicle_id": vid,
            "sequence": payload.sequence,
            "source": source_val,
            "is_duplicate": True,
            "communication_status": "ONLINE"
        })

    if payload.sequence > last_seq:
        last_sequence_by_vehicle[vid] = payload.sequence
    deduplication_store.add(vid, payload.sequence, payload.model_dump())

    ax_raw = payload.effective_ax
    ay_raw = payload.effective_ay
    az_raw = payload.effective_az
    gx_raw = payload.effective_gx
    gy_raw = payload.effective_gy
    gz_raw = payload.effective_gz

    accel_scale = 16384.0 if abs(az_raw) > 100 else 1.0
    gyro_scale = 131.0 if abs(gx_raw) > 10 else 1.0

    ax_phys = round((ax_raw / accel_scale) * (9.81 if accel_scale > 1 else 1.0), 3)
    ay_phys = round((ay_raw / accel_scale) * (9.81 if accel_scale > 1 else 1.0), 3)
    az_phys = round((az_raw / accel_scale) * (9.81 if accel_scale > 1 else 1.0), 3)

    gx_phys = round((gx_raw / gyro_scale) * ((3.14159 / 180.0) if gyro_scale > 1 else 1.0), 4)
    gy_phys = round((gy_raw / gyro_scale) * ((3.14159 / 180.0) if gyro_scale > 1 else 1.0), 4)
    gz_phys = round((gz_raw / gyro_scale) * ((3.14159 / 180.0) if gyro_scale > 1 else 1.0), 4)

    canonical_record = {
        "vehicle_id": vid,
        "source": source_val,
        "primary_source": source_val,
        "sequence_number": payload.sequence,
        "rpm": payload.rpm,
        "speed": payload.speed,
        "speed_value": 0.0 if payload.speed is None else float(payload.speed),
        "speed_unit": "m/s",
        "speed_calibrated": False,
        "acceleration": {
            "x": ax_phys,
            "y": ay_phys,
            "z": az_phys
        },
        "gyroscope": {
            "x": gx_phys,
            "y": gy_phys,
            "z": gz_phys
        },
        "raw_imu": {
            "ax": ax_raw,
            "ay": ay_raw,
            "az": az_raw,
            "gx": gx_raw,
            "gy": gy_raw,
            "gz": gz_raw
        },
        "communication": {
            "status": "ONLINE",
            "last_seen": now,
            "rssi": payload.rssi,
            "snr": payload.snr
        },
        "communication_status": "ONLINE",
        "communication_state": "HEALTHY",
        "safety_state": "NORMAL",
        "data_quality": "LIVE",
        "stale_threshold_s": STALE_THRESHOLD_S,
        "offline_threshold_s": OFFLINE_THRESHOLD_S,
        "timestamp": now,
        "received_at": now
    }

    vehicle_telemetry_store[vid] = canonical_record

    # P3: forward to the canonical Twin. This endpoint is the physical-device path, so the
    # observation is HARDWARE unless the caller declares otherwise.
    forward_to_twin(
        {
            "vehicle_id": vid,
            "sequence_number": payload.sequence,
            "timestamp": now,
            "rpm": canonical_record["rpm"],
            "speed": payload.speed,
            "acceleration": canonical_record["acceleration"],
            "gyroscope": canonical_record["gyroscope"],
            "communication": canonical_record["communication"],
            "communication_state": canonical_record["communication_state"],
            "data_quality": canonical_record["data_quality"],
            "source": source_val,
        },
        is_simulated=False,
    )

    await broadcast_twin_update(vid)

    message_json = json.dumps({"type": "telemetry_update", "data": canonical_record})
    iso_ts = datetime.fromtimestamp(now, tz=timezone.utc).isoformat()
    # ===================================================================
    # P6 - NO FABRICATED VehicleState
    #
    # This block used to hand the HMI an invented vehicle: position x=120/80, y=50,
    # segment SEG_01, friction 0.8, comm_confidence 0.95, grade 0.0. None of those are
    # measured by this prototype, and none of them were in the Twin. It existed only to
    # satisfy `rawVehicleStateSchema`, whose speed/accel/grade/friction/comm_confidence
    # fields are all non-nullable.
    #
    # The envelope is now built ONLY from values the canonical Twin actually holds, and is
    # skipped entirely when the schema's required fields are unavailable. An HMI showing
    # nothing is correct; an HMI showing an invented position is not.
    #
    # CONSEQUENCE (reported, not hidden): a hardware-only vehicle supplies no position,
    # grade, friction or comm confidence, so no legacy VehicleState is emitted for it. The
    # canonical `twin_vehicle_update` projection carries its real state instead. Restoring
    # legacy rendering for hardware-only vehicles needs an additive contract change in
    # `frontend/src/contracts/raw.ts` (nullable fields + provenance), which is deliberately
    # NOT done here - it touches the protected frontend pipeline.
    # ===================================================================
    vstate_json = None
    if twin_store is not None and build_vehicle_projection is not None:
        try:
            projection = build_vehicle_projection(twin_store, vid) or {}
            dynamic = projection.get("dynamic", {})

            def available(field_name):
                field = dynamic.get(field_name)
                return field["value"] if field and field.get("available") else None

            speed_value = available("speed_mps")
            position_value = available("position_s")
            road_value = available("road_id")

            # Every field the frontend schema requires must genuinely exist.
            if speed_value is not None and position_value is not None:
                vstate_json = json.dumps({
                    "type": "VehicleState",
                    "payload": {
                        "vehicle_id": vid,
                        "timestamp": iso_ts,
                        "position": {
                            "x": None,
                            "y": None,
                            "segment_id": road_value,
                            "offset_m": position_value,
                        },
                        "speed_mps": float(speed_value),
                        "accel_mps2": available("acceleration_mps2"),
                        "grade_rad": None,
                        "friction_est": None,
                        "mode": available("state"),
                        "comm_confidence": None,
                        "vehicle_kind": "TRUCK",
                        "route_id": road_value,
                    },
                })
        except Exception:  # noqa: BLE001 - projection issues must not break ingestion
            logging.getLogger("hmi.backend").exception("VehicleState projection failed")
    disconnected = []
    for ws in active_websockets:
        try:
            await ws.send_text(message_json)
            if vstate_json is not None:
                await ws.send_text(vstate_json)
        except Exception:
            disconnected.append(ws)
    for ws in disconnected:
        if ws in active_websockets:
            active_websockets.remove(ws)

    logging.getLogger("hmi.backend").info(
        "[HARDWARE TELEMETRY] vehicle=%s sequence=%d speed=%.2f m/s rpm=%.2f source=%s",
        vid, payload.sequence, canonical_record["speed_value"], payload.rpm, source_val
    )

    return {
        "status": "ACCEPTED",
        "vehicle_id": vid,
        "sequence": payload.sequence,
        "source": source_val,
        "is_duplicate": False,
        "communication_status": "ONLINE"
    }


class HardwareResetRequest(BaseModel):
    vehicle_id: Optional[str] = Field("TRUCK_01", description="Vehicle ID to reset, or empty/null for all vehicles")


@app.post("/api/hardware/reset", tags=["hardware"])
async def reset_hardware_session(req: Optional[HardwareResetRequest] = None) -> Dict[str, Any]:
    """
    Resets the hardware sequence tracking and deduplication store for a vehicle or fleet.
    Allows a newly powered on or rebooted physical ESP32 to establish a fresh sequence lifecycle.
    """
    target_vid = req.vehicle_id.upper() if (req and req.vehicle_id) else None
    targets = [target_vid] if target_vid else (list(last_sequence_by_vehicle.keys()) or ["TRUCK_01", "TRUCK_02"])

    for vid in targets:
        last_sequence_by_vehicle[vid] = 0
        deduplication_store.clear_vehicle(vid)
        if twin_ingestor is not None:
            if hasattr(twin_ingestor, "_last_sequence") and vid in twin_ingestor._last_sequence:
                twin_ingestor._last_sequence[vid] = 0
            if hasattr(twin_ingestor, "_seen_sequences") and vid in twin_ingestor._seen_sequences:
                from telemetry_ingest import BoundedSequenceTracker
                twin_ingestor._seen_sequences[vid] = BoundedSequenceTracker()

    logging.getLogger("hmi.backend").info(
        "[HARDWARE SESSION RESET] Reset sequence and dedup tracking for vehicles: %s", targets
    )

    return {
        "status": "RESET_SUCCESS",
        "vehicles": targets,
        "last_sequence": 0,
        "message": f"Hardware telemetry sequence state reset successfully for {targets}"
    }


@app.get("/api/hardware/sequence", tags=["hardware"])
def get_hardware_sequence(vehicle_id: str = "TRUCK_01") -> Dict[str, Any]:
    """Exposes current sequence synchronization state for a vehicle."""
    vid = vehicle_id.upper()
    last_seq = last_sequence_by_vehicle.get(vid, 0)
    return {
        "vehicle_id": vid,
        "last_sequence": last_seq,
        "next_sequence": last_seq + 1
    }


@app.post("/api/commands", response_model=HMICommandResponse, tags=["command"])
async def post_command(cmd: HMICommandRequest) -> HMICommandResponse:
    """Processes HMI supervisory command (TARGET_SPEED, HOLD, STOP, RELEASE). Rejects duplicate command_id."""
    valid_actions = ["TARGET_SPEED", "HOLD", "STOP", "RELEASE"]
    if cmd.action.upper() not in valid_actions:
        raise HTTPException(status_code=400, detail=f"Invalid action '{cmd.action}'. Must be one of {valid_actions}")

    now = time.time()

    # ---------------------------------------------------------------
    # P5: this endpoint is a COMMAND SUBMISSION PATH, not a vehicle-state author.
    #
    # It no longer writes speed_mps / safety_state / mode into the telemetry store.
    # Accepting a command does not move a truck. The vehicle executes it, reports
    # telemetry, and the Twin updates from that telemetry - that is the only honest
    # order of events.
    #
    # Validation (unknown vehicle, duplicate command_id, staleness, NaN/negative target,
    # v_safe dependency) lives in the canonical CommandGateway.
    # ---------------------------------------------------------------
    if command_gateway is not None:
        from command_gateway import CommandSource, VehicleCommand

        result = command_gateway.submit(
            VehicleCommand(
                vehicle_id=cmd.vehicle_id,
                command_id=cmd.command_id,
                created_at=now,
                action=cmd.action.upper(),
                target_speed_mps=float(cmd.target_speed or 0.0),
                source=CommandSource.OPERATOR,
                reason=cmd.reason,
                mode="HARDWARE" if HMI_MODE == "LIVE" else "SIMULATION",
            )
        )
        record = {
            "command_id": cmd.command_id,
            "vehicle_id": cmd.vehicle_id,
            "action": cmd.action.upper(),
            "target_speed": cmd.target_speed,
            "reason": cmd.reason,
            "timestamp": now,
            "status": result.status,
            "gateway_reason": result.reason,
        }
        command_history.append(record)

        if not result.accepted:
            return HMICommandResponse(
                command_id=cmd.command_id,
                vehicle_id=cmd.vehicle_id,
                action=cmd.action.upper(),
                status=result.status,
                timestamp=now,
                message=result.reason,
            )
    else:
        # Gateway unavailable: preserve the previous duplicate check so the endpoint keeps
        # behaving, but still never author vehicle state.
        if any(c.get("command_id") == cmd.command_id for c in command_history):
            return HMICommandResponse(
                command_id=cmd.command_id,
                vehicle_id=cmd.vehicle_id,
                action=cmd.action.upper(),
                status="REJECTED",
                timestamp=now,
                message=f"Duplicate command_id '{cmd.command_id}' rejected."
            )
        record = {
            "command_id": cmd.command_id,
            "vehicle_id": cmd.vehicle_id,
            "action": cmd.action.upper(),
            "target_speed": cmd.target_speed,
            "reason": cmd.reason,
            "timestamp": now,
            "status": "ACCEPTED"
        }
        command_history.append(record)

    # Broadcast command event to WebSocket subscribers
    broadcast_msg = json.dumps({"type": "command_issued", "data": record})
    disconnected = []
    for ws in active_websockets:
        try:
            await ws.send_text(broadcast_msg)
        except Exception:
            disconnected.append(ws)
    for ws in disconnected:
        if ws in active_websockets:
            active_websockets.remove(ws)

    return HMICommandResponse(
        command_id=cmd.command_id,
        vehicle_id=cmd.vehicle_id,
        action=cmd.action.upper(),
        status="ACCEPTED",
        timestamp=now,
        # ACCEPTED means validated and recorded. It does NOT mean transmitted, acknowledged
        # or executed - those states are only claimed with evidence (P5).
        message=f"Command {cmd.action.upper()} accepted by gateway for {cmd.vehicle_id}; not yet executed"
    )


@app.get("/api/commands/history", tags=["command"])
def get_command_history() -> Dict[str, Any]:
    """Returns history of dispatched HMI commands."""
    return {"commands": command_history, "count": len(command_history)}


@app.get("/api/twin/snapshot", tags=["twin"])
def get_twin_snapshot() -> Dict[str, Any]:
    """
    READ-ONLY projection of canonical Twin state (P6).

    This endpoint never mutates the Twin. Every dynamic field carries its full P4.1
    envelope: value, timestamp, source, origin, quality, age_s, available, clock_domain
    and freshness. Fields the Twin does not hold are absent rather than defaulted.
    """
    if twin_store is None or build_twin_snapshot is None:
        raise HTTPException(status_code=503, detail="Canonical Twin is unavailable")
    return build_twin_snapshot(twin_store)


@app.get("/api/twin/vehicles/{vehicle_id}", tags=["twin"])
def get_twin_vehicle(vehicle_id: str) -> Dict[str, Any]:
    """READ-ONLY projection of one vehicle from canonical Twin state."""
    if twin_store is None or build_vehicle_projection is None:
        raise HTTPException(status_code=503, detail="Canonical Twin is unavailable")
    projection = build_vehicle_projection(twin_store, vehicle_id)
    if projection is None:
        raise HTTPException(status_code=404, detail=f"Unknown vehicle '{vehicle_id}'")
    return projection


@app.websocket("/ws/live")
async def websocket_live_alias(websocket: WebSocket):
    """
    Compatibility alias for the frontend's configured `VITE_LIVE_WS_URL`
    (ws://host/ws/live). Same handler, same single stream - NOT a second state stream.
    """
    await websocket_endpoint(websocket)


@app.websocket("/api/ws")
async def websocket_endpoint(websocket: WebSocket):
    """Independent HMI WebSocket Endpoint for telemetry streaming and command updates."""
    await websocket.accept()
    active_websockets.append(websocket)
    try:
        # Send initial snapshot of registered vehicles
        # Initial state is the canonical Twin projection, not the transitional cache.
        payload = {
            "type": "connection_established",
            "message": "Connected to HMI Independent Backend",
            "vehicles": {},   # D005: never send raw cache; Twin projection is canonical
        }
        if twin_store is not None and build_twin_snapshot is not None:
            try:
                payload["twin"] = build_twin_snapshot(twin_store)
            except Exception:  # noqa: BLE001 - a projection fault must not drop the socket
                logging.getLogger("hmi.backend").exception("Twin projection failed on connect")
        await websocket.send_text(json.dumps(payload))
        
        while True:
            data = await websocket.receive_text()
            # ===========================================================
            # P5.1 - INBOUND WEBSOCKET IS NOT A STATE WRITER
            #
            # Before P5.1 this branch took arbitrary client JSON and wrote it straight into
            # `vehicle_telemetry_store[vid]`, then broadcast it to every other client. Any
            # connected browser could invent a vehicle, forge its telemetry, and claim any
            # provenance it liked.
            #
            # Inbound WS is now a thin adapter onto the ONE canonical boundary
            # (`telemetry_ingest.TelemetryIngestor`) - the same validation, deduplication,
            # ordering and provenance rules as HTTP, V2V and the serial gateway. WS input is
            # untrusted exactly like HTTP input.
            #
            # PROVENANCE IS NOT NEGOTIABLE: this path FORCES SIMULATION. A client cannot
            # promote its data to HARDWARE by setting a field. Hardware provenance comes
            # only from the trusted hardware ingestion path.
            # ===========================================================
            try:
                msg = json.loads(data)
            except json.JSONDecodeError:
                await websocket.send_text(json.dumps({
                    "type": "error", "reason": "MALFORMED_JSON",
                    "message": "Message could not be parsed; nothing was ingested.",
                }))
                continue

            if not isinstance(msg, dict):
                await websocket.send_text(json.dumps({
                    "type": "error", "reason": "MALFORMED_MESSAGE",
                    "message": "Expected a JSON object.",
                }))
                continue

            mtype = msg.get("type")

            if mtype == "ping":
                await websocket.send_text(json.dumps({"type": "pong", "timestamp": time.time()}))

            elif mtype == "telemetry":
                payload = msg.get("data")
                if not isinstance(payload, dict):
                    await websocket.send_text(json.dumps({
                        "type": "telemetry_rejected", "reason": "MALFORMED_PAYLOAD",
                        "message": "telemetry.data must be an object.",
                    }))
                    continue

                if twin_ingestor is None:
                    await websocket.send_text(json.dumps({
                        "type": "telemetry_rejected", "reason": "INGESTION_UNAVAILABLE",
                        "message": "Canonical ingestion boundary unavailable; nothing ingested.",
                    }))
                    continue

                # Strip any client-declared provenance before ingestion. The transport
                # decides provenance, never the sender.
                candidate = {k: v for k, v in payload.items()
                             if k not in ("source", "provenance_source", "is_simulated")}

                try:
                    result = twin_ingestor.ingest_parsed_record(
                        candidate,
                        transport=IngestTransport.EMULATOR,
                        is_simulated=True,          # FORCED - never HARDWARE from a WS client
                    )
                except Exception:  # noqa: BLE001 - one bad message must not kill the socket
                    logging.getLogger("hmi.backend").exception("WS telemetry ingestion failed")
                    await websocket.send_text(json.dumps({
                        "type": "telemetry_rejected", "reason": "INGESTION_ERROR",
                        "message": "Telemetry could not be ingested.",
                    }))
                    continue

                if not result.accepted:
                    await websocket.send_text(json.dumps({
                        "type": "telemetry_rejected",
                        "reason": result.reason,
                        "vehicle_id": result.vehicle_id,
                        "sequence": result.sequence,
                        "message": "Rejected by the canonical ingestion boundary.",
                    }))
                    continue

                # Accepted by the canonical boundary. Only now may the backend cache and
                # other clients see it, and only as SIMULATION.
                accepted_record = dict(candidate)
                accepted_record["received_at"] = time.time()
                accepted_record["source"] = "SIMULATION"
                accepted_record["provenance_source"] = "SIMULATION"
                vehicle_telemetry_store[result.vehicle_id] = accepted_record

                await websocket.send_text(json.dumps({
                    "type": "telemetry_accepted",
                    "vehicle_id": result.vehicle_id,
                    "sequence": result.sequence,
                    "source": "SIMULATION",
                }))

                await broadcast_twin_update(result.vehicle_id)

                bc = json.dumps({"type": "telemetry_update", "data": accepted_record})
                # A dead peer must not kill this connection. Same defensive pattern the
                # other broadcast sites in this file already use.
                stale = []
                for client in active_websockets:
                    if client is websocket:
                        continue
                    try:
                        await client.send_text(bc)
                    except Exception:  # noqa: BLE001
                        stale.append(client)
                for client in stale:
                    if client in active_websockets:
                        active_websockets.remove(client)

            elif mtype in ("command", "command_issued", "dispatch"):
                # Commands never enter through this socket. They go through
                # POST /api/commands -> CommandGateway, the only validated command path (P5).
                await websocket.send_text(json.dumps({
                    "type": "command_rejected",
                    "reason": "COMMAND_INJECTION_NOT_PERMITTED",
                    "message": "Submit commands via POST /api/commands; they are validated "
                               "by the command gateway.",
                }))

            else:
                await websocket.send_text(json.dumps({
                    "type": "error", "reason": "UNSUPPORTED_MESSAGE_TYPE",
                    "message": "Unsupported inbound message type.",
                }))
    except WebSocketDisconnect:
        if websocket in active_websockets:
            active_websockets.remove(websocket)
    except Exception:
        if websocket in active_websockets:
            active_websockets.remove(websocket)

