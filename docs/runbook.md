# Operations runbook

## Approval rule

Terraform plan is read-only and may be run by the implementer. Every apply,
Azure resource-provider registration, resource creation, paid API call, and
state migration requires the project manager's approval relayed by the owner.

## M1 rollout order

1. Review the seven missing namespaces in `infra/providers`; register only the
   approved set. `Microsoft.Insights` is already registered.
2. Save, review and apply `infra/bootstrap`. It creates both resource groups,
   state storage and the GitHub UAMI with PR/main federated credentials. Keep
   its local state encrypted and backed up outside GitHub.
3. Initialize `infra/guardrails` against the new `guardrails.tfstate` backend
   key and apply only its approved new-subscription plan. Never migrate the old
   subscription state archived under ignored `tmp/`.
4. Initialize `infra/terraform` against `production.tfstate`. Save and review
   the complete production plan before apply.
5. After the approved production apply, stage the approved reference export and
   M3 gold Parquet with `scripts/stage_azure_data.py --account-name <account>
   --execute`. Run it without `--execute` first to see the bounded file count
   and byte total. The script uploads only Parquet to the private curated and
   gold containers; it never uploads raw source ZIPs or DuckDB databases.
   Before deploying the Function package, remove any platform-injected base
   `AzureWebJobsStorage` connection string. The host storage account disables
   shared keys; the Function uses the configured `AzureWebJobsStorage__accountName`
   and `AzureWebJobsStorage__credential=managedidentity` settings instead. The
   deployment workflow performs this check and removal automatically.
6. Set the GitHub encrypted secrets and enablement variables listed in the
   workflow files. Never print
   their values in an issue, PR comment, log, screenshot, or repository file.
   `AZURE_GITHUB_PRINCIPAL_ID` is the bootstrap output used by production plans.
7. Merge the PR only after CI passes. The main-branch deployment workflow builds
   the locked Function package and React application, deploys both and checks
   the startup `housekeeping` run. It preserves runtime `data/` and `briefings/`
   in `$web`. The Function publishes a new data generation after startup and
   each hourly run, and after queue-triggered event assessment.

The 31 Oct replan was approved and applied; see
`evidence/m1-a/azure-acceptance-2026-11-02.md` for verified rollout steps and
remaining acceptance checks. Do not use the original 50-create production plan
against the now-populated remote state.

## Pre-upgrade stop drill

1. Record current Cost Management, Function status, and `runs` switch state.
2. In Azure Monitor, use **Test action group** on `ag-nzhem-budget-stop` with the
   common alert schema. This test is a state-changing operation and is run only
   inside the approved drill window.
3. Verify a request with a missing or wrong random webhook token is rejected
   before any storage, email or ARM call. Then verify the Action Group test
   request enables the
   `control / budget-killswitch` entity, records the stop run, sends the ACS
   email, and stops the Function App in ARM.
   The owner must first have the separately approved `runs`-table recovery role;
   subscription Owner alone cannot delete a Table entity with shared keys off.
4. Capture screenshots and timestamps without subscription IDs, tenant IDs, or
   personal email addresses.

## Recover after a budget stop

Recovery is owner-only and starts only after the cost cause is understood.

```bash
az storage entity delete \
  --account-name <storage-account> \
  --table-name runs \
  --partition-key control \
  --row-key budget-killswitch \
  --auth-mode login

az functionapp start \
  --resource-group rg-nzhem-prod \
  --name <function-app>
```

Confirm that a new successful `housekeeping` row appears and that the metric
alert is healthy. Deleting the switch entity is deliberate: a missing entity is
the only disabled state and avoids storing the string `"false"` as a truthy
Table value.

## Live budget drill

For the approved Azure for Students drill, create an independent temporary
NZD 1 monthly subscription budget bound to the existing budget-stop Action
Group. Its Terraform root must plan exactly one new budget and no changes to
the permanent budgets. Cost Management may report usage with a delay; wait for
the actual amount to cross NZD 1 and record the Azure budget notification,
Action Group delivery, webhook receipt, durable switch and ARM stop in order.
After owner-operated recovery, remove only this temporary budget with a plan
showing one deletion. If Azure rejects the budget or never delivers an alert,
record the failure without claiming the end-to-end path passed.

The Azure for Students spending limit remains enabled as the final backstop. Do
not upgrade the subscription or attach a payment method.

## Event replay and catch-up

The Azure timer runs at `0 0 * * * *` (UTC cron, once per hour). At startup,
GeoNet FDSN `updatedafter` catches up changes made while the host was offline.
Check the `runs` table for successful `housekeeping` rows, then read the public
`data/manifest.json`; its generation must advance after a run. A new event may
be `ready` or `outside_model_range`, but must not remain `processing` beyond
the 60-minute limit. Never infer completion from an administrator invocation's
HTTP 202 alone.

