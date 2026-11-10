# GitHub OIDC deployment handover, 9 Nov 2026 NZDT

The project manager approved the completion plan in
[`docs/github-oidc-completion.md`](../../docs/github-oidc-completion.md).
This record separates configuration from a successful GitHub-hosted release.

## Bootstrap and repository configuration

- The saved bootstrap plan contained exactly two updates, both to
  `azurerm_federated_identity_credential` resources. A JSON plan comparison
  showed `subject` as the only changed field for each. The new subjects are
  `environment:terraform-plan` and `environment:production` for the same
  repository and user-assigned identity. No role, scope, resource, issuer,
  audience or network setting changed.
- The owner MFA management token contained `amr=mfa` before the saved plan was
  applied. A fresh bootstrap plan afterward reported zero changes. Local
  bootstrap state, plan and logs remain ignored and are not published.
- Both GitHub environments require review by the repository owner. The
  `production` environment has a custom branch policy allowing only `main`.
  The plan workflow accepts only same-repository PRs targeting `main`, or
  manual dispatch on `main`; the deploy workflow requires `main`.
- Each environment has only its named encrypted secrets. Their values were
  supplied from local Terraform outputs, the current Azure account and
  ignored local configuration through the GitHub CLI's standard input. No
  secret value or account identifier is included here.
- [PR #72](https://github.com/liyang6620/nz-hazard-exposure-monitor/pull/72)
  merged after all CI checks passed. It contains the subject definitions,
  workflow gates and updated identity test; it does not include secret values.

## Workflow verification

- `AZURE_OIDC_ENABLED=true` was set after the branch and reviewer gates were
  checked. The first attempt of the [read-only plan run](https://github.com/liyang6620/nz-hazard-exposure-monitor/actions/runs/42479175837)
  passed the owner's environment gate but failed at `azure/login` with
  `AADSTS700213`. GitHub's actual default subject included immutable numeric
  IDs after the owner and repository names; the Azure federated subjects used
  names alone. No Terraform state access or apply occurred in that attempt.
- On 10 Nov NZDT, the observed claim was compared with the IDs returned by the
  GitHub repository API. The strings matched exactly. A new saved bootstrap
  plan contained only the same two federated credential `subject` updates,
  adding those IDs while retaining each environment, identity, audience,
  issuer and role scope. The owner MFA token was rechecked before apply; a
  post-apply bootstrap plan reported zero changes. The numeric IDs and plan
  files remain out of the repository and evidence.
- The owner approved attempt two. `azure/login` and remote production-state
  initialization both passed, proving the corrected OIDC trust can reach the
  private backend. The plan step then failed because the workflow omitted the
  required `owner_object_id` and `budget_start_date` variables; no apply ran.
- The workflow now supplies those variables from encrypted environment
  secrets, along with the existing second alert receiver. It sets the Azure
  ArcGIS publisher input to its already deployed `true` state. The budget
  date was normalized to UTC RFC3339 before storing it. A local read-only
  production plan with the same inputs reported **zero changes**.
- The owner approved the [PR #73 GitHub plan run](https://github.com/liyang6620/nz-hazard-exposure-monitor/actions/runs/42729229579).
  OIDC login and remote state initialization passed. During state refresh,
  Terraform received HTTP 401 reading the subscription-level
  `budget-killswitch`. The GitHub identity has no subscription-level budget
  read role; this is a permission gap, not another subject mismatch. No plan
  completed and no apply ran. `AZURE_OIDC_ENABLED` was returned to `false`
  while this scope change is reviewed; the production deployment switch
  remains unset.
- Candidate fix for project-manager review: a subscription-scoped custom
  read-only role limited to `Microsoft.Consumption/budgets/read`, assigned to
  the existing GitHub managed identity. This would add a role definition and
  one assignment, with no write permission, new identity or network change.
  A saved local bootstrap proposal plan was checked: **2 creates, 0 updates,
  0 deletes**, and no other resource changes. Its SHA-256 is
  `B11C063C4CFEC2D921E36CA57F1BA9F96763A577115DEE7A49E8B27E2617275C`.
  The saved plan is ignored and must be regenerated from reviewed source before
  any eventual apply. This permission change is **not approved or applied**.
  The broader built-in Cost Management Reader
  role also includes other Cost Management and Support actions and was not
  granted. If the narrow role does not resolve the 401, stop and review again.
- `AZURE_DEPLOYMENT_ENABLED` remains unset. A production deployment and its
  next-hour heartbeat are not yet verified.
