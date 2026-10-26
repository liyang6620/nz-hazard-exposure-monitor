# Required Azure resource providers

All AzureRM provider blocks disable automatic registration. Registration is a
separately reviewed operation in `infra/providers`; `Microsoft.AVS` is not
managed and remains unregistered in the Azure for Students subscription.

| Namespace | M1 use |
|---|---|
| `Microsoft.Storage` | State storage, ADLS Gen2, queues and tables |
| `Microsoft.Web` | Flex Consumption plan and Function App |
| `Microsoft.KeyVault` | Runtime secret store |
| `Microsoft.ManagedIdentity` | Package-storage user-assigned identity |
| `Microsoft.Communication` | ACS and managed email domain |
| `Microsoft.OperationalInsights` | Log Analytics workspace |
| `Microsoft.Insights` | Application Insights, Action Groups and metric alert |
| `Microsoft.CognitiveServices` | Azure OpenAI account and model deployment |

On the 2026-10-26 Azure for Students assessment, `Microsoft.Insights` was
already registered. The first approval list therefore contains the other seven
namespaces only. Registration is free but remains an explicit write operation.

`Microsoft.Resources`, `Microsoft.Authorization`, and
`Microsoft.CostManagement` are platform namespaces used for the resource group,
RBAC, and budgets. Their registration state is checked before apply; they are
not included in the registration root unless Azure reports that they support
explicit registration and are unregistered.

No provider registration command may run before plan approval.
