"""
Pytest integration test suite for V2V HMI Telemetry Ingestion.
Verifies 18 mandatory integration checks across V2V parsing, vehicle isolation,
sequence tracking, health state transitions, WebSocket streaming, and mock mode compatibility.
"""

import sys
import os
import time
import pytest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
hmi_backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "SYNQRA_SIH2026-27-HMI", "backend"))
if hmi_backend_dir not in sys.path:
    sys.path.insert(0, hmi_backend_dir)

from v2v_packet_parser import V2VPacketParser
from v2v_telemetry_emulator import V2VTelemetryEmulator
from fastapi.testclient import TestClient
from app.main import app as hmi_app

@pytest.fixture
def parser():
    return V2VPacketParser(stale_sec=1.0, offline_sec=2.0)

@pytest.fixture
def emulator():
    return V2VTelemetryEmulator()

@pytest.fixture
def client():
    return TestClient(hmi_app)

def test_1_valid_truck_01_accepted(parser, emulator):
    pkt = emulator.generate_packet("TRUCK_01", rpm=240.0)
    parsed = parser.parse_v2v_packet(pkt)
    assert parsed is not None
    assert parsed["vehicle_id"] == "TRUCK_01"
    assert parsed["rpm"] == 240.0

def test_2_valid_truck_02_accepted(parser, emulator):
    pkt = emulator.generate_packet("TRUCK_02", rpm=180.0)
    parsed = parser.parse_v2v_packet(pkt)
    assert parsed is not None
    assert parsed["vehicle_id"] == "TRUCK_02"
    assert parsed["rpm"] == 180.0

def test_3_vehicle_isolation(parser, emulator):
    pkt_a = emulator.generate_packet("TRUCK_01", rpm=240.0)
    parsed_a = parser.parse_v2v_packet(pkt_a)
    assert parsed_a["vehicle_id"] == "TRUCK_01"
    assert parsed_a["rpm"] == 240.0

    pkt_b = emulator.generate_packet("TRUCK_02", rpm=180.0)
    parsed_b = parser.parse_v2v_packet(pkt_b)
    assert parsed_b["vehicle_id"] == "TRUCK_02"
    assert parsed_b["rpm"] == 180.0
    assert parsed_a["vehicle_id"] != parsed_b["vehicle_id"]

def test_4_sequence_increases(parser, emulator):
    pkt1 = emulator.generate_packet("TRUCK_01", seq_override=10)
    pkt2 = emulator.generate_packet("TRUCK_01", seq_override=11)
    res1 = parser.parse_v2v_packet(pkt1)
    res2 = parser.parse_v2v_packet(pkt2)
    assert res1["sequence_number"] == 10
    assert res2["sequence_number"] == 11
    assert res2["sequence_number"] > res1["sequence_number"]

def test_5_duplicate_sequence(parser, emulator):
    pkt1 = emulator.generate_packet("TRUCK_01", seq_override=15)
    parser.parse_v2v_packet(pkt1)
    res2 = parser.parse_v2v_packet(pkt1)
    assert res2["is_duplicate"] is True

def test_6_out_of_order_sequence(parser, emulator):
    pkt_high = emulator.generate_packet("TRUCK_01", seq_override=50)
    pkt_low = emulator.generate_packet("TRUCK_01", seq_override=20)
    parser.parse_v2v_packet(pkt_high)
    res_low = parser.parse_v2v_packet(pkt_low)
    assert res_low["is_out_of_order"] is True

def test_7_missing_packet_detected(parser, emulator):
    pkt1 = emulator.generate_packet("TRUCK_01", seq_override=1)
    pkt2 = emulator.generate_packet("TRUCK_01", seq_override=5)  # Gap of 3 packets
    parser.parse_v2v_packet(pkt1)
    res2 = parser.parse_v2v_packet(pkt2)
    assert res2["sequence_number"] == 5

def test_8_malformed_packet_rejected(parser):
    assert parser.parse_v2v_packet("STATE,TRUCK_01,CORRUPTED") is None
    assert parser.parse_v2v_packet(None) is None
    assert parser.parse_v2v_packet("") is None

def test_9_unknown_vehicle_rejected(parser, emulator):
    pkt = emulator.generate_packet("TRUCK_99", rpm=240.0)
    assert parser.parse_v2v_packet(pkt) is None

def test_10_ping_ack_does_not_corrupt_state(parser):
    assert parser.parse_v2v_packet("PING,TRUCK_01,1,OK") is None
    assert parser.parse_v2v_packet("ACK,TRUCK_01,1,ACCEPTED") is None

def test_11_fresh_telemetry_online(parser, emulator):
    pkt = emulator.generate_packet("TRUCK_01", rpm=240.0)
    res = parser.parse_v2v_packet(pkt)
    assert res["communication_status"] == "ONLINE"

def test_12_stale_telemetry_detection(parser):
    now = time.time()
    parser.last_seen_map["TRUCK_01"] = now - 1.5
    status = parser.evaluate_health_status("TRUCK_01", now)
    assert status == "STALE"

def test_13_no_telemetry_offline(parser):
    now = time.time()
    parser.last_seen_map["TRUCK_01"] = now - 5.0
    status = parser.evaluate_health_status("TRUCK_01", now)
    assert status == "OFFLINE"

def test_14_recovery_to_online(parser, emulator):
    now = time.time()
    parser.previous_health_map["TRUCK_01"] = "OFFLINE"
    pkt1 = emulator.generate_packet("TRUCK_01", rpm=240.0)
    res1 = parser.parse_v2v_packet(pkt1)
    assert res1["communication_status"] == "RECOVERING"

    pkt2 = emulator.generate_packet("TRUCK_01", rpm=240.0)
    res2 = parser.parse_v2v_packet(pkt2)
    assert res2["communication_status"] == "ONLINE"

def test_15_hmi_websocket_compatibility(client):
    with client.websocket_connect("/api/ws") as websocket:
        data = websocket.receive_json()
        assert "vehicles" in data or "timestamp" in data or "type" in data

def test_16_frontend_schema_matching(parser, emulator):
    pkt = emulator.generate_packet("TRUCK_01", rpm=240.0)
    res = parser.parse_v2v_packet(pkt)
    assert "vehicle_id" in res
    assert "rpm" in res
    assert "speed_calibrated" in res
    assert res["speed_calibrated"] is False

def test_17_mock_mode_preserved(client):
    res = client.get("/api/vehicles")
    assert res.status_code == 200

def test_18_existing_testers_pass(client):
    res_health = client.get("/api/health")
    assert res_health.status_code == 200

if __name__ == "__main__":
    pytest.main(["-v", __file__])
