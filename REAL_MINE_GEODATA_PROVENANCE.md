# REAL MINE GEODATA PROVENANCE — BAILADILA DEPOSIT-5

**Target Site:** NMDC Bailadila Iron Ore Mine, Bacheli Complex, Deposit-5, South Bastar Dantewada, Chhattisgarh  
**Date:** 2026-09-08  
**Scope:** Geospatial Digital Twin 2D Representation in FOG-ORCHESTRATOR  

---

## 1. TARGET SITE INFORMATION

- **Site:** NMDC Limited — Bailadila Iron Ore Mine (Deposit-5)
- **Location:** Bacheli, District South Bastar Dantewada, Chhattisgarh, India
- **Lease Area:** 540.05 ha (all forest land)
- **Toposheet:** Survey of India Toposheet No. E44J2
- **Seismic Zone:** Seismic Zone-II

---

## 2. LEVEL 1 & 2: AUTHORITATIVE & DERIVED PUBLIC DATA

### Published Source
- **Document:** MoEF&CC File No. `J-11015/261/2007-IA.II(M)`, dated 11/12/2024
- **Host Domain:** `nmdc.co.in` (NMDC's official domain)
- **Classification:** `AUTHORITATIVE_PUBLIC` / `DERIVED_FROM_AUTHORITATIVE`

### Published Coordinates (Verbatim)
- **Latitude:** `18°40'00.54"` to `18°41'50.38" N`
- **Longitude:** `81°10'41.83"` to `81°12'31.89" E`

### Bounding Extent Justification (NOT a Lease Boundary)
- **Geometry Type:** `BOUNDING_EXTENT` (4 bounding values: North, South, East, West).
- **Coordinate List:** Empty (`coordinates: []`).
- **Reasoning:** Four published boundary coordinates define a bounding rectangle, NOT a surveyed lease polygon. The bounding rectangle covers approx. $10.95\text{ km}^2$, while the official lease is $540.05\text{ ha} = 5.40\text{ km}^2$ ($\sim 49\%$ of the bounding box). Converting the extent into a solid polygon and calling it a lease boundary would be an invented shape.
- **Display Label:** `"PUBLISHED LEASE COORDINATE EXTENT — not a lease boundary"`

### CRS / Datum Uncertainty
- **Datum:** Not stated in the MoEF&CC document (Survey of India sheets use Everest 1830 and WGS84 realisations).
- **Classification:** Recorded as `ASSUMED_WGS84_UNVERIFIED`. Never presented as an authoritative datum.

---

## 3. LEVEL 3 & 4: OPENSTRERTMAP DATA (OPEN_DATA_OSM)

### Bundled Offline Extract
- **File:** `src/data/osm/bailadila-deposit5.osm.json`
- **Extraction Bounding Box:** `south: 18.6668, west: 81.1783, north: 18.6974, east: 81.2089` (Deposit-5 extent)
- **License & Attribution:** Open Database License (ODbL) 1.0 — `© OpenStreetMap contributors, ODbL`
- **Network Dependency:** ZERO runtime network calls (bundled locally for offline execution).

### OSM Layer Classification & Policy

| Layer ID | OSM Features | Default Visibility | Provenance | Policy Note |
|---|---|---|---|---|
| `OSM_SITE_AREAS` | `landuse=quarry` (Way 119388112) | **ON** (`true`) | `OPEN_DATA_OSM` | Mapped open-pit area from OSM. Not surveyed NMDC pit boundary. |
| `OSM_SITE_ROADS` | Non-residential ways (`highway=unclassified/track`) | **ON** (`true`) | `OPEN_DATA_OSM` | Site access roads. Not verified NMDC haul roads. |
| `OSM_TOWNSHIP_ROADS` | 36 residential streets (`highway=residential`) | **OFF** (`false`) | `OPEN_DATA_OSM` | Bacheli township streets. OFF by default so residential streets do not read as haul roads. |

*OSM geometry is never classified as `AUTHORITATIVE_PUBLIC` or attributed to NMDC ownership.*

---

## 4. LEVEL 6: SYNTHETIC DEMONSTRATION GEOMETRY (SYNTHETIC_FOR_DEMO)

- **Layers:** `SYNTHETIC_PIT`, `SYNTHETIC_BENCHES`, `SYNTHETIC_HAUL_ROADS`, `SYNTHETIC_JUNCTIONS`, `SYNTHETIC_LOADING_FACES`, `SYNTHETIC_PROCESSING`, `SYNTHETIC_DUMPS`, `SYNTHETIC_SUPPORT`, `SYNTHETIC_OPERATIONAL_ZONES`
- **Default Visibility:** **OFF** (`false`). Hidden by default so real OSM & extent data take precedence.
- **Provenance & Source:** Every feature carries `provenance: "SYNTHETIC_FOR_DEMO"` and `source: "Invented for demonstration. SYNTHETIC — NOT NMDC INFRASTRUCTURE."`
- **Names:** Every synthetic feature name contains the word `"demonstration"`.

---

## 5. LEVEL 7: UNAVAILABLE FEATURES & ISOLATION

| Feature | Status | Reason |
|---|---|---|
| Lease Polygon | `UNAVAILABLE` | Not published in public document (KML presented to EAC was not released). |
| Real Mine Haul Roads / Pit Benches | `UNAVAILABLE` | Operational mine layout is not public. |
| LIVE Vehicle GPS Coordinates | `UNAVAILABLE` | Vehicle hardware has wheel encoders and IMU, but no GNSS receiver. Live positions evaluate strictly to `position = null` / `UNAVAILABLE`. |

---

## 6. NON-CLAIM DISCLAIMER

This system is a **2D geographic Digital Twin representation of the NMDC Bailadila Deposit-5 area grounded in publicly published NMDC/Government extent data and OpenStreetMap geographic data, with synthetic demonstration geometry explicitly isolated.** It makes NO claim of official NMDC Digital Twin authorization, surveyed lease boundary ownership, or real-time physical vehicle GPS positioning.
