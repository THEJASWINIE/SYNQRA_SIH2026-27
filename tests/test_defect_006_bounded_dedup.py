"""
D006 — Bounded deduplication stores regression tests.

Verifies:
1. Dedup tracker stays bounded after many packets.
2. Duplicate detection works for recent sequences.
3. Old sequences that fall out of the dedup window are STILL rejected as
   out-of-order by last_accepted_sequence (NOT re-accepted as new).
4. last_accepted_sequence stays accurate.
"""

import pytest

from telemetry_ingest import (
    BoundedSequenceTracker,
    MAX_DEDUP_HISTORY,
    REJECT_DUPLICATE,
    REJECT_OUT_OF_ORDER,
    TelemetryIngestor,
    Transport,
)
from twin.twin_state_store import TwinMode, TwinStateStore


# ---------------------------------------------------------------------------
# BoundedSequenceTracker unit tests
# ---------------------------------------------------------------------------

class TestBoundedSequenceTracker:

    def test_membership_works(self):
        t = BoundedSequenceTracker(maxlen=5)
        t.add(1)
        t.add(2)
        t.add(3)
        assert 1 in t
        assert 2 in t
        assert 3 in t
        assert 4 not in t

    def test_eviction_at_capacity(self):
        t = BoundedSequenceTracker(maxlen=5)
        for i in range(10):
            t.add(i)
        assert len(t) == 5
        # Only the last 5 should be tracked
        for i in range(5):
            assert i not in t, f"seq {i} should have been evicted"
        for i in range(5, 10):
            assert i in t

    def test_len_stays_bounded(self):
        t = BoundedSequenceTracker(maxlen=100)
        for i in range(500):
            t.add(i)
        assert len(t) == 100


# ---------------------------------------------------------------------------
# Ingestor-level bounded dedup
# ---------------------------------------------------------------------------

def _hw(vehicle_id="TRUCK_01", sequence=1, **over):
    rec = dict(
        vehicle_id=vehicle_id,
        sequence_number=sequence,
        rpm=240.0,
        speed=2.5,
        acceleration={"x": 0.12, "y": -0.05, "z": 9.81},
        gyroscope={"x": 0.02, "y": 0.01, "z": -0.03},
        communication={"rssi": -65, "snr": 9.2},
        communication_state="HEALTHY",
        data_quality="LIVE",
    )
    rec.update(over)
    return rec


class TestIngestorBoundedDedup:

    @pytest.fixture
    def setup(self):
        store = TwinStateStore(mode=TwinMode.HYBRID, stale_after_s=3.0)
        ingestor = TelemetryIngestor(store)
        return ingestor, store

    def test_dedup_memory_stays_bounded(self, setup):
        """After >1000 packets, the dedup tracker size stays at MAX_DEDUP_HISTORY."""
        ingestor, store = setup
        for seq in range(1, 1500):
            result = ingestor.ingest_parsed_record(
                _hw(sequence=seq), Transport.V2V
            )
            assert result.accepted, f"seq={seq} should have been accepted"

        tracker = ingestor._seen_sequences.get("TRUCK_01")
        assert tracker is not None
        assert len(tracker) == MAX_DEDUP_HISTORY

    def test_duplicate_detection_for_recent_sequences(self, setup):
        """Duplicate detection works for sequences within the bounded window."""
        ingestor, store = setup
        # Accept sequence 100
        assert ingestor.ingest_parsed_record(_hw(sequence=100), Transport.V2V).accepted

        # Replay sequence 100 — should be DUPLICATE
        result = ingestor.ingest_parsed_record(_hw(sequence=100), Transport.V2V)
        assert not result.accepted
        assert result.reason == REJECT_DUPLICATE

    def test_old_sequence_outside_window_still_rejected_as_ooo(self, setup):
        """An old sequence that falls out of the dedup window is STILL out-of-order.

        This is the critical D006 invariant: the bounded deque ONLY caps
        duplicate history; it NEVER changes ordering semantics.
        """
        ingestor, store = setup
        # Accept sequences 1..5
        for seq in range(1, 6):
            assert ingestor.ingest_parsed_record(_hw(sequence=seq), Transport.V2V).accepted

        # Now accept 1000 more to push seq 1-5 out of the dedup window
        for seq in range(6, 1100):
            assert ingestor.ingest_parsed_record(_hw(sequence=seq), Transport.V2V).accepted

        # Replay sequence 3 — should be OUT_OF_ORDER (not accepted as new!)
        result = ingestor.ingest_parsed_record(_hw(sequence=3), Transport.V2V)
        assert not result.accepted
        assert result.reason == REJECT_OUT_OF_ORDER, \
            "Old sequence that fell out of dedup window must still be rejected as OoO"

    def test_last_accepted_sequence_stays_accurate(self, setup):
        """last_accepted_sequence is always the highest accepted sequence."""
        ingestor, store = setup
        for seq in [10, 20, 30, 15, 25]:  # 15 and 25 are OoO
            ingestor.ingest_parsed_record(_hw(sequence=seq), Transport.V2V)

        assert ingestor._last_sequence["TRUCK_01"] == 30
