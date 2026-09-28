class BaselineDispatch:
    """
    Implements a static time-based departure dispatch policy.
    Releases vehicles from Shovel at a constant baseline rate.
    """
    def __init__(self, shovel_service_rate_vph: float):
        self.shovel_service_rate_vph = shovel_service_rate_vph
        self.default_delay_s = 3600.0 / shovel_service_rate_vph

    def calculate_release_delay(self, current_time: float, network_state: dict) -> float:
        """
        Always returns the default static release interval based on shovel capacity.
        Does not adapt to downstream capacity or queue surges.
        """
        return self.default_delay_s
