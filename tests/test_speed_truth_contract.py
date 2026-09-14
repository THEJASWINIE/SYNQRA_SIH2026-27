"""
HMI-DATA-01 — operational telemetry truth contract, backend side.

SOFTWARE ONLY. Every packet here is a hand-built record replayed through the canonical
ingestor or posted to the SIMULATED ingress. No physical ESP32 executed.

Pins the semantics the HMI relies on (frontend/src/state/speedContract.ts mirrors these):

  speed_mps              CANONICAL actual speed = rpm x 2*pi*wheel_radius_m / 60,
                         source DERIVED (origin HARDWARE) or SIMULATION. Absent without rpm.
  speed_mps_reported     the producer's SPEED field, kept apart (TRUCK_01).
  speed_mps_pwm_derived  TRUCK_02's SPEED field, PWM-derived, never speed_mps_reported.
  v_command_mps          a request; never written into speed_mps.
  Sourced.timestamp      measurement time when the packet carried source_timestamp,
                         otherwise received_at (and the packet's `timestamp` is NOT one).
  received_at            the ingest clock, its own Twin field.
  freshness              CURRENT -> STALE at stale_after_s; UNAVAILABLE when never reported.
"""
import math
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "SYNQRA_SIH2026-27-HMI", "backend"))

from telemetry_ingest import TelemetryIngestor, Transport  # noqa: E402
from twin.twin_state_store import Source, Sourced, TwinMode, TwinStateStore, UNAVAILABLE  # noqa: E402
from twin_projection import build_vehicle_projection  # noqa: E402

R01 = 0.050  # config/physical_vehicle_parameters.json TRUCK_01 wheel_radius_m (measured)


def derived(rpm, r=R01):
    return round(rpm * 2.0 * math.pi * r / 60.0, 4)


class FixedClock:
    def __init__(self, t=1_000_000.0):
        self.t = t

    def __call__(self):
        return self.t


@pytest.fixture
def clock():
    return FixedClock()


@pytest.fixture
def store(clock):
    return TwinStateStore(mode=TwinMode.HYBRID, clock=clock, stale_after_s=3.0)


@pytest.fixture
def ingestor(store, clock):
    return TelemetryIngestor(store, clock=clock)


def rec(vehicle_id="TRUCK_01", sequence=1, **over):
    body = dict(vehicle_id=vehicle_id, sequence_number=sequence, rpm=1450.0, speed=7.8)
    body.update(over)
    return body


def ingest(ingestor, simulated=False, **over):
    r = ingestor.ingest_parsed_record(
        rec(**over), transport=Transport.DIRECT_WIFI, is_simulated=simulated
    )
    assert r.accepted, r.reason
    return r


class TestSpeedFields:
    def test_reported_and_derived_are_separate_fields_with_separate_values(self, ingestor, store):
        ingest(ingestor)
        canonical = store.get_vehicle_field("TRUCK_01", "speed_mps")
        reported = store.get_vehicle_field("TRUCK_01", "speed_mps_reported")
        assert canonical.value == derived(1450.0)  # 7.5922 m/s
        assert reported.value == 7.8
        assert canonical.value != reported.value

    def test_canonical_is_encoder_derived_from_hardware(self, ingestor, store):
        ingest(ingestor)
        f = store.get_vehicle_field("TRUCK_01", "speed_mps")
        assert f.source is Source.DERIVED
        assert f.effective_origin is Source.HARDWARE
        assert store.get_vehicle_field("TRUCK_01", "rpm").source is Source.HARDWARE

    def test_reported_change_does_not_move_canonical(self, ingestor, store):
        ingest(ingestor, sequence=1, speed=7.8)
        before = store.get_vehicle_field("TRUCK_01", "speed_mps").value
        ingest(ingestor, sequence=2, speed=9.9)  # same rpm
        assert store.get_vehicle_field("TRUCK_01", "speed_mps").value == before
        assert store.get_vehicle_field("TRUCK_01", "speed_mps_reported").value == 9.9

    def test_rpm_change_moves_canonical_not_reported(self, ingestor, store):
        ingest(ingestor, sequence=1)
        ingest(ingestor, sequence=2, rpm=1700.0)  # same reported speed
        assert store.get_vehicle_field("TRUCK_01", "speed_mps").value == derived(1700.0)
        assert store.get_vehicle_field("TRUCK_01", "speed_mps_reported").value == 7.8

    def test_no_rpm_means_no_canonical_speed_not_zero(self, ingestor, store):
        r = ingestor.ingest_parsed_record(
            {"vehicle_id": "TRUCK_01", "sequence_number": 1, "speed": 7.8},
            transport=Transport.DIRECT_WIFI, is_simulated=False,
        )
        assert r.accepted
        assert store.get_vehicle_field("TRUCK_01", "speed_mps") is UNAVAILABLE
        assert store.get_vehicle_field("TRUCK_01", "speed_mps_reported").value == 7.8

    def test_truck02_speed_field_is_pwm_derived_never_reported(self, ingestor, store):
        ingest(ingestor, vehicle_id="TRUCK_02", rpm=300.0, speed=2.5)
        assert store.get_vehicle_field("TRUCK_02", "speed_mps_pwm_derived").value == 2.5
        assert store.get_vehicle_field("TRUCK_02", "speed_mps_reported") is UNAVAILABLE
        # Its canonical speed still comes from its measured RPM and its own radius.
        assert store.get_vehicle_field("TRUCK_02", "speed_mps").value == derived(300.0, 0.0425)

    def test_simulated_ingress_marks_every_speed_simulation(self, ingestor, store):
        ingest(ingestor, simulated=True)
        for name in ("speed_mps", "speed_mps_reported", "rpm"):
            f = store.get_vehicle_field("TRUCK_01", name)
            assert f.source is Source.SIMULATION, name
            assert f.effective_origin is Source.SIMULATION, name

    def test_command_speed_never_becomes_actual_speed(self, ingestor, store, clock):
        ingest(ingestor)
        store.update_vehicle_fields(
            "TRUCK_01",
            {"v_command_mps": Sourced(value=12.0, timestamp=clock(), source=Source.DERIVED)},
        )
        assert store.get_vehicle_field("TRUCK_01", "v_command_mps").value == 12.0
        assert store.get_vehicle_field("TRUCK_01", "speed_mps").value == derived(1450.0)

    @pytest.mark.parametrize("bad", [math.nan, math.inf, -1.0, "7.8", True])
    def test_invalid_speed_creates_no_value(self, ingestor, store, bad):
        r = ingestor.ingest_parsed_record(
            rec(speed=bad), transport=Transport.DIRECT_WIFI, is_simulated=False
        )
        assert not r.accepted
        assert store.get_vehicle_field("TRUCK_01", "speed_mps") is UNAVAILABLE
        assert store.get_vehicle_field("TRUCK_01", "speed_mps_reported") is UNAVAILABLE


