"""
P5.1 — the inbound WebSocket must not bypass the canonical ingestion boundary.

Before P5.1 any connected client could write an arbitrary dict into the backend cache
under any vehicle_id and have it broadcast to every other client. These tests pin that
hole shut.

All data here is SIMULATED. No physical hardware was connected.
"""

import os
import sys

import pytest


def _backend_on_path():
    backend = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "SYNQRA_SIH2026-27-HMI", "backend",
    )
    if backend not in sys.path:
        sys.path.insert(0, backend)


_backend_on_path()

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app, twin_store, vehicle_telemetry_store  # noqa: E402
from twin.twin_state_store import UNAVAILABLE, Source  # noqa: E402


_SEQ = [9_000_000]


def next_seq(step=1):
    """
    Strictly increasing, high sequence numbers.

    The backend's TelemetryIngestor is a module-level singleton shared with every other
    test in the session and enforces canonical duplicate/out-of-order rejection. Two rules
    keep these tests order-independent:
      * start above anything the other suites use, and
      * ALWAYS move the shared counter forward - including when a test needs a gap, so a
        later allocation can never fall behind the ingestor's last accepted sequence.
    """
    _SEQ[0] += step
    return _SEQ[0]


def telemetry(vehicle_id="TRUCK_02", sequence=None, **over):
    sequence = next_seq() if sequence is None else sequence
    payload = {
        "vehicle_id": vehicle_id,
        "sequence_number": sequence,
        "rpm": 123.0,
        "speed": 1.5,
        "acceleration": {"x": 0.1, "y": 0.0, "z": 9.81},
        "gyroscope": {"x": 0.0, "y": 0.0, "z": 0.0},
    }
    payload.update(over)
    return {"type": "telemetry", "data": payload}



def receive_skipping_twin(ws):
    """
    P6: an accepted packet now also emits a canonical `twin_vehicle_update` broadcast.
    These tests assert on the legacy/reply messages, so skip the projection frames.
    """
    for _ in range(6):
        message = ws.receive_json()
        if message.get("type") != "twin_vehicle_update":
            return message
    raise AssertionError("only twin_vehicle_update frames received")


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


# ---------------------------------------------------------------------
# 1/7. inbound WS telemetry goes through TelemetryIngestor
# ---------------------------------------------------------------------

def test_ws_telemetry_is_ingested_through_the_canonical_boundary(client):
    from unittest import mock

    import app.main as backend

    assert backend.twin_ingestor is not None

    with client.websocket_connect("/api/ws") as ws:
        ws.receive_json()                                   # connection_established
        with mock.patch.object(
            backend.twin_ingestor, "ingest_parsed_record",
            wraps=backend.twin_ingestor.ingest_parsed_record,
        ) as spy:
            ws.send_json(telemetry())
            reply = receive_skipping_twin(ws)

    assert spy.call_count == 1, "WS telemetry bypassed the ingestion boundary"
    assert reply["type"] == "telemetry_accepted"
    # The transport, not the client, decided provenance.
    assert spy.call_args.kwargs["is_simulated"] is True


def test_accepted_ws_telemetry_reaches_the_twin_as_simulation(client):
    with client.websocket_connect("/api/ws") as ws:
        ws.receive_json()
        ws.send_json(telemetry(rpm=456.0))
        assert receive_skipping_twin(ws)["type"] == "telemetry_accepted"

    rpm = twin_store.get_vehicle_field("TRUCK_02", "rpm")
    assert rpm.value == 456.0
    assert rpm.source is Source.SIMULATION


# ---------------------------------------------------------------------
# 2/3. invalid input rejected; no arbitrary state written
# ---------------------------------------------------------------------

