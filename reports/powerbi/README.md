# NZHEM Power BI report

This PBIP is the interactive Analyst Workbench for completed live assessments
and ten fixed historical replays. Live events use event-time buildings;
historical events use current buildings (as-if-today). Both use 2023 population.
The semantic model is a star schema with event, region, date and MMI-band
dimensions, exposure and event-summary facts, accumulation, validation, map and
local run-health facts. Relationships filter from dimensions to facts in one
direction. Numeric source columns and keys are hidden; every displayed number
uses a documented measure in `_Measures`. Implicit measures are discouraged.

The five pages are Event Overview, Event Comparison, Regional Exposure, Event
History and Data Health. MMI Threshold runs from 4 to 8, default 6. The Event
Overview map plots H3 resolution 6 centres by longitude and latitude in an
offline scatter visual; it does not use Azure Maps or a paid mapping service.
For live events, the map shows the epicentre only because the published live
feed has no regional H3 fact. Event Comparison is restricted to the ten replays.
The regional map plots accumulation centroids. Selecting an event or region
filters the related visuals. The regional share is blank with multiple events
selected because adding event exposures would overstate the share of stock.

## Refresh locally

Run `.\.venv\Scripts\python.exe scripts/build_powerbi_snapshot.py --azure`
from the repository root after an owner-assisted MFA `az login`. This reads
Azure gold and run data, plus the public ready-event feed, into the compact,
ignored `.local/data/powerbi/` snapshot. Without `--azure`, it builds from
local M3 gold Parquet and the LINZ reference export. The builder limits DuckDB to 512 MB,
uses one thread and checks the 20 GiB C-drive floor. Run
`python scripts/check_powerbi_snapshot.py` to reconcile MMI 6+ buildings and
population to all ten gold replay summaries and the ready live events and to
check region keys. See [the Workbench guide](../../docs/powerbi.md) for shared
terminology, the model diagram, DAX and Canterbury RLS instructions.

The source-controlled `RepoRoot` expression is deliberately relative. Run
`python scripts/prepare_powerbi_desktop.py` to create an ignored Desktop copy
under `.local/powerbi-desktop/` with the machine path set locally. Open its
`nzhem.pbip`, refresh, then use report view to inspect or export. Do not save
the machine path to `reports/powerbi/` and do not sign in or publish to Power BI
Service. `python scripts/check_pbip_portability.py` enforces this in CI.

## Interpretation

Buildings are attributed to the region and territorial authority that contains
the majority of current building outlines in each H3 resolution 8 cell. This
is a boundary approximation; `Outside mapped regions` is retained rather than
silently dropped. Accumulation counts repeated MMI 6+ exposure across the ten
events, not unique damaged buildings. Estimated MMI MAE is calculated from
valid station errors, weighted by station count. Data Health is an explicitly
labelled read-only Azure snapshot when built with `--azure`, not live telemetry. The report does
not contain insured values, loss estimates, or individual policy data.
