# Power BI Desktop owner checklist

Desktop validation is complete. Power BI Desktop 2.155.756.0 loaded and
refreshed both M3 Parquet tables, and all five pages were visually checked.
Screenshots and the exported five-page PDF are under `evidence/m5/`.

The remaining owner action is to record the required two-minute walkthrough.
During recording:

1. Open `reports/powerbi/nzhem.pbip` without signing in.
2. Set `RepoRoot` locally to the absolute repository root before refreshing;
   do not commit that machine-specific value.
3. Show all five pages and the visible limitations on Method and quality.
4. Mention that pre-2018-10-16 event-time values are unsupported rather than
   zero and that the report presents the as-if-today exposure view.
5. Do not publish to Power BI Service or connect the project to a tenant.
