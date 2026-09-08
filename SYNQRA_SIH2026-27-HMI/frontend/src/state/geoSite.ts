/**
 * Geospatial site model — NMDC Bailadila geospatial Digital Twin prototype.
 *
 * ==========================================================================
 *  THIS IS NOT AN OFFICIAL NMDC DIGITAL TWIN.
 *
 *  It is a prototype that renders ONE published, verifiable coordinate extent plus
 *  clearly-labelled synthetic demonstration geometry. No mine geometry is invented and
 *  presented as NMDC infrastructure.
 * ==========================================================================
 *
 * THE ONLY AUTHORITATIVE GEOGRAPHIC FACT IN THIS FILE
 *
 * MoEF&CC File No. J-11015/261/2007-IA.II(M), dated 11/12/2024, hosted on nmdc.co.in,
 * states verbatim:
 *
 *   "The mine lease area is located between Latitude: 18°40'00.54" to 18°41'50.38" N and
 *    Longitude: 81°10'41.83" to 81°12'31.89" E. The mine lease area falls under the
 *    Survey of India Toposheet No: E44J2 and falls in Seismic Zone-II."
 *
 * FOUR NUMBERS. That is a BOUNDING EXTENT, not a lease polygon. The document contains no
 * corner list, no pillar coordinates and no vertices - it was checked, and there are zero
 * DMS corner tokens in all 23 pages. A KML file was presented to the EAC but is not
 * included in the published document.
 *
 * So this module models an EXTENT and refuses to produce a polygon. Drawing a rectangle
 * through four bounds and calling it a lease boundary would be an invented shape: the real
 * lease is 540.05 ha inside a bounding box of roughly 10.9 km², so the rectangle is about
 * twice the area of the actual lease. It is labelled accordingly everywhere it appears.
 *
 * DATUM
 *
 * The source does NOT state a datum. Survey of India toposheets exist in both Everest 1830
 * and WGS84 realisations. This module therefore records `ASSUMED_WGS84_UNVERIFIED` and
 * never silently claims WGS84.
 *
 * Pure and framework-free, so it is testable without a DOM (M4D-C).
 */

// ---------------------------------------------------------------------------
// provenance — three chains that must never be merged
// ---------------------------------------------------------------------------

/**
 * Where a geographic feature came from.
 *
 * The three chains are deliberately separate:
 *
 *   AUTHORITATIVE_PUBLIC -> DERIVED_FROM_AUTHORITATIVE   government / NMDC published
 *   OPEN_DATA_OSM        -> DERIVED_FROM_OSM             OpenStreetMap, ODbL
 *   SYNTHETIC_FOR_DEMO                                    invented for demonstration
 *
 * OSM is open data, NOT authoritative mine geometry, and is never labelled as NMDC's.
 */
export type GeoProvenance =
  | "AUTHORITATIVE_PUBLIC"
  | "DERIVED_FROM_AUTHORITATIVE"
  | "OPEN_DATA_OSM"
  | "DERIVED_FROM_OSM"
  | "SYNTHETIC_FOR_DEMO"
  | "UNAVAILABLE";

/** Short badge text. Every feature shows one; colour is never the only signal. */
export const GEO_PROVENANCE_TEXT: Record<GeoProvenance, string> = {
  AUTHORITATIVE_PUBLIC: "AUTHORITATIVE (PUBLIC)",
  DERIVED_FROM_AUTHORITATIVE: "DERIVED FROM AUTHORITATIVE",
  OPEN_DATA_OSM: "OPENSTREETMAP (ODbL)",
  DERIVED_FROM_OSM: "DERIVED FROM OSM (ODbL)",
  SYNTHETIC_FOR_DEMO: "SYNTHETIC — DEMONSTRATION ONLY",
  UNAVAILABLE: "UNAVAILABLE",
};

/** True only for the government/NMDC chain. OSM and synthetic are never authoritative. */
export function isAuthoritativeChain(p: GeoProvenance): boolean {
  return p === "AUTHORITATIVE_PUBLIC" || p === "DERIVED_FROM_AUTHORITATIVE";
}

/** ODbL requires attribution wherever OSM-derived geometry is shown. */
export const OSM_ATTRIBUTION = "© OpenStreetMap contributors, ODbL";

// ---------------------------------------------------------------------------
// coordinates
// ---------------------------------------------------------------------------

/** A degrees/minutes/seconds value exactly as the source document printed it. */
export interface Dms {
  degrees: number;
  minutes: number;
  seconds: number;
  hemisphere: "N" | "S" | "E" | "W";
}

