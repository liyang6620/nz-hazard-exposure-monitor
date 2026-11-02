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
- The separately approved `owner_runs_recovery` plan was applied after the
  saved SHA-256 and MFA claim were rechecked. It added only the approved
  `runs`-table Storage Table Data Contributor role. A direct authenticated
  budget webhook drill returned HTTP 202; the `control / budget-killswitch`
  entity became enabled and ARM reported the Function `Stopped`. The webhook's
  synchronous ACS send completed without error. The owner recovery procedure
  deleted the switch and restarted the Function; ARM now reports `Running` and
  the switch is absent. Final mailbox delivery was not independently checked.

## Open acceptance items

- Create an Azure pending briefing, deliver its approval email, and have the
  repository owner perform GET confirmation then POST approval. Verify website
  publication and rejection of altered, expired and reused links. The existing
  Azure host exposes review routes but no cloud draft command yet; this is not
  equivalent to the completed local Mailpit approval test.
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
  availability problem. This remains a blocker for reliable browser review.
- The first Cost Management month-to-date query returned zero rows; a
  several-day actual-spend reading is not yet possible.
  Keep the student subscription spending limit enabled; do not upgrade or add a
  payment method.
- Azure is not the ArcGIS publisher yet. Both Azure and local
  `ARCGIS_PUBLISHER_ENABLED` remain false until Azure acceptance passes.

The Azure site is available at
<https://stnzhem8495b7ca.z8.web.core.windows.net/>. These observations are
deployment progress, not final M1-A acceptance.
