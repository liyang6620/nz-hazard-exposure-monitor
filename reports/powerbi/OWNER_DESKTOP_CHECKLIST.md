# Power BI Desktop validation

Desktop validation was completed on 4 Nov 2026 with Power BI Desktop
2.155.385.0. The ignored local copy refreshed all tables from the bounded gold
snapshot. Event Overview showed Kaikōura M7.8, max MMI 8.4, 78,564 exposed
buildings and 83,276 exposed people at the default MMI threshold of 6. Changing
the threshold to 7 changed the building measure to 9,720; it was restored to 6.
The five-page PDF and full-canvas images are in `evidence/m5/`.

To refresh on another computer:

1. Run `python scripts/build_powerbi_snapshot.py` and
   `python scripts/check_powerbi_snapshot.py`.
2. Run `python scripts/prepare_powerbi_desktop.py` and open the ignored
   `.local/powerbi-desktop/nzhem.pbip` copy. Use **Refresh > Data** after the
   model has finished opening. Power BI's early schema refresh can report an
   intermittent cyclic-reference error; reopening and using Data refresh
   succeeded in validation.
3. Inspect Event Overview, Event Comparison, Regional Exposure, Event History
   and Data Health. Check measures, map points, filters, drill-down, navigation
   and the MMI threshold 4–8 with default 6.
4. Export to PDF from Desktop. If its auto-recovery banner appears in the PDF,
   run `python scripts/finalize_powerbi_pdf.py` to crop only that banner and
   render the five page images.
5. Do not log in to a Microsoft account, accept licence or privacy prompts, or
   publish to Power BI Service. Deliver the PBIP, five canvas screenshots and PDF.
