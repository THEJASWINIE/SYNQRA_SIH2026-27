"""
Road Geometry & Environment Model.
Enforces strictly:
  +x direction = downhill travel direction
  theta > 0 = downhill grade (radians)
"""

import numpy as np

class RoadSegment:
    """
    Represents a haul road segment with grade, surface rolling resistance, curve radius, and site limits.
    """
    def __init__(self, percent_grade: float = 0.0, c_rr: float = 0.02, curve_radius: float = np.inf, speed_limit_kmh: float = 20.0):
        """
        :param percent_grade: Grade in % (e.g. +8.0 for 8% downhill, -4.0 for 4% uphill)
        :param c_rr: Coefficient of rolling resistance (dimensionless)
        :param curve_radius: Radius of horizontal curve in meters (np.inf for straight road)
        :param speed_limit_kmh: Regulatory site speed limit in km/h
        """
        self.percent_grade = percent_grade
        self.c_rr = c_rr
        self.curve_radius = curve_radius
        self.speed_limit_kmh = speed_limit_kmh

    @property
    def theta(self) -> float:
        """Returns road grade angle theta in radians. Downhill theta > 0."""
        return np.arctan(self.percent_grade / 100.0)

    @property
    def speed_limit_ms(self) -> float:
        return self.speed_limit_kmh / 3.6
