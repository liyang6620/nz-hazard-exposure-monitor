# M5 Power BI evidence

Power BI Desktop 2.155.756.0 opened the PBIP project and refreshed both real
M3 Parquet tables on 2026-10-25 after `RepoRoot` was set locally to the
absolute repository path. That machine-specific value was restored to the
source-controlled relative placeholder before commit. The five pages rendered
nonblank data and were captured individually:

- `powerbi-overview.png`
- `powerbi-event-explorer.png`
- `powerbi-population-exposure.png`
- `powerbi-buildings-footprint.png`
- `powerbi-method-quality.png`

`nzhem-powerbi-report.pdf` is the exported five-page report (275,462 bytes).
`pdfinfo` reports five pages at 996 x 576 points. The final Method and quality page uses a static
imported notes table so the policy-data, interpretation, and building-date
limitations remain visible in both Power BI Desktop and PDF export.

No Microsoft account was used, no report was published, and no license or
privacy terms were accepted. A clipboard permission prompt raised by the
embedded Power BI WebView was dismissed without granting access. The required
two-minute walkthrough remains an owner action.
