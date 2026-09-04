"""
Unit tests for VehicleIDMapper adapter.
Tests valid mapping, invalid ID rejection, duplicate ID detection, reverse mapping,
and no cross-vehicle contamination.
"""

import pytest
from integration_adapters.vehicle_id_mapper import VehicleIDMapper

def test_valid_id_mapping():
    mapper = VehicleIDMapper()
    assert mapper.to_twin_id("TRUCK_01") == "vehicle_1"
    assert mapper.to_twin_id("TRUCK_02") == "vehicle_2"

def test_reverse_mapping():
    mapper = VehicleIDMapper()
    assert mapper.to_physical_id("vehicle_1") == "TRUCK_01"
    assert mapper.to_physical_id("vehicle_2") == "TRUCK_02"

def test_invalid_id_rejection():
    mapper = VehicleIDMapper()
    assert mapper.to_twin_id("TRUCK_99") is None
    assert mapper.to_physical_id("vehicle_99") is None
    assert mapper.to_twin_id(None) is None
    assert mapper.to_physical_id("") is None

def test_duplicate_id_detection():
    with pytest.raises(ValueError):
        VehicleIDMapper({"TRUCK_01": "vehicle_1", "TRUCK_02": "vehicle_1"})

def test_no_cross_vehicle_contamination():
    mapper = VehicleIDMapper()
    assert mapper.to_twin_id("TRUCK_01") != mapper.to_twin_id("TRUCK_02")
    assert mapper.to_physical_id("vehicle_1") != mapper.to_physical_id("vehicle_2")

if __name__ == "__main__":
    pytest.main(["-v", __file__])
