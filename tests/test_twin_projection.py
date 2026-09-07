"""
P6 — canonical Twin -> backend projection -> REST/WebSocket.

All data is SIMULATED / REPLAYED. No physical ESP32 was connected.
"""

import os
import sys

import pytest

from twin_projection import (
    build_twin_snapshot,
    build_vehicle_projection,
    value_of,
)
from twin.twin_state_store import TwinMode, TwinStateStore

WALL_NOW = 1_788_000_000.0
SIM_NOW = 120.0


class FixedClock:
    def __init__(self, t=WALL_NOW):
        self.t = t

    def __call__(self):
        return self.t

    def advance(self, dt):
        self.t += dt


class SimVehicle:
    def __init__(self, vehicle_id):
        self.id = vehicle_id
        self.tare_mass = 74000.0
        self.length = 10.52
        self.position_s = 40.0
        self.current_edge = "ROAD_2"
        self.current_node = None
        self.speed_mps = 7.5
        self.acceleration_mps2 = 0.4
        self.mass_kg = 165000.0
        self.payload_kg = 91000.0
        self.is_loaded = True
        self.state = "traveling"
        self.v_safe_mps = 9.5
        self.v_dispatch_mps = 11.11
        self.v_command_mps = 9.5
        self.safe_headway_m = 40.0
        self.stop_envelope_m = 35.0
        self.warning_fault = False


class SimFog:
    current_visibility = 15.0
    current_friction = 0.35
    current_rr = 0.02
    current_state = "wet"
    scenario_name = "dense_fog"


@pytest.fixture
def clock():
    return FixedClock()


@pytest.fixture
def store(clock):
    return TwinStateStore(mode=TwinMode.HYBRID, clock=clock, stale_after_s=3.0)


def ingest_hardware(store, clock, vehicle_id="TRUCK_02", sequence=1, rpm=180.0):
    from telemetry_ingest import TelemetryIngestor, Transport

    ingestor = TelemetryIngestor(store, clock=clock)
    ingestor.ingest_parsed_record(
        {
            "vehicle_id": vehicle_id, "sequence_number": sequence, "rpm": rpm, "speed": 2.5,
            "acceleration": {"x": 0.1, "y": 0.0, "z": 9.81},
            "gyroscope": {"x": 0.0, "y": 0.0, "z": 0.0},
            "communication": {"rssi": -65, "snr": 9.2},
            "communication_state": "HEALTHY", "data_quality": "LIVE",
        },
        transport=Transport.DIRECT_WIFI, is_simulated=False,
    )
    return ingestor


# ---------------------------------------------------------------------
# 2/3/4/5. projection fidelity and provenance
# ---------------------------------------------------------------------

def test_projection_does_not_fabricate_missing_fields(store, clock):
    ingest_hardware(store, clock)
    projection = build_vehicle_projection(store, "TRUCK_02")

    # Nothing on this prototype measures these; they must be ABSENT, not zeroed.
    for name in ("position_s", "road_id", "heading_rad", "v_safe_mps"):
        assert name not in projection["dynamic"], f"{name} was fabricated"
    assert value_of(projection, "position_s") is None


def test_hardware_provenance_is_preserved(store, clock):
    ingest_hardware(store, clock)
    rpm = build_vehicle_projection(store, "TRUCK_02")["dynamic"]["rpm"]

    assert rpm["value"] == 180.0
    assert rpm["source"] == "HARDWARE"
    assert rpm["origin"] == "HARDWARE"
    assert rpm["available"] is True


def test_simulation_provenance_is_preserved(store, clock):
    store.sync_from_simulation(vehicles=[SimVehicle("TRUCK_01")], fog_model=SimFog(), timestamp=SIM_NOW)
    projection = build_vehicle_projection(store, "TRUCK_01")

    assert projection["dynamic"]["position_s"]["source"] == "SIMULATION"
    assert projection["dynamic"]["position_s"]["origin"] == "SIMULATION"
    assert projection["has_hardware_data"] is False


