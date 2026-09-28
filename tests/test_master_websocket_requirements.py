"""
GAP 3 — Complete WebSocket Test Matrix (Master Prompt Requirement)

Verifies:
A. Initial connection & handshake (connection_established, empty vehicles dict, twin projection)
B. Valid telemetry delivery
C. Malformed inbound WS message (server resilience, no crash, no Twin corruption)
D. Client disconnect & cleanup
E. Client reconnect & state resumption
F. Delayed telemetry / out-of-order policy preserved
G. Stale telemetry / freshness semantics
H. Two vehicles isolation (TRUCK_01 does not alter TRUCK_02)
I. Rapid sequential updates (ordered, no corruption)
"""

import json
import time
import sys
import os
import pytest
from fastapi.testclient import TestClient

backend_dir = os.path.join(os.path.dirname(__file__), "..", "SYNQRA_SIH2026-27-HMI", "backend")
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from app.main import (
    app,
    vehicle_telemetry_store,
    deduplication_store,
    last_sequence_by_vehicle,
    active_websockets,
    twin_store,
    twin_ingestor,
)


@pytest.fixture(autouse=True)
def clean_system_state():
    vehicle_telemetry_store.clear()
    deduplication_store.clear()
    last_sequence_by_vehicle.clear()
    if twin_store is not None:
        with twin_store._lock:
            twin_store._vehicles.clear()
    if twin_ingestor is not None:
        twin_ingestor._last_sequence.clear()
        twin_ingestor._seen_sequences.clear()
    yield
    vehicle_telemetry_store.clear()
    deduplication_store.clear()
    last_sequence_by_vehicle.clear()
    if twin_store is not None:
        with twin_store._lock:
            twin_store._vehicles.clear()
    if twin_ingestor is not None:
        twin_ingestor._last_sequence.clear()
        twin_ingestor._seen_sequences.clear()


@pytest.fixture
def client():
    return TestClient(app)


def next_legacy_frame(ws, limit=6):
    """
    Return the next legacy `telemetry_update`, skipping canonical Twin projections.

    Both telemetry ingresses now emit `twin_vehicle_update` first (the frame the HMI
    actually consumes). These checks assert on the legacy compatibility frame, so they
    scan past the canonical one rather than assuming it is absent - the same idiom
    `test_twin_projection._drain_for` and `test_ws_ingestion_boundary.receive_skipping_twin`
    already use.
    """
    for _ in range(limit):
        message = ws.receive_json()
        if message.get("type") != "twin_vehicle_update":
            return message
    raise AssertionError("only twin_vehicle_update frames received")


