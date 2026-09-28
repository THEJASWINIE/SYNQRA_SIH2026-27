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
    
    Internal Physics Convention:
      +x direction = downhill forward travel direction
      percent_grade > 0 = downhill grade (radians theta > 0, gravity opposes deceleration)
      percent_grade < 0 = uphill grade (radians theta < 0, gravity assists deceleration)

    Standard Civil Convention:
      civil_grade_pct > 0 = uphill (+8%)
      civil_grade_pct < 0 = downhill (-8%)
      civil_grade_pct == -percent_grade
    """
    def __init__(
        self,
        percent_grade: float = 0.0,
        c_rr: float = 0.02,
        curve_radius: float = np.inf,
        speed_limit_kmh: float = 20.0,
        civil_grade_pct: float = None
    ):
        """
        :param percent_grade: Internal physics grade in % (+8.0 for 8% downhill, -4.0 for 4% uphill)
        :param c_rr: Coefficient of rolling resistance (dimensionless)
        :param curve_radius: Radius of horizontal curve in meters (np.inf for straight road)
        :param speed_limit_kmh: Regulatory site speed limit in km/h
        :param civil_grade_pct: Standard civil engineering grade in % (-8.0 for downhill, +8.0 for uphill)
        """
        if civil_grade_pct is not None:
            self.percent_grade = -float(civil_grade_pct)
        else:
            self.percent_grade = float(percent_grade)

        self.c_rr = c_rr
        self.curve_radius = curve_radius
        self.speed_limit_kmh = speed_limit_kmh

    @classmethod
    def from_civil_grade(
        cls,
        civil_grade_pct: float,
        c_rr: float = 0.02,
        curve_radius: float = np.inf,
        speed_limit_kmh: float = 20.0
    ) -> "RoadSegment":
        """Factory method constructing a RoadSegment from standard civil grade (uphill > 0, downhill < 0)."""
        return cls(
            percent_grade=-float(civil_grade_pct),
            c_rr=c_rr,
            curve_radius=curve_radius,
            speed_limit_kmh=speed_limit_kmh
        )

    @property
    def civil_grade_pct(self) -> float:
        """Returns road grade in standard civil engineering convention: + uphill, - downhill."""
        return -self.percent_grade

    @property
    def theta(self) -> float:
        """Returns road grade angle theta in radians. Downhill theta > 0."""
        return np.arctan(self.percent_grade / 100.0)

    @property
    def speed_limit_ms(self) -> float:
        return self.speed_limit_kmh / 3.6