def test_derived_origin_distinguishes_hardware_from_simulation(store, clock):
    """The P6 requirement: source=DERIVED alone is not enough for the HMI."""
    ingest_hardware(store, clock)
    store.sync_from_simulation(vehicles=[SimVehicle("TRUCK_02")], timestamp=SIM_NOW)
    dynamic = build_vehicle_projection(store, "TRUCK_02")["dynamic"]

    # speed derived from a MEASURED rpm
    assert dynamic["speed_mps"]["source"] == "DERIVED"
    assert dynamic["speed_mps"]["origin"] == "HARDWARE"
    assert dynamic["speed_mps"]["clock_domain"] == "WALL_CLOCK"

    # solver output for the simulated side of the same vehicle
    assert dynamic["v_safe_mps"]["source"] == "DERIVED"
    assert dynamic["v_safe_mps"]["origin"] == "SIMULATION"
    assert dynamic["v_safe_mps"]["clock_domain"] == "SIMULATION"


def test_pwm_derived_speed_is_never_projected_as_hardware(store, clock):
    ingest_hardware(store, clock)
    pwm = build_vehicle_projection(store, "TRUCK_02")["dynamic"]["speed_mps_pwm_derived"]
    assert pwm["source"] == "DERIVED"
    assert pwm["source"] != "HARDWARE"


# ---------------------------------------------------------------------
# 6/7/8. freshness, clock domain, simulation_time
# ---------------------------------------------------------------------

def test_freshness_and_clock_domain_are_projected(store, clock):
    ingest_hardware(store, clock)
    store.sync_from_simulation(vehicles=[SimVehicle("TRUCK_02")], timestamp=SIM_NOW)
    dynamic = build_vehicle_projection(store, "TRUCK_02")["dynamic"]

    assert dynamic["rpm"]["clock_domain"] == "WALL_CLOCK"
    assert dynamic["rpm"]["freshness"] == "CURRENT"
    assert dynamic["position_s"]["clock_domain"] == "SIMULATION"
    assert dynamic["position_s"]["freshness"] == "CURRENT"


def test_simulation_fields_are_not_stale_against_the_wall_clock(store, clock):
    """P4.1 must survive projection: the whole point of the clock-domain work."""
    store.sync_from_simulation(vehicles=[SimVehicle("TRUCK_01")], timestamp=SIM_NOW)
    dynamic = build_vehicle_projection(store, "TRUCK_01")["dynamic"]
    for name, field in dynamic.items():
        assert field["quality"] != "STALE", f"{name} wrongly stale after projection"


def test_stale_hardware_is_projected_as_stale(store, clock):
    ingest_hardware(store, clock)
    clock.advance(30.0)
    rpm = build_vehicle_projection(store, "TRUCK_02")["dynamic"]["rpm"]
    assert rpm["freshness"] == "STALE"
    assert rpm["quality"] == "STALE"


def test_snapshot_carries_simulation_time_and_mode(store, clock):
    store.sync_from_simulation(vehicles=[SimVehicle("TRUCK_01")], fog_model=SimFog(), timestamp=SIM_NOW)
    snapshot = build_twin_snapshot(store)

    assert snapshot["schema"] == "twin_projection/1"
    assert snapshot["mode"] == "HYBRID"
    assert snapshot["simulation_time"] == SIM_NOW
    assert snapshot["environment"]["visibility_m"]["value"] == 15.0
    assert snapshot["environment"]["visibility_m"]["source"] == "SIMULATION"


def test_projection_is_read_only(store, clock):
    ingest_hardware(store, clock)
    before = store.get_state_snapshot(now=clock.t)
    build_twin_snapshot(store)
    build_vehicle_projection(store, "TRUCK_02")
    assert store.get_state_snapshot(now=clock.t) == before


def test_unknown_vehicle_projects_to_none(store):
    assert build_vehicle_projection(store, "TRUCK_47") is None


# =====================================================================
# Backend REST + WebSocket
# =====================================================================

def _backend_on_path():
    backend_dir = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "SYNQRA_SIH2026-27-HMI", "backend",
    )
    if backend_dir not in sys.path:
        sys.path.insert(0, backend_dir)


_backend_on_path()

