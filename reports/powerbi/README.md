# NZHEM Power BI project

`nzhem.pbip` is a source-controlled Power BI Project for the local M3
outputs. It contains one semantic model and five report pages:

1. Overview
2. Event explorer
3. Population exposure
4. Buildings and footprint
5. Method and quality

The model reads the local Parquet outputs under
`.local/data/curated/events/m3`. Power Query requires an absolute path for
`File.Contents`, so before the first refresh edit the `RepoRoot` M expression
from its source-controlled relative placeholder to the absolute repository
root. Do not commit that local path or copy secrets or data into this folder.

Each page contains a table visual backed by the refreshed M3 Parquet outputs.
The Method and quality page also shows the required limitations. Event-time
fields are nullable for events before 2018-10-16; use `event_time_status` when
presenting them and never substitute zero for unsupported values.

Power BI Desktop 2.155.756.0 opened and refreshed the project successfully on
2026-10-25 after that local-only `RepoRoot` change. The acceptance screenshots and five-page PDF are under
`evidence/m5/`. The source-controlled semantic-model and report definitions
are under 1 MB; Power BI's local cache is excluded from Git.

No Power BI Service connection, Microsoft login, publish action, or external
data source is configured in this project.
