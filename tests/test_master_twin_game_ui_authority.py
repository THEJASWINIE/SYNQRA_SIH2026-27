"""
GAP 9 — Digital Twin vs game_ui Direct Authority Test (Master Prompt Requirement)

The master prompt requires:
1. Modify Twin State directly.
2. Confirm game_ui reflects it.
3. Modify game_ui display state if possible.
4. Confirm game_ui cannot become authoritative.

Executable test demonstrating the one-way authority invariant:
Twin -> game_ui
and NOT:
game_ui -> Twin
"""

import importlib.util
import os
import sys
import pytest

from twin.twin_state_store import Source, Quality, ClockDomain

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MAIN_ROOT = os.path.join(REPO_ROOT, "SYNQRA_SIH2026-27-main")
GAME_UI_PATH = os.path.join(MAIN_ROOT, "game_ui.py")


@pytest.fixture
def bridge():
    """Create a headless SimulationUIBridge instance."""
    for path in (REPO_ROOT, MAIN_ROOT):
        if path not in sys.path:
            sys.path.insert(0, path)

    spec = importlib.util.spec_from_file_location("game_ui_authority_test", GAME_UI_PATH)
    module = importlib.util.module_from_spec(spec)

    prev_cwd = os.getcwd()
    os.chdir(MAIN_ROOT)
    try:
        spec.loader.exec_module(module)
        return module.SimulationUIBridge()
    finally:
        os.chdir(prev_cwd)


class TestMasterTwinGameUIAuthority:
    """Executable verification of Twin -> game_ui authority."""

    def test_step_1_modify_twin_state_directly(self, bridge):
        """1. Directly modify Twin state."""
        twin = bridge.twin
        vehicle_id = bridge.sim.vehicles[0].id

        # Update Twin with a distinctive safe speed value
        test_safe_speed = 7.42
        twin.update_vehicle_field(
            vehicle_id=vehicle_id,
            name="v_safe_mps",
            value=test_safe_speed,
            source=Source.DERIVED,
            quality=Quality.GOOD,
            clock_domain=ClockDomain.WALL_CLOCK
        )

        field = twin.get_vehicle_field(vehicle_id, "v_safe_mps")
        assert field.value == test_safe_speed

    def test_step_2_confirm_game_ui_reflects_twin(self, bridge):
        """2. Confirm game_ui immediately reflects the Twin's updated value."""
        twin = bridge.twin
        vehicle_id = bridge.sim.vehicles[0].id

        test_safe_speed = 6.28
        twin.update_vehicle_field(
            vehicle_id=vehicle_id,
            name="v_safe_mps",
            value=test_safe_speed,
            source=Source.DERIVED,
            quality=Quality.GOOD,
            clock_domain=ClockDomain.WALL_CLOCK
        )

        # game_ui accessor must read the exact Twin value
        displayed_speed = bridge.twin_v_safe_mps(vehicle_id)
        assert displayed_speed == test_safe_speed
        assert displayed_speed == pytest.approx(6.28)

    def test_step_3_and_4_game_ui_cannot_become_authoritative(self, bridge):
        """
        3. Modify game_ui internal state/attributes.
        4. Confirm game_ui cannot mutate or become authoritative over the Twin.
        """
        twin = bridge.twin
        vehicle_id = bridge.sim.vehicles[0].id

        authoritative_speed = 5.15
        twin.update_vehicle_field(
            vehicle_id=vehicle_id,
            name="v_safe_mps",
            value=authoritative_speed,
            source=Source.DERIVED,
            quality=Quality.GOOD,
            clock_domain=ClockDomain.WALL_CLOCK
        )

        # Simulate rogue attempt on game_ui to forge or override display value
        # Attempt to set arbitrary attribute on bridge
        bridge.forged_safe_speed = 99.99
        if hasattr(bridge, "_cached_display_speed"):
            bridge._cached_display_speed = 99.99

        # Confirm the authoritative Twin state is completely untouched
        twin_field = twin.get_vehicle_field(vehicle_id, "v_safe_mps")
        assert twin_field.value == authoritative_speed
        assert twin_field.value != 99.99

        # Confirm bridge's authoritative accessor still returns the canonical Twin value
        assert bridge.twin_v_safe_mps(vehicle_id) == authoritative_speed

    def test_direction_invariant_twin_to_game_ui_only(self, bridge):
        """
        Demonstrate that calling step() on bridge pulls from Twin and never
        allows game_ui to author or inject its own v_safe.
        """
        twin = bridge.twin
        vehicle_id = bridge.sim.vehicles[0].id

        # Set specific visibility in simulation
        bridge.set_visibility(25.0)
        bridge.step()

        # v_safe was computed by the domain solver and written to the Twin
        twin_v_safe = twin.get_vehicle_field(vehicle_id, "v_safe_mps").value
        assert twin_v_safe is not None

        # game_ui readout is identical to Twin
        assert bridge.twin_v_safe_mps(vehicle_id) == twin_v_safe
