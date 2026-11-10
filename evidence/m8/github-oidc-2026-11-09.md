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
  production plan with the same inputs reported **zero changes**. A complete
  GitHub-hosted plan remains pending the updated workflow run.
- `AZURE_DEPLOYMENT_ENABLED` remains unset. A production deployment and its
  next-hour heartbeat are not yet verified.