For a manual catch-up, invoke the existing `housekeeping` function through the
Azure Functions administrator endpoint with a host master key retrieved only
into process memory. Do not paste the key, URL query tokens or response bodies
into a ticket or terminal transcript. Check the resulting `runs` row and
manifest. Repeating catch-up should not create duplicate event IDs or replace
terminal results when GeoNet has no newer revision.

The ten fixed historical events can be rebuilt locally from the licensed raw
shaking files and the approved reference export:

```powershell
$env:PYTHONPATH = 'src'
.venv\Scripts\python.exe scripts/replay_historical_events.py `
  --output-root tmp/weekly-rebuild/gold `
  --evidence-root tmp/weekly-rebuild/evidence
```

Use a fresh ignored output directory. Keep `DUCKDB_MEMORY_LIMIT_MB=512`,
`REFERENCE_MAX_RSS_MB=768` and `REFERENCE_MIN_FREE_DISK_GB=20` or stricter.
Compare rebuilt Parquet hashes with the approved gold files before replacing
anything. A 2 November rehearsal matched all 37 Parquet files without
overwriting the approved output.

## Poison messages

The `events` queue trigger uses plain JSON, one message per batch,
`maxDequeueCount=3` and a one-minute visibility timeout. After three failed
deliveries, the Functions queue extension sends the message to `events-poison`.
Inspect the poison count and message with a narrowly scoped Queue Data role;
never paste its raw payload into public evidence. Diagnose the schema or
downstream failure, repair the processor, then requeue only verified event
payloads. Keep the original poison message until a successful terminal event
state and site publication are confirmed. The malformed-message cloud drill
remains unverified because the signed-in owner lacks Queue Data access.

## Rollback and backup

Before deployment, keep the last CI-built Function ZIP and Vite `dist` artifact
and record their commit. On an application regression, redeploy those exact
artifacts, verify all six functions index, check the timer and queue trigger,
and confirm the public manifest and direct-link routes. Do not roll back the
manifest to a generation that lacks an event already published. Runtime data
in `$web/data/` and approved `briefings/` is preserved by the static deploy
script.

Back up each Terraform root's state separately with `terraform state pull` to
an encrypted, ignored owner-only location; state contains credentials. Validate
the backup parses as JSON and record its SHA-256 and resource count outside
the public repository. Do not commit or email the state. The production-state
read-only backup rehearsal on 2 November contained 39 resource blocks; no
state restore or resource mutation was performed.

## Move to another subscription

Treat a replacement subscription as a fresh deployment. Obtain project-manager
approval for its provider registrations and each bootstrap, guardrails and
production plan. Do not import the student-subscription state into it. Use
new backend coordinates and a new identity/OIDC configuration, then upload
only approved Parquet and frontend artifacts. Run `scripts/e2e_replay.py` with
`--azure-account-name` to compare every curated/gold object to local source,
and verify direct website routes, mailbox approval, event processing, budget
stop and recovery before switching traffic or ArcGIS publication. The
non-mutating migration rehearsal verified the existing 56-file digest and
fixed routes; an actual second subscription was not created.

## Review-link availability

On Flex Consumption, the first browser GET may show "The service is
unavailable" while a host instance starts. Refresh the GET confirmation page
after a short wait; an unsuccessful GET never approves a briefing. Confirm the
briefing title and action, then click the POST button once. If the response is
unclear, check the public briefing index before trying again. A used, expired
or modified link shows a friendly HTML unavailable page. Do not automate POST
retries or weaken the one-time HMAC decision check.

## ArcGIS publisher handover

The private `event_exposure_r6` hosted item is the only write target. The
Azure hourly timer publishes only ready, recent monitoring events from the
already published website generation. It matches `event_id` and `h3_r6`, uses
50-feature `applyEdits` batches with rollback enabled, and records the source
GeoJSON digest in the `runs` table after successful edits. A failed batch is
safe to retry because the next run queries current object IDs. It rejects an
unexpected item URL, public sharing, changed layer schema, duplicate cells,
oversized event payloads, storage at 125 MiB, or edits exceeding the 125 MiB
monthly local ledger. Check the portal's account-wide monthly usage as well:
the local ledger cannot include edits made outside this application.

Keep both deployments' `ARCGIS_PUBLISHER_ENABLED` false while handing over.
First generate a Terraform plan with only the vault-scoped temporary
`owner_arcgis_key_write` role, and apply it under the existing approval. The
owner then adds a Key Vault secret named `arcgis-publisher-key` through the
Azure portal, pasting the existing server-side key directly into the secret
form. Do not place the key in a shell argument, application setting, browser
bundle, issue, screenshot or log. Disable the temporary role and apply a plan
containing only its deletion. The Function's existing `Key Vault Secrets User`
role remains. Verify the Function can read the secret without printing it,
then enable only the Azure publisher through a reviewed application-setting
plan. Confirm the hosted item ID is unchanged, read back feature count and
storage use, compare the monthly feature-edit allowance, and verify the local
publisher is still off. If the ArcGIS service rejects any edit, leave Azure
publishing off and record the error code for review.
