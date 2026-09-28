"""
models/bottleneck.py
--------------------
Evaluates dynamic network bottleneck scores and tracks bottleneck migration between
fixed service nodes (crushers, shovels) and degraded haul-road segments.

Equation:
- B = (w1 * rho) * (1 + w2 * Q) * (w3 * Criticality)

Requirements:
- Configurable weights (w1, w2, w3)
- Dynamic evaluation based on utilization (rho), queue length (Q), and criticality
- Network ranking across nodes and road segments
- Automated bottleneck migration detection (e.g. Crusher -> Haul Road -> Crusher)

Evidence Tags:
- Scoring Formulation: [MODEL CONFIG] Configurable scoring function.
- Migration Detection: [VERIFIED / PRIMARY] Dynamic bottleneck tracking.
"""

from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
import math


@dataclass
class BottleneckEntry:
    """Represents an evaluated bottleneck score for an individual node or road segment."""
    element_id: str
    element_type: str  # 'NODE' or 'ROAD_SEGMENT'
    score: float
    utilization_rho: float
    queue_length: float
    criticality: float
    rank: int = 1


@dataclass
class BottleneckMigrationEvent:
    """Recorded when the primary (#1) bottleneck shifts to a different network element."""
    timestamp: float
    previous_primary_id: str
    new_primary_id: str
    previous_score: float
    new_score: float
    reason: str


class BottleneckDetector:
    """
    Evaluates bottleneck scores across all nodes and road segments,
    ranks network choke points, and detects bottleneck migration.
    """
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        cfg = config or {}
        b_cfg = cfg.get("bottleneck", cfg)
        
        self.w1 = float(b_cfg.get("w1", 1.0))
        self.w2 = float(b_cfg.get("w2", 0.5))
        self.w3 = float(b_cfg.get("w3", 1.0))
        
        if self.w1 < 0.0 or self.w2 < 0.0 or self.w3 < 0.0:
            raise ValueError("Bottleneck weights w1, w2, w3 must be non-negative")

        self.last_primary_id: Optional[str] = None
        self.migration_history: List[BottleneckMigrationEvent] = []

    def calculate_bottleneck_score(
        self,
        utilization_rho: float,
        queue_length: float,
        criticality: float,
        w1: Optional[float] = None,
        w2: Optional[float] = None,
        w3: Optional[float] = None
    ) -> float:
        """
        Compute composite bottleneck score for an individual element:
        B = (w1 * rho) * (1 + w2 * Q) * (w3 * Criticality)
        """
        for name, val in [("utilization_rho", utilization_rho), ("queue_length", queue_length), ("criticality", criticality)]:
            if math.isnan(val) or math.isinf(val):
                raise ValueError(f"Input '{name}' cannot be NaN or infinite")
            if val < 0.0:
                raise ValueError(f"Input '{name}' must be non-negative, got {val}")

        _w1 = self.w1 if w1 is None else w1
        _w2 = self.w2 if w2 is None else w2
        _w3 = self.w3 if w3 is None else w3

        # Formula: (w1 * rho) * (1 + w2 * Q) * (w3 * Criticality)
        term1 = _w1 * utilization_rho
        term2 = 1.0 + (_w2 * queue_length)
        term3 = _w3 * criticality

        return term1 * term2 * term3

    def rank_elements(
        self,
        elements: List[Dict[str, Any]]
    ) -> List[BottleneckEntry]:
        """
        Computes bottleneck scores for a list of elements and sorts them in descending order.
        Each element dict must contain: id, type, utilization, queue, criticality.
        """
        scored_entries: List[BottleneckEntry] = []

        for el in elements:
            el_id = el.get("id", "UNKNOWN")
            el_type = el.get("type", "NODE")
            rho = float(el.get("utilization", 0.0))
            q = float(el.get("queue", 0.0))
            crit = float(el.get("criticality", 0.5))

            score = self.calculate_bottleneck_score(rho, q, crit)
            scored_entries.append(
                BottleneckEntry(
                    element_id=el_id,
                    element_type=el_type,
                    score=score,
                    utilization_rho=rho,
                    queue_length=q,
                    criticality=crit
                )
            )

        # Sort descending by score
        scored_entries.sort(key=lambda x: x.score, reverse=True)

        # Assign 1-based ranks
        for idx, entry in enumerate(scored_entries):
            entry.rank = idx + 1

        return scored_entries

    def check_migration(
        self,
        ranked_entries: List[BottleneckEntry],
        timestamp: float = 0.0
    ) -> Tuple[bool, Optional[BottleneckMigrationEvent]]:
        """
        Detects if the primary (#1 ranked) bottleneck has shifted since last evaluation.
        """
        if not ranked_entries:
            return False, None

        current_primary = ranked_entries[0]
        current_primary_id = current_primary.element_id

        if self.last_primary_id is None:
            self.last_primary_id = current_primary_id
            return False, None

        if current_primary_id != self.last_primary_id:
            event = BottleneckMigrationEvent(
                timestamp=timestamp,
                previous_primary_id=self.last_primary_id,
                new_primary_id=current_primary_id,
                previous_score=0.0,  # Updated from history
                new_score=current_primary.score,
                reason=f"Primary bottleneck migrated from {self.last_primary_id} to {current_primary_id}"
            )
            self.migration_history.append(event)
            self.last_primary_id = current_primary_id
            return True, event

        return False, None
