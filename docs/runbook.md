# Operations runbook

## Approval rule

Terraform plan is read-only and may be run by the implementer. Every apply,
Azure resource-provider registration, resource creation, paid API call, and
state migration requires the project manager's approval relayed by the owner.

## M1 rollout order

1. Save and review the `infra/providers` plan. Import already registered
   namespaces into that root; register only approved missing namespaces.
2. Save, review and apply `infra/bootstrap`. Keep its local state encrypted and
   backed up outside GitHub.
3. Initialize `infra/identity` against `identity.tfstate`, then save, review and
   apply its plan.
4. Pass identity outputs to `infra/terraform` through untracked environment
   variables. Save and review the complete production plan before apply.
5. Set the GitHub encrypted secrets listed in the workflow files. Never print
   their values in an issue, PR comment, log, screenshot, or repository file.
6. Initialize `infra/guardrails` with `-migrate-state` only after the migration
   has been approved. Confirm a subsequent guardrails plan reports no changes.
7. Merge the PR only after CI passes. The main-branch deployment workflow builds
   the locked package, deploys it and checks the startup `housekeeping` run.

## Pre-upgrade stop drill

1. Record current Cost Management, Function status, and `runs` switch state.
2. In Azure Monitor, use **Test action group** on `ag-nzhem-budget-stop` with the
   common alert schema. This test is a state-changing operation and is run only
   inside the approved drill window.
3. Verify the request was accepted by Easy Auth, the `control / budget-killswitch`
   entity is enabled, the `budget_stop_switch` run record exists, the ACS email
   arrived, and ARM reports the Function App as stopped.
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

## Post-upgrade budget drill

Within seven days after PAYG upgrade, first confirm that Cost Management is
calculating actual usage. Submit a new plan that temporarily lowers only
`budget-killswitch` to the approved test amount. After the real budget triggers,
restore NZD 5 through another approved plan and perform the recovery procedure.

## Deadline gate

The PAYG upgrade deadline is 2026-11-18. If M1 is not clearly on track by
2026-11-14, report immediately and stop expanding scope while the project
manager decides whether to deploy only the minimum automatic-stop chain.
