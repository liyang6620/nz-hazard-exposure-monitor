# Production apply recovery review, 2 Nov 2026 NZDT

The project manager approved the 1 November `budget-killswitch` start date in
addition to replacing the placeholder GitHub principal ID. Immediately before
apply, the active subscription matched the reviewed plan and the management
token included MFA. The saved plan contained 50 creates, zero changes, zero
deletes, and only those two approved value differences.

## Partial apply

The apply created part of the approved production infrastructure, including
the two storage accounts, private data containers and queues, the public static
website configuration, Key Vault, monitoring resources, Azure OpenAI, ACS Email
and its Azure-managed domain. A read-only ARM query confirmed all four intended
runtime tables exist. The ACS managed domain did **not** fail to create.

Terraform stopped on these errors:

1. AzureRM attempted key-based data-plane ACL calls for four Azure Tables on
   the ADLS account. Shared-key access is disabled as approved, so Azure
   returned 403. The tables were created but marked tainted in Terraform state.
2. Flex Consumption rejected the explicit `FUNCTIONS_WORKER_RUNTIME` app
   setting. Python is already specified by the Function resource's runtime
   fields; the Function App was not created.
3. Application Insights `exceptions/count` rejected `Total` aggregation and
   requires `Count`; the metric alert was not created.
4. Azure activity showed transient `PrincipalNotFound` responses for newly
   created identities during role assignment. The affected assignments remain
   in the uncreated set and can be retried after directory replication.

No reference data or Function package has been uploaded. No ACS approval email,
budget-stop test, Azure/local replay comparison, cloud event processing, or
public website acceptance has occurred. The partial deployment may accrue
storage and monitoring charges; actual billed cost is not yet available.

## Proposed repair plan, not approved for apply

- Manage the four existing tables through AzAPI's ARM resource instead of
  AzureRM's key-based table operation. Declarative `removed` and `import`
  blocks preserve the Azure tables and move their Terraform addresses. The
  plan shows four `forget` state actions and four imports, with **zero Azure
  resource deletes**.
- Remove the unsupported Flex app setting and change the metric aggregation
  to `Count`. Neither change broadens permissions or network exposure.
- The state-aware saved plan has **17 creates, 4 state forgets paired with 4
  imports, 0 cloud resource updates, and 0 deletes**. The creates are the
  Function App, budget-stop Action Group and budget, the metric alert, and 13
  Function role assignments. Existing resources otherwise show no changes.

The saved plan remains only at ignored
`tmp/m1-a-production-repair-review.tfplan`, SHA-256
`F27B91AD158145BB7000A48B0289DF98F2BD3C7BF06E899C7E622763E9290869`.
This recovery differs from the approved 50-create plan in provider/resource
type and Function/alert settings. **Do not apply it without project-manager
review.** No Terraform state was manually removed and no production repair
apply was attempted.

## Approved repair and initial deployment

The project manager approved this exact recovery plan after PR #31 CI passed.
The management token still included MFA, and the saved-plan SHA-256 matched the
reviewed value immediately before apply. Terraform completed with four imports,
17 creates, zero changes, and zero destroys. The approved reference and M3 gold
data upload then completed: 56 Parquet files, 216,680,598 bytes.

The CI-built Linux Function package was accepted by the deployment service and
all six expected functions indexed. Azure CLI returned an error while fetching
the host key for its post-deployment status check, so runtime validation remains
open. The first static-site upload hit an ADLS Gen2 hierarchical-namespace name
conflict: `history` and `history/index.html` cannot both exist. The route
publisher now writes only the requested extensionless paths; direct HTTP checks
are pending the corrected publication.

The Function host initially failed to read its Blob secret repository. A
read-only settings check found that the platform had injected a base
`AzureWebJobsStorage` connection string despite the identity-based settings in
Terraform. The base setting takes precedence and used a shared key against the
host account, where shared keys are disabled. The Function's system identity
already held Blob Data Owner, Queue Data Contributor and Table Data Contributor
on the host account. The injected base setting was removed without changing
roles or network exposure; the deployment workflow now repeats this removal on
future deployments.

After the host started, Application Insights reported that the `queueTrigger`
binding for `process_event` was not registered. `host.json` lacked the Functions
extension bundle declaration required for the Python queue trigger. The standard
v4 bundle declaration has been added; queue consumption must be rechecked after
the next package deployment.
