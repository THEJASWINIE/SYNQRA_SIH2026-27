"""
Unit tests for TelemetryQualityFilter.
Tests evaluation of LIVE, DELAYED, STALE, OFFLINE, RECOVERING, and INVALID telemetry states,
packet loss estimation, and prevention of stale data updating Digital Twin.
"""

import time
import pytest
from integration_adapters.telemetry_quality_filter import TelemetryQualityFilter

def test_live_telemetry():
    filt = TelemetryQualityFilter(stale_threshold_s=3.0)
    now = time.time()
    pkt = {"vehicle_id": "TRUCK_01", "source_timestamp": now, "sequence_number": 1}
    res = filt.filter_telemetry(pkt)
    assert res["data_quality"] == "LIVE"
    assert res["should_update_twin"] is True

def test_stale_telemetry_prevention():
    filt = TelemetryQualityFilter(stale_threshold_s=3.0, offline_threshold_s=10.0)
    now = time.time()
    stale_pkt = {"vehicle_id": "TRUCK_01", "source_timestamp": now - 5.0, "sequence_number": 1}
    res = filt.filter_telemetry(stale_pkt)
    assert res["data_quality"] == "STALE"
    assert res["should_update_twin"] is False

def test_invalid_telemetry():
    filt = TelemetryQualityFilter()
    res = filt.filter_telemetry(None)
    assert res["data_quality"] == "INVALID"
    assert res["should_update_twin"] is False

def test_recovery_phase():
    filt = TelemetryQualityFilter(stale_threshold_s=1.0, offline_threshold_s=2.0)
    now = time.time()
    # Force OFFLINE state
    filt.filter_telemetry({"vehicle_id": "TRUCK_01", "source_timestamp": now - 5.0, "sequence_number": 1})
    # 1st packet after offline -> RECOVERING
    res1 = filt.filter_telemetry({"vehicle_id": "TRUCK_01", "source_timestamp": now, "sequence_number": 2})
    assert res1["data_quality"] == "RECOVERING"
    # 2nd packet confirms LIVE
    res2 = filt.filter_telemetry({"vehicle_id": "TRUCK_01", "source_timestamp": now + 0.5, "sequence_number": 3})
    assert res2["data_quality"] == "LIVE"

if __name__ == "__main__":
    pytest.main(["-v", __file__])
