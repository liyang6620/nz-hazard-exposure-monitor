# Azure for Students read-only assessment

Checked: 2026-10-26 14:27 NZDT

This assessment used the repository owner's interactive Azure CLI login and
read-only ARM, Microsoft Graph and Azure CLI queries. It contains no
subscription ID, tenant ID or email address. No resource, resource group,
provider registration, application, federated credential, budget or Action
Group was created or modified.

## Subscription

| Check | Result |
|---|---|
| Offer | Azure for Students (`AzureForStudents_2018-01-01`) |
| State | Enabled |
| Spending limit | On |
| Subscription RBAC | Owner |
| Existing resource groups/resources | 0 / 0 |
| Exact remaining credit | Not exposed by the available CLI/ARM billing endpoints |
| Exact expiry date | Not exposed by the available CLI/ARM subscription endpoints |

The billing account and profile were active. Consumption usage returned no
records and zero measured cost for the current month, but that is not evidence
of the remaining promotional-credit balance. The owner's expected expiry of
approximately October 2027 was not independently verified and must not be used
as an automated lifecycle date until it is read from the Education portal.

## Region policy

One enforced subscription policy, `Allowed resource deployment regions`, was
returned. Its allowed values are:

- `australiaeast`
- `japaneast`
- `koreacentral`
- `eastasia`
- `indonesiacentral`

`australiaeast` is therefore allowed and remains the preferred deployment
region. No fallback region is required. `newzealandnorth` exists in Azure but
is not allowed by this subscription policy.

## Required resource providers

| Namespace | Registration state |
|---|---|
| `Microsoft.Storage` | Registered after explicit approval |
| `Microsoft.Web` | Registered after explicit approval |
| `Microsoft.KeyVault` | Registered after explicit approval |
| `Microsoft.ManagedIdentity` | Registered after explicit approval |
| `Microsoft.Communication` | Registered after explicit approval |
| `Microsoft.OperationalInsights` | Registered after explicit approval |
| `Microsoft.Insights` | Registered |
| `Microsoft.CognitiveServices` | Registered after explicit approval |
| `Microsoft.Resources` | Registered |
| `Microsoft.Authorization` | Registered |
| `Microsoft.CostManagement` | Registered |
| `Microsoft.Consumption` | Registered |
| `Microsoft.AVS` | NotRegistered; leave unmanaged and unregistered |

The initial table was read-only. The project manager subsequently approved the
seven registrations, which were executed and all reached `Registered`. No
resource was created by registration.

## Service availability

| Service | Read-only finding |
|---|---|
| Flex Consumption Functions | The subscription-specific catalog lists `australiaeast`. FC1 with Python 3.12 is returned, including 512 MB, 2,048 MB and 4,096 MB memory options. The regional quota API cannot be validated before `Microsoft.Web` registration. |
| Storage | The subscription SKU API returns 26 SKUs in `australiaeast`, including `Standard_LRS`. |
| Key Vault | The `vaults` resource type catalog lists `Australia East`; deployment remains conditional on approved `Microsoft.KeyVault` registration. |
| Azure Communication Services Email | After registration, `CommunicationServices`, `EmailServices` and `EmailServices/Domains` are all listed as global resources. The usage endpoint returned `InvalidResourceType` and a name-check probe returned `InvalidRequestContent`; no resource was created. Azure-managed-domain creation therefore remains an apply-time acceptance item. |
| Application Insights | `Microsoft.Insights` is registered; `components` lists `Australia East`. The FC1 runtime response also reports Application Insights support. |
| Log Analytics | `workspaces` lists `Australia East`; deployment remains conditional on approved `Microsoft.OperationalInsights` registration. |
| Action Groups | The read API succeeds and returns zero existing groups. `actiongroups` is a global resource type and `Microsoft.Insights` is registered. |

These are catalog and read-API findings, not deployment evidence. The approved
provider registrations do not prove that the student offer will accept every
planned resource or quota request.

## Entra application and GitHub OIDC

The school directory authorization policy reports
`allowedToCreateApps = false`. The signed-in account has no assigned directory
role and owns no applications. It therefore cannot create the two Entra
applications or their federated identity credentials required by the current
`infra/identity` design.

The project manager subsequently selected a user-assigned managed identity with
GitHub federated credentials. That design uses Azure Resource Manager and does
not require an Entra application registration. No request for broader directory
rights was made.

## Budgets and kill switch

- The subscription budget read API succeeds and returns zero existing budgets.
- The Action Group read API succeeds and returns zero existing Action Groups.
- The signed-in account is subscription Owner, so ARM RBAC is not the known
  blocker for creating these resources after approval.
- A read-only Cost Management ActualCost query returned HTTP 429. Budget
  calculation on this student offer is therefore not verified.
- No budget, Action Group, alert or webhook was created to test write behavior.

The Terraform budget and stop-chain design should be retained in the next plan,
but its effective calculation and notification behavior must remain an Azure
deployment acceptance item until an approved apply and live test are possible.

## Decision gate

This read-only assessment is superseded by the separately reviewed M1-A plans.
No Azure write is allowed until those plans and the provider-registration list
are approved.
