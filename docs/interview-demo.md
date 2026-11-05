# Five-minute product demonstration

Audience: catastrophe or exposure analysts, with hiring reviewers as a
secondary audience. Open the [public website](https://stnzhem8495b7ca.z8.web.core.windows.net/)
before starting. This walkthrough is read-only: do not open approval links,
change Azure resources, invoke a model or display credentials.

| Time | Screen and action | What to say |
|---|---|---|
| 0:00-0:45 | Homepage: point to the latest monitored event and recent-event strip. | "GeoNet events are polled hourly. Each assessment reports maximum MMI and buildings and people in MMI 6+ shaking. The first genuine Azure event was on the site 32 minutes 9 seconds after origin." |
| 0:45-1:45 | Open a recent assessed event. Show the epicentre, H3 cells, MMI legend and map text alternative. | "An official Shaking Layer is preferred. When it is unavailable, an in-range point-source estimate is labelled preliminary. An event with no damaging shaking has an explicit result instead of a pending chart." |
| 1:45-2:35 | On the same detail page, compare the MMI 5+ chart and regional table. | "These are screening exposure counts, not insured losses. The chart keeps damaging bands readable; the table omits empty regions and explains unmatched geography." |
| 2:35-3:35 | Open History, then the Kaikōura replay and its approved briefing. | "This replay applies today's 3,219,311 deduplicated buildings and 2023 population to historical shaking. Kaikōura shows 78,564 buildings and 83,276 people at MMI 6+. Its briefing appeared only after a person approved it." |
| 3:35-4:20 | Open Method. Point out the data versions and limitations. | "Population starts at SA1 and is allocated by building footprint. The point-source model has station MAE 1.049 MMI. Water cells and the Chatham Islands are excluded. These boundaries matter before using the numbers." |
| 4:20-5:00 | Open About and the repository README architecture diagram. | "The same core runs in local Docker Compose and Azure Functions. Azure publishes immutable JSON and GeoJSON generations for the public React site. The local and cloud replay hashes matched across 56 Parquet files. November actual cost reported on 4 Nov was NZD 0.535918, with billing delay." |

If the latest live event is outside model range or has no damaging shaking,
show that explicit status and use the historical Kaikōura page for the exposure
comparison. Do not imply that a historical replay describes 2016 building
stock. This written script is the M8 interview demonstration deliverable; no
video is required.
