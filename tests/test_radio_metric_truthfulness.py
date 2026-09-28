"""
Radio metrics: measured, or absent. Never invented.

Two radios exist on this prototype and they measure different things. Wi-Fi RSSI comes
from `WiFi.RSSI()` on the vehicle's own ESP32. LoRa RSSI and SNR come from the receiving
LoRa modem's `packetRssi()` / `packetSnr()`. A number from one is not evidence about the
other, and a number nobody measured is not evidence about anything.

TRUCK_02's firmware sends no `rssi` and no `snr` field at all. Until now the backend's
Pydantic model defaulted those to -75 dBm and 9.5 dB, and the ingestor stamped the result
`observed` - so every TRUCK_02 frame carried a fabricated signal strength that looked
exactly like a measurement. These tests hold that shut.

SOFTWARE ONLY. No hardware is exercised here; payloads are constructed in-process.
"""

import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BACKEND = os.path.join(ROOT, "SYNQRA_SIH2026-27-HMI", "backend")
for _path in (ROOT, BACKEND):
    if _path not in sys.path:
        sys.path.insert(0, _path)

from fastapi.testclient import TestClient  # noqa: E402

import app.main as main  # noqa: E402

HARDWARE = "/api/hardware/telemetry"


@pytest.fixture(autouse=True)
def reset_stores():
    main.vehicle_telemetry_store.clear()
    if main.twin_store is not None:
        main.twin_store._vehicles.clear()
        main.twin_store._roads.clear()
    yield
    main.vehicle_telemetry_store.clear()
    if main.twin_store is not None:
        main.twin_store._vehicles.clear()
        main.twin_store._roads.clear()


def _frame(vehicle_id, sequence, **extra):
    """A TRUCK_02-shaped frame: the fields its firmware actually sends, and no others."""
    frame = {
        "vehicle_id": vehicle_id,
        "sequence": sequence,
        "rpm": 120.0,
        "speed": 0.35,
        "accel_x": 100,
        "accel_y": 200,
        "accel_z": 16000,
        "gyro_x": 10,
        "gyro_y": 20,
        "gyro_z": 30,
        "source": "DIRECT_WIFI",
    }
    frame.update(extra)
    return frame


def _twin_fields(client, vehicle_id):
    response = client.get("/api/twin/vehicles/%s" % vehicle_id)
    assert response.status_code == 200, response.text
    return response.json().get("dynamic", {})


# ---------------------------------------------------------------------------
# absence stays absence
# ---------------------------------------------------------------------------


def test_an_unsent_rssi_does_not_become_minus_75():
    """THE REGRESSION. A frame with no `rssi` must not acquire one."""
    with TestClient(main.app) as client:
        assert client.post(HARDWARE, json=_frame("TRUCK_02", 9101)).status_code == 200
        fields = _twin_fields(client, "TRUCK_02")

    for name in ("wifi_rssi_dbm", "rssi_dbm"):
        field = fields.get(name)
        if field is None:
            continue  # absent entirely is the strongest form of unavailable
        assert field.get("available") is not True, "%s was fabricated: %r" % (name, field)
        assert field.get("value") != -75


def test_an_unsent_snr_does_not_become_9_5():
    with TestClient(main.app) as client:
        assert client.post(HARDWARE, json=_frame("TRUCK_02", 9102)).status_code == 200
        fields = _twin_fields(client, "TRUCK_02")

    for name in ("lora_snr_db", "snr_db"):
        field = fields.get(name)
        if field is None:
            continue
        assert field.get("available") is not True, "%s was fabricated: %r" % (name, field)
        assert field.get("value") != 9.5


def test_the_payload_model_carries_no_radio_default():
    """Asserted on the model itself, so a default cannot be reintroduced quietly."""
    fields = main.HardwareTelemetryPayload.model_fields
    assert fields["rssi"].default is None
    assert fields["snr"].default is None


def test_a_frame_that_omits_radio_metrics_is_still_accepted():
    """Refusing the frame would be the wrong fix - the telemetry is valid, the radio is not."""
    with TestClient(main.app) as client:
        response = client.post(HARDWARE, json=_frame("TRUCK_02", 9103))
        assert response.status_code == 200
        fields = _twin_fields(client, "TRUCK_02")
    assert fields.get("rpm", {}).get("available") is True, "the real measurement survived"


# ---------------------------------------------------------------------------
# a measurement that WAS taken still arrives
# ---------------------------------------------------------------------------


def test_a_measured_wifi_rssi_is_projected_to_the_hmi():
    with TestClient(main.app) as client:
        assert client.post(HARDWARE, json=_frame("TRUCK_01", 9104, rssi=-58)).status_code == 200
        fields = _twin_fields(client, "TRUCK_01")

    wifi = fields.get("wifi_rssi_dbm")
    assert wifi is not None, "the per-radio field must reach the HMI, not only the legacy one"
    assert wifi.get("available") is True
    assert wifi.get("value") == -58


def test_a_wifi_frame_never_produces_lora_metrics():
    """
    THE SEPARATION. DIRECT_WIFI crossed no LoRa radio, so both LoRa fields stay absent
    even though the frame carried a `snr` value.
    """
    with TestClient(main.app) as client:
        assert (
            client.post(HARDWARE, json=_frame("TRUCK_01", 9105, rssi=-58, snr=9.5)).status_code
            == 200
        )
        fields = _twin_fields(client, "TRUCK_01")

    for name in ("lora_rssi_dbm", "lora_snr_db"):
        field = fields.get(name)
        if field is None:
            continue
        assert field.get("available") is not True, "%s leaked from a Wi-Fi frame" % name

    # And the Wi-Fi number did not become the LoRa number.
    lora_rssi = fields.get("lora_rssi_dbm") or {}
    assert lora_rssi.get("value") != -58


def test_the_projection_exposes_all_three_radio_fields():
    """The whitelist is the gate. A field the projection drops is invisible to every HMI."""
    from twin_projection import VEHICLE_PROJECTION_FIELDS

    for name in ("wifi_rssi_dbm", "lora_rssi_dbm", "lora_snr_db"):
        assert name in VEHICLE_PROJECTION_FIELDS


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-q"]))
