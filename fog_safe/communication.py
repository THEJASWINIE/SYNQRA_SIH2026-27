"""
Model 12 — Communication Latency & Adaptive Safety Margin Model.
"""

from fog_safe.config import ReactionTimeParameters, SafetyMarginParameters

class CommunicationModel:
    """
    Models communication quality index C_comm in [0, 1], dynamic latency, and adaptive safety margin expansion.
    """
    def __init__(
        self,
        c_comm: float = 1.0,
        rx_params: ReactionTimeParameters = None,
        margin_params: SafetyMarginParameters = None
    ):
        self.c_comm = max(0.0, min(1.0, c_comm))
        self.rx_params = rx_params if rx_params is not None else ReactionTimeParameters()
        self.margin_params = margin_params if margin_params is not None else SafetyMarginParameters()

    @property
    def tau_comm(self) -> float:
        """
        V2X communication latency grows as quality degrades.
        At C_comm=1, tau_comm = base (0.1s).
        At C_comm=0, tau_comm = base + 1.0s penalty.
        """
        penalty = 1.0 * (1.0 - self.c_comm)
        return self.rx_params.tau_comm_base + penalty

    @property
    def tau_total(self) -> float:
        """
        Total perception-to-action latency tau_total.
        tau_total = tau_sensor + tau_comm + tau_decision + tau_human
        """
        return self.rx_params.tau_sensor + self.tau_comm + self.rx_params.tau_decision + self.rx_params.tau_human

    def calculate_safety_margin(self, v: float) -> float:
        """
        Calculates adaptive safety margin S_margin (meters):
        S_margin = S_base + k_comm * (1 - C_comm) * v
        """
        return self.margin_params.s_base + self.margin_params.k_comm * (1.0 - self.c_comm) * v
