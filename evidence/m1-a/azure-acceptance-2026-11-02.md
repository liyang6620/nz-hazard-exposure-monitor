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

## Open acceptance items

- Observe one unattended hourly housekeeping run and its data publication.
- Wait for a genuine GeoNet M4.0+ event originating after cloud activation;
  record origin-to-publication time and compare it with the one-hour target.
- Create an Azure pending briefing, deliver its approval email, and have the
  repository owner perform GET confirmation then POST approval. Verify website
  publication and rejection of altered, expired and reused links. The existing
  Azure host exposes review routes but no cloud draft command yet; this is not
  equivalent to the completed local Mailpit approval test.
- Repeated HTTP probes of the Function host were inconsistent. Some returned
  the expected 400/403/404 in under two seconds; others completed TLS but timed
  out after 12-35 seconds without a response. This remains an availability
  concern for approval and budget-stop routes.
- Before testing the budget-stop Action Group, establish an owner-operated
  recovery path for the `runs` Table switch. The signed-in owner currently has
  no Table data role, so the documented `az storage entity delete --auth-mode
  login` recovery command is forbidden. A state-aware Terraform plan adds only
  `azurerm_role_assignment.owner_runs_recovery`: Storage Table Data Contributor
  on this one table to the repository owner, with no updates or deletes, no
  network change and no incremental monthly cost. The saved ignored plan is
  `tmp/m1-a-runs-recovery-role-review.tfplan`, SHA-256
  `10D07F7F9495AC143D8AAFB23AAFC05A67B365AD8293FBA4091080D089F5C9A8`.
  **This permission change requires project-manager approval before apply.**
  The stop drill has not run.
- The first Cost Management month-to-date query returned zero rows; a
  several-day actual-spend reading is not yet possible.
  Keep the student subscription spending limit enabled; do not upgrade or add a
  payment method.
- Azure is not the ArcGIS publisher yet. Both Azure and local
  `ARCGIS_PUBLISHER_ENABLED` remain false until Azure acceptance passes.

The Azure site is available at
<https://stnzhem8495b7ca.z8.web.core.windows.net/>. These observations are
deployment progress, not final M1-A acceptance.
