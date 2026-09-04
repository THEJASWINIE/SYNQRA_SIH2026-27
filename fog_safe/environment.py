"""
Environment & Perception Awareness Model.
"""

from fog_safe.config import EnvironmentParameters

class EnvironmentState:
    """
    Environmental awareness model defining usable perception range R_effective.
    """
    def __init__(self, r_effective: float = 30.0, mu_true: float = 0.35, env_params: EnvironmentParameters = None):
        """
        :param r_effective: Effective usable perception / awareness distance in meters.
        :param mu_true: True ground-truth tire-road friction coefficient.
        :param env_params: Environment parameters dataclass.
        """
        self.r_effective = r_effective
        self.mu_true = mu_true
        self.params = env_params if env_params is not None else EnvironmentParameters()

    @property
    def g(self) -> float:
        return self.params.gravity

    @property
    def rho(self) -> float:
        return self.params.air_density