/**
 * DMS -> signed decimal degrees.
 *
 * The published values are stored as DMS, not as pre-computed decimals, so the numbers in
 * this repository are literally the numbers in the source document and the conversion is
 * testable rather than trusted.
 */
export function dmsToDecimal(dms: Dms): number {
  const magnitude = Math.abs(dms.degrees) + dms.minutes / 60 + dms.seconds / 3600;
  const negative = dms.hemisphere === "S" || dms.hemisphere === "W";
  return negative ? -magnitude : magnitude;
}

/** Format a DMS value back to the source notation, for display beside the map. */
export function formatDms(dms: Dms): string {
  const minutes = String(dms.minutes).padStart(2, "0");
  return `${dms.degrees}°${minutes}'${dms.seconds.toFixed(2)}"${dms.hemisphere}`;
}

/**
 * A rectangular coordinate extent.
 *
 * Named `SiteExtent`, never `SiteBoundary`: it bounds the lease, it is not the lease.
 */
export interface SiteExtent {
  north: Dms;
  south: Dms;
  east: Dms;
  west: Dms;
}

export interface DecimalExtent {
  north: number;
  south: number;
  east: number;
  west: number;
}

export function toDecimalExtent(extent: SiteExtent): DecimalExtent {
  return {
    north: dmsToDecimal(extent.north),
    south: dmsToDecimal(extent.south),
    east: dmsToDecimal(extent.east),
    west: dmsToDecimal(extent.west),
  };
}

/** A WGS84-style position. `LonLat`, in that order, to match GeoJSON convention. */
export interface LonLat {
  lon: number;
  lat: number;
}

// ---------------------------------------------------------------------------
// projection
// ---------------------------------------------------------------------------

/** Metres per degree of latitude. Spherical approximation; adequate at this scale. */
const M_PER_DEG_LAT = 111_320;

/**
 * Local equirectangular projection about the extent centroid.
 *
 * Chosen deliberately over a full projection library. Over a site of ~3.4 km at 18.7° N the
 * error of an equirectangular projection versus a proper transverse Mercator is well under
 * a metre - far below anything this prototype can claim to resolve, given it has no
 * surveyed geometry and no GNSS at all. Adding proj4 would be weight without accuracy.
 *
 * Returns metres east/north of the origin. Screen mapping happens separately, so the
 * projection itself is testable without any rendering concern.
 */
export function projectToLocalMetres(point: LonLat, origin: LonLat): { x: number; y: number } {
  const latScale = Math.cos((origin.lat * Math.PI) / 180);
  return {
    x: (point.lon - origin.lon) * M_PER_DEG_LAT * latScale,
    y: (point.lat - origin.lat) * M_PER_DEG_LAT,
  };
}

/** Inverse of `projectToLocalMetres`. Round-tripping is asserted in the tests. */
export function unprojectFromLocalMetres(
  metres: { x: number; y: number },
  origin: LonLat,
): LonLat {
  const latScale = Math.cos((origin.lat * Math.PI) / 180);
  return {
    lon: origin.lon + metres.x / (M_PER_DEG_LAT * latScale),
    lat: origin.lat + metres.y / M_PER_DEG_LAT,
  };
}

export function extentCentroid(extent: DecimalExtent): LonLat {
  return {
    lon: (extent.east + extent.west) / 2,
    lat: (extent.north + extent.south) / 2,
  };
}

/** Extent size in metres, for the scale bar and the area cross-check. */
export function extentSizeMetres(extent: DecimalExtent): { widthM: number; heightM: number } {
  const centroid = extentCentroid(extent);
  const sw = projectToLocalMetres({ lon: extent.west, lat: extent.south }, centroid);
  const ne = projectToLocalMetres({ lon: extent.east, lat: extent.north }, centroid);
  return { widthM: ne.x - sw.x, heightM: ne.y - sw.y };
}

/**
 * Screen projection: a lon/lat to SVG viewBox units.
 *
 * SVG y grows downward while latitude grows upward, so y is inverted here - the one place
 * that flip happens.
 */
export interface ScreenProjection {
  width: number;
  height: number;
  project: (point: LonLat) => { x: number; y: number };
}

export function screenProjection(
  extent: DecimalExtent,
  width: number,
  height: number,
): ScreenProjection {
  const lonSpan = extent.east - extent.west || 1;
  const latSpan = extent.north - extent.south || 1;
  return {
    width,
    height,
    project: (point) => ({
      x: ((point.lon - extent.west) / lonSpan) * width,
      y: height - ((point.lat - extent.south) / latSpan) * height,
    }),
  };
}

