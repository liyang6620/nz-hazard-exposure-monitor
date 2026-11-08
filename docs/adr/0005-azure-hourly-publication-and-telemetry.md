# ADR 0005: Azure hourly publication and telemetry

Status: accepted operational decision, 4 November 2026 NZDT.

## Context

Flex Consumption can wake the Function host shortly before each hourly timer
tick. With `run_on_startup=True`, this produced an extra successful
`housekeeping` request near :58 UTC as well as the scheduled request at the
top of the hour. Each pass can poll GeoNet and write a new public generation,
increasing transactions without improving the stated hourly schedule.

The first deployment attempts used ZIP deployment, reported trigger-sync
problems, and left hourly publication stopped despite a Running Function App.
Later Core Tools deployment and managed-identity host-storage settings restored
the timer. Application Insights 20% sampling then omitted successful hourly
requests, making the missing-housekeeping log alert unreliable.

## Decision

- Set the Azure timer's `run_on_startup` to `False`. Keep `0 0 * * * *`,
  monitored execution, GeoNet `updatedafter` catch-up and the 60-minute
  processing timeout. The next scheduled run catches up after a host restart.
- Deploy an immutable CI-built package with Functions Core Tools, check the
  deployed SHA and all six bindings, and preserve the host's
  `AzureWebJobsStorage__credential=managedidentity` setting. The base
  `AzureWebJobsStorage` connection string must remain absent.
- Treat the deployment as complete only after the next scheduled request is
  recorded and `/data/housekeeping.json` advances with the deployed SHA.
  `/data/manifest.json` advances only when public data changes. A Running
  status or successful package upload alone is insufficient.
- Keep Request and Exception telemetry unsampled at the Function host. The
  approved fallback sets Application Insights sampling to 100% while retaining
  its 0.1 GB daily cap. Compare two consecutive scheduled requests with the
  hourly public heartbeat before accepting the execution alert.

## Consequences

An idle-host wakeup no longer creates an extra poll. After a long outage, a
catch-up run may wait until the next UTC hour; the one-hour publication target
is measured from each real event and must be reported from observed runs,
never inferred from the cron expression. The first observed Azure event took
32 minutes 9 seconds from origin to public publication.

The missing-housekeeping alert's older Fired instances resolved once hourly
requests appeared in telemetry. Action Group email delivery remains unverified
despite a separate Function-failure alert firing and resolving. The NZD 1
drill budget was removed before natural trigger, so that stop path remains
unverified. Actual telemetry cost must be read from Cost Management rather
than inferred from the sampling percentage.
