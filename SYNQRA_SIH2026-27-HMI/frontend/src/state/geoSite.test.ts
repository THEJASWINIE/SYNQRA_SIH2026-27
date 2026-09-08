/**
 * Geospatial site model tests — Bailadila Deposit-5 prototype.
 *
 * Pure logic. No DOM, no jsdom, no Testing Library (M4D-C).
 *
 * THE CENTRAL ASSERTION OF THIS FILE: exactly one geographic fact in this system is backed
 * by an official document — four published coordinates — and everything else is either
 * absent or explicitly marked synthetic. The four numbers are a BOUNDING EXTENT and the
 * code must refuse to turn them into a lease polygon.
 */

import { describe, expect, it } from "vitest";
import {
  bailadilaDeposit5,
  DEPOSIT5_EXTENT,
  dmsToDecimal,
  drawableLayers,
  extentCentroid,
  extentSizeMetres,
  formatDms,
  GEO_PROVENANCE_TEXT,
  type GeoProvenance,
  isAuthoritativeChain,
  OSM_ATTRIBUTION,
  projectToLocalMetres,
  requiresOsmAttribution,
  screenProjection,
  toDecimalExtent,
  unavailableLayers,
  unprojectFromLocalMetres,
} from "./geoSite";

// ---------------------------------------------------------------------------
// the published coordinates
// ---------------------------------------------------------------------------

describe("published source coordinates", () => {
  it("stores the DMS values exactly as the source document printed them", () => {
    // "Latitude: 18°40'00.54" to 18°41'50.38" N and Longitude: 81°10'41.83" to 81°12'31.89" E"
    expect(formatDms(DEPOSIT5_EXTENT.south)).toBe('18°40\'0.54"N');
    expect(formatDms(DEPOSIT5_EXTENT.north)).toBe('18°41\'50.38"N');
    expect(formatDms(DEPOSIT5_EXTENT.west)).toBe('81°10\'41.83"E');
    expect(formatDms(DEPOSIT5_EXTENT.east)).toBe('81°12\'31.89"E');
  });

  it("converts DMS to decimal degrees correctly", () => {
    expect(dmsToDecimal(DEPOSIT5_EXTENT.south)).toBeCloseTo(18.6668167, 6);
    expect(dmsToDecimal(DEPOSIT5_EXTENT.north)).toBeCloseTo(18.6973278, 6);
    expect(dmsToDecimal(DEPOSIT5_EXTENT.west)).toBeCloseTo(81.1782861, 6);
    expect(dmsToDecimal(DEPOSIT5_EXTENT.east)).toBeCloseTo(81.2088583, 6);
  });

  it("handles southern and western hemispheres as negative", () => {
    expect(dmsToDecimal({ degrees: 10, minutes: 30, seconds: 0, hemisphere: "S" })).toBeCloseTo(
      -10.5,
      6,
    );
    expect(dmsToDecimal({ degrees: 20, minutes: 15, seconds: 0, hemisphere: "W" })).toBeCloseTo(
      -20.25,
      6,
    );
  });

  it("the extent is ordered north>south and east>west", () => {
    const d = toDecimalExtent(DEPOSIT5_EXTENT);
    expect(d.north).toBeGreaterThan(d.south);
    expect(d.east).toBeGreaterThan(d.west);
  });

  it("the extent is larger than the stated lease — it is a bounding box, not the lease", () => {
    // Independent cross-check: 540.05 ha = 5.4005 km². If the bbox were SMALLER than the
    // lease the figures would be inconsistent and the source could not be trusted.
    const { widthM, heightM } = extentSizeMetres(toDecimalExtent(DEPOSIT5_EXTENT));
    const bboxKm2 = (widthM / 1000) * (heightM / 1000);
    expect(bboxKm2).toBeGreaterThan(5.4005);
    expect(bboxKm2).toBeLessThan(20); // sane upper bound for a ~3.4 km site
  });
});

// ---------------------------------------------------------------------------
// NOT A POLYGON
// ---------------------------------------------------------------------------

