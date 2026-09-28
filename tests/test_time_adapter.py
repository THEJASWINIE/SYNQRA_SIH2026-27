"""
Unit tests for TimeAdapter.
Tests integration timestamp authority, out-of-order packet detection, duplicate detection,
stale telemetry detection, and recommendation expiration.
"""

import time
import pytest
from integration_adapters.time_adapter import TimeAdapter

def test_normal_telemetry_processing():
    adapter = TimeAdapter(max_telemetry_age_s=3.0)
    now = time.time()
    pkt = {"vehicle_id": "TRUCK_01", "sequence_number": 1, "timestamp": now}
    res = adapter.process_telemetry(pkt)
    assert res["integration_timestamp"] >= now
    assert res["is_duplicate"] is False
    assert res["is_out_of_order"] is False
    assert res["is_stale"] is False

def test_duplicate_telemetry_detection():
    adapter = TimeAdapter()
    now = time.time()
    pkt = {"vehicle_id": "TRUCK_01", "sequence_number": 10, "timestamp": now}
    adapter.process_telemetry(pkt)
    res_dup = adapter.process_telemetry(pkt)
    assert res_dup["is_duplicate"] is True

def test_out_of_order_telemetry_detection():
    adapter = TimeAdapter()
    now = time.time()
    pkt1 = {"vehicle_id": "TRUCK_01", "sequence_number": 5, "timestamp": now}
    pkt2 = {"vehicle_id": "TRUCK_01", "sequence_number": 3, "timestamp": now}
    adapter.process_telemetry(pkt1)
    res_ooo = adapter.process_telemetry(pkt2)
    assert res_ooo["is_out_of_order"] is True

def test_stale_telemetry_detection():
    adapter = TimeAdapter(max_telemetry_age_s=3.0)
    now = time.time()
    old_pkt = {"vehicle_id": "TRUCK_01", "sequence_number": 1, "timestamp": now - 5.0}
    res = adapter.process_telemetry(old_pkt)
    assert res["is_stale"] is True

def test_recommendation_expiration():
    adapter = TimeAdapter(max_recommendation_age_s=5.0)
    now = time.time()
    assert adapter.is_recommendation_expired(now - 1.0) is False
    assert adapter.is_recommendation_expired(now - 10.0) is True

if __name__ == "__main__":
    pytest.main(["-v", __file__])
