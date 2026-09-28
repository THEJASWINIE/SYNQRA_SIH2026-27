"""
Synthetic GNSS telemetry test fixture — SOFTWARE-ONLY positioning harness.

Provides reusable helpers for building and injecting synthetic GNSS telemetry
payloads through the production pipeline (telemetry_ingest -> TwinStateStore -> twin_projection).

PROVENANCE GUARANTEE (Rules 1-10):
  Every payload produced here explicitly sets:
    is_simulated = True
    origin = "SOFTWARE_ONLY_SYNTHETIC"
    position_source = "GNSS"
  No payload produced by this test harness is EVER marked as HARDWARE or PHYSICAL.
"""

from __future__ import annotations

import time
from typing import Any, Dict, Optional

# Standard Deposit-5 synthetic test coordinates
SYNTHETIC_TEST_COORDINATES = {
    "TRUCK_01": {"latitude": 18.67812, "longitude": 81.18912},
    "TRUCK_02": {"latitude": 18.68120, "longitude": 81.19310},
}


def build_synthetic_gnss_payload(
    vehicle_id: str,
    latitude: Optional[float] = None,
    longitude: Optional[float] = None,
    timestamp: Optional[float] = None,
    sequence: int = 1,
    status: str = "VALID",
    source_name: str = "GNSS",
) -> Dict[str, Any]:
    """
    Build one synthetic GNSS telemetry record.

    Explicitly carries is_simulated=True and provenance_source="SOFTWARE_ONLY_SYNTHETIC".
    """
    coords = SYNTHETIC_TEST_COORDINATES.get(vehicle_id, {"latitude": 18.67812, "longitude": 81.18912})
    if latitude is None:
        latitude = coords["latitude"]
    if longitude is None:
        longitude = coords["longitude"]

    now = timestamp if timestamp is not None else time.time()

    return {
        "vehicle_id": vehicle_id,
        "sequence_number": sequence,
        "source_timestamp": now,
        "provenance_source": "SOFTWARE_ONLY_SYNTHETIC",
        "is_simulated": True,
        "rpm": 120.0,
        "speed_mps": 1.5,
        "latitude": latitude,
        "longitude": longitude,
        "position_source": source_name,
        "position_status": status,
        "position_timestamp": now,
    }


def inject_synthetic_gnss_vehicle(
    ingestor: Any,
    vehicle_id: str,
    latitude: Optional[float] = None,
    longitude: Optional[float] = None,
    timestamp: Optional[float] = None,
    sequence: int = 1,
    status: str = "VALID",
):
    """
    Inject one synthetic GNSS telemetry record into the production TelemetryIngestor.

    Guarantees transport=Transport.EMULATOR and is_simulated=True so the packet
    is NEVER classified as physical hardware data.
    """
    from telemetry_ingest import Transport

    payload = build_synthetic_gnss_payload(
        vehicle_id=vehicle_id,
        latitude=latitude,
        longitude=longitude,
        timestamp=timestamp,
        sequence=sequence,
        status=status,
    )
    return ingestor.ingest_parsed_record(payload, transport=Transport.EMULATOR, is_simulated=True)
