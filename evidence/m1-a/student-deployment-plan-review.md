# Azure for Students M1-A plan review

Generated: 2026-10-26 NZDT

All plans used the interactively selected Azure for Students subscription,
`australiaeast`, Terraform 1.16.6 and AzureRM 4.81.0. The seven explicitly
approved provider registrations were performed. No Terraform apply, import,
state migration, Azure resource creation or paid API call was performed.
Subscription ID, tenant ID and notification email are absent from this evidence.

The subscription billing profile reports NZD and has its spending limit on.
The fixed budgets therefore retain their original NZD 2, NZD 5 and NZD 8
amounts; the production kill-switch budget remains NZD 5. The student spending
limit is the final backstop and must not be disabled or replaced with PAYG.

## Provider registration and ACS recheck

The project manager approved registration of these seven providers. Registration
was executed on 2026-10-26 and all seven reached `Registered`:

1. `Microsoft.CognitiveServices`
2. `Microsoft.Communication`
3. `Microsoft.KeyVault`
4. `Microsoft.ManagedIdentity`
5. `Microsoft.OperationalInsights`
6. `Microsoft.Storage`
7. `Microsoft.Web`

`Microsoft.Insights` was already registered and was not written.
`Microsoft.AVS` remains unregistered and unmanaged.

After registration, the resource catalog lists `CommunicationServices`,
`EmailServices` and `EmailServices/Domains` as global resource types. The usage
endpoint returned `InvalidResourceType`, and a read-only name-check probe
returned `InvalidRequestContent`. No ACS resource was created. Actual
Azure-managed-domain eligibility therefore remains unverified; if its approved
create is rejected, stop and submit the exact error plus an alternative design.

The subscription also does not expose the planned `Azure Communication Services
Email Sender` built-in role. The only visible communication/email management
role is too broad for the runtime. The revised production plan therefore uses
the ACS connection string from protected Terraform state and Function app
settings. It is never committed or copied to evidence.

## Bootstrap plan

Result: **12 add, 0 change, 0 destroy**.

Plan SHA-256:
`F3A26DD95E4C0B03656FA6D2ED00D4D0EAE80C9B29C70126FFCDE46B8E1C87C7`

Resources:

- two resource groups: remote state and production;
- one Standard LRS state storage account and one private state container;
- one GitHub user-assigned managed identity;
- one custom `NZHEM Function Stop Operator` role, created by the owner-run
  bootstrap with a deterministic role ID;
- two workload identity credentials, restricted to this repository's pull
  requests and `main` branch;
- `Storage Blob Data Contributor` for the owner and GitHub identity on the state
  container;
- `Contributor` and `Role Based Access Control Administrator` for the GitHub
  identity on the production resource group only.

There is no subscription-level role for GitHub. The production-resource-group
RBAC Administrator assignment has condition version 2.0. It allows assignment
and deletion only for these roles, and only when the target principal type is
`ServicePrincipal`:

- `Storage Blob Data Contributor`;
- `Storage Queue Data Contributor`;
- `Storage Table Data Contributor`;
- `Key Vault Secrets User`;
- `Cognitive Services OpenAI User`;
- custom `NZHEM Function Stop Operator`.

Owner, User Access Administrator and Role Based Access Control Administrator are
not in the allowlist. The custom role definition itself is bootstrap-owned, so
the GitHub identity cannot create or modify role definitions. Human owner role
assignments are not present in the GitHub-applied production root. If federation
or the conditioned assignment is rejected, stop and use the approved fallback:
owner-run local `az login`, with CI limited to fmt/validate.

Network exposure: the state storage account uses a public Azure endpoint, but
the container is private, anonymous nested-item access is disabled and shared
key authentication is disabled. Access uses Entra RBAC.

Expected monthly cost: resource groups, managed identity, federated credentials
and RBAC have no charge. A small versioned state container is expected to cost
approximately **NZD 0.01-0.10/month**, depending on retained versions and
transactions.

## Guardrails plan

Result: **3 add, 0 change, 0 destroy**.

Plan SHA-256:
`762C6092A261D65819043224B29EB79A8454E30FCCDEA6622F91397EA6584432`

Resources:

- `spend-alert-1`: NZD 2, Actual 100%;
- `spend-alert-3`: NZD 5, Actual 100% and Forecasted 100%;
- `spend-alert-5`: NZD 8, Actual 100%.

All three budgets are monthly, notify the uncommitted email variable and use
`prevent_destroy`. They add no role assignment and no network endpoint.

Expected monthly cost: **NZD 0**.

The old subscription's local state and saved plan were moved intact to ignored
`tmp/guardrails-old-subscription-2026-10-26/`. This plan starts from empty state
and does not import or migrate that archive.

## Production plan

Result: **41 add, 0 change, 0 destroy**.

Plan SHA-256:
`7DF01C5D8DD9D07C5D927D028DF048172639D2ECFCA69E6D8952A450CB4DFCA9`

Resources by function:

- data: one ADLS Gen2 StorageV2 account, five private containers, one queue,
  three tables, static website configuration and one lifecycle policy;
- compute: one Linux FC1 plan, one Python 3.12 Flex Consumption Function App
  capped at one 2 GB instance, and one package-storage managed identity;
