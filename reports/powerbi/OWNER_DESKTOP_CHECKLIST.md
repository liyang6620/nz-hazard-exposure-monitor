# Power BI Desktop validation

The report source is generated and statically checked. Desktop refresh, five
canvas screenshots and PDF export remain pending until the Windows session is
unlocked. Once available:

1. Run `python scripts/build_powerbi_snapshot.py` and
   `python scripts/check_powerbi_snapshot.py`.
2. Run `python scripts/prepare_powerbi_desktop.py`; open the ignored
   `.local/powerbi-desktop/nzhem.pbip` copy and refresh all tables.
3. Inspect Event Overview, Event Comparison, Regional Exposure, Event History
   and Data Health. Check measures, map points, filters, drill-down, navigation
   and the MMI threshold 4–8 with default 6.
4. Capture each full report canvas and export a five-page PDF to `evidence/m5/`.
   Record the semantic model cache size and Desktop version.
5. Do not log in to a Microsoft account, accept licence or privacy prompts, or
   publish to Power BI Service. The owner records the two-minute walkthrough.
