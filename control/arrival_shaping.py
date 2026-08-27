class ArrivalShaper:
    """
    Tier 3 controller responsible for shaping vehicle arrival rates
    at downstream nodes by adjusting departure delays at upstream loading points.
    """
    def __init__(self, target_node_id: str, base_shovel_service_rate_vph: float):
        self.target_node_id = target_node_id
        self.base_shovel_delay_s = 3600.0 / base_shovel_service_rate_vph if base_shovel_service_rate_vph > 0 else 240.0
        self.active_delay_s = self.base_shovel_delay_s
        self.shaping_active = False

    def update_release_delay(self, shaping_active: bool, downstream_queue_len: int,
                             downstream_service_rate_vph: float, delta_buffer_vph: float) -> float:
        """
        Dynamically determine the shovel release delay.
        
        If shaping is inactive:
          return base shovel service time (e.g. 240s for 15 vph).
          
        If shaping is active:
          Calculate target arrival rate based on downstream service rate:
            target_arrival_rate_vph = downstream_service_rate_vph - delta_buffer_vph
          Adjust release delay to be the maximum of shovel service time or target release time:
            target_delay_s = 3600.0 / target_arrival_rate_vph
            release_delay = max(base_shovel_delay, target_delay_s)
          If downstream queue is overloaded (e.g. queue_len >= 2), apply a temporary penalty delay:
            release_delay += queue_len * 120.0 (seconds)
        """
        self.shaping_active = shaping_active
        if not shaping_active:
            self.active_delay_s = self.base_shovel_delay_s
            return self.active_delay_s

        # Downhill/downstream service constraint
        target_arrival_rate = max(1.0, downstream_service_rate_vph - delta_buffer_vph)
        target_delay_s = 3600.0 / target_arrival_rate
        
        # We must not release faster than the physical loading time
        self.active_delay_s = max(self.base_shovel_delay_s, target_delay_s)
        
        # Apply congestion penalty if queue is backed up
        if downstream_queue_len >= 2:
            self.active_delay_s += downstream_queue_len * 120.0  # Add 2 mins per vehicle in queue
            
        return self.active_delay_s
