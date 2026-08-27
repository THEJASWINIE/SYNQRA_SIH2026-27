class SwitchbackCoordinator:
    """
    Tier 2 switchback/intersection slot reservation coordinator.
    Manages and schedules reservations to prevent overlapping occupancy intervals 
    for conflicting traffic in shared mine conflict zones.
    """
    def __init__(self, priority_policy: str = "stopping_difficulty"):
        # Format: {node_id: [(t_start, t_end, vehicle_id, priority)]}
        self.reservations = {}
        # Priority policies: "stopping_difficulty", "loaded_downhill", "fifo"
        self.priority_policy = priority_policy

    def get_priority(self, vehicle_id: str, is_loaded: bool, grade_percent: float, speed_mps: float, mass_kg: float) -> float:
        """
        Calculate priority based on the active policy.
        Higher value means higher priority.
        """
        if self.priority_policy == "fifo":
            return 1.0
            
        elif self.priority_policy == "loaded_downhill":
            # Priority to loaded vehicles traveling downhill (grade_percent < 0)
            base = 10.0 if is_loaded else 1.0
            grade_mult = 1.0 + abs(grade_percent) / 100.0 if grade_percent < 0 else 1.0
            return base * grade_mult
            
        elif self.priority_policy == "stopping_difficulty":
            # Priority to heavier vehicles moving faster, especially downhill
            # Mass * Speed * (1 - grade_percent/100)
            grade_factor = 1.0 - (grade_percent / 100.0)  # Downhill grade increases priority
            return mass_kg * max(1.0, speed_mps) * grade_factor
            
        return 1.0

    def request_slot(self, node_id: str, t_start: float, t_end: float, vehicle_id: str, 
                     is_loaded: bool = False, grade_percent: float = 0.0, 
                     speed_mps: float = 0.0, mass_kg: float = 74000.0) -> tuple[bool, float]:
        """
        Request a reservation slot [t_start, t_end] at the node.
        Returns:
            (approved: bool, suggested_start_time: float)
            suggested_start_time is t_start if approved, or the next available safe start time if rejected.
        """
        if node_id not in self.reservations:
            self.reservations[node_id] = []
            
        priority = self.get_priority(vehicle_id, is_loaded, grade_percent, speed_mps, mass_kg)
        
        # Check overlaps
        overlap_found = False
        latest_end_time = t_start
        
        for res_start, res_end, res_vid, res_pri in self.reservations[node_id]:
            # Interval overlap: max(start1, start2) < min(end1, end2)
            if max(t_start, res_start) < min(t_end, res_end):
                overlap_found = True
                latest_end_time = max(latest_end_time, res_end)
                
        if not overlap_found:
            # Reserve slot
            self.reservations[node_id].append((t_start, t_end, vehicle_id, priority))
            # Sort reservations by start time
            self.reservations[node_id].sort(key=lambda x: x[0])
            return True, t_start
        else:
            # Overlap found. Check priority.
            # For the MVP, we suggest scheduling immediately after the overlapping slot ends.
            return False, latest_end_time

    def clear_reservations(self):
        self.reservations.clear()
