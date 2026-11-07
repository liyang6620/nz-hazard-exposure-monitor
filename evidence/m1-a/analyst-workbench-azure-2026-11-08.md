# Analyst Workbench Azure rollout, 8 Nov 2026 NZDT

## Deployment

- PR #63 merged after all checks passed. The production workflow dispatch was
  skipped because its repository deployment switch and encrypted environment
  are not configured. The owner-authorised local Azure session had MFA; the
  same documented Flex path was used from a clean `main` checkout.
- CI-built Linux Function packages were checked against their embedded Git
  SHA and the 1 GB package limit. The final Functions Core Tools deployment
  completed at 7 Nov 2026 11:34 UTC from `a72e817` (PRs #66 and #67 merged).
  The token-free review GET returned that exact `X-NZHEM-Build` SHA. All six
  triggers indexed: hourly housekeeping, event queue consumer, budget stop,
  map token, and review GET/POST.
- Function app settings after deployment had no base `AzureWebJobsStorage`
  connection string. `AzureWebJobsStorage__credential=managedidentity` and the
  host-account setting remained present. `HOUSEKEEPING_SCHEDULE` was
  `0 0 * * * *`; the timer has `run_on_startup=False`. Application Insights
  recorded zero extra housekeeping requests between 11:34 and 11:59 UTC.
- The static app was built with the separately scoped browser LINZ LDS tile
  variable and review API origin, then uploaded to `$web` while retaining
  runtime `data/` and approved briefings. PR #66 moved report attachments to
  `/report-assets/` because an ADLS directory object at `/workbench` prevented
  the route blob from being created. After all replacement attachments returned
  200, the obsolete six-file directory was removed and `/workbench` returned
  200. PR #67 made static deployment refresh all event deep links even when
  the data generation is unchanged.

## Public checks

- Site: https://stnzhem8495b7ca.z8.web.core.windows.net/
- `/`, `/history`, `/method`, `/about`, `/workbench`, and the Kaikōura detail
  deep link each returned HTTP 200. All 55 event routes in the published
  manifest returned 200. The detail page showed the "Open in Analyst
  Workbench" link; desktop and mobile navigation exposed the same page.
- Five public report PNGs and the PDF returned 200 with the expected media
  types. Downloaded copies matched the committed files byte-for-byte by
  SHA-256. Extracted PDF text had no local path, email address, GUID-shaped
  identifier, or secret variable name; the report images and site screenshots
  were visually reviewed for the same exclusions.
- Desktop and 390 px mobile Workbench views had no JavaScript page errors or
  horizontal overflow. After the next hourly run, "Last checked" showed
  8 Nov 2026 01:00 NZDT on desktop and mobile, matching the public heartbeat.
  The review API CORS preflight returned only the public site origin.
- `/briefings/index.json` and the approved Kaikōura briefing remained
  available after the static deployment.

## Screenshots

- [Workbench desktop](analyst-workbench-live-desktop.png)
- [Workbench mobile](analyst-workbench-live-mobile.png)
- [Home desktop](home-live-workbench-desktop.png)
- [Home mobile](home-live-workbench-mobile.png)
- [Kaikōura detail desktop](detail-live-workbench-desktop.png)
- [Kaikōura detail mobile](detail-live-workbench-mobile.png)

## Hourly gate

Application Insights recorded a successful `housekeeping` request starting
7 Nov 2026 12:00:00 UTC and lasting 14.7 seconds. Public
`data/housekeeping.json` advanced to 12:00:14 UTC, reported `status=success`,
and carried the deployed `a72e817` SHA. The Function was not run on startup;
the first post-deployment execution was the scheduled hour. The manifest kept
its prior generation because no source data changed, as the unchanged-data
publication rule requires.
