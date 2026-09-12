"""
models/queue_model.py
---------------------
Implements discrete-time queue dynamics, finite buffer capacities, service rate
constraints, blocking, overflow handling, and Arrival-Rate Shaping (lambda-shaping).

Equations:
- Q(t + dt) = max(0, Q(t) + A(t) - D(t))
- D(t) <= service_rate * dt
- rho = lambda / mu  (Traffic intensity / utilization)
- lambda_arrival <= mu_node - delta_buffer  (Arrival-rate shaping constraint)
- Delta_t_release >= 3600 / lambda_safe  (Minimum release headway)

Evidence Tags:
- Queue Conservation: [VERIFIED / PRIMARY] Discrete-time mass conservation.
- Arrival Shaping: [MODEL CONFIG] Proactive upstream release metering.
"""

from typing import Dict, Any, Tuple, Optional
import math


class QueueModel:
    """
    Simulates discrete-time vehicle arrival accumulation, service departures,
    finite buffer storage, blocking, and overflow at mine service nodes and segments.
    """
    def __init__(
        self,
        node_id: str,
        service_rate_vph: float,
        queue_max: int = 10,
        initial_queue: float = 0.0
    ):
        if service_rate_vph <= 0.0 or math.isnan(service_rate_vph) or math.isinf(service_rate_vph):
            raise ValueError(f"Service rate must be strictly positive, got {service_rate_vph} vph")
        if queue_max < 0:
            raise ValueError(f"queue_max cannot be negative, got {queue_max}")
        if initial_queue < 0.0 or math.isnan(initial_queue) or math.isinf(initial_queue):
            raise ValueError(f"initial_queue must be non-negative, got {initial_queue}")

        self.node_id = node_id
        self.service_rate_vph = float(service_rate_vph)
        self.service_rate_vps = self.service_rate_vph / 3600.0
        self.queue_max = float(queue_max)
        self.current_queue = min(float(initial_queue), self.queue_max)
        
        # Cumulative tracking counters
        self.total_arrivals = 0.0
        self.total_departures = 0.0
        self.total_blocked_arrivals = 0.0

    @property
    def is_blocked(self) -> bool:
        """Returns True if queue buffer has reached or exceeded maximum capacity."""
        return self.current_queue >= (self.queue_max - 1e-6)

    @property
    def available_capacity(self) -> float:
        """Returns remaining available buffer space before blocking."""
        return max(0.0, self.queue_max - self.current_queue)

    def get_utilization(self, arrival_rate_vph: float) -> float:
        """
        Calculate traffic intensity (utilization ratio):
        rho = lambda / mu
        """
        if arrival_rate_vph < 0.0 or math.isnan(arrival_rate_vph) or math.isinf(arrival_rate_vph):
            raise ValueError(f"arrival_rate_vph must be non-negative, got {arrival_rate_vph}")
        return arrival_rate_vph / self.service_rate_vph

    def is_stable(self, arrival_rate_vph: float) -> bool:
        """
        Returns True if queue is theoretically stable (rho <= 1.0),
        False if arrival rate exceeds service rate causing unstable queue growth (rho > 1.0).
        """
        return self.get_utilization(arrival_rate_vph) <= 1.0

    def step(
        self,
        dt_seconds: float,
        arrivals: float = 0.0
    ) -> Tuple[float, float, float]:
        """
        Advance queue by time step dt_seconds with incoming arrivals.
        
        Enforces:
        - D(t) <= service_rate * dt
        - Q(t + dt) = max(0, Q(t) + A_accepted(t) - D(t))
        - Q(t + dt) <= Q_max
        
        Returns:
            Tuple[float, float, float]: (departures, new_queue_length, blocked_arrivals)
        """
        if dt_seconds <= 0.0 or math.isnan(dt_seconds) or math.isinf(dt_seconds):
            raise ValueError(f"dt_seconds must be strictly positive, got {dt_seconds}")
        if arrivals < 0.0 or math.isnan(arrivals) or math.isinf(arrivals):
            raise ValueError(f"arrivals must be non-negative, got {arrivals}")

        max_service_capacity = self.service_rate_vps * dt_seconds
        available_vehicles = self.current_queue + arrivals
        departures = min(available_vehicles, max_service_capacity)
        unbounded_queue = self.current_queue + arrivals - departures

        if unbounded_queue > self.queue_max:
            blocked_arrivals = unbounded_queue - self.queue_max
            new_queue = self.queue_max
        else:
            blocked_arrivals = 0.0
            new_queue = max(0.0, unbounded_queue)

        self.current_queue = new_queue
        self.total_arrivals += (arrivals - blocked_arrivals)
        self.total_departures += departures
        self.total_blocked_arrivals += blocked_arrivals

        return departures, new_queue, blocked_arrivals

    def get_state(self) -> Dict[str, Any]:
        """Return instantaneous queue state dictionary."""
        return {
            "node_id": self.node_id,
            "queue_length": self.current_queue,
            "queue_max": self.queue_max,
            "service_rate_vph": self.service_rate_vph,
            "is_blocked": self.is_blocked,
            "available_capacity": self.available_capacity,
            "total_arrivals": self.total_arrivals,
            "total_departures": self.total_departures,
            "total_blocked": self.total_blocked_arrivals
        }

    def reset(self, initial_queue: float = 0.0) -> None:
        """Reset queue state and counters."""
        self.current_queue = min(max(0.0, float(initial_queue)), self.queue_max)
        self.total_arrivals = 0.0
        self.total_departures = 0.0
        self.total_blocked_arrivals = 0.0


