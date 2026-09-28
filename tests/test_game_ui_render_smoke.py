"""
P7.1 — headless render smoke tests for unavailable Twin values.

pygame is NOT installed and is NOT required here. The presentation helpers exercised
below are pure (they import no pygame), and `get_fleet_telemetry()` / `get_telemetry()`
produce the exact dictionaries the draw path formats.

SIMULATION only. No physical hardware.
"""

import importlib.util
import os
import sys

import pytest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MAIN_ROOT = os.path.join(REPO_ROOT, "SYNQRA_SIH2026-27-main")
GAME_UI_PATH = os.path.join(MAIN_ROOT, "game_ui.py")


@pytest.fixture(scope="module")
def ui():
    """The game_ui module, imported headlessly (pygame is only needed to draw)."""
    for path in (REPO_ROOT, MAIN_ROOT):
        if path not in sys.path:
            sys.path.insert(0, path)

    spec = importlib.util.spec_from_file_location("game_ui_render_smoke", GAME_UI_PATH)
    module = importlib.util.module_from_spec(spec)

    previous = os.getcwd()
    os.chdir(MAIN_ROOT)
    try:
        spec.loader.exec_module(module)
        return module
    finally:
        os.chdir(previous)


@pytest.fixture(scope="module")
def bridge(ui):
    previous = os.getcwd()
    os.chdir(MAIN_ROOT)
    try:
        return ui.SimulationUIBridge()
    finally:
        os.chdir(previous)


# ---------------------------------------------------------------------
# The helpers are pure: no pygame needed to prove the semantics.
# ---------------------------------------------------------------------

def test_presentation_helpers_are_importable_without_pygame(ui):
    assert "pygame" not in sys.modules, "importing game_ui should not pull in pygame"
    for name in ("fmt_value", "to_kmh", "exceeds", "safety_known"):
        assert callable(getattr(ui, name))


# ---- case 10: None value --------------------------------------------

def test_none_renders_as_unavailable_marker(ui):
    assert ui.fmt_value(None) == ui.UNAVAILABLE_TEXT
    assert ui.to_kmh(None) is None


# ---- case 9: zero value ---------------------------------------------

def test_zero_renders_as_zero_not_unavailable(ui):
    rendered = ui.fmt_value(0.0)
    assert rendered != ui.UNAVAILABLE_TEXT
    assert rendered.strip() == "0.0"
    assert ui.to_kmh(0.0) == 0.0


# ---- THE CRITICAL SEMANTIC TEST -------------------------------------

def test_unavailable_is_not_zero_and_not_a_safety_fallback(ui):
    """UNAVAILABLE must never become 0, 13.89, or any other speed."""
    assert ui.fmt_value(None) != ui.fmt_value(0.0)
    assert ui.to_kmh(None) is None
    assert ui.to_kmh(None) != 0.0
    assert ui.to_kmh(None) != 13.89

    # The marker is not a number a reader could mistake for a speed.
    with pytest.raises(ValueError):
        float(ui.fmt_value(None))


def test_missing_safe_speed_never_implies_safe(ui):
    """No ceiling means no violation evidence - but also no clearance."""
    assert ui.exceeds(20.0, None) is False        # cannot claim a violation
    assert ui.safety_known(None) is False         # ...and must not claim safety either
    assert ui.safety_known(0.0) is True           # 0.0 IS a known ceiling
    assert ui.exceeds(1.0, 0.0) is True           # moving above a 0 ceiling is a violation


def test_exceeds_handles_unknown_actual_speed(ui):
    assert ui.exceeds(None, 10.0) is False
    assert ui.exceeds(None, None) is False
    assert ui.exceeds(10.5, 10.0, 0.1) is True
    assert ui.exceeds(10.05, 10.0, 0.1) is False


def test_fmt_value_survives_non_numeric(ui):
    for junk in ("abc", object(), [], {}):
        assert ui.fmt_value(junk) == ui.UNAVAILABLE_TEXT


# ---------------------------------------------------------------------
# Cases 1-8 against the REAL bridge telemetry dictionaries
# ---------------------------------------------------------------------

def test_case1_fully_populated_simulation_vehicle(bridge, ui):
    bridge.set_visibility(50.0)
    for _ in range(3):
        bridge.step()

    fleet = bridge.get_fleet_telemetry()
    assert fleet, "no vehicles rendered"
    row = fleet[0]

    assert row["v_safe_kmh"] is not None
    assert ui.fmt_value(row["v_safe_kmh"]) != ui.UNAVAILABLE_TEXT
    assert row["speed_kmh"] is not None


