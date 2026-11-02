# Azure ArcGIS publisher preparation, 3 Nov 2026

PR #41 merged after all CI jobs passed. The CI Function package contained
the Azure ArcGIS adapter. The adapter remains disabled by default and no
ArcGIS write, Key Vault role grant, secret entry, or Terraform apply was
performed. Unit tests exercised incremental add/update/delete, 50-feature
batches, digest idempotency, failed edits and both quota guards. The full
Python suite passed 165 tests with 80.62% coverage. Terraform validation and
the public-identifier scan passed in CI.

The main-branch CI package was submitted twice to the existing Azure Function
App through the approved ZIP deployment path. Both CLI invocations reported a
trigger-sync/health-check failure after the ZIP endpoint accepted the package.
Azure listed completed deployment records, the Function App remained Running
and all six functions were enumerable. The public manifest still returned
HTTP 200. These observations do not establish that the new package is active;
no ArcGIS handover or publisher enable may rely on this deployment until a
separate verification succeeds.

Read-only application settings returned `HOUSEKEEPING_SCHEDULE = 0 0 * * * *`,
`POLL_INTERVAL_MINUTES = 60`, and `ARCGIS_PUBLISHER_ENABLED = false`. The
local publisher also remains disabled. Cost Management returned HTTP 429 on
3 Nov; no new daily actual charge was inferred. The NZD 1 budget's natural
Action Group notification has not been observed, and the Function App was
still Running at this check.

The repository owner's browser POST Reject for test briefing `2026p824047`
is separately verified against public data in
`rejected-test-briefing-2026-11-03.md`.