class TestMasterWebSocketMatrix:
    """Master Prompt Complete WebSocket Requirements."""

    def test_case_a_initial_connection(self, client):
        """Check A: Handshake on /api/ws."""
        with client.websocket_connect("/api/ws") as ws:
            init = ws.receive_json()
            assert init["type"] == "connection_established"
            assert "Connected to HMI Independent Backend" in init["message"]
            assert init["vehicles"] == {}  # D005: empty dict, never raw cache
            assert "twin" in init
            assert "snapshot_timestamp" in init["twin"]

    def test_case_b_valid_telemetry_delivery(self, client):
        """Check B: Live telemetry broadcast to connected client."""
        with client.websocket_connect("/api/ws") as ws:
            _ = ws.receive_json()  # Handshake

            payload = {
                "vehicle_id": "TRUCK_01",
                "sequence": 1,
                "speed": 3.5,
                "rpm": 180.0,
                "data_quality": "LIVE"
            }
            res = client.post("/api/telemetry", json=payload)
            assert res.status_code == 200

            msg = next_legacy_frame(ws)
            assert msg["type"] == "telemetry_update"
            assert msg["data"]["vehicle_id"] == "TRUCK_01"
            assert msg["data"]["speed"] == 3.5
            assert msg["data"]["rpm"] == 180.0

    def test_case_c_malformed_inbound_ws_message(self, client):
        """Check C: Malformed inbound message does not crash server or corrupt Twin."""
        with client.websocket_connect("/api/ws") as ws:
            _ = ws.receive_json()

            # Send non-JSON text
            ws.send_text("MALFORMED_GARBAGE_PAYLOAD {{{")
            reply = ws.receive_json()
            assert reply["type"] == "error"
            assert reply["reason"] == "MALFORMED_JSON"

            # Verify server is still alive and responsive
            res = client.get("/api/health")
            assert res.status_code == 200

            # Verify Twin is not corrupted
            if twin_store is not None:
                assert twin_store.get_all_vehicles() == {}

    def test_case_d_client_disconnect(self, client):
        """Check D: Client disconnect removes client from active set."""
        initial_ws_count = len(active_websockets)
        with client.websocket_connect("/api/ws") as ws:
            _ = ws.receive_json()
            assert len(active_websockets) == initial_ws_count + 1

        # After exiting context, socket is closed and cleaned up
        assert len(active_websockets) == initial_ws_count

    def test_case_e_client_reconnect(self, client):
        """Check E: Client disconnects and reconnects, receiving fresh state."""
        # First connection establishes initial state
        with client.websocket_connect("/api/ws") as ws1:
            _ = ws1.receive_json()
            # Send telemetry while connected
            client.post("/api/telemetry", json={"vehicle_id": "TRUCK_01", "sequence": 1, "speed": 4.0, "rpm": 120.0})
            msg = next_legacy_frame(ws1)
            assert msg["data"]["speed"] == 4.0

        # Second connection (reconnect) receives fresh handshake containing projected Twin state
        with client.websocket_connect("/api/ws") as ws2:
            reconnect_init = ws2.receive_json()
            assert reconnect_init["type"] == "connection_established"
            assert "TRUCK_01" in reconnect_init["twin"]["vehicles"]

    def test_case_f_delayed_telemetry_out_of_order_policy(self, client):
        """Check F: Out-of-order telemetry rejected, not broadcast."""
        with client.websocket_connect("/api/ws") as ws:
            _ = ws.receive_json()

            # Sequence 10 (valid)
            res1 = client.post("/api/hardware/telemetry", json={
                "vehicle_id": "TRUCK_01",
                "sequence": 10,
                "source": "DIRECT_WIFI",
                "rpm": 150.0,
                "speed": 2.0
            })
            assert res1.status_code == 200

            # May receive twin_vehicle_update then telemetry_update
            received = []
            while len(received) < 2:
                received.append(ws.receive_json())
            telem_msg = next(m for m in received if m.get("type") == "telemetry_update")
            assert telem_msg["data"]["sequence_number"] == 10

            # Sequence 5 (delayed / out-of-order)
            res2 = client.post("/api/hardware/telemetry", json={
                "vehicle_id": "TRUCK_01",
                "sequence": 5,
                "source": "DIRECT_WIFI",
                "rpm": 150.0,
                "speed": 2.0
            })
            assert res2.status_code == 409
            assert res2.json()["status"] == "REJECTED_OUT_OF_ORDER"

            # Probe queue with sequence 11 to verify seq 5 was never broadcast
            res3 = client.post("/api/hardware/telemetry", json={
                "vehicle_id": "TRUCK_01",
                "sequence": 11,
                "source": "DIRECT_WIFI",
                "rpm": 160.0,
                "speed": 2.2
            })
            assert res3.status_code == 200
            received_next = []
            while len(received_next) < 2:
                received_next.append(ws.receive_json())
            next_telem = next(m for m in received_next if m.get("type") == "telemetry_update")
            assert next_telem["data"]["sequence_number"] == 11  # Next frame is 11, not 5

    def test_case_g_stale_telemetry_semantics(self, client):
        """Check G: Stale state transitions visible in telemetry status."""
        client.post("/api/hardware/telemetry", json={
            "vehicle_id": "TRUCK_01",
            "sequence": 1,
            "source": "DIRECT_WIFI",
            "rpm": 100.0,
            "speed": 1.5
        })
        # Check /api/vehicles
        v_res = client.get("/api/vehicles").json()
        assert v_res["vehicles"]["TRUCK_01"]["communication_status"] == "ONLINE"

        # Simulate age passing stale threshold
        vehicle_telemetry_store["TRUCK_01"]["timestamp"] = time.time() - 4.0
        v_stale = client.get("/api/vehicles").json()
        assert v_stale["vehicles"]["TRUCK_01"]["is_stale"] is True

    def test_case_h_two_vehicles_isolation(self, client):
        """Check H: TRUCK_01 updates do not alter TRUCK_02."""
        with client.websocket_connect("/api/ws") as ws:
            _ = ws.receive_json()

            # Seed TRUCK_02 with initial state
            client.post("/api/telemetry", json={
                "vehicle_id": "TRUCK_02",
                "sequence": 1,
                "speed": 1.2,
                "rpm": 60.0
            })
            msg_init_t2 = next_legacy_frame(ws)
            assert msg_init_t2["data"]["vehicle_id"] == "TRUCK_02"
            assert msg_init_t2["data"]["speed"] == 1.2

            # Stream updates to TRUCK_01
            client.post("/api/telemetry", json={
                "vehicle_id": "TRUCK_01",
                "sequence": 2,
                "speed": 5.8,
                "rpm": 250.0
            })
            msg_t1 = next_legacy_frame(ws)
            assert msg_t1["data"]["vehicle_id"] == "TRUCK_01"
            assert msg_t1["data"]["speed"] == 5.8

            # Verify TRUCK_02 in cache and Twin remained untouched
            assert vehicle_telemetry_store["TRUCK_02"]["speed"] == 1.2
            assert vehicle_telemetry_store["TRUCK_02"]["rpm"] == 60.0
            if twin_store is not None:
                assert twin_store.get_vehicle_field("TRUCK_02", "speed_mps").value != 5.8

    def test_case_i_rapid_sequential_updates(self, client):
        """Check I: Rapid sequential burst maintains strict order without loss."""
        with client.websocket_connect("/api/ws") as ws:
            _ = ws.receive_json()

            num_updates = 15
            for seq in range(1, num_updates + 1):
                client.post("/api/telemetry", json={
                    "vehicle_id": "TRUCK_01",
                    "sequence": seq,
                    "speed": float(seq) * 0.5,
                    "rpm": float(seq) * 20.0
                })

            for seq in range(1, num_updates + 1):
                msg = next_legacy_frame(ws)
                assert msg["type"] == "telemetry_update"
                assert msg["data"]["sequence"] == seq
                assert msg["data"]["speed"] == float(seq) * 0.5