class TestTimestampAndFreshness:
    def test_packet_timestamp_is_arrival_metadata_not_measurement_time(self, ingestor, store, clock):
        ingest(ingestor, timestamp=clock.t - 100.0)  # a parser's arrival stamp
        f = store.get_vehicle_field("TRUCK_01", "speed_mps")
        assert f.timestamp == clock.t  # received_at fallback, NOT the bare `timestamp`

    def test_source_timestamp_is_the_measurement_time(self, ingestor, store, clock):
        ingest(ingestor, source_timestamp=clock.t - 0.25)
        assert store.get_vehicle_field("TRUCK_01", "speed_mps").timestamp == clock.t - 0.25
        assert store.get_vehicle_field("TRUCK_01", "received_at").value == clock.t

    def test_freshness_current_then_stale_then_value_kept(self, ingestor, store, clock):
        ingest(ingestor)
        cur = build_vehicle_projection(store, "TRUCK_01")["dynamic"]["speed_mps"]
        assert cur["freshness"] == "CURRENT" and cur["age_s"] == 0.0
        clock.t += 3.5  # past stale_after_s=3.0
        stale = build_vehicle_projection(store, "TRUCK_01")["dynamic"]["speed_mps"]
        assert stale["freshness"] == "STALE"
        assert stale["value"] == derived(1450.0)  # kept and flagged, not zeroed
        assert stale["available"] is True

    def test_never_reported_field_is_absent_from_projection(self, ingestor, store):
        ingest(ingestor, vehicle_id="TRUCK_02", rpm=300.0, speed=2.5)
        dynamic = build_vehicle_projection(store, "TRUCK_02")["dynamic"]
        assert "speed_mps_reported" not in dynamic
        assert "v_safe_mps" not in dynamic  # no safety slice on this path: UNAVAILABLE

    def test_future_source_timestamp_rejected(self, ingestor, store, clock):
        r = ingestor.ingest_parsed_record(
            rec(source_timestamp=clock.t + 5.0), transport=Transport.DIRECT_WIFI, is_simulated=False
        )
        assert not r.accepted
        assert store.get_vehicle_field("TRUCK_01", "speed_mps") is UNAVAILABLE


class TestSimulatedApiIngress:
    """POST /api/telemetry: the SIMULATED ingress the three HMIs were exercised with."""

    @pytest.fixture(autouse=True)
    def reset(self):
        from app.main import deduplication_store, last_sequence_by_vehicle, vehicle_telemetry_store
        vehicle_telemetry_store.clear()
        deduplication_store.clear()
        last_sequence_by_vehicle.clear()
        yield

    def test_twin_endpoint_exposes_both_speeds_marked_simulation(self):
        from app.main import app
        from fastapi.testclient import TestClient
        c = TestClient(app)
        # The process-wide Twin keeps per-vehicle sequence ordering across test modules,
        # so use a sequence base no earlier test can have reached.
        import time
        seq = int(time.time()) * 10
        assert c.post("/api/telemetry", json={"vehicle_id": "TRUCK_01", "sequence": seq + 1, "rpm": 1450.0, "speed": 7.8}).status_code == 200
        d = c.get("/api/twin/vehicles/TRUCK_01").json()["dynamic"]
        assert d["speed_mps"]["value"] == derived(1450.0)
        assert d["speed_mps_reported"]["value"] == 7.8
        assert d["speed_mps"]["source"] == "SIMULATION"
        assert d["speed_mps"]["origin"] == "SIMULATION"
        # Case B: reported changes, canonical does not.
        assert c.post("/api/telemetry", json={"vehicle_id": "TRUCK_01", "sequence": seq + 2, "rpm": 1450.0, "speed": 9.9}).status_code == 200
        d = c.get("/api/twin/vehicles/TRUCK_01").json()["dynamic"]
        assert d["speed_mps"]["value"] == derived(1450.0)
        assert d["speed_mps_reported"]["value"] == 9.9
        # Case C: rpm changes, canonical follows.
        assert c.post("/api/telemetry", json={"vehicle_id": "TRUCK_01", "sequence": seq + 3, "rpm": 1700.0, "speed": 9.9}).status_code == 200
        assert c.get("/api/twin/vehicles/TRUCK_01").json()["dynamic"]["speed_mps"]["value"] == derived(1700.0)
