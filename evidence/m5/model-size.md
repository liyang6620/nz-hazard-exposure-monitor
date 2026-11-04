# M5 model size

Power BI Desktop version: 2.155.385.0 (26.06).

| Item | Size | Notes |
| --- | ---: | --- |
| Imported Parquet tables | 0.52 MiB | Twelve files; includes the cell-owner helper not imported into the model. |
| Refreshed Desktop `cache.abf` | 0.55 MiB | Ignored local QA copy after save. |
| Final five-page PDF | 0.90 MiB | Desktop export, recovery banner cropped. |

The local snapshot contains 10 events, 341 event/region/MMI exposure rows,
14,321 H3 map points and 2,547 validation stations. It excludes raw building
geometry and insured-value records. Snapshot creation used one DuckDB thread
with a 512 MB memory limit; this model does not require the 3.07 GB GeoPackage
in Desktop.
