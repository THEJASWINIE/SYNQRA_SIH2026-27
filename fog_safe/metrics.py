"""
Evaluation & System Performance Metrics.
"""

import numpy as np
import pandas as pd

def compute_summary_statistics(series: pd.Series) -> dict:
    """Computes mean, median, 5th percentile, 95th percentile, min, max."""
    return {
        "mean": float(series.mean()),
        "std": float(series.std()),
        "median": float(series.median()),
        "p5": float(np.percentile(series, 5)),
        "p95": float(np.percentile(series, 95)),
        "min": float(series.min()),
        "max": float(series.max())
    }

def evaluate_safety_margin_buffer(s_stop: float, s_margin: float, r_effective: float) -> dict:
    """
    Evaluates residual safety buffer: R_effective - (S_stop + S_margin).
    """
    buffer = r_effective - (s_stop + s_margin)
    return {
        "s_stop": s_stop,
        "s_margin": s_margin,
        "r_effective": r_effective,
        "residual_buffer_m": buffer,
        "is_violating": buffer < -1e-4
    }
