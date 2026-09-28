"""
Software-Only Synthetic GNSS Telemetry Verification & Demo Script.

Demonstrates:
1. Ingestion of synthetic GNSS-shaped telemetry for TRUCK_01 and TRUCK_02.
2. Verification of strict provenance isolation (origin=SOFTWARE_ONLY, is_simulated=True).
3. Verification of position validation & invalid coordinate rejection.
4. Position movement from A -> B.
5. Printing clear verdict distinguishing SOFTWARE PIPELINE from PHYSICAL HARDWARE.
"""

from __future__ import annotations

import sys
import os

workspace_root = os.path.dirname(os.path.abspath(__file__))
digital_twin_root = os.path.join(workspace_root, "SYNQRA_SIH2026-27-main")
backend_root = os.path.join(workspace_root, "SYNQRA_SIH2026-27-HMI", "backend")
tests_dir = os.path.join(workspace_root, "tests")
fixtures_dir = os.path.join(tests_dir, "fixtures")
for p in (workspace_root, digital_twin_root, backend_root, tests_dir, fixtures_dir):
    if p not in sys.path:
        sys.path.insert(0, p)

from telemetry_ingest import TelemetryIngestor, Transport
from twin.twin_state_store import TwinStateStore
from twin_projection import build_vehicle_projection, build_twin_snapshot
from synthetic_gnss import inject_synthetic_gnss_vehicle, SYNTHETIC_TEST_COORDINATES


def run_verification():
    print("==================================================")
    print("SOFTWARE-ONLY SYNTHETIC GNSS HARNESS VERIFICATION")
    print("==================================================\n")

    store = TwinStateStore()
    ingestor = TelemetryIngestor(store)

    # 1. Inject synthetic GNSS for TRUCK_01 and TRUCK_02
    print("[STEP 1] Injecting synthetic GNSS telemetry for TRUCK_01 and TRUCK_02...")
    res1 = inject_synthetic_gnss_vehicle(ingestor, "TRUCK_01", sequence=1)
    res2 = inject_synthetic_gnss_vehicle(ingestor, "TRUCK_02", sequence=1)

    if not (res1 and res2):
        print("FAIL: Ingestion rejected valid synthetic telemetry records.")
        sys.exit(1)

    print("  -> TRUCK_01 injected:", SYNTHETIC_TEST_COORDINATES["TRUCK_01"])
    print("  -> TRUCK_02 injected:", SYNTHETIC_TEST_COORDINATES["TRUCK_02"])
    print("  -> Status: ACCEPTED\n")

    # 2. Inspect Twin State Store & Projection
    print("[STEP 2] Inspecting Twin State Store & Projection...")
    proj1 = build_vehicle_projection(store, "TRUCK_01")
    proj2 = build_vehicle_projection(store, "TRUCK_02")

    gnss1 = proj1["dynamic"]["position_gnss"]
    gnss2 = proj2["dynamic"]["position_gnss"]

    print("  TRUCK_01 Projection:", gnss1["value"])
    print("  TRUCK_01 Origin:    ", gnss1["origin"])
    print("  TRUCK_02 Projection:", gnss2["value"])
    print("  TRUCK_02 Origin:    ", gnss2["origin"])

    assert gnss1["value"]["origin"] == "SOFTWARE_ONLY"
    assert gnss2["value"]["origin"] == "SOFTWARE_ONLY"
    assert gnss1["origin"] == "SIMULATION"
    assert gnss2["origin"] == "SIMULATION"
    print("  -> Provenance Isolation Verified: NOT HARDWARE / NOT PHYSICAL\n")

    # 3. Test Invalid Coordinate Rejection (Rule 9)
    print("[STEP 3] Testing Invalid Coordinate Rejection (latitude = 91.0)...")
    res_bad = inject_synthetic_gnss_vehicle(ingestor, "TRUCK_01", latitude=91.0, sequence=2)
    current_pos = store.get_vehicle_field("TRUCK_01", "position_gnss").value
    print("  -> Out-of-bounds latitude (91.0) was safely rejected.")
    print("  -> Twin position retained previous valid fix:", current_pos["latitude"], current_pos["longitude"])
    assert current_pos["latitude"] == 18.67812
    print("  -> Rule 9 Compliance Verified\n")

    # 4. Position Movement (A -> B)
    print("[STEP 4] Testing Position Movement (A -> B)...")
    inject_synthetic_gnss_vehicle(ingestor, "TRUCK_01", latitude=18.67950, longitude=81.19050, sequence=3)
    updated_pos = store.get_vehicle_field("TRUCK_01", "position_gnss").value
    print("  -> TRUCK_01 updated position B:", updated_pos["latitude"], updated_pos["longitude"])
    assert updated_pos["latitude"] == 18.67950
    print("  -> Movement Verified\n")

    # 5. Summary Report Output
    print("==================================================")
    print("VERDICT & STATUS REPORT")
    print("==================================================")
    print("IMPLEMENTATION STATUS:             PASS")
    print("SOFTWARE POSITIONING PIPELINE:     VERIFIED")
    print("SYNTHETIC GNSS TEST:               VERIFIED")
    print("TRUCK_01 SYNTHETIC MARKER:         VERIFIED (SOFTWARE TEST · SYNTHETIC GNSS)")
    print("TRUCK_02 SYNTHETIC MARKER:         VERIFIED (SOFTWARE TEST · SYNTHETIC GNSS)")
    print("LIVE CURRENT HARDWARE RESULT:      POSITION UNAVAILABLE")
    print("PROVENANCE:                        SOFTWARE_ONLY_SYNTHETIC")
    print("PHYSICAL GNSS HARDWARE:            NOT PRESENT / NOT VERIFIED")
    print("PHYSICAL E2E:                      NOT VERIFIED")
    print("==================================================")


if __name__ == "__main__":
    run_verification()
