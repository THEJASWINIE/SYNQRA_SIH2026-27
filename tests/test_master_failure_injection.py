"""Master Failure Injection Test Suite (Section 13).

Covers all 11 failure injection requirements from the Original Master Prompt:
1. Malformed JSON
2. Missing required field
3. Wrong data type
4. Duplicate packet
5. Delayed packet
6. Disconnected ESP32 representation
7. Disconnected WebSocket
8. Invalid command
9. Unknown vehicle
10. Unrealistic speed
11. Sudden visibility drop

Verifies:
- System behavior recorded
- No crash / unhandled exception
- Clean rejection / handling
- Safe state preserved
- Clean system recovery
"""

import json
import math
import sys
import os
import pytest

backend_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "SYNQRA_SIH2026-27-HMI", "backend")
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from fastapi.testclient import TestClient
from app.main import app, vehicle_telemetry_store, deduplication_store, twin_store, twin_ingestor

from telemetry_ingest import TelemetryIngestor, Transport, IngestResult
from twin.twin_state_store import TwinStateStore, TwinMode, Source, Quality, ClockDomain
from command_gateway import (
    CommandGateway,
    VehicleCommand,
    CommandSource,
    CommandStatus,
)
from fog_safe.vehicle import MiningVehicle
from fog_safe.road import RoadSegment
from fog_safe.environment import EnvironmentState
from fog_safe.communication import CommunicationModel
from fog_safe.safety import solve_safe_speed


@pytest.fixture(autouse=True)
def reset_system():
    vehicle_telemetry_store.clear()
    deduplication_store.clear()
    if twin_store is not None:
        with twin_store._lock:
            twin_store._vehicles.clear()
    if twin_ingestor is not None:
        twin_ingestor._seen_sequences.clear()
        twin_ingestor._last_sequence.clear()
    yield
    vehicle_telemetry_store.clear()
    deduplication_store.clear()
    if twin_store is not None:
        with twin_store._lock:
            twin_store._vehicles.clear()
    if twin_ingestor is not None:
        twin_ingestor._seen_sequences.clear()
        twin_ingestor._last_sequence.clear()


client = TestClient(app)


def test_failure_01_malformed_json():
    """Failure 1: Malformed JSON sent to telemetry endpoints must return 400, no crash."""
    resp = client.post(
        "/api/telemetry",
        content="{\"vehicle_id\": \"TRUCK_01\", speed: invalid_json}",
        headers={"Content-Type": "application/json"}
    )
    assert resp.status_code == 400
    assert "TRUCK_01" not in vehicle_telemetry_store


def test_failure_02_missing_required_field():
    """Failure 2: Missing required field (missing vehicle_id) must be rejected."""
    # /api/hardware/telemetry requires vehicle_id
    resp = client.post("/api/hardware/telemetry", json={"speed_mps": 1.5, "sequence": 1})
    assert resp.status_code == 422
    assert len(vehicle_telemetry_store) == 0


def test_failure_03_wrong_data_type():
    """Failure 3: Wrong data type (string for speed) must be rejected with 400/422."""
    resp = client.post("/api/telemetry", json={"vehicle_id": "TRUCK_01", "speed": "fast"})
    assert resp.status_code == 400
    assert "TRUCK_01" not in vehicle_telemetry_store


def test_failure_04_duplicate_packet():
    """Failure 4: Duplicate sequence packet must be recognized and handled without crash."""
    store = TwinStateStore(mode=TwinMode.HYBRID)
    ingestor = TelemetryIngestor(store)
    pkt = {
        "vehicle_id": "TRUCK_01",
        "sequence": 42,
        "timestamp_ms": 1000.0,
        "speed_mps": 2.0,
        "hazard_detected": False
    }
    r1 = ingestor.ingest_parsed_record(pkt, transport=Transport.DIRECT_WIFI)
    assert r1.accepted is True
    assert r1.reason == "ACCEPTED"

    # Ingest identical packet again
    r2 = ingestor.ingest_parsed_record(pkt, transport=Transport.DIRECT_WIFI)
    assert r2.accepted is False
    assert r2.reason == "REJECTED_DUPLICATE"


def test_failure_05_delayed_out_of_order_packet():
    """Failure 5: Delayed / out-of-order sequence packet."""
    store = TwinStateStore(mode=TwinMode.HYBRID)
    ingestor = TelemetryIngestor(store)

    # Packet seq 10 arrives
    r1 = ingestor.ingest_parsed_record({
        "vehicle_id": "TRUCK_01",
        "sequence": 10,
        "timestamp_ms": 100000.0,
        "speed_mps": 2.0
    }, transport=Transport.DIRECT_WIFI)
    assert r1.accepted is True
    assert store.get_vehicle_field("TRUCK_01", "speed_mps_reported").value == 2.0

    # Packet seq 5 arrives delayed
    r2 = ingestor.ingest_parsed_record({
        "vehicle_id": "TRUCK_01",
        "sequence": 5,
        "timestamp_ms": 90000.0,
        "speed_mps": 1.0
    }, transport=Transport.DIRECT_WIFI)
    assert r2.accepted is False
    assert r2.reason == "REJECTED_OUT_OF_ORDER"

    # Digital twin state must retain newer sequence 10's speed (2.0)
    assert store.get_vehicle_field("TRUCK_01", "speed_mps_reported").value == 2.0


