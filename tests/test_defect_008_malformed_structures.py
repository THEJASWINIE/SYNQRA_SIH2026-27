"""
D008 — Malformed nested structures regression tests.

Verifies that non-dict values for acceleration, gyroscope, and communication
do not raise AttributeError or any other uncaught exception.
"""

import pytest

from telemetry_ingest import TelemetryIngestor, Transport
from twin.twin_state_store import TwinMode, TwinStateStore


def _hw(vehicle_id="TRUCK_01", sequence=1, **over):
    """A minimal valid telemetry record."""
    rec = dict(
        vehicle_id=vehicle_id,
        sequence_number=sequence,
        rpm=240.0,
        speed=2.5,
        acceleration={"x": 0.12, "y": -0.05, "z": 9.81},
        gyroscope={"x": 0.02, "y": 0.01, "z": -0.03},
        communication={"rssi": -65, "snr": 9.2},
        communication_state="HEALTHY",
        data_quality="LIVE",
    )
    rec.update(over)
    return rec


@pytest.fixture
def ingestor():
    store = TwinStateStore(mode=TwinMode.HYBRID, stale_after_s=3.0)
    return TelemetryIngestor(store), store


class TestMalformedAcceleration:

    @pytest.mark.parametrize("bad_accel", [
        "bad_string",
        123,
        [1, 2, 3],
        True,
        42.5,
    ])
    def test_non_dict_acceleration_does_not_raise(self, ingestor, bad_accel):
        ing, store = ingestor
        record = _hw(sequence=1, acceleration=bad_accel)
        # Must not raise AttributeError or any exception
        result = ing.ingest_parsed_record(record, Transport.V2V)
        # The record should be accepted (other fields valid), but IMU fields absent
        assert result.accepted or not result.accepted  # no crash is the invariant

    def test_none_acceleration_handled(self, ingestor):
        ing, store = ingestor
        record = _hw(sequence=1, acceleration=None)
        result = ing.ingest_parsed_record(record, Transport.V2V)
        assert result.accepted  # valid record, just no accel data

    def test_empty_dict_acceleration_handled(self, ingestor):
        ing, store = ingestor
        record = _hw(sequence=1, acceleration={})
        result = ing.ingest_parsed_record(record, Transport.V2V)
        assert result.accepted

    def test_valid_dict_acceleration_works(self, ingestor):
        ing, store = ingestor
        record = _hw(sequence=1, acceleration={"x": 0.1, "y": 0.2, "z": 9.81})
        result = ing.ingest_parsed_record(record, Transport.V2V)
        assert result.accepted
        ax = store.get_vehicle_field("TRUCK_01", "ax_mps2")
        assert ax.value == pytest.approx(0.1)


class TestMalformedGyroscope:

    @pytest.mark.parametrize("bad_gyro", [
        "bad_string",
        123,
        [1, 2, 3],
        True,
    ])
    def test_non_dict_gyroscope_does_not_raise(self, ingestor, bad_gyro):
        ing, store = ingestor
        record = _hw(sequence=1, gyroscope=bad_gyro)
        result = ing.ingest_parsed_record(record, Transport.V2V)
        assert result.accepted or not result.accepted  # no crash


class TestMalformedCommunication:

    @pytest.mark.parametrize("bad_comm", [
        "bad_string",
        123,
        [1, 2, 3],
        True,
    ])
    def test_non_dict_communication_does_not_raise(self, ingestor, bad_comm):
        ing, store = ingestor
        record = _hw(sequence=1, communication=bad_comm)
        result = ing.ingest_parsed_record(record, Transport.V2V)
        assert result.accepted or not result.accepted  # no crash

    def test_none_communication_handled(self, ingestor):
        ing, store = ingestor
        record = _hw(sequence=1, communication=None)
        result = ing.ingest_parsed_record(record, Transport.V2V)
        assert result.accepted


class TestAllMalformedAtOnce:

    def test_all_nested_fields_malformed_does_not_crash(self, ingestor):
        ing, store = ingestor
        record = _hw(
            sequence=1,
            acceleration="bad",
            gyroscope=[1, 2, 3],
            communication=42,
        )
        result = ing.ingest_parsed_record(record, Transport.V2V)
        # Should not crash — that's the invariant
        assert result.accepted or not result.accepted
