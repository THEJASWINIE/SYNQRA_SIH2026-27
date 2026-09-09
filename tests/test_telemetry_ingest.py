"""
P3 — canonical telemetry ingestion tests.

All data here is SIMULATED / REPLAYED. No physical ESP32 was connected or exercised.
Packets are either the frozen V2V wire format built by hand, or deterministic emulator
records. Nothing in this file constitutes a physical hardware test.
"""

import math
import threading

import pytest

from telemetry_ingest import (
    PWM_DERIVED_SPEED_VEHICLES,
    REJECT_BAD_SEQUENCE,
    REJECT_BAD_TIMESTAMP,
    REJECT_DUPLICATE,
    REJECT_MISSING_VEHICLE_ID,
    REJECT_NON_FINITE,
    REJECT_OUT_OF_ORDER,
    REJECT_UNKNOWN_VEHICLE,
    NormalizedTelemetry,
    TelemetryIngestor,
    Transport,
    map_quality,
)
from twin.twin_state_store import Quality, Source, TwinMode, TwinStateStore, UNAVAILABLE


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


def hw(vehicle_id="TRUCK_02", sequence=1, **over):
    """A deterministic HARDWARE-shaped record (replayed, not captured from a live device)."""
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


def _backend_on_path():
    import os
    import sys

    backend = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "SYNQRA_SIH2026-27-HMI", "backend",
    )
    if backend not in sys.path:
        sys.path.insert(0, backend)
    return backend


# ---------------------------------------------------------------------
# 1/2. valid hardware telemetry reaches the Twin, tagged HARDWARE
# ---------------------------------------------------------------------

def test_hardware_telemetry_reaches_twin_as_hardware(ingestor, store):
    result = ingestor.ingest_parsed_record(hw(), transport=Transport.DIRECT_WIFI, is_simulated=False)

    assert result.accepted
    assert result.reason == "ACCEPTED"

    rpm = store.get_vehicle_field("TRUCK_02", "rpm")
    assert rpm.value == 240.0
    assert rpm.source is Source.HARDWARE
    assert rpm.quality is Quality.GOOD

    for name in ("ax_mps2", "ay_mps2", "az_mps2", "gx_rad_s", "gy_rad_s", "gz_rad_s"):
        assert store.get_vehicle_field("TRUCK_02", name).source is Source.HARDWARE


def test_frozen_v2v_packet_ingests_unchanged(ingestor, store):
    """The frozen wire format STATE,TRUCK_0x,seq,rpm,speed,ax..gz is parsed by the EXISTING parser."""
    packet = "STATE,TRUCK_01,28,240.00,0.00,-496,132,16696,703,342,191"
    result = ingestor.ingest_v2v_packet(packet, is_simulated=False)

    assert result.accepted, result.reason
    assert result.vehicle_id == "TRUCK_01"
    assert result.sequence == 28
    assert store.get_vehicle_field("TRUCK_01", "rpm").value == 240.0
    assert store.get_vehicle_field("TRUCK_01", "rpm").source is Source.HARDWARE
    # IMU LSB were converted to SI by the existing parser, not re-implemented here.
    assert store.get_vehicle_field("TRUCK_01", "az_mps2").value == pytest.approx(9.998, abs=1e-2)


# ---------------------------------------------------------------------
# 3/4. simulation telemetry reaches the Twin, tagged SIMULATION
# ---------------------------------------------------------------------

def test_simulation_telemetry_is_tagged_simulation(ingestor, store):
    result = ingestor.ingest_parsed_record(hw("TRUCK_01"), transport=Transport.EMULATOR, is_simulated=True)

    assert result.accepted
    assert store.get_vehicle_field("TRUCK_01", "rpm").source is Source.SIMULATION
    assert store.get_vehicle_field("TRUCK_01", "ax_mps2").source is Source.SIMULATION


def test_emulator_packet_is_never_labelled_hardware(ingestor, store):
    ingestor.ingest_v2v_packet(
        "STATE,TRUCK_01,5,180.00,1.20,-100,50,16400,10,5,2", is_simulated=True
    )
    for name in ("rpm", "ax_mps2", "sequence"):
        got = store.get_vehicle_field("TRUCK_01", name)
        assert got.source is not Source.HARDWARE, f"{name} was mislabelled HARDWARE"