describe("the extent is never represented as a polygon", () => {
  const site = bailadilaDeposit5();
  const extentLayer = site.layers.find((l) => l.id === "SITE_EXTENT");
  const feature = extentLayer?.features[0];

  it("the site extent feature has geometryType BOUNDING_EXTENT", () => {
    expect(feature?.geometryType).toBe("BOUNDING_EXTENT");
    expect(feature?.geometryType).not.toBe("POLYGON");
  });

  it("it carries NO coordinate list — no corners are manufactured", () => {
    // Four bounds do not make four surveyed corners. The document publishes no vertices.
    expect(feature?.coordinates).toEqual([]);
  });

  it("NOTHING in the authoritative chain is a POLYGON", () => {
    // The invariant protects the PUBLISHED EXTENT, not polygons in general. Synthetic
    // demonstration areas (pit, benches, dumps, zones) are legitimately polygons - they
    // are invented and say so. What must never happen is the four published bounds being
    // promoted into a lease shape, so the rule is scoped to the authoritative chain.
    for (const layer of site.layers) {
      if (!isAuthoritativeChain(layer.provenance)) continue;
      for (const f of layer.features) {
        expect(f.geometryType, `${layer.id}/${f.id}`).not.toBe("POLYGON");
      }
    }
  });

  it("every POLYGON in the site is synthetic and says so", () => {
    for (const layer of site.layers) {
      for (const f of layer.features) {
        if (f.geometryType !== "POLYGON") continue;
        expect(f.provenance, f.id).toBe("SYNTHETIC_FOR_DEMO");
        expect(f.name.toLowerCase(), f.id).toContain("demonstration");
      }
    }
  });

  it("is named as an extent, never as a boundary", () => {
    expect(feature?.name).toBe("PUBLISHED LEASE COORDINATE EXTENT");
    expect(extentLayer?.id).toBe("SITE_EXTENT");
    expect(JSON.stringify(site.layers)).not.toContain("SITE_BOUNDARY");
  });

  it("states in its notes that it is not the lease boundary", () => {
    expect(feature?.notes).toContain("NOT the lease boundary");
  });
});

// ---------------------------------------------------------------------------
// provenance chains
// ---------------------------------------------------------------------------

describe("the three provenance chains stay separate", () => {
  const site = bailadilaDeposit5();

  it("the published extent is DERIVED_FROM_AUTHORITATIVE and cites its source", () => {
    expect(site.extentProvenance).toBe("DERIVED_FROM_AUTHORITATIVE");
    expect(site.extentSource).toContain("J-11015/261/2007-IA.II(M)");
    expect(site.extentSource).toContain("nmdc.co.in");
    expect(isAuthoritativeChain(site.extentProvenance)).toBe(true);
  });

  it("OSM is NEVER classified as authoritative", () => {
    expect(isAuthoritativeChain("OPEN_DATA_OSM")).toBe(false);
    expect(isAuthoritativeChain("DERIVED_FROM_OSM")).toBe(false);
    expect(GEO_PROVENANCE_TEXT.OPEN_DATA_OSM).toContain("OPENSTREETMAP");
    expect(GEO_PROVENANCE_TEXT.OPEN_DATA_OSM).not.toContain("AUTHORITATIVE");
  });

  it("synthetic geometry is never classified as authoritative", () => {
    expect(isAuthoritativeChain("SYNTHETIC_FOR_DEMO")).toBe(false);
    expect(GEO_PROVENANCE_TEXT.SYNTHETIC_FOR_DEMO).toContain("DEMONSTRATION ONLY");
  });

  it("every provenance value has distinct display text", () => {
    const texts = Object.values(GEO_PROVENANCE_TEXT);
    expect(new Set(texts).size).toBe(texts.length);
  });

  it("every feature carries a provenance and a source", () => {
    for (const layer of site.layers) {
      for (const f of layer.features) {
        expect(f.provenance, f.id).toBeTruthy();
        expect(f.source.length, f.id).toBeGreaterThan(0);
      }
    }
  });
});

// ---------------------------------------------------------------------------
// synthetic geometry
// ---------------------------------------------------------------------------

