class ServiceQueue:
    """
    Simulates a service node queue where vehicles are served one by one.
    The service rate determines the service time required per vehicle.
    """
    def __init__(self, node_id: str, service_rate_vph: float):
        self.node_id = node_id
        self.service_rate_vph = service_rate_vph
        self.vehicles = []  # List of vehicles in queue
        self.accumulated_service_time = 0.0
        
    @property
    def service_time_s(self) -> float:
        """Calculate service time per vehicle in seconds."""
        if self.service_rate_vph <= 0:
            return float('inf')
        return 3600.0 / self.service_rate_vph

    def add_vehicle(self, vehicle):
        """Append vehicle to queue."""
        vehicle.state = "queued"
        vehicle.speed_mps = 0.0
        vehicle.acceleration_mps2 = 0.0
        self.vehicles.append(vehicle)

    def step(self, dt: float) -> list:
        """
        Advance the service timer. If service time matches service_time_s,
        discharge the vehicle from the head of the queue.
        Returns the list of discharged vehicles.
        """
        discharged = []
        if not self.vehicles:
            self.accumulated_service_time = 0.0
            return discharged

        # Accumulate service time for the vehicle at the head of the queue
        self.accumulated_service_time += dt
        
        # Check if service is complete
        if self.accumulated_service_time >= self.service_time_s:
            # Service completed
            vehicle = self.vehicles.pop(0)
            
            # Perform action based on node type
            if "SHOVEL" in self.node_id:
                vehicle.load_cargo()
            elif "CRUSHER" in self.node_id:
                vehicle.unload_cargo()
                
            discharged.append(vehicle)
            # Reset service timer, subtract service time to handle excess dt correctly
            self.accumulated_service_time = max(0.0, self.accumulated_service_time - self.service_time_s)
            
        return discharged

    @property
    def length(self) -> int:
        return len(self.vehicles)


def calculate_next_queue_size(q_current: float, arrivals: float, departures: float) -> float:
    """
    Analytical discrete-time queue dynamics.
      Q(t + dt) = max(0, Q(t) + arrivals - departures)
    """
    return max(0.0, q_current + arrivals - departures)