// ---------------------------------------------------------------------------
// features and layers
// ---------------------------------------------------------------------------

export type GeoGeometryType = "BOUNDING_EXTENT" | "LINESTRING" | "POINT" | "POLYGON";

export interface GeoFeature {
  id: string;
  name: string;
  geometryType: GeoGeometryType;
  /** Ordered positions. A BOUNDING_EXTENT carries none — it is described by the extent. */
  coordinates: LonLat[];
  provenance: GeoProvenance;
  /** Human-readable source identifier. Required for anything not synthetic. */
  source: string;
  notes?: string | undefined;
}

export type LayerId =
  | "SITE_EXTENT"
  | "OSM_CONTEXT_ROADS"
  | "SYNTHETIC_HAUL_ROADS"
  | "SYNTHETIC_JUNCTIONS"
  | "SYNTHETIC_OPERATIONAL_ZONES"
  | "VEHICLES";

export interface MapLayer {
  id: LayerId;
  name: string;
  provenance: GeoProvenance;
  features: GeoFeature[];
  /** Stated when a layer has no data, so absence is explained rather than blank. */
  unavailableReason?: string | undefined;
}

export interface GeoSite {
  siteId: string;
  siteName: string;
  /** Exactly as printed in the source document. */
  extent: SiteExtent;
  /** The datum the source did NOT state. */
  coordinateReference: "ASSUMED_WGS84_UNVERIFIED";
  extentProvenance: GeoProvenance;
  extentSource: string;
  leaseAreaHa: number;
  toposheet: string;
  district: string;
  state: string;
  layers: MapLayer[];
}

// ---------------------------------------------------------------------------
// the verified site
// ---------------------------------------------------------------------------

const SOURCE_EC =
  "MoEF&CC File No. J-11015/261/2007-IA.II(M) dated 11/12/2024 (hosted on nmdc.co.in)";

/**
 * The published extent, transcribed digit-for-digit from the source document.
 *
 * This is the ONLY geographic assertion in this prototype backed by an official document.
 */
export const DEPOSIT5_EXTENT: SiteExtent = {
  south: { degrees: 18, minutes: 40, seconds: 0.54, hemisphere: "N" },
  north: { degrees: 18, minutes: 41, seconds: 50.38, hemisphere: "N" },
  west: { degrees: 81, minutes: 10, seconds: 41.83, hemisphere: "E" },
  east: { degrees: 81, minutes: 12, seconds: 31.89, hemisphere: "E" },
};

/**
 * Synthetic demonstration geometry.
 *
 * INVENTED. Placed inside the published extent so the demonstration is spatially
 * plausible, and carrying `SYNTHETIC_FOR_DEMO` so nothing can mistake it for surveyed
 * infrastructure. NMDC's actual haul roads, faces, crusher and dumps are NOT public and
 * are NOT modelled here.
 */
function syntheticFeature(
  id: string,
  name: string,
  geometryType: GeoGeometryType,
  coordinates: LonLat[],
  notes: string,
): GeoFeature {
  return {
    id,
    name,
    geometryType,
    coordinates,
    provenance: "SYNTHETIC_FOR_DEMO",
    source: "Invented for demonstration. Not NMDC infrastructure.",
    notes,
  };
}