def test_failure_06_disconnected_esp32_timeout():
    """Failure 6: Disconnected ESP32 (silence > 10 seconds) triggers OFFLINE status."""
    import time
    res = client.post("/api/hardware/telemetry", json={
        "vehicle_id": "TRUCK_01",
        "sequence": 1,
        "source": "DIRECT_WIFI",
        "rpm": 100.0,
        "speed": 2.0
    })
    assert res.status_code == 200

    # Online immediately
    data_online = client.get("/api/vehicles").json()["vehicles"]["TRUCK_01"]
    assert data_online["communication_status"] == "ONLINE"

    # Simulate elapsed time past OFFLINE_THRESHOLD_S (10.0s)
    vehicle_telemetry_store["TRUCK_01"]["timestamp"] = time.time() - 15.0
    data_offline = client.get("/api/vehicles").json()["vehicles"]["TRUCK_01"]
    assert data_offline["communication_status"] == "OFFLINE"


def test_failure_07_disconnected_websocket():
    """Failure 7: WebSocket client disconnects mid-session, recovers cleanly on reconnect."""
    with client.websocket_connect("/api/ws") as ws:
        msg = ws.receive_json()
        assert msg["type"] == "connection_established"
        # Disconnect cleanly by exiting context
    
    # Second client connects without server having crashed
    with client.websocket_connect("/api/ws") as ws2:
        msg2 = ws2.receive_json()
        assert msg2["type"] == "connection_established"


def test_failure_08_invalid_command():
    """Failure 8: Invalid command (speed exceeding safe speed) rejected safely."""
    store = TwinStateStore(mode=TwinMode.HYBRID)
    store.register_vehicle("TRUCK_01")
    store.update_vehicle_field(
        "TRUCK_01", "v_safe_mps", 2.0,
        source=Source.DERIVED, timestamp=100.0, quality=Quality.GOOD, clock_domain=ClockDomain.WALL_CLOCK
    )
    class FixedClock:
        t = 100.0
        def __call__(self):
            return self.t
    gateway = CommandGateway(store=store, clock=FixedClock(), validity_window_s=5.0)

    # Attempt to command 5.0 m/s (> safe speed 2.0)
    cmd = VehicleCommand(
        command_id="CMD-001",
        vehicle_id="TRUCK_01",
        action="TARGET_SPEED",
        target_speed_mps=5.0,
        created_at=100.0,
        source=CommandSource.OPERATOR
    )
    res = gateway.submit(cmd)
    assert res.status == CommandStatus.REJECTED
    assert "exceeds" in res.reason.lower() or "safe" in res.reason.lower()


def test_failure_09_unknown_vehicle():
    """Failure 9: Unknown vehicle command handled cleanly."""
    store = TwinStateStore(mode=TwinMode.HYBRID)
    class FixedClock:
        t = 100.0
        def __call__(self):
            return self.t
    gateway = CommandGateway(store=store, clock=FixedClock(), validity_window_s=5.0)
    cmd = VehicleCommand(
        command_id="CMD-999",
        vehicle_id="GHOST_TRUCK_X",
        action="TARGET_SPEED",
        target_speed_mps=1.0,
        created_at=100.0,
        source=CommandSource.OPERATOR
    )
    res = gateway.submit(cmd)
    assert res.status == CommandStatus.UNKNOWN_VEHICLE
    assert "known" in res.reason.lower() or "unknown" in res.reason.lower()


def test_failure_10_unrealistic_speed():
    """Failure 10: Unrealistic / negative speed is rejected before state mutation."""
    resp = client.post("/api/telemetry", json={"vehicle_id": "TRUCK_01", "speed": -25.0})
    assert resp.status_code == 400
    assert "TRUCK_01" not in vehicle_telemetry_store


def test_failure_11_sudden_visibility_drop():
    """Failure 11: Sudden visibility drop (100m -> 4m) immediately drops safe speed."""
    import numpy as np
    veh = MiningVehicle()
    road = RoadSegment(percent_grade=0.0, curve_radius=np.inf, speed_limit_kmh=50.0)
    comm = CommunicationModel()

    # Clear visibility (100m)
    env_clear = EnvironmentState(r_effective=100.0, mu_true=0.7)
    res_clear = solve_safe_speed(veh, road, env_clear, comm, mu_effective=0.7)
    v_clear = res_clear.v_safe_ms

    # Sudden dense fog drop (4m)
    env_fog = EnvironmentState(r_effective=4.0, mu_true=0.7)
    res_fog = solve_safe_speed(veh, road, env_fog, comm, mu_effective=0.7)
    v_fog = res_fog.v_safe_ms

    # Safe speed must sharply drop to allow stopping within 4m
    assert v_fog < v_clear
    assert v_fog <= 4.0
    assert res_fog.primary_constraint == "v_stop"