@pytest.mark.parametrize(
    "message,expected",
    [
        ({"type": "telemetry", "data": {"sequence_number": 1}}, "REJECTED_MISSING_VEHICLE_ID"),
        ({"type": "telemetry", "data": {"vehicle_id": "TRUCK_47", "sequence_number": 1}},
         "REJECTED_UNKNOWN_VEHICLE"),
        ({"type": "telemetry", "data": {"vehicle_id": "TRUCK_02", "sequence_number": "x"}},
         "REJECTED_INVALID_SEQUENCE"),
    ],
)
def test_invalid_ws_telemetry_is_rejected(client, message, expected):
    with client.websocket_connect("/api/ws") as ws:
        ws.receive_json()
        ws.send_json(message)
        reply = ws.receive_json()

    assert reply["type"] == "telemetry_rejected"
    assert reply["reason"] == expected


def test_ws_cannot_invent_a_vehicle_in_the_cache_or_twin(client):
    with client.websocket_connect("/api/ws") as ws:
        ws.receive_json()
        ws.send_json(telemetry(vehicle_id="GHOST_TRUCK", sequence=1))
        assert ws.receive_json()["type"] == "telemetry_rejected"

    assert "GHOST_TRUCK" not in vehicle_telemetry_store
    assert twin_store.get_vehicle("GHOST_TRUCK") is None


def test_ws_cannot_write_arbitrary_vehicle_state(client):
    """A client cannot force speed/safety fields into the Twin the way it used to."""
    with client.websocket_connect("/api/ws") as ws:
        ws.receive_json()
        ws.send_json({
            "type": "telemetry",
            "data": {
                "vehicle_id": "TRUCK_02", "sequence_number": next_seq(),
                "speed_mps": 99.0, "safety_state": "NORMAL", "position_s": 4242.0,
            },
        })
        assert receive_skipping_twin(ws)["type"] == "telemetry_accepted"

    # position is not measurable on this prototype and must never appear from a client.
    assert twin_store.get_vehicle_field("TRUCK_02", "position_s") is UNAVAILABLE
    # And the forged safety_state never became authoritative Twin state.
    assert twin_store.get_vehicle_field("TRUCK_02", "safety_state") is UNAVAILABLE


def test_malformed_ws_messages_are_answered_not_ignored(client):
    with client.websocket_connect("/api/ws") as ws:
        ws.receive_json()

        ws.send_text("this is not json")
        assert ws.receive_json()["reason"] == "MALFORMED_JSON"

        ws.send_json({"type": "telemetry", "data": "not-an-object"})
        assert ws.receive_json()["reason"] == "MALFORMED_PAYLOAD"

        ws.send_json({"type": "nonsense"})
        assert ws.receive_json()["reason"] == "UNSUPPORTED_MESSAGE_TYPE"


# ---------------------------------------------------------------------
# 4/5. provenance cannot be self-declared
# ---------------------------------------------------------------------

def test_ws_client_cannot_declare_hardware_provenance(client):
    """The whole point of P5.1: setting source=HARDWARE must not make it hardware."""
    with client.websocket_connect("/api/ws") as ws:
        ws.receive_json()
        ws.send_json(telemetry(
            rpm=777.0,
            source="HARDWARE", provenance_source="HARDWARE", is_simulated=False,
        ))
        reply = receive_skipping_twin(ws)

    assert reply["type"] == "telemetry_accepted"
    assert reply["source"] == "SIMULATION"

    rpm = twin_store.get_vehicle_field("TRUCK_02", "rpm")
    assert rpm.value == 777.0
    assert rpm.source is Source.SIMULATION
    assert rpm.source is not Source.HARDWARE
    assert not rpm.is_hardware_backed()


def test_ws_path_forces_simulation_in_the_broadcast_and_cache(client):
    with client.websocket_connect("/api/ws") as ws:
        ws.receive_json()
        ws.send_json(telemetry(source="HARDWARE"))
        assert receive_skipping_twin(ws)["type"] == "telemetry_accepted"

    cached = vehicle_telemetry_store["TRUCK_02"]
    assert cached["source"] == "SIMULATION"
    assert cached["provenance_source"] == "SIMULATION"


# ---------------------------------------------------------------------
# 6. duplicate / out-of-order handling stays canonical
# ---------------------------------------------------------------------

