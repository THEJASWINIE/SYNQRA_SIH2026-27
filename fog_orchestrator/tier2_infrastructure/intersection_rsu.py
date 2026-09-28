"""
Tier 2: Intersection & Switchback Roadside Unit (RSU) Manager
Manages V2I broadcasts, speed harmonization, and local infrastructure state.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional
from fog_orchestrator.tier2_infrastructure.slot_reservation import VirtualSlotScheduler, SlotRequest, ReservedSlot

@dataclass
class RSUState:
    """Roadside Unit Operational State."""
    rsu_id: str
    edge_id: str
    visibility_broadcast_m: float
    friction_broadcast: float
    active_reservations: List[ReservedSlot]
    comm_health: float = 1.0  # V2I link quality: 1.0 (healthy) down to 0.0 (lost)


class IntersectionRSU:
    """Roadside Unit managing local infrastructure state and V2I communications."""
    def __init__(self, rsu_id: str, edge_id: str, zone_length_m: float):
        self.rsu_id = rsu_id
        self.edge_id = edge_id
        self.scheduler = VirtualSlotScheduler(conflict_zone_id=rsu_id, zone_length_m=zone_length_m)
        self.comm_health = 1.0

    def process_vehicle_beacon(
        self,
        vehicle_id: str,
        is_loaded: bool,
        is_downhill: bool,
        current_time_s: float,
        eta_to_zone_s: float,
        v_safe_kmh: float
    ) -> ReservedSlot:
        """Processes incoming vehicle beacon and returns allocated virtual slot reservation."""
        self.scheduler.clear_past_slots(current_time_s)

        eta_start = current_time_s + eta_to_zone_s
        eta_end = eta_start + max(5.0, self.scheduler.zone_length_m / max(1.0, v_safe_kmh / 3.6))

        req = SlotRequest(
            vehicle_id=vehicle_id,
            is_loaded=is_loaded,
            is_downhill=is_downhill,
            eta_start_s=eta_start,
            eta_end_s=eta_end
        )

        allocated_slot = self.scheduler.allocate_slot(req, v_safe_kmh)
        return allocated_slot

    def get_rsu_state(self, visibility_m: float, friction: float) -> RSUState:
        return RSUState(
            rsu_id=self.rsu_id,
            edge_id=self.edge_id,
            visibility_broadcast_m=visibility_m,
            friction_broadcast=friction,
            active_reservations=self.scheduler.reserved_slots,
            comm_health=self.comm_health
        )
