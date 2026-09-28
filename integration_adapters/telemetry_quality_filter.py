"""
FOG-ORCHESTRATOR 2.0 — Telemetry Quality & Data Trust Filter (Blocker 7 Resolution)

Evaluates incoming telemetry quality (LIVE, DELAYED, STALE, OFFLINE, RECOVERING, INVALID),
prevents corrupted or stale telemetry from polluting Digital Twin state, and exposes
packet loss & sequence integrity metrics.
"""

import time
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger("TelemetryQualityFilter")

class TelemetryQualityFilter:
    """Evaluates telemetry data trust, age, packet loss, and state transition validity."""

    def __init__(self, stale_threshold_s: float = 3.0, offline_threshold_s: float = 10.0):
        self.stale_threshold_s = stale_threshold_s
        self.offline_threshold_s = offline_threshold_s
        self.vehicle_state_history: Dict[str, Dict[str, Any]] = {}

    def filter_telemetry(self, telemetry: Dict[str, Any]) -> Dict[str, Any]:
        """
        Filters incoming telemetry frame and appends data_quality, age_ms,
        packet_loss_estimate, and sequence_integrity.
        """
        now = time.time()
        if not telemetry or not isinstance(telemetry, dict) or "vehicle_id" not in telemetry:
            return {
                "data_quality": "INVALID",
                "should_update_twin": False,
                "age_ms": 0.0,
                "packet_loss_estimate": 1.0,
                "sequence_integrity": "CORRUPTED"
            }

        vid = telemetry["vehicle_id"]
        source_ts = telemetry.get("source_timestamp", telemetry.get("timestamp", now))
        seq_num = telemetry.get("sequence_number", 0)

        age_s = max(0.0, now - source_ts)
        age_ms = round(age_s * 1000.0, 1)

        history = self.vehicle_state_history.setdefault(vid, {
            "last_seen": now,
            "last_seq": 0,
            "received_count": 0,
            "dropped_count": 0,
            "prev_quality": "LIVE",
            "recovery_counter": 0
        })

        # Calculate packet loss estimate from sequence gap
        prev_seq = history["last_seq"]
        if prev_seq > 0 and seq_num > prev_seq + 1:
            dropped = (seq_num - prev_seq - 1)
            history["dropped_count"] += dropped
        history["received_count"] += 1
        history["last_seq"] = max(history["last_seq"], seq_num)

        total_expected = history["received_count"] + history["dropped_count"]
        loss_est = round(history["dropped_count"] / total_expected, 3) if total_expected > 0 else 0.0

        # Evaluate quality state
        prev_q = history["prev_quality"]
        if age_s > self.offline_threshold_s:
            quality = "OFFLINE"
            history["recovery_counter"] = 0
        elif age_s > self.stale_threshold_s:
            quality = "STALE"
            history["recovery_counter"] = 0
        elif prev_q == "OFFLINE" or prev_q == "STALE":
            # Initiate recovery phase
            cnt = history.get("recovery_counter", 0) + 1
            history["recovery_counter"] = cnt
            if cnt >= 2:
                quality = "LIVE"
            else:
                quality = "RECOVERING"
        elif age_s > 1.0:
            quality = "DELAYED"
        else:
            quality = "LIVE"

        history["prev_quality"] = quality
        history["last_seen"] = now

        should_update = quality in ["LIVE", "DELAYED", "RECOVERING"]

        filtered = dict(telemetry)
        filtered.update({
            "data_quality": quality,
            "should_update_twin": should_update,
            "age_ms": age_ms,
            "packet_loss_estimate": loss_est,
            "sequence_integrity": "OK" if not telemetry.get("is_out_of_order") else "OUT_OF_ORDER"
        })
        return filtered
