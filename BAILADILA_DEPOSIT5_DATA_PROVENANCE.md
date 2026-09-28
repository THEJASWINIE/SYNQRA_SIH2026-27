# BAILADILA DEPOSIT-5 — DATA PROVENANCE

**Three chains. They are never merged.**

```
AUTHORITATIVE_PUBLIC              OPEN_DATA_OSM                SYNTHETIC_FOR_DEMO
        |                               |                              |
        v                               v                              |
DERIVED_FROM_AUTHORITATIVE      DERIVED_FROM_OSM                       |
        |                               |                              |
        +---------------+---------------+------------------------------+
                        |
                        v
              GEOSPATIAL RENDERING
        (each layer labelled with its own chain)
```

A feature never changes chain. An OSM road never becomes authoritative because it is drawn
next to a published extent, and synthetic geometry never becomes real because it is drawn
inside one.

---

## Chain 1 — AUTHORITATIVE / DERIVED_FROM_AUTHORITATIVE

| Feature | Provenance | Source |
|---|---|---|
| `DEP5-EXTENT` published lease coordinate extent | `DERIVED_FROM_AUTHORITATIVE` | MoEF&CC J-11015/261/2007-IA.II(M), 11/12/2024, nmdc.co.in |

`DERIVED_FROM_AUTHORITATIVE` rather than `AUTHORITATIVE_PUBLIC` because the *numbers* are
published but the *rectangle* is our construction from them. The document publishes four
bounds, not a shape.

Rendered as: **"PUBLISHED LEASE COORDINATE EXTENT — not a lease boundary"**.

## Chain 2 — OPEN_DATA_OSM / DERIVED_FROM_OSM

| Layer | State |
|---|---|
| `OSM_CONTEXT_ROADS` | **Declared, empty, not drawn** |

No OpenStreetMap extract has been imported. The layer is declared so its absence is visible
and carries the reason. Should OSM geometry be added later, `requiresOsmAttribution()`
returns true and the renderer emits `© OpenStreetMap contributors, ODbL` — enforced by test.

**OSM is never authoritative and never NMDC's.** `isAuthoritativeChain("OPEN_DATA_OSM")`
returns false, asserted in `geoSite.test.ts`.

## Chain 3 — SYNTHETIC_FOR_DEMO

| Layer | Features | Provenance |
|---|---|---|
| `SYNTHETIC_HAUL_ROADS` | 2 demonstration routes | `SYNTHETIC_FOR_DEMO` |
| `SYNTHETIC_JUNCTIONS` | 2 demonstration junctions | `SYNTHETIC_FOR_DEMO` |
| `SYNTHETIC_OPERATIONAL_ZONES` | loading / crusher / dump demonstration points | `SYNTHETIC_FOR_DEMO` |

**All invented.** Positioned as fractions of the published extent so they scale with the
real bounds rather than carrying invented absolute coordinates. Every feature's `source`
reads *"Invented for demonstration. Not NMDC infrastructure."* and every name contains the
word "demonstration" — both asserted by test.

NMDC's actual haul roads, faces, crusher and dumps are **not public and not modelled**.

## Position provenance — a separate axis

Geographic provenance answers *where did this shape come from*. Position provenance answers
*where did this vehicle's coordinate come from*. They are different questions.

| Mode | Provider | Result |
|---|---|---|
| LIVE | `PhysicalVehiclePositionProvider` | **UNAVAILABLE, always** |
| SIMULATION | `SimulatedVehiclePositionProvider` | coordinate marked `SIMULATED` |
| REPLAY | `ReplayVehiclePositionProvider` | recorded coordinate marked `REPLAY` |

There is no GNSS on this prototype. `position` and `heading` are in the ingestor's
`NEVER_FROM_HARDWARE` set. A coordinate is never derived from wheel RPM.

## Unavailable

| Item | Why |
|---|---|
| Lease polygon | Not published. KML shown to the EAC but not released |
| Datum | Not stated in the source → `ASSUMED_WGS84_UNVERIFIED` |
| Real haul roads / crusher / dumps | Not public |
| Live vehicle position | No positioning hardware |
| Deposit-14 / Kirandul extents | Could not be verified from a primary document |