- secrets and monitoring: one Key Vault, Log Analytics workspace, Application
  Insights component, two Action Groups and one metric alert;
- email: one ACS service, one Email Communication Service, one Azure-managed
  domain and one domain association;
- LLM: one Azure OpenAI account and one `gpt-5-mini` Global Standard deployment
  at capacity 1;
- cost and approvals: one NZD 5 subscription budget, one random 32-byte webhook
  token, one random 48-byte HMAC key, and the budget Action Group;
- authorization: 11 role assignments for the Function and package identity. The
  custom role is now bootstrap-owned, and the two human owner assignments and
  unavailable ACS sender-role assignment were removed. No GitHub or
  subscription-level role is created by this plan.

The count changed from 44 to 41: remove one custom role definition, two human
role assignments and one unavailable ACS sender role assignment; add one random
approval HMAC key. No billable service was added by the revision.

Network exposure:

- Function public networking is enabled and HTTPS is mandatory. Whole-app
  access restrictions default to allow because they cannot distinguish routes;
  every HTTP route authenticates in application code as shown below;
- the SCM deployment endpoint is public, basic authentication is disabled, and
  deployment relies on Azure RBAC/OIDC;
- Storage, Key Vault and Azure OpenAI use public Azure endpoints to avoid fixed
  private-endpoint cost;
- Storage anonymous access and shared keys are disabled, Key Vault uses RBAC,
  and Azure OpenAI local-key authentication is disabled;
- the static website is intentionally public; it contains approved public
  outputs only.

Microsoft documents that disabling Blob anonymous access does not affect a
storage static website and that `$web` remains publicly accessible. Static
website reads use the separate website endpoint; the five ordinary containers
remain private. Source:
<https://learn.microsoft.com/azure/storage/blobs/anonymous-read-access-configure>.

## Function HTTP route authentication

| Route | Method | Application authentication | Missing or failed authentication |
|---|---|---|---|
| `/api/budget-stop` | POST | Terraform-generated 32-byte random query token, constant-time comparison, then Azure Monitor common-alert-schema validation | Missing/wrong token: 403 before storage, email or ARM work. Invalid JSON/schema after authentication: 400. |
| `/api/review-briefing` | GET | Signed HMAC token containing briefing ID, action and expiry; briefing must still be pending and unused | Uniform 400; no mutation. Valid GET only renders a confirmation form. |
| `/api/review-briefing` | POST | Same HMAC plus expiry, pending-state and one-time-use checks | Uniform 400 for tamper, expiry, replay or unavailable briefing. Only valid POST approves/rejects and may publish. |
| `/api/map-token` | GET | Currently disabled under MG plan B and returns 404. If later enabled, exact HTTPS `Origin`, same-origin `Referer` when supplied, and a hashed-client-IP limit of 30 requests/minute run before any broker call | Disabled: 404; wrong origin: 403; limit exceeded: 429. Even a valid guarded request currently returns 503 until a separately approved read-only OAuth broker exists. |

Those are the only HTTP triggers. `housekeeping` is a timer trigger. All HTTP
decorators use Functions `ANONYMOUS` auth deliberately so browsers and Action
Groups do not need a platform Function key. Function keys are not used as
authorization and do not bypass the application checks; SCM basic publishing
authentication is disabled. The owner-privileged ArcGIS publisher key is never
served to a browser.

The budget webhook token, approval HMAC key and ACS connection string are
sensitive and absent from source and this summary. Terraform stores them in
protected state and supplies them only to Function settings as required.

The Azure OpenAI deployment uses `GlobalStandard`. Microsoft states that Global
requests may be processed in any Azure region, so processing may occur outside
Australia. This is accepted because prompts contain only public earthquake and
exposure data; no private owner or subscriber data is sent to the model.

Expected normal demonstration-month cost: approximately **NZD 0.50-1.60**.
There is no always-ready Function instance or private endpoint. The estimate is
usage-sensitive and assumes low Function execution, a few GB of storage, low
email volume, sampled logs, and the enforced maximum of ten short briefings.
The code-capped OpenAI portion was previously estimated at no more than USD
0.051/month. Retail prices and the model version must be rechecked immediately
before apply; the NZD 2 alert is deliberately close to the expected range.

## Cost Management retry

The ActualCost read query was retried with the correct JSON content type and
again returned HTTP 429. Budget resources can be planned, but live budget
calculation remains an Azure deployment acceptance item. The Action Group and
student spending limit do not depend on this read query.

## State and approval boundary

The bootstrap saved plan is generated from the real bootstrap root and can be
matched by its hash. Because the remote state account does not yet exist, the
guardrails and production plans are pre-bootstrap review plans generated from
temporary, ignored copies of the exact modules with only `backend.tf` omitted.
They are not apply artifacts. The revised production pre-bootstrap plan uses
an ignored copy of the exact module with only `backend.tf` omitted.

After an approved bootstrap apply, initialize the formal `guardrails.tfstate`
and `production.tfstate` backends and regenerate both saved plans. They must
still report 3 and 41 creates respectively. Any content or count difference is
submitted for review before apply.

No action in this approval package authorizes registration or apply.
