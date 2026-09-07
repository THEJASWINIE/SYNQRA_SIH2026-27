"""
P7 — game_ui.py as a read-only canonical Twin client.

SIMULATION only. No physical hardware, and pygame is not installed in this environment,
so the GUI itself is not exercised here (see the P7 report).
"""

import importlib.util
import inspect
import os
import subprocess
import sys

import pytest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MAIN_ROOT = os.path.join(REPO_ROOT, "SYNQRA_SIH2026-27-main")
GAME_UI_PATH = os.path.join(MAIN_ROOT, "game_ui.py")


def game_ui_source() -> str:
    with open(GAME_UI_PATH, "r", encoding="utf-8", errors="ignore") as handle:
        return handle.read()


def executable_source(text: str) -> str:
    """Source with docstrings and comments stripped, so prose cannot satisfy a check."""
    without_docstrings = "".join(text.split('"""')[::2])
    return "\n".join(
        line for line in without_docstrings.splitlines() if not line.strip().startswith("#")
    )


@pytest.fixture(scope="module")
def bridge():
    """A real SimulationUIBridge, built headless (pygame is only needed for rendering)."""
    for path in (REPO_ROOT, MAIN_ROOT):
        if path not in sys.path:
            sys.path.insert(0, path)

    spec = importlib.util.spec_from_file_location("game_ui_under_test", GAME_UI_PATH)
    module = importlib.util.module_from_spec(spec)

    previous = os.getcwd()
    os.chdir(MAIN_ROOT)          # the module loads its YAML config relative to the sub-repo
    try:
        spec.loader.exec_module(module)
        return module.SimulationUIBridge()
    finally:
        os.chdir(previous)


# ---------------------------------------------------------------------
# 1/3/4. game_ui is no longer a safety authority
# ---------------------------------------------------------------------

def test_game_ui_never_calls_the_authoritative_solver():
    code = executable_source(game_ui_source())
    for banned in ("resolve_v_safe(", "solve_safe_speed(", "calculate_stopping_distance("):
        assert banned not in code, f"game_ui calls the safety solver directly: {banned}"


def test_game_ui_does_not_import_the_solver():
    code = executable_source(game_ui_source())
    for banned in (
        "from models.vehicle_physics import",
        "from models.braking import",
        "from fog_safe",
        "import fog_safe",
    ):
        assert banned not in code, f"game_ui imports the safety layer: {banned}"


def test_no_duplicate_safety_formula_remains_in_game_ui():
    code = executable_source(game_ui_source())
    for banned in ("math.sqrt", "np.sqrt", "* 9.81", "9.81 *"):
        assert banned not in code, f"game_ui appears to compute physics: {banned}"


def test_no_hardcoded_safety_fallback_remains():
    """13.89 m/s (50 km/h) was handed out as a safe speed when none was known."""
    assert "13.89" not in game_ui_source()


def test_domain_service_owns_the_solver_call():
    from twin.ui_domain import UISimulationDomain

    source = inspect.getsource(UISimulationDomain)
    assert "resolve_v_safe(" in source          # the domain calls the ONE adapter
    assert "np.sqrt" not in source              # and implements no formula of its own
    assert "math.sqrt" not in source


# ---------------------------------------------------------------------
# 2. game_ui reads canonical v_safe
# ---------------------------------------------------------------------

def test_bridge_owns_a_canonical_twin(bridge):
    from twin.twin_state_store import TwinStateStore

    assert isinstance(bridge.twin, TwinStateStore)
    assert hasattr(bridge, "domain")


def test_v_safe_is_read_from_the_twin(bridge):
    bridge.set_visibility(50.0)
    bridge.step()

    vehicle_id = bridge.sim.vehicles[0].id
    from_twin = bridge.twin.get_vehicle_field(vehicle_id, "v_safe_mps")

    assert from_twin.is_available
    assert bridge.twin_v_safe_mps(vehicle_id) == from_twin.value


def test_unknown_vehicle_v_safe_is_unavailable_not_optimistic(bridge):
    assert bridge.twin_v_safe_mps("NO_SUCH_TRUCK") is None