class ArrivalRateShaper:
    """
    Arrival-Rate Shaping controller enforcing:
    lambda_arrival <= mu_node - delta_buffer

    Controls upstream truck release timing and metering intervals to prevent
    downstream queue explosion, gridlock, and spillback on haul roads.
    """
    def __init__(self, default_delta_buffer_vph: float = 2.0):
        if default_delta_buffer_vph < 0.0:
            raise ValueError("default_delta_buffer_vph must be non-negative")
        self.default_delta_buffer_vph = float(default_delta_buffer_vph)

    def calculate_safe_arrival_rate(
        self,
        service_rate_vph: float,
        delta_buffer_vph: Optional[float] = None
    ) -> float:
        """
        Calculate maximum permitted arrival rate (vehicles/hour) at a downstream service node:
        lambda_safe = max(0.0, mu_node - delta_buffer)
        """
        if service_rate_vph < 0.0 or math.isnan(service_rate_vph) or math.isinf(service_rate_vph):
            raise ValueError(f"service_rate_vph must be non-negative, got {service_rate_vph}")

        delta = self.default_delta_buffer_vph if delta_buffer_vph is None else delta_buffer_vph
        if delta < 0.0:
            raise ValueError("delta_buffer_vph must be non-negative")

        return max(0.0, service_rate_vph - delta)

    def calculate_release_interval(
        self,
        service_rate_vph: float,
        delta_buffer_vph: Optional[float] = None
    ) -> float:
        """
        Calculate minimum release headway interval in seconds between consecutive truck departures:
        Delta_t_release = 3600 / lambda_safe
        """
        lambda_safe = self.calculate_safe_arrival_rate(service_rate_vph, delta_buffer_vph)
        if lambda_safe <= 1e-4:
            return float("inf")  # Hold releases indefinitely
        return 3600.0 / lambda_safe

    def shape_arrival_rate(
        self,
        requested_arrival_rate_vph: float,
        service_rate_vph: float,
        delta_buffer_vph: Optional[float] = None
    ) -> float:
        """
        Applies arrival-rate shaping to clamp requested release flow:
        lambda_shaped = min(lambda_requested, lambda_safe)
        """
        if requested_arrival_rate_vph < 0.0:
            raise ValueError("requested_arrival_rate_vph must be non-negative")
        lambda_safe = self.calculate_safe_arrival_rate(service_rate_vph, delta_buffer_vph)
        return min(requested_arrival_rate_vph, lambda_safe)

    def evaluate_truck_release(
        self,
        current_time: float,
        last_release_time: float,
        service_rate_vph: float,
        downstream_queue: float,
        downstream_queue_max: float,
        delta_buffer_vph: Optional[float] = None
    ) -> Tuple[bool, float, str]:
        """
        Determines whether a truck can be released from an upstream source (shovel/buffer).
        
        Returns:
            Tuple[bool, float, str]: (is_allowed, delay_required_seconds, status_reason)
        """
        if downstream_queue >= (downstream_queue_max - 1e-4):
            return False, 60.0, "DOWNSTREAM_BUFFER_SATURATED"

        release_interval = self.calculate_release_interval(service_rate_vph, delta_buffer_vph)
        if math.isinf(release_interval):
            return False, float("inf"), "ZERO_PERMITTED_CAPACITY"

        elapsed = current_time - last_release_time
        if elapsed < release_interval:
            required_delay = release_interval - elapsed
            return False, required_delay, "METERING_HEADWAY_ACTIVE"

        return True, 0.0, "RELEASE_PERMITTED"