from fastapi.testclient import TestClient  # noqa: E402

import app.main as backend  # noqa: E402
from app.main import app  # noqa: E402

_SEQ = [8_000_000]


def next_seq(step=1):
    _SEQ[0] += step
    return _SEQ[0]


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


def post_hardware(client, sequence=None, rpm=240.0):
    return client.post(
        "/api/hardware/telemetry",
        json={"vehicle_id": "TRUCK_02", "sequence": sequence or next_seq(), "rpm": rpm,
              "speed": 2.5, "ax": 0.1, "ay": 0.0, "az": 9.81, "gx": 0.0, "gy": 0.0, "gz": 0.0,
              "source": "DIRECT_WIFI"},
    )


# ---------------------------------------------------------------------
# 1. REST reads the canonical projection
# ---------------------------------------------------------------------

def test_twin_snapshot_endpoint_serves_the_canonical_projection(client):
    post_hardware(client, rpm=333.0)
    body = client.get("/api/twin/snapshot").json()

    assert body["schema"] == "twin_projection/1"
    rpm = body["vehicles"]["TRUCK_02"]["dynamic"]["rpm"]
    assert rpm["value"] == 333.0
    assert rpm["source"] == "HARDWARE"
    assert {"clock_domain", "freshness", "origin", "age_s", "available"} <= set(rpm)


def test_twin_vehicle_endpoint(client):
    post_hardware(client, rpm=444.0)
    body = client.get("/api/twin/vehicles/TRUCK_02").json()
    assert body["vehicle_id"] == "TRUCK_02"
    assert body["dynamic"]["rpm"]["value"] == 444.0

    assert client.get("/api/twin/vehicles/TRUCK_47").status_code == 404


def test_get_requests_never_mutate_the_twin(client):
    post_hardware(client)
    before = backend.twin_store.get_state_snapshot()
    client.get("/api/twin/snapshot")
    client.get("/api/twin/vehicles/TRUCK_02")
    client.get("/api/vehicles")
    after = backend.twin_store.get_state_snapshot()

    # Read-derived fields (snapshot_timestamp, age_s, freshness, quality) legitimately
    # advance with the clock. The STORED state - values, provenance, timestamps - must not.
    def stored(snapshot):
        return {
            vid: {
                name: (f["value"], f["source"], f["timestamp"])
                for name, f in vehicle["dynamic"].items()
            }
            for vid, vehicle in snapshot["vehicles"].items()
        }

    assert stored(after) == stored(before), "a GET mutated stored Twin state"
    assert after["simulation_time"] == before["simulation_time"]
    assert after["mine"] == before["mine"]


def test_existing_endpoints_still_work(client):
    """Compatibility: health, mode, vehicles, command history must not break."""
    assert client.get("/api/health").status_code == 200
    assert client.get("/api/mode").status_code == 200

    vehicles = client.get("/api/vehicles")
    assert vehicles.status_code == 200
    assert "vehicles" in vehicles.json()

    assert client.get("/api/commands/history").status_code == 200


# ---------------------------------------------------------------------
# 9/12/13. WebSocket: canonical projection, both routes
# ---------------------------------------------------------------------

def _drain_for(ws, message_type, limit=8):
    for _ in range(limit):
        message = ws.receive_json()
        if message.get("type") == message_type:
            return message
    raise AssertionError(f"{message_type} not received")


def test_ws_emits_the_canonical_projection(client):
    with client.websocket_connect("/api/ws") as ws:
        hello = ws.receive_json()
        assert hello["type"] == "connection_established"
        assert hello["twin"]["schema"] == "twin_projection/1"

        post_hardware(client, rpm=555.0)
        update = _drain_for(ws, "twin_vehicle_update")

    assert update["data"]["vehicle_id"] == "TRUCK_02"
    rpm = update["data"]["dynamic"]["rpm"]
    assert rpm["value"] == 555.0
    assert rpm["source"] == "HARDWARE"
    assert rpm["clock_domain"] == "WALL_CLOCK"


