"""
FOG-ORCHESTRATOR 2.0 — Vehicle Identity Mapper Adapter (Blocker 1 Resolution)

Provides deterministic, bidirectional translation between Phase 1 Physical Vehicle IDs
(TRUCK_01, TRUCK_02) and Phase 2 Digital Twin Fleet Identifiers (vehicle_1, vehicle_2).
Strictly rejects unmapped IDs and logs identity mapping failures.
"""

import logging
from typing import Dict, Optional

logger = logging.getLogger("VehicleIDMapper")

class VehicleIDMapper:
    """Deterministic bidirectional Vehicle ID Mapper."""

    def __init__(self, mapping_dict: Optional[Dict[str, str]] = None):
        if mapping_dict is None:
            self._forward_map: Dict[str, str] = {
                "TRUCK_01": "vehicle_1",
                "TRUCK_02": "vehicle_2"
            }
        else:
            self._forward_map = dict(mapping_dict)

        # Build reverse map
        self._reverse_map: Dict[str, str] = {}
        for p_id, t_id in self._forward_map.items():
            if t_id in self._reverse_map:
                raise ValueError(f"Duplicate twin vehicle ID mapping detected for '{t_id}'")
            self._reverse_map[t_id] = p_id

    def to_twin_id(self, physical_id: str) -> Optional[str]:
        """Translates physical ID (e.g. TRUCK_01) to twin ID (e.g. vehicle_1). Returns None if unmapped."""
        if not physical_id or not isinstance(physical_id, str):
            logger.warning(f"Invalid physical_id input: {physical_id}")
            return None
        
        twin_id = self._forward_map.get(physical_id.strip())
        if not twin_id:
            logger.error(f"[VehicleIDMapper] Identity Mapping Failure: Unknown physical ID '{physical_id}'")
            return None
        return twin_id

    def to_physical_id(self, twin_id: str) -> Optional[str]:
        """Translates twin ID (e.g. vehicle_1) to physical ID (e.g. TRUCK_01). Returns None if unmapped."""
        if not twin_id or not isinstance(twin_id, str):
            logger.warning(f"Invalid twin_id input: {twin_id}")
            return None

        physical_id = self._reverse_map.get(twin_id.strip())
        if not physical_id:
            logger.error(f"[VehicleIDMapper] Reverse Mapping Failure: Unknown twin ID '{twin_id}'")
            return None
        return physical_id

    def is_mapped_physical(self, physical_id: str) -> bool:
        return physical_id in self._forward_map

    def is_mapped_twin(self, twin_id: str) -> bool:
        return twin_id in self._reverse_map
