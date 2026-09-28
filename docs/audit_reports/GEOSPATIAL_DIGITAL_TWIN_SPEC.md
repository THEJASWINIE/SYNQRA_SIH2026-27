# GEOSPATIAL DIGITAL TWIN — SPECIFICATION

**NMDC Bailadila geospatial Digital Twin prototype.** Not an official NMDC system.

## 1. Scope

Adds a geographically grounded 2D site model to the EXISTING Digital Twin. It does not
create a second Twin, does not own vehicle state, and does not duplicate telemetry, safety
or orchestration state. Vehicle identities come from the canonical `AppState.vehicles`.

## 2. Model

```
GeoSite
  siteId, siteName, district, state
  extent               SiteExtent  (DMS, as published)
  coordinateReference  ASSUMED_WGS84_UNVERIFIED
  extentProvenance     DERIVED_FROM_AUTHORITATIVE
  extentSource         document identifier
  leaseAreaHa, toposheet
  layers[]             MapLayer
                         id, name, provenance, features[], unavailableReason?
                         GeoFeature: id, name, geometryType, coordinates[],
                                     provenance, source, notes?
```

`geometryType` ∈ `BOUNDING_EXTENT | LINESTRING | POINT | POLYGON`. The site extent is
`BOUNDING_EXTENT` and carries an **empty** coordinate list — four published bounds are not
four surveyed corners. No feature in the model is a `POLYGON`; a test enforces this.

## 3. Coordinate system

| Stage | CRS |
|---|---|
| Source | DMS lat/lon, **datum not stated** |
| Canonical (stored) | DMS as published, converted by tested `dmsToDecimal` |
| Recorded as | `ASSUMED_WGS84_UNVERIFIED` |
| Rendering | local equirectangular about the extent centroid → SVG viewBox units |

**Why equirectangular, not a projection library:** over a ~3.4 km site at 18.7° N the error
against a proper transverse Mercator is sub-metre — far below what a prototype with no
surveyed geometry and no GNSS can claim to resolve. `proj4` would add weight without
accuracy. `projectToLocalMetres` / `unprojectFromLocalMetres` round-trip to 1e-9 degrees,
asserted by test. SVG y-inversion happens in exactly one place, `screenProjection`.

## 4. Layers

| Layer | Chain | State |
|---|---|---|
| `SITE_EXTENT` | authoritative | drawn |
| `OSM_CONTEXT_ROADS` | OSM | declared, empty, reason stated |
| `SYNTHETIC_HAUL_ROADS` | synthetic | drawn, dotted |
| `SYNTHETIC_JUNCTIONS` | synthetic | drawn |
| `SYNTHETIC_OPERATIONAL_ZONES` | synthetic | drawn |
| `VEHICLES` | position provider | drawn only where a position exists |

A declared-but-empty layer renders `UNAVAILABLE` with its reason. It is never silently
omitted, because an absent layer and a layer with nothing in it look identical otherwise.

## 5. Rendering

SVG, same architecture as `MineMap.tsx`. **No mapping library, no tiles, no imagery.**
`MineMap.tsx` is unmodified — it renders the abstract topology graph in topology units,
`GeoSiteMap.tsx` renders geographic coordinates, and the two coordinate systems are kept in
separate components so a projection error cannot hide.

The three chains are separable without colour: solid extent, dashed OSM, dotted synthetic,
and every layer's provenance is written out in the legend (NFR-008).

## 6. HMI integration

Mounted inside **S1 Operations**. No seventh primary screen. S1–S6 unchanged, all
additional screens still reachable.

## 7. Invariants

1. The extent is never a polygon and never called a boundary.
2. OSM is never authoritative and never attributed to NMDC.
3. Every synthetic feature is marked `SYNTHETIC_FOR_DEMO`.
4. LIVE never receives a coordinate.
5. Simulated positions are always marked `SIMULATED`.
6. Replay positions are always marked `REPLAY`, never promoted.
7. Missing position renders `POSITION UNAVAILABLE`, never a coordinate.

All seven are asserted by tests.