# ---------------------------------------------------------------------
# 5/6/7/8. fog -> Twin -> displayed v_safe, and recovery
# ---------------------------------------------------------------------

def test_fog_change_reaches_the_twin_and_lowers_v_safe(bridge):
    vehicle_id = bridge.sim.vehicles[0].id

    bridge.set_visibility(50.0)
    for _ in range(3):
        bridge.step()
    clear = bridge.twin_v_safe_mps(vehicle_id)

    bridge.set_visibility(6.0)
    for _ in range(3):
        bridge.step()
    dense = bridge.twin_v_safe_mps(vehicle_id)

    assert clear is not None and dense is not None
    assert dense < clear, f"dense fog did not lower v_safe ({dense} !< {clear})"

    # ...and the environment change is visible in the Twin itself.
    visibility = bridge.twin.get_environment().get("visibility_m")
    assert visibility.value == pytest.approx(6.0)


def test_clear_fog_dense_clear_recovery(bridge):
    vehicle_id = bridge.sim.vehicles[0].id
    readings = []

    for visibility in (50.0, 30.0, 10.0, 6.0, 30.0, 50.0):
        bridge.set_visibility(visibility)
        for _ in range(3):
            bridge.step()
        readings.append(bridge.twin_v_safe_mps(vehicle_id))

    assert all(r is not None for r in readings)
    # Monotonic down through the fog...
    assert readings[0] >= readings[1] >= readings[2] >= readings[3]
    # ...and recovery on the way back out.
    assert readings[4] > readings[3]
    assert readings[5] > readings[4]
    assert readings[5] == pytest.approx(readings[0])


# ---------------------------------------------------------------------
# 9/13/14/15. provenance, clock domain, freshness
# ---------------------------------------------------------------------

def test_simulated_position_stays_simulation_originated(bridge):
    from twin.twin_state_store import ClockDomain, Source

    bridge.step()
    vehicle_id = bridge.sim.vehicles[0].id
    position = bridge.twin.get_vehicle_field(vehicle_id, "position_s")

    assert position.source is Source.SIMULATION
    assert position.clock_domain is ClockDomain.SIMULATION


def test_v_safe_provenance_is_derived_from_simulation(bridge):
    from twin.twin_state_store import ClockDomain, Source

    bridge.step()
    field = bridge.twin.get_vehicle_field(bridge.sim.vehicles[0].id, "v_safe_mps")

    # A solver output for a simulated truck: DERIVED, but originating in SIMULATION.
    assert field.source is Source.DERIVED
    assert field.origin is Source.SIMULATION
    assert field.clock_domain is ClockDomain.SIMULATION
    assert not field.is_hardware_backed()


def test_twin_uses_the_simulation_clock_not_wall_clock(bridge):
    bridge.step()
    assert bridge.twin.simulation_now == pytest.approx(bridge.sim.current_time)
    # A simulation timestamp is nowhere near epoch seconds.
    assert bridge.twin.simulation_now < 1_000_000


def test_freshness_is_evaluated_in_the_simulation_domain(bridge):
    from twin.twin_state_store import ClockDomain

    bridge.step()
    field = bridge.twin.get_vehicle_field(bridge.sim.vehicles[0].id, "v_safe_mps")

    # Fresh against ITS OWN clock...
    assert field.freshness(bridge.sim.current_time, 3.0, ClockDomain.SIMULATION) == "CURRENT"
    # ...and never judged against a wall clock.
    assert field.freshness(1_788_000_000.0, 3.0, ClockDomain.WALL_CLOCK) == "NOT_EVALUATED"


# ---------------------------------------------------------------------
# 10/11/12. hardware / hybrid behaviour in the same Twin
# ---------------------------------------------------------------------