# ---------------------------------------------------------------------
# 5. mixed SIMULATION / HARDWARE coexistence (HYBRID)
# ---------------------------------------------------------------------

def test_simulation_and_hardware_vehicles_coexist(ingestor, store):
    ingestor.ingest_parsed_record(hw("TRUCK_01", 1), transport=Transport.EMULATOR, is_simulated=True)
    ingestor.ingest_parsed_record(hw("TRUCK_02", 1), transport=Transport.DIRECT_WIFI, is_simulated=False)

    assert store.mode is TwinMode.HYBRID
    assert store.get_vehicle_field("TRUCK_01", "rpm").source is Source.SIMULATION
    assert store.get_vehicle_field("TRUCK_02", "rpm").source is Source.HARDWARE

    # Neither vehicle's provenance leaked into the other.
    snap = store.get_state_snapshot()
    assert snap["vehicles"]["TRUCK_01"]["dynamic"]["rpm"]["source"] == "SIMULATION"
    assert snap["vehicles"]["TRUCK_02"]["dynamic"]["rpm"]["source"] == "HARDWARE"


# ---------------------------------------------------------------------
# 6/7. deduplication and out-of-order rejection
# ---------------------------------------------------------------------

def test_duplicate_sequence_is_rejected(ingestor, store):
    assert ingestor.ingest_parsed_record(hw(sequence=10, rpm=240.0), Transport.V2V).accepted

    dup = ingestor.ingest_parsed_record(hw(sequence=10, rpm=999.0), Transport.V2V)
    assert not dup.accepted
    assert dup.reason == REJECT_DUPLICATE
    # The duplicate did NOT mutate the Twin.
    assert store.get_vehicle_field("TRUCK_02", "rpm").value == 240.0


def test_out_of_order_sequence_is_rejected(ingestor, store):
    assert ingestor.ingest_parsed_record(hw(sequence=20, rpm=240.0), Transport.V2V).accepted

    old = ingestor.ingest_parsed_record(hw(sequence=15, rpm=999.0), Transport.V2V)
    assert not old.accepted
    assert old.reason == REJECT_OUT_OF_ORDER
    assert store.get_vehicle_field("TRUCK_02", "rpm").value == 240.0


def test_dedup_happens_before_any_twin_mutation(ingestor, store):
    ingestor.ingest_parsed_record(hw(sequence=5), Transport.V2V)
    before = store.get_state_snapshot(now=1_000_000.0)

    ingestor.ingest_parsed_record(hw(sequence=5, rpm=1.0), Transport.V2V)
    ingestor.ingest_parsed_record(hw(sequence=1, rpm=2.0), Transport.V2V)

    assert store.get_state_snapshot(now=1_000_000.0) == before


# ---------------------------------------------------------------------
# 8/9/10/11. malformed, NaN, Infinity, bad timestamp
# ---------------------------------------------------------------------

@pytest.mark.parametrize(
    "packet",
    [
        "",
        "GARBAGE",
        "STATE,TRUCK_01",
        "STATE,TRUCK_01,1,2,3",
        "PING,TRUCK_01,1,2,3,4,5,6,7,8,9",
        "STATE,TRUCK_99,1,240,0,1,2,3,4,5,6",
        "STATE,TRUCK_01,x,240,0,1,2,3,4,5,6",
    ],
)
def test_malformed_packets_are_rejected_without_raising(ingestor, store, packet):
    result = ingestor.ingest_v2v_packet(packet)
    assert not result.accepted
    assert store.get_all_vehicles() == {}      # nothing was created by a bad packet


@pytest.mark.parametrize("bad", [float("nan"), float("inf"), float("-inf")])
def test_non_finite_values_are_rejected(ingestor, store, bad):
    for field_name in ("rpm", "speed"):
        res = ingestor.ingest_parsed_record(hw(sequence=1, **{field_name: bad}), Transport.V2V)
        assert not res.accepted
        assert res.reason == REJECT_NON_FINITE

    res = ingestor.ingest_parsed_record(
        hw(sequence=2, acceleration={"x": bad, "y": 0.0, "z": 9.81}), Transport.V2V
    )
    assert not res.accepted
    assert res.reason == REJECT_NON_FINITE
    assert store.get_all_vehicles() == {}


