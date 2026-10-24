# NZHEM Power BI project

`nzhem.pbip` is a source-controlled Power BI Project for the local M3
outputs. It contains one semantic model and five report pages:

1. Overview
2. Event explorer
3. Population exposure
4. Buildings and footprint
5. Method and quality

The model reads the local Parquet outputs under
`.local/data/curated/events/m3`. The `RepoRoot` M expression defaults to the
repository root relative to the project folder. If Power BI Desktop resolves
the project from another working directory, edit only that parameter to the
absolute repository path; do not copy secrets or data into this folder.

The five page definitions intentionally start with no visuals. The owner can
open the project, refresh, and add visuals from the documented fields without
changing the reproducible semantic model. The event-time fields are nullable
for events before 2018-10-16; use `event_time_status` when presenting them.

No Power BI Service connection, Microsoft login, publish action, or external
data source is configured in this project.
