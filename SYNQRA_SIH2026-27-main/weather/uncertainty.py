import numpy as np

class UncertaintyModel:
    """
    Models parameter distributions and errors for Monte Carlo sweeps
    and chance-constrained predictive control.
    """
    @staticmethod
    def sample_visibility(nominal: float, std_dev: float = 5.0, size: int = 1) -> np.ndarray:
        """Sample visibility from a normal distribution, clamped to [5.0, 50.0] meters."""
        samples = np.random.normal(nominal, std_dev, size)
        return np.clip(samples, 5.0, 50.0)

    @staticmethod
    def sample_friction(nominal_mu: float, std_dev: float = 0.05, size: int = 1) -> np.ndarray:
        """Sample friction coefficient from a normal distribution, clamped to [0.15, 0.65]."""
        samples = np.random.normal(nominal_mu, std_dev, size)
        return np.clip(samples, 0.15, 0.65)

    @staticmethod
    def sample_vehicle_mass(nominal_mass: float, std_dev: float = 2000.0, size: int = 1) -> np.ndarray:
        """Sample vehicle mass (kg) from a normal distribution to represent payload variance."""
        samples = np.random.normal(nominal_mass, std_dev, size)
        return np.maximum(50000.0, samples)  # Must be positive and realistic