@pytest.mark.parametrize(
    "ts", [float("nan"), float("inf"), -1.0, 1_000_000.0 + 60.0]  # NaN, Inf, negative, future
)
def test_invalid_timestamps_are_rejected(ingestor, store, ts):
    # `source_timestamp` is the key that explicitly claims a measurement time.
    res = ingestor.ingest_parsed_record(hw(source_timestamp=ts), Transport.V2V)
    assert not res.accepted
    assert res.reason == REJECT_BAD_TIMESTAMP
    assert store.get_all_vehicles() == {}


def test_invalid_sequence_is_rejected(ingestor):
    assert ingestor.ingest_parsed_record(hw(sequence="abc"), Transport.V2V).reason == REJECT_BAD_SEQUENCE
    assert ingestor.ingest_parsed_record(hw(sequence=None), Transport.V2V).reason == REJECT_BAD_SEQUENCE
    assert ingestor.ingest_parsed_record(hw(sequence=-5), Transport.V2V).reason == REJECT_BAD_SEQUENCE


# ---------------------------------------------------------------------
# 12. unknown / missing vehicle
# ---------------------------------------------------------------------

def test_unknown_vehicle_is_rejected(ingestor, store):
    res = ingestor.ingest_parsed_record(hw("TRUCK_47"), Transport.V2V)
    assert not res.accepted
    assert res.reason == REJECT_UNKNOWN_VEHICLE
    assert store.get_vehicle("TRUCK_47") is None


def test_missing_vehicle_id_is_rejected(ingestor):
    for bad in (None, "", "   "):
        rec = hw()
        rec["vehicle_id"] = bad
        assert ingestor.ingest_parsed_record(rec, Transport.V2V).reason == REJECT_MISSING_VEHICLE_ID


# ---------------------------------------------------------------------
# 13. unavailable fields stay unavailable
# ---------------------------------------------------------------------

def test_unreported_fields_remain_unavailable(ingestor, store):
    ingestor.ingest_parsed_record(hw(), Transport.DIRECT_WIFI)

    # No sensor on this prototype produces these. They must NOT be fabricated.
    for name in ("position_s", "road_id", "node_id", "heading_rad", "visibility_m", "friction_mu"):
        assert store.get_vehicle_field("TRUCK_02", name) is UNAVAILABLE, f"{name} was fabricated"


def test_absent_optional_signal_is_not_zero_filled(ingestor, store):
    record = hw("TRUCK_01")
    record.pop("gyroscope")
    ingestor.ingest_parsed_record(record, Transport.V2V)

    assert store.get_vehicle_field("TRUCK_01", "gx_rad_s") is UNAVAILABLE
    assert store.get_vehicle_field("TRUCK_01", "rpm").is_available   # what WAS reported landed


# ---------------------------------------------------------------------
# 14. received_at is distinct from the measurement timestamp
# ---------------------------------------------------------------------

def test_received_at_is_distinct_from_measurement_timestamp(ingestor, store, clock):
    measured_at = clock.t - 2.0
    ingestor.ingest_parsed_record(hw(source_timestamp=measured_at), Transport.V2V)

    rpm = store.get_vehicle_field("TRUCK_02", "rpm")
    received = store.get_vehicle_field("TRUCK_02", "received_at")

    assert rpm.timestamp == measured_at          # provenance carries the measurement time
    assert received.value == clock.t             # arrival time kept separately
    assert received.value != rpm.timestamp


def test_missing_source_timestamp_is_not_disguised_as_a_measurement(clock, store):
    ingestor = TelemetryIngestor(store, clock=clock)

    normalized = NormalizedTelemetry(
        vehicle_id="TRUCK_01", sequence=1, received_at=clock.t, timestamp=None,
        transport=Transport.V2V, rpm=100.0,
    )
    assert normalized.timestamp is None                    # explicitly absent
    assert normalized.measurement_timestamp == clock.t     # falls back, but the caller can tell
    assert ingestor.ingest_normalized(normalized).accepted


