"""
TC-ING-005: Master Prompt Requirement — Negative Speed Rejection

Requirements:
- Negative physical vehicle speed is invalid telemetry.
- Reject it before state mutation.
- Do not reinterpret/clamp it to 0.0.
- Verify through actual ingestion boundary and HTTP endpoints.

Evidence captured:
- expected
- actual
- status / reason
- Twin unchanged
- cache unchanged
- no WS broadcast
"""

import pytest
from fastapi.testclient import TestClient

from telemetry_ingest import (
    TelemetryIngestor,
    Transport,
    REJECT_NEGATIVE_SPEED,
)
from twin.twin_state_store import TwinStateStore, TwinMode


@pytest.fixture
def store():
    return TwinStateStore(mode=TwinMode.HYBRID)


@pytest.fixture
def ingestor(store):
    return TelemetryIngestor(store)


def base_payload(vehicle_id="TRUCK_01", seq=1, speed=5.0):
    return {
        "vehicle_id": vehicle_id,
        "sequence_number": seq,
        "speed": speed,
        "rpm": 120.0,
        "acceleration": {"x": 0.0, "y": 0.0, "z": 9.81},
        "gyroscope": {"x": 0.0, "y": 0.0, "z": 0.0},
    }


class TestMasterTCING005NegativeSpeed:
    """Rigorous tests for TC-ING-005 Negative Speed Rejection."""

    @pytest.mark.parametrize("neg_speed", [-0.001, -1.0, -15.5, -100.0])
    def test_negative_speed_rejected_at_ingestor_boundary(self, ingestor, store, neg_speed):
        payload = base_payload(speed=neg_speed)
        
        # Ingestion attempt
        result = ingestor.ingest_parsed_record(payload, transport=Transport.DIRECT_WIFI)

        # Evidence assertions
        expected_accepted = False
        actual_accepted = result.accepted
        expected_reason = REJECT_NEGATIVE_SPEED
        actual_reason = result.reason

        assert actual_accepted == expected_accepted, f"Expected {expected_accepted}, got {actual_accepted}"
        assert actual_reason == expected_reason, f"Expected reason {expected_reason}, got {actual_reason}"

        # Twin unchanged: vehicle must not exist in Twin store
        assert store.get_vehicle("TRUCK_01") is None
        assert store.get_all_vehicles() == {}

    @pytest.mark.parametrize("neg_speed", [-0.01, -5.0])
    def test_v2v_packet_parser_rejects_negative_speed(self, neg_speed):
        from v2v_packet_parser import V2VPacketParser
        parser = V2VPacketParser()
        # Wire packet: STATE,TRUCK_01,seq,rpm,speed,ax,ay,az,gx,gy,gz
        packet = f"STATE,TRUCK_01,1,240.0,{neg_speed},0,0,16384,0,0,0"
        parsed = parser.parse_v2v_packet(packet)
        assert parsed is None, f"Expected V2VPacketParser to reject packet with negative speed {neg_speed}"


class TestMasterTCING005HttpEndpoints:
    """Verify HTTP endpoints reject negative speed with no cache/Twin/WS mutation."""

    @pytest.fixture(autouse=True)
    def setup_backend(self):
        import sys
        import os
        backend_dir = os.path.join(os.getcwd(), "SYNQRA_SIH2026-27-HMI", "backend")
        if backend_dir not in sys.path:
            sys.path.insert(0, backend_dir)
        from app.main import app, vehicle_telemetry_store, twin_store, active_websockets
        self.app = app
        self.cache = vehicle_telemetry_store
        self.twin = twin_store
        self.active_websockets = active_websockets
        self.client = TestClient(app)
        self.cache.clear()
        if self.twin is not None:
            with self.twin._lock:
                self.twin._vehicles.clear()
        yield
        self.cache.clear()
        if self.twin is not None:
            with self.twin._lock:
                self.twin._vehicles.clear()

    def test_api_telemetry_rejects_negative_speed_no_mutation(self):
        payload = {
            "vehicle_id": "TRUCK_01",
            "speed": -2.5,
            "rpm": 120.0,
            "sequence": 1
        }
        res = self.client.post("/api/telemetry", json=payload)
        
        # Evidence check
        expected_status = 400
        actual_status = res.status_code
        assert actual_status == expected_status
        assert "negative speed is invalid" in res.json()["detail"]

        # Cache unchanged
        assert "TRUCK_01" not in self.cache

        # Twin unchanged
        if self.twin is not None:
            assert self.twin.get_vehicle("TRUCK_01") is None

    def test_api_hardware_telemetry_rejects_negative_speed_no_mutation(self):
        payload = {
            "vehicle_id": "TRUCK_01",
            "sequence": 105,
            "source": "DIRECT_WIFI",
            "rpm": 200.0,
            "speed": -4.2
        }
        res = self.client.post("/api/hardware/telemetry", json=payload)
        
        # Expected: HTTP 422 Unprocessable Entity
        assert res.status_code == 422
        assert "Negative speed" in res.json()["detail"]
        assert "TRUCK_01" not in self.cache

    def test_negative_speed_does_not_broadcast_to_websocket(self):
        # Open websocket and ensure no broadcast occurs for rejected negative speed
        with self.client.websocket_connect("/api/ws") as ws:
            init_msg = ws.receive_json()
            assert init_msg["type"] == "connection_established"

            # Post negative speed
            bad_payload = {
                "vehicle_id": "TRUCK_01",
                "speed": -3.0,
                "rpm": 100.0,
                "sequence": 10
            }
            res = self.client.post("/api/telemetry", json=bad_payload)
            assert res.status_code == 400

            # Post a valid packet to flush/probe websocket queue
            valid_payload = {
                "vehicle_id": "TRUCK_02",
                "speed": 1.5,
                "rpm": 80.0,
                "sequence": 11
            }
            res2 = self.client.post("/api/telemetry", json=valid_payload)
            assert res2.status_code == 200

            # The next WS message received MUST be for TRUCK_02, never TRUCK_01 with negative speed
            # Both ingresses now emit the canonical `twin_vehicle_update` first; this
            # check is about the legacy frame's contents, so scan past it.
            msg = ws.receive_json()
            while msg.get("type") == "twin_vehicle_update":
                msg = ws.receive_json()
            assert msg["type"] == "telemetry_update"
            assert msg["data"]["vehicle_id"] == "TRUCK_02"
            assert msg["data"]["speed"] == 1.5
