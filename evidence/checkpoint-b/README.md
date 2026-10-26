# Checkpoint B: MG, M5 and M6 completion

Date: 2026-10-26 (Pacific/Auckland)

MG, M5 and M6 are complete and accepted. This summary supersedes the earlier
progress review.

## 1. Completed work

### MG

- Exported and validated the three-layer File Geodatabase in EPSG:2193.
- Cross-validated 3,219,311 Kaikoura building points against the production
  H3-centre method.
- Published the private `event_exposure_r6` hosted feature layer with 4,011
  features.
- Verified one `applyEdits` incremental update without changing item ID
  `ce9c69b085584965a236d0c6fdfb7ebc`.
- Verified Static Maps with two REST calls and one Esri MCP
  `map_with_overlay` call.
- Documented that the publisher credential is server-side only and may operate
  only on this project's content and approved Basemaps/Static Maps services.

### M5

- Delivered the PBIP semantic model and five report pages.
- Refreshed the model from the real M3 Parquet outputs in Power BI Desktop
  without signing in or publishing.
- Captured all five pages and exported a five-page PDF.
- Kept the required limitations visible in Desktop and the PDF.
- Added a CI portability check that rejects machine-local absolute paths in
  committed PBIP sources.

### M6

- Implemented four DuckDB-backed tools and their JSON schemas, briefing draft
  rendering, numeric-fidelity validation and retry.
- Implemented one-time HMAC approval with confirmation-only GET and mutating
  POST, including tamper, expiry, replay, rejection and timeout handling.
- Published approved briefings to the local static site and delivered approval
  mail through local Mailpit.
- Delivered the local project MCP server.
- Evaluated all 10 fixed events with 10/10 numeric-fidelity passes (100%).
- Enforced per-briefing and monthly token limits and recorded cost without
  logging credentials.

## 2. Pull requests and CI

The implementation PRs are merged and their CI checks passed, including:

- [PR #27: complete M6 briefing agent and approval workflow](https://github.com/liyang6620/nz-hazard-exposure-monitor/pull/27)
- [PR #28: publish ArcGIS layer and attach static maps](https://github.com/liyang6620/nz-hazard-exposure-monitor/pull/28)

Earlier M5 and MG evidence PRs are retained in repository history. Detailed
evidence is under `evidence/mg/`, `evidence/m5/` and `evidence/m6/`.

## 3. Key measurements

| Area | Measurement |
|---|---:|
| Hosted feature count | 4,011 |
| ArcGIS portal storage | 3,513,272 bytes |
| Hosted item size | 3,080,192 bytes |
| Incremental edit usage | 1 operation / 849 bytes |
| Monthly feature bandwidth observed | 32,941 bytes |
| Static Map calls for MG validation | 3 |
| M6 events evaluated | 10 |
| M6 numeric fidelity | 100% |
| Known cumulative OpenAI cost | US$0.01287375 |
| Budget-accounted OpenAI cost | US$0.02307375 |

ArcGIS storage and editing remained within the 125 MB project limits, and
Static Map use remained within the maximum of 200 calls per month.

## 4. Remaining work

1. Repository owner records the two-minute Power BI walkthrough video.
2. M7 Snowflake work awaits project-manager scheduling.
3. Azure deployment awaits Microsoft account recovery.

No Azure or Snowflake operation was performed for this checkpoint.
