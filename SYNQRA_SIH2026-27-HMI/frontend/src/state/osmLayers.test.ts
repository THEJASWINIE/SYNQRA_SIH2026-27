/**
 * OpenStreetMap layers unit tests — NMDC Bailadila Deposit-5 area.
 *
 * Pure logic. No DOM, no jsdom, no Testing Library (M4D-C).
 */

import { describe, expect, it } from "vitest";
import { isAuthoritativeChain } from "./geoSite";
import { osmCounts, osmLayers, OSM_PROVENANCE } from "./osmLayers";

describe("OpenStreetMap extract and layers", () => {
  it("carries full ODbL attribution and extraction metadata", () => {
    expect(OSM_PROVENANCE.source).toBe("OpenStreetMap");
    expect(OSM_PROVENANCE.license).toContain("Open Database License (ODbL)");
    expect(OSM_PROVENANCE.attribution).toContain("© OpenStreetMap contributors, ODbL");
    expect(OSM_PROVENANCE.crs).toContain("WGS84");
    expect(OSM_PROVENANCE.warning).toContain("NOT NMDC surveyed geometry");
  });

  it("extract contains real OSM geometry elements", () => {
    const counts = osmCounts();
    expect(counts.areas).toBeGreaterThan(0);
    expect(counts.siteRoads).toBeGreaterThan(0);
    expect(counts.townshipRoads).toBeGreaterThan(0);
  });

  it("every imported feature has provenance OPEN_DATA_OSM", () => {
    const layers = osmLayers();
    for (const layer of layers) {
      expect(layer.provenance).toBe("OPEN_DATA_OSM");
      for (const feature of layer.features) {
        expect(feature.provenance).toBe("OPEN_DATA_OSM");
      }
    }
  });

  it("no OSM feature is classified as AUTHORITATIVE_PUBLIC or verified NMDC geometry", () => {
    const layers = osmLayers();
    for (const layer of layers) {
      expect(isAuthoritativeChain(layer.provenance)).toBe(false);
      for (const feature of layer.features) {
        expect(isAuthoritativeChain(feature.provenance)).toBe(false);
        expect(feature.source).toContain("OpenStreetMap");
      }
    }
  });

  it("landuse quarry and non-residential site roads are ON by default", () => {
    const layers = osmLayers();
    const areas = layers.find((l) => l.id === "OSM_SITE_AREAS");
    const siteRoads = layers.find((l) => l.id === "OSM_SITE_ROADS");

    expect(areas?.defaultVisible).toBe(true);
    expect(siteRoads?.defaultVisible).toBe(true);

    const quarryFeature = areas?.features.find((f) => f.name.includes("Quarry"));
    expect(quarryFeature).toBeDefined();
    expect(quarryFeature?.geometryType).toBe("POLYGON");
  });

  it("township/residential streets are OFF by default (defaultVisible = false)", () => {
    const layers = osmLayers();
    const township = layers.find((l) => l.id === "OSM_TOWNSHIP_ROADS");

    expect(township?.defaultVisible).toBe(false);
    expect(township?.name).toContain("not mine haul roads");
    for (const feature of township?.features ?? []) {
      expect(feature.name).toContain("Township street");
    }
  });

  it("non-authoritative OSM feature naming includes explicit OSM label notices", () => {
    const layers = osmLayers();
    for (const layer of layers) {
      for (const feature of layer.features) {
        expect(feature.name).not.toMatch(/^NMDC /i);
        expect(feature.notes).toContain("Community-contributed open data");
      }
    }
  });
});