# ---------------------------------------------------------------------
# 15. hardware values are not overwritten by synthetic values
# ---------------------------------------------------------------------

def test_simulation_does_not_silently_overwrite_hardware(store, clock):
    """
    PRECEDENCE RULE (explicit, deliberately simple for P3):
    the ingestor records each observation with its own provenance; sequence ordering is
    what protects the Twin - a stale or duplicate synthetic packet cannot displace a newer
    hardware reading. No arbitration beyond ordering is introduced in P3.
    """
    ingestor = TelemetryIngestor(store, clock=clock)
    ingestor.ingest_parsed_record(hw("TRUCK_02", 10, rpm=240.0), Transport.DIRECT_WIFI, is_simulated=False)
    assert store.get_vehicle_field("TRUCK_02", "rpm").source is Source.HARDWARE

    # An older synthetic packet is rejected outright.
    stale_sim = ingestor.ingest_parsed_record(
        hw("TRUCK_02", 3, rpm=1.0), Transport.EMULATOR, is_simulated=True
    )
    assert not stale_sim.accepted
    got = store.get_vehicle_field("TRUCK_02", "rpm")
    assert got.value == 240.0
    assert got.source is Source.HARDWARE


def test_hardware_state_survives_later_simulation_vehicle_attachment(store, clock):
    """A physical truck may exist in the Twin before any simulation Vehicle object exists."""
    ingestor = TelemetryIngestor(store, clock=clock)
    ingestor.ingest_parsed_record(hw("TRUCK_02", 1, rpm=240.0), Transport.DIRECT_WIFI)

    class DomainVehicle:
        id = "TRUCK_02"
        tare_mass = 74000.0
        length = 10.52

    store.register_vehicle(DomainVehicle())

    rpm = store.get_vehicle_field("TRUCK_02", "rpm")
    assert rpm.value == 240.0                      # hardware state was NOT discarded
    assert rpm.source is Source.HARDWARE
    assert store.get_vehicle("TRUCK_02").static["tare_mass_kg"] == 74000.0


# ---------------------------------------------------------------------
# 16. source/quality survive snapshots
# ---------------------------------------------------------------------

def test_provenance_survives_snapshot(ingestor, store, clock):
    ingestor.ingest_parsed_record(hw(), Transport.DIRECT_WIFI, is_simulated=False)
    snap = store.get_state_snapshot(now=clock.t)

    rpm = snap["vehicles"]["TRUCK_02"]["dynamic"]["rpm"]
    assert rpm["source"] == "HARDWARE"
    assert rpm["quality"] == "GOOD"
    assert rpm["available"] is True
    assert rpm["timestamp"] is not None


def test_quality_mapping_uses_existing_vocabulary():
    assert map_quality("LIVE") is Quality.GOOD
    assert map_quality("DELAYED") is Quality.DEGRADED
    assert map_quality("RECOVERING") is Quality.DEGRADED
    assert map_quality("STALE") is Quality.STALE
    assert map_quality("OFFLINE") is Quality.STALE
    assert map_quality("INVALID") is Quality.INVALID
    assert map_quality(None) is Quality.UNKNOWN
    assert map_quality("something-nobody-defined") is Quality.UNKNOWN


def test_degraded_quality_is_carried_into_the_twin(ingestor, store):
    ingestor.ingest_parsed_record(hw(data_quality="DELAYED"), Transport.V2V)
    assert store.get_vehicle_field("TRUCK_02", "rpm").quality is Quality.DEGRADED


# ---------------------------------------------------------------------
# 17/18. hardware truth: measured RPM vs PWM-derived speed
# ---------------------------------------------------------------------

def test_measured_rpm_is_preserved_as_hardware(ingestor, store):
    ingestor.ingest_parsed_record(hw("TRUCK_01", rpm=312.5), Transport.V2V, is_simulated=False)
    rpm = store.get_vehicle_field("TRUCK_01", "rpm")
    assert rpm.value == 312.5
    assert rpm.source is Source.HARDWARE


