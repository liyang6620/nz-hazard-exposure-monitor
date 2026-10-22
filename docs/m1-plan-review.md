# M1 plan review notes

## Approval boundary

The M1 rollout is staged so every Azure mutation has a saved plan:

1. Explicit provider registrations in `infra/providers`.
2. State resource group, storage account and container in `infra/bootstrap`.
3. Entra applications, service principals and federated credentials in
   `infra/identity`.
4. Production resources in `infra/terraform`.
5. Guardrails local-state migration to the `guardrails.tfstate` backend key.

No apply, registration, import, state migration, Action Group test, email send,
or model inference occurs before approval. The three M0 fixed budgets remain in
their independent root and are not present in the production plan.

## Azure OpenAI price and hard limits

The Azure OpenAI pricing page was checked on 2026-10-23 for Australia East,
Global Standard `GPT-5-mini`. It lists USD 0.25 per million input tokens, USD
0.025 per million cached input tokens, and USD 2.00 per million output tokens.
Source: <https://azure.microsoft.com/pricing/details/cognitive-services/openai-service/>.

The code and Function settings reserve at most 12,000 total tokens per briefing,
including at most 1,200 output/reasoning tokens, and at most 10 briefings per
month. A conservative uncached maximum is:

```text
10,800 input * USD 0.25 / 1,000,000 = USD 0.00270
 1,200 output * USD 2.00 / 1,000,000 = USD 0.00240
worst case per briefing                 USD 0.00510
worst case for 10 briefings/month       USD 0.05100
```

The model version and displayed price must be rechecked immediately before
apply. No inference is part of M1 validation.

## Expected no-charge creation versus metered use

Resource creation for budgets, identities, role assignments, Action Groups,
storage configuration, and the Azure OpenAI deployment does not itself produce
token charges. Storage capacity/operations, Function execution, logs, Key Vault
operations, ACS email, and later model inference are metered. The existing M0
estimate remains USD 0.25-0.90 in a normal demonstration month and below the
USD 3 hard ceiling; the NZD 5 `budget-killswitch` is the approved approximate
ceiling in the subscription billing currency.

## Items verified only after approved apply

- Actual model deployment availability and version in Australia East.
- Managed-domain sender address and the minimum ACS email RBAC role.
- Secure Action Group token acceptance by Easy Auth.
- Function startup, managed-identity table write, metric alert email, and the
  complete stop/recovery drill.
- Linux package compressed size and temporary-space headroom from GitHub CI.
