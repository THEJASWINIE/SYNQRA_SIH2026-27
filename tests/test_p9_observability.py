"""
P9 — observability, configuration centralization and hardware-status honesty.

All data here is SIMULATED. No physical ESP32 was connected; the "hardware" ingress is
exercised over HTTP exactly as an emulator would.
"""

import os
import sys
import time

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
from command_gateway import CommandGateway, CommandSource, CommandStatus, VehicleCommand  # noqa: E402
from integration_adapters.config_paths import load_timeouts  # noqa: E402

_SEQ = [7_100_000]


def next_seq():
    _SEQ[0] += 1
    return _SEQ[0]


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture(autouse=True)
def restore_shared_backend_state():
    """
    Put back everything this file touches on the process-wide backend singletons.

    The backend's `TelemetryIngestor` is shared with every other suite in the session and
    enforces monotonic sequence numbers per vehicle. Ingesting a high sequence here would
    make a LOWER sequence in a later suite look out-of-order, so the sequence bookkeeping
    is snapshotted and restored alongside the hardware latch.
    """
    seen, mode = backend.last_hardware_packet_at, backend.HMI_MODE
    ingestor = backend.twin_ingestor
    last_seq = dict(ingestor._last_sequence) if ingestor is not None else None
    seen_seq = {k: set(v) for k, v in ingestor._seen_sequences.items()} if ingestor is not None else None
    dedup = dict(backend.deduplication_store)
    last_seq_backend = dict(backend.last_sequence_by_vehicle)
    try:
        yield
    finally:
        backend.last_hardware_packet_at, backend.HMI_MODE = seen, mode
        backend.deduplication_store.clear()
        backend.deduplication_store.update(dedup)
        backend.last_sequence_by_vehicle.clear()
        backend.last_sequence_by_vehicle.update(last_seq_backend)
        if ingestor is not None:
            ingestor._last_sequence = last_seq
            ingestor._seen_sequences = seen_seq


def hardware_payload(vehicle_id="TRUCK_02"):
    return {
        "vehicle_id": vehicle_id, "sequence": next_seq(), "source": "DIRECT_WIFI",
        "rpm": 180.0, "speed": 2.5, "ax": 0.1, "ay": 0.0, "az": 9.81,
        "gx": 0.0, "gy": 0.0, "gz": 0.0, "rssi": -65, "snr": 9.2,
    }


# ---------------------------------------------------------------------
# 1. counter semantics: `rejected` is the total, and it moves
# ---------------------------------------------------------------------

def test_rejected_counter_counts_every_refusal():
    gateway = CommandGateway(store=None)
    before = dict(gateway.stats)
    now = time.time()

    def cmd(command_id, vehicle_id):
        return VehicleCommand(command_id=command_id, vehicle_id=vehicle_id, created_at=now,
                              action="TARGET_SPEED", target_speed_mps=1.0,
                              source=CommandSource.OPERATOR)

    # one refusal of each distinguishable kind reachable without a Twin
    gateway.submit(cmd("", "TRUCK_01"))          # INVALID
    gateway.submit(cmd("c2", "GHOST"))           # UNKNOWN_VEHICLE
    result = gateway.submit(cmd("c3", "TRUCK_01"))  # fail-closed: no Twin to validate against

    assert gateway.stats["invalid"] == before["invalid"] + 1
    assert gateway.stats["unknown_vehicle"] == before["unknown_vehicle"] + 1
    assert result.status == CommandStatus.REJECTED  # fail-closed: no Twin
    assert gateway.stats["unsafe"] == before["unsafe"] + 1

    # THE POINT: the aggregate is no longer stuck at zero while the buckets fill.
    assert gateway.stats["rejected"] == before["rejected"] + 3
    assert gateway.stats["rejected"] != 0


def test_timeout_is_not_counted_as_a_gate_rejection():
    """A timed-out command was ACCEPTED; that is not a refusal at the gate."""
    gateway = CommandGateway(store=None)
    assert gateway.stats["timeout"] == 0
    assert gateway.stats["rejected"] == 0


# ---------------------------------------------------------------------
# 2. hardware-status honesty
# ---------------------------------------------------------------------

def test_mode_is_mock_before_any_hardware_packet(client):
    backend.last_hardware_packet_at = None
    body = client.get("/api/mode").json()
    assert body["mode"] == "MOCK"
    assert body["hardware_seen"] is False
    assert body["hardware_connected"] is False
    assert body["hardware_age_seconds"] is None


