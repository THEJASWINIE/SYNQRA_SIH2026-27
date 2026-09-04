"""
Tier 2: Infrastructure Virtual Slot Reservation & Conflict Arbitration System (Post-Audit Corrected Version)
Handles switchbacks, narrow two-way conflict zones, and crusher approach corridors with dynamic safety clearance buffers.
"""

import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

@dataclass
class SlotRequest:
    """Request for virtual slot reservation through a conflict zone."""
    vehicle_id: str
    is_loaded: bool
    is_downhill: bool
    eta_start_s: float
    eta_end_s: float
    priority_score: float = 0.0

@dataclass
class ReservedSlot:
    """Allocated non-overlapping slot in conflict zone."""
    vehicle_id: str
    t_start_s: float
    t_end_s: float
    target_speed_kmh: float

class VirtualSlotScheduler:
    """
    Tier 2 Virtual Slot Scheduler for conflict zones (Switchbacks, Intersections, Narrow Haul Roads).
    Arbitrates arrival windows [t_start, t_end] to ensure non-overlapping occupancy.
    """
    def __init__(self, conflict_zone_id: str, zone_length_m: float, priority_policy: str = "LOADED_DOWNHILL_PRIORITY"):
        self.conflict_zone_id = conflict_zone_id
        self.zone_length_m = zone_length_m
        self.priority_policy = priority_policy
        self.reserved_slots: List[ReservedSlot] = []

    def compute_priority(self, req: SlotRequest) -> float:
        """Computes priority score based on configurable policy."""
        if self.priority_policy == "LOADED_DOWNHILL_PRIORITY":
            # Highest priority to 165t loaded dumpers descending steep 8% grades (high momentum/braking risk)
            score = 100.0 if (req.is_loaded and req.is_downhill) else (50.0 if req.is_loaded else 10.0)
            score -= req.eta_start_s * 0.1
            return score
        elif self.priority_policy == "FCFS":
            return -req.eta_start_s
        else: # QUEUE_BALANCED
            return req.priority_score - req.eta_start_s * 0.05

    def allocate_slot(
        self,
        request: SlotRequest,
        v_safe_kmh: float,
        safety_clearance_s: float = 5.0  # Dynamic default clearance buffer
    ) -> ReservedSlot:
        """
        Allocates safe non-overlapping departure slot for request.
        Adjusts target speed or delays departure if conflict window overlaps.
        """
        v_safe_mps = max(1.0, v_safe_kmh / 3.6)
        # Dynamically scale slot clearance time based on stopping time on steep descents
        dynamic_clearance = max(safety_clearance_s, (v_safe_mps / 2.0) + 2.0)

        req_duration = max(3.0, self.zone_length_m / v_safe_mps)
        desired_start = request.eta_start_s

        self.reserved_slots.sort(key=lambda s: s.t_start_s)
        allocated_start = desired_start

        conflict_found = True
        while conflict_found:
            conflict_found = False
            allocated_end = allocated_start + req_duration
            for slot in self.reserved_slots:
                if not (allocated_end + dynamic_clearance <= slot.t_start_s or allocated_start >= slot.t_end_s + dynamic_clearance):
                    allocated_start = slot.t_end_s + dynamic_clearance
                    conflict_found = True
                    break

        allocated_end = allocated_start + req_duration
        travel_time = allocated_end - allocated_start
        v_target_mps = self.zone_length_m / travel_time if travel_time > 0 else v_safe_mps
        v_target_kmh = min(v_safe_kmh, v_target_mps * 3.6)

        new_slot = ReservedSlot(
            vehicle_id=request.vehicle_id,
            t_start_s=allocated_start,
            t_end_s=allocated_end,
            target_speed_kmh=v_target_kmh
        )
        self.reserved_slots.append(new_slot)
        return new_slot

    def clear_past_slots(self, current_time_s: float):
        """Purges expired slots."""
        self.reserved_slots = [s for s in self.reserved_slots if s.t_end_s > current_time_s]