def test_hardware_only_vehicle_has_no_invented_position(bridge):
    from telemetry_ingest import TelemetryIngestor, Transport
    from twin.twin_state_store import UNAVAILABLE

    ingestor = TelemetryIngestor(bridge.twin)
    ingestor.ingest_parsed_record(
        {"vehicle_id": "TRUCK_02", "sequence_number": 5_000_001, "rpm": 180.0,
         "acceleration": {"x": 0.1, "y": 0.0, "z": 9.81}},
        transport=Transport.DIRECT_WIFI, is_simulated=False,
    )
    # Nothing on the prototype measures heading; it must stay unavailable.
    assert bridge.twin.get_vehicle_field("TRUCK_02", "heading_rad") is UNAVAILABLE


def test_hardware_rpm_is_not_overwritten_by_simulation(bridge):
    from telemetry_ingest import TelemetryIngestor, Transport
    from twin.twin_state_store import Source

    ingestor = TelemetryIngestor(bridge.twin)
    ingestor.ingest_parsed_record(
        {"vehicle_id": "TRUCK_01", "sequence_number": 5_100_001, "rpm": 191.0,
         "acceleration": {"x": 0.1, "y": 0.0, "z": 9.81}},
        transport=Transport.DIRECT_WIFI, is_simulated=False,
    )

    for _ in range(3):
        bridge.step()          # simulation syncs repeatedly over the top

    rpm = bridge.twin.get_vehicle_field("TRUCK_01", "rpm")
    assert rpm.value == 191.0
    assert rpm.source is Source.HARDWARE


# ---------------------------------------------------------------------
# 16/17. commands do not move vehicles
# ---------------------------------------------------------------------

def test_ui_command_does_not_directly_set_actual_speed(bridge):
    bridge.set_visibility(50.0)
    bridge.step()
    vehicle = bridge.sim.vehicles[0]
    before = vehicle.speed_mps

    # Ask for a high target. The UI must not assign it to the vehicle's actual speed.
    bridge.set_target_speed(40.0)
    assert vehicle.speed_mps == before, "a UI command directly mutated actual speed"


def test_commanded_speed_never_exceeds_twin_v_safe(bridge):
    bridge.set_visibility(6.0)
    bridge.set_target_speed(60.0)
    for _ in range(3):
        bridge.step()

    for vehicle in bridge.sim.vehicles:
        v_safe = bridge.twin_v_safe_mps(vehicle.id)
        if v_safe is not None:
            assert vehicle.v_command_mps <= v_safe + 1e-6


# ---------------------------------------------------------------------
# 18. CWD-independent configuration (the P6.1 finding)
# ---------------------------------------------------------------------

def test_unit_converter_resolves_config_from_any_cwd():
    from integration_adapters.unit_converter import UnitConverter

    assert UnitConverter().rpm_to_speed_mps("TRUCK_01", 240.0) is not None


@pytest.mark.parametrize(
    "cwd", ["SYNQRA_SIH2026-27-HMI/backend", "SYNQRA_SIH2026-27-main", "tests"]
)
def test_config_resolves_from_a_different_working_directory(cwd):
    """
    The P6.1 browser run launched uvicorn from backend/ and a legitimately derived speed
    silently became unavailable. Configuration must not depend on the process CWD.
    """
    script = (
        "import sys; sys.path.insert(0, r'%s');"
        "from integration_adapters.unit_converter import UnitConverter;"
        "v = UnitConverter().rpm_to_speed_mps('TRUCK_01', 240.0);"
        "assert v is not None, 'config not found';"
        "print(round(v, 4))" % REPO_ROOT
    )
    result = subprocess.run(
        [sys.executable, "-c", script],
        cwd=os.path.join(REPO_ROOT, cwd), capture_output=True, text=True, timeout=120,
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "1.2566"


def test_all_adapters_use_the_project_anchored_resolver():
    adapters = ("unit_converter", "kinematic_scale", "coordinate_mapper", "twin_velocity_adapter")
    for name in adapters:
        path = os.path.join(REPO_ROOT, "integration_adapters", f"{name}.py")
        with open(path, "r", encoding="utf-8") as handle:
            source = handle.read()
        assert 'os.path.join("config"' not in source, f"{name} still resolves config via CWD"