def test_ws_duplicate_and_out_of_order_use_canonical_rules(client):
    with client.websocket_connect("/api/ws") as ws:
        ws.receive_json()

        # Leave a gap so `seq - 1` is genuinely UNSEEN: the counter is monotonic, so an
        # adjacent number would already have been accepted and would trip the duplicate
        # rule instead of the ordering rule.
        seq = next_seq(step=100)
        ws.send_json(telemetry(sequence=seq, rpm=100.0))
        assert receive_skipping_twin(ws)["type"] == "telemetry_accepted"

        ws.send_json(telemetry(sequence=seq, rpm=999.0))            # duplicate
        assert receive_skipping_twin(ws)["reason"] == "REJECTED_DUPLICATE"

        ws.send_json(telemetry(sequence=seq - 1, rpm=888.0))        # out of order
        assert receive_skipping_twin(ws)["reason"] == "REJECTED_OUT_OF_ORDER"

    assert twin_store.get_vehicle_field("TRUCK_02", "rpm").value == 100.0


# ---------------------------------------------------------------------
# 8. command injection over WS is refused
# ---------------------------------------------------------------------

@pytest.mark.parametrize("mtype", ["command", "command_issued", "dispatch"])
def test_ws_command_injection_is_rejected(client, mtype):
    with client.websocket_connect("/api/ws") as ws:
        ws.receive_json()
        ws.send_json({
            "type": mtype,
            "data": {"command_id": "WS_1", "vehicle_id": "TRUCK_02",
                     "action": "TARGET_SPEED", "target_speed": 99.0},
        })
        reply = ws.receive_json()

    assert reply["type"] == "command_rejected"
    assert reply["reason"] == "COMMAND_INJECTION_NOT_PERMITTED"


def test_ws_command_injection_does_not_reach_the_gateway(client):
    import app.main as backend

    if backend.command_gateway is None:
        pytest.skip("gateway unavailable")

    before = len(backend.command_gateway.history())
    with client.websocket_connect("/api/ws") as ws:
        ws.receive_json()
        ws.send_json({"type": "command", "data": {"command_id": "WS_INJECT",
                                                  "vehicle_id": "TRUCK_02"}})
        ws.receive_json()

    assert len(backend.command_gateway.history()) == before
    assert backend.command_gateway.get_status("WS_INJECT") is None


# ---------------------------------------------------------------------
# 9. outbound broadcasting still works
# ---------------------------------------------------------------------

def test_outbound_broadcast_still_reaches_other_clients(client):
    with client.websocket_connect("/api/ws") as listener:
        listener.receive_json()                              # connection_established

        with client.websocket_connect("/api/ws") as sender:
            sender.receive_json()
            sender.send_json(telemetry(rpm=222.0))
            assert receive_skipping_twin(sender)["type"] == "telemetry_accepted"

        update = receive_skipping_twin(listener)

    assert update["type"] == "telemetry_update"
    assert update["data"]["vehicle_id"] == "TRUCK_02"
    assert update["data"]["source"] == "SIMULATION"


def test_http_hardware_telemetry_still_broadcasts_over_ws(client):
    """The trusted hardware path still reaches HMI clients, and stays HARDWARE."""
    with client.websocket_connect("/api/ws") as ws:
        ws.receive_json()
        client.post(
            "/api/hardware/telemetry",
            json={"vehicle_id": "TRUCK_02", "sequence": next_seq(), "rpm": 240.0, "speed": 2.5,
                  "ax": 0.1, "ay": 0.0, "az": 9.81, "gx": 0.0, "gy": 0.0, "gz": 0.0,
                  "source": "DIRECT_WIFI"},
        )
        message = receive_skipping_twin(ws)

    assert message["type"] == "telemetry_update"
    assert twin_store.get_vehicle_field("TRUCK_02", "rpm").source is Source.HARDWARE


def test_ping_pong_still_works(client):
    with client.websocket_connect("/api/ws") as ws:
        ws.receive_json()
        ws.send_json({"type": "ping"})
        assert ws.receive_json()["type"] == "pong"