describe("synthetic demonstration geometry", () => {
  const site = bailadilaDeposit5();
  const syntheticLayers = site.layers.filter((l) => l.id.startsWith("SYNTHETIC_"));

  it("the full demonstration mine is present as synthetic layers", () => {
    expect(syntheticLayers.map((l) => l.id).sort()).toEqual([
      "SYNTHETIC_BENCHES",
      "SYNTHETIC_DUMPS",
      "SYNTHETIC_HAUL_ROADS",
      "SYNTHETIC_JUNCTIONS",
      "SYNTHETIC_LOADING_FACES",
      "SYNTHETIC_OPERATIONAL_ZONES",
      "SYNTHETIC_PIT",
      "SYNTHETIC_PROCESSING",
      "SYNTHETIC_SUPPORT",
    ]);
  });

  it("the demonstration mine has enough substance to be a mine site", () => {
    const featureCount = syntheticLayers.reduce((n, l) => n + l.features.length, 0);
    expect(featureCount).toBeGreaterThanOrEqual(20);
    // A haul network, not a single line.
    const roads = syntheticLayers.find((l) => l.id === "SYNTHETIC_HAUL_ROADS");
    expect(roads?.features.length).toBeGreaterThanOrEqual(4);
  });

  it("EVERY synthetic feature is marked SYNTHETIC_FOR_DEMO", () => {
    for (const layer of syntheticLayers) {
      expect(layer.provenance, layer.id).toBe("SYNTHETIC_FOR_DEMO");
      for (const f of layer.features) {
        expect(f.provenance, f.id).toBe("SYNTHETIC_FOR_DEMO");
      }
    }
  });

  it("every synthetic feature states it is not NMDC infrastructure", () => {
    for (const layer of syntheticLayers) {
      for (const f of layer.features) {
        expect(f.source, f.id).toContain("Not NMDC infrastructure");
      }
    }
  });

  it("synthetic geometry sits inside the published extent", () => {
    const d = toDecimalExtent(DEPOSIT5_EXTENT);
    for (const layer of syntheticLayers) {
      for (const f of layer.features) {
        for (const c of f.coordinates) {
          expect(c.lon, f.id).toBeGreaterThanOrEqual(d.west);
          expect(c.lon, f.id).toBeLessThanOrEqual(d.east);
          expect(c.lat, f.id).toBeGreaterThanOrEqual(d.south);
          expect(c.lat, f.id).toBeLessThanOrEqual(d.north);
        }
      }
    }
  });

  it("no synthetic feature name claims to be official", () => {
    for (const layer of syntheticLayers) {
      for (const f of layer.features) {
        expect(f.name.toLowerCase(), f.id).toContain("demonstration");
        expect(f.name, f.id).not.toContain("NMDC");
      }
    }
  });
});

// ---------------------------------------------------------------------------
// OSM
// ---------------------------------------------------------------------------

describe("OpenStreetMap layer", () => {
  const site = bailadilaDeposit5();
  const osm = site.layers.find((l) => l.id === "OSM_CONTEXT_ROADS");

  it("is declared, empty, and explains why", () => {
    expect(osm?.provenance).toBe("OPEN_DATA_OSM");
    expect(osm?.features).toEqual([]);
    expect(osm?.unavailableReason).toContain("No OpenStreetMap extract has been imported");
  });

  it("states that OSM roads are never NMDC haul roads", () => {
    expect(osm?.unavailableReason).toContain("never NMDC haul-road geometry");
  });

  it("attribution is not rendered while no OSM geometry is drawn", () => {
    expect(requiresOsmAttribution(site)).toBe(false);
  });

  it("attribution WOULD be required once OSM geometry is drawn", () => {
    const withOsm = bailadilaDeposit5();
    const layer = withOsm.layers.find((l) => l.id === "OSM_CONTEXT_ROADS");
    layer?.features.push({
      id: "OSM-1",
      name: "Contextual road",
      geometryType: "LINESTRING",
      coordinates: [
        { lon: 81.18, lat: 18.67 },
        { lon: 81.19, lat: 18.68 },
      ],
      provenance: "OPEN_DATA_OSM",
      source: "OpenStreetMap",
    });
    expect(requiresOsmAttribution(withOsm)).toBe(true);
    expect(OSM_ATTRIBUTION).toContain("OpenStreetMap");
    expect(OSM_ATTRIBUTION).toContain("ODbL");
  });
});

