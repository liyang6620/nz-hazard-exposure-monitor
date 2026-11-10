# GitHub OIDC closeout, 10 Nov 2026 NZDT

The owner decided not to enable GitHub-hosted Azure planning or deployment.
GitHub Actions continues to run CI tests, checks and builds. Production
releases remain owner-run from a local MFA session.

## Verified boundary

- [PR #72](https://github.com/liyang6620/nz-hazard-exposure-monitor/pull/72)
  merged the environment-scoped identity definitions and workflow branch
  gates. Azure's retained federated subjects were subsequently corrected to
  GitHub's observed immutable-ID claim format. No subscription-level budget
  role was added.
- The owner-approved [read-only PR #73 plan run](https://github.com/liyang6620/nz-hazard-exposure-monitor/actions/runs/42729229579)
  passed OIDC login and private Terraform state initialization. It failed with
  HTTP 401 while refreshing the subscription-level `budget-killswitch`.
  Terraform did not complete the plan or apply anything.
- A local proposal plan showed only two creations: a custom role with
  `Microsoft.Consumption/budgets/read` and one assignment to the existing
  GitHub identity. The owner declined that permission expansion. The proposal
  was never applied, its saved local plan was deleted, and
  [PR #73](https://github.com/liyang6620/nz-hazard-exposure-monitor/pull/73)
  was closed without merge.
- Repository variables `AZURE_OIDC_ENABLED` and
  `AZURE_DEPLOYMENT_ENABLED` were each read back as `false`. The retained
  GitHub environments require owner review, and `production` allows only
  `main`. Encrypted environment values are not included in this record.
- With the retained subject format represented in bootstrap source and the
  GitHub numeric IDs passed as sensitive local inputs, a fresh read-only
  bootstrap plan reported zero changes. The IDs and plan output remain out of
  the repository.

## Owner-notified follow-ups

The owner will request the remaining checks separately: one week of actual
Azure cost, Snowflake usage before trial expiry, and an Esri billing-state
screenshot. None is marked as verified here, and no recurring task was added.
