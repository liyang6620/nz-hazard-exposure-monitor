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
  checked. The [read-only plan run](https://github.com/liyang6620/nz-hazard-exposure-monitor/actions/runs/42479175837)
  is waiting for the owner's `terraform-plan` environment approval. It has not
  yet demonstrated state access.
- `AZURE_DEPLOYMENT_ENABLED` remains unset. A production deployment and its
  next-hour heartbeat are not yet verified.
