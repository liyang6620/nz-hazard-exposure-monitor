# Power BI Desktop owner checklist

The agent could not complete a Desktop interaction because Computer Use was
stopped by the physical Escape key. The repository PBIP assets are complete;
the owner should perform the remaining visual QA locally.

1. Open `reports/powerbi/nzhem.pbip` in Power BI Desktop.
2. If a Microsoft sign-in prompt appears, close it or choose Skip. Do not enter
   credentials.
3. If a license, privacy, or terms prompt appears, stop and record the exact
   prompt; do not accept it.
4. Check that the model loads both Parquet tables. If the path is unresolved,
   update the `RepoRoot` parameter to the repository root and refresh.
5. Refresh the model and check that all five pages are present.
6. Add or verify the five page layouts using the fields in `README.md` and the
   M3 evidence tables. Keep event-time `NULL` values visible as unsupported,
   never as zero.
7. Export a PDF and capture screenshots locally for the acceptance package.
8. Do not publish to Power BI Service, connect to a tenant, or record a video
   as part of this task.
