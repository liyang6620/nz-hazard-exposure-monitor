# Azure acceptance progress, 2 Nov 2026 NZDT

PR #31 remains open. The Azure for Students deployment is running in Australia
East. Bootstrap and all three Guardrails budgets converged before production.
The project manager approved the production recovery plan after the partial
apply; it completed with four existing Table imports, 17 creates, zero changes
and zero destroys. See [the recovery record](production-recovery-2026-11-02.md).

## Verified

- The approved reference export and M3 gold outputs were uploaded: 56 Parquet
  files, 216,680,598 bytes. `scripts/e2e_replay.py` streamed each cloud Blob in
  bounded chunks and matched its SHA-256 and byte count to the local file. The
  aggregate file digest is
  `adcfc2ea9a29a5b22ef0006514b9ea1cdce23dc41c1b591eb4a06147e91eea10`.
  The existing Christchurch 2011 and Kaikōura replay fixture hashes also ran.
- The Function host loaded all six expected functions, including the hourly
  `housekeeping` timer and `process_event` queue trigger. Application Insights
  recorded successful `process_event` executions. Queue message encoding is
  `None`, matching the adapter's plain JSON messages.
- A manually triggered housekeeping recovery pass cleared stranded work. The
  published generation at 12:04 UTC on 1 November contained 47 events: 24
  `ready`, 23 `outside_model_range`, zero `processing`. The manual trigger is
  not evidence of an unattended hourly run.
- The public site returns HTTP 200 for `/`, `/history`, `/method`, `/about` and
  `/events/2016p858000`. Browser navigation rendered those pages; the home
  page displayed the real GeoNet station waveform with zero console errors.
  [Desktop home](azure-home-desktop.png), [mobile home](azure-home-mobile.png),
  [desktop detail](azure-detail-desktop.png), and
  [mobile detail](azure-detail-mobile.png) were captured after the backlog
  reached terminal states.
- An ACS Azure-managed-domain email send to the configured recipient returned
  `Succeeded`. No address, connection string or message ID is in this record.
- Missing budget webhook credentials returned HTTP 403, an invalid approval
  token returned HTTP 400 in a successful probe, and the disabled `map-token`
  route returned HTTP 404.
- PR #31 CI passed its frontend, Python/dbt, local deployment, Terraform,
  package-size and public-identifier checks after the queue and waveform fixes.
- The 11:00 and 12:00 NZDT hourly `housekeeping` rows on 2 November both show
  `success`; the public manifest advanced to generation
  `20261101T230000282475Z` at 12:00 NZDT. These scheduled rows are separate
  from the 10:58 and 11:58 startup/recovery runs.
- GeoNet's public quake API independently returned event `2026p824047`,
  magnitude 4.990952572393716, origin `2026-11-01T21:26:49.605Z` (10:26:49
  NZDT, 2 November). It occurred after the cloud deployment was active. The
  published manifest records `ready`, publication at 10:58:57 NZDT and
  `elapsed_seconds: 1929` (32 minutes 9 seconds), meeting the one-hour target.
  Its detail summary is a preliminary estimate with maximum MMI 0.8 and no
  damaging shaking. The public manifest and GeoNet event are independently
  retrievable; this is an actual new event, not an injected replay.
  The updated site rendered this observed processing record in both the
  [desktop homepage](azure-home-realtime-desktop.png) and
  [mobile homepage](azure-home-realtime-mobile.png).
- The separately approved `owner_runs_recovery` plan was applied after the
  saved SHA-256 and MFA claim were rechecked. It added only the approved
  `runs`-table Storage Table Data Contributor role. A direct authenticated
  budget webhook drill returned HTTP 202; the `control / budget-killswitch`
  entity became enabled and ARM reported the Function `Stopped`. The webhook's
  synchronous ACS send completed without error. The owner recovery procedure
  deleted the switch and restarted the Function; ARM now reports `Running` and
  the switch is absent. Final mailbox delivery was not independently checked.
- A CI-verified application-only update was deployed after the stop drill.
  The Function still indexes the same six triggers, and its administrator
  invocation created a Kaikōura review draft in the private `briefings`
  container at 13:19 NZDT. The draft reads the summary chosen by the public
  manifest and passed the local Python tests, including duplicate-request,
  monthly-limit and numeric-fidelity guards. A separate read of the private
  draft matched its headline and every key figure to the currently published
  `summary.json`. The repository owner received the ACS email, opened its GET
  confirmation page and clicked the POST approval button personally. The first
  browser request showed "The service is unavailable"; refreshing succeeded.
  The approved HTML and its index entry are now public at
  `/briefings/2016p858000.html`. A newly signed link for that used briefing
  returned HTTP 400 to both GET and POST. No script performed the approval.
