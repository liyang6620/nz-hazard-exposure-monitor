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
6. Set the GitHub encrypted secrets and enablement variables listed in the
   workflow files. Never print
   their values in an issue, PR comment, log, screenshot, or repository file.
   `AZURE_GITHUB_PRINCIPAL_ID` is the bootstrap output used by production plans.
7. Merge the PR only after CI passes. The main-branch deployment workflow builds
   the locked Function package and React application, deploys both and checks
   the startup `housekeeping` run. It preserves runtime `data/` and `briefings/`
   in `$web`. The Function publishes a new data generation after startup and
   each hourly run, and after queue-triggered event assessment.

The 31 Oct replan changes resources and permissions; steps 2-7 are paused until
the project manager reviews the diff in `evidence/m1-a/replan-2026-10-31.md`.

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

After deployment, first confirm that Cost Management is calculating actual
usage on Azure for Students. Submit a new plan that temporarily lowers only
`budget-killswitch` to the approved test amount. After the real budget triggers,
restore NZD 5 through another approved plan and perform the recovery procedure.

The Azure for Students spending limit remains enabled as the final backstop. Do
not upgrade the subscription or attach a payment method.
