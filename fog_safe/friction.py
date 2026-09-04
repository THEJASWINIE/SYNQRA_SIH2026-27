"""
Model 10 — Tire-Road Friction Model & Condition Classifications.
"""

from dataclasses import dataclass

@dataclass
class FrictionState:
    """
    Friction state container tracking true ground-truth friction, prior, and estimation bounds.
    """
    mu_true: float = 0.35
    mu_prior: float = 0.35
    mu_hat: float = 0.35
    sigma_mu: float = 0.10

    @property
    def mu_lower(self) -> float:
        """Safety-critical lower bound mu_lower = mu_hat - 2*sigma_mu, bounded above zero."""
        return max(0.05, self.mu_hat - 2.0 * self.sigma_mu)

def classify_friction_condition(mu: float) -> str:
    """Classifies numerical friction coefficient into surface category label."""
    if mu >= 0.65:
        return "Dry Hardpack"
    elif mu >= 0.50:
        return "Damp Haul Road"
    elif mu >= 0.35:
        return "Wet Compacted Surface"
    elif mu >= 0.25:
        return "Loose Gravel / Silt"
    else:
        return "Muddy / Slippery Slope"
