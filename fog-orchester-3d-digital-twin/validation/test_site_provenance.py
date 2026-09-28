"""
FOG-ORCHESTRATOR 2.0 — Site Provenance & Geospatial Truth Validation Suite
==============================================================================
Validates the 12 rigorous criteria for scientific honesty, traceability,
and geospatial integrity for Bailadila Iron Ore Mine, Deposit-5, Bacheli.

Outputs:
  SITE PROVENANCE AUDIT: PASS
or
  SITE PROVENANCE AUDIT: NEEDS CORRECTION
"""

import os
import sys
import yaml
import pytest


def run_site_provenance_audit() -> bool:
    """Audits site provenance metadata against the 12 authoritative criteria."""
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    meta_path = os.path.join(base_dir, "config", "site_metadata.yaml")

    if not os.path.isfile(meta_path):
        print(f"[-] Missing metadata file: {meta_path}")
        print("SITE PROVENANCE AUDIT: NEEDS CORRECTION")
        return False

    with open(meta_path, "r", encoding="utf-8") as f:
        meta = yaml.safe_load(f) or {}

    checks = []

    # 1. SITE_NAME exists
    site_name = meta.get("site", {}).get("name")
    c1 = (site_name == "Bailadila Iron Ore Mine, Deposit-5, Bacheli")
    checks.append(("1. Authoritative SITE_NAME exists", c1))

    # 2. LEASE_EXTENT_HA = 540.05
    lease_ha = meta.get("lease", {}).get("extent_ha")
    c2 = (lease_ha == 540.05)
    checks.append(("2. LEASE_EXTENT_HA = 540.05", c2))

    # 3. GEOMETRY_TYPE = BOUNDING_EXTENT
    geom_type = meta.get("lease", {}).get("geometry_type")
    c3 = (geom_type == "BOUNDING_EXTENT")
    checks.append(("3. GEOMETRY_TYPE = BOUNDING_EXTENT", c3))

    # 4. No lease polygon is claimed
    poly_avail = meta.get("lease", {}).get("boundary_polygon_available", True)
    poly_fab_allowed = meta.get("integrity", {}).get("lease_polygon_fabrication_allowed", True)
    c4 = (poly_avail is False and poly_fab_allowed is False)
    checks.append(("4. No lease polygon claimed / fabricated", c4))

    # 5. CRS source is marked UNSTATED_BY_SOURCE
    source_crs = meta.get("crs", {}).get("source_crs")
    c5 = (source_crs == "UNSTATED_BY_SOURCE")
    checks.append(("5. Source CRS marked UNSTATED_BY_SOURCE", c5))

    # 6. Rendering WGS84 is marked ASSUMED_WGS84_UNVERIFIED
    rendering_crs_status = meta.get("crs", {}).get("rendering_crs_status")
    c6 = (rendering_crs_status == "ASSUMED_WGS84_UNVERIFIED")
    checks.append(("6. Rendering WGS84 marked ASSUMED_WGS84_UNVERIFIED", c6))

    # 7. OSM geometry is explicitly classified
    prov = meta.get("provenance", {})
    c7 = (prov.get("osm_geometry") == "OPEN_DATA_OSM" and prov.get("osm_derived_geometry") == "DERIVED_FROM_OSM")
    checks.append(("7. OSM geometry classified OPEN_DATA_OSM / DERIVED_FROM_OSM", c7))

    # 8. Mine-specific synthetic geometry is explicitly classified
    c8 = (
        prov.get("mine_specific_geometry") == "SYNTHETIC_FOR_DEMO"
        and prov.get("haul_roads") == "SYNTHETIC_FOR_DEMO"
        and prov.get("switchbacks") == "SYNTHETIC_FOR_DEMO"
        and prov.get("terrain") == "SYNTHETIC_FOR_DEMO"
    )
    checks.append(("8. Mine geometry classified SYNTHETIC_FOR_DEMO", c8))

    # 9. Real vehicle positions are marked UNAVAILABLE
    real_pos = meta.get("telemetry", {}).get("real_physical_vehicle_positions")
    c9 = (real_pos == "UNAVAILABLE")
    checks.append(("9. Real physical vehicle positions marked UNAVAILABLE", c9))

    # 10. NMDC live operational data is not claimed
    live_claimed = meta.get("telemetry", {}).get("nmdc_live_operational_data")
    telemetry_conn = meta.get("telemetry", {}).get("live_nmdc_telemetry")
    c10 = (live_claimed == "NOT_CLAIMED" and telemetry_conn in ["UNAVAILABLE", "NOT_CONNECTED"])
    checks.append(("10. NMDC live operational data NOT_CLAIMED", c10))

    # 11. Simulated vehicles are clearly labelled as simulated
    sim_pos = meta.get("telemetry", {}).get("simulated_vehicle_positions")
    c11 = (sim_pos == "AVAILABLE")
    checks.append(("11. Simulated vehicle positions marked AVAILABLE", c11))

    # 12. Source information exists for verified facts
    source_info = meta.get("sources", {}).get("primary", {})
    org = source_info.get("organization")
    doc_type = source_info.get("document_type")
    domain = source_info.get("hosting_domain")
    c12 = (org == "MoEF&CC" and doc_type == "Environmental Clearance" and domain == "nmdc.co.in")
    checks.append(("12. Source traceability exists (MoEF&CC / nmdc.co.in)", c12))

    # Report results
    all_passed = True
    print("\n==================================================================")
    print("      FOG-ORCHESTRATOR 2.0 -- SITE PROVENANCE AUDIT CHECK         ")
    print("==================================================================")
    for name, passed in checks:
        status_str = "PASS [OK]" if passed else "FAIL [X]"
        print(f"  {status_str} {name}")
        if not passed:
            all_passed = False

    print("------------------------------------------------------------------")
    if all_passed:
        print("RESULT: SITE PROVENANCE AUDIT: PASS")
    else:
        print("RESULT: SITE PROVENANCE AUDIT: NEEDS CORRECTION")
    print("==================================================================\n")

    return all_passed


def test_site_provenance_audit():
    """Pytest hook for automated regression test suite."""
    assert run_site_provenance_audit() is True, "SITE PROVENANCE AUDIT: NEEDS CORRECTION"


if __name__ == "__main__":
    success = run_site_provenance_audit()
    sys.exit(0 if success else 1)
