# GitHub OIDC deployment completion proposal

Status: **approved and partly configured; production deployment not yet
verified** (10 Nov 2026 NZDT). The live Azure deployment has used an
owner-authorised local MFA session. GitHub CI validates and builds.

## Verified repository state

- Before implementation, the repository had no `AZURE_OIDC_ENABLED` or
  `AZURE_DEPLOYMENT_ENABLED` variable. Its only listed repository secret was
  the browser-scoped LINZ LDS tile key.
- Before implementation, the `terraform-plan` environment had no required
  reviewer and the `production` environment had not been configured.
- The bootstrap identity has federated subjects for
  `repo:<owner>/<repo>:pull_request` and
  `repo:<owner>/<repo>:ref:refs/heads/main`. Both workflows declare a GitHub
  environment. The observed default GitHub claim also appends immutable
  numeric IDs to the owner and repository names. Azure must match the exact
  environment-scoped subject, including those IDs; do not commit them.

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
   | `terraform-plan` | `AZURE_CLIENT_ID`, `AZURE_TENANT_ID`, `AZURE_SUBSCRIPTION_ID`, `AZURE_GITHUB_PRINCIPAL_ID`, `AZURE_OWNER_OBJECT_ID`, `TFSTATE_RESOURCE_GROUP`, `TFSTATE_STORAGE_ACCOUNT`, `NOTIFICATION_EMAIL`, `FAILURE_ALERT_GMAIL`, `BUDGET_START_DATE` |
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

The production plan workflow must also set
`TF_VAR_arcgis_publisher_enabled=true` to match the live single-publisher
handover. Its private owner ID, second alert address and budget start date
come from the current deployment; omitting them prevents a plan or creates
misleading drift. The bootstrap's GitHub owner and repository IDs are read
from the GitHub API as sensitive Terraform inputs.

The first approved read-only workflow reached `azure/login` but failed because
the federated subjects lacked those immutable IDs. A saved bootstrap plan
changed only the two subjects, with no role or resource-scope change; owner
MFA apply and a zero-change follow-up plan completed. The second approved
workflow passed OIDC login and state initialization but exposed two missing
Terraform inputs (`owner_object_id` and `budget_start_date`). The environment
now holds the needed values without publishing them. Production deployment
remains disabled until the read-only plan and a reviewed release both pass.
