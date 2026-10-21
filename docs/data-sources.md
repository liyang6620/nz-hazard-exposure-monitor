# Data sources

This document records the M0 source assessment performed on 2026-10-22. Raw
source data is not committed to this repository. All timestamps stored by the
project will be UTC; presentation converts them to `Pacific/Auckland`.

## Summary

| Dataset | Selected source | Access and volume | Licence | M0 conclusion |
|---|---|---|---|---|
| Earthquake catalogue | GeoNet FDSN Event v1.2 plus GeoNet Quake API | Public HTTPS; FDSN returns at most 10,000 events per response. A year-partitioned M4+ query over the NZ region returned 18,895 rows for 2000-2026. | [GeoNet data policy](https://www.geonet.org.nz/policy), CC BY 3.0 NZ | Suitable. Poll FDSN with `updatedafter`; use the Quake API to observe the current quality state. |
| Measured/reported intensity | GeoNet Intensity API; Shaking Layers `stationlist.json` for archived events | Public HTTPS. The Intensity API is a current snapshot, not an event-history service. A Kaikoura archive contained 324 station/macroseismic features. | GeoNet data policy, CC BY 3.0 NZ | Use the live API for current display and archived `stationlist.json` for historical validation when a Shaking Layers event exists. |
| Official MMI surfaces | Earth Sciences New Zealand Shaking Layers API; rolling ArcGIS layer for discovery | Public HTTPS. Historical events expose versioned files; Kaikoura's MMI polygon ZIP was 1,289,508 bytes. The rolling ArcGIS layer has a 2,000-record response limit. | GeoNet terms and disclaimer; cite DOI `10.21420/J856-2J84` | Suitable. Prefer the versioned Shaking Layers API over the rolling 30-day ArcGIS layer. |
| Building outlines | LINZ layer 101292, NZ Building Outlines (All Sources) | 6,634,223 polygons, EPSG:2193. Metadata is public; WFS, spatial queries and changesets require an API key. | CC BY 4.0 | Suitable, but it is a large national dataset and must be ingested in regional batches. |
| Population | Stats NZ layer 120766, 2023 Census totals by topic for individuals, SA1 part 1 | 33,164 multipolygons, including 16 empty geometries, EPSG:2193. WFS requires an API key. | CC BY 4.0 | No public meshblock population layer matching the plan was found. SA1 population is available; this requires a PM decision before M2. |
| Administrative boundaries | Stats NZ layer 111225, Meshblock Higher Geographies 2023 (high definition) | 57,539 multipolygons, including 16 empty geometries, EPSG:2193. Contains meshblock, SA1, SA2, TA and regional council codes. | CC BY 4.0 | Suitable. Reject or quarantine null geometry rows and retain their identifiers for reconciliation. |

## GeoNet earthquake catalogue

### Interfaces

- FDSN Event: `https://service.geonet.org.nz/fdsnws/event/1/query`
- Quake API: `https://api.geonet.org.nz/quake`
- FDSN usage: <https://www.geonet.org.nz/data/tools/FDSN>
- Quake API documentation: <https://api.geonet.org.nz/>

FDSN v1.2 supports QuakeML XML and pipe-delimited text. It does not support
GeoJSON or a `limit` parameter. Relevant text fields are `EventID`, `Time`,
`Latitude`, `Longitude`, `Depth/km`, `Magnitude`, `EventLocationName`, and
`EventType`. `updatedafter` is supported and is the incremental polling cursor.

The Quake API returns GeoJSON. Fields observed in M0 were `publicID`, `time`,
`depth`, `magnitude`, `mmi`, `locality`, and `quality`. The live feed has shown
`quality = deleted`; therefore the pipeline must compare the current Quake API
state with previously seen IDs. FDSN does not provide a reliable tombstone
history and must not be treated as the deletion source.

The FDSN service caps a response at 10,000 events. Backfill must partition by
year and may further partition spatially or monthly if a partition approaches
that cap. A reproducibility query over latitude -50 to -25 and the two longitude
ranges 160..180 and -180..-170 returned 18,895 M4+ rows for 2000 through 2026.
This is a planning count, not a final catalogue count; revisions and boundary
choices can change it.

## GeoNet intensity

The live endpoints are:

- `https://api.geonet.org.nz/intensity?type=measured`
- `https://api.geonet.org.nz/intensity?type=reported`

M0 observed 325 measured point features with `mmi`. The reported response had
`mmi`, `count`, and `count_mmi`. The endpoint has no event-ID or time-range
parameter and is not an archive.

For events processed by Shaking Layers, the versioned archive includes
`stationlist.json`. Its features include coordinates, station code/name,
`instrumentType`, observed `intensity`, uncertainty, distance measures, and
model predictions. This is the reproducible historical validation source for
those events. Events without a Shaking Layers archive have no confirmed public
historical intensity source and must be marked unavailable, not imputed.

## Earth Sciences New Zealand Shaking Layers

### Versioned API

- Documentation: <https://shakinglayers.geonet.org.nz/api>
- Year listing: `GET /api/v1/events?year=YYYY`
- Versions: `GET /api/v1/events/{publicID}`
- Latest manifest: `GET /api/v1/events/{publicID}/latest`
- File: `GET /api/v1/events/{publicID}/latest/{fileName}`
- Archive: `GET /api/v1/download/events/{publicID}/latest.zip`

The archive provides reviewed or automatic versions and files including MMI
GeoTIFF, standard-deviation GeoTIFF, contour GeoJSON, contour polygon
Shapefile ZIP, CoverageJSON, map PDF, parameters, and `stationlist.json`.
Direct checks found published versions for every named historical event in
section 10.4 of the plan through the 2021 Kermadec event:

| Event | GeoNet public ID | Latest checked type |
|---|---|---|
| 2010 Darfield | `3366146` | reviewed |
| 2011 Christchurch (February) | `3468575` | reviewed |
| 2011 Christchurch (June) | `3528839` | reviewed |
| 2013 Cook Strait / Seddon | `2013p543824` | reviewed |
| 2013 Lake Grassmere | `2013p613797` | reviewed |
| 2014 Eketahuna | `2014p051675` | reviewed |
| 2016 East Cape | `2016p661332` | reviewed |
| 2016 Kaikoura | `2016p858000` | reviewed |
| 2021 Kermadec | `2021p169764` | automatic |

The tenth, recent event is deliberately selected in M3 so it is within the
required rolling 12-month window at implementation time.

### Rolling ArcGIS layer

ArcGIS item `987481c6a53245e7ad8b13ec404e7402` is the public "Modified
Mercalli Intensity (MMI) Last 30 Days" feature service. Layer 0 supports JSON,
GeoJSON and PBF. Fields include `MMI`, `MMI_INTENSITY`, `MMI_DESCRIPTION`,
`MAGNITUDE`, `DEPTH`, `TIME`, `PUBLIC_ID`, and `LINK`. It is useful for current
discovery but is not the historical system of record.

Shaking Layers can be automatically generated and later reviewed. Persist the
source `versionpath`, `type`, `issue_time`, URL and checksum. A later reviewed
version is a revision, not a new earthquake.

## LINZ building outlines

- Metadata API: <https://data.linz.govt.nz/services/api/v1/layers/101292/>
- Dataset page: <https://data.linz.govt.nz/layer/101292/>

The primary key is `building_outline_id`. Important attributes are
`building_id`, `capture_source_from`, `capture_source_to`,
`building_outline_lifecycle`, `begin_lifespan`, `end_lifespan`, and
`last_modified`. `shape` is a polygon in EPSG:2193.

Time semantics are not interchangeable. The initial implementation should use
`begin_lifespan` and `end_lifespan` for lifecycle filtering, preserve the
capture dates as provenance, and measure null/contradictory dates in M2 before
claiming historical completeness. The source notes that lifecycle-table
maintenance stopped after January 2025, so "currently present" is approximate.

The national layer excludes some remote areas, including parts of the Southern
Alps, Fiordland, Stewart Island and the Chatham Islands. That limitation must be
carried into exposure reporting. WFS, WFS changesets, the spatial query API and
data-table API require a LINZ API key. Full export size was not measured because
no owner-created API key is available in M0. M2 should use GeoParquet or
GeoPackage regional exports, log bytes and feature counts, and never commit the
downloads.

## Stats NZ population and boundaries

### Population candidate

- Layer 120766: <https://datafinder.stats.govt.nz/services/api/v1/layers/120766/>
- Lookup attachment: document 25524 on the same service

The official lookup maps `VAR_1_3` to the 2023 Census usually resident
population count. Counts use fixed random rounding to base 3 and suppression;
`-997` means not available and `-999` means confidential. Individual values do
not necessarily add to published totals.

This layer is SA1, not meshblock. No suitable public 2023 Census meshblock
total-population layer was found. The plan's building-footprint allocation
algorithm can be applied at SA1, but that changes its spatial precision and
must not be done without PM approval.

### Boundaries

- Layer 111225: <https://datafinder.stats.govt.nz/services/api/v1/layers/111225/>

The layer contains `MB2023_V1_00`, `SA12023_V1_00`, `SA22023_V1_00`,
`TA2023_V1_00`, `REGC2023_V1_00`, names, land/water classification and areas.
It supplies all required hierarchy codes in one high-definition layer. Smaller
generalised layers may be used only for display, not source allocation.

## Coordinate handling

LINZ and Stats NZ geometry is NZTM2000 (EPSG:2193). Calculate footprint area
and spatial joins in EPSG:2193. Transform to EPSG:4326 with explicit
traditional GIS axis order (`always_xy=True` in pyproj) before computing H3.
Store longitude before latitude when calling H3 APIs that expect `(lat, lng)`
arguments by name; never rely on CRS axis metadata alone.

## Attribution

Product documentation and published outputs must include, at minimum:

- "Earthquake data: GeoNet / Earth Sciences New Zealand, CC BY 3.0 NZ."
- "Shaking Layers Dataset, Earth Sciences New Zealand, DOI 10.21420/J856-2J84."
- "Building outlines: Land Information New Zealand, CC BY 4.0."
- "Census and boundary data: Stats NZ, CC BY 4.0. Counts are randomly rounded and may be suppressed."
