"""
REGRESSION - the SIMULATED ingress must broadcast the canonical Twin projection.

THE DEFECT
    `POST /api/hardware/telemetry` called `forward_to_twin(...)` AND
    `await broadcast_twin_update(vid)`.
    `POST /api/telemetry` called `forward_to_twin(...)` and stopped there.

    So simulated telemetry reached the Twin but never produced a `twin_vehicle_update`
    frame. The frontend deliberately IGNORES the legacy `telemetry_update` frame (P6.1 -
    it used to fabricate position/friction/comm_confidence), so the HMI vehicle slice was
    populated once from `connection_established` at page load and never again.

    Symptom: the Twin held speed_mps=0.7859 freshness=CURRENT while the S2 Vehicle screen
    showed a frozen 1.8 km/h "STALE 3+ minutes", and only a browser refresh moved it.

    Measured before the fix: 23 `telemetry_update` frames in 6 s, ZERO
    `twin_vehicle_update` frames, while telemetry_ingest.accepted climbed steadily.

WHAT THIS PINS
    Both ingresses emit the canonical projection. Nothing here asserts a safety value the
    backend did not itself produce, and nothing is fabricated.

All telemetry here is SIMULATED. No physical hardware is involved.
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

import app.main as backend  # noqa: E402
from app.main import app  # noqa: E402

_SEQ = [12_400_000]


def next_seq():
    _SEQ[0] += 1
    return _SEQ[0]


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture(autouse=True)
def restore_shared_state():
    """This module posts telemetry; put the session-wide bookkeeping back."""
    ingestor = backend.twin_ingestor
    last_seq = dict(ingestor._last_sequence) if ingestor is not None else None
    backend_seq = dict(backend.last_sequence_by_vehicle)
    dedup = dict(backend.deduplication_store)
    try:
        yield
    finally:
        backend.last_sequence_by_vehicle.clear()
        backend.last_sequence_by_vehicle.update(backend_seq)
        backend.deduplication_store.clear()
        backend.deduplication_store.update(dedup)
        if ingestor is not None and last_seq is not None:
            ingestor._last_sequence = last_seq


def simulated_payload(vehicle_id="TRUCK_01", rpm=180.0, speed_mps=0.7859):
    """The shape `run_live_demo.py` posts: a generator frame plus a sequence."""
    return {
        "vehicle_id": vehicle_id,
        "sequence": next_seq(),
        "rpm": rpm,
        "speed_mps": speed_mps,
        "communication_state": "HEALTHY",
    }


def first_frame_after_post(ws):
    """
    Read exactly ONE frame.

    Every accepted /api/telemetry POST emits at least one frame (the legacy
    `telemetry_update`), so a single blocking read can never hang - unlike a loop, which
    wedges pytest the moment the frame under test is missing, i.e. exactly the pre-fix
    condition. The canonical projection is broadcast BEFORE the legacy frame (mirroring
    /api/hardware/telemetry), so frame #1 is the assertion point.
    """
    return ws.receive_json()


# ---------------------------------------------------------------------
# THE REGRESSION
# ---------------------------------------------------------------------

def test_simulated_ingress_broadcasts_the_canonical_twin_projection(client):
    """THE defect: /api/telemetry updated the Twin but never broadcast it."""
    with client.websocket_connect("/api/ws") as ws:
        ws.receive_json()  # connection_established

        posted = client.post("/api/telemetry", json=simulated_payload(rpm=222.0))
        assert posted.status_code == 200, posted.text

        frame = first_frame_after_post(ws)

    assert frame.get("type") == "twin_vehicle_update", (
        "simulated telemetry produced no canonical Twin projection; first frame was %r. "
        "The HMI ignores telemetry_update by design, so it would never see this update."
        % frame.get("type")
    )


def test_broadcast_carries_the_value_the_twin_actually_holds(client):
    """The frame must carry Twin state, not the raw posted payload."""
    with client.websocket_connect("/api/ws") as ws:
        ws.receive_json()
        client.post("/api/telemetry", json=simulated_payload(rpm=333.0))
        frame = first_frame_after_post(ws)

    assert frame.get("type") == "twin_vehicle_update", frame.get("type")
    data = frame["data"]
    assert data["vehicle_id"] == "TRUCK_01"

    dynamic = data["dynamic"]
    assert dynamic["rpm"]["value"] == 333.0

    # Provenance survives the broadcast: the simulated ingress is never HARDWARE.
    assert dynamic["rpm"]["source"] == "SIMULATION"
    assert dynamic["rpm"]["origin"] == "SIMULATION"

    # The canonical envelope the frontend normalizer requires.
    for key in ("value", "timestamp", "source", "origin", "quality",
                "age_s", "available", "clock_domain", "freshness"):
        assert key in dynamic["rpm"], "%s missing from the broadcast envelope" % key


def test_both_vehicles_broadcast_independently(client):
    """One vehicle's update must not stand in for the other's."""
    seen = {}
    with client.websocket_connect("/api/ws") as ws:
        ws.receive_json()
        for vehicle_id, rpm in (("TRUCK_01", 111.0), ("TRUCK_02", 444.0)):
            client.post("/api/telemetry", json=simulated_payload(vehicle_id, rpm=rpm))
            frame = first_frame_after_post(ws)
            assert frame.get("type") == "twin_vehicle_update", frame.get("type")
            data = frame["data"]
            seen[data["vehicle_id"]] = data["dynamic"]["rpm"]["value"]
            ws.receive_json()  # the legacy telemetry_update that follows

    assert seen.get("TRUCK_01") == 111.0, seen
    assert seen.get("TRUCK_02") == 444.0, seen


def test_hardware_ingress_still_broadcasts(client):
    """The path that already worked must keep working."""
    with client.websocket_connect("/api/ws") as ws:
        ws.receive_json()
        posted = client.post("/api/hardware/telemetry", json={
            "vehicle_id": "TRUCK_02", "sequence": next_seq(), "source": "DIRECT_WIFI",
            "rpm": 240.0, "speed": 2.5, "ax": 0.1, "ay": 0.0, "az": 9.81,
            "gx": 0.0, "gy": 0.0, "gz": 0.0, "rssi": -65, "snr": 9.2,
        })
        assert posted.status_code == 200
        frame = first_frame_after_post(ws)

    assert frame.get("type") == "twin_vehicle_update", frame.get("type")


def test_rejected_simulated_telemetry_broadcasts_no_projection(client):
    """A refused packet must not produce a Twin update - no phantom state."""
    with client.websocket_connect("/api/ws") as ws:
        ws.receive_json()
        # No sequence: the canonical boundary refuses it (REJECTED_INVALID_SEQUENCE).
        client.post("/api/telemetry", json={"vehicle_id": "TRUCK_01", "rpm": 5.0})
        frame = first_frame_after_post(ws)

    assert frame.get("type") != "twin_vehicle_update", (
        "a rejected packet broadcast a Twin projection")
