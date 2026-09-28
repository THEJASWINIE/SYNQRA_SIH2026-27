"""
HMI-COMMS-01 — communication truth contract, backend side.

SOFTWARE ONLY. Frames are the frozen wire formats built by hand and replayed through the
real parsers (`v2v_packet_parser.V2VPacketParser`, `gateway_serial_reader
.GatewayTelemetryParser`) and the canonical ingestor. No radio, no ESP32 executed.

    WI-FI CONNECTIVITY != V2V.   NO VERIFIED PHYSICAL V2I ENDPOINT = V2I UNAVAILABLE.

Pins:
  - a DIRECT_WIFI frame yields wifi_rssi_dbm only: no LoRa metric, no receiver, no V2V
    sequence, and its firmware `snr` fallback is not stored as a measured SNR;
  - a V2V_VIA_TRUCK_02 relay yields lora_rssi_dbm / lora_snr_db measured at TRUCK_02,
    lora_receiver_id = TRUCK_02 and v2v_sequence = the LoRa frame's SEQ;
  - a serial-gateway line yields LoRa metrics with lora_receiver_id = LORA_GATEWAY;
  - both parsers return None - never -75 / 9.5 / -65 / 9.0 - when the frame carries no
    RSSI/SNR, and the ingestor leaves the fields absent;
  - the projection exposes v2v_sequence and lora_receiver_id.
"""
import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BACKEND = os.path.join(ROOT, "SYNQRA_SIH2026-27-HMI", "backend")
for _p in (ROOT, BACKEND):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from app.gateway_serial_reader import GatewayTelemetryParser  # noqa: E402
from telemetry_ingest import TelemetryIngestor, Transport  # noqa: E402
from twin.twin_state_store import Source, TwinMode, TwinStateStore, UNAVAILABLE  # noqa: E402
from twin_projection import VEHICLE_PROJECTION_FIELDS, build_vehicle_projection  # noqa: E402
from v2v_packet_parser import V2VPacketParser  # noqa: E402


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


def wifi_frame(seq=1, **over):
    """What sketch_aug26a.ino POSTs: Wi-Fi RSSI, and `snr` = remoteDataValid ? remoteSNR : 9.5."""
    f = {
        "vehicle_id": "TRUCK_01", "sequence": seq, "rpm": 1450.0, "speed": 7.8,
        "accel_x": 0, "accel_y": 0, "accel_z": 16384, "gyro_x": 0, "gyro_y": 0, "gyro_z": 0,
        "rssi": -45, "snr": 9.5, "source": "DIRECT_WIFI",
    }
    f.update(over)
    return f


def relay_frame(seq=1, **over):
    """What vehicle_B.ino POSTs after hearing TRUCK_01 on LoRa: metrics measured at TRUCK_02."""
    f = {
        "vehicle_id": "TRUCK_01", "sequence": seq, "rpm": 1450.0, "speed": 7.8,
        "accel_x": 0, "accel_y": 0, "accel_z": 16384, "gyro_x": 0, "gyro_y": 0, "gyro_z": 0,
        "rssi": -72, "snr": 8.5, "source": "V2V_VIA_TRUCK_02",
    }
    f.update(over)
    return f


def _http(ingestor, frame):
    r = ingestor.ingest_http_payload(frame, is_simulated=False)
    assert r.accepted, r.reason


class TestWifiIsNotV2V:
    def test_wifi_frame_yields_wifi_rssi_only(self, ingestor, store):
        _http(ingestor, wifi_frame())
        assert store.get_vehicle_field("TRUCK_01", "wifi_rssi_dbm").value == -45
        assert store.get_vehicle_field("TRUCK_01", "lora_rssi_dbm") is UNAVAILABLE
        assert store.get_vehicle_field("TRUCK_01", "lora_snr_db") is UNAVAILABLE
        assert store.get_vehicle_field("TRUCK_01", "lora_receiver_id") is UNAVAILABLE
        assert store.get_vehicle_field("TRUCK_01", "v2v_sequence") is UNAVAILABLE
        assert store.get_vehicle_field("TRUCK_01", "telemetry_transport").value == Transport.DIRECT_WIFI

    def test_wifi_fallback_snr_is_not_stored_as_measured(self, ingestor, store):
        _http(ingestor, wifi_frame(snr=9.5))
        assert store.get_vehicle_field("TRUCK_01", "snr_db") is UNAVAILABLE
        assert store.get_vehicle_field("TRUCK_01", "lora_snr_db") is UNAVAILABLE


