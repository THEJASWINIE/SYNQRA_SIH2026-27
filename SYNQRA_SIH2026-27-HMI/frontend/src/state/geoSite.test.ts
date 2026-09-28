/**
 * Geospatial site model tests — Bailadila Deposit-5 prototype.
 *
 * Pure logic. No DOM, no jsdom, no Testing Library (M4D-C).
 *
 * THE CENTRAL ASSERTION OF THIS FILE: exactly one geographic fact in this system is backed
 * by an official document — four published coordinates — and everything else is either
 * absent, open data (OSM), or explicitly marked synthetic. The four numbers are a BOUNDING
 * EXTENT and the code must refuse to turn them into a lease polygon.
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
    expect(formatDms(DEPOSIT5_EXTENT.south)).toBe("18°40'0.54\"N");
    expect(formatDms(DEPOSIT5_EXTENT.north)).toBe("18°41'50.38\"N");
    expect(formatDms(DEPOSIT5_EXTENT.west)).toBe("81°10'41.83\"E");
    expect(formatDms(DEPOSIT5_EXTENT.east)).toBe("81°12'31.89\"E");
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
    const { widthM, heightM } = extentSizeMetres(toDecimalExtent(DEPOSIT5_EXTENT));
    const bboxKm2 = (widthM / 1000) * (heightM / 1000);
    expect(bboxKm2).toBeGreaterThan(5.4005);
    expect(bboxKm2).toBeLessThan(20);
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
    expect(feature?.coordinates).toEqual([]);
  });

  it("NOTHING in the authoritative chain is a POLYGON", () => {
    for (const layer of site.layers) {
      if (!isAuthoritativeChain(layer.provenance)) continue;
      for (const f of layer.features) {
        expect(f.geometryType, `${layer.id}/${f.id}`).not.toBe("POLYGON");
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

describe("the provenance chains stay separate", () => {
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

describe("synthetic demonstration geometry isolation", () => {
  const site = bailadilaDeposit5();
  const syntheticLayers = site.layers.filter((l) => l.id.startsWith("SYNTHETIC_"));

  it("synthetic demonstration layers exist and are hidden by default", () => {
    expect(syntheticLayers.length).toBeGreaterThan(0);
    for (const layer of syntheticLayers) {
      expect(layer.defaultVisible, layer.id).toBe(false);
    }
  });

  it("EVERY synthetic feature is marked SYNTHETIC_FOR_DEMO", () => {
    for (const layer of syntheticLayers) {
      expect(layer.provenance, layer.id).toBe("SYNTHETIC_FOR_DEMO");
      for (const f of layer.features) {
        expect(f.provenance, f.id).toBe("SYNTHETIC_FOR_DEMO");
      }
    }
  });

  it("every synthetic feature states SYNTHETIC — NOT NMDC INFRASTRUCTURE", () => {
    for (const layer of syntheticLayers) {
      for (const f of layer.features) {
        expect(f.source, f.id).toContain("SYNTHETIC — NOT NMDC INFRASTRUCTURE");
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
});

// ---------------------------------------------------------------------------
// OpenStreetMap Integration
// ---------------------------------------------------------------------------

describe("OpenStreetMap integrated layers", () => {
  const site = bailadilaDeposit5();
  const osmAreaLayer = site.layers.find((l) => l.id === "OSM_SITE_AREAS");
  const osmRoadLayer = site.layers.find((l) => l.id === "OSM_SITE_ROADS");
  const osmTownshipLayer = site.layers.find((l) => l.id === "OSM_TOWNSHIP_ROADS");

  it("OSM layers are present and tagged OPEN_DATA_OSM", () => {
    expect(osmAreaLayer?.provenance).toBe("OPEN_DATA_OSM");
    expect(osmRoadLayer?.provenance).toBe("OPEN_DATA_OSM");
    expect(osmTownshipLayer?.provenance).toBe("OPEN_DATA_OSM");
  });

  it("quarry and site access roads are enabled by default; township streets disabled", () => {
    expect(osmAreaLayer?.defaultVisible).toBe(true);
    expect(osmRoadLayer?.defaultVisible).toBe(true);
    expect(osmTownshipLayer?.defaultVisible).toBe(false);
  });

  it("requires ODbL attribution when OSM layers are rendered", () => {
    expect(requiresOsmAttribution(site)).toBe(true);
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

  it("screen projection puts north at the top and west at the left", () => {
    const d = toDecimalExtent(DEPOSIT5_EXTENT);
    const p = screenProjection(d, 100, 200);
    const nw = p.project({ lon: d.west, lat: d.north });
    const se = p.project({ lon: d.east, lat: d.south });
    expect(nw.x).toBeCloseTo(0, 6);
    expect(nw.y).toBeCloseTo(0, 6);
    expect(se.x).toBeCloseTo(100, 6);
    expect(se.y).toBeCloseTo(200, 6);
  });

  it("drawableLayers and unavailableLayers properly filter site layers", () => {
    const site = bailadilaDeposit5();
    const drawn = drawableLayers(site);
    expect(drawn.map((l) => l.id)).toEqual(["SITE_EXTENT", "OSM_SITE_AREAS", "OSM_SITE_ROADS"]);

    const unavailable = unavailableLayers(site);
    expect(unavailable.map((l) => l.id)).toEqual(["VEHICLES"]);
    expect(unavailable[0]?.unavailableReason).toBeTruthy();
  });
});
