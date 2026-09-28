# BAILADILA DEPOSIT-5 — SOURCE VERIFICATION RECORD

**Date:** 2026-09-08
**Purpose:** record exactly how the one authoritative geographic fact in this prototype was
obtained and checked. Nothing here is taken from a search-result summary.

---

## 1. VERIFIED SOURCE

**Document:** MoEF&CC File No. `J-11015/261/2007-IA.II(M)`, dated 11/12/2024
**Subject:** Grant of prior Environmental Clearance, "Capacity Expansion of Bailadila Iron
Ore Mine", addressed to NMDC Limited
**Host:** `nmdc.co.in` (NMDC's own domain)
**Classification:** `AUTHORITATIVE_PUBLIC`

**Verification method:** the PDF was downloaded and its text extracted locally with
`pypdf` (23 pages, 69,996 characters). The passage below was read from the extracted text,
not from a search engine summary.

## 2. QUOTED PASSAGE (verbatim)

> "The mine lease area is located between Latitude: 18°40'00.54" to 18°41'50.38" N and
> Longitude: 81°10'41.83" to 81°12'31.89" E. The mine lease area falls under the Survey of
> India Toposheet No: E44J2 and falls in Seismic Zone-II."

Appears four times in the document. Also verified from the same document:

| Fact | Value |
|---|---|
| Deposit | Deposit-5, village **Bacheli** |
| District / State | South Bastar Dantewada, Chhattisgarh |
| Mine lease area | **540.05 ha**, entirely forest land |
| Lease period | 11/09/2015 – 10/09/2035 |
| Toposheet | E44J2 (Survey of India) |

## 3. INTERPRETATION

| Question | Answer |
|---|---|
| Coordinate order | Latitude first (N), then Longitude (E); each min → max |
| Geometry type | **BOUNDING EXTENT.** Two latitudes + two longitudes |
| Polygon available? | **NO.** Zero DMS corner tokens in 23 pages; no pillar, vertex or corner list |
| CRS / datum | **NOT STATED IN THE SOURCE** |
| Confidence (numbers) | **HIGH** — verbatim, official, NMDC-hosted, extracted locally |
| Confidence (datum) | **MEDIUM** — inferred, not stated |

## 4. CONSISTENCY CROSS-CHECK (performed by us, not from the document)

The extent spans ≈ 3.39 km N–S × 3.22 km E–W ≈ **10.9 km²**. The stated lease is 540.05 ha
= **5.40 km²**, i.e. ~50% of its bounding box — the expected ratio for an irregular
ridge-top deposit. Had the bounding box been *smaller* than the lease, the figures would be
inconsistent. They are not. This check is asserted in `geoSite.test.ts`.

## 5. DOCUMENTS CHECKED AND REJECTED AS COORDINATE SOURCES

| Document | Outcome |
|---|---|
| IBM MCDR "Dep 14 ML" inspection report | Extracted cleanly (7 pages, 15,189 chars). **Contains NO coordinates** — no latitude, longitude, toposheet, datum or degree symbol. It is an inspection report |
| MoEF TOR annexure, Deposit-11 | **Scanned image, no text layer** (3 pages, 0 extractable characters). Not usable |
| Web search summary quoting Deposit-14 extents | **UNVERIFIED — NOT USED.** Could not be confirmed against any primary document |

## 6. WHAT REMAINS UNVERIFIED

1. **The datum.** Recorded in code as `ASSUMED_WGS84_UNVERIFIED`. Survey of India sheets
   exist in both Everest 1830 and WGS84 realisations.
2. **The lease polygon.** A KML file was presented to the EAC (stated in the minutes) but
   is not included in the published document. The real shape is not public here.
3. **Deposit-14 / Kirandul coordinates.** Not verified. Not used anywhere in the code.

## 7. WHAT IS NOT CLAIMED

Physical NMDC mine integration is **NOT VERIFIED**.
Real mine operational geometry is **NOT CLAIMED**.
Real vehicle positioning is **NOT VERIFIED**.
