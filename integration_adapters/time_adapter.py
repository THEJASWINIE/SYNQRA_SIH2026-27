"""
FOG-ORCHESTRATOR 2.0 — Time Synchronization Adapter (Blocker 5 Resolution)

Establishes host/backend clock as integration timekeeper authority.
Tracks sequence continuity, out-of-order packets, duplicates, stale telemetry age,
and recommendation expiration.
"""

import time
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger("TimeAdapter")

class TimeAdapter:
    """Manages integration timestamps, sequence tracking, and expiration evaluation."""

    def __init__(self, max_telemetry_age_s: float = 3.0, max_recommendation_age_s: float = 5.0):
        self.max_telemetry_age_s = max_telemetry_age_s
        self.max_recommendation_age_s = max_recommendation_age_s
        self._last_sequence_map: Dict[str, int] = {}
        self._seen_sequence_history: Dict[str, set] = {}

    def process_telemetry(self, raw_telemetry: Dict[str, Any]) -> Dict[str, Any]:
        """
        Attaches integration_timestamp, tracks sequence continuity,
        detects out-of-order & duplicate packets, and evaluates stale status.
        """
        now = time.time()
        vehicle_id = raw_telemetry.get("vehicle_id", "UNKNOWN")
        seq_num = raw_telemetry.get("sequence_number", 0)

        source_ts = raw_telemetry.get("timestamp", now)
        gateway_ts = raw_telemetry.get("gateway_timestamp", source_ts)

        # Sequence tracking & duplicate detection
        seen_set = self._seen_sequence_history.setdefault(vehicle_id, set())
        is_duplicate = seq_num in seen_set
        seen_set.add(seq_num)

        last_seq = self._last_sequence_map.get(vehicle_id, 0)
        is_out_of_order = (seq_num < last_seq) and not is_duplicate
        if seq_num > last_seq:
            self._last_sequence_map[vehicle_id] = seq_num

        age_s = now - source_ts
        is_stale = age_s > self.max_telemetry_age_s
        is_future = source_ts > (now + 1.0)

        adapted = dict(raw_telemetry)
        adapted.update({
            "vehicle_id": vehicle_id,
            "sequence_number": seq_num,
            "source_timestamp": source_ts,
            "gateway_timestamp": gateway_ts,
            "integration_timestamp": now,
            "telemetry_age_seconds": round(age_s, 3),
            "is_duplicate": is_duplicate,
            "is_out_of_order": is_out_of_order,
            "is_stale": is_stale,
            "is_future_timestamp": is_future
        })
        return adapted

    def is_recommendation_expired(self, recommendation_timestamp: float) -> bool:
        """Evaluates whether a Digital Twin advisory recommendation has expired."""
        if recommendation_timestamp is None:
            return True
        now = time.time()
        age = now - recommendation_timestamp
        return age > self.max_recommendation_age_s or recommendation_timestamp > (now + 1.0)