def test_pwm_derived_speed_is_not_labelled_measured(ingestor, store):
    """
    TRUCK_02's V2V SPEED field is PWM-derived by the existing firmware. It must never be
    presented as an encoder measurement.
    """
    assert "TRUCK_02" in PWM_DERIVED_SPEED_VEHICLES

    ingestor.ingest_parsed_record(hw("TRUCK_02", speed=2.5), Transport.V2V, is_simulated=False)

    pwm = store.get_vehicle_field("TRUCK_02", "speed_mps_pwm_derived")
    assert pwm.value == 2.5
    assert pwm.source is Source.DERIVED            # NOT HARDWARE

    # And it did not leak into the plain reported-speed field.
    assert store.get_vehicle_field("TRUCK_02", "speed_mps_reported") is UNAVAILABLE


def test_encoder_derived_speed_is_marked_derived_not_measured(ingestor, store):
    """speed_mps computed from MEASURED rpm is DERIVED - honest about the extra step."""
    ingestor.ingest_parsed_record(hw("TRUCK_01", rpm=240.0), Transport.V2V, is_simulated=False)

    speed = store.get_vehicle_field("TRUCK_01", "speed_mps")
    assert speed.is_available
    assert speed.source is Source.DERIVED
    # v = rpm * 2*pi*r / 60, with the MEASURED wheel radius from
    # config/physical_vehicle_parameters.json (TRUCK_01: 0.050 m)
    assert speed.value == pytest.approx(240.0 * 2 * math.pi * 0.050 / 60.0, abs=1e-3)


def test_speed_unavailable_when_no_calibrated_radius(store, clock):
    """No calibrated wheel radius => encoder speed is unavailable, never guessed."""
    class NoCalibration:
        def rpm_to_speed_mps(self, vehicle_id, rpm):
            return None

    ingestor = TelemetryIngestor(store, unit_converter=NoCalibration(), clock=clock)
    ingestor.ingest_parsed_record(hw("TRUCK_01", rpm=240.0), Transport.V2V)

    assert store.get_vehicle_field("TRUCK_01", "speed_mps") is UNAVAILABLE
    assert store.get_vehicle_field("TRUCK_01", "rpm").is_available


# ---------------------------------------------------------------------
# 19. gateway simulated fallback is labelled SIMULATION
# ---------------------------------------------------------------------

def test_gateway_simulated_fallback_is_labelled_simulation(ingestor, store):
    _backend_on_path()
    from app.gateway_serial_reader import GatewayTelemetryParser

    line = ("V=TRUCK_01,SEQ=7,RPM=240.0,SPD=2.50,AX=0.12,AY=-0.05,AZ=9.81,"
            "GX=0.02,GY=0.01,GZ=-0.03,RSSI=-62,SNR=9.5")

    simulated = GatewayTelemetryParser.parse_packet(line, provenance_source="SIMULATION")
    assert simulated["provenance_source"] == "SIMULATION"
    assert ingestor.ingest_gateway_record(simulated).accepted
    assert store.get_vehicle_field("TRUCK_01", "rpm").source is Source.SIMULATION


def test_gateway_real_serial_record_is_hardware(store, clock):
    _backend_on_path()
    from app.gateway_serial_reader import GatewayTelemetryParser

    ingestor = TelemetryIngestor(store, clock=clock)
    line = "V=TRUCK_01,SEQ=8,RPM=240.0,SPD=2.50,AX=0.12,AY=-0.05,AZ=9.81,GX=0.02,GY=0.01,GZ=-0.03"
    record = GatewayTelemetryParser.parse_packet(line, provenance_source="HARDWARE")

    assert record["provenance_source"] == "HARDWARE"
    assert ingestor.ingest_gateway_record(record).accepted
    assert store.get_vehicle_field("TRUCK_01", "rpm").source is Source.HARDWARE


def test_gateway_record_without_provenance_defaults_to_simulation(ingestor, store):
    """Refuse to assume hardware when provenance was not declared."""
    record = hw("TRUCK_01")
    record.pop("provenance_source", None)
    assert ingestor.ingest_gateway_record(record).accepted
    assert store.get_vehicle_field("TRUCK_01", "rpm").source is Source.SIMULATION


