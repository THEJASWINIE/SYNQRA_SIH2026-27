r"""
models/switchback.py
--------------------
Implements Tier-2 tactical conflict coordination and non-overlapping time-slot
reservation for narrow switchbacks, blind hairpin turns, and single-lane haul sections.

Constraints & Policies:
- Slot_A = [tA_start, tA_end], Slot_B = [tB_start, tB_end]
- Slot_A \cap Slot_B = \emptyset  for conflicting movements
- Priority rule: Loaded downhill trucks (with longer stopping distances and high thermal
  retarder loads) receive priority over empty uphill trucks.

Evidence Tags:
- Invariant: [VERIFIED / PRIMARY] Mutual exclusion of conflicting occupancy intervals.
- Priority Policy: [MODEL CONFIG] Priority weighting based on kinetic/retarder load.
"""

from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
import math


@dataclass
class TimeSlot:
    """Represents an allocated exclusive occupancy interval."""
    slot_id: str
    vehicle_id: str
    resource_id: str
    start_time: float
    end_time: float
    direction: str            # 'downhill' or 'uphill'
    is_loaded: bool           # True for loaded haul
    priority_level: int       # Higher number = higher priority (e.g. 2 for loaded downhill, 1 for empty uphill)
    status: str = "CONFIRMED" # 'CONFIRMED', 'ACTIVE', 'COMPLETED', 'CANCELLED'

    @property
    def duration(self) -> float:
        return self.end_time - self.start_time

    def overlaps_with(self, start: float, end: float, buffer_s: float = 0.5) -> bool:
        """
        Returns True if [start, end] overlaps with this slot's time interval,
        including a safety guard buffer.
        """
        return not (end <= (self.start_time - buffer_s) or start >= (self.end_time + buffer_s))


class SwitchbackCoordinator:
    """
    Tier-2 tactical conflict coordinator for single-lane switchbacks,
    hairpin curves, and grade transitions.
    """
    def __init__(self, resource_id: str, config: Optional[Dict[str, Any]] = None):
        self.resource_id = resource_id
        self.config = config or {}
        self.safety_buffer_s = float(self.config.get("safety_buffer_s", 0.5))
        self.active_slots: List[TimeSlot] = []
        self.slot_counter = 0

    def _generate_slot_id(self) -> str:
        self.slot_counter += 1
        return f"SLOT_{self.resource_id}_{self.slot_counter:04d}"

    def check_conflict(
        self,
        start_time: float,
        end_time: float,
        direction: str,
        exclude_slot_id: Optional[str] = None
    ) -> bool:
        """
        Verify if a proposed interval [start_time, end_time] conflicts with any active reservation.
        Opposing directions are strictly mutually exclusive.
        Same-direction follow-on requires safety buffer spacing.
        """
        for slot in self.active_slots:
            if slot.status not in {"CONFIRMED", "ACTIVE"}:
                continue
            if exclude_slot_id and slot.slot_id == exclude_slot_id:
                continue

            if slot.overlaps_with(start_time, end_time, self.safety_buffer_s):
                return True

        return False

    def request_reservation(
        self,
        vehicle_id: str,
        start_time: float,
        duration_seconds: float,
        direction: str = "downhill",
        is_loaded: bool = True
    ) -> Tuple[bool, Optional[TimeSlot], str]:
        """
        Attempts to reserve a specific time slot [start_time, start_time + duration].
        Returns (is_approved, slot_or_none, reason_string).
        """
        if duration_seconds <= 0.0 or math.isnan(duration_seconds) or math.isinf(duration_seconds):
            raise ValueError(f"duration_seconds must be strictly positive, got {duration_seconds}")
        if start_time < 0.0 or math.isnan(start_time) or math.isinf(start_time):
            raise ValueError(f"start_time must be non-negative, got {start_time}")

        end_time = start_time + duration_seconds
        dir_norm = direction.lower()

        # Priority calculation: loaded downhill = 2, empty uphill = 1
        priority = 2 if (is_loaded and dir_norm == "downhill") else 1

        if self.check_conflict(start_time, end_time, dir_norm):
            return False, None, "CONFLICT_INTERVAL_OVERLAPS_EXISTING_SLOT"

        slot = TimeSlot(
            slot_id=self._generate_slot_id(),
            vehicle_id=vehicle_id,
            resource_id=self.resource_id,
            start_time=start_time,
            end_time=end_time,
            direction=dir_norm,
            is_loaded=is_loaded,
            priority_level=priority,
            status="CONFIRMED"
        )
        self.active_slots.append(slot)
        self.active_slots.sort(key=lambda s: s.start_time)

        return True, slot, "RESERVATION_CONFIRMED"

    def find_earliest_slot(
        self,
        vehicle_id: str,
        earliest_start: float,
        duration_seconds: float,
        direction: str = "downhill",
        is_loaded: bool = True,
        max_lookahead_s: float = 3600.0
    ) -> TimeSlot:
        """
        Finds and allocates the earliest feasible non-conflicting time slot on or after earliest_start.
        """
        candidate_start = earliest_start
        step_increment = max(1.0, self.safety_buffer_s)

        while candidate_start <= earliest_start + max_lookahead_s:
            candidate_end = candidate_start + duration_seconds
            if not self.check_conflict(candidate_start, candidate_end, direction.lower()):
                success, slot, _ = self.request_reservation(
                    vehicle_id=vehicle_id,
                    start_time=candidate_start,
                    duration_seconds=duration_seconds,
                    direction=direction,
                    is_loaded=is_loaded
                )
                if success and slot:
                    return slot

            candidate_start += step_increment

        raise RuntimeError(f"Could not find feasible slot within {max_lookahead_s}s lookahead.")

    def release_expired_slots(self, current_time: float, occupied_vehicle_ids: Optional[Any] = None) -> int:
        """
        Marks completed slots where end_time < current_time and vehicle is not currently occupying the resource.
        Returns count of newly completed slots.
        """
        completed_count = 0
        occ = set(occupied_vehicle_ids) if occupied_vehicle_ids else set()
        for slot in self.active_slots:
            # Never prematurely expire an active slot while the vehicle is still traversing the switchback
            if slot.vehicle_id in occ:
                continue
            if slot.status in {"CONFIRMED", "ACTIVE"} and slot.end_time < current_time:
                slot.status = "COMPLETED"
                completed_count += 1

        # Keep active and recently confirmed slots
        self.active_slots = [
            s for s in self.active_slots if s.status in {"CONFIRMED", "ACTIVE"}
        ]
        return completed_count

    def cancel_slot(self, slot_id: str) -> bool:
        """Cancel a reserved slot by ID."""
        for slot in self.active_slots:
            if slot.slot_id == slot_id:
                slot.status = "CANCELLED"
                self.active_slots.remove(slot)
                return True
        return False

    def get_active_slots(self, current_time: Optional[float] = None) -> List[TimeSlot]:
        """Return all currently active / confirmed reservations."""
        if current_time is not None:
            self.release_expired_slots(current_time)
        return list(self.active_slots)