- A separate `2026p824047-r1` test draft remains pending. Two read-only GET
  requests returned its confirmation page with HTTP 200, so GET did not consume
  its decision. Signed expired and HMAC-modified test links both returned
  HTTP 400 with the friendly HTML "Review link unavailable" page. The actual
  reject POST is reserved for the repository owner; its test link is not in
  this evidence.
- After the application update, direct HTTP requests returned 200 for `/`,
  `/history`, `/method`, `/about`, the Kaikōura detail route and the new GeoNet
  event detail route. A browser loaded 24 LINZ LDS tiles with HTTP 200 and no
  OSM fallback; [the detail screenshot](azure-linz-map-detail.png) shows the
  LINZ attribution and the approved briefing. Cost Management returned an
  early month-to-date actual cost of **NZD 0.277** on 2 November. This is not
  a several-day cost result.
- The hourly schedule is `0 0 * * * *`. Successful unattended 11:00, 12:00
  and 13:00 NZDT runs were observed. A temporary `0 */5 * * * *` setting
  produced a successful 13:40 NZDT timer run and manifest publication; it was
  restored and read back as `0 0 * * * *`. Two subsequent administrator-triggered
  housekeeping runs at 13:45 and 13:46 NZDT each enqueued zero events. The
  published 49-event list contained 49 unique IDs and one ready record for the
  new GeoNet event.
- `scripts/e2e_replay.py` compared the Christchurch and Kaikōura real-event
  fixtures, then streamed all 56 Azure curated/gold Parquet objects against
  local files: 216,680,598 bytes, aggregate SHA-256
  `adcfc2ea9a29a5b22ef0006514b9ea1cdce23dc41c1b591eb4a06147e91eea10`.
  A separate weekly-rebuild rehearsal wrote only to ignored `tmp/` storage;
  all 37 rebuilt Parquet files exactly matched the existing gold hashes. The
  existing gold was not overwritten. C-drive free space after the run exceeded
  44 GiB.
- A read-only remote Terraform state backup was stored under ignored `tmp/`:
  39 resource blocks, 151,107 bytes, valid JSON, SHA-256
  `167C7F91203DFD2657F5C5ED7FFCFF5D6DBFB866A50A694C174E40435E2E53B0`.
  It contains secrets and must never be committed. Migration preflight repeated
  the 56-file parity check and verified fixed website routes without creating
  another subscription or resource.

## Open acceptance items

- Have the repository owner reject the separate pending test briefing through
  its emailed GET confirmation and POST button. Do not script a human decision.
- A malformed queue-message poison drill could not run: the owner login has
  no Queue Data role on the data account, and shared-key access is disabled.
  A new assignment would change the approved permission plan. No queue message
  was injected and gold was not changed for this proposed test.
- Azure rejected its built-in Action Group budget test with HTTP 409
  `Free subscription not supported`. Therefore the Action Group notification
  delivery itself is **not verified** on Azure for Students. The direct webhook
  drill verifies the downstream stop and recovery path only. Do not describe
  it as a complete Action Group drill.
- The Function HTTP entrance is still intermittent. Six invalid approval-link
  GET probes returned three correct HTTP 400 responses (6.8, 15.3 and 15.7
  seconds) and three no-response timeouts at 45 seconds. Four IPv4 `curl`
  probes against the one resolved address returned one HTTP 400 in 0.19
  seconds and three no-response timeouts at 15 seconds, after successful TLS.
  Application Insights recorded fast successful function executions but no
  invocation for the timed-out requests, pointing to an upstream or host
  availability problem. The owner also saw "The service is unavailable" on
  the first real approval-link open, then succeeded after refresh. Flex
  Consumption cold start is plausible but not proven; the runbook instructs
  retrying GET and never auto-submitting POST. This remains an availability
  concern for time-sensitive review links.
- A several-day actual-spend reading is not yet possible.
  Keep the student subscription spending limit enabled; do not upgrade or add a
  payment method.
- Azure is not the ArcGIS publisher yet. The current Azure adapter has no
  hosted-layer incremental publisher, and the owner login cannot write the
  server-only ArcGIS key into Key Vault. The necessary code, least-privilege
  credential-write plan and quota test need review before switching it on.
  Both Azure and local `ARCGIS_PUBLISHER_ENABLED` remain false.

The Azure site is available at
<https://stnzhem8495b7ca.z8.web.core.windows.net/>. These observations are
deployment progress, not final M1-A acceptance.
