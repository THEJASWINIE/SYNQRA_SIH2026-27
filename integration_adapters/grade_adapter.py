"""
integration_adapters/grade_adapter.py
-------------------------------------
Grade Sign Convention & Normalization Adapter (Blocker 2 Resolution).

Conventions:
1. CANONICAL CIVIL ENGINEERING / GIS CONVENTION:
   - Elevation change along vehicle travel direction: Delta_h / Delta_s.
   - Uphill: civil_grade_pct > 0 (e.g. +8.0%). Gravity opposes motion and assists braking.
   - Downhill: civil_grade_pct < 0 (e.g. -8.0%). Gravity pulls vehicle forward and opposes braking.
   - Flat: civil_grade_pct == 0.0%.

2. INTERNAL RESISTANCE CONVENTION (fog_safe/road.py & fog_safe/braking.py):
   - +x direction is forward travel direction.
   - theta > 0 is defined as downhill forward slope where F_grade = m*g*sin(theta) > 0.
   - In braking force balance: F_net_retarding = F_brake + F_roll + F_aero - F_grade.
   - Therefore, internal percent_grade = -civil_grade_pct.

This adapter explicitly normalizes all grade inputs at the system boundary.
"""

from typing import Tuple, Optional
import math
import numpy as np

class GradeConventionError(ValueError):
    """Raised when an invalid or unphysical grade value is provided."""
    pass


class GradeAdapter:
    """
    Authoritative boundary adapter for road elevation and grade conversions.
    Ensures that external civil grades are correctly mapped to internal physical forces.
    """

    MAX_MINE_GRADE_PCT = 25.0  # Open-pit haul roads rarely exceed 15%; 25% hard clamp

    @staticmethod
    def civil_to_physics_grade(civil_grade_pct: float) -> float:
        """
        Converts standard civil engineering grade (uphill > 0, downhill < 0)
        to internal fog_safe physics grade (downhill > 0, uphill < 0).

        :param civil_grade_pct: Grade in % (e.g., -8.0 for 8% downhill, +8.0 for 8% uphill)
        :return: Internal physics percent_grade for fog_safe.RoadSegment
        """
        if civil_grade_pct is None or math.isnan(civil_grade_pct) or math.isinf(civil_grade_pct):
            raise GradeConventionError(f"Invalid civil grade value: {civil_grade_pct}")

        clamped = max(-GradeAdapter.MAX_MINE_GRADE_PCT, min(GradeAdapter.MAX_MINE_GRADE_PCT, float(civil_grade_pct)))
        # Civil downhill (-8%) -> Internal physics positive angle (+8%)
        # Civil uphill (+8%) -> Internal physics negative angle (-8%)
        return -clamped

    @staticmethod
    def physics_to_civil_grade(physics_grade_pct: float) -> float:
        """
        Converts internal fog_safe physics grade back to standard civil grade
        for HMI display, operator HUDs, and GIS maps.

        :param physics_grade_pct: Internal physics percent_grade
        :return: Civil grade in % (+ for uphill, - for downhill)
        """
        if physics_grade_pct is None or math.isnan(physics_grade_pct) or math.isinf(physics_grade_pct):
            raise GradeConventionError(f"Invalid physics grade value: {physics_grade_pct}")

        return -float(physics_grade_pct)

    @staticmethod
    def elevation_to_civil_grade(start_alt_m: float, end_alt_m: float, horizontal_distance_m: float) -> float:
        """
        Computes standard civil grade from two geospatial elevation points.

        :param start_alt_m: Elevation at segment start in meters
        :param end_alt_m: Elevation at segment end in meters
        :param horizontal_distance_m: Horizontal distance traveled in meters
        :return: Civil grade in % (+ uphill, - downhill)
        """
        if horizontal_distance_m <= 0:
            raise GradeConventionError(f"Horizontal distance must be strictly positive, got {horizontal_distance_m} m")

        delta_h = end_alt_m - start_alt_m
        grade_pct = (delta_h / horizontal_distance_m) * 100.0
        return round(float(grade_pct), 4)

    @staticmethod
    def create_adapted_road_segment(
        civil_grade_pct: float,
        c_rr: float = 0.02,
        curve_radius: float = float("inf"),
        speed_limit_kmh: float = 20.0
    ):
        """
        Creates a fog_safe.RoadSegment properly adapted from a standard civil grade input.
        """
        from fog_safe.road import RoadSegment
        physics_grade = GradeAdapter.civil_to_physics_grade(civil_grade_pct)
        return RoadSegment(
            percent_grade=physics_grade,
            c_rr=c_rr,
            curve_radius=curve_radius,
            speed_limit_kmh=speed_limit_kmh
        )