def test_gateway_parser_default_is_not_hardware():
    _backend_on_path()
    from app.gateway_serial_reader import GatewayTelemetryParser

    rec = GatewayTelemetryParser.parse_packet("V=TRUCK_01,SEQ=1,RPM=10.0,SPD=0.1")
    assert rec["provenance_source"] == "SIMULATION"


# ---------------------------------------------------------------------
# 20/21. robustness: bad packets never corrupt the Twin; Twin stays queryable
# ---------------------------------------------------------------------

def test_bad_packet_storm_does_not_corrupt_twin(ingestor, store):
    ingestor.ingest_parsed_record(hw("TRUCK_02", 100, rpm=240.0), Transport.DIRECT_WIFI)
    good = store.get_state_snapshot(now=1_000_000.0)

    for junk in ("", "GARBAGE", "STATE,TRUCK_99,1,1,1,1,1,1,1,1,1", None, 12345, [], {}):
        try:
            ingestor.ingest_v2v_packet(junk)          # type: ignore[arg-type]
        except Exception as exc:                       # must never escape
            pytest.fail(f"ingestion raised on {junk!r}: {exc}")
    for junk_record in ({}, {"vehicle_id": None}, {"vehicle_id": "TRUCK_02"}, None, "str"):
        try:
            ingestor.ingest_parsed_record(junk_record, Transport.V2V)  # type: ignore[arg-type]
        except Exception as exc:
            pytest.fail(f"ingestion raised on {junk_record!r}: {exc}")

    assert store.get_state_snapshot(now=1_000_000.0) == good


def test_twin_remains_queryable_after_many_updates(ingestor, store):
    for seq in range(1, 51):
        assert ingestor.ingest_parsed_record(
            hw("TRUCK_02", seq, rpm=200.0 + seq), Transport.DIRECT_WIFI
        ).accepted

    assert store.get_vehicle_field("TRUCK_02", "rpm").value == 250.0
    assert store.get_vehicle("TRUCK_02") is not None
    assert store.get_state_snapshot()["vehicles"]["TRUCK_02"]["dynamic"]["rpm"]["value"] == 250.0
    assert ingestor.stats["accepted"] == 50


