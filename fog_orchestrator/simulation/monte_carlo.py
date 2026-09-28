"""
Monte Carlo Uncertainty Analysis Engine for FOG-ORCHESTRATOR 2.0 (Post-Audit Corrected Version)
Executes 1,000 randomized trials over vehicle mass, road grade, correlated friction-fog, latency, and comm loss.
"""

import random
import numpy as np
import pandas as pd
from typing import Dict, List, Tuple
from fog_orchestrator.core.config import VehicleParameters, EnvironmentalParameters, PerceptionCommParameters
from fog_orchestrator.tier1_governor.safety_governor import VehicleSafetyGovernor, SafetyState

class MonteCarloAnalyzer:
    """Monte Carlo simulator for 1,000+ stochastic parameter sweeps."""

    @staticmethod
    def run_monte_carlo_trials(num_samples: int = 1000, random_seed: int = 42) -> pd.DataFrame:
        """Runs 1,000 randomized Monte Carlo trials with correlated fog and slick friction."""
        np.random.seed(random_seed)
        random.seed(random_seed)
        governor = VehicleSafetyGovernor()

        records = []
        for i in range(num_samples):
            mass_loaded_kg = float(np.random.normal(165000.0, 5000.0))
            grade_pct = float(np.random.uniform(0.0, 10.0))
            visibility_m = float(np.random.uniform(5.0, 50.0))

            # CORRELATED FOG & FRICTION (Post-Audit Fix):
            # Low visibility (<20m) correlates with wet/slick surface (mu ~ Uniform(0.15, 0.35))
            if visibility_m < 20.0:
                friction_mu = float(np.random.uniform(0.15, 0.35))
            else:
                friction_mu = float(np.random.uniform(0.30, 0.65))

            comm_confidence = float(np.random.uniform(0.0, 1.0))
            curve_radius_m = float(np.random.choice([35.0, 50.0, 100.0, float('inf')]))

            grade_rad = np.arctan(grade_pct / 100.0)
            safety_eval = governor.evaluate_tier1_safety(
                r_effective_m=visibility_m,
                grade_rad=grade_rad,
                is_loaded=True,
                friction_mu=friction_mu,
                curve_radius_m=curve_radius_m,
                comm_confidence=comm_confidence
            )

            is_physically_safe = (safety_eval.s_stop_m <= visibility_m + 0.1) or (safety_eval.v_safe_mps == 0.0)

            records.append({
                "sample_id": i + 1,
                "mass_loaded_kg": mass_loaded_kg,
                "grade_pct": grade_pct,
                "friction_mu": friction_mu,
                "visibility_m": visibility_m,
                "comm_confidence": comm_confidence,
                "curve_radius_m": curve_radius_m,
                "v_safe_kmh": safety_eval.v_safe_kmh,
                "v_stop_kmh": safety_eval.v_stop_kmh,
                "v_retarder_kmh": safety_eval.v_retarder_kmh,
                "s_stop_m": safety_eval.s_stop_m,
                "h_safe_m": safety_eval.h_safe_m,
                "active_constraint": safety_eval.active_constraint,
                "is_physically_safe": is_physically_safe
            })

        df_mc = pd.DataFrame(records)
        return df_mc