class TestRelayIsV2V:
    def test_relay_yields_lora_metrics_receiver_and_sequence(self, ingestor, store):
        _http(ingestor, relay_frame(seq=41))
        assert store.get_vehicle_field("TRUCK_01", "lora_rssi_dbm").value == -72
        assert store.get_vehicle_field("TRUCK_01", "lora_snr_db").value == 8.5
        assert store.get_vehicle_field("TRUCK_01", "lora_receiver_id").value == "TRUCK_02"
        assert store.get_vehicle_field("TRUCK_01", "v2v_sequence").value == 41
        assert store.get_vehicle_field("TRUCK_01", "telemetry_transport").value == Transport.V2V
        assert store.get_vehicle_field("TRUCK_01", "wifi_rssi_dbm") is UNAVAILABLE
        assert store.get_vehicle_field("TRUCK_01", "lora_rssi_dbm").source is Source.HARDWARE

    def test_wifi_rssi_does_not_overwrite_lora_rssi(self, ingestor, store):
        _http(ingestor, relay_frame(seq=1))
        _http(ingestor, wifi_frame(seq=2, rssi=-45))
        assert store.get_vehicle_field("TRUCK_01", "lora_rssi_dbm").value == -72
        assert store.get_vehicle_field("TRUCK_01", "wifi_rssi_dbm").value == -45
        assert store.get_vehicle_field("TRUCK_01", "lora_receiver_id").value == "TRUCK_02"

    def test_simulated_relay_is_simulation(self, ingestor, store):
        r = ingestor.ingest_http_payload(relay_frame(), is_simulated=True)
        assert r.accepted
        assert store.get_vehicle_field("TRUCK_01", "lora_rssi_dbm").source is Source.SIMULATION
        assert store.get_vehicle_field("TRUCK_01", "lora_receiver_id").value == "TRUCK_02"

    def test_v2v_evidence_goes_stale_not_current_forever(self, ingestor, store, clock):
        _http(ingestor, relay_frame())
        assert build_vehicle_projection(store, "TRUCK_01")["dynamic"]["lora_rssi_dbm"]["freshness"] == "CURRENT"
        clock.t += 3.5
        assert build_vehicle_projection(store, "TRUCK_01")["dynamic"]["lora_rssi_dbm"]["freshness"] == "STALE"


class TestRealParsers:
    def test_gateway_line_with_radio_metadata(self, ingestor, store):
        line = ("V=TRUCK_01,SEQ=7,RPM=240.0,SPD=2.50,AX=0.12,AY=-0.05,AZ=9.81,"
                "GX=0.02,GY=0.01,GZ=-0.03,RSSI=-78,SNR=9.7")
        rec = GatewayTelemetryParser.parse_packet(line, provenance_source="HARDWARE")
        assert rec["communication"]["rssi"] == -78 and rec["communication"]["snr"] == 9.7
        assert ingestor.ingest_gateway_record(rec).accepted
        assert store.get_vehicle_field("TRUCK_01", "lora_rssi_dbm").value == -78
        assert store.get_vehicle_field("TRUCK_01", "lora_snr_db").value == 9.7
        assert store.get_vehicle_field("TRUCK_01", "lora_receiver_id").value == "LORA_GATEWAY"
        assert store.get_vehicle_field("TRUCK_01", "v2v_sequence").value == 7

    def test_gateway_line_without_radio_metadata_yields_none_not_defaults(self, ingestor, store):
        line = "V=TRUCK_01,SEQ=8,RPM=240.0,SPD=2.50,AX=0.12,AY=-0.05,AZ=9.81,GX=0.02,GY=0.01,GZ=-0.03"
        rec = GatewayTelemetryParser.parse_packet(line, provenance_source="HARDWARE")
        assert rec["communication"]["rssi"] is None and rec["communication"]["snr"] is None
        assert ingestor.ingest_gateway_record(rec).accepted
        assert store.get_vehicle_field("TRUCK_01", "lora_rssi_dbm") is UNAVAILABLE
        assert store.get_vehicle_field("TRUCK_01", "lora_snr_db") is UNAVAILABLE

    def test_state_frame_with_and_without_radio_metadata(self):
        parser = V2VPacketParser()
        with_meta = parser.parse_v2v_packet(
            "STATE,TRUCK_02,28,240.00,0.00,-496,132,16696,703,342,191,RSSI=-78,SNR=9.75"
        )
        assert with_meta["vehicle_id"] == "TRUCK_02"
        assert with_meta["sequence_number"] == 28
        assert with_meta["communication"]["rssi"] == -78
        assert with_meta["communication"]["snr"] == 9.75
        bare = parser.parse_v2v_packet("STATE,TRUCK_02,29,240.00,0.00,-496,132,16696,703,342,191")
        assert bare["communication"]["rssi"] is None
        assert bare["communication"]["snr"] is None
        assert bare["communication"]["rssi"] != -75 and bare["communication"]["snr"] != 9.5

    def test_state_frame_ingested_as_v2v_without_receiver_claims_no_peer(self, ingestor, store):
        r = ingestor.ingest_v2v_packet(
            "STATE,TRUCK_02,30,240.00,0.00,-496,132,16696,703,342,191,RSSI=-70,SNR=8.0"
        )
        assert r.accepted
        assert store.get_vehicle_field("TRUCK_02", "lora_rssi_dbm").value == -70
        assert store.get_vehicle_field("TRUCK_02", "v2v_sequence").value == 30
        # Nobody said who received it: the Twin names no peer rather than guessing one.
        assert store.get_vehicle_field("TRUCK_02", "lora_receiver_id") is UNAVAILABLE


def test_projection_exposes_v2v_fields():
    for name in ("v2v_sequence", "lora_receiver_id", "wifi_rssi_dbm", "lora_rssi_dbm", "lora_snr_db"):
        assert name in VEHICLE_PROJECTION_FIELDS
