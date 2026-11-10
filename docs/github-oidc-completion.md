# GitHub OIDC deployment decision

Status: **not enabled by owner decision**, 10 Nov 2026 NZDT.

GitHub Actions automatically runs tests, checks and builds. Azure releases
use an owner-authorised local MFA session and the Flex-supported Functions
Core Tools deployment path. Neither GitHub workflow performs production
planning or deployment: repository variables `AZURE_OIDC_ENABLED` and
`AZURE_DEPLOYMENT_ENABLED` are both `false`.

## What was prepared

- The existing GitHub user-assigned managed identity retains access to the
  private Terraform state container and approved production resource-group
  roles. It has no subscription-level budget-read role.
- The two Azure federated credentials retain environment-scoped subjects for
  `terraform-plan` and `production`. Their subjects match GitHub's observed
  default claim, including immutable owner and repository IDs. The IDs are
  sensitive Terraform inputs read from the GitHub API, not committed values.
- Both GitHub environments require the repository owner's review;
  `production` allows only `main`. Environment secrets are encrypted and their
  values are absent from repository files, logs and screenshots.

## Why it remains off

The owner-approved [read-only plan run](https://github.com/liyang6620/nz-hazard-exposure-monitor/actions/runs/42729229579)
passed Azure OIDC login and private state initialization. Terraform then
received HTTP 401 while refreshing the subscription-level
`budget-killswitch`. The plan did not complete or apply. A local MFA plan
with the same application inputs reported zero changes.

A local proposal for a custom role limited to
`Microsoft.Consumption/budgets/read` plus one assignment to the existing
GitHub identity showed two creations, zero updates and zero deletions. The
owner decided not to expand subscription-level permissions. That proposal
was **never applied** and its saved plan file was deleted. [PR #73](https://github.com/liyang6620/nz-hazard-exposure-monitor/pull/73)
was closed without merge. No alternative plan that skips budget refresh is
accepted as proof of a complete Terraform plan.

The corrected Azure federated subjects remain, but the disabled switches and
environment review gates prevent their use in the current workflows. Future
OIDC enablement would require a new permission and plan review, followed by
an actual zero-change hosted plan and an approved `main` deployment. Until
then, the [runbook](runbook.md) describes the active local MFA path.