def test_case4_unavailable_v_safe_formats_without_raising(bridge, ui):
    """The exact draw-path expression that used to raise on None."""
    row = dict(bridge.get_fleet_telemetry()[0])
    row["v_safe_kmh"] = None

    assert ui.fmt_value(row["v_safe_kmh"]) == ui.UNAVAILABLE_TEXT

    # The pre-P7.1 expression would have raised here.
    with pytest.raises(TypeError):
        f"{row['v_safe_kmh']:4.1f}"


def test_case5_unavailable_road_limit_formats_without_raising(bridge, ui):
    telemetry = dict(bridge.get_telemetry())
    telemetry["speed_limit_kmh"] = None
    assert ui.fmt_value(telemetry["speed_limit_kmh"]) == ui.UNAVAILABLE_TEXT


def test_telemetry_conversions_preserve_unavailable(bridge):
    """to_kmh must not turn an unavailable m/s value into a number."""
    telemetry = bridge.get_telemetry()
    for mps_key, kmh_key in (("v_safe_mps", "v_safe_kmh"), ("speed_limit_mps", "speed_limit_kmh")):
        if telemetry.get(mps_key) is None:
            assert telemetry[kmh_key] is None, f"{kmh_key} fabricated from a missing {mps_key}"


def test_case7_stale_and_case8_unavailable_fields(bridge, ui):
    from twin.twin_state_store import ClockDomain, UNAVAILABLE

    vehicle_id = bridge.sim.vehicles[0].id

    # Unavailable: a field the Twin does not hold.
    assert bridge.twin.get_vehicle_field(vehicle_id, "heading_rad") is UNAVAILABLE
    assert ui.fmt_value(None) == ui.UNAVAILABLE_TEXT

    # Stale: evaluated in its own clock domain, and still not a fabricated value.
    field = bridge.twin.get_vehicle_field(vehicle_id, "v_safe_mps")
    assert field.freshness(bridge.sim.current_time + 10_000.0, 3.0, ClockDomain.SIMULATION) == "STALE"
    assert field.value is not None          # staleness does not erase the last known value


def test_case2_and_3_hardware_only_vehicle_missing_position_and_road(bridge, ui):
    from telemetry_ingest import TelemetryIngestor, Transport
    from twin.twin_state_store import UNAVAILABLE

    ingestor = TelemetryIngestor(bridge.twin)
    ingestor.ingest_parsed_record(
        {"vehicle_id": "TRUCK_02", "sequence_number": 4_200_001, "rpm": 180.0,
         "acceleration": {"x": 0.1, "y": 0.0, "z": 9.81}},
        transport=Transport.DIRECT_WIFI, is_simulated=False,
    )

    # No fabricated heading for a hardware-only vehicle, and it renders as UNAVAILABLE.
    heading = bridge.twin.get_vehicle_field("TRUCK_02", "heading_rad")
    assert heading is UNAVAILABLE
    assert ui.fmt_value(heading.value if heading.is_available else None) == ui.UNAVAILABLE_TEXT


def test_case6_hybrid_vehicle_renders_both_domains(bridge, ui):
    from telemetry_ingest import TelemetryIngestor, Transport
    from twin.twin_state_store import Source

    ingestor = TelemetryIngestor(bridge.twin)
    ingestor.ingest_parsed_record(
        {"vehicle_id": "TRUCK_01", "sequence_number": 4_300_001, "rpm": 177.0,
         "acceleration": {"x": 0.1, "y": 0.0, "z": 9.81}},
        transport=Transport.DIRECT_WIFI, is_simulated=False,
    )
    bridge.step()

    rpm = bridge.twin.get_vehicle_field("TRUCK_01", "rpm")
    position = bridge.twin.get_vehicle_field("TRUCK_01", "position_s")

    assert rpm.source is Source.HARDWARE and rpm.value == 177.0
    assert position.source is Source.SIMULATION
    # Both render as real values; neither is a fabricated stand-in.
    assert ui.fmt_value(rpm.value) != ui.UNAVAILABLE_TEXT
    assert ui.fmt_value(position.value) != ui.UNAVAILABLE_TEXT


# ---------------------------------------------------------------------
# Whole-fleet sweep: nothing in the display path raises on unavailable data
# ---------------------------------------------------------------------

def test_full_display_sweep_never_raises(bridge, ui):
    """Exercise the value paths the renderer formats, across a fog sweep."""
    for visibility in (50.0, 30.0, 10.0, 5.0):
        bridge.set_visibility(visibility)
        for _ in range(2):
            bridge.step()

        for row in bridge.get_fleet_telemetry():
            for key in ("speed_kmh", "v_safe_kmh", "v_command_kmh"):
                if key in row:
                    ui.fmt_value(row[key])          # must not raise

        telemetry = bridge.get_telemetry()
        for value in telemetry.values():
            if isinstance(value, (int, float)) or value is None:
                ui.fmt_value(value)                 # must not raise
