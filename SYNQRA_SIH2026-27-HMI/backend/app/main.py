"""FOG-ORCHESTRATOR 2.0 — Task 1 HMI backend.

Supervisory HMI Backend with independent REST and WebSocket telemetry capabilities.

Scope boundary (see `CLAUDE.md`, `requirements/DECISIONS.md` PAD-A/B/E):
This process performs NO Digital Twin computation, NO physics, NO prediction,
NO optimization, and NO simulation. It acts as an independent HMI supervisor.
"""

import time
import json
import asyncio
from datetime import datetime, timezone
from typing import Dict, Any, List
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from app.config import settings
from app.schemas.health import SERVICE_VERSION, HealthResponse

app = FastAPI(
    title="FOG-ORCHESTRATOR 2.0 — Task 1 HMI backend",
    version=SERVICE_VERSION,
    summary="Supervisory HMI backend. Advisory only; performs no safety computation.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
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


# Mode Configuration: 'MOCK' or 'HARDWARE'
HMI_MODE: str = "MOCK"

# Deduplication and sequence history tracking
deduplication_store: Dict[str, Dict[str, Any]] = {}
last_sequence_by_vehicle: Dict[str, int] = {}


@app.get("/api/health", response_model=HealthResponse, tags=["health"])
def get_health() -> HealthResponse:
    """Liveness of this service. Used by the frontend as its connectivity proof."""
    return HealthResponse()


@app.get("/api/mode", tags=["config"])
def get_mode() -> Dict[str, str]:
    """Returns current operating mode (MOCK or LIVE)."""
    now = time.time()
    has_active_live = any(
        d.get("data_quality") == "LIVE" and (now - d.get("timestamp", now)) <= 10.0
        for d in vehicle_telemetry_store.values()
    )
    active_mode = "LIVE" if (HMI_MODE == "LIVE" or has_active_live) else "MOCK"
    return {"mode": active_mode, "status": "ACTIVE"}


@app.get("/api/vehicles", tags=["telemetry"])
def get_vehicles() -> Dict[str, Any]:
    """Returns currently registered vehicle states and staleness status."""
    now = time.time()
    result = {}
    has_active_live = False

    for vid, data in vehicle_telemetry_store.items():
        ts = data.get("timestamp", now)
        age = now - ts
        
        stale_thresh = data.get("stale_threshold_s", 3.0)
        offline_thresh = data.get("offline_threshold_s", 10.0)

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

        if "communication" in veh_copy and isinstance(veh_copy["communication"], dict):
            comm_sub = dict(veh_copy["communication"])
            comm_sub["status"] = comm_status
            veh_copy["communication"] = comm_sub
        
        result[vid] = veh_copy

    active_mode = "LIVE" if (HMI_MODE == "LIVE" or has_active_live) else "MOCK"
    return {"vehicles": result, "count": len(result), "mode": active_mode, "timestamp": now}


@app.post("/api/telemetry", tags=["telemetry"])
async def ingest_telemetry(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Ingests vehicle telemetry payload from mock telemetry generator or external source."""
    vid = payload.get("vehicle_id")
    if not vid:
        raise HTTPException(status_code=400, detail="vehicle_id is required")

    # Protection: Active LIVE hardware telemetry takes precedence over mock updates
    existing = vehicle_telemetry_store.get(vid)
    if existing and existing.get("data_quality") == "LIVE":
        age = time.time() - existing.get("timestamp", 0)
        if age <= 10.0:
            return {
                "status": "IGNORED_MOCK_OVERWRITE",
                "vehicle_id": vid,
                "timestamp": time.time(),
                "message": "Active LIVE hardware telemetry stream has precedence over mock telemetry"
            }
    
    payload["received_at"] = time.time()
    vehicle_telemetry_store[vid] = payload
    
    # Broadcast to active WebSockets
    message_json = json.dumps({"type": "telemetry_update", "data": payload})
    disconnected = []
    for ws in active_websockets:
        try:
            await ws.send_text(message_json)
        except Exception:
            disconnected.append(ws)
    for ws in disconnected:
        if ws in active_websockets:
            active_websockets.remove(ws)
            
    return {"status": "INGESTED", "vehicle_id": vid, "timestamp": payload["received_at"]}


@app.post("/api/hardware/telemetry", tags=["telemetry"])
async def ingest_hardware_telemetry(payload: HardwareTelemetryPayload) -> Dict[str, Any]:
    """
    Ingests canonical vehicle telemetry from physical Wi-Fi Direct or V2V relay paths.
    Enforces deduplication by (vehicle_id, sequence), source priority (DIRECT_WIFI > V2V_VIA_TRUCK_02),
    and sequence continuity.
    """
    global HMI_MODE
    HMI_MODE = "LIVE"

    vid = payload.vehicle_id.upper()
    if vid not in ["TRUCK_01", "TRUCK_02"]:
        raise HTTPException(status_code=400, detail=f"Invalid vehicle_id '{vid}'. Must be TRUCK_01 or TRUCK_02")

    source_val = payload.source.upper()
    if source_val not in ["DIRECT_WIFI", "V2V_VIA_TRUCK_02"]:
        raise HTTPException(status_code=400, detail=f"Invalid source '{source_val}'. Must be DIRECT_WIFI or V2V_VIA_TRUCK_02")

    dedup_key = f"{vid}_{payload.sequence}"
    is_duplicate = dedup_key in deduplication_store

    now = time.time()
    last_seq = last_sequence_by_vehicle.get(vid, 0)
    is_out_of_order = (payload.sequence < last_seq) and not is_duplicate

    if is_out_of_order:
        return {
            "status": "REJECTED_OUT_OF_ORDER",
            "vehicle_id": vid,
            "sequence": payload.sequence,
            "last_sequence": last_seq,
            "is_duplicate": False,
            "message": f"Sequence {payload.sequence} is older than last seen {last_seq}"
        }

    # Store deduplication record
    existing_rec = deduplication_store.get(dedup_key)
    if is_duplicate and existing_rec:
        if source_val == "DIRECT_WIFI" and existing_rec.get("source") != "DIRECT_WIFI":
            existing_rec["source"] = "DIRECT_WIFI"
            if vid in vehicle_telemetry_store:
                vehicle_telemetry_store[vid]["source"] = "DIRECT_WIFI"
                vehicle_telemetry_store[vid]["primary_source"] = "DIRECT_WIFI"

        return {
            "status": "ACCEPTED_DUPLICATE",
            "vehicle_id": vid,
            "sequence": payload.sequence,
            "source": source_val,
            "is_duplicate": True,
            "communication_status": "ONLINE"
        }

    if payload.sequence > last_seq:
        last_sequence_by_vehicle[vid] = payload.sequence
    deduplication_store[dedup_key] = payload.dict()

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
        "rpm": max(0.0, payload.rpm),
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
        "stale_threshold_s": 3.0,
        "offline_threshold_s": 10.0,
        "timestamp": now,
        "received_at": now
    }

    vehicle_telemetry_store[vid] = canonical_record

    message_json = json.dumps({"type": "telemetry_update", "data": canonical_record})
    iso_ts = datetime.fromtimestamp(now, tz=timezone.utc).isoformat()
    vstate_json = json.dumps({
        "type": "VehicleState",
        "payload": {
            "vehicle_id": vid,
            "timestamp": iso_ts,
            "position": {
                "x": 120.0 if vid == "TRUCK_01" else 80.0,
                "y": 50.0,
                "segment_id": "SEG_01",
                "offset_m": 10.0
            },
            "speed_mps": float(payload.speed or 0.0),
            "accel_mps2": float(payload.az or 0.0) / 1000.0,
            "grade_rad": 0.0,
            "friction_est": { "value": 0.8, "sigma": 0.05 },
            "mode": "TRAVELING",
            "comm_confidence": 0.95,
            "vehicle_kind": "TRUCK",
            "route_id": "ROUTE_MAIN"
        }
    })
    disconnected = []
    for ws in active_websockets:
        try:
            await ws.send_text(message_json)
            await ws.send_text(vstate_json)
        except Exception:
            disconnected.append(ws)
    for ws in disconnected:
        if ws in active_websockets:
            active_websockets.remove(ws)

    return {
        "status": "ACCEPTED",
        "vehicle_id": vid,
        "sequence": payload.sequence,
        "source": source_val,
        "is_duplicate": False,
        "communication_status": "ONLINE"
    }


@app.post("/api/commands", response_model=HMICommandResponse, tags=["command"])
async def post_command(cmd: HMICommandRequest) -> HMICommandResponse:
    """Processes HMI supervisory command (TARGET_SPEED, HOLD, STOP, RELEASE). Rejects duplicate command_id."""
    valid_actions = ["TARGET_SPEED", "HOLD", "STOP", "RELEASE"]
    if cmd.action.upper() not in valid_actions:
        raise HTTPException(status_code=400, detail=f"Invalid action '{cmd.action}'. Must be one of {valid_actions}")
    
    # Check for duplicate command_id
    if any(c.get("command_id") == cmd.command_id for c in command_history):
        return HMICommandResponse(
            command_id=cmd.command_id,
            vehicle_id=cmd.vehicle_id,
            action=cmd.action.upper(),
            status="REJECTED",
            timestamp=time.time(),
            message=f"Duplicate command_id '{cmd.command_id}' rejected."
        )

    now = time.time()
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
    
    # If vehicle exists in store, update mode or speed
    if cmd.vehicle_id in vehicle_telemetry_store:
        veh = vehicle_telemetry_store[cmd.vehicle_id]
        if cmd.action.upper() == "STOP":
            veh["speed_mps"] = 0.0
            veh["mode"] = "stopped"
            veh["safety_state"] = "CRITICAL"
        elif cmd.action.upper() == "HOLD":
            veh["speed_mps"] = 0.0
            veh["mode"] = "holding"
            veh["safety_state"] = "WARNING"
        elif cmd.action.upper() == "RELEASE":
            veh["mode"] = "traveling"
            veh["safety_state"] = "NORMAL"
        elif cmd.action.upper() == "TARGET_SPEED":
            veh["target_speed_mps"] = cmd.target_speed
            veh["mode"] = "traveling"
            
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
        message=f"Command {cmd.action.upper()} accepted for vehicle {cmd.vehicle_id}"
    )


@app.get("/api/commands/history", tags=["command"])
def get_command_history() -> Dict[str, Any]:
    """Returns history of dispatched HMI commands."""
    return {"commands": command_history, "count": len(command_history)}


@app.websocket("/api/ws")
async def websocket_endpoint(websocket: WebSocket):
    """Independent HMI WebSocket Endpoint for telemetry streaming and command updates."""
    await websocket.accept()
    active_websockets.append(websocket)
    try:
        # Send initial snapshot of registered vehicles
        snapshot = json.dumps({
            "type": "connection_established",
            "message": "Connected to HMI Independent Backend",
            "vehicles": vehicle_telemetry_store
        })
        await websocket.send_text(snapshot)
        
        while True:
            data = await websocket.receive_text()
            try:
                msg = json.loads(data)
                mtype = msg.get("type")
                if mtype == "ping":
                    await websocket.send_text(json.dumps({"type": "pong", "timestamp": time.time()}))
                elif mtype == "telemetry":
                    telemetry_data = msg.get("data", {})
                    vid = telemetry_data.get("vehicle_id")
                    if vid:
                        telemetry_data["received_at"] = time.time()
                        vehicle_telemetry_store[vid] = telemetry_data
                        # Echo broadcast
                        bc = json.dumps({"type": "telemetry_update", "data": telemetry_data})
                        for client in active_websockets:
                            if client != websocket:
                                await client.send_text(bc)
            except json.JSONDecodeError:
                pass
    except WebSocketDisconnect:
        if websocket in active_websockets:
            active_websockets.remove(websocket)
    except Exception:
        if websocket in active_websockets:
            active_websockets.remove(websocket)

