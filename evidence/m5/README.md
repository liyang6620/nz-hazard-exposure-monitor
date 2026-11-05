# M5 Power BI redesign evidence

The prior five-page PDF and screenshots were rejected. They remain in
`rejected-v1/` as historical evidence only. The replacement report was refreshed
in Power BI Desktop 2.155.385.0 on 6 Nov 2026 without Microsoft sign-in or
Power BI Service publication.

## Deliverables

- [Five-page PDF](nzhem-powerbi-report.pdf)
- [Event Overview](event-overview.png)
- [Event Comparison](event-comparison.png)
- [Regional Exposure](regional-exposure.png)
- [Event History](event-history.png)
- [Data Health](data-health.png)
- [Model size and validation](model-size.md)

The PDF is a Power BI Desktop export. Desktop printed its unrelated auto-recovery
banner above every page; `finalize_powerbi_pdf.py` cropped 43 PDF points from
the top of each page. The five images are rendered from that final PDF, showing
only the report canvas.

## Checks

The PBIP has five pages, 62 visual definitions, 13 source tables plus the
`_Measures` table, 28 explicit measures and nine one-way relationships. Implicit
measures are discouraged. Keys and source numeric columns are hidden. The MMI
threshold supports 4-8 with default 6 through a single-select dropdown;
Desktop's native numeric slider did not preserve the single selected value
needed by the threshold measures.

`check_powerbi_project.py` passed PBIR schema validation. The bounded snapshot
was built with DuckDB limited to 512 MB and one thread. `check_powerbi_snapshot.py`
reconciled all ten events' MMI 6+ buildings and population to M3 gold with no
orphan region keys. C-drive free space remained above 20 GiB.

In Desktop, Kaikōura at threshold 6 showed M7.8, max MMI 8.4, 78,564 buildings
and 83,276 people. Changing the threshold to 7 changed exposed buildings to
9,720; it was returned to 6 before export. The Taumarunui history magnitude is
5.7, based on the local newer GeoNet revision of 5.66. Data Health reports the
station-weighted MAE of 1.049, not a sum of event errors.

Data Health uses a read-only Azure gold/runtime snapshot captured before the
Desktop refresh; it is not a live dashboard. Its MMI map is an offline
longitude/latitude H3 scatter plot over a locally generated coastline image,
not a service-backed basemap. The regional page combines that map with a
full-height region/district ranking table; the table supports drill-down.

The 6 Nov NZDT read-only snapshot captured Azure's latest successful
housekeeping completion at 5 Nov 2026 12:00:02 UTC, alongside the public
manifest generated at 12:00:02 UTC. Data Health stores UTC clock time without
timezone conversion and calculates age at snapshot time, not at viewing time.
The poison-queue depth of 27 includes acceptance-drill messages; the queue does
not label those messages separately, so no unverified split is presented.
