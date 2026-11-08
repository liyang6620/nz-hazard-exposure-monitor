# Five-minute interview demonstration

Audience: catastrophe and exposure analysts, then hiring reviewers. Open the
[public website](https://stnzhem8495b7ca.z8.web.core.windows.net/) and the
[Analyst Workbench](https://stnzhem8495b7ca.z8.web.core.windows.net/workbench)
before starting. Use public, read-only pages; do not display credentials or
approval links. This written script replaces the cancelled video deliverable.

| Time | Show | Say |
| --- | --- | --- |
| 0:00-0:45 | Home: latest monitored event, recent strip, Last checked | "GeoNet is polled hourly. The first genuine Azure event reached the site 32 minutes 9 seconds after origin. Last checked comes from the hourly heartbeat even when the data manifest does not change." |
| 0:45-1:35 | A live event detail: map, epicentre, MMI source, summary | "Official shaking is preferred. Otherwise an in-range point-source estimate is labelled preliminary; out-of-range and no-damaging-shaking results are explicit. Buildings and people at MMI 6+ are exposure, not loss." |
| 1:35-2:20 | Historical Kaikōura detail and approved briefing | "Ten fixed events replay historical shaking over current buildings and 2023 population. Kaikōura has 78,564 buildings and 83,276 people at MMI 6+ in that as-if-today scenario. The numeric heading is deterministic; a human approved the prose before publication." |
| 2:20-3:20 | Analyst Workbench, then five-page PDF | "The website supports a first-hour decision; the Desktop report supports threshold, regional-repeat, comparison and data-health questions. The public PDF is a dated snapshot. A Canterbury RLS role was checked in Desktop; there is no Power BI Service login." |
| 3:20-4:15 | Method and Data Health | "The point-source station MAE is 1.049 MMI. SA1 population allocation, water-cell exclusions and missing Chatham Islands coverage are disclosed. The 11-hour 2 Nov publication outage was detected because the manifest stopped updating while the Function still said Running; we now gate releases on the next real timer run and heartbeat." |
| 4:15-5:00 | README architecture and platform comparison | "Local Docker and Azure share the core, and 56 Parquet objects matched by hash. Snowflake reproduced the dbt marts but took 36.1 seconds for the full rebuild versus 22.1 on bounded local DuckDB. Azure Cost Management had returned NZD 1.141149 month-to-date rows on 9 Nov; a stable daily rate is not yet verified." |

If the latest event has no damaging shaking, use that clear state rather than
an empty chart, then open Kaikōura for the exposure example. Never describe a
historical replay as a 2016 building inventory.

## Common follow-up questions

| Question | Answer points |
| --- | --- |
| Why DuckDB rather than Snowflake in production? | The approved curated/gold volume fits one thread and 512 MB. In the controlled trial, local full and single-event dbt runs were faster; Snowflake adds a separately metered warehouse and trial expiry. Strict row, MMI and aggregate parity passed. |
| How do you keep AI from inventing numbers? | Titles and key figures come directly from the event summary. The model writes only short situation and check text; each numeric mention must match a named metric and value. Unknown regions, leaked field names and decimal people are rejected. GET previews are read-only and approval requires a one-time human POST. |
| How was the 11-hour outage found? | The public manifest froze after a legacy Flex ZIP deployment even though ARM said Running. App Insights showed the timer listener failing to authenticate to host storage. The runbook now checks the served SHA, indexed triggers, managed-identity settings and the next scheduled heartbeat; unchanged data does not force a new manifest. |
| What caused the Power BI regional percentage regression? | A visual filter hiding zero rows also shrank the building-stock denominator. The DAX measure now removes visual row filters, then reapplies the intended region/district context. The total matches national share, and Canterbury RLS retains its regional denominator. |
| What remains unverified? | A clean physical-computer install, a complete stable billing period under US$3/month, natural budget alert to stop delivery, GitHub OIDC deployment, and Snowflake per-run metered credits. These are labelled as gaps in the final checklist. |
