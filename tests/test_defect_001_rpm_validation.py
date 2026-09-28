"""
D001 — RPM validation regression tests.

Verifies that NaN, ±Inf, and negative RPM are rejected BEFORE any clamping.
Verifies RPM 0.0 (motor stopped) remains valid.
Tests both the direct V2V parser path and the HMI backend hardware telemetry path.
"""

import math
import sys
import os

import pytest

# Ensure imports work
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.path.insert(0, os.path.join(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")), "SYNQRA_SIH2026-27-main"))

from v2v_packet_parser import V2VPacketParser


# ---------------------------------------------------------------------------
# V2V Packet Parser — direct unit tests
# ---------------------------------------------------------------------------

VALID_PACKET = "STATE,TRUCK_01,28,240.00,0.00,-496,132,16696,703,342,191"


def _packet_with_rpm(rpm_str: str) -> str:
    """Build a frozen V2V packet with a specific RPM field value."""
    return f"STATE,TRUCK_01,1,{rpm_str},0.00,-496,132,16696,703,342,191"


class TestV2VParserRPMValidation:

    def test_valid_positive_rpm_accepted(self):
        parser = V2VPacketParser()
        result = parser.parse_v2v_packet(VALID_PACKET)
        assert result is not None
        assert result["rpm"] == 240.0

    def test_valid_zero_rpm_accepted(self):
        """RPM 0.0 (motor stopped) is a legitimate measured value."""
        parser = V2VPacketParser()
        result = parser.parse_v2v_packet(_packet_with_rpm("0.0"))
        assert result is not None
        assert result["rpm"] == 0.0

    def test_nan_rpm_rejected(self):
        parser = V2VPacketParser()
        result = parser.parse_v2v_packet(_packet_with_rpm("nan"))
        assert result is None, "NaN RPM must be rejected, not laundered to 0.0"

    def test_positive_inf_rpm_rejected(self):
        parser = V2VPacketParser()
        result = parser.parse_v2v_packet(_packet_with_rpm("inf"))
        assert result is None, "+Inf RPM must be rejected"

    def test_negative_inf_rpm_rejected(self):
        parser = V2VPacketParser()
        result = parser.parse_v2v_packet(_packet_with_rpm("-inf"))
        assert result is None, "-Inf RPM must be rejected"

    def test_negative_rpm_rejected(self):
        parser = V2VPacketParser()
        result = parser.parse_v2v_packet(_packet_with_rpm("-5.0"))
        assert result is None, "Negative RPM must be rejected, not clamped to 0.0"

    def test_negative_small_rpm_rejected(self):
        parser = V2VPacketParser()
        result = parser.parse_v2v_packet(_packet_with_rpm("-0.001"))
        assert result is None, "Small negative RPM must be rejected"

    def test_rpm_not_clamped_to_zero(self):
        """Verify max(0.0, rpm) is no longer used — negative RPM must not become 0.0."""
        parser = V2VPacketParser()
        result = parser.parse_v2v_packet(_packet_with_rpm("-100"))
        assert result is None, "Negative RPM must not be clamped to 0.0"


# ---------------------------------------------------------------------------
# Full ingestion path — V2V packet -> TelemetryIngestor -> Twin
# ---------------------------------------------------------------------------

class TestFullIngestionPathRPM:

    def _make_ingestor(self):
        from telemetry_ingest import TelemetryIngestor
        from twin.twin_state_store import TwinMode, TwinStateStore

        store = TwinStateStore(mode=TwinMode.HYBRID, stale_after_s=3.0)
        ingestor = TelemetryIngestor(store)
        return ingestor, store

    def test_nan_rpm_rejected_via_full_ingestion(self):
        ingestor, store = self._make_ingestor()
        result = ingestor.ingest_v2v_packet(_packet_with_rpm("nan"))
        assert not result.accepted
        assert store.get_all_vehicles() == {}

    def test_negative_rpm_rejected_via_full_ingestion(self):
        ingestor, store = self._make_ingestor()
        result = ingestor.ingest_v2v_packet(_packet_with_rpm("-5.0"))
        assert not result.accepted
        assert store.get_all_vehicles() == {}

    def test_valid_zero_rpm_accepted_via_full_ingestion(self):
        ingestor, store = self._make_ingestor()
        result = ingestor.ingest_v2v_packet(_packet_with_rpm("0.0"))
        assert result.accepted
        assert result.vehicle_id == "TRUCK_01"


# ---------------------------------------------------------------------------
# HMI backend /api/hardware/telemetry — RPM validation
# ---------------------------------------------------------------------------

class TestHMIBackendRPMValidation:

    @pytest.fixture(autouse=True)
    def setup_client(self):
        sys.path.insert(0, os.path.join(
            os.path.dirname(__file__), "..", "SYNQRA_SIH2026-27-HMI", "backend"
        ))
        from app.main import app, vehicle_telemetry_store, deduplication_store, last_sequence_by_vehicle
        from fastapi.testclient import TestClient

        self.client = TestClient(app)
        self.store = vehicle_telemetry_store
        self.dedup = deduplication_store
        self.last_seq = last_sequence_by_vehicle
        vehicle_telemetry_store.clear()
        deduplication_store.clear()
        last_sequence_by_vehicle.clear()
        yield

    def _payload(self, rpm=240.0, seq=1):
        return {
            "vehicle_id": "TRUCK_01",
            "sequence": seq,
            "rpm": rpm,
            "speed": 0.0,
            "ax": 0, "ay": 0, "az": 16384,
            "gx": 0, "gy": 0, "gz": 0,
            "rssi": -75, "snr": 9.5,
            "source": "DIRECT_WIFI",
        }

    def test_valid_rpm_accepted(self):
        r = self.client.post("/api/hardware/telemetry", json=self._payload(rpm=240.0))
        assert r.status_code == 200
        assert r.json()["status"] == "ACCEPTED"

    def test_zero_rpm_accepted(self):
        r = self.client.post("/api/hardware/telemetry", json=self._payload(rpm=0.0))
        assert r.status_code == 200
        assert r.json()["status"] == "ACCEPTED"

    def _post_raw(self, payload_dict):
        """Post a payload using allow_nan JSON encoding (NaN/Inf are not standard JSON)."""
        import json as _json
        raw = _json.dumps(payload_dict, allow_nan=True)
        return self.client.post(
            "/api/hardware/telemetry",
            content=raw,
            headers={"content-type": "application/json"},
        )

    def test_nan_rpm_rejected_422(self):
        r = self._post_raw(self._payload(rpm=float("nan")))
        assert r.status_code == 422

    def test_positive_inf_rpm_rejected_422(self):
        r = self._post_raw(self._payload(rpm=float("inf")))
        assert r.status_code == 422

    def test_negative_inf_rpm_rejected_422(self):
        r = self._post_raw(self._payload(rpm=float("-inf")))
        assert r.status_code == 422

    def test_negative_rpm_rejected_422(self):
        r = self.client.post("/api/hardware/telemetry", json=self._payload(rpm=-5.0))
        assert r.status_code == 422
        # Verify no cache mutation
        assert "TRUCK_01" not in self.store