def test_concurrent_ingestion_does_not_partially_apply(store, clock):
    """One packet lands whole or not at all, even with several writer threads."""
    ingestor = TelemetryIngestor(store, clock=clock)
    errors = []

    def worker(base):
        try:
            for i in range(40):
                ingestor.ingest_parsed_record(
                    hw("TRUCK_02", base + i, rpm=float(base + i)), Transport.DIRECT_WIFI
                )
        except Exception as exc:  # noqa: BLE001
            errors.append(exc)

    threads = [threading.Thread(target=worker, args=(b,)) for b in (1000, 2000, 3000)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert not errors
    snap = store.get_state_snapshot()
    dynamic = snap["vehicles"]["TRUCK_02"]["dynamic"]
    # Every accepted packet writes the same field set, so the snapshot is internally
    # consistent: rpm and sequence come from the same packet.
    assert dynamic["rpm"]["value"] == float(dynamic["sequence"]["value"])


def test_ingestor_counters_are_accurate(ingestor):
    ingestor.ingest_parsed_record(hw(sequence=1), Transport.V2V)
    ingestor.ingest_parsed_record(hw(sequence=1), Transport.V2V)     # duplicate
    ingestor.ingest_parsed_record(hw(sequence=0), Transport.V2V)     # out of order
    ingestor.ingest_parsed_record(hw("TRUCK_47", 9), Transport.V2V)  # unknown
    ingestor.ingest_v2v_packet("GARBAGE")                            # malformed

    assert ingestor.stats["accepted"] == 1
    assert ingestor.stats["duplicate"] == 1
    assert ingestor.stats["out_of_order"] == 1
    assert ingestor.stats["unknown_vehicle"] == 1
    assert ingestor.stats["invalid"] == 1


# ---------------------------------------------------------------------
# Backend wiring: the HMI backend forwards into the canonical Twin
# ---------------------------------------------------------------------

def test_backend_forwards_hardware_telemetry_to_canonical_twin():
    _backend_on_path()

    from fastapi.testclient import TestClient

    from app.main import app, twin_store

    assert twin_store is not None, "backend did not wire up the canonical Twin"

    with TestClient(app) as client:
        resp = client.post(
            "/api/hardware/telemetry",
            json={
                # P9: sequence raised out of the low band. The backend ingestor is a
                # session-wide singleton enforcing monotonic sequences, so at 90001 this
                # packet was silently REJECTED_OUT_OF_ORDER and the assertion below passed
                # on an rpm that `test_command_gateway` had left in the Twin. It now proves
                # its OWN packet landed.
                #
                # Sequence bands on the shared backend ingestor, so no suite starves
                # another:  7_100_000 test_p9_observability (restored on teardown)
                #           7_600_000 this test
                #           8_000_000 test_twin_projection
                #           9_000_000 test_ws_ingestion_boundary
                "vehicle_id": "TRUCK_02", "sequence": 7_600_001, "rpm": 240.0, "speed": 2.5,
                "ax": 0.12, "ay": -0.05, "az": 9.81, "gx": 0.02, "gy": 0.01, "gz": -0.03,
                "source": "DIRECT_WIFI",
            },
        )
    assert resp.status_code == 200
    assert resp.json()["status"] == "ACCEPTED"

    rpm = twin_store.get_vehicle_field("TRUCK_02", "rpm")
    assert rpm.value == 240.0
    assert rpm.source is Source.HARDWARE
    # The backend's own cache is NOT the Twin; position was never fabricated in the Twin.
    assert twin_store.get_vehicle_field("TRUCK_02", "position_s") is UNAVAILABLE


def test_parser_arrival_stamp_is_not_promoted_to_measurement_time(ingestor, store):
    """
    The frozen V2V format carries no time field, so the existing parsers stamp arrival
    time as `timestamp`. That must not become a measurement timestamp.
    """
    assert ingestor.ingest_v2v_packet("STATE,TRUCK_01,42,240.00,0.00,-496,132,16696,703,342,191").accepted

    rpm = store.get_vehicle_field("TRUCK_01", "rpm")
    received = store.get_vehicle_field("TRUCK_01", "received_at")
    # With no source time available, the field time falls back to our arrival time...
    assert rpm.timestamp == received.value
    # ...and an explicit source timestamp, when one exists, is used instead.
    ingestor.ingest_parsed_record(
        hw("TRUCK_01", 43, source_timestamp=received.value - 5.0), Transport.V2V
    )
    assert store.get_vehicle_field("TRUCK_01", "rpm").timestamp == received.value - 5.0


# ---------------------------------------------------------------------
# 19. GNSS position ingestion & validation (Rules 1-12)
# ---------------------------------------------------------------------

def test_software_only_synthetic_input_valid_gnss_position_ingestion(ingestor, store):
    """SOFTWARE-ONLY / SYNTHETIC INPUT: Valid GNSS position is accepted and written as position_gnss."""
    record = hw("TRUCK_01", 100, latitude=18.6812, longitude=81.1855, position_source="GNSS", position_status="VALID")
    result = ingestor.ingest_parsed_record(record, Transport.DIRECT_WIFI, is_simulated=False)
    assert result.accepted
    pos = store.get_vehicle_field("TRUCK_01", "position_gnss")
    assert pos is not None
    assert pos.value["latitude"] == 18.6812
    assert pos.value["longitude"] == 81.1855
    assert pos.value["source"] == "GNSS"
    assert pos.value["status"] == "VALID"


def test_software_only_synthetic_input_out_of_bounds_gnss_position_rejected(ingestor, store):
    """SOFTWARE-ONLY / SYNTHETIC INPUT: Rule 9: Out of bounds latitude is rejected and does not overwrite twin."""
    record = hw("TRUCK_01", 101, latitude=195.0, longitude=81.1855, position_source="GNSS", position_status="VALID")
    result = ingestor.ingest_parsed_record(record, Transport.DIRECT_WIFI, is_simulated=False)
    assert result.accepted  # packet as a whole accepted, but position field rejected
    pos = store.get_vehicle_field("TRUCK_01", "position_gnss")
    assert pos is None or pos.value is None


# ---------------------------------------------------------------------------
# NEGATIVE PROVENANCE REGRESSION - a coordinate must EARN the HARDWARE label
#
# The hole these close: the HTTP hardware ingress treated an OMITTED simulation
# flag as "this is real hardware", so any unauthenticated client that posted a
# latitude and longitude got a position stamped HARDWARE, which the HMI then
# rendered as a PHYSICAL GNSS fix. No sensor on this prototype produces a
# position at all, so every such fix was fabricated.
#
# The rule now is positive evidence, not absence of denial.
# ---------------------------------------------------------------------------


def test_position_gnss_is_in_the_hardware_guard():
    """The existing hardware truth guard must cover the geographic position too."""
    from telemetry_ingest import NEVER_FROM_HARDWARE

    assert "position_gnss" in NEVER_FROM_HARDWARE


def test_ambiguous_client_coordinates_never_become_hardware(ingestor, store):
    """
    THE CRITICAL ONE.

    A payload carrying valid coordinates but NO explicit physical-GNSS evidence must
    never be stamped HARDWARE, even when the packet arrives on the physical-device
    transport with is_simulated=False. Omission is not evidence.
    """
    record = hw(
        "TRUCK_01",
        700,
        latitude=18.6812,
        longitude=81.1855,
        position_source="GNSS",
        position_status="VALID",
    )
    result = ingestor.ingest_parsed_record(record, Transport.DIRECT_WIFI, is_simulated=False)
    assert result.accepted

    pos = store.get_vehicle_field("TRUCK_01", "position_gnss")
    assert pos is not None, "the position should still be ingested, just not as hardware"

    # The Sourced wrapper - what every consumer reads for provenance.
    assert pos.source is not Source.HARDWARE, "an unevidenced coordinate was stamped HARDWARE"
    assert pos.origin is not Source.HARDWARE, "an unevidenced coordinate got HARDWARE origin"

    # The inner payload the frontend reads to decide PHYSICAL vs SYNTHETIC.
    assert pos.value["origin"] == "SOFTWARE_ONLY"


def test_explicitly_synthetic_coordinates_stay_software_only(ingestor, store):
    """An explicitly synthetic payload is SOFTWARE_ONLY and can never be promoted."""
    record = hw(
        "TRUCK_01",
        701,
        latitude=18.6812,
        longitude=81.1855,
        position_source="GNSS",
        position_status="VALID",
    )
    result = ingestor.ingest_parsed_record(record, Transport.DIRECT_WIFI, is_simulated=True)
    assert result.accepted

    pos = store.get_vehicle_field("TRUCK_01", "position_gnss")
    assert pos is not None
    assert pos.value["origin"] == "SOFTWARE_ONLY"
    assert pos.source is not Source.HARDWARE
    assert pos.origin is not Source.HARDWARE


def test_a_vehicle_with_a_verified_receiver_can_still_report_a_physical_fix(
    ingestor, store, monkeypatch
):
    """
    The future physical path stays open.

    Fitting a real receiver is a one-line change to the documented allowlist, and this
    proves the mechanism works - so the guard above is a locked door, not a bricked wall.
    """
    import telemetry_ingest

    monkeypatch.setattr(
        telemetry_ingest, "GNSS_EQUIPPED_VEHICLES", frozenset({"TRUCK_01"}), raising=True
    )

    record = hw(
        "TRUCK_01",
        702,
        latitude=18.6812,
        longitude=81.1855,
        position_source="GNSS",
        position_status="VALID",
    )
    result = ingestor.ingest_parsed_record(record, Transport.DIRECT_WIFI, is_simulated=False)
    assert result.accepted

    pos = store.get_vehicle_field("TRUCK_01", "position_gnss")
    assert pos is not None
    assert pos.value["origin"] == "HARDWARE"
    assert pos.source is Source.HARDWARE


def test_no_vehicle_on_this_prototype_has_a_verified_receiver():
    """
    Hardware truth: the allowlist is empty because no vehicle carries a GNSS receiver.

    If this ever fails, someone claimed a receiver exists. That claim needs physical
    evidence, not a code edit.
    """
    from telemetry_ingest import GNSS_EQUIPPED_VEHICLES

    assert GNSS_EQUIPPED_VEHICLES == frozenset()
