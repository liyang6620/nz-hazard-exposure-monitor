# MG local GIS acceptance evidence

This evidence covers the MG work that does not require an Esri account. No
hosted layer, API key, OAuth token, paid ArcGIS service or cloud resource was
created.

## File Geodatabase

`scripts/export_file_geodatabase.py` generated
`.local/artifacts/mg/nzhem_mg_sample.gdb` with GDAL 3.12.4 and read every layer
back through OpenFileGDB:

| Layer | Rows | Geometry | CRS |
|---|---:|---|---|
| `nzhem_events` | 10 | Point | EPSG:2193 |
| `event_exposure_r6` | 4,011 | MultiPolygon | EPSG:2193 |
| `nzhem_metadata` | 16 | None | Non-spatial |

The event layer carries both `valid_bldg` (event-time, nullable),
`as_if_today_buildings` and `event_time_status`. The exposure layer carries
event-time, as-if-today and current counts separately.

The committed JSON contains the read-back schema. The generated geodatabase is
an ignored local artifact because it can be reproduced from M3 Parquet outputs.

## Kaikoura cross-validation

The exact GeoPandas/Shapely point-in-polygon result and the production H3-8
centre assignment were compared for 3,219,311 current, deduplicated building
points in batches of 20,000:

- MMI band matches: 3,201,877 (99.458%).
- Band mismatches: 17,434.
- Mean absolute numeric MMI difference: 0.00365.
- Peak process RSS: 450.4 MB, below the 768 MB guard.
- Minimum C-drive free space: 57.27 GB, above the 20 GB floor.
- DuckDB memory limit: 512 MB; batch size: 20,000 buildings.

Differences are concentrated near official MMI contour boundaries, where a
building point and its H3-8 centre can lie on different sides. The CSV records
counts by region and MMI band.

Kaikoura's event-time valid building count is `NULL` with status
`not_supported` because source lifecycle coverage starts in 2018. Current
buildings are used only to validate the spatial assignment method and are not
substituted into the historical exposure result.

## Token-free local map

`scripts/build_local_map.py` generated 4,011 MMI 5+ H3-6 features for ten events
and a project-derived New Zealand outline. The complete static payload is
2,195,110 bytes. `/map/` uses the ArcGIS Maps SDK with local GeoJSON, no basemap,
no API key and no authenticated Esri service.

## Coordinate contract

`docs/notes/nztm-wgs84-axis-order.md` documents EPSG:2193 easting/northing,
forced longitude/latitude output for EPSG:4326, H3's latitude/longitude input,
and GeoJSON's longitude/latitude coordinate order.

## Deferred ArcGIS account work

The following are explicitly deferred until the repository owner has an Esri
account and the applicable approval is given:

- unattended hosted-layer update validation;
- API key or minimum-scope OAuth configuration;
- refresh-token storage, renewal and expiry alerting;
- hosted-layer publication and Esri MCP validation.