def test_ws_live_alias_is_the_same_single_stream(client):
    with client.websocket_connect("/ws/live") as ws:
        hello = ws.receive_json()
        assert hello["type"] == "connection_established"
        assert "twin" in hello

        post_hardware(client, rpm=666.0)
        update = _drain_for(ws, "twin_vehicle_update")

    assert update["data"]["dynamic"]["rpm"]["value"] == 666.0


def test_both_ws_routes_receive_the_same_broadcast(client):
    """One stream, two URLs - not two independent state streams."""
    with client.websocket_connect("/api/ws") as a, client.websocket_connect("/ws/live") as b:
        a.receive_json()
        b.receive_json()
        post_hardware(client, rpm=777.0)

        update_a = _drain_for(a, "twin_vehicle_update")
        update_b = _drain_for(b, "twin_vehicle_update")

    assert update_a["data"]["dynamic"]["rpm"]["value"] == 777.0
    assert update_b["data"]["dynamic"]["rpm"]["value"] == 777.0


def test_ws_reconnect_receives_current_twin_state(client):
    post_hardware(client, rpm=888.0)

    with client.websocket_connect("/api/ws") as ws:
        hello = ws.receive_json()
    assert hello["twin"]["vehicles"]["TRUCK_02"]["dynamic"]["rpm"]["value"] == 888.0

    # Reconnect: state is still there, and still canonical.
    with client.websocket_connect("/ws/live") as ws:
        again = ws.receive_json()
    assert again["twin"]["vehicles"]["TRUCK_02"]["dynamic"]["rpm"]["value"] == 888.0


# ---------------------------------------------------------------------
# 15/21. robustness
# ---------------------------------------------------------------------

def test_dead_ws_client_does_not_kill_the_broadcast(client):
    with client.websocket_connect("/api/ws") as survivor:
        survivor.receive_json()

        with client.websocket_connect("/api/ws") as doomed:
            doomed.receive_json()
        # `doomed` is now closed but may still sit in active_websockets.

        post_hardware(client, rpm=999.0)
        update = _drain_for(survivor, "twin_vehicle_update")

    assert update["data"]["dynamic"]["rpm"]["value"] == 999.0


def test_projection_failure_does_not_break_ingestion(client, monkeypatch):
    """A broken projection must not turn a good telemetry POST into a 500."""
    def boom(*_args, **_kwargs):
        raise RuntimeError("projection exploded")

    monkeypatch.setattr(backend, "build_vehicle_projection", boom)
    response = post_hardware(client, rpm=121.0)

    assert response.status_code == 200
    assert response.json()["status"] == "ACCEPTED"
    assert backend.twin_store.get_vehicle_field("TRUCK_02", "rpm").value == 121.0


def test_snapshot_survives_a_vehicle_with_no_dynamic_fields(client):
    """A registered vehicle with nothing observed yet must project cleanly, not crash."""
    backend.twin_store.register_vehicle("TRUCK_01")
    body = client.get("/api/twin/snapshot").json()

    vehicle = body["vehicles"]["TRUCK_01"]
    assert vehicle["vehicle_id"] == "TRUCK_01"
    assert isinstance(vehicle["dynamic"], dict)
    assert isinstance(vehicle["has_hardware_data"], bool)
    # Unobserved fields are absent, never defaulted.
    for name in ("position_s", "heading_rad"):
        assert name not in vehicle["dynamic"]


# ---------------------------------------------------------------------
# 18. commands still do not mutate telemetry
# ---------------------------------------------------------------------

def test_commands_do_not_mutate_projected_vehicle_state(client):
    post_hardware(client, rpm=200.0)
    before = client.get("/api/twin/vehicles/TRUCK_02").json()["dynamic"]

    client.post("/api/commands", json={
        "command_id": f"P6_CMD_{next_seq()}", "vehicle_id": "TRUCK_02",
        "action": "STOP", "target_speed": 0.0, "reason": "operator",
    })

    after = client.get("/api/twin/vehicles/TRUCK_02").json()["dynamic"]
    assert after["rpm"]["value"] == before["rpm"]["value"]
    assert "v_command_mps" not in after      # a command did not invent commanded state
