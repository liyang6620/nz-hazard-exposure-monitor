# Checkpoint B: MG, M5 and M6 progress review

Date: 2026-10-25 (Pacific/Auckland)

This checkpoint is a progress review, not a claim that every MG and M6
acceptance criterion is complete. The local deliverables are reproducible, but
the hosted ArcGIS work is blocked by the current credential/network result and
the full M6 approval agent remains a separate implementation scope.

## 1. Completed work

### MG

- Exported a three-layer File Geodatabase and read it back with GDAL in
  EPSG:2193.
- Cross-validated 3,219,311 Kaikoura building points with exact
  GeoPandas/Shapely assignment against the production H3-centre method.
- Built a token-free ArcGIS Maps SDK page with 4,011 local MMI 5+ features.
- Documented NZTM2000/WGS84 axis-order handling.
- Performed read-only ArcGIS key checks without changing account state.

### M5

- Delivered a Desktop-generated PBIP semantic model and five report pages.
- Refreshed the model from the real M3 Parquet outputs in Power BI Desktop
  2.155.756.0 without signing in or publishing.
- Captured all five pages and exported a five-page PDF.
- Kept the three required limitations visible in Desktop and the PDF.
- Verified the model contains no key or machine-specific repository path.

### M6

- Enforced the existing per-briefing and monthly token limits.
- Ran six real `gpt-5-mini` evaluation calls with minimal reasoning and a
  450-token output ceiling.
- Recorded token usage and cost per call without logging the API key.
- Delivered the saved successful approval draft to local Mailpit without a
  further model call. SMTP and the Mailpit UI bind only to `127.0.0.1`.

## 2. Evidence

### Pull requests and CI

All listed pull requests are merged and all nine CI jobs passed:

- [PR #16: MG local GIS validation and token-free map](https://github.com/liyang6620/nz-hazard-exposure-monitor/pull/16)
- [PR #18: M5 PBIP model and five pages](https://github.com/liyang6620/nz-hazard-exposure-monitor/pull/18)
- [PR #19: MG read-only ArcGIS key check](https://github.com/liyang6620/nz-hazard-exposure-monitor/pull/19)
- [PR #20: budgeted M6 OpenAI evaluation](https://github.com/liyang6620/nz-hazard-exposure-monitor/pull/20)
- [PR #21: Power BI Desktop validation status](https://github.com/liyang6620/nz-hazard-exposure-monitor/pull/21)
- [PR #22: saved-draft Mailpit-only retry path](https://github.com/liyang6620/nz-hazard-exposure-monitor/pull/22)
- [PR #23: Power BI Desktop report and evidence](https://github.com/liyang6620/nz-hazard-exposure-monitor/pull/23)
- [PR #24: loopback Mailpit SMTP delivery](https://github.com/liyang6620/nz-hazard-exposure-monitor/pull/24)

### Key measurements

| Area | Measurement |
|---|---:|
| File Geodatabase layers | 3 |
| Kaikoura building points checked | 3,219,311 |
| MMI band agreement | 99.458% |
| Cross-validation peak RSS | 450.4 MB |
| Local map features | 4,011 |
| Local map payload | 2,195,110 bytes |
| Tracked Power BI semantic-model files | 16,489 bytes |
| Refreshed local Power BI cache | 51,530 bytes |
| Power BI PDF | 5 pages, 275,462 bytes |
| Real OpenAI calls | 6 |
| Actual OpenAI cost | US$0.0023465 |
| Mailpit messages delivered in final retry | 1 |
| Esri static-map calls | 0 |
| C-drive free after validation | 54.96 GB |

Detailed evidence is under `evidence/mg/`, `evidence/m5/` and `evidence/m6/`.
The latest local suite passed 69 tests at 84.88% coverage. PR #24 also passed
the Docker Compose deployment check.

## 3. Deviations from the plan

- MG uses approved token-free option B for the browser map. Hosted-layer
  publication was not substituted with local evidence.
- The Portal self endpoint accepted the ArcGIS key, but private owner-content
  read returned HTTP 403 and the basemap/static-map hosts were not resolvable
  from this environment. No write operation or permission change was attempted.
- M5 uses a local absolute `RepoRoot` parameter only during Desktop refresh;
  the committed value is the portable relative placeholder.
- The required two-minute Power BI walkthrough was left to the repository
  owner, as instructed.
- M6 evaluation used six paid calls rather than the ten-event target. It proves
  model access, limits and cost accounting, but it is not the complete agent
  evaluation.
- Mailpit proves local delivery only. It is not evidence for Azure
  Communication Services delivery.

## 4. Risks and unresolved items

- Hosted ArcGIS layer creation/update, stable item IDs, quota measurements,
  authenticated map access and Esri MCP static-map output are unverified.
- No ArcGIS billing-page screenshot is committed.
- M6 does not yet implement the four DuckDB-backed tools and their JSON
  schemas, draft rendering, numeric-fidelity retry, one-time HMAC approval
  state machine, reject/expiry handling, approved static-site publication or
  the local project MCP server.
- Consequently, the M6 trigger-to-approval-to-publication demonstration,
  approval security tests, ten-event 100% numeric-fidelity evaluation and MCP
  combination recording are outstanding.
- Azure deployment acceptance remains deferred under D30/D31. No Azure
  operation was performed in this stage.

## 5. Project-manager decisions required

1. Approve treating the current work as the local M5 completion plus partial
   MG/M6 checkpoint, with the full M6 agent delivered as a separate follow-up
   PR before M7/M8.
2. Decide whether and when to schedule an owner-observed, free-quota ArcGIS
   write test. It must not require pay-as-you-go, a payment method, broader key
   permissions or an account-setting change.
3. Confirm whether Esri MCP evidence should remain deferred until its host is
   reachable and static-map permission can be verified without paid services.
4. The owner still needs to record the required two-minute Power BI walkthrough.

## 6. Actual cost

- OpenAI API: **US$0.0023465**.
- Azure: **US$0.00**; no Azure action was performed.
- Esri: **US$0.00**; no metered ArcGIS or Esri MCP operation was performed.
- Power BI Desktop and local Docker validation: **US$0.00**.
