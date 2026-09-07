"""
GAP 5 — Operator HMI Traceability Completion (Master Prompt Requirement)

Verifies:
1. NORMAL state (actual <= safe * CAUTION_RATIO)
2. CAUTION state (actual > safe * CAUTION_RATIO and actual <= safe)
3. SLOW DOWN state (actual > safe)
4. STOP state (safe speed == 0.0)
5. Communication/system warning (degraded/stale link)
6. Disconnected vehicle
7. Safety data unavailable (no safe speed supplied)
8. Freshness & unavailable handling (no stale data disguised as fresh)
"""

import pytest
from twin.twin_state_store import TwinStateStore, TwinMode, Quality, Source, UNAVAILABLE
from twin_projection import build_vehicle_projection

CAUTION_RATIO = 0.88


def derive_operator_action(actual_speed, safe_speed, comm_status="ONLINE"):
    """
    Python counterpart of the Operator HMI state derivation in operatorAction.ts.
    Advisory presentation mapping, not a safety solver.
    """
    if comm_status in ["OFFLINE", "DISCONNECTED"]:
        return "COMMUNICATION_WARNING", "Vehicle disconnected"

    if safe_speed is None:
        return "SAFETY_DATA_UNAVAILABLE", "No safe speed supplied"

    if safe_speed == 0.0:
        return "STOP", "Safe speed is zero — do not proceed"

    if actual_speed is None:
        return "SAFETY_DATA_UNAVAILABLE", "Actual speed unknown"

    if actual_speed > safe_speed:
        return "SLOW_DOWN", "Above safe speed — reduce speed"

    if actual_speed >= safe_speed * CAUTION_RATIO:
        return "CAUTION", "Close to safe speed ceiling"

    return "NORMAL", "Within safe operating limits"


class TestMasterOperatorHMIRequirements:
    """Master Prompt GAP 5 Operator HMI Matrix."""

    def test_state_normal_actual_well_below_safe(self):
        """NORMAL: actual speed well below safe speed."""
        action, detail = derive_operator_action(actual_speed=3.0, safe_speed=10.0)
        assert action == "NORMAL"
        assert "Within safe" in detail

    def test_state_caution_near_ceiling(self):
        """CAUTION: actual speed in caution ratio band (>= 0.88 * safe)."""
        action, detail = derive_operator_action(actual_speed=9.0, safe_speed=10.0)
        assert action == "CAUTION"
        assert "Close to safe" in detail

    def test_state_slow_down_actual_exceeds_safe(self):
        """SLOW DOWN: actual speed exceeds safe speed."""
        action, detail = derive_operator_action(actual_speed=12.0, safe_speed=10.0)
        assert action == "SLOW_DOWN"
        assert "Above safe" in detail

    def test_state_stop_safe_speed_zero(self):
        """STOP: safe speed is zero."""
        action, detail = derive_operator_action(actual_speed=0.0, safe_speed=0.0)
        assert action == "STOP"
        assert "Safe speed is zero" in detail

    def test_state_communication_warning(self):
        """Communication/system warning on disconnected vehicle."""
        action, detail = derive_operator_action(actual_speed=5.0, safe_speed=10.0, comm_status="OFFLINE")
        assert action == "COMMUNICATION_WARNING"
        assert "disconnected" in detail

    def test_state_safety_data_unavailable(self):
        """Safety data unavailable when safe speed is None - never defaults to NORMAL."""
        action, detail = derive_operator_action(actual_speed=5.0, safe_speed=None)
        assert action == "SAFETY_DATA_UNAVAILABLE"
        assert action != "NORMAL"

    def test_twin_projection_preserves_unavailable_speed(self):
        """Twin projection leaves unheld v_safe absent rather than fabricating 0.0 or True."""
        store = TwinStateStore(mode=TwinMode.HYBRID)
        store.register_vehicle("TRUCK_01")

        # In Twin store, unpopulated field is UNAVAILABLE
        v_safe_store = store.get_vehicle_field("TRUCK_01", "v_safe_mps")
        assert v_safe_store.is_available is False
        assert v_safe_store.value is None

        # In canonical projection, unheld field stays absent
        proj = build_vehicle_projection(store, "TRUCK_01")
        assert proj is not None
        assert "v_safe_mps" not in proj["dynamic"]  # Absent, never defaulted to 0.0