// ---------------------------------------------------------------------------
// CRS and projection
// ---------------------------------------------------------------------------

describe("coordinate reference and projection", () => {
  it("records the datum as assumed and unverified, never as plain WGS84", () => {
    expect(bailadilaDeposit5().coordinateReference).toBe("ASSUMED_WGS84_UNVERIFIED");
  });

  it("projection round-trips within a millimetre", () => {
    const origin = extentCentroid(toDecimalExtent(DEPOSIT5_EXTENT));
    const point = { lon: 81.2, lat: 18.69 };
    const metres = projectToLocalMetres(point, origin);
    const back = unprojectFromLocalMetres(metres, origin);
    expect(back.lon).toBeCloseTo(point.lon, 9);
    expect(back.lat).toBeCloseTo(point.lat, 9);
  });

  it("the origin projects to zero", () => {
    const origin = extentCentroid(toDecimalExtent(DEPOSIT5_EXTENT));
    const metres = projectToLocalMetres(origin, origin);
    expect(metres.x).toBeCloseTo(0, 9);
    expect(metres.y).toBeCloseTo(0, 9);
  });

  it("one degree of latitude is about 111 km, and longitude is shorter at 18.7N", () => {
    const origin = { lon: 81.19, lat: 18.68 };
    const north = projectToLocalMetres({ lon: 81.19, lat: 19.68 }, origin);
    const east = projectToLocalMetres({ lon: 82.19, lat: 18.68 }, origin);
    expect(north.y).toBeCloseTo(111_320, 0);
    expect(east.x).toBeLessThan(north.y); // cos(18.68 deg) shortens longitude
    expect(east.x).toBeCloseTo(111_320 * Math.cos((18.68 * Math.PI) / 180), 0);
  });

  it("screen projection puts north at the top and west at the left", () => {
    const d = toDecimalExtent(DEPOSIT5_EXTENT);
    const p = screenProjection(d, 100, 200);
    const nw = p.project({ lon: d.west, lat: d.north });
    const se = p.project({ lon: d.east, lat: d.south });
    expect(nw.x).toBeCloseTo(0, 6);
    expect(nw.y).toBeCloseTo(0, 6); // SVG y grows downward, so north is y=0
    expect(se.x).toBeCloseTo(100, 6);
    expect(se.y).toBeCloseTo(200, 6);
  });
});

// ---------------------------------------------------------------------------
// layers
// ---------------------------------------------------------------------------

describe("layer availability", () => {
  const site = bailadilaDeposit5();

  it("drawable layers are exactly those with features", () => {
    for (const layer of drawableLayers(site)) {
      expect(layer.features.length, layer.id).toBeGreaterThan(0);
    }
  });

  it("empty layers are declared with a reason rather than omitted", () => {
    const missing = unavailableLayers(site);
    expect(missing.map((l) => l.id).sort()).toEqual(["OSM_CONTEXT_ROADS", "VEHICLES"]);
    for (const layer of missing) {
      expect(layer.unavailableReason, layer.id).toBeTruthy();
    }
  });

  it("the site names itself with its real administrative facts", () => {
    expect(site.siteName).toContain("NMDC Bailadila");
    expect(site.leaseAreaHa).toBe(540.05);
    expect(site.toposheet).toContain("E44J2");
    expect(site.district).toBe("South Bastar Dantewada");
    expect(site.state).toBe("Chhattisgarh");
  });

  it("no layer claims an authoritative provenance it has not earned", () => {
    const authoritative = site.layers.filter((l) => isAuthoritativeChain(l.provenance));
    expect(authoritative.map((l) => l.id)).toEqual(["SITE_EXTENT"]);
  });

  it("the provenance union covers every value the model can produce", () => {
    const used = new Set<GeoProvenance>(site.layers.map((l) => l.provenance));
    for (const p of used) expect(GEO_PROVENANCE_TEXT[p]).toBeTruthy();
  });
});
