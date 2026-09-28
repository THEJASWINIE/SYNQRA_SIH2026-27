/**
 * OpenStreetMap layers for the Bailadila Deposit-5 area.
 *
 * ==========================================================================
 *  THIS IS OPEN DATA. IT IS NOT NMDC GEOMETRY.
 *
 *  Every feature produced here is OPEN_DATA_OSM and carries ODbL attribution.
 *  None of it is authoritative, and none of it may be relabelled as NMDC
 *  infrastructure, however suggestive its tags are:
 *
 *    - a way tagged `landuse=quarry` is a CONTRIBUTOR'S mapping of a quarry.
 *      It is NOT NMDC's surveyed pit boundary, and it is not the lease.
 *    - a way whose OSM `name` is "NMDC" is a CONTRIBUTOR'S LABEL. A name tag
 *      is not provenance. It does not make the polygon authoritative.
 *    - `highway=residential` ways inside the extent are Bacheli TOWNSHIP
 *      STREETS. They are not mine haul roads, and they are not drawn by
 *      default, because forty street lines under a mine heading reads as a
 *      haul network to anyone glancing at it.
 * ==========================================================================
 *
 * The extract is bundled rather than fetched at runtime: S1 then works offline and
 * deterministically, and the demonstration cannot silently change because someone edited
 * OSM an hour before. ODbL permits redistribution with attribution, which the bundled
 * file carries verbatim in `_provenance`.
 *
 * Pure and framework-free, so it is testable without a DOM (M4D-C).
 */

import extract from "../data/osm/bailadila-deposit5.osm.json";
import type { GeoFeature, LonLat, MapLayer } from "./geoSite";

interface OsmProvenance {
  source: string;
  source_url: string;
  license: string;
  attribution: string;
  retrieved_at: string;
  overpass_timestamp: string | null;
  crs: string;
  warning: string;
}

interface OsmElement {
  id: number;
  tags: Record<string, string>;
  geometry: { lat: number; lon: number }[];
}

const doc = extract as unknown as { _provenance: OsmProvenance; elements: OsmElement[] };

/** The extract's own provenance block, shown in the UI rather than paraphrased. */
export const OSM_PROVENANCE: OsmProvenance = doc._provenance;

/** Ways whose `highway` value marks them as township streets rather than site access. */
const TOWNSHIP_HIGHWAY_VALUES = new Set(["residential"]);

function toLonLat(element: OsmElement): LonLat[] {
  return element.geometry.map((p) => ({ lon: p.lon, lat: p.lat }));
}

/**
 * A human-readable name that NEVER upgrades an OSM tag into an NMDC claim.
 *
 * An OSM `name` is included in parentheses so a reader can see what the contributor
 * wrote, while the leading text says plainly what the feature actually is.
 */
function describe(element: OsmElement): string {
  const tags = element.tags;
  const name = tags.name ? ` (OSM name: ${tags.name})` : "";
  if (tags.landuse === "quarry") return `Quarry area mapped in OSM${name}`;
  if (tags.landuse) return `OSM landuse: ${tags.landuse}${name}`;
  if (tags.highway === "residential") return `Township street${name}`;
  if (tags.highway) return `OSM road: ${tags.highway}${name}`;
  if (tags.railway) return `OSM railway: ${tags.railway}${name}`;
  return `OSM way ${element.id}${name}`;
}

function feature(element: OsmElement, isArea: boolean): GeoFeature {
  return {
    id: `OSM-${element.id}`,
    name: describe(element),
    geometryType: isArea ? "POLYGON" : "LINESTRING",
    coordinates: toLonLat(element),
    provenance: "OPEN_DATA_OSM",
    source: `OpenStreetMap way ${element.id} — ${OSM_PROVENANCE.license} (https://www.openstreetmap.org/way/${element.id})`,
    notes:
      "Community-contributed open data. NOT NMDC surveyed geometry and not an official " +
      "mine plan.",
  };
}

const areas = doc.elements.filter((e) => Boolean(e.tags.landuse));
const highways = doc.elements.filter((e) => Boolean(e.tags.highway));
const township = highways.filter((e) => TOWNSHIP_HIGHWAY_VALUES.has(e.tags.highway as string));
const siteAccess = highways.filter((e) => !TOWNSHIP_HIGHWAY_VALUES.has(e.tags.highway as string));

/**
 * The OSM layers.
 *
 * Visible by default: the mapped areas and the non-residential ways — the features that
 * actually say something about the site. Township streets are present, real, and OFF by
 * default (decision B), so the map never implies forty residential roads are haul roads.
 */
export function osmLayers(): MapLayer[] {
  return [
    {
      id: "OSM_SITE_AREAS",
      name: "Mapped areas (OpenStreetMap)",
      provenance: "OPEN_DATA_OSM",
      features: areas.map((e) => feature(e, true)),
      defaultVisible: true,
      ...(areas.length === 0 ? { unavailableReason: "No landuse areas in the extract." } : {}),
    },
    {
      id: "OSM_SITE_ROADS",
      name: "Site access roads (OpenStreetMap)",
      provenance: "OPEN_DATA_OSM",
      features: siteAccess.map((e) => feature(e, false)),
      defaultVisible: true,
      ...(siteAccess.length === 0
        ? { unavailableReason: "No non-residential ways in the extract." }
        : {}),
    },
    {
      id: "OSM_TOWNSHIP_ROADS",
      name: "Township streets (OpenStreetMap) — not mine haul roads",
      provenance: "OPEN_DATA_OSM",
      features: township.map((e) => feature(e, false)),
      defaultVisible: false,
      ...(township.length === 0
        ? { unavailableReason: "No residential ways in the extract." }
        : {}),
    },
  ];
}

/** Counts, for the provenance panel. Reported, never estimated. */
export function osmCounts(): { areas: number; siteRoads: number; townshipRoads: number } {
  return { areas: areas.length, siteRoads: siteAccess.length, townshipRoads: township.length };
}
