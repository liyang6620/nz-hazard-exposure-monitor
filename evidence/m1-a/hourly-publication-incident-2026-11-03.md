# Hourly publication outage, 3 Nov 2026

## Timeline (UTC)

- 2 Nov 10:58:55: last successful `housekeeping completed` trace. Its
  publication wrote a manifest with `generated_at` 11:00:00.
- 2 Nov 12:12 and 12:19: two legacy ZIP deployment attempts were accepted
  by Azure's deployment endpoint, but CLI trigger synchronization failed.
- From 2 Nov 12:59: the timer listener repeatedly failed to start.
  Application Insights exceptions report host-storage HTTP 403
  `AuthenticationFailed`. No later successful housekeeping request was found.
- 2 Nov 22:16: the project manager detected the public manifest was stale
  by about 11 hours. Function resource state was nevertheless `Running`.
- 2 Nov 22:4x: read-only app-setting inspection found a plain
  `AzureWebJobsStorage` setting alongside the intended managed-identity
  `AzureWebJobsStorage__accountName` and `__credential` settings. The plain
  setting was removed; a follow-up read confirmed managed identity remains.
- 2 Nov 22:50: a saved Terraform plan containing one new missing-housekeeping
  log alert and no other changes was applied under the project manager's
  preapproval. It sends to the existing failure email Action Group.
- 2 Nov 23:00: the restored timer ran and published a new public manifest.
  The published list had 50 events and no `processing` entries.
- 2 Nov 23:45-23:47: Functions Core Tools published the prebuilt CI artifact.
  The Flex deployment pipeline and host health check succeeded, six functions
  were indexed, and an invalid review GET returned the expected build SHA
  `aefd39b2211530aba206a58e4cdb1ae5d58f0b12` in `X-NZHEM-Build`.
  The host storage setting remained managed identity only. The next scheduled
  timer run after this code deployment was then observed.
- 3 Nov 00:00: the first post-deployment hourly run completed successfully in
  the Azure `runs` table, and public `manifest.json` advanced to
  `2026-11-03T00:00:00Z`. The 23:58 startup catch-up had enqueued one event;
  the published 50-event list contained no `processing` entries.

## Cause and impact

The legacy `az functionapp deployment source config-zip` path reintroduced
the shared-key host-storage connection setting on Flex Consumption. The host
then tried to authenticate with that invalid value and could not start its
timer listener. Function `Running` and an enumerated function list did not
prove a running schedule. Public data and the recent-event list remained
frozen; any events arriving during the outage were not polled until catch-up.
No evidence indicates that gold reference data was changed.

## Repair and prevention

The invalid setting was removed, restoring the approved managed-identity host
storage configuration. Deployment code now uses Functions Core Tools, embeds a git
SHA in the package, and checks the served SHA, six indexed functions and the
next scheduled manifest publication. The runbook requires observing an actual
timer execution after every deployment. The new log alert evaluates a
two-hour successful-housekeeping count every 30 minutes; it covers the failure
mode where the Function resource still says Running. The first post-deployment
hourly publication is confirmed. Alert delivery remains untested. A further
monitoring issue was observed: Application Insights `AppRequests` returned
zero housekeeping rows for the successful 23:00 and 00:00 runs even though
the Azure `runs` table and public manifest agree they completed. The existing
Application Insights resource samples at 20%, so a two-hour log-count rule
may falsely report a missed run. This alert is deployed but must not be
called a reliable freshness monitor until telemetry capture is verified.
An independent public-manifest freshness check would require a separately
reviewed Azure resource or monitoring architecture change; none was added.
