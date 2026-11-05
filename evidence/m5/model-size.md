# M5 model size

Power BI Desktop version: 2.155.385.0 (26.06).

| Item | Size | Notes |
| --- | ---: | --- |
| Snapshot Parquet files | 0.52 MiB | Fourteen files; one cell-owner helper is not imported into the model. |
| Refreshed Desktop `cache.abf` | 0.56 MiB | Ignored local QA copy after save. |
| Final five-page PDF | 1.32 MiB | Desktop export, recovery banner cropped. |
| Two-minute captioned demo | 3.38 MiB | Silent Desktop window recording. |

The local snapshot contains 10 events, 341 event/region/MMI exposure rows,
14,321 H3 map points and 2,547 validation stations. It excludes raw building
geometry and insured-value records. Snapshot creation used one DuckDB thread
with a 512 MB memory limit; this model does not require the 3.07 GB GeoPackage
in Desktop.