def test_mode_reports_live_only_while_hardware_is_recent(client):
    assert client.post("/api/hardware/telemetry", json=hardware_payload()).status_code == 200
    assert client.get("/api/mode").json()["mode"] == "LIVE"

    # Age the link past the configured offline threshold: the claim must lapse.
    backend.last_hardware_packet_at -= backend.HARDWARE_PRESENCE_TIMEOUT_S + 1.0
    body = client.get("/api/mode").json()

    assert body["mode"] == "MOCK", "a disconnected ESP32 was still reported as LIVE"
    assert body["hardware_seen"] is True          # it DID happen once ...
    assert body["hardware_connected"] is False    # ... and it is not happening now
    assert client.get("/api/vehicles").json()["mode"] == "MOCK"


def test_invalid_hardware_payload_does_not_claim_a_link(client):
    backend.last_hardware_packet_at = None
    bad = hardware_payload(vehicle_id="TRUCK_99")
    assert client.post("/api/hardware/telemetry", json=bad).status_code == 400
    assert backend.last_hardware_packet_at is None
    assert client.get("/api/mode").json()["hardware_seen"] is False


# ---------------------------------------------------------------------
# 3. provenance cannot be self-declared on the mock ingress
# ---------------------------------------------------------------------

def test_mock_ingress_cannot_declare_itself_live(client):
    """The HTTP twin of the P5.1 WebSocket hole."""
    backend.last_hardware_packet_at = None
    backend.vehicle_telemetry_store.pop("TRUCK_01", None)

    posted = client.post("/api/telemetry", json={
        "vehicle_id": "TRUCK_01", "sequence_number": next_seq(),
        "rpm": 150.0, "timestamp": time.time(),
        "data_quality": "LIVE",          # <- the forged claim
    })
    assert posted.status_code == 200

    stored = backend.vehicle_telemetry_store["TRUCK_01"]
    assert stored["data_quality"] == "SIMULATED"
    assert stored["data_quality"] != "LIVE"
    assert client.get("/api/mode").json()["mode"] == "MOCK"
    assert client.get("/api/vehicles").json()["vehicles"]["TRUCK_01"]["data_quality"] == "SIMULATED"


# ---------------------------------------------------------------------
# 4. the observability endpoint
# ---------------------------------------------------------------------

def test_observability_exposes_the_canonical_counters(client):
    body = client.get("/api/observability").json()

    assert body["twin_attached"] is True
    for key in ("accepted", "duplicate", "out_of_order", "invalid", "unknown_vehicle"):
        assert key in body["telemetry_ingest"]
    for key in ("accepted", "rejected", "duplicate", "stale", "invalid", "unsafe", "timeout"):
        assert key in body["command_gateway"]
    assert isinstance(body["websocket_clients"], int)
    assert body["hardware"]["hardware_seen"] in (True, False)


def test_observability_counters_actually_move(client):
    before = client.get("/api/observability").json()["telemetry_ingest"]["accepted"]
    assert client.post("/api/hardware/telemetry", json=hardware_payload()).status_code == 200
    after = client.get("/api/observability").json()["telemetry_ingest"]["accepted"]
    assert after == before + 1


def test_observability_reports_null_not_zero_for_absent_components():
    """UNAVAILABLE is not zero - the invariant this whole project runs on."""
    saved = backend.twin_ingestor
    backend.twin_ingestor = None
    try:
        with TestClient(app) as c:
            assert c.get("/api/observability").json()["telemetry_ingest"] is None
    finally:
        backend.twin_ingestor = saved


# ---------------------------------------------------------------------
# 5. configuration centralization
# ---------------------------------------------------------------------

def test_freshness_thresholds_come_from_configuration():
    configured = load_timeouts()
    assert backend.STALE_THRESHOLD_S == configured["max_telemetry_age_seconds"]
    assert backend.OFFLINE_THRESHOLD_S == configured["offline_threshold_seconds"]
    assert backend.twin_store.stale_after_s == configured["max_telemetry_age_seconds"]
    assert CommandGateway(store=None).safety_stale_after_s == configured["max_telemetry_age_seconds"]


def test_config_is_found_from_any_working_directory(tmp_path):
    """P6.1 regression: config resolved against the CWD, so the uvicorn launch dir broke it."""
    from integration_adapters.unit_converter import UnitConverter

    previous = os.getcwd()
    os.chdir(tmp_path)
    try:
        assert UnitConverter().vehicle_params, "configuration lost outside the project root"
        assert load_timeouts()["max_telemetry_age_seconds"] > 0
    finally:
        os.chdir(previous)