/** Build the demonstration layers, positioned relative to the published extent. */
function buildSyntheticLayers(extent: DecimalExtent): MapLayer[] {
  const { west, east, south, north } = extent;
  // Fractions of the extent, so the demo geometry scales with the real bounds rather
  // than carrying invented absolute coordinates of its own.
  const at = (fx: number, fy: number): LonLat => ({
    lon: west + (east - west) * fx,
    lat: south + (north - south) * fy,
  });

  return [
    {
      id: "SYNTHETIC_HAUL_ROADS",
      name: "Haul roads (demonstration)",
      provenance: "SYNTHETIC_FOR_DEMO",
      features: [
        syntheticFeature(
          "SYN-HR-1",
          "Demonstration haul route A",
          "LINESTRING",
          [at(0.18, 0.22), at(0.34, 0.38), at(0.52, 0.44), at(0.7, 0.6)],
          "Illustrative only. NMDC haul-road geometry is not public.",
        ),
        syntheticFeature(
          "SYN-HR-2",
          "Demonstration haul route B",
          "LINESTRING",
          [at(0.52, 0.44), at(0.6, 0.28), at(0.78, 0.24)],
          "Illustrative only. NMDC haul-road geometry is not public.",
        ),
      ],
    },
    {
      id: "SYNTHETIC_JUNCTIONS",
      name: "Junctions (demonstration)",
      provenance: "SYNTHETIC_FOR_DEMO",
      features: [
        syntheticFeature(
          "SYN-J-1",
          "Demonstration junction 1",
          "POINT",
          [at(0.52, 0.44)],
          "Illustrative.",
        ),
        syntheticFeature(
          "SYN-J-2",
          "Demonstration junction 2",
          "POINT",
          [at(0.34, 0.38)],
          "Illustrative.",
        ),
      ],
    },
    {
      id: "SYNTHETIC_OPERATIONAL_ZONES",
      name: "Operational zones (demonstration)",
      provenance: "SYNTHETIC_FOR_DEMO",
      features: [
        syntheticFeature(
          "SYN-Z-LOAD",
          "Demonstration loading zone",
          "POINT",
          [at(0.18, 0.22)],
          "Illustrative.",
        ),
        syntheticFeature(
          "SYN-Z-CRUSH",
          "Demonstration crusher area",
          "POINT",
          [at(0.7, 0.6)],
          "Illustrative.",
        ),
        syntheticFeature(
          "SYN-Z-DUMP",
          "Demonstration dump area",
          "POINT",
          [at(0.78, 0.24)],
          "Illustrative.",
        ),
      ],
    },
  ];
}

/**
 * The Bailadila Deposit-5 site.
 *
 * OSM_CONTEXT_ROADS is declared and EMPTY: no OSM extract has been imported into this
 * repository. It is listed rather than omitted so the absence is visible, and it carries
 * the reason. Nothing is drawn for it.
 */
export function bailadilaDeposit5(): GeoSite {
  const decimal = toDecimalExtent(DEPOSIT5_EXTENT);
  return {
    siteId: "NMDC-BAILADILA-DEP5",
    siteName: "NMDC Bailadila Iron Ore Mine, Deposit-5, Bacheli",
    extent: DEPOSIT5_EXTENT,
    coordinateReference: "ASSUMED_WGS84_UNVERIFIED",
    extentProvenance: "DERIVED_FROM_AUTHORITATIVE",
    extentSource: SOURCE_EC,
    leaseAreaHa: 540.05,
    toposheet: "E44J2 (Survey of India)",
    district: "South Bastar Dantewada",
    state: "Chhattisgarh",
    layers: [
      {
        id: "SITE_EXTENT",
        name: "Published lease coordinate extent",
        provenance: "DERIVED_FROM_AUTHORITATIVE",
        features: [
          {
            id: "DEP5-EXTENT",
            name: "PUBLISHED LEASE COORDINATE EXTENT",
            geometryType: "BOUNDING_EXTENT",
            coordinates: [],
            provenance: "DERIVED_FROM_AUTHORITATIVE",
            source: SOURCE_EC,
            notes:
              "Bounding extent of four published coordinates. NOT the lease boundary: the " +
              "lease is 540.05 ha and this box is larger. No polygon is published.",
          },
        ],
      },
      {
        id: "OSM_CONTEXT_ROADS",
        name: "Contextual roads (OpenStreetMap)",
        provenance: "OPEN_DATA_OSM",
        features: [],
        unavailableReason:
          "No OpenStreetMap extract has been imported. Nothing is drawn. OSM roads are " +
          "public context, never NMDC haul-road geometry.",
      },
      ...buildSyntheticLayers(decimal),
      {
        id: "VEHICLES",
        name: "Vehicles",
        provenance: "UNAVAILABLE",
        features: [],
        unavailableReason:
          "Vehicle geography comes from the position provider, not from a geographic " +
          "dataset. No physical positioning source exists on this prototype.",
      },
    ],
  };
}

/** Layers carrying at least one feature. A declared-but-empty layer is not drawn. */
export function drawableLayers(site: GeoSite): MapLayer[] {
  return site.layers.filter((layer) => layer.features.length > 0);
}

/** Layers that exist in the model but have no data, with the reason each states. */
export function unavailableLayers(site: GeoSite): MapLayer[] {
  return site.layers.filter((layer) => layer.features.length === 0);
}

/** True when any drawn layer is OSM-derived, so ODbL attribution must be rendered. */
export function requiresOsmAttribution(site: GeoSite): boolean {
  return drawableLayers(site).some(
    (layer) => layer.provenance === "OPEN_DATA_OSM" || layer.provenance === "DERIVED_FROM_OSM",
  );
}
