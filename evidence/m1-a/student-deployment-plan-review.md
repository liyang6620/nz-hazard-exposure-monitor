# Azure for Students M1-A plan review

Generated: 2026-10-26 NZDT

All plans used the interactively selected Azure for Students subscription,
`australiaeast`, Terraform 1.16.6 and AzureRM 4.81.0. No provider registration,
apply, import, state migration, Azure resource creation or paid API call was
performed. Subscription ID, tenant ID and notification email are absent from
this evidence.

The subscription billing profile reports NZD and has its spending limit on.
The fixed budgets therefore retain their original NZD 2, NZD 5 and NZD 8
amounts; the production kill-switch budget remains NZD 5. The student spending
limit is the final backstop and must not be disabled or replaced with PAYG.

## Provider-registration approval list

The following seven providers are currently `NotRegistered`. Registration is a
subscription-level write but has no direct charge:

1. `Microsoft.CognitiveServices`
2. `Microsoft.Communication`
3. `Microsoft.KeyVault`
4. `Microsoft.ManagedIdentity`
5. `Microsoft.OperationalInsights`
6. `Microsoft.Storage`
7. `Microsoft.Web`

`Microsoft.Insights` is already registered and is not in the write list.
`Microsoft.AVS` remains unregistered and unmanaged.

After approved registration, recheck the ACS location/usage APIs immediately.
Actual Azure-managed email-domain eligibility cannot be proved by a read-only
query; it is represented by the production plan's email service, managed domain
and association resources. If any of those creates are rejected, stop without
substituting another mail service and submit the exact error plus an alternative
design for approval.

## Bootstrap plan

Result: **11 add, 0 change, 0 destroy**.

Plan SHA-256:
`E63F7200563A4D49E8F95D8A33DB3B8A7276793E2172599FF7869411CD96E622`

Resources:

- two resource groups: remote state and production;
- one Standard LRS state storage account and one private state container;
- one GitHub user-assigned managed identity;
- two workload identity credentials, restricted to this repository's pull
  requests and `main` branch;
- `Storage Blob Data Contributor` for the owner and GitHub identity on the state
  container;
- `Contributor` and `Role Based Access Control Administrator` for the GitHub
  identity on the production resource group only.

There is no subscription-level role for GitHub. The RBAC administrator role is
needed because the production module creates narrowly scoped runtime role
assignments and one custom Function stop role. If either managed-identity
federation or scoped role assignment is rejected, stop and use the approved
fallback: owner-run local `az login` deployment while CI runs only fmt/validate.

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

Result: **44 add, 0 change, 0 destroy**.

Plan SHA-256:
`A69800459EDC39BFD8753F2467F846B2394CC6123B037D342A19A7F84E1100C1`

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
- cost stop: one NZD 5 subscription budget, one random 32-byte webhook token,
  and the budget Action Group;
- authorization: one custom stop-only role and 14 role assignments for the
  Function, package identity and owner. No GitHub or subscription-level role is
  created by this plan.

Network exposure:

- Function public networking is enabled, HTTPS is mandatory, application
  ingress defaults to deny, and only the `ActionGroup` service tag is allowed;
- the SCM deployment endpoint is public, basic authentication is disabled, and
  deployment relies on Azure RBAC/OIDC;
- Storage, Key Vault and Azure OpenAI use public Azure endpoints to avoid fixed
  private-endpoint cost;
- Storage anonymous access and shared keys are disabled, Key Vault uses RBAC,
  and Azure OpenAI local-key authentication is disabled;
- the static website is intentionally public; it contains approved public
  outputs only.

The budget webhook token is sensitive and is not present in source or this
summary. Terraform stores it in protected state and supplies it to the Function
setting and Action Group URI. The Function rejects a missing or incorrect token
before any table, email or ARM operation.

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
They are not apply artifacts.

After an approved bootstrap apply, initialize the formal `guardrails.tfstate`
and `production.tfstate` backends and regenerate both saved plans. They must
still report 3 and 44 creates respectively. Any content or count difference is
submitted for review before apply.

No action in this approval package authorizes registration or apply.
