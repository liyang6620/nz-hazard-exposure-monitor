# GitHub OIDC deployment completion proposal

Status: **proposal for project-manager review; not enabled** (9 Nov 2026 NZDT).
The live Azure deployment has used an owner-authorised local MFA session.
GitHub CI validates and builds but does not currently deploy.

## Verified repository state

- The repository has no `AZURE_OIDC_ENABLED` or
  `AZURE_DEPLOYMENT_ENABLED` variable. Its only listed repository secret is
  the browser-scoped LINZ LDS tile key.
- The `terraform-plan` GitHub environment exists with no required reviewers
  or branch policy. A `production` environment is not yet configured.
- The bootstrap identity has federated subjects for
  `repo:<owner>/<repo>:pull_request` and
  `repo:<owner>/<repo>:ref:refs/heads/main`. Both workflows declare a GitHub
  environment, which normally changes the OIDC `sub` to
  `repo:<owner>/<repo>:environment:<environment>`. Those existing subjects
  therefore do not match the workflow jobs. Enabling the switches alone is
  insufficient.

## Proposed configuration, in review order

1. Review a Terraform plan replacing the two federated credential subjects
   with `environment:terraform-plan` and `environment:production`. Keep the
   same user-assigned identity and role scopes. This changes identity trust,
   so it requires explicit project-manager approval before apply.
2. Add a required reviewer to each GitHub environment. Restrict
   `production` deployments to `main`; add a workflow-level
   `github.ref == 'refs/heads/main'` gate. Restrict the plan workflow to
   repository-owned pull-request branches and protect it with the environment
   reviewer. Confirm these rules with an unprivileged PR before any plan can
   access credentials. Do not rely on an empty environment as a security gate.
3. Store the following values as **GitHub encrypted environment secrets**;
   do not put their values in repository files, CI logs, artifacts, screenshots
   or issue comments. The environment split follows the existing workflows:

   | Environment | Secret names |
   | --- | --- |
   | `terraform-plan` | `AZURE_CLIENT_ID`, `AZURE_TENANT_ID`, `AZURE_SUBSCRIPTION_ID`, `AZURE_GITHUB_PRINCIPAL_ID`, `TFSTATE_RESOURCE_GROUP`, `TFSTATE_STORAGE_ACCOUNT`, `NOTIFICATION_EMAIL` |
   | `production` | `AZURE_CLIENT_ID`, `AZURE_TENANT_ID`, `AZURE_SUBSCRIPTION_ID`, `AZURE_RESOURCE_GROUP`, `AZURE_FUNCTION_APP_NAME`, `AZURE_STORAGE_ACCOUNT`, `LINZ_LDS_TILES_API_KEY` |

4. Only after identity claims, reviewers, branch restrictions and secrets are
   verified, set repository **variables** `AZURE_OIDC_ENABLED=true` and
   `AZURE_DEPLOYMENT_ENABLED=true`. These two booleans contain no identifiers.
   An approved plan workflow should first prove private state access without
   applying. A reviewed `main` deployment can then prove the served build SHA,
   six triggers, managed-identity host storage and next scheduled hourly
   heartbeat as in the runbook. Keep the local MFA deployment path documented
   until that verification passes.

The Azure client, tenant and subscription IDs are identifiers rather than
passwords, but the owner has explicitly prohibited them from the public
repository and screenshots. Keeping them in encrypted GitHub secrets respects
that rule. The LINZ LDS tile key is deliberately browser-readable and therefore
not a server secret; it is separate from ArcGIS, OpenAI and approval keys.
Third-party server keys remain in Key Vault or protected runtime settings.

No GitHub setting, identity trust, Azure role, resource or workflow was changed
by this proposal. If the project manager decides not to enable OIDC, retain
the present local MFA deployment statement in the README and ADR.
